;; Observe native equivalence to the original CCF evaluator and four mutants.
;; Ported from check-native-ccf-filter.py (Basilisp). Linux only.
;; Run: basilisp run scripts/seed/check-native-ccf-filter.cljc -- --compiler C --output OUT
(ns check-native-ccf-filter
  (:require [basilisp.string :as str]
            [gate-util :as u])
  (:import json operator pathlib platform sys time))

(defn main [compiler out]
  (u/chk (and (= "Linux" (platform/system)) (contains? #{"aarch64" "x86_64"} (platform/machine))))
  (.mkdir out ** :parents true :exist_ok false)
  (let [root u/root
        paths (vec (butlast (u/manifest-paths (.joinpath root "seed/CORE-STATIC-MANIFEST"))))
        source (.decode (.join (u/bytes-of) (python/list (for [p paths] (operator/add (.read_bytes (.joinpath root p)) (.encode "\n"))))))
        fixture (.joinpath root "seed/tests/native-ccf-filter.kotoba")
        text (str source (.read_text fixture))
        start (.index text "(defn- ccf-code [")
        end (.index text ";; Preserve direct returned-value comparison" start)
        fragment (subs text start end)
        target (if (= "aarch64" (platform/machine)) "aarch64-linux" "x86_64-linux")
        env (python/dict {"PATH" "/nonexistent" "KEXE_STACK_BYTES" "8388608" "KEXE_CAP_RESOURCES_35" (str out)
                          "KEXE_ALLOW" "35,37,38,39" "KEXE_FUEL" "10000000000" "KEXE_COMMAND" "1"})
        report (u/pydict "schema" "amu.native-ccf-filter-controls.v1" "nativeVerdictAuthority" false
                         "qualificationReplacement" false "wholeCompilerQualified" false "gridCases" 131072
                         "host" (python/list [(platform/system) (platform/machine)]) "producer" (u/pin compiler) "fixture" (u/pin fixture)
                         "observerSourceSHA256" (u/geti (u/pin (.joinpath root "scripts/seed/check-native-ccf-filter.cljc")) "sha256")
                         "sourceBindings" (u/pydict-from (for [p paths] [p (u/pin (.joinpath root p))]))
                         "calls" (python/list) "mutations" (python/list))
        save (fn [] (.write_text (.joinpath out "observations.json") (u/json-dump report)))
        run (fn [name argv & {:keys [expected] :or {expected 0}}]
              (let [started (time/monotonic)
                    p (u/run-process argv env 900 :cwd out)]
                (doseq [[stream raw] [["stdout" (.-stdout p)] ["stderr" (.-stderr p)]]]
                  (.write_bytes (.joinpath out (str name "." stream)) raw))
                (.append (u/geti report "calls") (u/pydict "name" name "exit" (.-returncode p) "seconds" (- (time/monotonic) started)))
                (save)
                (u/chk (and (= expected (.-returncode p)) (not (u/nonempty? (.-stderr p)))) [name (.-returncode p) (u/bslice (.-stderr p) -1200 nil)])
                (when-not (str/starts-with? name "build-")
                  (u/chk (not (u/nonempty? (.-stdout p))) [name "unexpected oracle output"]))))
        build (fn [name contents]
                (let [src (.joinpath out (str name ".kotoba"))]
                  (.write_text src contents)
                  (let [image (.joinpath out (str name ".elf"))]
                    (run (str "build-" name) [compiler "compile" src "--target" target "--output" image "--format" "static"])
                    (.chmod image 0755)
                    image)))
        image (build "oracle" text)]
    (run "original-evaluator-equivalence" [image])
    (run "wrong-mode" [image "fail"] :expected 1)
    (doseq [[name old new] [["word-bound" "(and (>= w 0) (<= w 4294967295)" "(and true true"]
                            ["adrp" "(not= page 2415919104)" "true"]
                            ["class-adr-bit" "67835469688274944" "67835469688209408"]
                            ["class-literal-bit" "67835469688274944" "67835469671497728"]]]
      (u/chk (= 1 (.count fragment old)) name)
      (let [mutant (build (str "mutant-" name) (str (subs text 0 start) (.replace fragment old new) (subs text end)))]
        (run (str "detect-" name) [mutant] :expected 1)
        (.append (u/geti report "mutations") (u/pydict "name" name "image" (u/pin mutant) "builtSuccessfully" true "executed" true "exit" 1))))
    (doseq [[k v] [["status" "PASS_NATIVE_CCF_FILTER_CONTROLS"] ["originalEvaluatorEquivalence" true]
                   ["noMutablePrefixCache" true] ["allOriginalLimitsAndPredicatesRetained" true]]]
      (operator/setitem report k v))
    (save)
    (println (u/geti report "status"))
    (.flush sys/stdout)))

(defn -main [& args]
  (main (.resolve (pathlib/Path (or (u/opt args "--compiler") (sys/exit "--compiler is required"))))
        (.resolve (pathlib/Path (or (u/opt args "--output") (sys/exit "--output is required"))))))

(when (some #(or (= % "check-native-ccf-filter.cljc") (str/ends-with? % "/check-native-ccf-filter.cljc")) sys/argv)
  (apply -main *command-line-args*))
