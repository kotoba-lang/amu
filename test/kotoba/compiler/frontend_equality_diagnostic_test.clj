(ns kotoba.compiler.frontend-equality-diagnostic-test
  "The safe equality profile rejects `=` on :string operands, and a rejection
  must NAME the admitted alternative (string=?) instead of only saying the
  type is outside the profile -- fleet-migration field evidence
  (com-junkawasaki/root ADR-2607241100 D2) showed the bare message costs a
  compile-debug cycle per project.

  `=` on two :f64 operands is no longer a rejection: since kotoba-sema
  e42b74ef (type-directed arithmetic, consumed here by ADR 0294) the
  comparison resolves to `f64-eq` by operand type. What remains refused is a
  MIXED pair, and that refusal must name both conversions -- the same rule,
  applied to the diagnostic the frontend now emits."
  (:require [clojure.test :refer [deftest is testing]]
            [kotoba.sema :as sema]))

(defn- rejection-message [source]
  (try
    (sema/analyze source)
    nil
    (catch clojure.lang.ExceptionInfo error
      (ex-message error))))

(deftest string-equality-rejection-names-the-admitted-operator
  (let [message (rejection-message
                 (str "(ns pilot.eq-str (:export [check])) "
                      "(defn check [] (if (= \"a\" \"b\") 1 0))"))]
    (is (some? message))
    (is (clojure.string/includes? message "outside the safe value profile"))
    (is (clojure.string/includes? message "string=?"))))

(deftest f64-equality-is-type-directed-and-a-mixed-pair-names-both-conversions
  (testing "two f64 operands resolve to f64-eq; nothing to reject"
    (is (nil? (rejection-message
               (str "(ns pilot.eq-f64 (:export [check])) "
                    "(defn check [] (if (= 1.5 2.5) 1 0))")))))
  (testing "an f64 beside an i64 is refused, and the refusal names a conversion each way"
    (let [message (rejection-message
                   (str "(ns pilot.eq-mixed-f64 (:export [check])) "
                        "(defn check [] (if (= 1.5 2) 1 0))"))]
      (is (some? message))
      (is (clojure.string/includes? message "= operands must share one numeric type; got f64 and i64"))
      (is (clojure.string/includes? message "i64-to-f64-checked"))
      (is (clojure.string/includes? message "f64-to-i64-checked")))))

(deftest admitted-equality-types-are-unaffected
  (testing "i64 equality still analyzes"
    (is (some? (sema/analyze
                (str "(ns pilot.eq-i64 (:export [check])) "
                     "(defn check [] (if (= 1 2) 1 0))")))))
  (testing "keyword equality still analyzes"
    (is (some? (sema/analyze
                (str "(ns pilot.eq-kw (:export [check])) "
                     "(defn check [] (if (= :a :b) 1 0))")))))
  (testing "mismatched operand types still use the same-type rejection"
    (let [message (rejection-message
                   (str "(ns pilot.eq-mixed (:export [check])) "
                        "(defn check [] (if (= 1 :a) 1 0))"))]
      (is (some? message))
      (is (clojure.string/includes? message "same value type")))))
