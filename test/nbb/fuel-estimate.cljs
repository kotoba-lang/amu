(ns test.nbb.fuel-estimate
  "The bounded-countdown fuel estimate (lang-h10) on the Node route.

  `kotoba.compiler.fuel-estimate` is one `.cljc`, so this pins the same
  numbers `test/kotoba/compiler/fuel_estimate_test.clj` pins on the JVM.
  The two halves DID disagree once: under nbb the frontend reads i64
  literals as BigInt, `integer?` is false for those, and the first cut of
  the recognizer answered 16007 on the JVM and 6 here (measured
  2026-09-07). A portable `int-literal` closed it; this file is what keeps
  it closed."
  (:require [kotoba.compiler.fuel-estimate :as fe]
            ["node:fs" :as fs]
            ["node:path" :as path]))

(def ^:private failures (atom 0))

(defn- check! [label ok? detail]
  (if ok?
    (println (str "ok   " label))
    (do (swap! failures inc)
        (println (str "FAIL " label " -- " (pr-str detail))))))

(defn- fixture [name]
  (.readFileSync fs (path/join "test" "fixtures" "fuel-estimate" name) "utf8"))

(let [r (fe/estimate-source (fixture "poll-countdown.kotoba"))
      poll (get-in r [:recursion 'poll])]
  (check! "poll is a bounded countdown"
          (= :bounded-countdown (:kind poll)) poll)
  (check! "poll steps -1 on n toward the literal 0"
          (= [-1 'n 0 2] [(:step poll) (:param poll) (:bound poll) (:per-iteration poll)]) poll)
  (check! "the literal call site expands to 8001 entries x 2 = 16002"
          (= [{:callee 'poll :caller 'main :param 'n :argument 8000
               :bound 0 :iterations 8001 :per-iteration 2 :units 16002}]
             (:bounded-calls r))
          (:bounded-calls r))
  (check! "crude units are 16007 (6 before expansion, +16002 -1)"
          (= 16007 (:crude-units r)) (:crude-units r))
  (check! "and that does not fit the 512 default"
          (false? (:within-default-budget? r)) r))

(let [c (fe/estimate-source (fixture "recursion-control.kotoba"))]
  (check! "control: (quot n 2) recursion stays unbounded"
          (= {:kind :unbounded} (get-in c [:recursion 'halve])) (:recursion c))
  (check! "control: no call site is expanded"
          (= [] (:bounded-calls c)) (:bounded-calls c))
  (check! "control: today's answer, 4 units"
          (= 4 (:crude-units c)) (:crude-units c)))

(when (pos? @failures)
  (println (str @failures " failure(s)"))
  (.exit js/process 1))
