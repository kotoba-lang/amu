;; Observe actual native reused/fresh item zeros and executable runtime mutants.
;; Ported from check-native-zero-watermark.py (Basilisp). Linux only.
;; Run: basilisp run scripts/seed/check-native-zero-watermark.cljc -- --compiler C --output OUT
(ns check-native-zero-watermark
  (:require [basilisp.string :as str]
            [gate-util :as u])
  (:import json operator pathlib platform sys time))

(def mark "r (kxrt-store64 (+ (kxrt-gl 688) (* u 8)) 0) high (if (> (+ off n) (kxrt-gl 760)) (kxrt-gs 760 (+ off n)) 0) w (kxrt-gs 48 (inc u))")
(def without "r (kxrt-store64 (+ (kxrt-gl 688) (* u 8)) 0) w (kxrt-gs 48 (inc u))")
(def end-bound "byte-end (+ base (* 8 count))")
(def short-bound "byte-end (+ base (* 8 (if (> count 0) (dec count) 0)))")

(defn main [compiler out]
  (u/chk (and (= "Linux" (platform/system)) (contains? #{"aarch64" "x86_64"} (platform/machine))))
  (.mkdir out ** :parents true :exist_ok false)
  (let [root u/root
        paths (u/manifest-paths (.joinpath root "seed/FULL-MANIFEST"))
        original (.decode (.join (u/bytes-of) (python/list (for [p paths] (operator/add (.read_bytes (.joinpath root p)) (.encode "\n"))))))
        _ (u/chk (and (= 2 (.count original mark)) (= 2 (.count original end-bound))))
        fixture (.joinpath root "seed/tests/native-zero-watermark.kotoba")
        source (.joinpath out "oracle.kotoba")
        _ (.write_bytes source (.read_bytes fixture))
        target (if (= "aarch64" (platform/machine)) "aarch64-linux" "x86_64-linux")
        env (python/dict {"PATH" "/nonexistent" "KEXE_STACK_BYTES" "8388608" "KEXE_CAP_RESOURCES_35" (str out)
                          "KEXE_ALLOW" "35,37,38,39" "KEXE_FUEL" "10000000000" "KEXE_COMMAND" "1"})
        report (u/pydict "schema" "amu.native-zero-watermark-controls.v1" "nativeVerdictAuthority" false
                         "qualificationReplacement" false "wholeCompilerQualified" false "officialPerformanceQualified" false
                         "observerSourceSHA256" (u/geti (u/pin (.joinpath root "scripts/seed/check-native-zero-watermark.cljc")) "sha256")
                         "host" (python/list [(platform/system) (platform/machine)]) "producer" (u/pin compiler) "fixture" (u/pin fixture)
                         "sourceBindings" (u/pydict-from (for [p paths] [p (u/pin (.joinpath root p))]))
                         "calls" (python/list) "mutations" (python/list))
        save (fn [] (.write_text (.joinpath out "observations.json") (u/json-dump report)))
        run (fn [name argv & {:keys [expected execution] :or {expected 0 execution false}}]
              (let [started (time/monotonic)
                    p (u/run-process argv env 900 :cwd out)]
                (doseq [[stream raw] [["stdout" (.-stdout p)] ["stderr" (.-stderr p)]]]
                  (.write_bytes (.joinpath out (str name "." stream)) raw))
                (let [row (u/pydict "name" name "exit" (.-returncode p) "seconds" (- (time/monotonic) started))]
                  (.append (u/geti report "calls") row)
                  (save)
                  (u/chk (and (= expected (.-returncode p)) (not (u/nonempty? (.-stderr p)))) [name (.-returncode p) (u/bslice (.-stderr p) -1200 nil)])
                  (when execution (u/chk (not (u/nonempty? (.-stdout p))) [name "unexpected runtime output"]))
                  (println (json/dumps row))
                  (.flush sys/stdout))))
        build (fn [name producer src]
                (let [image (.joinpath out (str name ".elf"))]
                  (run (str "build-" name) [producer "compile" src "--target" target "--output" image "--format" "static"])
                  (.chmod image 0755)
                  image))
        image (build "oracle" compiler source)]
    (run "fresh-reused-partial-and-nested-scopes" [image] :execution true)
    (operator/setitem report "image" (u/pin image))
    (doseq [[name changed] [["missing-marker" (.replace original mark without)]
                            ["relative-marker" (.replace original "(kxrt-gs 760 (+ off n))" "(kxrt-gs 760 n)")]
                            ["last-word" (.replace original end-bound short-bound)]]]
      (let [src (.joinpath out (str "mutant-" name ".kotoba"))]
        (.write_text src changed)
        ;; The compiler's existing engine stays correct while its emitted guest runtime is broken. Compilation
        ;; failure cannot count as detection.
        (let [mutant-compiler (build (str "mutant-compiler-" name) compiler src)
              mutant (build (str "mutant-oracle-" name) mutant-compiler source)]
          (run (str "detect-" name) [mutant] :expected 1 :execution true)
          (.append (u/geti report "mutations")
                   (u/pydict "name" name "source" (u/pin src) "compiler" (u/pin mutant-compiler) "image" (u/pin mutant)
                             "builtSuccessfully" true "executed" true "exit" 1)))))
    (doseq [[k v] [["status" "PASS_NATIVE_ZERO_WATERMARK_CONTROLS"] ["partialFreshSuffixAndReusedPrefix" true]
                   ["nestedScopesAndOuterValue" true] ["unchangedArenaBudgets" true]]]
      (operator/setitem report k v))
    (save)
    (println (u/geti report "status"))
    (.flush sys/stdout)))

(defn -main [& args]
  (main (.resolve (pathlib/Path (or (u/opt args "--compiler") (sys/exit "--compiler is required"))))
        (.resolve (pathlib/Path (or (u/opt args "--output") (sys/exit "--output is required"))))))

(when (some #(or (= % "check-native-zero-watermark.cljc") (str/ends-with? % "/check-native-zero-watermark.cljc")) sys/argv)
  (apply -main *command-line-args*))
