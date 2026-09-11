(ns kotoba.compiler.lang-native-conformance-test
  "T1.4 pure-native-v1 pilot."
  (:require [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.lang-native-conformance :as nc]))

(deftest native-manifest-loads
  (let [m (nc/load-manifest)]
    (is (= 2 (:kotoba.lang.conformance/version m)))
    (is (= "T1.4" (:kotoba.lang.conformance/wbs m)))
    (is (= 20 (count (:cases m))))))

(deftest pure-native-pilot-suite
  ;; No `when-not (:skipped? report)` guard here any more. It used to wrap the
  ;; count assertion, so the one check that could notice "nothing ran" was
  ;; skipped by the very condition that caused it. Under the `:test` alias
  ;; kototama-native is an extra-dep, so the suite MUST be able to measure;
  ;; if it cannot, that is a finding about the environment and should be loud.
  (let [report (nc/run-suite)]
    (is (= :measured (:status report))
        (str "the native suite did not run: " (:status report)
             " — a green here would say nothing about the native backend"))
    (is (true? (:ok? report))
        (str "failed: " (pr-str (:failed report))))
    (is (= 20 (:passed report)))
    (is (#{:x86_64-kotoba-v1 :aarch64-kotoba-v1} (:target report)))
    (doseq [r (:results report)]
      (testing (str (:id r))
        (is (true? (:ok? r)))))))

(deftest a-suite-that-could-not-run-is-not-a-pass
  ;; Both ways the report used to be :ok? true having executed nothing.
  ;; Measured 2026-08-19 against the code as it stood.
  (testing "the native dependency is absent"
    (with-redefs [nc/tender-native-available? (constantly false)]
      (let [report (nc/run-suite)]
        (is (= :could-not-measure (:status report)))
        (is (false? (:ok? report))
            "all 20 cases skipped and the old :ok? was true")
        (is (zero? (:passed report))))))
  (testing "the manifest has no cases"
    (let [report (nc/run-suite {:cases []})]
      (is (= :no-cases (:status report)))
      (is (false? (:ok? report))
          "0 passed of 0 satisfied the old (= passed (count cases))")))
  (testing "a real failure is still a failure, not an excuse"
    ;; The floor must not turn a genuine red into "could not measure".
    (with-redefs [nc/run-native-case (fn [c] {:id (:id c) :ok? false :status :failed})]
      (let [report (nc/run-suite {:cases [{:id :x} {:id :y}]})]
        (is (= :measured (:status report)))
        (is (false? (:ok? report)))
        (is (= 2 (:failed-count report)))))))
