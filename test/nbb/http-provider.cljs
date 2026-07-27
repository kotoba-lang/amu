(ns test.nbb.http-provider
  "W5 family-2 first slice — dual-runtime semantic vectors for `http-v1`
  on `:cljs` with a mock host transport (production cljs transport is still
  intentionally unimplemented; see provider.http-transport).

  Mirrors `test/kotoba/compiler/http_provider_test.clj` (the `:clj` oracle)
  through the same typed `typed-cap-call` + reference-runtime boundary.
  Status and timeout-ms are JS bigint on cljs (canonical i64).

  Run from the repo root: `npm run test-nbb-http-provider`."
  (:require [kotoba.kir.admission :as admission]
            [kotoba.kir.cljs-i64 :as i64]
            [kotoba.compiler.frontend :as frontend]
            [kotoba.kir :as ir]
            [provider.http :as http]
            [kotoba.compiler.reference-runtime :as runtime]))

(def source
  (str "(ns app.http (:export [post]) (:capabilities #{:http/post}))"
       "(defn post [request " (pr-str http/request-type) "] "
       (pr-str http/result-type) " (typed-cap-call :http/post "
       (pr-str http/request-type) " " (pr-str http/result-type) " request))"))

(defn- hosted [transport]
  (let [provider (http/provider {:allowed-origins #{"https://api.example.test"}
                                 :transport transport})
        hir (frontend/analyze source)
        _ (admission/check hir {:allow #{[:cap/call (js/BigInt 4)]}})
        kir (ir/lower hir)]
    (runtime/instantiate kir {:allow #{4} :providers {4 provider}})))

(defn- check [name ok? detail]
  {:name name :ok? (boolean ok?) :detail (when-not ok? detail)})

(defn- post-bounded-ok-case []
  (try
    (let [seen (atom nil)
          runtime (hosted (fn [request]
                            (reset! seen request)
                            {:status 201 :headers {:content-type "application/json"}
                             :body "{\"ok\":true}"}))
          headers [http/header-set-type
                   [[http/header-type :content-type "application/json"]]]
          request [http/request-type "https://api.example.test/v1/items"
                   headers "{\"name\":\"kotoba\"}" (js/BigInt 5000)]
          result ((:invoke runtime) 'post [request])]
      (check "cljs-post-crosses-a-bounded-typed-boundary"
             (and (= [http/result-type :ok
                      [http/response-type (js/BigInt 201)
                       [http/header-set-type
                        [[http/header-type :content-type "application/json"]]]
                       "{\"ok\":true}"]]
                     result)
                  (= "https://api.example.test/v1/items" (:url @seen))
                  (= 5000 (:timeout-ms @seen)))
             (pr-str {:result result :seen @seen})))
    (catch :default e
      (check "cljs-post-crosses-a-bounded-typed-boundary" false (.-message e)))))

(defn- destinations-and-timeouts-case []
  (try
    (let [called? (atom false)
          runtime (hosted (fn [_] (reset! called? true) {:status 200 :headers {} :body ""}))
          origin-threw?
          (try
            ((:invoke runtime) 'post
             [[http/request-type "https://other.example.test/path"
               [http/header-set-type []] "" (js/BigInt 1000)]])
            false
            (catch :default e
              (boolean (re-find #"origin is not allowed" (.-message e)))))
          timeout-threw?
          (try
            ((:invoke runtime) 'post
             [[http/request-type "https://api.example.test/path"
               [http/header-set-type []] "" i64/zero]])
            false
            (catch :default e
              (boolean (re-find #"timeout is outside" (.-message e)))))]
      (check "cljs-destinations-and-timeouts-fail-closed"
             (and origin-threw? timeout-threw? (false? @called?))
             (pr-str {:origin-threw? origin-threw? :timeout-threw? timeout-threw?
                      :called? @called?})))
    (catch :default e
      (check "cljs-destinations-and-timeouts-fail-closed" false (.-message e)))))

(defn- transport-error-case []
  (try
    (let [runtime (hosted (fn [_] {:error {:code :http/timeout
                                           :message "deadline exceeded"
                                           :retryable true}}))
          result ((:invoke runtime) 'post
                  [[http/request-type "https://api.example.test/path"
                    [http/header-set-type []] "" (js/BigInt 1000)]])]
      (check "cljs-transport-errors-remain-typed-values"
             (= [http/result-type :error
                 [http/error-type :http/timeout "deadline exceeded" true]]
                result)
             (pr-str result)))
    (catch :default e
      (check "cljs-transport-errors-remain-typed-values" false (.-message e)))))

(defn- transport-exception-case []
  (try
    (let [runtime (hosted (fn [_] (throw (js/Error. "secret host detail"))))
          result ((:invoke runtime) 'post
                  [[http/request-type "https://api.example.test/path"
                    [http/header-set-type []] "" (js/BigInt 1000)]])]
      (check "cljs-host-transport-exceptions-are-redacted-and-typed"
             (= [http/result-type :error
                 [http/error-type :http/transport "transport failed" false]]
                result)
             (pr-str result)))
    (catch :default e
      (check "cljs-host-transport-exceptions-are-redacted-and-typed" false (.-message e)))))

(defn- denial-case []
  (try
    (let [hir (frontend/analyze source)
          _ (admission/check hir {:allow #{[:cap/call (js/BigInt 4)]}})
          kir (ir/lower hir)
          runtime (runtime/instantiate kir)
          denied?
          (try
            ((:invoke runtime) 'post
             [[http/request-type "https://api.example.test/path"
               [http/header-set-type []] "" (js/BigInt 1000)]])
            false
            (catch :default e
              (boolean (re-find #"capability denied" (.-message e)))))]
      (check "cljs-missing-grant-denies-before-provider-invoke"
             denied?
             (pr-str {:denied? denied?})))
    (catch :default e
      (check "cljs-missing-grant-denies-before-provider-invoke" false (.-message e)))))

(let [results [(post-bounded-ok-case)
               (destinations-and-timeouts-case)
               (transport-error-case)
               (transport-exception-case)
               (denial-case)]
      failures (remove :ok? results)]
  (doseq [{:keys [name ok? detail]} results]
    (println (if ok? "PASS" "FAIL") name (or detail "")))
  (println (count results) "cases," (count failures) "failed")
  (when (seq failures) (.exit js/process 1)))
