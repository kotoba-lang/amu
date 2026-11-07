;; Native whole-prefix label-index semantic and mutation controls.
;;
;; Basilisp stages source bytes and records actual process results. It emits no native formats. This unit is not
;; whole compiler/product qualification.
;; Ported from check-native-label-index.py (Basilisp). Linux only.
;; Run: basilisp run scripts/seed/check-native-label-index.cljc -- --compiler C --output OUT [--controls-only]
(ns check-native-label-index
  (:require [basilisp.string :as str]
            [gate-util :as u])
  (:import json operator os pathlib platform resource sys time))

(defn- usage [] (python/list (os/getloadavg)))

(defn main [compiler output]
  (u/chk (= "Linux" (platform/system)))
  (let [architecture (platform/machine)
        _ (u/chk (contains? #{"aarch64" "x86_64"} architecture))
        target (if (= "aarch64" architecture) "aarch64-linux" "x86_64-linux")
        root u/root
        _ (.mkdir output ** :parents true :exist_ok false)
        paths (u/manifest-paths (.joinpath root "seed/CORE-STATIC-MANIFEST"))
        _ (u/chk (= "seed/99-entry.kotoba" (last paths)))
        fixture (.joinpath root "seed/tests/native-label-index.kotoba")
        unity (.joinpath output "label-index.kotoba")
        _ (.write_bytes unity (operator/add (.join (u/bytes-of) (python/list (for [p (butlast paths)] (operator/add (.read_bytes (.joinpath root p)) (.encode "\n")))))
                                            (.read_bytes fixture)))
        report (u/pydict "schema" "amu.native-label-index-experiment.v1" "host" (python/list [(platform/system) architecture])
                         "officialPerformanceQualified" false "wholeCompilerQualified" false "candidateAdopted" false
                         "sourceModules" (count paths) "productionPrefixModules" (dec (count paths))
                         "unitEntryReplacement" (last paths)
                         "sourceBindings" (u/pydict-from (for [p (butlast paths)] [p (u/pin (.joinpath root p))]))
                         "fixture" (u/pin fixture) "unity" (u/pin unity) "producer" (u/pin compiler)
                         "loadStart" (usage) "calls" (python/list))
        env (python/dict {"PATH" "/nonexistent" "KEXE_STACK_BYTES" "8388608" "KEXE_CAP_RESOURCES_35" (str output)
                          "KEXE_FUEL" "10000000000" "KEXE_COMMAND" "1" "KEXE_ALLOW" "38"})
        build-env (let [e (python/dict env)] (operator/setitem e "KEXE_ALLOW" "35,37,38,39") e)
        save (fn [] (.write_text (.joinpath output "observations.json") (u/json-dump report)))
        run (fn [name argv & {:keys [expected process-env] :or {expected 0}}]
              (let [started (time/monotonic)
                    before (resource/getrusage resource/RUSAGE_CHILDREN)
                    result (u/run-process argv (or process-env env) 900 :cwd output)
                    after (resource/getrusage resource/RUSAGE_CHILDREN)
                    row (u/pydict "name" name "exit" (.-returncode result) "seconds" (- (time/monotonic) started)
                                  "cpuSeconds" (- (+ (.-ru_utime after) (.-ru_stime after)) (.-ru_utime before) (.-ru_stime before))
                                  "load" (usage))]
                (doseq [[suffix raw] [["stdout" (.-stdout result)] ["stderr" (.-stderr result)]]]
                  (.write_bytes (.joinpath output (str name "." suffix)) raw))
                (.append (u/geti report "calls") row)
                (save)
                (println (json/dumps row))
                (.flush sys/stdout)
                (u/chk (and (= expected (.-returncode result)) (not (u/nonempty? (.-stderr result)))) [name (.-returncode result) (u/bslice (.-stderr result) -1000 nil)])
                row))
        image (.joinpath output "label-index.elf")]
    (run "build" [compiler "compile" unity "--target" target "--output" image "--format" "static"] :process-env build-env)
    (.chmod image 0755)
    (operator/setitem report "image" (u/pin image))
    (run "semantic-anchors-grid-and-malformed" [image])
    (run "wrong-mode-failure-control" [image "fail-control"] :expected 1)
    (let [original (.read_text unity)
          ;; Preserve the selfhost's original R6C inference exercise after making implementation signatures
          ;; explicit. Every declaration/body stays in this source; the only edits remove these three parameter
          ;; annotations. The independently checked forms must generate the same entire image.
          inference-parameters [["ck-r6c-doctail" "c"] ["ck-r6c-dt" "b"] ["ck-r6c-lit" "m"]]
          inferred (reduce (fn [text [function lastp]]
                             (let [typed (str "(defn- " function " [M :vector-i64 S :string " lastp " :i64]")
                                   untyped (str "(defn- " function " [M :vector-i64 S " lastp " :i64]")]
                               (u/chk (and (= 1 (.count text typed)) (zero? (.count text untyped))) function)
                               (.replace text typed untyped)))
                           original inference-parameters)
          inferred-source (.joinpath output "unannotated-inference.kotoba")
          _ (.write_text inferred-source inferred)
          inferred-image (.joinpath output "unannotated-inference.elf")]
      (run "build-unannotated-inference" [compiler "compile" inferred-source "--target" target "--output" inferred-image "--format" "static"]
           :process-env build-env)
      (u/chk (= (.read_bytes inferred-image) (.read_bytes image)) "inferred and explicit signatures emit different code")
      (.chmod inferred-image 0755)
      (run "semantic-unannotated-inference" [inferred-image])
      (run "wrong-mode-unannotated-inference" [inferred-image "fail-control"] :expected 1)
      (operator/setitem report "inferenceControl"
                        (u/pydict "source" (u/pin inferred-source) "image" (u/pin inferred-image)
                                  "parameters" (python/list (map first inference-parameters)) "wholeImageByteIdentical" true
                                  "freshCompilation" true "freshExecution" true))
      (operator/setitem report "mutationControls" (python/list))
      (doseq [[name old new]
              [["duplicate-label" "(if (= (vector-at out (+ base l)) 0) j -1)" "j"]
               ["suffix-query" "(and (= j 1) (= found 0) (> (glx-base M) 0))" "(and (= found 0) (> (glx-base M) 0))"]
               ["accumulator-query" "(and (= j 1) (= found 0) (> (glx-base M) 0))" "(and (= j 1) (> (glx-base M) 0))"]
               ["ccf-suffix-query" "(and (= j 1) (= found 0) (> l 0) (< l MM-LABEL-CAP) (> (glx-base M) 0))" "(and (= found 0) (> l 0) (< l MM-LABEL-CAP) (> (glx-base M) 0))"]
               ["release-top" "(= (vector-at M MM-HEAP-TOP) (+ base MM-LABEL-CAP))" "true"]
               ["ccf-window" "(or (< position (- i 2)) (> position i))" "true"]
               ["ccf-reserved-operands" "(= (gn-sir M position IF-B) 0) (= (gn-sir M position IF-C) 0)" "true"]
               ["optional-heap" "(> (vector-at M MM-HEAP-TOP) (- MM-HEAP-END MM-LABEL-CAP))" "false"]
               ["stale-extent" "(= (vector-at M base) sn)" "true"]]]
        (u/chk (= 1 (.count original old)) name)
        (let [source (.joinpath output (str "mutant-" name ".kotoba"))
              _ (.write_text source (.replace original old new))
              mutant (.joinpath output (str "mutant-" name ".elf"))]
          (run (str "build-mutant-" name) [compiler "compile" source "--target" target "--output" mutant "--format" "static"] :process-env build-env)
          (.chmod mutant 0755)
          (run (str "reject-mutant-" name) [mutant] :expected 1)
          (.append (u/geti report "mutationControls")
                   (u/pydict "removedGuard" name "source" (u/pin source) "image" (u/pin mutant) "expectedSemanticExit" 1)))))
    (doseq [[k v] [["status" "PASS_NATIVE_LABEL_INDEX_SEMANTIC_AND_MUTATION_CONTROLS"] ["anchorsPassed" true]
                   ["benchmarkExecuted" false] ["loadEnd" (usage)]]]
      (operator/setitem report k v))
    (save)
    (println (u/geti report "status"))
    (.flush sys/stdout)))

(defn -main [& args]
  (main (.resolve (pathlib/Path (or (u/opt args "--compiler") (sys/exit "--compiler is required"))))
        (.resolve (pathlib/Path (or (u/opt args "--output") (sys/exit "--output is required"))))))

(when (some #(or (= % "check-native-label-index.cljc") (str/ends-with? % "/check-native-label-index.cljc")) sys/argv)
  (apply -main *command-line-args*))
