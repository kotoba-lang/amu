(ns kotoba.compiler.plan-test
  (:require [clojure.test :refer [deftest is]]
            [kotoba.compiler.plan :as plan]))

(def cid
  "A real CIDv1 — cidv1-raw(sha2-256(\"compiler/plan\")).
  It was \"bafycompilerplan\", which is not an identifier;
  `kotoba.abi.contract/cid?` was `#\"b.+\"` and accepted it
  (abi 32ee84b, com-junkawasaki ADR-2608100500)."
  "bafkreihteekkh5xzrg6bat5mjthbtylimi36nifl62c2ladfyftplijcke")

(def input
  {:plan-cid cid :code-closure-cid cid :artifact-cid cid
   :compiler-contract cid :input-cid cid
   :requested-resources #{:customer-record}
   :budget {:fuel 1000}})

(deftest plans-take-effects-only-from-kir
  (let [compiled {:kir {:effects #{[:cap/call 7]}}}
        result (plan/build! compiled input)]
    (is (= :kotoba.plan/v1 (:format result)))
    (is (= #{[:cap/call 7]} (:requested-effects result)))
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"plan input is not exact"
                          (plan/build! compiled (assoc input :requested-effects #{:anything}))))))
