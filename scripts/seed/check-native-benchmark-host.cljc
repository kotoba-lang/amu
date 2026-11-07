;; Observe the closed native ARM measurement-host candidate, not a score.
;;
;; Amu builds the host and every workload. This observer stages unchanged bytes, captures all process outputs and
;; checks records; it is not native verdict or performance authority. x86 host/payload admission and built semantic
;; mutation controls remain separate mandatory work.
;; Ported from check-native-benchmark-host.py (Basilisp). valid-observation / unique-fields are in
;; native_benchmark_lib.cljc.
;; Run: basilisp run scripts/seed/check-native-benchmark-host.cljc -- (--one DIR | --complete DIR) --corpus DIR --output OUT
;;        [--arm-controls FILE] [--host-source FILE] [--full-counts] [--wall-seconds N]
(ns check-native-benchmark-host
  (:require [basilisp.string :as str]
            [embench-candidate-lib :as C]
            [gate-util :as u]
            [native-benchmark-lib :as lib]
            [native-profile :as profile])
  (:import json operator pathlib shutil subprocess sys))

(defn- elf-or-nil [x] x)

(defn main [a]
  (let [{:keys [one complete arm-controls corpus output host-source full-counts wall-seconds]} a
        root u/root
        [compiler machine _target receipt sources] (C/provenance (when one (.resolve one)) (when complete (.resolve complete)))
        _ (u/chk (or (and (= 183 machine) (nil? arm-controls)) (and (= 62 machine) arm-controls full-counts)))
        corpus (.resolve corpus)
        original-report (u/read-json (.joinpath corpus "observations.json"))
        _ (u/chk (u/deq (u/geti original-report "compiler") (C/elf compiler machine)))
        _ (u/chk (u/deq (u/geti original-report "sources") sources))
        rows (vec (u/geti original-report "workloads"))
        _ (u/chk (and (= 19 (count rows)) (= 19 (count (set (map #(u/geti % "workload") rows))))))
        _ (u/chk (every? (fn [r] (and (u/geti r "sourceUnchanged") (= 0 (u/geti (u/geti (u/geti r "calls") 0) "exit"))
                                      (seq (u/geti r "exports")) (every? #(u/geti % "valid") (u/geti r "exports"))))
                         rows))
        out (.resolve output)
        _ (.mkdir out ** :mode 0700 :parents true :exist_ok false)
        _ (.write_bytes (.joinpath out "observer.cljc") (.read_bytes (.joinpath root "scripts/seed/check-native-benchmark-host.cljc")))
        host-src (.joinpath out "host.kotoba")
        registry-src (.joinpath out "registry.kotoba")
        _ (shutil/copy2 (if host-source (.resolve host-source) (.joinpath root "seed/bench/host-arm.kotoba")) host-src)
        _ (shutil/copy2 (.joinpath root "seed/bench/registry-arm.kotoba") registry-src)
        host (.joinpath out "host.elf")
        report (u/pydict "status" "running" "compiler" (C/elf compiler machine) "receipt" (C/pin receipt)
                         "sources" sources "hostSource" (C/pin host-src) "registry" (C/pin registry-src)
                         "observer" (C/pin (.joinpath root "scripts/seed/check-native-benchmark-host.cljc"))
                         "calls" (python/list) "workloads" (python/list)
                         "performanceQualified" false "nativeVerdictAuthority" false "fullQualification" false
                         "builtSemanticMutationControls" false "mode" (if full-counts "registered" "diagnostic-one-body"))
        reference-path (.joinpath root "bench/embench/reproduce-20261015/round-sa-m104-20261015/records/round/expected-accounting-mw.json")
        _ (u/chk (= (u/geti (C/pin reference-path) "sha256") (u/geti C/data-pins "round-sa-m104-20261015/records/round/expected-accounting-mw.json")))
        references (into {} (for [row (json/loads (.read_text reference-path))] [(u/geti row "workload") row]))
        _ (u/chk (= 19 (count references)))
        _ (operator/setitem report "accountingReference" (C/pin reference-path))
        persist (fn [] (profile/atomic-json (.joinpath out "observations.json") report))
        run (fn [name argv env & {:keys [timeout] :or {timeout 300}}]
              (let [e (python/dict {"PATH" "/nonexistent"})
                    _ (doseq [[k v] (.items env)] (operator/setitem e k v))
                    [code stdout stderr]
                    (try (let [r (u/run-process argv e timeout :cwd out)] [(.-returncode r) (.-stdout r) (.-stderr r)])
                         (catch subprocess/TimeoutExpired ex
                           ["observer-timeout" (or (.-stdout ex) (u/bytes-of)) (or (.-stderr ex) (u/bytes-of))]))]
                (.write_bytes (.joinpath out (str name ".stdout")) stdout)
                (.write_bytes (.joinpath out (str name ".stderr")) stderr)
                (.append (u/geti report "calls")
                         (u/pydict "name" name "argv" (python/list (map str argv)) "exit" code
                                   "stdout" (C/pin (.joinpath out (str name ".stdout"))) "stderr" (C/pin (.joinpath out (str name ".stderr")))))
                (persist)
                (println name code (.decode (u/bslice stdout 0 180) ** :errors "replace") (.decode (u/bslice stderr 0 180) ** :errors "replace"))
                (.flush sys/stdout)
                [code stdout stderr]))
        compile-env (python/dict {"KEXE_ALLOW" "35,37,38,39" "KEXE_CAP_RESOURCES_35" (str out) "KEXE_STACK_BYTES" "8388608"})
        argv [compiler "bench-build" "aarch64-linux" host-src registry-src host "--runtime-profile" "large-vectors-v1"]
        _ (persist)
        [code stdout stderr] (run "build" argv compile-env)]
    (if (or (not (zero? code)) (u/nonempty? stderr) (not (.is_file host)))
      (do (operator/setitem report "status" "refused-host-build") (persist) 2)
      (do
        (u/chk (u/has-bytes? (.encode ":runtime-profile :large-vectors-v1") stdout))
        (.chmod host 0755)
        (operator/setitem report "host" (C/elf host 183))
        (let [refusals (python/list)
              mutated (.joinpath out "mutated-host.kotoba")
              _ (.write_bytes mutated (operator/add (.read_bytes host-src) (.encode "\n;; not the pinned source\n")))
              bad-registry (.joinpath out "mutated-registry.kotoba")
              _ (.write_bytes bad-registry (operator/add (.read_bytes registry-src) (.encode "\n;; not the pinned registry\n")))
              refused? (fn [code destination] (and (contains? #{1 2} code) (not (.exists destination))))]
          (doseq [[label args] [["wrong-host-source" ["aarch64-linux" mutated registry-src]]
                                ["wrong-registry" ["aarch64-linux" host-src bad-registry]]
                                ["unsupported-x86-host" ["x86_64-linux" host-src registry-src]]]]
            (let [destination (.joinpath out (str label ".elf"))
                  [code _ _] (run label (concat [compiler "bench-build"] args [destination "--runtime-profile" "large-vectors-v1"]) compile-env)]
              (.append refusals (u/pydict "name" label "passed" (refused? code destination)))))
          (doseq [[label suffix] [["missing-profile" []] ["unknown-profile" ["--runtime-profile" "unknown"]]
                                  ["standard-profile" ["--runtime-profile" "standard-v1"]]
                                  ["duplicate-profile" ["--runtime-profile" "large-vectors-v1" "--runtime-profile" "large-vectors-v1"]]]]
            (let [destination (.joinpath out (str label ".elf"))
                  [code _ _] (run label (concat [compiler "bench-build" "aarch64-linux" host-src registry-src destination] suffix) compile-env)]
              (.append refusals (u/pydict "name" label "passed" (refused? code destination)))))
          (let [existing-pin (C/pin host)
                [code _ _] (run "existing-output" argv compile-env)]
            (.append refusals (u/pydict "name" "existing-output" "passed" (and (contains? #{1 2} code) (u/deq (C/pin host) existing-pin)))))
          (if (= machine 62)
            ;; Public x86 compiler executes natively, but this closed command emits only ARM hosts. Bind its exact
            ;; bytes/exports to the actually executed ARM qualification; never execute ARM code under x86 emulation.
            (let [arm (u/read-json arm-controls)]
              (u/chk (and (= "native-candidate-observed" (u/geti arm "status")) (= "registered" (u/geti arm "mode"))))
              (u/chk (and (u/deq (u/geti arm "sources") sources) (u/deq (u/geti arm "hostSource") (u/geti report "hostSource"))))
              (u/chk (and (u/deq (u/geti arm "registry") (u/geti report "registry")) (u/deq (u/geti arm "host") (u/geti report "host"))))
              (u/chk (= 19 (u/geti arm "observedWorkloads") (u/geti arm "referenceMatchedWorkloads")))
              (u/chk (and (= 19 (python/len (u/geti arm "workloads"))) (every? #(and (u/geti % "valid") (= 0 (u/geti % "exit"))) (u/geti arm "workloads"))))
              (u/chk (every? #(u/geti % "passed") (concat (u/geti arm "factoryRefusals") (u/geti arm "runtimeRefusals"))))
              (let [by-name (into {} (for [r (u/geti arm "workloads")] [(u/geti r "workload") r]))]
                (doseq [row rows]
                  (let [name (u/geti row "workload") symbol (u/geti (u/geti row "registered") "measuredSymbol")
                        exported (into {} (for [e (u/geti row "exports")] [(u/geti e "name") e]))
                        payload (.joinpath (.joinpath corpus name) (str symbol ".bin"))]
                    (u/chk (and (u/deq (C/pin payload) (u/geti (get exported symbol) "payload")) (u/deq (u/geti (get exported symbol) "payload") (u/geti (get by-name name) "payload"))))
                    (u/chk (u/deq (u/geti row "originalSource") (u/geti (get by-name name) "source")))
                    (.append (u/geti report "workloads")
                             (u/pydict "workload" name "source" (u/geti row "originalSource") "payload" (C/pin payload) "exports" (u/geti row "exports")
                                       "registered" (u/geti row "registered") "matchesExecutedArmPayload" true "executedHere" false)))))
              (u/chk (every? #(u/geti % "passed") refusals))
              (u/chk (every? (fn [[name value]] (u/deq (C/pin (.joinpath root name)) value)) (.items sources)))
              (doseq [[k v] [["status" "PASS_NATIVE_X86_BENCHMARK_FACTORY"] ["factoryRefusals" refusals]
                             ["armExecutionReference" (C/pin arm-controls)] ["emittedArmHostMatches" true]
                             ["observedWorkloads" 19] ["executedArmHostHere" false] ["x86MeasurementHostSupported" false]]]
                (operator/setitem report k v))
              (persist)
              0)
            ;; Exercise the real pinned host's admission and fuel failures. Keep every failed input/output; never
            ;; mutate an original source or payload in place.
            (let [crc (nth rows 1)
                  _ (u/chk (= "crc32" (u/geti crc "workload")))
                  good-payload (.joinpath out "control-crc32.bin")
                  _ (shutil/copy2 (.joinpath (.joinpath corpus "crc32") "benchmark-unchecked.bin") good-payload)
                  _ (u/chk (u/deq (C/pin good-payload) (u/geti (u/geti (u/geti crc "exports") 0) "payload")))
                  damaged (.joinpath out "control-damaged.bin")
                  data (python/bytearray (.read_bytes good-payload))
                  _ (operator/setitem data 0 (bit-xor (operator/getitem data 0) 1))
                  _ (.write_bytes damaged data)
                  truncated (.joinpath out "control-truncated.bin")
                  _ (.write_bytes truncated (u/bslice (.read_bytes good-payload) 0 -1))
                  appended (.joinpath out "control-appended.bin")
                  _ (.write_bytes appended (operator/add (.read_bytes good-payload) (u/bytes-of 0)))
                  symlink (.joinpath out "control-symlink.bin")
                  _ (.symlink_to symlink (.-name good-payload))
                  runtime-env {"KEXE_ALLOW" "-" "KEXE_FUEL" "1000000000000" "KEXE_STACK_BYTES" "8388608" "KEXE_CPU_SECONDS" "10" "KEXE_WALL_SECONDS" "10"}
                  full "1000000000000"
                  runtime-refusals (python/list)]
              (doseq [[label args fuel]
                      [["payload-hash" [1 damaged 1 1] full] ["payload-truncated" [1 truncated 1 1] full]
                       ["payload-appended" [1 appended 1 1] full] ["payload-symlink" [1 symlink 1 1] full]
                       ["payload-directory" [1 out 1 1] full] ["unknown-workload" [19 good-payload 1 1] full]
                       ["negative-workload" [-1 good-payload 1 1] full] ["nondecimal-workload" ["1x" good-payload 1 1] full]
                       ["reduced-registered-count" [1 good-payload 1 0] full] ["increased-diagnostic-count" [1 good-payload 2 1] full]
                       ["unknown-execution-profile" [1 good-payload 1 2] full] ["missing-argument" [1 good-payload 1] full]
                       ["extra-argument" [1 good-payload 1 1 0] full] ["unmetered-fuel" [1 good-payload 1 1] "off"]
                       ["empty-fuel" [1 good-payload 1 1] ""] ["zero-fuel" [1 good-payload 1 1] "0"]
                       ["insufficient-fuel" [1 good-payload 1 1] "1"]]]
                (let [[code stdout _] (run label (cons host args) (python/dict (assoc runtime-env "KEXE_FUEL" fuel)) :timeout 20)]
                  (.append runtime-refusals
                          (u/pydict "name" label "passed" (and (= code (if (= label "insufficient-fuel") 120 2))
                                                               (not (u/has-bytes? (.encode "\"result\":1") stdout)))))))
              (operator/setitem report "runtimeRefusals" runtime-refusals)
              (doseq [[index row] (map-indexed vector rows)]
                (let [name (u/geti row "workload")
                      exported (into {} (for [e (u/geti row "exports")] [(u/geti e "name") e]))
                      symbol (u/geti (u/geti row "registered") "measuredSymbol")
                      payload (.joinpath out (str name ".bin"))
                      _ (shutil/copy2 (.joinpath (.joinpath corpus name) (str symbol ".bin")) payload)
                      _ (u/chk (u/deq (C/pin payload) (u/geti (get exported symbol) "payload")))
                      original (.joinpath root (str "bench/embench/reproduce-20261015/ports/official-" name ".kotoba"))
                      _ (u/chk (u/deq (C/pin original) (u/geti row "originalSource")))
                      n (if full-counts (u/geti (u/geti row "registered") "n") 1)
                      env (python/dict {"KEXE_ALLOW" "-" "KEXE_FUEL" "1000000000000" "KEXE_STACK_BYTES" "8388608"
                                        "KEXE_CPU_SECONDS" (str wall-seconds) "KEXE_WALL_SECONDS" (str wall-seconds)})
                      [code stdout stderr] (run name [host index payload n (if full-counts 0 1)] env :timeout (+ wall-seconds 30))
                      observation (when (and (zero? code) (not (u/nonempty? stderr)))
                                    (try (json/loads stdout ** :object_pairs_hook lib/unique-fields)
                                         (catch python/UnicodeDecodeError _ nil)
                                         (catch python/ValueError _ nil)))
                      valid (lib/valid-observation observation index n (if full-counts 0 1))
                      comparison (when (and valid full-counts)
                                   (let [reference (get references name)
                                         expected-arena (C/arena (.encode (u/geti reference "expectedStderr")))]
                                     (u/chk (and (some? expected-arena) (= (u/geti reference "n") n)))
                                     (u/pydict "benchmarkFuel" (= (u/geti observation "benchmarkFuel") (u/geti (u/geti reference "expectedSample") "benchmarkFuel"))
                                               "verifyFuel" (= (u/geti observation "verifyFuel") (u/geti (u/geti reference "expectedSample") "verifyFuel"))
                                               "finalArena" (u/deq (u/geti observation "finalArena") (python/list (map #(u/geti expected-arena %) C/fields))))))]
                  (.append (u/geti report "workloads")
                           (u/pydict "workload" name "source" (u/geti row "originalSource") "payload" (C/pin payload) "observation" observation
                                     "valid" (boolean valid) "exit" code "observerReferenceComparison" comparison))
                  (persist)))
              ;; Factory/source refusal is only part of qualification: no pass promotion.
              (operator/setitem report "factoryRefusals" refusals)
              (let [wls (python/list (u/geti report "workloads"))]
                (operator/setitem report "observedWorkloads" (count (filter #(u/geti % "valid") wls)))
                (operator/setitem report "referenceMatchedWorkloads"
                                  (when full-counts
                                    (count (filter #(and (some? (u/geti % "observerReferenceComparison"))
                                                         (every? identity (.values (u/geti % "observerReferenceComparison")))) wls))))
                (operator/setitem report "status"
                                  (if (and (= 19 (u/geti report "observedWorkloads"))
                                           (every? #(u/geti % "passed") (concat refusals runtime-refusals))
                                           (or (not full-counts) (= 19 (u/geti report "referenceMatchedWorkloads"))))
                                    "native-candidate-observed" "native-candidate-incomplete")))
              (u/chk (every? (fn [[name value]] (u/deq (C/pin (.joinpath root name)) value)) (.items sources)))
              (persist)
              (if (= "native-candidate-observed" (u/geti report "status")) 0 2))))))))

(defn -main [& args]
  (let [one (u/opt args "--one") complete (u/opt args "--complete")
        ws (python/int (or (u/opt args "--wall-seconds") "300"))]
    (when (= (nil? one) (nil? complete)) (sys/exit "exactly one of --one/--complete is required"))
    (u/chk (<= 1 ws 86400))
    (sys/exit
      (main {:one (when one (pathlib/Path one)) :complete (when complete (pathlib/Path complete))
             :arm-controls (when-let [p (u/opt args "--arm-controls")] (pathlib/Path p))
             :corpus (pathlib/Path (or (u/opt args "--corpus") (sys/exit "--corpus is required")))
             :output (pathlib/Path (or (u/opt args "--output") (sys/exit "--output is required")))
             :host-source (when-let [p (u/opt args "--host-source")] (pathlib/Path p))
             :full-counts (boolean (some #{"--full-counts"} args)) :wall-seconds ws}))))

(when (some #(or (= % "check-native-benchmark-host.cljc") (str/ends-with? % "/check-native-benchmark-host.cljc")) sys/argv)
  (apply -main *command-line-args*))
