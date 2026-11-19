;; Compile and run js-browser-static/v1 modules in headless Chromium (ADR 0397, JUN-706).
;;
;; A compiler F (the Mac full compiler, or a Linux ELF) compiles the 24 runtime cases (seed/static-cases.json)
;; and the wasm probes (spin, deep, entry) to both --target js-browser and --target wasm32-browser. The modules
;; run in headless Chromium through runtime/js-browser-static-run.html and the shared Worker host, driven by the
;; DevTools pipe (wasm32_browser_lib.cljc): no Node, npm, nbb or Playwright. The gate requires every js case to
;; return the static case's result, trap and remaining fuel; its stdout to equal the wasm module's; the probes as
;; on wasm; every module to export only instantiate and name no global or loader (FORBIDDEN, scanned outside
;; string literals, with a negative control that calls fetch); and the float cases refused at compile time
;; (E7101) without an artifact. Ported from check-js-browser.py (Basilisp, JUN-974).
;; Run: basilisp run -p scripts/seed scripts/seed/check-js-browser.cljc -- --compiler F --output OUT [--browser PATH]
(ns check-js-browser
  (:require [basilisp.string :as str]
            [gate-util :as u]
            [macos-native-lib :as mac]
            [wasm32-browser-lib :as w])
  (:import base64 json operator os pathlib re shutil subprocess sys time))

(def root u/root)
(def cases-path (pathlib/Path root "seed/static-cases.json"))
(def float-cases-path (pathlib/Path root "seed/float-cases.json"))
(def forbidden ["globalThis" "window" "self" "document" "fetch" "XMLHttpRequest" "WebSocket" "importScripts"
                "import(" "eval" "Function" "WebAssembly" "require" "process" "postMessage" "setTimeout"])

;; the three probes of selfhost-bootstrap.py WASM_PROBES that this gate compiles
(def wasm-probes
  [["spin" "(defn main [] :i64 (loop [i 0] (if (< i 0) i (recur (inc i)))))"]
   ["deep" "(defn- f [n :i64] :i64 (if (= n 0) 0 (+ 1 (f (dec n)))))\n(defn main [] :i64 (f 100000000))"]
   ["entry" (str "(defn main [] :i64 (let [p (typed-cap-call :cli/args :string :string \"0\")\n"
                 "  s (typed-cap-call :fs/app-data :string :string p) w (typed-cap-call :io/write :string :string s)]\n"
                 "  (string-length s)))")]])

(defn compile- [F work src target dst & {:keys [expected] :or {expected 0}}]
  (if (= (.-suffix F) ".macho")
    (mac/native-run F work ["compile" src "--target" target "--output" dst] :expected expected)
    (let [r (subprocess/run (python/list [(str F) "compile" src "--target" target "--output" dst]) ** :cwd work :capture_output true
                            :env (u/pydict "PATH" "/usr/bin:/bin" "KEXE_CAP_RESOURCES_35" (str work)) :timeout 1200)]
      (when (not= (.-returncode r) expected)
        (throw (python/ValueError (str src " -> " target ": exit " (.-returncode r) ": "
                                       (let [e (.decode (.-stderr r) "utf-8" "replace")] (subs e (max 0 (- (count e) 600))))))))
      r)))

(defn code-tokens
  "The module text with every string literal blanked, so the scan reads code only."
  [text]
  (re/sub "\"(?:[^\"\\\\\\n]|\\\\.)*\"" "\"\"" text))

(defn scan
  "Problems of a js-browser module: forbidden names, imports, or exports other than instantiate."
  [text]
  (let [code (code-tokens text)
        problems (atom (vec (filter (fn [name]
                                      (re/search (str "(?<![A-Za-z0-9_$])" (re/escape name)
                                                      (if (str/ends-with? name "(") "" "(?![A-Za-z0-9_$])"))
                                                 code))
                                    forbidden)))
        exports (python/list (re/findall "\\bexport\\b[^\\n]*" code))]
    (when (re/search "(?m)^\\s*import\\b" code) (swap! problems conj "import statement"))
    (when-not (u/deq exports (python/list ["export function instantiate(host){\"\";"]))
      (swap! problems conj (str "exports " (python/repr exports))))
    @problems))

(defn fail [msg] (throw (python/ValueError msg)))

(defn run [compiler output browser-arg]
  (let [F (.resolve (pathlib/Path compiler) ** :strict true)
        browser (or (w/find-browser browser-arg) (fail "no Chromium or Chrome found (--browser or KOTOBA_BROWSER)"))
        out (.resolve (pathlib/Path output))
        _ (.mkdir out ** :parents false :exist_ok false)
        work (pathlib/Path out "work")
        _ (.mkdir work)
        cases (operator/getitem (json/loads (.read_text cases-path)) "cases")
        modules (atom [])]
    (doseq [case cases]
      (let [n (operator/getitem case "name")]
        (.write_text (pathlib/Path work (str "case-" n ".kotoba")) (operator/getitem case "source"))
        (swap! modules conj (str "case-" n))))
    (doseq [[name body] wasm-probes]
      (.write_text (pathlib/Path work (str "probe-" name ".kotoba")) (str "(ns probe-" name " (:export [main]))\n" body "\n"))
      (swap! modules conj (str "probe-" name)))
    (doseq [stem @modules]
      (compile- F work (str stem ".kotoba") "js-browser" (str stem ".mjs"))
      (compile- F work (str stem ".kotoba") "wasm32-browser" (str stem ".wasm")))
    (let [scans (into {} (for [stem @modules] [stem (scan (.read_text (pathlib/Path work (str stem ".mjs"))))]))
          bad (into {} (filter (fn [[_ v]] (seq v)) scans))]
      (when (seq bad) (fail (str "module scan: " bad))))
    (let [mutated (.replace (.read_text (pathlib/Path work "case-string-literal.mjs")) "let pc=0" "let pc=0;fetch(\"x\")" 1)]
      (when-not (some #(= % "fetch") (scan mutated))
        (fail "negative control: the scan accepted a module that calls fetch")))
    (let [floats (atom [])]
      (when (.exists float-cases-path)
        (doseq [case (operator/getitem (json/loads (.read_text float-cases-path)) "cases")]
          (let [n (operator/getitem case "name")
                r (do (.write_text (pathlib/Path work (str "float-" n ".kotoba")) (operator/getitem case "source"))
                      (compile- F work (str "float-" n ".kotoba") "js-browser" (str "float-" n ".mjs") :expected 1))]
            (when (or (not (u/has-bytes? (.encode "E7101") (.-stderr r))) (.exists (pathlib/Path work (str "float-" n ".mjs"))))
              (fail (str "float case " n " was not refused: " (let [e (.-stderr r)] (u/bslice e (max 0 (- (python/len e) 300)) (python/len e))))))
            (swap! floats conj n))))
      (let [runs (vec (for [stem @modules
                            :let [probe? (str/starts-with? stem "probe-")
                                  extras (if probe?
                                           (let [pn (subs stem (count "probe-"))] (get w/probe-runs pn [[pn (python/dict)]]))
                                           [[stem (python/dict)]])]
                            [name extra] extras
                            :let [key (if probe? (str "probe-" name) name)]
                            r [[(str "js:" key) (pathlib/Path work (str stem ".mjs")) extra]
                               [(str "wasm:" key) (pathlib/Path work (str stem ".wasm")) extra]]]
                        r))
            t0 (time/time)
            [version lines] (w/run-js browser out runs 600)
            seconds (python/round (- (time/time) t0) 3)
            results (atom [])
            probe-results (atom [])]
        (doseq [case cases]
          (let [n (operator/getitem case "name")
                js (operator/getitem lines (str "js:case-" n))
                wasm (operator/getitem lines (str "wasm:case-" n))
                o (w/observe js)
                status (if (operator/getitem case "trap") "trap" "ok")
                ref (operator/getitem case "reference")
                ok (and (= (operator/getitem o "exit") (operator/getitem ref "exit"))
                        (= (operator/getitem o "remainingFuel") (operator/getitem ref "remainingFuel"))
                        (= (operator/getitem o "status") status)
                        (or (operator/getitem case "trap") (= (operator/getitem o "result") (operator/getitem case "result"))))]
            (when-not ok (fail (str "case " n ": " o " expected " (operator/getitem case "result") " " ref " (" js ")")))
            (when-not (and (= (.get js "stdout") (.get wasm "stdout")) (= (.get js "exit") (.get wasm "exit")))
              (fail (str "case " n ": js and wasm differ: " js " / " wasm)))
            (let [row (u/pydict "name" n)]
              (.update row o)
              (swap! results conj row))))
        (doseq [[name expect] w/probes]
          (let [key (str "js:probe-" name)]
            (when (operator/contains lines key)
              (let [line (operator/getitem lines key)
                    o (w/observe line)]
                (when-not (every? (fn [[k v]] (= (operator/getitem o k) v)) expect)
                  (fail (str "probe " name ": " o " expected " expect " (" line ")")))
                (when (and (= name "deep") (not (.get line "wasmTrap")))
                  (fail (str "probe deep ended without an engine trap: " line)))
                (when (and (= name "entry") (not= (.get line "output") w/entry-text))
                  (fail (str "probe entry: " line)))
                (when (and (= name "entry-denied") (not (operator/contains (or (.get line "stderr") "") ":wire 38 :refused")))
                  (fail (str "probe entry-denied: " line)))
                (let [row (u/pydict "name" name "engineTrap" (.get line "wasmTrap"))]
                  (.update row o)
                  (swap! probe-results conj row))))))
        (let [report (u/pydict "schema" "amu.js-browser-target.v1" "status" "PASS_JS_BROWSER_TARGET" "browser" version "seconds" seconds
                               "fuel" w/fuel "compiler" (u/pydict "path" (str F) "sha256" (w/sha256 F))
                               "cases" (python/list @results) "probes" (python/list @probe-results)
                               "identicalToWasm32Browser" (count @results) "floatRefusals" (python/list @floats)
                               "modules" (u/pydict-from (for [stem @modules] [stem (w/sha256 (pathlib/Path work (str stem ".mjs")))]))
                               "forbiddenScan" (u/pydict "names" (python/list forbidden) "negativeControl" "fetch refused")
                               "nodeOrNbb" false)]
          (.write_text (pathlib/Path out "js-browser.json") (u/json-dump report))
          (println "PASS_JS_BROWSER_TARGET" (count @results) "cases identical to wasm32-browser," (count @probe-results) "probes,"
                   (count @floats) "float refusals"))))))

(defn -main [& args]
  (run (or (u/opt args "--compiler") (sys/exit "--compiler is required"))
       (or (u/opt args "--output") (sys/exit "--output is required"))
       (u/opt args "--browser")))

(when (some #(or (= % "check-js-browser.cljc") (str/ends-with? % "/check-js-browser.cljc")) sys/argv)
  (apply -main *command-line-args*))
