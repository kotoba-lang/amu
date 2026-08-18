(ns test.nbb.storage-provider
  "W5 family-4 second slice — dual-runtime semantic vectors for `storage-v1`
  on `:cljs` with a mock host transport. Versions are JS bigint (canonical i64).

  Production cljs storage transport remains host-specific (ADR 0071 JVM path).
  Run: `npm run test-nbb-storage-provider`."
  (:require [kotoba.kir.admission :as admission]
            [kotoba.kir.cljs-i64 :as i64]
            [kotoba.sema :as sema]
            [kotoba.kir :as ir]
            [provider.storage :as storage]
            [kotoba.compiler.reference-runtime :as runtime]))

(def source
  (str "(ns app.storage (:export [transact]) (:capabilities #{:storage/transact}))"
       "(defn transact [request " (pr-str storage/request-type) "] "
       (pr-str storage/result-type) " (typed-cap-call :storage/transact "
       (pr-str storage/request-type) " " (pr-str storage/result-type) " request))"))

(defn- hosted [transport]
  (let [provider (storage/provider {:storage-namespace :example/app-data
                                    :transport transport})
        hir (sema/analyze source)
        _ (admission/check hir {:allow #{[:cap/call (js/BigInt 12)]}})
        kir (ir/lower hir)]
    (runtime/instantiate kir {:allow #{12} :providers {12 provider}})))

(defn- check [name ok? detail]
  {:name name :ok? (boolean ok?) :detail (when-not ok? detail)})

(defn- put-boundary-case []
  (try
    (let [seen (atom nil)
          runtime (hosted (fn [request]
                            (reset! seen request)
                            {:tag :written :value (:value request) :version 4}))
          expected [storage/expected-version-type true (js/BigInt 3)]
          request [storage/request-type :put
                   [storage/put-type :profile/name "Kotoba" expected]]
          result ((:invoke runtime) 'transact [request])]
      (check "cljs-namespace-and-version-stay-on-the-typed-boundary"
             (and (= [storage/result-type :written
                      [storage/entry-type :profile/name "Kotoba" (js/BigInt 4)]]
                     result)
                  (= :example/app-data (:namespace @seen))
                  (= :put (:operation @seen))
                  (= 3 (:expected-version @seen)))
             (pr-str {:result result :seen @seen})))
    (catch :default e
      (check "cljs-namespace-and-version-stay-on-the-typed-boundary" false (.-message e)))))

(defn- missing-conflict-case []
  (try
    (let [missing (hosted (fn [_] {:tag :missing}))
          conflict (hosted (fn [_] {:tag :conflict :current-version 7}))
          miss ((:invoke missing) 'transact
                [[storage/request-type :get [storage/get-type :profile/name]]])
          conf ((:invoke conflict) 'transact
                [[storage/request-type :delete
                  [storage/delete-type :profile/name
                   [storage/expected-version-type true (js/BigInt 3)]]]])]
      (check "cljs-missing-and-conflict-are-typed-results"
             (and (= [storage/result-type :missing false] miss)
                  (= [storage/result-type :conflict
                      [storage/conflict-type :profile/name
                       [storage/expected-version-type true (js/BigInt 7)]]]
                     conf))
             (pr-str {:miss miss :conf conf})))
    (catch :default e
      (check "cljs-missing-and-conflict-are-typed-results" false (.-message e)))))

(defn- exception-case []
  (try
    (let [runtime (hosted (fn [_] (throw (js/Error. "secret database URL"))))
          result ((:invoke runtime) 'transact
                  [[storage/request-type :get [storage/get-type :profile/name]]])]
      (check "cljs-backend-exceptions-are-redacted-and-typed"
             (= [storage/result-type :error
                 [storage/error-type :storage/transport "storage provider failed" false]]
                result)
             (pr-str result)))
    (catch :default e
      (check "cljs-backend-exceptions-are-redacted-and-typed" false (.-message e)))))

(defn- invalid-version-case []
  ;; The assertion is the typed denial CODE, not a message substring. Version 0
  ;; is refused twice over: `validate-delete` answers :storage/invalid-version
  ;; in the pure policy, and `expected-version` throws "storage expected
  ;; version is invalid" at the wire boundary behind it. This case used to
  ;; match the second message, so when the pure policy caught it first the
  ;; denial arrived as "storage request denied" and the case failed while the
  ;; property it names -- refused, and the transport never called -- still
  ;; held. A message is not the contract; `{:phase :storage-provider :code
  ;; :storage/invalid-version}` is, and asserting on it also keeps the case
  ;; from passing on some unrelated throw.
  (try
    (let [called? (atom false)
          runtime (hosted (fn [_] (reset! called? true) {:tag :missing}))
          denial
          (try
            ((:invoke runtime) 'transact
             [[storage/request-type :delete
               [storage/delete-type :profile/name
                [storage/expected-version-type true i64/zero]]]])
            nil
            (catch :default e (ex-data e)))]
      (check "cljs-invalid-conditional-versions-fail-before-the-transport"
             (and (= :storage-provider (:phase denial))
                  (= :storage/invalid-version (:code denial))
                  (false? @called?))
             (pr-str {:denial denial :called? @called?})))
    (catch :default e
      (check "cljs-invalid-conditional-versions-fail-before-the-transport" false (.-message e)))))

(defn- denial-case []
  (try
    (let [hir (sema/analyze source)
          _ (admission/check hir {:allow #{[:cap/call (js/BigInt 12)]}})
          kir (ir/lower hir)
          runtime (runtime/instantiate kir)
          denied?
          (try
            ((:invoke runtime) 'transact
             [[storage/request-type :get [storage/get-type :profile/name]]])
            false
            (catch :default e
              (boolean (re-find #"capability denied" (.-message e)))))]
      (check "cljs-missing-grant-denies-before-provider-invoke"
             denied?
             (pr-str {:denied? denied?})))
    (catch :default e
      (check "cljs-missing-grant-denies-before-provider-invoke" false (.-message e)))))

(let [results [(put-boundary-case)
               (missing-conflict-case)
               (exception-case)
               (invalid-version-case)
               (denial-case)]
      failures (remove :ok? results)]
  (doseq [{:keys [name ok? detail]} results]
    (println (if ok? "PASS" "FAIL") name (or detail "")))
  (println (count results) "cases," (count failures) "failed")
  (when (seq failures) (.exit js/process 1)))
