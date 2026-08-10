(ns test.nbb.ui-provider
  "W5 family-5 first slice — dual-runtime semantic vectors for `ui-v1` on
  `:cljs`. Revisions/node-count/event revision are JS bigint (canonical i64).

  Run: `npm run test-nbb-ui-provider`."
  (:require [kotoba.kir.admission :as admission]
            [kotoba.kir.cljs-i64 :as i64]
            [kotoba.sema :as sema]
            [kotoba.kir :as ir]
            [provider.ui :as ui]
            [kotoba.compiler.reference-runtime :as runtime]))

(def source
  (str "(ns app.ui (:export [commit next-event]) "
       "(:capabilities #{:ui/commit :ui/next-event}))"
       "(defn commit [request " (pr-str ui/commit-request-type) "] "
       (pr-str ui/commit-result-type) " (typed-cap-call :ui/commit "
       (pr-str ui/commit-request-type) " " (pr-str ui/commit-result-type) " request))"
       "(defn next-event [request " (pr-str ui/event-request-type) "] "
       (pr-str ui/event-result-type) " (typed-cap-call :ui/next-event "
       (pr-str ui/event-request-type) " " (pr-str ui/event-result-type) " request))"))

(defn- hosted []
  (let [kit (ui/create-provider)
        hir (sema/analyze source)
        _ (admission/check hir {:allow #{[:cap/call (js/BigInt 9)]
                                         [:cap/call (js/BigInt 10)]}})
        kir (ir/lower hir)]
    {:kit kit
     :runtime (runtime/instantiate kir {:allow #{9 10} :providers (:providers kit)})}))

(defn- check [name ok? detail]
  {:name name :ok? (boolean ok?) :detail (when-not ok? detail)})

(defn- declarative-case []
  (try
    (let [{:keys [kit runtime]} (hosted)
          none [ui/parent-type false]
          node [ui/node-type :view/title none :ui/text "Hello"]
          nodes [ui/node-set-type [node]]
          commit [ui/commit-request-type i64/zero nodes]
          c-result ((:invoke runtime) 'commit [commit])
          snap ((:snapshot kit))
          enq ((:enqueue! kit) :view/title :ui/click "open")
          e1 ((:invoke runtime) 'next-event [[ui/event-request-type i64/zero]])
          e2 ((:invoke runtime) 'next-event [[ui/event-request-type i64/one]])]
      (check "cljs-declarative-view-and-events-cross-only-typed-boundaries"
             (and (= [ui/commit-result-type i64/one i64/one] c-result)
                  (= i64/one (:revision snap))
                  (= [node] (:nodes snap))
                  (= i64/one enq)
                  (= [ui/event-result-type true
                      [ui/event-type i64/one :view/title :ui/click "open"]]
                     e1)
                  (= [ui/event-result-type false] e2))
             (pr-str {:c-result c-result :snap snap :enq enq :e1 e1 :e2 e2})))
    (catch :default e
      (check "cljs-declarative-view-and-events-cross-only-typed-boundaries"
             false (.-message e)))))

(defn- stale-revision-case []
  (try
    (let [{:keys [runtime]} (hosted)
          threw?
          (try
            ((:invoke runtime) 'commit
             [[ui/commit-request-type i64/one [ui/node-set-type []]]])
            false
            (catch :default e
              (boolean (re-find #"revision conflict" (.-message e)))))]
      (check "cljs-stale-view-revisions-fail-closed" threw?
             (pr-str {:threw? threw?})))
    (catch :default e
      (check "cljs-stale-view-revisions-fail-closed" false (.-message e)))))

(defn- node-limit-case []
  (try
    (let [{:keys [kit runtime]} (hosted)
          nodes (mapv (fn [i]
                        [ui/node-type (keyword "n" (str i))
                         [ui/parent-type false] :ui/text "x"])
                      (range (inc ui/max-nodes)))
          threw?
          (try
            ((:invoke runtime) 'commit
             [[ui/commit-request-type i64/zero [ui/node-set-type nodes]]])
            false
            (catch :default e
              (boolean (re-find #"(node limit|typed set)" (.-message e)))))
          snap ((:snapshot kit))]
      (check "cljs-node-limit-fails-before-mutation"
             (and threw? (= i64/zero (:revision snap)))
             (pr-str {:threw? threw? :revision (:revision snap)})))
    (catch :default e
      (check "cljs-node-limit-fails-before-mutation" false (.-message e)))))

(defn- denial-case []
  (try
    (let [hir (sema/analyze source)
          _ (admission/check hir {:allow #{[:cap/call (js/BigInt 9)]
                                           [:cap/call (js/BigInt 10)]}})
          kir (ir/lower hir)
          runtime (runtime/instantiate kir)
          commit-denied?
          (try
            ((:invoke runtime) 'commit
             [[ui/commit-request-type i64/zero [ui/node-set-type []]]])
            false
            (catch :default e
              (boolean (re-find #"capability denied" (.-message e)))))
          event-denied?
          (try
            ((:invoke runtime) 'next-event [[ui/event-request-type i64/zero]])
            false
            (catch :default e
              (boolean (re-find #"capability denied" (.-message e)))))]
      (check "cljs-missing-grant-denies-before-provider-invoke"
             (and commit-denied? event-denied?)
             (pr-str {:commit-denied? commit-denied? :event-denied? event-denied?})))
    (catch :default e
      (check "cljs-missing-grant-denies-before-provider-invoke" false (.-message e)))))

(let [results [(declarative-case)
               (stale-revision-case)
               (node-limit-case)
               (denial-case)]
      failures (remove :ok? results)]
  (doseq [{:keys [name ok? detail]} results]
    (println (if ok? "PASS" "FAIL") name (or detail "")))
  (println (count results) "cases," (count failures) "failed")
  (when (seq failures) (.exit js/process 1)))
