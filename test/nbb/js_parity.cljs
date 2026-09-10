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
     rather than pass;
  5. the committed JVM goldens under `test/fixtures/js-parity/` (todo-app:
     typed values + `:document`; consumer: a `--source-path` linked project;
     capability-fuel: `--fuel 4096`) are reproduced byte for byte, and their
     manifest / provenance sidecars are equal to the JVM's as EDN values --
     the first differing key is named when they are not.
  Run from the repo root: `npm run test-nbb-js`. Last line `SCANNED <n>
  failed <k>`; SCANNED 0 is exit 2."
  (:require ["node:child_process" :as cp]
            ["node:crypto" :as crypto]
            ["node:fs" :as fs]
            ["node:os" :as os]
            ["node:path" :as path]
            [cljs.reader :as reader]
            [kotoba.lang.text :as str]))

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

;; 5. committed JVM goldens under test/fixtures/js-parity/ (README.md there
;;    records the exact JVM command and the kotoba-script pin per golden).
;;    For each: the nbb route with the same flags must reproduce the `.mjs`
;;    byte for byte, and its manifest / provenance sidecars must equal the
;;    JVM's AS EDN VALUES (key order in the text is not a claim; see the
;;    js-cli docstring). The three cover what route-decide does not: typed
;;    values + `:document` (todo-app), a `--source-path` linked project
;;    (consumer -> parity.util), and a `--fuel` override (4096) on a
;;    capability-bearing module.
(def golden-dir (.join path root "test" "fixtures" "js-parity"))

(def goldens
  [{:name "todo-app"
    :source "examples/todo-app.kotoba"
    :flags []}
   {:name "consumer"
    :source "test/fixtures/js-parity/consumer.kotoba"
    ;; `--unpinned` because the JVM route refuses a path-resolved project
    ;; without it (ADR-2608580000 D5, `:compile/unpinned-inputs`); the nbb
    ;; route accepts the flag and emits the same bytes with or without it
    ;; (measured 2026-09-06), so the golden's flags are the JVM's.
    :flags ["--source-path" "test/fixtures/js-parity/lib" "--unpinned"]}
   {:name "capability-fuel"
    :source "examples/capability.kotoba"
    :flags ["--policy" "examples/capability-policy.edn" "--fuel" "4096"]
    :fuel 4096}])

(defn- first-diff
  "The first path at which two EDN values differ, as {:path :nbb :jvm}, or
  nil when they are equal. Maps descend key by key (a key present on one side
  only is reported at that key), equal-length sequences index by index;
  anything else is reported where it is."
  [a b at]
  (cond
    (= a b) nil
    (and (map? a) (map? b))
    (some (fn [k] (first-diff (get a k ::absent) (get b k ::absent) (conj at k)))
          (distinct (concat (keys a) (keys b))))
    (and (sequential? a) (sequential? b) (= (count a) (count b)))
    (some (fn [[i x y]] (first-diff x y (conj at i))) (map vector (range) a b))
    :else {:path at :nbb a :jvm b}))

(defn- read-edn [file] (reader/read-string (.readFileSync fs file "utf8")))

(defn- first-byte-diff [a b]
  (or (some (fn [i] (when (not= (.charAt a i) (.charAt b i)) i))
            (range (min (count a) (count b))))
      (min (count a) (count b))))

(doseq [{:keys [name source flags fuel]} goldens]
  (let [golden (.join path golden-dir (str name ".mjs"))
        missing (remove #(.existsSync fs %) [golden (str golden ".manifest.edn") (str golden ".provenance.edn")])
        out (.join path tmp (str name ".mjs"))
        r (when (empty? missing)
            (apply amu! "compile" source "--target" "js" "--jvm-free" "--output" out flags))]
    (swap! scanned inc)
    (cond
      ;; A golden that is not there is a FAIL with a name, not an uncaught
      ;; ENOENT that ends the run before the SCANNED line.
      (seq missing)
      (fail! (str name " golden missing") (str/join ", " missing))

      (not= 0 (:status r))
      (fail! (str name " compile (jvm-free)") (str (:err r) (:out r)))

      :else
      (let [nbb-bytes (.readFileSync fs out "utf8")
            jvm-bytes (.readFileSync fs golden "utf8")]
        (if (= nbb-bytes jvm-bytes)
          (ok! (str name ".mjs: nbb route == committed JVM golden (" (count nbb-bytes) " bytes)"))
          (fail! (str name ".mjs parity")
                 (str "first difference at byte " (first-byte-diff nbb-bytes jvm-bytes)
                      ", sizes nbb=" (count nbb-bytes) " jvm=" (count jvm-bytes))))
        (doseq [sidecar [".manifest.edn" ".provenance.edn"]]
          (swap! scanned inc)
          (let [nbb-value (read-edn (str out sidecar))
                jvm-value (read-edn (str golden sidecar))]
            (if-let [d (first-diff nbb-value jvm-value [])]
              (fail! (str name sidecar " as EDN")
                     (str "first differing key " (pr-str (:path d))
                          ": nbb=" (pr-str (:nbb d)) " jvm=" (pr-str (:jvm d))))
              (ok! (str name sidecar ": nbb route == JVM golden as an EDN value")))))
        (when fuel
          (swap! scanned inc)
          (let [needle (str "let fuel=" fuel ";")]
            (if (str/includes? nbb-bytes needle)
              (ok! (str name ".mjs carries `" needle "` (the --fuel override reached the emitter)"))
              (fail! (str name " --fuel") (str "module does not contain " (pr-str needle))))))))))

(.rmSync fs tmp #js {:recursive true :force true})
(println (str "SCANNED " @scanned " failed " (count @failures)))
(.exit js/process (cond (zero? @scanned) 2 (seq @failures) 1 :else 0))
