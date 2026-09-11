(ns kotoba.compiler.http-ingress-provider-test
  "W5 family-3 — HTTP ingress accept/reply dual-runtime vectors
  (first slice + multi-inflight queue depth)."
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
    (is (= {:queued 0 :pending? false
            :max-queue-depth ingress/default-max-queue-depth}
           ((:snapshot kit))))))

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
    (dotimes [i ingress/default-max-queue-depth]
      ((:enqueue! kit) :http/get (str "/q" i) {} ""))
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"queue is full"
         ((:enqueue! kit) :http/get "/overflow" {} "")))))

(deftest multi-inflight-queue-is-fifo-and-allows-host-buffering
  (let [kit (ingress/create-provider {:max-queue-depth 3})
        kir (ir/lower (:hir (compiler/check-source
                             source {:allow #{[:cap/call 17] [:cap/call 18]}})))
        runtime (runtime/instantiate kir
                                     {:allow #{17 18}
                                      :providers (:providers kit)})
        reply-ok (fn [body]
                   ((:invoke runtime) 'reply
                    [[ingress/reply-request-type 200
                      [ingress/header-set-type []] body]]))]
    ((:enqueue! kit) :http/get "/1" {} "a")
    ((:enqueue! kit) :http/get "/2" {} "b")
    ((:enqueue! kit) :http/post "/3" {} "c")
    (is (= 3 (:queued ((:snapshot kit)))))
    ;; host may keep buffering path while guest has not accepted yet
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"queue is full"
                          ((:enqueue! kit) :http/get "/4" {} "")))
    (is (= [ingress/accept-result-type true
            [ingress/incoming-request-type :http/get "/1"
             [ingress/header-set-type []] "a"]]
           ((:invoke runtime) 'accept [[ingress/accept-request-type 0]])))
    ;; while pending, remaining queue still holds later requests
    (is (= {:queued 2 :pending? true :max-queue-depth 3}
           ((:snapshot kit))))
    (is (true? (reply-ok "r1")))
    (is (= [ingress/accept-result-type true
            [ingress/incoming-request-type :http/get "/2"
             [ingress/header-set-type []] "b"]]
           ((:invoke runtime) 'accept [[ingress/accept-request-type 0]])))
    (is (true? (reply-ok "r2")))
    (is (= [ingress/accept-result-type true
            [ingress/incoming-request-type :http/post "/3"
             [ingress/header-set-type []] "c"]]
           ((:invoke runtime) 'accept [[ingress/accept-request-type 0]])))
    (is (true? (reply-ok "r3")))
    (is (= [ingress/accept-result-type false]
           ((:invoke runtime) 'accept [[ingress/accept-request-type 0]])))))

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
