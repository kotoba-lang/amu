;; Build and execute semantic host mutations; Basilisp only stages/observes.
;;
;; Each mutation gets an isolated test compiler whose factory admits exactly that mutant's hash instead of the
;; production host hash. No production whitelist, private guest escape, original library or runtime limit changes.
;; The candidate native host's fixed oracle and ordered guards must refuse the executed mutant with its named native
;; refusal, not a timeout or build error.
;; Ported from check-native-benchmark-mutations.py (Basilisp). The mutation list is in native_benchmark_lib.cljc.
;; Run: basilisp run scripts/seed/check-native-benchmark-mutations.cljc -- --one DIR --controls DIR --output OUT [--shard I/N]
(ns check-native-benchmark-mutations
  (:require [basilisp.string :as str]
            [embench-candidate-lib :as C]
            [gate-util :as u]
            [native-benchmark-lib :as lib]
            [native-profile :as profile])
  (:import json operator pathlib sys))

(defn main [one controls output shard]
  (let [root u/root
        one (.resolve one)
        [compiler machine _target receipt sources] (C/provenance one nil)
        _ (u/chk (= 183 machine))
        basis (.resolve controls)
        observed (u/read-json (.joinpath basis "observations.json"))
        _ (u/chk (and (= "native-candidate-observed" (u/geti observed "status")) (= "registered" (u/geti observed "mode"))))
        _ (u/chk (and (u/deq (u/geti observed "sources") sources) (u/deq (u/geti observed "compiler") (C/elf compiler machine))))
        _ (u/chk (= 19 (u/geti observed "observedWorkloads") (u/geti observed "referenceMatchedWorkloads")))
        _ (u/chk (every? #(u/geti % "passed") (concat (u/geti observed "factoryRefusals") (u/geti observed "runtimeRefusals"))))
        host-path (.joinpath root "seed/bench/host-arm.kotoba")
        host (.read_bytes host-path)
        registry (.joinpath root "seed/bench/registry-arm.kotoba")
        _ (u/chk (u/deq (C/pin host-path) (u/geti observed "hostSource")))
        _ (u/chk (u/deq (C/pin registry) (u/geti observed "registry")))
        paths (u/manifest-paths (.joinpath root "seed/FULL-MANIFEST"))
        unity (.join (u/bytes-of) (python/list (for [p paths] (operator/add (.read_bytes (.joinpath root p)) (.encode "\n")))))
        _ (u/chk (= unity (.read_bytes (.joinpath one "full.kotoba"))))
        admitted (.encode (lib/digest host))
        _ (u/chk (= 1 (.count unity admitted)))
        out (.resolve output)
        _ (.mkdir out ** :mode 0700 :parents true :exist_ok false)
        _ (.write_bytes (.joinpath out "observer.cljc") (.read_bytes (.joinpath root "scripts/seed/check-native-benchmark-mutations.cljc")))
        staged-registry (.joinpath out "registry.kotoba")
        _ (.write_bytes staged-registry (.read_bytes registry))
        runner (.joinpath out "runner.kotoba")
        _ (.write_bytes runner (.read_bytes (.joinpath one "runner.kotoba")))
        report (u/pydict "schema" "amu.native-benchmark-semantic-controls.v1" "status" "running"
                         "performanceQualified" false "fullQualification" false "qualificationReplacement" false
                         "nativeVerdictAuthority" false "nativeGuardAuthority" true
                         "compiler" (C/elf compiler machine) "sources" sources "receipt" (C/pin receipt)
                         "positiveObservation" (C/pin (.joinpath basis "observations.json")) "hostSource" (C/pin host-path)
                         "observer" (C/pin (.joinpath root "scripts/seed/check-native-benchmark-mutations.cljc"))
                         "calls" (python/list) "mutations" (python/list))
        save (fn [] (profile/atomic-json (.joinpath out "observations.json") report))
        run (fn [directory name argv env & {:keys [expected] :or {expected 0}}]
              (let [e (python/dict {"PATH" "/nonexistent"})
                    _ (doseq [[k v] (.items env)] (operator/setitem e k v))
                    r (u/run-process argv e 360 :cwd out)]
                (.write_bytes (.joinpath directory (str name ".stdout")) (.-stdout r))
                (.write_bytes (.joinpath directory (str name ".stderr")) (.-stderr r))
                (.append (u/geti report "calls")
                         (u/pydict "name" (str (.-name directory) "/" name) "argv" (python/list (map str argv)) "exit" (.-returncode r)
                                   "stdout" (C/pin (.joinpath directory (str name ".stdout")))
                                   "stderr" (C/pin (.joinpath directory (str name ".stderr")))))
                (save)
                (println (.-name directory) name (.-returncode r))
                (.flush sys/stdout)
                (u/chk (= expected (.-returncode r)) [(.-name directory) name (.-returncode r) (u/bslice (.-stderr r) -500 nil)])
                (when (zero? expected) (u/chk (not (u/nonempty? (.-stderr r)))))
                r))
        build-env (python/dict {"KEXE_ALLOW" "35,37,38,39" "KEXE_CAP_RESOURCES_35" (str out) "KEXE_STACK_BYTES" "8388608"})
        run-env (python/dict {"KEXE_ALLOW" "-" "KEXE_FUEL" "1000000000000" "KEXE_STACK_BYTES" "8388608" "KEXE_CPU_SECONDS" "120" "KEXE_WALL_SECONDS" "120"})
        rows (into {} (for [r (u/geti observed "workloads")] [(u/geti r "workload") r]))
        _ (save)
        everything (lib/mutations (.decode host))
        _ (u/chk (and (= 13 (count everything)) (= 13 (count (set (map first everything))))))
        ;; JUN-759: the mutants are independent. --shard I/N runs every N-th one (I from 1); the shards partition all
        ;; 13, and each shard asserts that it ran all of its own. Without --shard all 13 run, as before.
        [index count-shards] shard
        selected (vec (take-nth count-shards (drop (dec index) everything)))]
    (operator/setitem report "shard" (u/pydict "index" index "of" count-shards "mutations" (python/list (map first selected))))
    (doseq [[name workload refusal changed] selected]
      (let [directory (.joinpath out name)
            _ (.mkdir directory ** :mode 0700)
            mutant-source (.joinpath directory "host.kotoba")
            _ (.write_bytes mutant-source (.encode changed))
            mutant-digest (.encode (lib/digest (.encode changed)))
            _ (u/chk (not= mutant-digest admitted))
            ;; Only the isolated test compiler's closed admission constant changes.
            source (.joinpath directory "compiler.kotoba")
            _ (.write_bytes source (.replace unity admitted mutant-digest))
            [container producer image] (map #(.joinpath directory %) ["compiler.kseed" "compiler.elf" "host.elf"])]
        (run directory "compiler-build" [compiler "compile" source "--target" "aarch64-macos" "--output" container] build-env)
        (run directory "compiler-pack" [compiler "compile" runner "--target" "aarch64-linux" "--output" producer "--format" "packed" "--payload" container] build-env)
        (.chmod producer 0700)
        (run directory "host-build" [producer "bench-build" "aarch64-linux" mutant-source staged-registry image "--runtime-profile" "large-vectors-v1"] build-env)
        (.chmod image 0700)
        ;; An emitted real host and a real original-count run are mandatory.
        (let [row (get rows workload)
              wid (u/geti (u/geti row "observation") "workloadId")
              cnt (u/geti (u/geti row "observation") "iterations")
              payload (.joinpath basis (str workload ".bin"))
              _ (u/chk (u/deq (C/pin payload) (u/geti row "payload")))
              result (run directory "detect" [image wid payload cnt 0] run-env :expected 2)]
          (u/chk (and (not (u/nonempty? (.-stdout result))) (= (.encode (str "KREFUSE:" refusal "\n")) (.-stderr result)))
                 [name (.-stdout result) (.-stderr result)])
          (.append (u/geti report "mutations")
                   (u/pydict "name" name "workload" workload "iterations" cnt "builtSuccessfully" true "executed" true
                             "detectedBy" "native named guard refusal" "refusal" refusal
                             "compilerSource" (C/pin source) "compilerContainer" (C/pin container) "compiler" (C/elf producer 183)
                             "hostSource" (C/pin mutant-source) "host" (C/elf image 183) "payload" (C/pin payload)))
          (save))))
    (u/chk (= (python/list (map first selected)) (python/list (map #(u/geti % "name") (u/geti report "mutations")))))
    (u/chk (every? (fn [[name value]] (u/deq (C/pin (.joinpath root name)) value)) (.items sources)))
    (u/chk (u/deq (C/pin host-path) (u/geti report "hostSource")))
    (operator/setitem report "status" "PASS_EXECUTED_NATIVE_BENCHMARK_MUTATIONS")
    (save)
    (println (u/geti report "status") (python/len (u/geti report "mutations")))
    (.flush sys/stdout)))

(defn -main [& args]
  (let [[i n] (map #(python/int %) (.split (or (u/opt args "--shard") "1/1") "/"))]
    (u/chk (<= 1 i n 13) "shard must be I/N with 1 <= I <= N <= 13")
    (main (pathlib/Path (or (u/opt args "--one") (sys/exit "--one is required")))
          (pathlib/Path (or (u/opt args "--controls") (sys/exit "--controls is required")))
          (pathlib/Path (or (u/opt args "--output") (sys/exit "--output is required")))
          [i n])))

(when (some #(or (= % "check-native-benchmark-mutations.cljc") (str/ends-with? % "/check-native-benchmark-mutations.cljc")) sys/argv)
  (apply -main *command-line-args*))
