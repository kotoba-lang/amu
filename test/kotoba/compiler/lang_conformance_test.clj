(ns kotoba.compiler.lang-conformance-test
  "T1.3: pure-product dual-backend (KIR + wasm32-kotoba-v1) pilot."
  (:require [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.lang-conformance :as lc]))

(deftest pilot-manifest-loads
  (let [m (lc/load-manifest)]
    (is (= 2 (:kotoba.lang.conformance/version m)))
    (is (= "T1.3" (:kotoba.lang.conformance/wbs m)))
    (is (= 58 (count (lc/pure-product-cases m))))))

(deftest pure-product-required-backends
  (is (= #{:kir :wasm32-kotoba-v1} lc/pure-product-required)))

(deftest dual-backend-pilot-suite-green
  (let [report (lc/run-suite)]
    (is (pos? (:total report)))
    (is (= 58 (:total report)))
    (is (true? (:ok? report))
        (str "failed: " (pr-str (:failed report))))
    (is (= (:total report) (:passed report)))
    (doseq [r (:results report)]
      (testing (str (:id r))
        (is (true? (:kir-ok? r)))
        (is (true? (:wasm-ok? r)))
        (is (= (get-in r [:kir :result])
               (get-in r [:wasm32-kotoba-v1 :result])))))))

(deftest single-case-kir-matches-expect
  (let [m (lc/load-manifest)
        case (first (filter #(= :portable-guest-assert (:id %))
                            (lc/pure-product-cases m)))
        r (lc/run-case case)]
    (is (true? (:ok? r)))
    (is (= 7 (:expect r)))
    (is (= 7 (get-in r [:kir :result])))))

;; --- T2.3: the profile label must be enforced, not decorative --------------

(deftest every-pure-product-case-passes-profile-admission
  (testing "a case labelled :pure-product compiles under :language-profile :pure-product"
    (let [m (lc/load-manifest)
          cases (lc/pure-product-cases m)
          pure (filter #(= :pure-product (lc/case-language-profile %)) cases)
          portable (filter #(= :portable (lc/case-language-profile %)) cases)]
      (is (= 53 (count pure)))
      (is (= 5 (count portable))
          "dotimes / condp / defmethod / cond->> / -> are portable-only surface")
      (doseq [c pure]
        (testing (str (:id c))
          (is (= :passed (:status (lc/run-case c)))))))))

(deftest pure-product-label-on-forbidden-surface-is-rejected
  (testing "mislabelling a portable-only case as :pure-product fails closed"
    (let [m (lc/load-manifest)
          condp-case (first (filter #(= :portable-static-predicate-condp (:id %))
                                    (lc/pure-product-cases m)))
          mislabelled (assoc condp-case :language-profile :pure-product)
          r (lc/run-case mislabelled)]
      (is (false? (:ok? r)))
      (is (= :profile-rejected (:status r)))
      (is (= :kotoba.error/pure-product-forbidden
             (:kotoba.error/code (:ex-data r)))))))

(deftest suite-reports-profile-split
  (let [report (lc/run-suite)]
    (is (= 53 (:pure-product-passed report)))
    (is (= 5 (:portable-passed report)))
    (is (= (:passed report)
           (+ (:pure-product-passed report) (:portable-passed report))))))
