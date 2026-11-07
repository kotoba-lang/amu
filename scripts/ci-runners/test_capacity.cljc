;; Ported from test_capacity.py. Run: basilisp test scripts/ci-runners/test_capacity.cljc
(ns test-capacity
  (:require [basilisp.test :refer [deftest is]]
            [capacity :refer [decide]]))

(def all #{"amu-linux-arm64" "amu-macos-arm64" "amu-linux-x86_64"})

(deftest decide-controls
  (is (= ["selfhosted" "ok"] (decide "selfhosted" all [3 20])))
  (is (= "hosted" (first (decide "selfhosted" (disj all "amu-linux-arm64") []))))          ; dead runner pool -> fall back
  (is (= "hosted" (first (decide "selfhosted-arm" #{"amu-linux-arm64"} []))))              ; mac pool missing
  (is (= "hosted" (first (decide "selfhosted-arm" #{"amu-linux-arm64" "amu-macos-arm64"} [500])))) ; stuck queue
  (is (= "hosted" (first (decide "selfhosted-arm" #{} []))))
  (is (= ["hosted" "not self-hosted"] (decide "hosted" #{} [999])))                         ; never promotes
  (is (= "" (first (decide "" all [])))))
