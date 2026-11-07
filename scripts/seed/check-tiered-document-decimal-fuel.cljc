;; Qualify document and decimal positives and low-fuel traps with tiered native producers.
;; Ported from check-tiered-document-decimal-fuel.py (Basilisp). Linux arm64 only.
;; Run: basilisp run scripts/seed/check-tiered-document-decimal-fuel.cljc -- --repo DIR --bootstrap DIR --output OUT
(ns check-tiered-document-decimal-fuel
  (:require [basilisp.string :as str]
            [gate-util :as u]
            [tiered-gate :as t])
  (:import operator pathlib re sys))

(defn main [repo boot out]
  (let [g (t/setup repo boot out (.joinpath u/root "scripts/seed/check-tiered-document-decimal-fuel.cljc"))
        {:keys [repo out run runner producer c0 receipt-path before tracked]} g
        fixtures [["document" (.joinpath repo "test/fixtures/selfhost/document/native/document_runtime_test.kotoba")]
                  ["decimal" (.joinpath repo "test/fixtures/selfhost/decimal-literals/native/exact_literals_test.kotoba")]]
        _ (doseq [[_ source] fixtures] (swap! before assoc (str source) (t/pin-of source)))
        observe (fn [producer-name compiler name source]
                  (let [tag (str producer-name "-" name)]
                    (.write_bytes (.joinpath out (str tag ".kotoba")) (.read_bytes source))
                    (let [container (.joinpath out (str tag ".kseed")) raw (.joinpath out (str tag ".bin"))
                          _ (run (str tag "-compile") [compiler "compile" (.joinpath out (str tag ".kotoba")) "--target" "aarch64-macos" "--output" container])
                          ex (run (str tag "-extract") [compiler "extract-native" container "--symbol" "main" "--output" raw])
                          match (re/search (.encode ":offset (\\d+), :length (\\d+), :arity 0}") (.-stdout ex))
                          _ (when (or (nil? match) (not= (python/int (.group match 2)) (.-st_size (.stat raw)))) (t/fail "extract metadata mismatch"))
                          invoke (fn [suffix fuel]
                                   (run (str tag "-" suffix) [runner raw (.decode (.group match 1)) "0" "aarch64" "35,37,38,39" "--"]
                                        :overrides {"KEXE_COMMAND" "1" "KEXE_STRUCTURED_REPORT" "1" "KEXE_FUEL" (str fuel) "KEXE_ALLOW" "-"} :expected nil))
                          normal (invoke "normal" 1000000000)
                          _ (when (or (not (zero? (.-returncode normal))) (u/nonempty? (.-stderr normal)) (not (re/search (.encode ":result 31\\b") (.-stdout normal)))
                                      (u/has-bytes? (.encode ":status :trap") (.-stdout normal)))
                              (t/fail (str [tag "normal" (.-returncode normal) (u/bslice (.-stdout normal) -400 nil) (u/bslice (.-stderr normal) -400 nil)])))
                          low (invoke "low-fuel" 1)
                          _ (when (or (not= 120 (.-returncode low)) (not (u/has-bytes? (.encode ":status :trap") (.-stdout low)))
                                      (not (u/has-bytes? (.encode ":remaining 0}") (.-stdout low))) (not (u/has-bytes? (.encode ":budget/fuel") (.-stderr low)))
                                      (re/search (.encode ":result (-?[0-9]+)") (.-stdout low)))
                              (t/fail (str [tag "fuel" (.-returncode low) (u/bslice (.-stdout low) -400 nil) (u/bslice (.-stderr low) -400 nil)])))]
                      (println tag "positive and low-fuel pass")
                      (.flush sys/stdout)
                      (u/pydict "producer" producer-name "fixture" name "source" (t/pin-of source) "normalExit" (.-returncode normal)
                                "normalOutput" (t/pin-of (.joinpath out (str tag "-normal.stdout")))
                                "lowFuelExit" (.-returncode low) "lowFuelOutput" (t/pin-of (.joinpath out (str tag "-low-fuel.stdout")))))))
        results (python/list (for [[tag compiler] (t/producers g) [name src] fixtures] (observe tag compiler name src)))]
    (when-not (t/unchanged-inputs? g) (t/fail "source changed"))
    (let [report (u/pydict "status" "PASS_TIERED_DOCUMENT_DECIMAL_POSITIVE_FUEL" "compilerF" (t/pin-of producer)
                           "compilerC0" (when c0 (t/pin-of c0)) "bootstrap" (t/pin-of receipt-path) "runner" (t/pin-of runner)
                           "results" results "fullCorpusQualified" false "refusalsQualified" false)]
      (.write_text (.joinpath out "receipt.json") (u/json-dump report))
      (println (u/geti report "status"))
      (.flush sys/stdout))))

(defn -main [& args]
  (let [need (fn [k] (pathlib/Path (or (u/opt args k) (sys/exit (str k " is required")))))]
    (main (need "--repo") (need "--bootstrap") (need "--output"))))

(when (some #(or (= % "check-tiered-document-decimal-fuel.cljc") (str/ends-with? % "/check-tiered-document-decimal-fuel.cljc")) sys/argv)
  (apply -main *command-line-args*))
