(ns test.nbb.state-provider
  "W5 family-4 first slice — dual-runtime semantic vectors for `state-v1`
  on `:cljs`. Mirrors `test/kotoba/compiler/state_provider_test.clj`.
  Entry versions are JS bigint (canonical i64).

  Run from the repo root: `npm run test-nbb-state-provider`."
  (:require [kotoba.kir.admission :as admission]
            [kotoba.kir.cljs-i64 :as i64]
            [kotoba.compiler.frontend :as frontend]
            [kotoba.kir :as ir]
            [provider.state :as state]
            [kotoba.compiler.reference-runtime :as runtime]))

(def source
  (str "(ns app.state (:export [transact]) (:capabilities #{:state/transact}))"
       "(defn transact [request " (pr-str state/request-type) "] "
       (pr-str state/result-type) " (typed-cap-call :state/transact "
       (pr-str state/request-type) " " (pr-str state/result-type) " request))"))

(defn- host []
  (let [provider (state/provider)
        hir (frontend/analyze source)
        _ (admission/check hir {:allow #{[:cap/call (js/BigInt 8)]}})
        kir (ir/lower hir)]
    (runtime/instantiate kir {:allow #{8} :providers {8 provider}})))

(defn- check [name ok? detail]
  {:name name :ok? (boolean ok?) :detail (when-not ok? detail)})

(defn- round-trip-case []
  (try
    (let [runtime (host)
          invoke #((:invoke runtime) 'transact [%])
          put [state/request-type :put [state/put-type :profile/name "Kotoba"]]
          get [state/request-type :get [state/get-type :profile/name]]
          delete [state/request-type :delete [state/delete-type :profile/name]]
          written (invoke put)
          found (invoke get)
          deleted (invoke delete)
          missing (invoke get)]
      (check "cljs-state-provider-round-trips-versioned-values"
             (and (= :written (second written))
                  (= [state/entry-type :profile/name "Kotoba" (js/BigInt 2)]
                     (nth found 2))
                  (= [state/result-type :deleted true] deleted)
                  (= [state/result-type :missing false] missing))
             (pr-str {:written written :found found :deleted deleted :missing missing})))
    (catch :default e
      (check "cljs-state-provider-round-trips-versioned-values" false (.-message e)))))

(defn- isolation-case []
  (try
    (let [left (host) right (host)
          put [state/request-type :put [state/put-type :scope/key "left"]]
          get [state/request-type :get [state/get-type :scope/key]]]
      ((:invoke left) 'transact [put])
      (check "cljs-state-provider-instances-are-isolated"
             (and (= :found (second ((:invoke left) 'transact [get])))
                  (= :missing (second ((:invoke right) 'transact [get]))))
             "cross-instance leak"))
    (catch :default e
      (check "cljs-state-provider-instances-are-isolated" false (.-message e)))))

(defn- capacity-case []
  (try
    (let [runtime (host)
          invoke #((:invoke runtime) 'transact [%])
          _ (dotimes [i state/max-entries]
              (invoke [state/request-type :put
                       [state/put-type (keyword "k" (str i)) (str "v" i)]]))
          overflow (invoke [state/request-type :put
                            [state/put-type :overflow "nope"]])
          update-existing (invoke [state/request-type :put
                                   [state/put-type (keyword "k" "0") "updated"]])]
      (check "cljs-capacity-exhaustion-returns-typed-error"
             (and (= [state/result-type :error
                      [state/error-type :state/capacity "state entry limit reached"]]
                     overflow)
                  (= :written (second update-existing)))
             (pr-str {:overflow overflow :update update-existing})))
    (catch :default e
      (check "cljs-capacity-exhaustion-returns-typed-error" false (.-message e)))))

(defn- denial-case []
  (try
    (let [hir (frontend/analyze source)
          _ (admission/check hir {:allow #{[:cap/call (js/BigInt 8)]}})
          kir (ir/lower hir)
          runtime (runtime/instantiate kir)
          put-denied?
          (try
            ((:invoke runtime) 'transact
             [[state/request-type :put [state/put-type :profile/name "x"]]])
            false
            (catch :default e
              (boolean (re-find #"capability denied" (.-message e)))))
          get-denied?
          (try
            ((:invoke runtime) 'transact
             [[state/request-type :get [state/get-type :profile/name]]])
            false
            (catch :default e
              (boolean (re-find #"capability denied" (.-message e)))))]
      (check "cljs-missing-grant-denies-before-provider-invoke"
             (and put-denied? get-denied?)
             (pr-str {:put-denied? put-denied? :get-denied? get-denied?})))
    (catch :default e
      (check "cljs-missing-grant-denies-before-provider-invoke" false (.-message e)))))

(let [results [(round-trip-case)
               (isolation-case)
               (capacity-case)
               (denial-case)]
      failures (remove :ok? results)]
  (doseq [{:keys [name ok? detail]} results]
    (println (if ok? "PASS" "FAIL") name (or detail "")))
  (println (count results) "cases," (count failures) "failed")
  (when (seq failures) (.exit js/process 1)))
