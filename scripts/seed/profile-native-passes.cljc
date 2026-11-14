;; Native pass/proof diagnostics for the Co-Scientist experiment loop. Only stage source-marker edits, invoke an
;; admitted native producer and observe processes. The instrumented compiler is never an adopted compiler or a
;; native verdict authority. Its emitted workload must match an independent frozen artifact; marker timings are
;; for hypothesis selection, not speedup claims. Ported from profile-native-passes.py (Basilisp, JUN-974).
;; Run (Linux): basilisp run -p scripts/seed scripts/seed/profile-native-passes.cljc -- --output DIR
;;   [--closure core|full] [--workload core|label-x86] [--detail passes|proofs] [--seconds N] [--workload-file F]
(ns profile-native-passes
  (:require [basilisp.string :as str]
            [gate-util :as u])
  (:import hashlib json operator os pathlib platform re struct subprocess sys threading time))

(def root u/root)
(defn rp [rel] (pathlib/Path root rel))
(defn g [m k] (operator/getitem m k))
(defn pin [p] (let [raw (.read_bytes (pathlib/Path p))] (u/pydict "bytes" (python/len raw) "sha256" (u/sha256-hex raw))))

(def passes ["lx-run" "rd-run" "nm-run" "ck-run-h" "lw-run" "gn-run" "gn-loop" "ly-run" "out-build"])
(def x86-passes ["xs-build" "xg-code" "xr-pool"])
(def proofs ["gn-op-fn" "gn-op-call" "qi-admit" "pi-admit" "ti-admit" "rp-admit" "rc-admit"
             "gn-call-wrapper" "gn-clamp" "gn-scalar-mask" "gn-affine-reader" "mr-reader" "di-admit"
             "tc-admit" "tb-admit" "aw-admit" "gn-mask-writer" "gn-chain-mode" "gn-chain-target"
             "gp-shape" "gn-small-label" "gn-small-tail" "gn-small-end" "jdag-owner" "ccf-admit"
             "ccf-code" "ccf-fixes" "ccf-labels" "ccf-functions" "ccf-label-source" "ccf-owner" "ccf-end"])
(def input-revision "4abac3fd612de050fd7f7a4635deb80ca9a0cb73")   ; immutable previously qualified workload
(def workloads {"core" {:source "026d87a058f4f8b7006e2f09ea26d3713633cf3b4585329d818caab1280bc79d"
                        :artifact "6ad407c211c16efb425f4fa4761b0421e6e180211e4d6c28b8d6fb4bf35e0070"}
                "label-x86" {:source "daa88291555eb738df9d0dd36a1a498d69d550eff89f97931318c20627fb5a8b"
                             :artifact "378fd3cd99fcd9951654612e2df4e2b055d00bf6c068c1b4eeec325325712591"}})

(defn manifest [path read-]
  (vec (filter #(and (seq %) (not (.startswith % "#"))) (.splitlines (.decode (read- path))))))

(defn instrument [text name]
  (let [pattern (str "^\\(defn- " (re/escape name) " \\[([^]]*)\\] :(i64|bool|vector-i64)")
        matches (python/list (re/finditer pattern text re/M))
        _ (u/chk (= (python/len matches) 1) (str [name "source anchor drift"]))
        match (operator/getitem matches 0)
        start (.start match)
        n (python/len text)
        end (loop [i start depth 0 quoted false escaped false comment false]
              (when (< i n)
                (let [c (operator/getitem text i)]
                  (cond
                    comment (recur (inc i) depth quoted escaped (not= c "\n"))
                    quoted (cond escaped (recur (inc i) depth true false false)
                                 (= c "\\") (recur (inc i) depth true true false)
                                 (= c "\"") (recur (inc i) depth false false false)
                                 :else (recur (inc i) depth true false false))
                    (= c ";") (recur (inc i) depth false false true)
                    (= c "\"") (recur (inc i) depth true false false)
                    (= c "(") (recur (inc i) (inc depth) false false false)
                    (= c ")") (if (= (dec depth) 0) (inc i) (recur (inc i) (dec depth) false false false))
                    :else (recur (inc i) depth false false false)))))
        _ (u/chk (some? end) name)
        args (.group match 1)
        names (vec (map #(.group % 1) (python/list (re/finditer "([\\w-]+) :(?:vector-i64|string|i64|bool)" args))))
        _ (u/chk (= (* (count names) 2) (python/len (.split args))) (str [name args]))
        inner (str "diagnostic-original-" name)
        body (-> (.replace (subs text start end) (str "(defn- " name " ") (str "(defn- " inner " ") 1)
                 (.replace (str "(" name " ") (str "(" inner " ")))
        wrapper (str "(defn- " name " [" args "] :" (.group match 2) "\n"
                     "  (let [begin (io-err \"B " name "\\n\")\n"
                     "        result (" inner " " (str/join " " names) ")\n"
                     "        end (io-err \"E " name "\\n\")] result))\n")]
    (str (subs text 0 start) body "\n" wrapper (subs text end))))

(defn run [out closure workload detail seconds workload-file]
  (u/chk (and (= (platform/system) "Linux") (contains? #{"aarch64" "x86_64"} (platform/machine))) "Linux aarch64/x86_64 required")
  (let [aarch? (= (platform/machine) "aarch64")
        machine (if aarch? 183 62)
        word (fn [b] (first (struct/unpack_from "<H" b 18)))
        _ (u/chk (= (word (.read_bytes (pathlib/Path "/proc/self/exe"))) machine) "self machine")
        producer (rp (if aarch? "seed/bootstrap/aarch64-linux-static-root.elf" "bin/amu-linux-x86_64"))
        _ (u/chk (= (word (.read_bytes producer)) machine) "producer machine")
        _ (u/chk (or (= closure "full") (= workload "core")) "x86 workload requires the full compiler")
        _ (.mkdir out ** :parents true :exist_ok false)
        read- (fn [p] (.read_bytes (rp p)))
        frozen (fn [path] (.-stdout (subprocess/run (python/list ["git" "show" (str input-revision ":" path)]) ** :cwd root :capture_output true :check true)))
        paths (manifest (if (= closure "full") "seed/FULL-MANIFEST" "seed/CORE-STATIC-MANIFEST") read-)
        original (.decode (.join (u/bytes-of) (python/list (map #(operator/add (read- %) (u/bytes-of 10)) paths))))
        functions (concat passes (when (= closure "full") x86-passes) (when (= detail "proofs") proofs))
        text (reduce instrument original functions)
        source (pathlib/Path out "probe.kotoba")
        _ (.write_text source text)
        raw (cond workload-file (.read_bytes (pathlib/Path workload-file))
                  (= workload "core") (.join (u/bytes-of) (python/list (map #(operator/add (frozen %) (u/bytes-of 10)) (manifest "seed/MANIFEST" frozen))))
                  :else (operator/add (.join (u/bytes-of) (python/list (map #(operator/add (frozen %) (u/bytes-of 10)) (butlast (manifest "seed/CORE-STATIC-MANIFEST" frozen)))))
                                      (frozen "seed/tests/native-label-index.kotoba")))
        src (pathlib/Path out "workload.kotoba")
        _ (.write_bytes src raw)
        expected (get workloads workload)
        _ (u/chk (= (g (pin src) "sha256") (:source expected)) "frozen workload drift")
        target (if aarch? "aarch64-linux" "x86_64-linux")
        image (pathlib/Path out "probe.elf")
        env (u/pydict "PATH" "/nonexistent" "KEXE_STACK_BYTES" "8388608" "KEXE_CAP_RESOURCES_35" (str out))]
    (println (json/dumps (u/pydict "phase" "BUILDING_PROBE" "closure" closure "workload" workload "detail" detail "source" (pin source) "nativeVerdictAuthority" false)))
    (.flush sys/stdout)
    (let [start (time/monotonic)
          build (subprocess/run (python/list [(str producer) "compile" (str source) "--target" target "--output" (str image) "--format" "static"])
                                ** :cwd out :env env :capture_output true :timeout 900)]
      (.write_bytes (pathlib/Path out "build.stdout") (.-stdout build))
      (.write_bytes (pathlib/Path out "build.stderr") (.-stderr build))
      (u/chk (and (= (.-returncode build) 0) (zero? (python/len (.-stderr build)))) (str [(.-returncode build) (.-stderr build)]))
      (.chmod image 0755)
      (println (json/dumps (u/pydict "phase" "RUNNING_DIAGNOSTIC" "compiler" (pin image) "source" (pin src))))
      (.flush sys/stdout)
      (let [report (u/pydict "schema" "amu.native-pass-diagnostic.v1" "nativeVerdictAuthority" false "qualificationReplacement" false "performanceQualified" false
                             "host" (python/list [(platform/system) (platform/machine) (platform/release)]) "loadStart" (os/getloadavg)
                             "closure" closure "detail" detail "workload" workload "workloadRevision" input-revision
                             "sourceBindings" (u/pydict-from (for [p paths] [p (pin (rp p))])) "source" (pin src)
                             "producer" (pin producer) "instrumentedSource" (pin source) "compiler" (pin image)
                             "buildSeconds" (- (time/monotonic) start) "status" "RUNNING" "events" 0 "totals" (python/dict) "stack" (python/list))
            core? (= workload "core")
            output (pathlib/Path out (if core? "workload.kseed" "workload.elf"))
            lock (pathlib/Path out "workload.ksl")
            argv (vec (concat [(str image) "compile" (str src) "--target" (if core? "aarch64-macos" "x86_64-linux") "--output" (str output)]
                              (if core?
                                (do (.write_text lock (str "KSL1\nentry " src "\nfile " (g (pin src) "sha256") " " src "\n"))
                                    ["--source-lock" (str lock) "--source-lock-sha256" (g (pin lock) "sha256")])
                                ["--format" "static"])))
            start (time/monotonic)
            write-report! (fn [] (.write_text (pathlib/Path out "observations.json") (u/json-dump report)))
            stack (python/list)
            totals (python/dict)
            errors (python/list)
            passes? (= detail "passes")
            code (with-open [stdout (.open (pathlib/Path out "compile.stdout") "wb")]
                   (let [proc (subprocess/Popen (python/list argv) ** :cwd out :env env :stdout stdout :stderr subprocess/PIPE)
                         timer (threading/Timer seconds (.-terminate proc))
                         monotonic time/monotonic
                         dumps json/dumps
                         stderr (.-stderr proc)]
                     (.start timer)
                     (with-open [raw-events (.open (pathlib/Path out "events.jsonl") "w")]
                       (loop [last- start events 0]
                         (let [data (.readline stderr)]
                           (when-not (operator/eq (python/len data) 0)
                             (let [now (monotonic)
                                   line (.strip (.decode data))
                                   top (when (operator/truth stack) (operator/getitem stack -1))]
                               (.write raw-events (operator/add (operator/add (operator/add "[" (python/repr (operator/sub now start))) (operator/add ", " (dumps line))) "]\n"))
                               (when top
                                 (let [d (operator/getitem totals (operator/getitem top 0))]
                                   (operator/setitem d "exclusiveSeconds" (operator/add (operator/getitem d "exclusiveSeconds") (operator/sub now last-)))))
                               (cond
                                 (.startswith line "B ")
                                 (let [name (operator/getitem line (python/slice 2 nil))]
                                   (.append stack (python/tuple [name now]))
                                   (let [row (or (.get totals name)
                                                 (let [d (python/dict ** :exclusiveSeconds 0 :inclusiveSeconds 0 :calls 0)] (operator/setitem totals name d) d))]
                                     (operator/setitem row "calls" (operator/add (operator/getitem row "calls") 1))))
                                 (.startswith line "E ")
                                 (let [name (operator/getitem line (python/slice 2 nil))]
                                   (u/chk (and top (operator/eq (operator/getitem top 0) name)) (str [name (operator/getitem stack (python/slice -5 nil))]))
                                   (let [began (operator/getitem (.pop stack) 1)
                                         d (operator/getitem totals name)]
                                     (operator/setitem d "inclusiveSeconds" (operator/add (operator/getitem d "inclusiveSeconds") (operator/sub now began)))))
                                 :else (.append errors line))
                               (let [events (operator/add events 1)]
                                 (operator/setitem report "events" events)
                                 (.update report (u/pydict "seconds" (operator/sub now start) "totals" totals "stack" (python/list (map first stack))))
                                 (when (or passes? (operator/eq (operator/mod events 256) 0)) (write-report!))
                                 (recur now events)))))))
                     (let [c (.wait proc)] (.cancel timer) c)))
            artifact (when (.exists output) (pin output))]
        (.update report (u/pydict "exit" code "seconds" (- (time/monotonic) start) "totals" totals "stack" (python/list (map first stack))
                                  "openSpans" (python/list (for [[n began] stack] (u/pydict "name" n "seconds" (- (time/monotonic) began))))
                                  "errors" errors "artifact" artifact "loadEnd" (os/getloadavg)
                                  "outputParity" (boolean (and artifact (= (g artifact "sha256") (:artifact expected))))
                                  "status" (if (zero? code) "COMPLETED_DIAGNOSTIC" "INCOMPLETE_DIAGNOSTIC")))
        (write-report!)
        (println (json/dumps (u/pydict-from (for [k ["status" "seconds" "outputParity" "totals" "openSpans"]] [k (g report k)]))))
        (.flush sys/stdout)
        (u/chk (and (zero? code) (zero? (python/len errors)) (g report "outputParity") (zero? (python/len stack)))
               "incomplete diagnostic or output differs from baseline")))))

(defn -main [& args]
  (let [closure (or (u/opt args "--closure") "full")
        workload (or (u/opt args "--workload") "core")
        detail (or (u/opt args "--detail") "passes")
        seconds (python/int (or (u/opt args "--seconds") "600"))]
    (when-not (#{"core" "full"} closure) (sys/exit "--closure must be core or full"))
    (when-not (contains? workloads workload) (sys/exit "--workload must be core or label-x86"))
    (when-not (#{"passes" "proofs"} detail) (sys/exit "--detail must be passes or proofs"))
    (u/chk (<= 1 seconds 900) "--seconds must be in 1..900")
    (run (.resolve (pathlib/Path (or (u/opt args "--output") (sys/exit "--output is required"))))
         closure workload detail seconds
         (when-let [w (u/opt args "--workload-file")] (.resolve (pathlib/Path w))))))

(when (some #(or (= % "profile-native-passes.cljc") (str/ends-with? % "/profile-native-passes.cljc")) sys/argv)
  (apply -main *command-line-args*))
