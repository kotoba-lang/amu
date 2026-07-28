(ns kotoba.compiler.http-provider-test
  (:require [clojure.test :refer [deftest is]]
            [kotoba.compiler.core :as compiler]
            [kotoba.kir :as ir]
            [provider.http :as http]
            [kotoba.kir.value :as value]
            [kotoba.compiler.reference-runtime :as runtime]))

(def source
  (str "(ns app.http (:export [post]) (:capabilities #{:http/post}))"
       "(defn post [request " (pr-str http/request-type) "] "
       (pr-str http/result-type) " (typed-cap-call :http/post "
       (pr-str http/request-type) " " (pr-str http/result-type) " request))"))

(defn- hosted [transport]
  (let [provider (http/provider {:allowed-origins #{"https://api.example.test"}
                                 :transport transport})
        kir (ir/lower (:hir (compiler/check-source source {:allow #{[:cap/call 4]}})))]
    (runtime/instantiate kir {:allow #{4} :providers {4 provider}})))

(deftest post-crosses-a-bounded-typed-boundary
  (let [seen (atom nil)
        runtime (hosted (fn [request]
                          (reset! seen request)
                          {:status 201 :headers {:content-type "application/json"}
                           :body "{\"ok\":true}"}))
        headers [http/header-set-type
                 [[http/header-type :content-type "application/json"]]]
        request [http/request-type "https://api.example.test/v1/items"
                 headers "{\"name\":\"kotoba\"}" 5000]]
    (is (= [http/result-type :ok
            [http/response-type 201
             [http/header-set-type
              [[http/header-type :content-type "application/json"]]]
             "{\"ok\":true}"]]
           ((:invoke runtime) 'post [request])))
    (is (= {:url "https://api.example.test/v1/items"
            :headers {:content-type "application/json"}
            :body "{\"name\":\"kotoba\"}" :timeout-ms 5000}
           @seen))))

(deftest destinations-and-timeouts-fail-closed
  (let [called? (atom false)
        runtime (hosted (fn [_] (reset! called? true)))]
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"origin is not allowed"
         ((:invoke runtime) 'post
          [[http/request-type "https://other.example.test/path"
            [http/header-set-type []] "" 1000]])))
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"timeout is outside"
         ((:invoke runtime) 'post
          [[http/request-type "https://api.example.test/path"
            [http/header-set-type []] "" 0]])))
    (is (false? @called?))))

(deftest transport-errors-remain-typed-values
  (let [runtime (hosted (fn [_] {:error {:code :http/timeout
                                         :message "deadline exceeded"
                                         :retryable true}}))]
    (is (= [http/result-type :error
            [http/error-type :http/timeout "deadline exceeded" true]]
           ((:invoke runtime) 'post
            [[http/request-type "https://api.example.test/path"
              [http/header-set-type []] "" 1000]])))))

(deftest host-transport-exceptions-are-redacted-and-typed
  (let [runtime (hosted (fn [_] (throw (ex-info "secret host detail" {}))))]
    (is (= [http/result-type :error
            [http/error-type :http/transport "transport failed" false]]
           ((:invoke runtime) 'post
            [[http/request-type "https://api.example.test/path"
              [http/header-set-type []] "" 1000]])))))

(deftest missing-grant-denies-before-provider-invoke
  ;; Empty providers / no allow at instantiate: guest still names :http/post,
  ;; but the runtime rejects before transport is reached (same fail-closed
  ;; path as log/clock W5 first-slice denial vectors).
  (let [kir (ir/lower (:hir (compiler/check-source
                             source {:allow #{[:cap/call 4]}})))
        runtime (runtime/instantiate kir)
        called? (atom false)]
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"capability denied"
         ((:invoke runtime) 'post
          [[http/request-type "https://api.example.test/path"
            [http/header-set-type []] "" 1000]])))
    (is (false? @called?))))

(def get-stream-source
  (str "(ns app.http-stream (:export [get-stream]) (:capabilities #{:http/get-stream}))"
       "(defn get-stream [request " (pr-str http/get-stream-request-type) "] "
       (pr-str http/get-stream-result-type) " (typed-cap-call :http/get-stream "
       (pr-str http/get-stream-request-type) " " (pr-str http/get-stream-result-type) " request))"))

(defn- hosted-get-stream [transport]
  (let [provider (http/get-stream-provider {:allowed-origins #{"https://api.example.test"}
                                            :transport transport})
        kir (ir/lower (:hir (compiler/check-source get-stream-source {:allow #{[:cap/call 13]}})))]
    (runtime/instantiate kir {:allow #{13} :providers {13 provider}})))

(deftest get-stream-returns-ready-task-and-reads-bytes
  (let [payload (value/utf8-string->bytes "stream-body")
        seen (atom nil)
        runtime (hosted-get-stream (fn [request]
                                     (reset! seen request)
                                     {:bytes payload}))
        request [http/get-stream-request-type "https://api.example.test/v1/blob"
                 [http/header-set-type []]]
        task ((:invoke runtime) 'get-stream [request])
        polled (value/task-poll task)
        chunk (value/stream-read! (:stream polled) 65536)]
    (is (= {:operation :get-stream
            :url "https://api.example.test/v1/blob"
            :headers {}}
           @seen))
    (is (value/task-value? task))
    (is (= :ready (:state polled)))
    (is (true? (:done? chunk)))
    (is (zero? (value/compare-typed-values :bytes payload (:bytes chunk))))))

(deftest get-stream-origin-denial-and-transport-redaction
  (let [called? (atom false)
        runtime (hosted-get-stream (fn [_] (reset! called? true) {:bytes (byte-array 0)}))]
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"origin is not allowed"
         ((:invoke runtime) 'get-stream
          [[http/get-stream-request-type "https://evil.example.test/x"
            [http/header-set-type []]]])))
    (is (false? @called?)))
  (let [runtime (hosted-get-stream (fn [_] (throw (ex-info "secret" {}))))]
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"http get-stream transport failed"
         ((:invoke runtime) 'get-stream
          [[http/get-stream-request-type "https://api.example.test/x"
            [http/header-set-type []]]])))))

(deftest get-stream-missing-grant-denies
  (let [kir (ir/lower (:hir (compiler/check-source
                             get-stream-source {:allow #{[:cap/call 13]}})))
        runtime (runtime/instantiate kir)]
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"capability denied"
         ((:invoke runtime) 'get-stream
          [[http/get-stream-request-type "https://api.example.test/x"
            [http/header-set-type []]]])))))

(deftest get-stream-pending-then-fulfill-then-read
  "Transport returns {:pending true}; host task-fulfill! then stream-read."
  (let [payload (value/utf8-string->bytes "late-http-body")
        runtime (hosted-get-stream (fn [_] {:pending true}))
        request [http/get-stream-request-type "https://api.example.test/v1/late"
                 [http/header-set-type []]]
        pending ((:invoke runtime) 'get-stream [request])
        polled0 (value/task-poll pending)
        ready (value/task-fulfill! pending payload)
        polled1 (value/task-poll ready)
        chunk (value/stream-read! (:stream polled1) 65536)]
    (is (value/task-value? pending))
    (is (= :pending (:state polled0)))
    (is (nil? (:stream polled0)))
    (is (= :ready (:state polled1)))
    (is (= (:kotoba.task/id pending) (:kotoba.task/id ready)))
    (is (true? (:done? chunk)))
    (is (zero? (value/compare-typed-values :bytes payload (:bytes chunk))))))

(deftest get-stream-multi-chunk-ready-task
  "Transport returns {:chunks [...]}; provider joins into one ready stream."
  (let [a (value/utf8-string->bytes "http-")
        b (value/utf8-string->bytes "chunks")
        joined (value/utf8-string->bytes "http-chunks")
        runtime (hosted-get-stream (fn [_] {:chunks [a b]}))
        request [http/get-stream-request-type "https://api.example.test/v1/chunks"
                 [http/header-set-type []]]
        task ((:invoke runtime) 'get-stream [request])
        polled (value/task-poll task)
        chunk (value/stream-read! (:stream polled) 65536)]
    (is (= :ready (:state polled)))
    (is (true? (:done? chunk)))
    (is (zero? (value/compare-typed-values :bytes joined (:bytes chunk))))))

(deftest get-stream-chunk-queue-yields-discrete-chunks
  "Transport returns {:chunk-queue [...]}; each stream-read! yields one producer chunk."
  (let [a (value/utf8-string->bytes "http-")
        b (value/utf8-string->bytes "queue")
        runtime (hosted-get-stream (fn [_] {:chunk-queue [a b]}))
        request [http/get-stream-request-type "https://api.example.test/v1/queue"
                 [http/header-set-type []]]
        task ((:invoke runtime) 'get-stream [request])
        polled (value/task-poll task)
        c1 (value/stream-read! (:stream polled) 65536)
        c2 (value/stream-read! (:stream polled) 65536)]
    (is (= :ready (:state polled)))
    (is (false? (:done? c1)))
    (is (zero? (value/compare-typed-values :bytes a (:bytes c1))))
    (is (true? (:done? c2)))
    (is (zero? (value/compare-typed-values :bytes b (:bytes c2))))))

(deftest get-stream-open-stream-progressive-push
  "Transport returns {:open-stream true}; host enqueues then closes."
  (let [runtime (hosted-get-stream (fn [_] {:open-stream true}))
        request [http/get-stream-request-type "https://api.example.test/v1/open"
                 [http/header-set-type []]]
        task ((:invoke runtime) 'get-stream [request])
        stream (:stream (value/task-poll task))
        p0 (value/stream-read! stream 65536)
        a (value/utf8-string->bytes "live")
        _ (value/stream-enqueue! stream a)
        c1 (value/stream-read! stream 65536)
        _ (value/stream-close! stream)
        done (value/stream-read! stream 65536)]
    (is (true? (:pending? p0)))
    (is (zero? (value/compare-typed-values :bytes a (:bytes c1))))
    (is (false? (:done? c1)))
    (is (true? (:done? done)))))

(def guest-poll-read-source
  (str "(ns app.http-guest (:export [get-stream-ready get-stream-byte-count]) "
       "(:capabilities #{:http/get-stream}))"
       "(defn get-stream-ready [request " (pr-str http/get-stream-request-type) "] :i64 "
       "(task-ready? (typed-cap-call :http/get-stream "
       (pr-str http/get-stream-request-type) " "
       (pr-str http/get-stream-result-type) " request)))"
       "(defn get-stream-byte-count [request " (pr-str http/get-stream-request-type) "] :i64 "
       "(bytes-task-byte-count (typed-cap-call :http/get-stream "
       (pr-str http/get-stream-request-type) " "
       (pr-str http/get-stream-result-type) " request)))"))

(defn- hosted-guest-poll [transport]
  (let [provider (http/get-stream-provider {:allowed-origins #{"https://api.example.test"}
                                            :transport transport})
        kir (ir/lower (:hir (compiler/check-source
                             guest-poll-read-source {:allow #{[:cap/call 13]}})))]
    (runtime/instantiate kir {:allow #{13} :providers {13 provider}})))

(deftest guest-task-ready?-reports-ready-http-stream
  (let [payload (value/utf8-string->bytes "xyz")
        runtime (hosted-guest-poll (fn [_] {:bytes payload}))
        request [http/get-stream-request-type "https://api.example.test/v1/x"
                 [http/header-set-type []]]]
    (is (= 1 ((:invoke runtime) 'get-stream-ready [request])))))

(deftest guest-bytes-task-byte-count-http-without-host-poll
  (let [payload (value/utf8-string->bytes "http-body")
        runtime (hosted-guest-poll (fn [_] {:bytes payload}))
        request [http/get-stream-request-type "https://api.example.test/v1/body"
                 [http/header-set-type []]]
        n ((:invoke runtime) 'get-stream-byte-count [request])]
    (is (= 9 n))))
