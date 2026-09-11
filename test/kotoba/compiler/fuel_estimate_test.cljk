(ns kotoba.compiler.fuel-estimate-test
  "T7.3 crude fuel estimate, plus the bounded-countdown expansion (lang-h10).

  The aiueos kernel waits with tail-recursive countdown polls such as
  `(rx-ring-wait-command win head 8000)`. Before this slice the estimate
  counted that call site as ONE unit and said nothing about recursion, so
  nobody could read from the source how many entries a run buys -- the
  cadence constant in aiueos was set by watching `ud2` deaths on hardware.
  The numbers pinned here are the estimator's model (1 unit per function
  entry, static call sites counted once), not a measured WCET.

  After the 2026-09-08 split, only the two deftests that read a `.kotoba`
  fixture through `clojure.java.io`/`slurp` stayed here -- nbb has no
  classpath `io/resource`. Every deftest that compiles an inline source
  string moved to `kotoba.compiler.fuel-estimate-portable-test` (.cljc),
  registered on both hosts."
  (:require [clojure.test :refer [deftest is testing]]
            [clojure.java.io :as io]
            [kotoba.compiler.fuel-estimate :as fe]))

(defn- fixture [name]
  (slurp (io/resource (str "fixtures/fuel-estimate/" name))))

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
