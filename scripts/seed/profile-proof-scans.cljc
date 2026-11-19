;; Diagnostic marker compiler; native verdict authority is always false. Stages existing source, invokes the
;; admitted producer, and timestamps stderr. It neither emits a native format nor supplies a qualification
;; verdict. Ported from profile-proof-scans.py (Basilisp, JUN-974).
;; Run (Linux): basilisp run -p scripts/seed scripts/seed/profile-proof-scans.cljc -- --output DIR [--seconds N]
;;   [--baseline-revision SHA] [--from-sir N] [--ccf-only]
(ns profile-proof-scans
  (:require [basilisp.string :as str]
            [clojure.set :as set]
            [gate-util :as u])
  (:import hashlib json operator pathlib platform re struct subprocess sys threading time))

(def root u/root)
(defn rp [rel] (pathlib/Path root rel))
(defn g [m k] (operator/getitem m k))
(defn pin [p] (let [b (.read_bytes (pathlib/Path p))] (u/pydict "bytes" (python/len b) "sha256" (u/sha256-hex b))))

(def lit-functions ["gn-small-label", "gn-op-fn", "gn-op-call", "qi-admit", "pi-admit", "ti-admit", "rp-admit", "rc-admit", "gn-call-wrapper", "gn-clamp", "gn-scalar-mask", "gn-affine-reader", "mr-reader", "di-admit", "tc-admit", "tb-admit", "aw-admit", "gn-mask-writer", "gn-chain-mode", "gn-chain-target", "gp-shape", "gn-ins", "gn-small-tail", "gn-small-end", "jt-return", "jdag-owner", "gn-op-label", "gn-op-fuel", "gn-chain-step", "srloop-entry", "btg-entry", "ts-entry", "jssa-entry", "sls-entry", "brc-entry", "snf-entry"])
(def lit-ccf ["gn-op-cmp", "ccf-admit", "ccf-code", "ccf-fixes", "ccf-labels", "ccf-functions", "ccf-label-source", "ccf-owner", "ccf-end", "bd-edges"])
(def lit-sir-extra ["dve-ins", "dve-original-ins", "gn-ins-quiet", "ocb-post", "vi-step", "gn-op-rt", "gn-op-bin"])
(def lit-alloc-old "(mem-alloc M0 (+ gn-a-lp MM-LABEL-CAP 91))")
(def lit-alloc-new "(mem-alloc M0 (+ gn-a-lp MM-LABEL-CAP 93))")
(def lit-ins-old "(let [M1 (gn-ins M i (gn-op M i))")
(def lit-ins-new "(let [current (gn-gs M (+ gn-g-open 92) i) M1 (gn-ins current i (gn-op M i))")
(def lit-marker "(let [module-info (if (= i 1) (io-err (string-concat \"MODULE \" (string-concat (mem-u2dec (vector-at M MM-SIR-N)) (string-concat \" INDEX \" (string-concat (mem-u2dec (glx-base M)) \"\\n\"))))) 0) M1 (gn-ins M i (gn-op M i))")

(defn machine-word [path] (first (struct/unpack_from "<H" path 18)))

(defn run [out seconds revision from-sir ccf-only]
  (u/chk (and (= (platform/system) "Linux") (contains? #{"x86_64" "aarch64"} (platform/machine))) "Linux x86_64/aarch64 required")
  (.mkdir out ** :parents true :exist_ok false)
  (let [x86? (= (platform/machine) "x86_64")
        target (if x86? "x86_64-linux" "aarch64-linux")
        producer (if x86? (rp "bin/amu-linux-x86_64") (rp "seed/bootstrap/aarch64-linux-static-root.elf"))
        expected-machine (if x86? 62 183)
        _ (u/chk (= (machine-word (.read_bytes (pathlib/Path "/proc/self/exe"))) expected-machine) "self machine")
        _ (u/chk (= (machine-word (.read_bytes producer)) expected-machine) "producer machine")
        read- (fn [path]
                (if-not revision
                  (.read_bytes (rp path))
                  (.-stdout (subprocess/run (python/list ["git" "show" (str revision ":" path)]) ** :cwd root :check true :capture_output true))))
        lines-of (fn [path] (vec (filter #(and (seq %) (not (.startswith % "#"))) (.splitlines (.decode (read- path))))))
        paths (lines-of "seed/CORE-STATIC-MANIFEST")
        source (.join (u/bytes-of) (python/list (map #(operator/add (read- %) (u/bytes-of 10)) paths)))
        text (atom (.decode source))
        functions (atom (vec (if ccf-only lit-ccf lit-functions)))]
    (when (pos? from-sir)
      (u/chk (not revision) "late probe currently uses the candidate snapshot")
      (let [t @text
            quiet (subs t (.index t "(defn- gn-ins-quiet ") (.index t ";; every instruction from i"))
            entries (sort (set/difference (set (map #(.group % 1) (python/list (re/finditer "\\(([\\w-]+-entry) " quiet)))) (set @functions)))]
        (swap! functions into entries)
        (swap! functions into lit-sir-extra)
        (swap! text #(.replace % lit-alloc-old lit-alloc-new))
        (swap! text #(.replace % lit-ins-old lit-ins-new))))
    (let [bindings (u/pydict-from (for [p paths] [p (u/pydict "bytes" (python/len (read- p)) "sha256" (u/sha256-hex (read- p)))]))]
      (doseq [name @functions]
        (let [t @text
              match (re/search (str "\\(defn- " (re/escape name) " \\[([^]]*)\\] :(i64|bool|vector-i64)") t)]
          (u/chk (some? match) name)
          (let [start (.start match)
                end (.find t "\n(def" (.end match))
                _ (u/chk (> end start) name)
                original (subs t start end)
                args (.group match 1)
                names (vec (map #(.group % 1) (python/list (re/finditer "([\\w-]+) :[\\w-]+" args))))
                inner (str "prof-original-" name)
                body (.replace (.replace original (str "(" name " ") (str "(" inner " ")) (str "(defn- " name " ") (str "(defn- " inner " ") 1)
                active (if (zero? from-sir) "true" (str "(>= (gn-g " (first names) " (+ gn-g-open 92)) " from-sir ")"))
                wrapper (str "(defn- " name " [" args "] :" (.group match 2) " (let [active " active " b (if active (io-err \"B " name "\\n\") 0) result (" inner " "
                             (str/join " " names) ") e (if active (io-err \"E " name "\\n\") 0)] result))\n")]
            (reset! text (str (subs t 0 start) body "\n" wrapper (subs t end))))))
      (when-not revision
        (swap! text #(.replace % lit-ins-old lit-marker 1)))
      (let [unit (pathlib/Path out "probe.kotoba")
            _ (.write_text unit @text)
            corepaths (lines-of "seed/MANIFEST")
            core (pathlib/Path out "core.kotoba")
            _ (.write_bytes core (.join (u/bytes-of) (python/list (map #(operator/add (read- %) (u/bytes-of 10)) corepaths))))
            lock (pathlib/Path out "core.ksl")
            _ (.write_text lock (str "KSL1\nentry " core "\nfile " (g (pin core) "sha256") " " core "\n"))
            env (u/pydict "PATH" "/nonexistent" "KEXE_STACK_BYTES" "8388608" "KEXE_CAP_RESOURCES_35" (str out))
            image (pathlib/Path out "probe.elf")
            r (subprocess/run (python/list [(str producer) "compile" (str unit) "--target" target "--output" (str image) "--format" "static"])
                              ** :env env :capture_output true :timeout 900)]
        (.write_bytes (pathlib/Path out "build.stdout") (.-stdout r))
        (.write_bytes (pathlib/Path out "build.stderr") (.-stderr r))
        (u/chk (and (= (.-returncode r) 0) (zero? (python/len (.-stderr r)))) (str [(.-returncode r) (.-stderr r)]))
        (.chmod image 0755)
        (let [report (u/pydict "schema" "amu.proof-scan-diagnostic.v1" "nativeVerdictAuthority" false "qualificationReplacement" false
                               "host" (python/list [(platform/system) (platform/machine) (platform/release)])
                               "sourceBindings" bindings "source" (pin core) "producer" (pin producer) "instrumented" (pin unit) "compiler" (pin image)
                               "status" "RUNNING" "events" 0 "totals" (python/dict) "stack" (python/list))
              write-report! (fn [] (.write_text (pathlib/Path out "observations.json") (u/json-dump report)))]
          (write-report!)
          (let [argv [(str image) "compile" (str core) "--target" "aarch64-macos" "--output" (str (pathlib/Path out "core.kseed"))
                      "--source-lock" (str lock) "--source-lock-sha256" (g (pin lock) "sha256")]
                start (time/monotonic)
                process (subprocess/Popen (python/list argv) ** :env env :stdout (.open (pathlib/Path out "compile.stdout") "wb") :stderr subprocess/PIPE)
                stop (threading/Timer seconds (.-terminate process))
                _ (.start stop)
                stack (python/list)            ; [name began] pairs, hot-loop state kept in plain Python values
                totals (python/dict)
                total-of (fn [name]
                           (or (.get totals name)
                               (let [d (python/dict ** :exclusiveSeconds 0 :inclusiveSeconds 0 :calls 0)] (operator/setitem totals name d) d)))
                stderr (.-stderr process)
                monotonic time/monotonic
                dumps json/dumps]
            (with-open [raw (.open (pathlib/Path out "events.jsonl") "w")]
              (loop [last- start events 0]
                (let [data (.readline stderr)]
                  (if (operator/eq (python/len data) 0)
                    (operator/setitem report "events" events)
                    (let [now (monotonic)
                          line (.strip (.decode data))
                          top (when (operator/truth stack) (operator/getitem stack -1))]
                      (.write raw (operator/add (operator/add (operator/add "[" (python/repr (operator/sub now start))) (operator/add ", " (dumps line))) "]\n"))
                      (when top
                        (let [d (total-of (operator/getitem top 0))]
                          (operator/setitem d "exclusiveSeconds" (operator/add (operator/getitem d "exclusiveSeconds") (operator/sub now last-)))))
                      (cond
                        (.startswith line "B ")
                        (let [name (operator/getitem line (python/slice 2 nil))]
                          (.append stack (python/tuple [name now]))
                          (let [d (total-of name)] (operator/setitem d "calls" (operator/add (operator/getitem d "calls") 1))))
                        (.startswith line "E ")
                        (let [name (operator/getitem line (python/slice 2 nil))]
                          (u/chk (and top (operator/eq (operator/getitem top 0) name)) (str [line (operator/getitem stack (python/slice -5 nil))]))
                          (let [began (operator/getitem (.pop stack) 1)
                                d (operator/getitem totals name)]
                            (operator/setitem d "inclusiveSeconds" (operator/add (operator/getitem d "inclusiveSeconds") (operator/sub now began))))))
                      (let [events (operator/add events 1)]
                        (when (operator/eq (operator/mod events 256) 0)
                          (operator/setitem report "events" events)
                          (.update report (u/pydict "seconds" (operator/sub now start) "totals" totals "stack" (python/list (map first stack))))
                          (write-report!))
                        (recur now events)))))))
            (let [code (.wait process)]
              (.cancel stop)
              (.update report (u/pydict "exit" code "seconds" (- (time/monotonic) start) "totals" totals "stack" (python/list (map first stack))
                                        "status" (if (zero? code) "COMPLETED_DIAGNOSTIC" "RIGHT_CENSORED_DIAGNOSTIC")
                                        "artifact" (when (.exists (pathlib/Path out "core.kseed")) (pin (pathlib/Path out "core.kseed")))))
              (write-report!)
              (println (json/dumps report ** :indent 2))
              (.flush sys/stdout))))))))

(defn -main [& args]
  (run (.resolve (pathlib/Path (or (u/opt args "--output") (sys/exit "--output is required"))))
       (python/int (or (u/opt args "--seconds") "240"))
       (u/opt args "--baseline-revision")
       (python/int (or (u/opt args "--from-sir") "0"))
       (boolean (some #{"--ccf-only"} args))))

(when (some #(or (= % "profile-proof-scans.cljc") (str/ends-with? % "/profile-proof-scans.cljc")) sys/argv)
  (apply -main *command-line-args*))
