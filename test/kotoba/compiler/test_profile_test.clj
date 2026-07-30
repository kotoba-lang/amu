(ns kotoba.compiler.test-profile-test
  (:require [clojure.test :refer [deftest is]]
            [kotoba.compiler.test-profile :as profile]))

(def source
  "(ns test.portable
     (:capabilities #{:http/post})
     (:export [test-handler test-pure test-ability]))
   (defn test-handler [cap-id value]
     (if (= cap-id 4) (+ value 1) 0))
   (defn test-pure [] (= (+ 20 22) 42))
   (defn test-ability [] (= (cap-call :http/post 41) 42))")

;; The two tests are predicates, written as predicates. They were briefly
;; `(if (= …) 1 0)` so that a runner checking `=== 1n` would keep passing --
;; which made the canonical example of what a Kotoba test looks like use the
;; exact profile-4 idiom ADR 0191 calls the non-Clojure one. The runner states
;; the rule instead (a test returns a boolean; 1/1n stays accepted for the
;; deprecation window), so the fixture can read like Clojure again.

(deftest one-kotoba-test-source-runs-on-every-target
  (let [report (profile/run-source source)]
    (is (:ok report) (pr-str (:failed report)))
    (is (= ['test-pure 'test-ability] (:tests report)))
    (is (= #{:jvm-kir :js :wasm} (set (keys (:results report)))))
    (is (re-matches #"[0-9a-f]{64}" (:test-definition-cid report)))))
