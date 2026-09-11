(ns kotoba.compiler.lang-conformance-golden-test
  "T1.5: golden digests for T1.3 pure-product pilot (KIR + wasm)."
  (:require [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.lang-conformance :as lc]))

;; Both counts here used to be the literal 60, repeating a number that lives in
;; the manifest. The manifest grew to 61 and these did not, which nothing
;; noticed because the suite was ending in an earlier namespace. What the golden
;; document actually has to satisfy is coverage — a digest for every case the
;; pilot declares — and that is checkable without naming a size at all.
(deftest golden-document-loads
  (let [g (lc/load-goldens)
        cases (count (lc/pure-product-cases (lc/load-manifest)))]
    (is (= 1 (:kotoba.lang.conformance.golden/version g)))
    (is (= "T1.5" (:kotoba.lang.conformance.golden/wbs g)))
    (is (= cases (count (:cases g)))
        "the golden document has to carry a digest for every declared case")))

(deftest golden-digests-match-live-compile
  (let [report (lc/check-goldens)]
    (is (true? (:ok? report))
        (str "digest drift — regenerate with: "
             "clojure -M:conformance --write-golden ; "
             (pr-str (:mismatches report))))
    (is (= (count (lc/pure-product-cases (lc/load-manifest)))
           (:case-count report))
        "and the check has to visit every one of them")))

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
