(ns kotoba.compiler.can-frame-provider-test
  "Reference-runtime proof for can/frame (capability id 29,
  resources/kotoba/lang/capability-kits/can-frame-v1.edn). Same method as
  kotoba.compiler.net-datagram-provider-test and
  kotoba.compiler.link-frame-provider-test: lower a KIR-checked guest that
  calls `typed-cap-call :can/frame ...`, instantiate it against
  kotoba.compiler.support.can-frame-provider's provider under
  kotoba.compiler.reference-runtime, and exercise the positive
  send/receive path, interface-allowlist denial, out-of-range 29-bit and
  11-bit CAN-id rejection, the 8-byte payload bound, and
  transport-exception redaction. The transport is an injected host
  function standing in for a real SocketCAN/vendor-driver send -- this
  session did not open a real CAN bus."
  (:require [clojure.test :refer [deftest is]]
            [kotoba.compiler.core :as compiler]
            [kotoba.kir :as ir]
            [kotoba.compiler.support.can-frame-provider :as can-frame]
            [kotoba.kir.value :as value]
            [kotoba.compiler.reference-runtime :as runtime]))

(def source
  (str "(ns app.can-frame (:export [transmit receive]) (:capabilities #{:can/frame}))"
       "(defn transmit [request " (pr-str can-frame/request-type) "] "
       (pr-str can-frame/result-type) " (typed-cap-call :can/frame "
       (pr-str can-frame/request-type) " " (pr-str can-frame/result-type) " request))"
       "(defn receive [request " (pr-str can-frame/request-type) "] "
       (pr-str can-frame/result-type) " (typed-cap-call :can/frame "
       (pr-str can-frame/request-type) " " (pr-str can-frame/result-type) " request))"))

;; SAE J1939 engine-speed PGN 61444 (0xF004), default priority 3, source
;; address 0 -- an arbitrary but realistic 29-bit extended identifier for
;; the positive-path tests below.
(def j1939-can-id 0x0CF00400)

(defn- hosted [transport]
  (let [provider (can-frame/provider {:allowed-interfaces #{"can0"}
                                      :transport transport})
        kir (ir/lower (:hir (compiler/check-source source {:allow #{[:cap/call 29]}})))]
    (runtime/instantiate kir {:allow #{29} :providers {29 provider}})))

(deftest send-crosses-a-bounded-typed-boundary
  (let [seen (atom nil)
        runtime (hosted (fn [request] (reset! seen request) true))
        payload (value/utf8-string->bytes "12345678")
        request [can-frame/request-type :send
                 [can-frame/send-request-type "can0" j1939-can-id true payload]]]
    (is (= [can-frame/result-type :sent true]
           ((:invoke runtime) 'transmit [request])))
    (is (= :send (:op @seen)))
    (is (= "can0" (:interface @seen)))
    (is (= j1939-can-id (:can-id @seen)))
    (is (true? (:extended @seen)))))

(deftest receive-crosses-a-bounded-typed-boundary
  (let [payload (value/utf8-string->bytes "abcdefgh")
        runtime (hosted (fn [_] {:can-id j1939-can-id :extended true :payload payload}))
        request [can-frame/request-type :receive
                 [can-frame/receive-request-type "can0" 5000]]]
    (is (= [can-frame/result-type :received
            [can-frame/received-type "can0" j1939-can-id true payload]]
           ((:invoke runtime) 'receive [request])))))

(deftest interface-not-on-the-allowlist-fails-closed-before-transport
  (let [called? (atom false)
        runtime (hosted (fn [_] (reset! called? true) true))
        payload (value/utf8-string->bytes "x")]
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"denied"
         ((:invoke runtime) 'transmit
          [[can-frame/request-type :send
            [can-frame/send-request-type "can1" j1939-can-id true payload]]])))
    (is (false? @called?))))

(deftest out-of-range-can-ids-fail-closed-before-transport
  (let [called? (atom false)
        runtime (hosted (fn [_] (reset! called? true) true))
        payload (value/utf8-string->bytes "x")]
    ;; 29-bit extended ceiling is 2^29 - 1 = 536870911.
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"denied"
         ((:invoke runtime) 'transmit
          [[can-frame/request-type :send
            [can-frame/send-request-type "can0"
             (inc can-frame/max-can-id-extended) true payload]]])))
    ;; 11-bit standard ceiling is 2047 -- a value legal when extended but
    ;; not when standard must be rejected for the standard-frame request.
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"denied"
         ((:invoke runtime) 'transmit
          [[can-frame/request-type :send
            [can-frame/send-request-type "can0" j1939-can-id false payload]]])))
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"denied"
         ((:invoke runtime) 'transmit
          [[can-frame/request-type :send
            [can-frame/send-request-type "can0" -1 true payload]]])))
    (is (false? @called?))))

(deftest payload-exceeding-the-8-byte-can-2.0b-limit-fails-closed-before-transport
  (let [called? (atom false)
        runtime (hosted (fn [_] (reset! called? true) true))
        oversized (byte-array (inc can-frame/max-payload-bytes))]
    (is (thrown? clojure.lang.ExceptionInfo
                 ((:invoke runtime) 'transmit
                  [[can-frame/request-type :send
                    [can-frame/send-request-type "can0" j1939-can-id true oversized]]])))
    (is (false? @called?))))

(deftest transport-errors-remain-typed-values
  (let [runtime (hosted (fn [_] {:error {:code :can.frame/bus-off
                                         :message "bus-off state"
                                         :retryable true}}))
        payload (value/utf8-string->bytes "x")]
    (is (= [can-frame/result-type :error
            [can-frame/error-type :can.frame/bus-off "bus-off state" true]]
           ((:invoke runtime) 'transmit
            [[can-frame/request-type :send
              [can-frame/send-request-type "can0" j1939-can-id true payload]]])))))

(deftest host-transport-exceptions-are-redacted-and-typed
  (let [runtime (hosted (fn [_] (throw (ex-info "secret CAN driver detail" {}))))
        payload (value/utf8-string->bytes "x")]
    (is (= [can-frame/result-type :error
            [can-frame/error-type :can.frame/transport
             "can/frame transport failed" false]]
           ((:invoke runtime) 'transmit
            [[can-frame/request-type :send
              [can-frame/send-request-type "can0" j1939-can-id true payload]]])))))

(deftest missing-grant-denies-before-provider-invoke
  (let [kir (ir/lower (:hir (compiler/check-source
                             source {:allow #{[:cap/call 29]}})))
        runtime (runtime/instantiate kir)
        called? (atom false)
        payload (value/utf8-string->bytes "x")]
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"capability denied"
         ((:invoke runtime) 'transmit
          [[can-frame/request-type :send
            [can-frame/send-request-type "can0" j1939-can-id true payload]]])))
    (is (false? @called?))))
