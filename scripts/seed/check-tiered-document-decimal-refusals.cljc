;; Qualify document and decimal refusals with tiered native producers.
;; Ported from check-tiered-document-decimal-refusals.py (Basilisp). Linux arm64 only.
;; Run: basilisp run scripts/seed/check-tiered-document-decimal-refusals.cljc -- --repo DIR --bootstrap DIR --output OUT
(ns check-tiered-document-decimal-refusals
  (:require [basilisp.string :as str]
            [gate-util :as u]
            [tiered-gate :as t])
  (:import operator pathlib re sys))

(defn main [repo boot out]
  (let [g (t/setup repo boot out (.joinpath u/root "scripts/seed/check-tiered-document-decimal-refusals.cljc"))
        {:keys [repo out run runner producer c0 receipt-path before]} g
        source (.joinpath repo "test/fixtures/selfhost/document/native/document_runtime_test.kotoba")
        symbols (vec (re/findall "^\\(defn (refuse-[\\w-]+) \\[\\]" (.read_text source) re/M))
        _ (when (not= 18 (count symbols)) (t/fail "refusal corpus mismatch"))
        _ (swap! before assoc (str source) (t/pin-of source))
        results (python/list)
        decimal (python/list)]
    (doseq [[producer-name compiler] (t/producers g)]
      (let [stage (.joinpath out (str producer-name "-document.kotoba"))
            _ (.write_bytes stage (.read_bytes source))
            container (.joinpath out (str producer-name "-document.kseed"))]
        (run (str producer-name "-document-compile") [compiler "compile" stage "--target" "aarch64-macos" "--output" container])
        (doseq [symbol symbols]
          (let [tag (str producer-name "-" symbol) raw (.joinpath out (str tag ".bin"))
                ex (run (str tag "-extract") [compiler "extract-native" container "--symbol" symbol "--output" raw])
                match (re/search (.encode ":offset (\\d+), :length (\\d+), :arity 0}") (.-stdout ex))
                _ (when (or (nil? match) (not= (python/int (.group match 2)) (.-st_size (.stat raw)))) (t/fail (str ["bad extraction" tag])))
                p (run (str tag "-run") [runner raw (.decode (.group match 1)) "0" "aarch64" "35,37,38,39" "--"]
                       :overrides {"KEXE_COMMAND" "1" "KEXE_STRUCTURED_REPORT" "1" "KEXE_FUEL" "1000000000" "KEXE_ALLOW" "-"} :expected nil)
                remaining (re/search (.encode ":remaining (\\d+)") (.-stdout p))
                expected-signal (.encode (if (= symbol "refuse-utf8") ":SIGILL" ":SIGTRAP"))]
            (when (or (not= 120 (.-returncode p)) (not (u/has-bytes? (.encode ":status :trap") (.-stdout p))) (not (u/has-bytes? expected-signal (.-stderr p)))
                      (and (= symbol "refuse-utf8") (not (u/has-bytes? (.encode ":utf8/invalid-byte") (.-stderr p))))
                      (u/has-bytes? (.encode "budget/fuel") (.-stderr p)) (nil? remaining) (<= (python/int (.group remaining 1)) 0)
                      (re/search (.encode ":result (-?[0-9]+)") (.-stdout p)))
              (t/fail (str [tag (.-returncode p) (u/bslice (.-stdout p) -400 nil) (u/bslice (.-stderr p) -400 nil)])))
            (println tag "trap with remaining fuel" (python/int (.group remaining 1)))
            (.flush sys/stdout)
            (.append results (u/pydict "producer" producer-name "symbol" symbol "remainingFuel" (python/int (.group remaining 1))
                                       "payload" (t/pin-of raw) "stdout" (t/pin-of (.joinpath out (str tag "-run.stdout")))
                                       "stderr" (t/pin-of (.joinpath out (str tag "-run.stderr")))))))))
    (doseq [[producer-name compiler] (t/producers g)]
      (doseq [src (sort-by str (python/list (.glob (.joinpath repo "test/fixtures/selfhost/decimal-literals/refusals") "*.kotoba")))]
        (let [tag (str producer-name "-" (.-stem src))
              _ (swap! before assoc (str src) (t/pin-of src))
              staged (.joinpath out (str tag ".kotoba"))
              _ (.write_bytes staged (.read_bytes src))
              artifact (.joinpath out (str tag ".kseed"))
              p (run (str tag "-refusal") [compiler "compile" staged "--target" "aarch64-macos" "--output" artifact] :expected nil)
              token-match (re/search "\\(f64-to-bits ([^\\s()]+)\\)" (.read_text src))
              _ (when (nil? token-match) (t/fail (str ["invalid refusal fixture" (.-name src)])))
              expected (.encode (str "unknown symbol '" (.group token-match 1) "'"))]
          (when (or (not (zero? (.-returncode p))) (.exists artifact) (not (u/has-bytes? (.encode "E2102") (.-stderr p))) (not (u/has-bytes? expected (.-stderr p))))
            (when (or (zero? (.-returncode p)) (.exists artifact) (not (u/has-bytes? (.encode "E2102") (.-stderr p))) (not (u/has-bytes? expected (.-stderr p))))
              (t/fail (str [tag (.-returncode p) (u/bslice (.-stderr p) -400 nil)]))))
          (println tag "compile refusal pass")
          (.flush sys/stdout)
          (.append decimal (u/pydict "producer" producer-name "source" (t/pin-of src) "exit" (.-returncode p)
                                     "stderr" (t/pin-of (.joinpath out (str tag "-refusal.stderr"))))))))
    (when (or (not= (python/len decimal) (if c0 10 5)) (some (fn [[p v]] (not (u/deq (t/pin-of (pathlib/Path p)) v))) @before))
      (t/fail "inputs changed"))
    (let [report (u/pydict "status" "PASS_TIERED_DOCUMENT_DECIMAL_REFUSALS" "bootstrap" (t/pin-of receipt-path) "compilerF" (t/pin-of producer)
                           "compilerC0" (when c0 (t/pin-of c0)) "runner" (t/pin-of runner) "document" results "decimal" decimal "releaseQualified" false)]
      (.write_text (.joinpath out "receipt.json") (u/json-dump report))
      (println (u/geti report "status"))
      (.flush sys/stdout))))

(defn -main [& args]
  (let [need (fn [k] (pathlib/Path (or (u/opt args k) (sys/exit (str k " is required")))))]
    (main (need "--repo") (need "--bootstrap") (need "--output"))))

(when (some #(or (= % "check-tiered-document-decimal-refusals.cljc") (str/ends-with? % "/check-tiered-document-decimal-refusals.cljc")) sys/argv)
  (apply -main *command-line-args*))
