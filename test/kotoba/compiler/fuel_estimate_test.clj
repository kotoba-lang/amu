(ns kotoba.compiler.fuel-estimate-test
  "T7.3 crude fuel estimate."
  (:require [clojure.test :refer [deftest is]]
            [kotoba.compiler.fuel-estimate :as fe]))

(deftest single-main-within-budget
  (let [r (fe/estimate-source
           "(ns t (:export [main])) (defn main [] :i64 (+ 1 2))")]
    (is (= :kotoba.fuel-estimate/v1 (:format r)))
    (is (= 1 (:function-count r)))
    (is (true? (:within-default-budget? r)))
    (is (<= (:crude-units r) 512))))

(deftest counts-static-callee-entries
  (let [r (fe/estimate-source
           "(ns t (:export [main]))
            (defn main [] :i64 (+ 1 (helper)))
            (defn helper [] :i64 2)")]
    (is (= 2 (:function-count r)))
    (is (= 1 (:static-call-sites r)))
    (is (= 3 (:crude-units r)))))
