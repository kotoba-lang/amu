(ns kotoba.compiler.lang-native-conformance-test
  "T1.4 pure-native-v1 pilot."
  (:require [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.lang-native-conformance :as nc]))

(deftest native-manifest-loads
  (let [m (nc/load-manifest)]
    (is (= 2 (:kotoba.lang.conformance/version m)))
    (is (= "T1.4" (:kotoba.lang.conformance/wbs m)))
    ;; 8 scalar/string/option cases plus the 7 vector cases added with the
    ;; host vector table (ADR-2608049200). Pinned as a count so a case that
    ;; stops being listed cannot pass by simply not running.
    (is (= 15 (count (:cases m))))))

(deftest pure-native-pilot-suite
  (let [report (nc/run-suite)]
    (is (true? (:ok? report))
        (str "failed: " (pr-str (:failed report))))
    (when-not (:skipped? report)
      (is (= 15 (:passed report)))
      (is (#{:x86_64-kotoba-v1 :aarch64-kotoba-v1} (:target report)))
      (doseq [r (:results report)]
        (testing (str (:id r))
          (is (true? (:ok? r))))))))
