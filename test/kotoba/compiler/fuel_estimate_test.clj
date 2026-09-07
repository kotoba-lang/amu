(ns kotoba.compiler.fuel-estimate-test
  "T7.3 crude fuel estimate, plus the bounded-countdown expansion (lang-h10).

  The aiueos kernel waits with tail-recursive countdown polls such as
  `(rx-ring-wait-command win head 8000)`. Before this slice the estimate
  counted that call site as ONE unit and said nothing about recursion, so
  nobody could read from the source how many entries a run buys -- the
  cadence constant in aiueos was set by watching `ud2` deaths on hardware.
  The numbers pinned here are the estimator's model (1 unit per function
  entry, static call sites counted once), not a measured WCET."
  (:require [clojure.test :refer [deftest is testing]]
            [clojure.java.io :as io]
            [kotoba.compiler.fuel-estimate :as fe]))

(defn- fixture [name]
  (slurp (io/resource (str "fixtures/fuel-estimate/" name))))

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

(deftest bounded-countdown-poll-is-estimable
  ;; poll: 3 functions, 3 static call sites -> 6 units before expansion.
  ;; poll's body has one non-self call (helper), so an entry costs 2.
  ;; (poll 3 8000) with guard (= n 0): entries at n = 8000..0 = 8001.
  ;; 8001 x 2 = 16002 units for that call site, replacing the 1 it counted
  ;; as: 6 + 16002 - 1 = 16007.
  (let [r (fe/estimate-source (fixture "poll-countdown.kotoba"))]
    (is (= 3 (:function-count r)))
    (is (= 3 (:static-call-sites r)))
    (testing "the function's recursion is classified as a bounded countdown"
      (is (= {:kind :bounded-countdown :param 'n :index 1 :step -1
              :op '= :bound 0 :terminates-when :test-true
              :guard '(= n 0) :per-iteration 2}
             (get-in r [:recursion 'poll]))))
    (testing "the literal call site is expanded"
      (is (= [{:callee 'poll :caller 'main :param 'n :argument 8000
               :bound 0 :iterations 8001 :per-iteration 2 :units 16002}]
             (:bounded-calls r))))
    (is (= 16007 (:crude-units r)))
    (is (false? (:within-default-budget? r))
        "8001 entries do not fit the 512 default; before this slice the same source reported 6 units and 'within budget'")))

(deftest non-countdown-recursion-keeps-todays-answer
  ;; halve: 2 functions, 2 static call sites -> 4 units, unchanged.
  (let [r (fe/estimate-source (fixture "recursion-control.kotoba"))]
    (is (= 2 (:function-count r)))
    (is (= 2 (:static-call-sites r)))
    (is (= {:kind :unbounded} (get-in r [:recursion 'halve])))
    (is (= [] (:bounded-calls r)))
    (is (= 4 (:crude-units r)))
    (is (true? (:within-default-budget? r)))))

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
