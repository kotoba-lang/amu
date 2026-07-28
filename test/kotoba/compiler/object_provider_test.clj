(ns kotoba.compiler.object-provider-test
  "W5 stream-object dual-runtime — put-block + CAS + get-stream ready/pending/multi-chunk."
  (:require [clojure.test :refer [deftest is]]
            [kotoba.compiler.core :as compiler]
            [kotoba.kir :as ir]
            [provider.object :as object]
            [kotoba.kir.value :as value]
            [kotoba.compiler.reference-runtime :as runtime]))

(def source
  (str "(ns app.object (:export [get-stream put-block compare-and-set-ref]) "
       "(:capabilities #{:object/get-stream :object/put-block :object/compare-and-set-ref}))"
       "(defn get-stream [request " (pr-str object/get-stream-request-type) "] "
       (pr-str object/get-stream-result-type)
       " (typed-cap-call :object/get-stream "
       (pr-str object/get-stream-request-type) " "
       (pr-str object/get-stream-result-type) " request))"
       "(defn put-block [request " (pr-str object/put-block-request-type) "] "
       (pr-str object/put-block-result-type)
       " (typed-cap-call :object/put-block "
       (pr-str object/put-block-request-type) " "
       (pr-str object/put-block-result-type) " request))"
       "(defn compare-and-set-ref [request " (pr-str object/cas-request-type) "] "
       (pr-str object/cas-result-type)
       " (typed-cap-call :object/compare-and-set-ref "
       (pr-str object/cas-request-type) " "
       (pr-str object/cas-result-type) " request))"))

(defn- hosted [transport]
  (let [kit (object/create-providers
             {:allowed-bindings #{:example/blocks :example/refs}
              :transport transport})
        kir (ir/lower (:hir (compiler/check-source
                             source {:allow #{[:cap/call 14] [:cap/call 15] [:cap/call 16]}})))]
    (runtime/instantiate kir {:allow #{14 15 16} :providers (:providers kit)})))

(deftest put-block-crosses-only-the-typed-boundary
  (let [seen (atom nil)
        runtime (hosted (fn [request]
                          (reset! seen request)
                          true))
        payload (value/utf8-string->bytes "payload-bytes")
        request [object/put-block-request-type
                 :example/blocks "sha256:deadbeef" payload]]
    (is (true? ((:invoke runtime) 'put-block [request])))
    (is (= :put-block (:operation @seen)))
    (is (= :example/blocks (:binding @seen)))
    (is (= "sha256:deadbeef" (:digest @seen)))
    (is (value/bytes-value? (:bytes @seen)))
    (is (zero? (value/compare-typed-values :bytes payload (:bytes @seen))))))

(deftest cas-wins-and-loses-are-typed-bools
  (let [won (hosted (fn [_] true))
        lost (hosted (fn [_] false))
        expected [object/expected-etag-type true "etag-1"]
        request [object/cas-request-type
                 :example/refs "main" expected "etag-2"]]
    (is (true? ((:invoke won) 'compare-and-set-ref [request])))
    (is (false? ((:invoke lost) 'compare-and-set-ref [request])))))

(deftest bindings-and-empty-fields-fail-closed
  (let [called? (atom false)
        runtime (hosted (fn [_] (reset! called? true) true))]
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"binding is not allowed"
         ((:invoke runtime) 'put-block
          [[object/put-block-request-type
            :example/other "sha256:x" (value/utf8-string->bytes "p")]])))
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"digest must be non-empty"
         ((:invoke runtime) 'put-block
          [[object/put-block-request-type
            :example/blocks "" (value/utf8-string->bytes "p")]])))
    (is (false? @called?))))

(deftest transport-exceptions-are-redacted
  (let [runtime (hosted (fn [_] (throw (ex-info "secret object URL" {}))))]
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"object provider failed"
         ((:invoke runtime) 'put-block
          [[object/put-block-request-type
            :example/blocks "sha256:x" (value/utf8-string->bytes "p")]])))))

(deftest missing-grant-denies-before-provider-invoke
  (let [kir (ir/lower (:hir (compiler/check-source
                             source {:allow #{[:cap/call 14] [:cap/call 15] [:cap/call 16]}})))
        runtime (runtime/instantiate kir)]
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"capability denied"
         ((:invoke runtime) 'put-block
          [[object/put-block-request-type
            :example/blocks "sha256:x" (value/utf8-string->bytes "p")]])))
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"capability denied"
         ((:invoke runtime) 'compare-and-set-ref
          [[object/cas-request-type
            :example/refs "main"
            [object/expected-etag-type false]
            "etag-2"]])))
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"capability denied"
         ((:invoke runtime) 'get-stream
          [[object/get-stream-request-type :example/blocks "k"]])))))

(deftest get-stream-returns-ready-task-and-reads-bytes
  (let [payload (value/utf8-string->bytes "stream-body")
        seen (atom nil)
        runtime (hosted (fn [request]
                          (reset! seen request)
                          {:bytes payload}))
        request [object/get-stream-request-type :example/blocks "key-1"]
        task ((:invoke runtime) 'get-stream [request])
        polled (value/task-poll task)
        chunk (value/stream-read! (:stream polled) 65536)]
    (is (= {:operation :get-stream :binding :example/blocks :key "key-1"} @seen))
    (is (value/task-value? task))
    (is (= :ready (:state polled)))
    (is (true? (:done? chunk)))
    (is (zero? (value/compare-typed-values :bytes payload (:bytes chunk))))))

(deftest get-stream-binding-denial-and-transport-redaction
  (let [called? (atom false)
        runtime (hosted (fn [_] (reset! called? true) {:bytes (byte-array 0)}))]
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"binding is not allowed"
         ((:invoke runtime) 'get-stream
          [[object/get-stream-request-type :example/other "k"]])))
    (is (false? @called?)))
  (let [runtime (hosted (fn [_] (throw (ex-info "secret object URL" {}))))]
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"object provider failed"
         ((:invoke runtime) 'get-stream
          [[object/get-stream-request-type :example/blocks "k"]])))))

(deftest get-stream-pending-then-fulfill-then-read
  "Transport returns {:pending true}; host task-fulfill! then stream-read."
  (let [payload (value/utf8-string->bytes "late-body")
        runtime (hosted (fn [_] {:pending true}))
        request [object/get-stream-request-type :example/blocks "key-pending"]
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
  (let [a (value/utf8-string->bytes "hel")
        b (value/utf8-string->bytes "lo")
        joined (value/utf8-string->bytes "hello")
        runtime (hosted (fn [_] {:chunks [a b]}))
        request [object/get-stream-request-type :example/blocks "key-chunks"]
        task ((:invoke runtime) 'get-stream [request])
        polled (value/task-poll task)
        chunk (value/stream-read! (:stream polled) 65536)]
    (is (= :ready (:state polled)))
    (is (true? (:done? chunk)))
    (is (zero? (value/compare-typed-values :bytes joined (:bytes chunk))))))

(deftest get-stream-chunk-queue-yields-discrete-chunks
  "Transport returns {:chunk-queue [...]}; each stream-read! yields one producer chunk."
  (let [a (value/utf8-string->bytes "hel")
        b (value/utf8-string->bytes "lo")
        runtime (hosted (fn [_] {:chunk-queue [a b]}))
        request [object/get-stream-request-type :example/blocks "key-queue"]
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
  "Transport returns {:open-stream true}; host enqueues then closes while guest holds task."
  (let [runtime (hosted (fn [_] {:open-stream true}))
        request [object/get-stream-request-type :example/blocks "key-open"]
        task ((:invoke runtime) 'get-stream [request])
        stream (:stream (value/task-poll task))
        p0 (value/stream-read! stream 65536)
        a (value/utf8-string->bytes "prog")
        b (value/utf8-string->bytes "-push")
        _ (value/stream-enqueue! stream a)
        c1 (value/stream-read! stream 65536)
        _ (value/stream-enqueue! stream b)
        c2 (value/stream-read! stream 65536)
        _ (value/stream-close! stream)
        done (value/stream-read! stream 65536)]
    (is (true? (:pending? p0)))
    (is (false? (:done? p0)))
    (is (zero? (value/compare-typed-values :bytes a (:bytes c1))))
    (is (false? (:done? c1)))
    (is (zero? (value/compare-typed-values :bytes b (:bytes c2))))
    (is (false? (:done? c2)))
    (is (true? (:done? done)))))

(def guest-poll-read-source
  "Guest poll/read ops (ADR 0127): task-ready? + bytes-task-byte-count over get-stream."
  (str "(ns app.object-guest (:export [get-stream-ready get-stream-byte-count]) "
       "(:capabilities #{:object/get-stream}))"
       "(defn get-stream-ready [request " (pr-str object/get-stream-request-type) "] :i64 "
       "(task-ready? (typed-cap-call :object/get-stream "
       (pr-str object/get-stream-request-type) " "
       (pr-str object/get-stream-result-type) " request)))"
       "(defn get-stream-byte-count [request " (pr-str object/get-stream-request-type) "] :i64 "
       "(bytes-task-byte-count (typed-cap-call :object/get-stream "
       (pr-str object/get-stream-request-type) " "
       (pr-str object/get-stream-result-type) " request)))"))

(defn- hosted-guest-poll [transport]
  (let [provider (object/get-stream-provider
                  {:allowed-bindings #{:example/blocks}
                   :transport transport})
        kir (ir/lower (:hir (compiler/check-source
                             guest-poll-read-source {:allow #{[:cap/call 14]}})))]
    (runtime/instantiate kir {:allow #{14} :providers {14 provider}})))

(deftest guest-task-ready?-reports-ready-task
  "Guest task-ready? is true (1) for a ready get-stream result."
  (let [payload (value/utf8-string->bytes "abc")
        runtime (hosted-guest-poll (fn [_] {:bytes payload}))
        request [object/get-stream-request-type :example/blocks "k"]]
    (is (= 1 ((:invoke runtime) 'get-stream-ready [request])))))

(deftest guest-bytes-task-byte-count-reads-without-host-poll
  "Guest bytes-task-byte-count drains the stream; host does not call task-poll."
  (let [payload (value/utf8-string->bytes "hello")
        runtime (hosted-guest-poll (fn [_] {:bytes payload}))
        request [object/get-stream-request-type :example/blocks "k"]
        n ((:invoke runtime) 'get-stream-byte-count [request])]
    (is (= 5 n)))
  (let [a (value/utf8-string->bytes "hel")
        b (value/utf8-string->bytes "lo")
        runtime (hosted-guest-poll (fn [_] {:chunk-queue [a b]}))
        request [object/get-stream-request-type :example/blocks "k2"]
        n ((:invoke runtime) 'get-stream-byte-count [request])]
    (is (= 5 n))))

(deftest resource-table-drop-and-guest-consume
  "ADR 0133: host drop and guest bytes-task-byte-count consume fail-closed after."
  (value/resource-table-reset!)
  (let [payload (value/utf8-string->bytes "xy")
        runtime (hosted (fn [_] {:bytes payload}))
        request [object/get-stream-request-type :example/blocks "k"]
        task ((:invoke runtime) 'get-stream [request])]
    (is (true? (value/task-live? task)))
    (value/task-drop! task)
    (is (false? (value/task-live? task)))
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"not live"
                          (value/task-poll task))))
  (value/resource-table-reset!)
  (let [payload (value/utf8-string->bytes "hello")
        runtime (hosted-guest-poll (fn [_] {:bytes payload}))
        request [object/get-stream-request-type :example/blocks "k"]
        n ((:invoke runtime) 'get-stream-byte-count [request])]
    (is (= 5 n))
    ;; A second consume is a new task from a new get-stream; table is clean.
    (is (= 5 ((:invoke runtime) 'get-stream-byte-count [request])))))
