(ns test.nbb.http-ingress-provider
  "W5 family-3 first slice — HTTP ingress accept/reply on `:cljs`.
  Status uses JS bigint (canonical i64). Run: `npm run test-nbb-http-ingress-provider`."
  (:require [kotoba.kir.admission :as admission]
            [kotoba.kir.cljs-i64 :as i64]
            [kotoba.sema :as sema]
            [kotoba.kir :as ir]
            [provider.http-ingress :as ingress]
            [kotoba.compiler.reference-runtime :as runtime]))

(def source
  (str "(ns app.http-ingress (:export [accept reply]) "
       "(:capabilities #{:http/accept :http/reply}))"
       "(defn accept [request " (pr-str ingress/accept-request-type) "] "
       (pr-str ingress/accept-result-type)
       " (typed-cap-call :http/accept "
       (pr-str ingress/accept-request-type) " "
       (pr-str ingress/accept-result-type) " request))"
       "(defn reply [request " (pr-str ingress/reply-request-type) "] "
       (pr-str ingress/reply-result-type)
       " (typed-cap-call :http/reply "
       (pr-str ingress/reply-request-type) " "
       (pr-str ingress/reply-result-type) " request))"))

(defn- hosted []
  (let [kit (ingress/create-provider)
        hir (sema/analyze source)
        _ (admission/check hir {:allow #{[:cap/call (js/BigInt 17)]
                                         [:cap/call (js/BigInt 18)]}})
        kir (ir/lower hir)]
    {:kit kit
     :runtime (runtime/instantiate kir
                                   {:allow #{17 18}
                                    :providers (:providers kit)})}))

(defn- check [name ok? detail]
  {:name name :ok? (boolean ok?) :detail (when-not ok? detail)})

(defn- round-trip-case []
  (try
    (let [{:keys [kit runtime]} (hosted)
          _ ((:enqueue! kit) :http/get "/v1/health" {} "")
          accepted ((:invoke runtime) 'accept
                                      [[ingress/accept-request-type i64/zero]])
          ok ((:invoke runtime) 'reply
                                [[ingress/reply-request-type (js/BigInt 200)
                                  [ingress/header-set-type []] "ok"]])]
      (check "cljs-host-injected-request-is-accepted-and-replied"
             (and (= [ingress/accept-result-type true
                      [ingress/incoming-request-type :http/get "/v1/health"
                       [ingress/header-set-type []] ""]]
                     accepted)
                  (true? ok)
                  (= {:queued 0 :pending? false
                      :max-queue-depth ingress/default-max-queue-depth}
                     ((:snapshot kit))))
             (pr-str {:accepted accepted :ok ok :snap ((:snapshot kit))})))
    (catch :default e
      (check "cljs-host-injected-request-is-accepted-and-replied" false (.-message e)))))

(defn- empty-case []
  (try
    (let [{:keys [runtime]} (hosted)
          result ((:invoke runtime) 'accept [[ingress/accept-request-type i64/zero]])]
      (check "cljs-empty-queue-returns-none"
             (= [ingress/accept-result-type false] result)
             (pr-str result)))
    (catch :default e
      (check "cljs-empty-queue-returns-none" false (.-message e)))))

(defn- pairing-case []
  (try
    (let [{:keys [kit runtime]} (hosted)
          bare-reply-threw?
          (try
            ((:invoke runtime) 'reply
             [[ingress/reply-request-type (js/BigInt 200)
               [ingress/header-set-type []] ""]])
            false
            (catch :default e
              (boolean (re-find #"reply requires a prior accept" (.-message e)))))
          _ ((:enqueue! kit) :http/get "/a" {} "")
          _ ((:invoke runtime) 'accept [[ingress/accept-request-type i64/zero]])
          double-accept-threw?
          (try
            ((:invoke runtime) 'accept [[ingress/accept-request-type i64/zero]])
            false
            (catch :default e
              (boolean (re-find #"reply before next accept" (.-message e)))))
          bad-status-threw?
          (try
            ((:invoke runtime) 'reply
             [[ingress/reply-request-type (js/BigInt 99)
               [ingress/header-set-type []] ""]])
            false
            (catch :default e
              (boolean (re-find #"status is outside" (.-message e)))))
          ok ((:invoke runtime) 'reply
                                [[ingress/reply-request-type (js/BigInt 204)
                                  [ingress/header-set-type []] ""]])]
      (check "cljs-pairing-and-bounds-fail-closed"
             (and bare-reply-threw? double-accept-threw? bad-status-threw? (true? ok))
             (pr-str {:bare-reply-threw? bare-reply-threw?
                      :double-accept-threw? double-accept-threw?
                      :bad-status-threw? bad-status-threw? :ok ok})))
    (catch :default e
      (check "cljs-pairing-and-bounds-fail-closed" false (.-message e)))))

(defn- denial-case []
  (try
    (let [hir (sema/analyze source)
          _ (admission/check hir {:allow #{[:cap/call (js/BigInt 17)]
                                           [:cap/call (js/BigInt 18)]}})
          kir (ir/lower hir)
          runtime (runtime/instantiate kir)
          denied?
          (try
            ((:invoke runtime) 'accept [[ingress/accept-request-type i64/zero]])
            false
            (catch :default e
              (boolean (re-find #"capability denied" (.-message e)))))]
      (check "cljs-missing-grant-denies-before-provider-invoke"
             denied?
             (pr-str {:denied? denied?})))
    (catch :default e
      (check "cljs-missing-grant-denies-before-provider-invoke" false (.-message e)))))

(defn- multi-inflight-case []
  (try
    (let [kit (ingress/create-provider {:max-queue-depth 3})
          hir (sema/analyze source)
          _ (admission/check hir {:allow #{[:cap/call (js/BigInt 17)]
                                           [:cap/call (js/BigInt 18)]}})
          kir (ir/lower hir)
          runtime (runtime/instantiate kir
                                       {:allow #{17 18}
                                        :providers (:providers kit)})
          _ ((:enqueue! kit) :http/get "/1" {} "a")
          _ ((:enqueue! kit) :http/get "/2" {} "b")
          a1 ((:invoke runtime) 'accept [[ingress/accept-request-type i64/zero]])
          snap ((:snapshot kit))
          ok ((:invoke runtime) 'reply
                                [[ingress/reply-request-type (js/BigInt 200)
                                  [ingress/header-set-type []] "r1"]])
          a2 ((:invoke runtime) 'accept [[ingress/accept-request-type i64/zero]])]
      (check "cljs-multi-inflight-queue-is-fifo"
             (and (= "/1" (get-in a1 [2 2]))
                  (= 1 (:queued snap))
                  (true? (:pending? snap))
                  (true? ok)
                  (= "/2" (get-in a2 [2 2])))
             (pr-str {:a1 a1 :snap snap :ok ok :a2 a2})))
    (catch :default e
      (check "cljs-multi-inflight-queue-is-fifo" false (.-message e)))))

(let [results [(round-trip-case) (empty-case) (pairing-case) (denial-case)
               (multi-inflight-case)]
      failures (remove :ok? results)]
  (doseq [{:keys [name ok? detail]} results]
    (println (if ok? "PASS" "FAIL") name (or detail "")))
  (println (count results) "cases," (count failures) "failed")
  (when (seq failures) (.exit js/process 1)))
