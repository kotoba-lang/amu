(ns kotoba.compiler.effect-row-test
  "A row member that is not a grant must not be asked for one.

  kotoba-sema e42b74ef (typed abort ability, slice 1) puts the bare keyword
  `:abort` on the inferred effect row of a function that throws, and the
  module row is the union of function rows. Measured 2026-09-02 at that pin
  bump, before `kotoba.compiler.effect-row` existed: `amu compile --target
  wasm32` answered `capability policy denies required effects` for a module
  whose helper throws and whose `main` catches -- a program that exercises no
  capability -- because every admission site handed the raw row to
  `kotoba.kir.admission/check`, and `:abort` is neither grantable nor
  granted.

  Each assertion here is written so that removing the narrowing turns it red
  by the failure it names, not by an unrelated one: the denial's `:missing`
  set is asserted by value, and the destructuring sites are exercised with a
  row that actually holds the keyword."
  (:require [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]
            [kotoba.compiler.effect-row :as effect-row]
            [kotoba.compiler.test-profile :as profile]
            [kotoba.kir :as ir]
            [kotoba.sema :as sema]))

;; ---------------------------------------------------------------------------
;; The narrowing itself, by value.

(deftest grants-drop-control-effects-and-keep-everything-else
  (is (= #{} (effect-row/grants #{:abort})))
  (is (= #{[:cap/call 3]} (effect-row/grants #{[:cap/call 3] :abort})))
  (is (= #{} (effect-row/grants nil)) "a missing row is an empty row, not an error")
  (testing "an unrecognised member is KEPT, so it reaches admission and is refused there"
    (is (= #{:not-a-known-effect} (effect-row/grants #{:not-a-known-effect :abort})))))

(deftest grant-and-control-effect-are-disjoint-predicates
  (is (effect-row/grant? [:cap/call 3]))
  (is (not (effect-row/grant? :abort)))
  (is (effect-row/control-effect? :abort))
  (is (not (effect-row/control-effect? [:cap/call 3])))
  (is (not (effect-row/control-effect? :cap/call))
      "the tag of a grant vector is not itself a control effect"))

(deftest check-does-not-demand-a-grant-for-abort
  (testing "a row that is only :abort is admitted by the empty policy"
    (is (map? (effect-row/check {:effects #{:abort}} {}))))
  (testing "a grant next to :abort is still required, and the denial names ONLY the grant"
    (let [e (is (thrown? clojure.lang.ExceptionInfo
                         (effect-row/check {:effects #{:abort [:cap/call 3]}} {})))]
      (is (= #{[:cap/call 3]} (:missing (ex-data e))))
      (is (= #{[:cap/call 3]} (:required (ex-data e)))
          "the row admission decided on is the narrowed one")))
  (testing "and granting it admits the module; :abort needs nothing"
    (is (map? (effect-row/check {:effects #{:abort [:cap/call 3]}}
                                {:allow #{[:cap/call 3]}})))))

;; ---------------------------------------------------------------------------
;; Through the compiler: the JVM route, end to end.

(def ^:private across-callee
  "(ns abort.callee (:export [main]))
   (defn- safe-div [a :i64 b :i64] :i64
     (if (= b 0) (throw \"division by zero\") (quot a b)))
   (defn main [] :i64 (try (safe-div 10 0) (catch e (string-length e))))")

(deftest a-module-whose-helper-aborts-is-admitted-with-no-policy
  (let [checked (compiler/check-source across-callee {})]
    (is (= #{:abort} (get-in checked [:hir :effects]))
        "the module row is reported as inferred; only the admission decision is narrowed")
    (is (= #{:abort} (:effects (first (filter #(= 'safe-div (:name %))
                                              (get-in checked [:hir :functions]))))))
    (is (map? (:admission checked)))))

(deftest the-aborting-module-compiles-to-wasm32-and-computes
  (let [compiled (compiler/compile-source across-callee :wasm32-kotoba-v1 {})]
    (is (bytes? (:bytes compiled)))
    (is (= 16 (long (ir/execute (:kir compiled) 'main []))))
    (is (= #{:abort} (get-in compiled [:hir :effects]))
        "provenance's view of the row keeps :abort as-is")))

(deftest an-unhandled-abort-at-main-is-refused-by-the-frontend-verbatim
  (is (= "unhandled abort at export boundary; catch it with try: main"
         (try (compiler/check-source "(defn main [] :i64 (if (= 1 1) (throw \"s\") 1))" {})
              nil
              (catch clojure.lang.ExceptionInfo e (ex-message e))))))

;; ---------------------------------------------------------------------------
;; The two destructuring sites in the test profile, fed a row that holds the
;; keyword. Before the guard `(first :abort)` and `[[effect id] :abort]` both
;; threw before any test ran.

(deftest test-profile-derives-policy-and-ids-from-a-row-holding-abort
  (let [kir (ir/lower (sema/analyze across-callee))]
    (is (= #{:abort} (:effects kir)))
    (is (= [] (#'profile/capability-ids kir)))
    (is (= {:allow #{}} (#'profile/test-policy {:hir {:effects (:effects kir)}}))))
  (testing "a grant beside the keyword still comes through"
    (is (= [7] (#'profile/capability-ids {:effects #{:abort [:cap/call 7]}})))
    (is (= {:allow #{[:cap/call 7]}}
           (#'profile/test-policy {:hir {:effects #{:abort [:cap/call 7]}}})))))
