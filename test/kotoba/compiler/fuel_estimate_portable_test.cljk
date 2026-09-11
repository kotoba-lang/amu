(ns kotoba.compiler.fuel-estimate-portable-test
  "The fixture-free half of kotoba.compiler.fuel-estimate-test (T7.3/lang-h10),
  split out because `kotoba.compiler.fuel-estimate` is already `.cljc` and
  every deftest here compiles an inline source string -- no `io/resource`,
  no `slurp`. `bounded-countdown-poll-is-estimable` and
  `non-countdown-recursion-keeps-todays-answer` stayed in the `.clj` sibling
  because they read `.kotoba` fixtures from `resources/fixtures/fuel-estimate/`
  through `clojure.java.io`/`slurp`, which nbb does not provide."
  (:require #?(:clj [clojure.test :refer [deftest is testing]]
               :cljs [cljs.test :refer [deftest is testing] :include-macros true])
            [kotoba.compiler.fuel-estimate :as fe]))

(deftest single-main-within-budget
  (let [r (fe/estimate-source
           "(ns t (:export [main])) (defn main [] :i64 (+ 1 2))")]
    (is (= :kotoba.fuel-estimate/v1 (:format r)))
    (is (= 1 (:function-count r)))
    (is (true? (:within-default-budget? r)))
    (is (<= (:crude-units r) 512))
    (is (= {} (:recursion r)) "no self-recursion: nothing to report")
    (is (= [] (:bounded-calls r)))))

(deftest counts-static-callee-entries
  (let [r (fe/estimate-source
           "(ns t (:export [main]))
            (defn main [] :i64 (+ 1 (helper)))
            (defn helper [] :i64 2)")]
    (is (= 2 (:function-count r)))
    (is (= 1 (:static-call-sites r)))
    (is (= 3 (:crude-units r)))))

(deftest countup-toward-a-literal-bound
  ;; (+ n 1) toward (>= n 10), self-call in the else branch: n = 0..10 = 11
  ;; entries x 1 unit. 2 + 2 = 4 before, 4 + 11 - 1 = 14 after.
  (let [r (fe/estimate-source
           "(ns t (:export [main]))
            (defn up [n :i64] :i64 (if (>= n 10) 0 (+ 1 (up (+ n 1)))))
            (defn main [] :i64 (up 0))")]
    (is (= 1 (get-in r [:recursion 'up :step])))
    (is (= 11 (:iterations (first (:bounded-calls r)))))
    (is (= 14 (:crude-units r)))))

(deftest self-call-in-the-then-branch-terminates-when-the-test-is-false
  ;; (if (> n 0) (recurse) 0) with (poll 5): n = 5..0 = 6 entries x 1 unit.
  (let [r (fe/estimate-source
           "(ns t (:export [main]))
            (defn poll [n :i64] :i64 (if (> n 0) (+ 1 (poll (- n 1))) 0))
            (defn main [] :i64 (poll 5))")]
    (is (= :test-false (get-in r [:recursion 'poll :terminates-when])))
    (is (= 6 (:iterations (first (:bounded-calls r)))))
    (is (= 9 (:crude-units r)))))

(deftest non-literal-argument-is-not-expanded
  ;; The countdown shape is recognized, but the call passes a parameter, not
  ;; a literal: no call-site expansion, crude units unchanged (3 + 3 = 6).
  (let [r (fe/estimate-source
           "(ns t (:export [main]))
            (defn poll [n :i64] :i64 (if (= n 0) 0 (+ 1 (poll (- n 1)))))
            (defn run [k :i64] :i64 (poll k))
            (defn main [] :i64 (run 8000))")]
    (is (= :bounded-countdown (get-in r [:recursion 'poll :kind])))
    (is (= [] (:bounded-calls r)))
    (is (= 6 (:crude-units r)))))
