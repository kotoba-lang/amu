(ns kotoba.compiler.dataspace-provider-test
  "Compiler injects kotoba-lang/provider's dataspace host (ADR-2608154100 gap 2).

  Guest uses named :dataspace/transact. The in-memory reference host no longer
  lives in this repo."
  (:require [clojure.edn :as edn]
            [clojure.test :refer [deftest is]]
            [kotoba.compiler.core :as compiler]
            [kotoba.kir :as ir]
            [kotoba.compiler.reference-runtime :as runtime]
            [provider.dataspace :as dataspace]))

(def source
  (str "(ns app.dataspace (:export [coord]) (:capabilities #{:dataspace/transact}))"
       "(defn coord [request " (pr-str dataspace/request-type) "] "
       (pr-str dataspace/result-type) " (typed-cap-call :dataspace/transact "
       (pr-str dataspace/request-type) " " (pr-str dataspace/result-type)
       " request))"))

(defn- host []
  (let [kir (ir/lower (:hir (compiler/check-source
                             source {:allow #{[:cap/call 24]}})))]
    (runtime/instantiate kir {:allow #{24}
                              :providers {24 (dataspace/provider)}})))

(defn- invoke [runtime request]
  ((:invoke runtime) 'coord [request]))

(defn- assert-req [edn facet]
  [dataspace/request-type :assert [dataspace/assert-type edn facet]])

(defn- observe-req [edn facet]
  [dataspace/request-type :observe [dataspace/observe-type edn facet]])

(deftest observe-pattern-binds-and-fires-on-matching-assert
  (let [runtime (host)
        observed (invoke runtime (observe-req "[:temperature :room/a ?t]" 0))
        asserted (invoke runtime (assert-req "[:temperature :room/a 21]" 0))]
    (is (= :matches (second observed)))
    (is (= "[]" (last (nth observed 2))))
    (is (= :asserted (second asserted)))
    (is (= [{'?t 21}] (edn/read-string (last (nth asserted 2)))))
    (let [again (invoke runtime (observe-req "[:temperature :room/a ?t]" 0))]
      (is (= [{'?t 21}] (edn/read-string (last (nth again 2))))))))

(deftest facet-exit-retracts-owned-assertions-and-drops-observations
  (let [runtime (host)
        entered (invoke runtime [dataspace/request-type :facet-enter true])
        fid (last (nth entered 2))]
    (is (= :facet (second entered)))
    (invoke runtime (observe-req "[:temperature :room/a ?t]" fid))
    (invoke runtime (assert-req "[:temperature :room/a 21]" fid))
    (let [left (invoke runtime [dataspace/request-type :facet-leave fid])
          remaining (invoke runtime (observe-req "[:temperature :room/a ?t]" 0))]
      (is (= :retracted (second left)))
      (is (= 1 (last (nth left 2))))
      (is (= [] (edn/read-string (last (nth remaining 2))))))))

(deftest missing-grant-denies-before-provider-invoke
  (let [kir (ir/lower (:hir (compiler/check-source
                             source {:allow #{[:cap/call 24]}})))
        runtime (runtime/instantiate kir)]
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"capability denied"
         (invoke runtime (assert-req "[:temperature :room/a 21]" 0))))
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"capability denied"
         (invoke runtime (observe-req "[:temperature :room/a ?t]" 0))))))

(deftest copied-assertion-edn-does-not-grant-observe
  (let [left (host)
        right (host)
        assertion "[:temperature :room/a 21]"]
    (invoke left (assert-req assertion 0))
    (let [stolen (vec (edn/read-string assertion))
          other (invoke right (observe-req (pr-str stolen) 0))]
      (is (= [:temperature :room/a 21] stolen))
      (is (= [] (edn/read-string (last (nth other 2))))))))

(deftest tagged-cap-literal-cannot-mint-authority
  (let [runtime (host)
        tagged (invoke runtime (assert-req "#cap \"dataspace\"" 0))
        observed (invoke runtime (observe-req "#cap-ref \"dataspace\"" 0))]
    (is (= :dataspace/tagged-rejected (second (nth tagged 2))))
    (is (= :dataspace/tagged-rejected (second (nth observed 2))))))

(deftest forged-facet-handle-is-rejected
  (let [runtime (host)
        forged (invoke runtime [dataspace/request-type :facet-leave 99])
        asserted (invoke runtime (assert-req "[:temperature :room/a 21]" 7))]
    (is (= :dataspace/unknown-facet (second (nth forged 2))))
    (is (= :dataspace/unknown-facet (second (nth asserted 2))))))

(deftest cap-shaped-map-is-inert-data-not-a-grant
  (let [runtime (host)
        forged-map "{:cap/kind :dataspace/transact :cap/resource \"ds\" :cap/provenance []}"
        stored (invoke runtime (assert-req forged-map 0))
        seen (invoke runtime (observe-req "{:cap/kind :dataspace/transact}" 0))]
    (is (= :asserted (second stored)))
    (is (= [{}] (edn/read-string (last (nth seen 2)))))
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"capability denied"
         (invoke (runtime/instantiate
                  (ir/lower (:hir (compiler/check-source
                                   source {:allow #{[:cap/call 24]}}))))
                 (observe-req "{:cap/kind :dataspace/transact}" 0))))))
