(ns kotoba.compiler.dataspace-provider-test
  "Compiler injects kotoba-lang/provider's dataspace host (ADR-2608154100).

  Guest uses named :dataspace/transact. Assertions are inert documents."
  (:require [clojure.edn :as edn]
            [clojure.test :refer [deftest is]]
            [kotoba.compiler.core :as compiler]
            [kotoba.kir :as ir]
            [kotoba.kir.value :as value]
            [kotoba.compiler.reference-runtime :as runtime]
            [provider.dataspace :as dataspace]))

(def source
  (str "(ns app.dataspace (:export [coord]) (:capabilities #{:dataspace/transact}))"
       "(defn coord [request " (pr-str dataspace/request-type) "] "
       (pr-str dataspace/result-type) " (typed-cap-call :dataspace/transact "
       (pr-str dataspace/request-type) " " (pr-str dataspace/result-type)
       " request))"))

(def surface-source
  (str "(ns app.dataspace.surface "
       "(:export [publish publish-in retract subscribe subscribe-in enter leave]) "
       "(:capabilities #{:dataspace/transact}))"
       "(defn publish [assertion :document] (assert! assertion))"
       "(defn publish-in [assertion :document facet :i64] (assert! assertion facet))"
       "(defn retract [assertion :document facet :i64] (retract! assertion facet))"
       "(defn subscribe [pattern :document] (observe! pattern))"
       "(defn subscribe-in [pattern :document facet :i64] (observe! pattern facet))"
       "(defn enter [] (facet-enter!))"
       "(defn leave [facet :i64] (facet-leave! facet))"))

(defn- host
  ([] (host source))
  ([source-text]
   (let [kir (ir/lower (:hir (compiler/check-source
                              source-text {:allow #{[:cap/call 24]}})))]
     (runtime/instantiate kir {:allow #{24}
                               :providers {24 (dataspace/provider)}}))))

(defn- invoke [runtime request]
  ((:invoke runtime) 'coord [request]))

(defn- invoke-surface [runtime function args]
  ((:invoke runtime) function args))

(defn- edn-doc [form]
  (value/document-edn-read (if (string? form) form (pr-str form))))

(defn- doc-edn [doc]
  (edn/read-string (value/document-edn-print doc)))

(defn- assert-req [edn facet]
  [dataspace/request-type :assert [dataspace/assert-type (edn-doc edn) facet]])

(defn- observe-req [edn facet]
  [dataspace/request-type :observe [dataspace/observe-type (edn-doc edn) facet]])

(defn- matches-bindings [result]
  (doc-edn (nth (nth result 2) 1)))

(defn- matches-notices [result]
  (doc-edn (nth (nth result 2) 2)))

(deftest abi-assertions-are-documents-not-edn-strings
  (is (= :document (second (first (nth dataspace/assert-type 2)))))
  (is (= :document (second (first (nth dataspace/observe-type 2)))))
  (is (= :document (second (second (nth dataspace/matches-type 2))))))

(deftest observe-pattern-binds-and-fires-on-matching-assert
  (let [runtime (host)
        observed (invoke runtime (observe-req "[:temperature :room/a ?t]" 0))
        asserted (invoke runtime (assert-req "[:temperature :room/a 21]" 0))]
    (is (= :matches (second observed)))
    (is (= [] (matches-bindings observed)))
    (is (= [] (matches-notices observed)))
    (is (= :asserted (second asserted)))
    (is (= [{'?t 21}] (doc-edn (last (nth asserted 2)))))
    (let [again (invoke runtime (observe-req "[:temperature :room/a ?t]" 0))]
      (is (= [{'?t 21}] (matches-bindings again)))
      (is (= [{:assertion [:temperature :room/a 21] :bindings {'?t 21}}]
             (matches-notices again))))))

(deftest matching-assert-delivers-document-notice-to-observer
  (let [runtime (host)]
    (invoke runtime (observe-req "[:temperature :room/a ?t]" 0))
    (invoke runtime (assert-req "[:temperature :room/a 21]" 0))
    (let [delivered (invoke runtime (observe-req "[:temperature :room/a ?t]" 0))]
      (is (= [{:assertion [:temperature :room/a 21] :bindings {'?t 21}}]
             (matches-notices delivered)))
      (is (= [] (matches-notices
                 (invoke runtime (observe-req "[:temperature :room/a ?t]" 0))))))))

(deftest native-source-forms-cross-hir-kir-and-provider
  (let [checked (compiler/check-source surface-source
                                       {:allow #{[:cap/call 24]}})
        kir (ir/lower (:hir checked))
        runtime (host surface-source)
        pattern (edn-doc "[:temperature :room/a ?t]")
        assertion (edn-doc "[:temperature :room/a 21]")
        subscribe (->> (get-in checked [:hir :functions])
                       (filter #(= 'subscribe (:name %)))
                       first)
        result-type (nth (:body subscribe) 3)
        matches-case (some #(when (= :matches (first %)) %)
                           (nth result-type 2))]
    (is (= #{[:cap/call 24]} (get-in checked [:hir :effects])))
    (is (= :kotoba.kir/v4 (:format kir)))
    (is (= [[:bindings :document] [:notices :document]]
           (nth (second matches-case) 2))
        "sugar observe! elaborates the provider notices mailbox, not only :matches snapshot")
    (let [empty (invoke-surface runtime 'subscribe [pattern])]
      (is (= [] (matches-bindings empty)))
      (is (= [] (matches-notices empty))
          "empty mailbox when nothing matched"))
    (is (= [{'?t 21}]
           (-> (invoke-surface runtime 'publish [assertion])
               (nth 2) last doc-edn)))
    (let [again (invoke-surface runtime 'subscribe [pattern])]
      (is (= [{'?t 21}] (matches-bindings again)))
      (is (= [{:assertion [:temperature :room/a 21] :bindings {'?t 21}}]
             (matches-notices again))))
    (is (= [] (matches-notices (invoke-surface runtime 'subscribe [pattern])))
        "next observe! drains the mailbox")))

(deftest native-source-forms-cannot-launder-the-dataspace-effect
  (is (thrown-with-msg?
       clojure.lang.ExceptionInfo #"capability policy denies required effects"
       (compiler/check-source surface-source {:allow #{}}))))

(deftest native-facet-forms-clean-up-owned-state
  (let [runtime (host surface-source)
        entered (invoke-surface runtime 'enter [])
        facet (-> entered (nth 2) last)
        assertion (edn-doc "[:presence :room/a :alice]")]
    (is (= :facet (second entered)))
    (is (= :asserted
           (second (invoke-surface runtime 'publish-in [assertion facet]))))
    (is (= :retracted
           (second (invoke-surface runtime 'leave [facet]))))
    (is (= [] (matches-bindings (invoke-surface runtime 'subscribe
                                               [(edn-doc "[:presence :room/a ?who]")]))))))

(deftest sugar-observe-facet-leave-drops-undelivered-mail
  "Observe on a child facet, assert on root, then leave without draining.
  The root assertion survives; the child's undelivered notices do not."
  (let [runtime (host surface-source)
        entered (invoke-surface runtime 'enter [])
        facet (-> entered (nth 2) last)
        pattern (edn-doc "[:temperature :room/a ?t]")
        assertion (edn-doc "[:temperature :room/a 21]")]
    (is (= :facet (second entered)))
    (is (= [] (matches-notices (invoke-surface runtime 'subscribe-in
                                              [pattern facet]))))
    (is (= :asserted (second (invoke-surface runtime 'publish [assertion]))))
    (is (= :retracted (second (invoke-surface runtime 'leave [facet]))))
    (let [remaining (invoke-surface runtime 'subscribe [pattern])]
      (is (= [{'?t 21}] (matches-bindings remaining)))
      (is (= [{:assertion [:temperature :room/a 21] :bindings {'?t 21}}]
             (matches-notices remaining))
          "facet-leave drops the child's mailbox; a new observe! replays the live current-set"))))

(deftest sugar-observe-replays-current-matching-assertions
  (let [runtime (host surface-source)
        pattern (edn-doc "[:temperature :room/a ?t]")
        assertion (edn-doc "[:temperature :room/a 21]")]
    (is (= :asserted (second (invoke-surface runtime 'publish [assertion]))))
    (let [first-obs (invoke-surface runtime 'subscribe [pattern])]
      (is (= [{'?t 21}] (matches-bindings first-obs)))
      (is (= [{:assertion [:temperature :room/a 21] :bindings {'?t 21}}]
             (matches-notices first-obs))
          "observe! after a matching assert delivers current-set :document notices"))
    (is (= [] (matches-notices (invoke-surface runtime 'subscribe [pattern])))
        "current-set replay is not re-enqueued")))

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
      (is (= [] (matches-bindings remaining)))
      (is (= [] (matches-notices remaining))))))

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

(deftest copied-assertion-document-does-not-grant-observe
  (let [left (host)
        right (host)
        assertion (edn-doc "[:temperature :room/a 21]")]
    (invoke left (assert-req "[:temperature :room/a 21]" 0))
    (let [other (invoke right (observe-req assertion 0))]
      (is (= [:temperature :room/a 21] (doc-edn assertion)))
      (is (= [] (matches-bindings other))))))

(deftest non-document-assertion-is-rejected
  (let [runtime (host)]
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"value is not a tagged document node"
         (invoke runtime [dataspace/request-type :assert
                          [dataspace/assert-type "#cap \"dataspace\"" 0]])))
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"value is not a tagged document node"
         (invoke runtime [dataspace/request-type :observe
                          [dataspace/observe-type "#cap-ref \"dataspace\"" 0]])))))

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
    (is (= [{}] (matches-bindings seen)))
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"capability denied"
         (invoke (runtime/instantiate
                  (ir/lower (:hir (compiler/check-source
                                   source {:allow #{[:cap/call 24]}}))))
                 (observe-req "{:cap/kind :dataspace/transact}" 0))))))
