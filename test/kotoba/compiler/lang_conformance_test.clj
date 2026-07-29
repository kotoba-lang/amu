(ns kotoba.compiler.lang-conformance-test
  "T1.3: pure-product dual-backend (KIR + wasm32-kotoba-v1) pilot."
  (:require [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.lang-conformance :as lc]))

(deftest pilot-manifest-loads
  (let [m (lc/load-manifest)]
    (is (= 2 (:kotoba.lang.conformance/version m)))
    (is (= "T1.3" (:kotoba.lang.conformance/wbs m)))
    (is (= 46 (count (lc/pure-product-cases m))))))

(deftest pure-product-required-backends
  (is (= #{:kir :wasm32-kotoba-v1} lc/pure-product-required)))

(deftest dual-backend-pilot-suite-green
  (let [report (lc/run-suite)]
    (is (pos? (:total report)))
    (is (= 46 (:total report)))
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
