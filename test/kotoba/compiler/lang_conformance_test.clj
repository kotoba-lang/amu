(ns kotoba.compiler.lang-conformance-test
  "T1.3: pure-product dual-backend (KIR + wasm32-kotoba-v1) pilot."
  (:require [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.lang-conformance :as lc]))

;; The size of the pilot is a ratchet: a case is added deliberately and these
;; numbers move with it in the same commit. They are stated once, here, because
;; the same three literals used to appear in five assertions across two
;; namespaces, and every one of them was stale — the manifest had grown to 61
;; while the tests still read 60. Nothing noticed, because nothing could reach
;; this namespace: the suite was ending in an earlier one. Everything below
;; that can be derived from the manifest now is.
(def ^:private expected-cases {:total 61 :pure-product 56 :portable 5})

(deftest pilot-manifest-loads
  (let [m (lc/load-manifest)]
    (is (= 2 (:kotoba.lang.conformance/version m)))
    (is (= "T1.3" (:kotoba.lang.conformance/wbs m)))
    (is (= (:total expected-cases) (count (lc/pure-product-cases m))))
    (is (= (:total expected-cases)
           (+ (:pure-product expected-cases) (:portable expected-cases)))
        "the profile split has to account for every case in the pilot")))

(deftest pure-product-required-backends
  (is (= #{:kir :wasm32-kotoba-v1} lc/pure-product-required)))

(deftest dual-backend-pilot-suite-green
  (let [report (lc/run-suite)
        cases (count (lc/pure-product-cases (lc/load-manifest)))]
    (is (pos? (:total report)))
    (is (= cases (:total report))
        "the suite has to run every case the manifest declares")
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
      (is (= (:pure-product expected-cases) (count pure)))
      (is (= (:portable expected-cases) (count portable))
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
    (is (= (:pure-product expected-cases) (:pure-product-passed report)))
    (is (= (:portable expected-cases) (:portable-passed report)))
    (is (= (:passed report)
           (+ (:pure-product-passed report) (:portable-passed report))))))

(deftest a-case-that-ran-nothing-is-not-a-pass
  ;; ADR 0260, the sibling of ADR 0259 one layer down: there the SUITE could
  ;; report ok having executed nothing, here a single CASE could.
  ;;
  ;; `nil` for a backend legitimately means "this case does not require it", so
  ;; the old per-backend `(or (nil? kir) ...)` is right on its own. What was
  ;; missing is that every backend being nil left `ok?` true, and the case then
  ;; asserted nothing while reporting :passed.
  (let [real (first (lc/pure-product-cases (lc/load-manifest)))]
    (testing "a backend name that does not exist"
      ;; Measured before the fix: {:ok? true :status :passed :kir nil
      ;; :wasm32-kotoba-v1 nil}. The case is still SELECTED, because
      ;; pure-product-cases also matches on :class :pure-product-run, which all
      ;; 61 carry — so a renamed backend would turn cases into green no-ops
      ;; without moving a single count.
      (let [r (lc/run-case (assoc real :required-backends #{:wasm32-kotoba-v1-TYPO}))]
        (is (false? (:ok? r)))
        (is (= :unknown-backend (:status r)))
        (is (= #{:wasm32-kotoba-v1-TYPO} (set (:unknown-backends r)))
            "the unknown name is reported, not just the emptiness — a typo and
             an empty requirement want different repairs")
        (is (empty? (:ran r)))))
    (testing "an empty requirement"
      (let [r (lc/run-case (assoc real :required-backends #{}))]
        (is (false? (:ok? r)))
        (is (= :no-backend-ran (:status r)))))
    (testing "the real case still passes on both backends"
      ;; The floor must not cost a genuine pass.
      (let [r (lc/run-case real)]
        (is (true? (:ok? r)))
        (is (= :passed (:status r)))
        (is (= #{:kir :wasm32-kotoba-v1} (set (:ran r))))))))

(deftest an-empty-manifest-is-not-a-pass
  ;; `(empty? failed)` was satisfied by having no cases at all.
  (let [report (lc/run-suite {:cases []})]
    (is (false? (:ok? report)))
    (is (= :no-cases (:status report)))
    (is (zero? (:total report)))))

(deftest the-real-suite-is-measured
  (let [report (lc/run-suite)]
    (is (= :measured (:status report)))
    (is (true? (:ok? report)))
    (is (pos? (:total report)))
    (is (= (:total report) (:passed report)))))
