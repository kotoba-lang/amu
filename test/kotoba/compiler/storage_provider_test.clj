(ns kotoba.compiler.storage-provider-test
  (:require [clojure.test :refer [deftest is]]
            [kotoba.compiler.core :as compiler]
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
        kir (ir/lower (:hir (compiler/check-source source {:allow #{[:cap/call 12]}})))]
    (runtime/instantiate kir {:allow #{12} :providers {12 provider}})))

(deftest namespace-and-version-stay-on-the-typed-boundary
  (let [seen (atom nil)
        runtime (hosted (fn [request]
                          (reset! seen request)
                          {:tag :written :value (:value request) :version 4}))
        expected [storage/expected-version-type true 3]
        request [storage/request-type :put
                 [storage/put-type :profile/name "Kotoba" expected]]]
    (is (= [storage/result-type :written
            [storage/entry-type :profile/name "Kotoba" 4]]
           ((:invoke runtime) 'transact [request])))
    (is (= {:namespace :example/app-data :operation :put
            :key :profile/name :value "Kotoba" :expected-version 3}
           @seen))))

(deftest missing-and-conflict-are-typed-results
  (let [missing (hosted (fn [_] {:tag :missing}))
        conflict (hosted (fn [_] {:tag :conflict :current-version 7}))]
    (is (= [storage/result-type :missing false]
           ((:invoke missing) 'transact
            [[storage/request-type :get [storage/get-type :profile/name]]])))
    (is (= [storage/result-type :conflict
            [storage/conflict-type :profile/name
             [storage/expected-version-type true 7]]]
           ((:invoke conflict) 'transact
            [[storage/request-type :delete
              [storage/delete-type :profile/name
               [storage/expected-version-type true 3]]]])))))

(deftest backend-exceptions-are-redacted-and-typed
  (let [runtime (hosted (fn [_] (throw (ex-info "secret database URL" {}))))]
    (is (= [storage/result-type :error
            [storage/error-type :storage/transport "storage provider failed" false]]
           ((:invoke runtime) 'transact
            [[storage/request-type :get [storage/get-type :profile/name]]])))))

;; Same reason as object-provider-test: the denial is `:code` in ex-data and
;; the message is prose the provider reworded to "storage request denied".
(defn- denial-code [f]
  (try (f) nil
       (catch clojure.lang.ExceptionInfo e (:code (ex-data e)))))

(deftest invalid-conditional-versions-fail-before-the-transport
  (let [called? (atom false)
        runtime (hosted (fn [_] (reset! called? true)))]
    (is (= :storage/invalid-version
           (denial-code #((:invoke runtime) 'transact
                          [[storage/request-type :delete
                            [storage/delete-type :profile/name
                             [storage/expected-version-type true 0]]]]))))
    (is (false? @called?))))

(deftest missing-grant-denies-before-provider-invoke
  (let [kir (ir/lower (:hir (compiler/check-source
                             source {:allow #{[:cap/call 12]}})))
        runtime (runtime/instantiate kir)
        called? (atom false)]
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"capability denied"
         ((:invoke runtime) 'transact
          [[storage/request-type :get [storage/get-type :profile/name]]])))
    (is (false? @called?))))
