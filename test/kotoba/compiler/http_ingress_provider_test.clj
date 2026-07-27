(ns kotoba.compiler.http-ingress-provider-test
  "W5 family-3 first slice — HTTP ingress accept/reply dual-runtime vectors."
  (:require [clojure.test :refer [deftest is]]
            [kotoba.compiler.core :as compiler]
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
        kir (ir/lower (:hir (compiler/check-source
                             source {:allow #{[:cap/call 17] [:cap/call 18]}})))]
    {:kit kit
     :runtime (runtime/instantiate kir
                                   {:allow #{17 18}
                                    :providers (:providers kit)})}))

(deftest host-injected-request-is-accepted-and-replied
  (let [{:keys [kit runtime]} (hosted)
        _ ((:enqueue! kit) :http/get "/v1/health" {} "")
        accepted ((:invoke runtime) 'accept
                                    [[ingress/accept-request-type 0]])
        reply [ingress/reply-request-type 200
               [ingress/header-set-type
                [[ingress/header-type :content-type "text/plain"]]]
               "ok"]]
    (is (= [ingress/accept-result-type true
            [ingress/incoming-request-type :http/get "/v1/health"
             [ingress/header-set-type []] ""]]
           accepted))
    (is (true? ((:invoke runtime) 'reply [reply])))
    (is (= {:queued 0 :pending? false} ((:snapshot kit))))))

(deftest empty-queue-returns-none
  (let [{:keys [runtime]} (hosted)]
    (is (= [ingress/accept-result-type false]
           ((:invoke runtime) 'accept [[ingress/accept-request-type 0]])))))

(deftest pairing-and-bounds-fail-closed
  (let [{:keys [kit runtime]} (hosted)]
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"reply requires a prior accept"
         ((:invoke runtime) 'reply
          [[ingress/reply-request-type 200
            [ingress/header-set-type []] ""]])))
    ((:enqueue! kit) :http/get "/a" {} "")
    ((:invoke runtime) 'accept [[ingress/accept-request-type 0]])
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"reply before next accept"
         ((:invoke runtime) 'accept [[ingress/accept-request-type 0]])))
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"status is outside"
         ((:invoke runtime) 'reply
          [[ingress/reply-request-type 99
            [ingress/header-set-type []] ""]])))
    (is (true? ((:invoke runtime) 'reply
                                 [[ingress/reply-request-type 204
                                   [ingress/header-set-type []] ""]])))))

(deftest enqueue-bounds-fail-before-guest
  (let [{:keys [kit]} (hosted)]
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"path must be non-empty"
         ((:enqueue! kit) :http/get "" {} "")))
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"queue is full"
         (do ((:enqueue! kit) :http/get "/a" {} "")
             ((:enqueue! kit) :http/get "/b" {} ""))))))

(deftest missing-grant-denies-before-provider-invoke
  (let [kir (ir/lower (:hir (compiler/check-source
                             source {:allow #{[:cap/call 17] [:cap/call 18]}})))
        runtime (runtime/instantiate kir)]
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"capability denied"
         ((:invoke runtime) 'accept [[ingress/accept-request-type 0]])))
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"capability denied"
         ((:invoke runtime) 'reply
          [[ingress/reply-request-type 200
            [ingress/header-set-type []] ""]])))))
