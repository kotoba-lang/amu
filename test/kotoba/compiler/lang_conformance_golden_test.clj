(ns kotoba.compiler.lang-conformance-golden-test
  "T1.5: golden digests for T1.3 pure-product pilot (KIR + wasm)."
  (:require [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.lang-conformance :as lc]))

(deftest golden-document-loads
  (let [g (lc/load-goldens)]
    (is (= 1 (:kotoba.lang.conformance.golden/version g)))
    (is (= "T1.5" (:kotoba.lang.conformance.golden/wbs g)))
    (is (= 59 (count (:cases g))))))

(deftest golden-digests-match-live-compile
  (let [report (lc/check-goldens)]
    (is (true? (:ok? report))
        (str "digest drift — regenerate with: "
             "clojure -M:conformance --write-golden ; "
             (pr-str (:mismatches report))))
    (is (= 59 (:case-count report)))))

(deftest digest-case-includes-both-hashes
  (let [m (lc/load-manifest)
        case (first (filter #(= :record-kit (:id %)) (lc/pure-product-cases m)))
        d (lc/digest-case case)]
    (is (true? (:result-ok? d)))
    (is (= 7 (:result d)))
    (is (string? (:kir-sha256 d)))
    (is (= 64 (count (:kir-sha256 d))))
    (is (string? (:wasm-sha256 d)))
    (is (= 64 (count (:wasm-sha256 d))))
    (is (pos? (:wasm-byte-count d)))))
