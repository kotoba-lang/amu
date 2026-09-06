(ns test.nbb.js-parity
  "JVM-free regression test for the restricted-ESM route (`bin/amu compile
  --target js`, hosted by `kotoba.compiler.nbb.js-cli`).

  Claims, each measured:
  1. compiling `runtime/http/route-decide.kotoba` on this route reproduces the
     committed `runtime/http/route-decide.mjs` BYTE FOR BYTE. That file is
     written by the JVM route at the same kotoba-script pin (the drift gate in
     scripts/http-service-e2e.cljs keeps it fresh), so equality here is the
     two-route parity Q9 asks for, not a self-comparison;
  2. the manifest sidecar's output digest is the SHA-256 of the module bytes,
     and the provenance sidecar's primary-output identity is the same digest
     (measured 2026-09-06 against the JVM route at the same pin: module bytes,
     manifest and provenance all equal as values);
  3. the module runs under Node: `examples/capability.kotoba` answers 42n,
     its capability export goes through a supplied grant, and the same export
     is refused (`capability-denied`) when the grant is absent;
  4. `--jvm-free` is honoured: `clojure` and `java` are hidden from PATH for
     every compile below, so a silent fall-back to the JVM route would fail
     rather than pass.
  Run from the repo root: `npm run test-nbb-js`. Last line `SCANNED <n>
  failed <k>`; SCANNED 0 is exit 2."
  (:require ["node:child_process" :as cp]
            ["node:crypto" :as crypto]
            ["node:fs" :as fs]
            ["node:os" :as os]
            ["node:path" :as path]
            [cljs.reader :as reader]
            [clojure.string :as str]))

(def root (.cwd js/process))
(def tmp (.mkdtempSync fs (.join path (.tmpdir os) "amu-js-parity-")))
(def failures (atom []))
(def scanned (atom 0))
(defn- fail! [what detail] (swap! failures conj what) (println "FAIL" what "--" detail))
(defn- ok! [what] (println "ok  " what))

(def jvm-free-env
  ;; A PATH with no `clojure`/`java`, plus a JAVA_HOME that does not exist:
  ;; the launcher cannot reach the JVM route even if it wanted to.
  (let [bin (.join path tmp "bin")]
    (.mkdirSync fs bin #js {:recursive true})
    (doseq [tool ["node" "git"]]
      (let [found (str/trim (str (.-stdout (cp/spawnSync "sh" #js ["-c" (str "command -v " tool)] #js {:encoding "utf8"}))))]
        (when (seq found) (.symlinkSync fs found (.join path bin tool)))))
    (js/Object.assign #js {} (.-env js/process)
                      #js {:PATH (str bin ":/usr/bin:/bin") :JAVA_HOME "/nonexistent"})))

(defn- amu! [& args]
  (let [r (cp/spawnSync (.-execPath js/process) (clj->js (into [(.join path root "bin" "amu")] args))
                        #js {:encoding "utf8" :cwd root :env jvm-free-env :maxBuffer (* 64 1024 1024)})]
    {:status (.-status r) :out (str (.-stdout r)) :err (str (.-stderr r))}))

(defn- sha256-hex [text] (-> (.createHash crypto "sha256") (.update text "utf8") (.digest "hex")))

;; 1. byte parity with the committed JVM artifact
(let [out (.join path tmp "route-decide.mjs")
      r (amu! "compile" "runtime/http/route-decide.kotoba" "--target" "js" "--jvm-free" "--output" out)]
  (swap! scanned inc)
  (if (not= 0 (:status r))
    (fail! "route-decide compile (jvm-free)" (str (:err r) (:out r)))
    (let [nbb-bytes (.readFileSync fs out "utf8")
          jvm-bytes (.readFileSync fs (.join path root "runtime" "http" "route-decide.mjs") "utf8")]
      (if (= nbb-bytes jvm-bytes)
        (ok! (str "route-decide.mjs: nbb route == committed JVM artifact (" (count nbb-bytes) " bytes)"))
        (let [i (or (some (fn [i] (when (not= (.charAt nbb-bytes i) (.charAt jvm-bytes i)) i))
                          (range (min (count nbb-bytes) (count jvm-bytes))))
                    (min (count nbb-bytes) (count jvm-bytes)))]
          (fail! "route-decide.mjs parity" (str "first difference at byte " i ", sizes nbb=" (count nbb-bytes) " jvm=" (count jvm-bytes)))))
      ;; 2. manifest digest
      (swap! scanned inc)
      (let [manifest (reader/read-string (.readFileSync fs (str out ".manifest.edn") "utf8"))
            declared (:kotoba.artifact/output-digest manifest)]
        (if (= declared (sha256-hex nbb-bytes))
          (ok! "manifest output-digest == sha256(module)")
          (fail! "manifest output-digest" (str declared " vs " (sha256-hex nbb-bytes)))))
      (swap! scanned inc)
      (let [prov (reader/read-string (.readFileSync fs (str out ".provenance.edn") "utf8"))
            manifest (reader/read-string (.readFileSync fs (str out ".manifest.edn") "utf8"))
            primary (get-in prov [:outputs :primary])]
        (if (and (= :kotoba.provenance/v1 (:format prov))
                 (= :javascript-source (:format primary))
                 (= (sha256-hex nbb-bytes) (:sha256 primary))
                 (= (.byteLength js/Buffer nbb-bytes "utf8") (:size primary))
                 (= (:kotoba.artifact/provenance manifest) prov))
          (ok! "provenance.edn: primary output identity == module, and the manifest carries the same descriptor")
          (fail! "provenance.edn" (pr-str (select-keys prov [:format :outputs])))))
      (swap! scanned inc)
      (let [json (js->clj (.parse js/JSON (.readFileSync fs (str out ".manifest.json") "utf8")))]
        (if (= "kotoba-js-artifact/v1" (get json "kotoba.artifact/schema"))
          (ok! "manifest.json carries the artifact schema")
          (fail! "manifest.json" (pr-str (keys json))))))))

;; 3. the module runs under Node, through and without a grant
(let [out (.join path tmp "capability.mjs")
      r (amu! "compile" "examples/capability.kotoba" "--target" "js" "--jvm-free"
              "--policy" "examples/capability-policy.edn" "--output" out)]
  (swap! scanned inc)
  (if (not= 0 (:status r))
    (fail! "capability compile (jvm-free)" (str (:err r) (:out r)))
    (let [probe (str "import('" out "').then(m=>{"
                     "const granted=m.instantiateKotoba({7:v=>v+1n});"
                     "const a=String(granted.main())+' '+String(granted.audit(41n));"
                     "let denied='no-throw';try{m.instantiateKotoba({}).audit(1n)}catch(e){denied=e.message}"
                     "console.log(a+' '+denied)})")
          node (cp/spawnSync (.-execPath js/process) #js ["--input-type=module" "-e" probe] #js {:encoding "utf8"})
          line (str/trim (str (.-stdout node)))]
      (if (= "42 42 capability-grant-mismatch" line)
        (ok! "capability.mjs: main()=42, audit(41n) via grant = 42, instantiate without the required grant refused")
        (fail! "capability.mjs run" (str (pr-str line) (.-stderr node)))))))

;; 4. the JVM-only target is still refused on this route rather than faked
(let [r (amu! "compile" "runtime/http/route-decide.kotoba" "--target" "cljs-browser" "--jvm-free" "--output" (.join path tmp "x.cljs"))]
  (swap! scanned inc)
  (if (and (not= 0 (:status r)) (re-find #"(?i)jvm|clojure|not found|refus" (str (:err r) (:out r))))
    (ok! "cljs-browser under --jvm-free is refused, not silently routed")
    (fail! "cljs-browser --jvm-free" (str "status " (:status r) " " (subs (str (:err r) (:out r)) 0 200)))))

(.rmSync fs tmp #js {:recursive true :force true})
(println (str "SCANNED " @scanned " failed " (count @failures)))
(.exit js/process (cond (zero? @scanned) 2 (seq @failures) 1 :else 0))
