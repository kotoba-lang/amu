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

(defn- refusal
  "What THUNK refused with: the exception's ex-data plus its :message, or nil
  when it did not refuse.

  Cases assert the structured keys where the provider carries one that
  identifies the guard -- :phase plus the operand it rejected -- and the
  message only where it does not. A message is not the contract: measured
  2026-08-18, three cases in this directory matched wording that belonged to a
  guard behind the one that actually fired, and failed while the property in
  their own name still held."
  [thunk]
  (try (thunk) nil (catch :default e (assoc (or (ex-data e) {}) :message (.-message e)))))

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
          denial
          (refusal #((:invoke runtime) 'commit
                     [[ui/commit-request-type i64/one [ui/node-set-type []]]]))]
      (check "cljs-stale-view-revisions-fail-closed"
             ;; The revisions it compared, not the wording -- and the pair is
             ;; worth pinning because the names read the other way round from
             ;; the guest's side: measured 2026-08-18, :expected is the view's
             ;; current revision (0) and :actual is the one the request carried
             ;; (1), not the reverse.
             (and (= :ui-provider (:phase denial))
                  (= i64/zero (:expected denial))
                  (= i64/one (:actual denial)))
             (pr-str {:denial denial})))
    (catch :default e
      (check "cljs-stale-view-revisions-fail-closed" false (.-message e)))))

(defn- node-limit-case []
  (try
    (let [{:keys [kit runtime]} (hosted)
          nodes (mapv (fn [i]
                        [ui/node-type (keyword "n" (str i))
                         [ui/parent-type false] :ui/text "x"])
                      (range (inc ui/max-nodes)))
          denial
          (refusal #((:invoke runtime) 'commit
                     [[ui/commit-request-type i64/zero [ui/node-set-type nodes]]]))
          snap ((:snapshot kit))]
      (check "cljs-node-limit-fails-before-mutation"
             ;; The alternation this replaced -- #"(node limit|typed set)" --
             ;; admitted two wordings because it was not settled which guard
             ;; fires. It is the value codec, not the provider: measured
             ;; 2026-08-18 the refusal is {:phase :value, :limit 32}, and 32 is
             ;; ui/max-nodes, so the bound is asserted from the authority
             ;; rather than from a literal.
             (and (= :value (:phase denial))
                  (= ui/max-nodes (:limit denial))
                  (= i64/zero (:revision snap)))
             (pr-str {:denial denial :revision (:revision snap)})))
    (catch :default e
      (check "cljs-node-limit-fails-before-mutation" false (.-message e)))))

(defn- denial-case []
  (try
    (let [hir (sema/analyze source)
          _ (admission/check hir {:allow #{[:cap/call (js/BigInt 9)]
                                           [:cap/call (js/BigInt 10)]}})
          kir (ir/lower hir)
          runtime (runtime/instantiate kir)
          commit-denial
          (refusal #((:invoke runtime) 'commit
                     [[ui/commit-request-type i64/zero [ui/node-set-type []]]]))
          event-denial
          (refusal #((:invoke runtime) 'next-event
                     [[ui/event-request-type i64/zero]]))]
      (check "cljs-missing-grant-denies-before-provider-invoke"
             ;; WHICH capability each call was denied for: capability-kits/
             ;; ui-v1.edn assigns :ui/commit id 9 and :ui/next-event id 10.
             (and (= :reference-runtime (:phase commit-denial))
                  (= (js/BigInt 9) (:capability commit-denial))
                  (= :reference-runtime (:phase event-denial))
                  (= (js/BigInt 10) (:capability event-denial)))
             (pr-str {:commit commit-denial :event event-denial})))
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
