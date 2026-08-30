(ns kotoba.compiler.net-datagram-provider-test
  "Reference-runtime proof for net/datagram (capability id 27,
  resources/kotoba/lang/capability-kits/datagram-v1.edn). Same method as
  every other reference-kit test in this repository
  (kotoba.compiler.http-provider-test, kotoba.compiler.storage-provider-test,
  ...): lower a KIR-checked guest that calls
  `typed-cap-call :net/datagram <request-type> <result-type> request`,
  instantiate it against kotoba.compiler.support.net-datagram-provider's
  provider under `kotoba.compiler.reference-runtime`, and exercise the
  positive path, the destination/port/timeout/payload-limit denials
  (denied BEFORE the transport function runs), and transport-exception
  redaction.

  `net/datagram` is the highest-priority of the three capabilities this
  kit-set adds, so this file additionally proves the boundary against a
  REAL OS UDP socket (`send-round-trips-over-a-real-loopback-udp-socket`),
  not only an in-memory mock transport -- no other reference-kit test in
  this repository does that."
  (:require [clojure.test :refer [deftest is]]
            [kotoba.compiler.core :as compiler]
            [kotoba.kir :as ir]
            [kotoba.compiler.support.net-datagram-provider :as datagram]
            [kotoba.kir.value :as value]
            [kotoba.compiler.reference-runtime :as runtime])
  (:import (java.net DatagramSocket DatagramPacket InetAddress)))

(def source
  (str "(ns app.datagram (:export [transmit receive]) (:capabilities #{:net/datagram}))"
       "(defn transmit [request " (pr-str datagram/request-type) "] "
       (pr-str datagram/result-type) " (typed-cap-call :net/datagram "
       (pr-str datagram/request-type) " " (pr-str datagram/result-type) " request))"
       "(defn receive [request " (pr-str datagram/request-type) "] "
       (pr-str datagram/result-type) " (typed-cap-call :net/datagram "
       (pr-str datagram/request-type) " " (pr-str datagram/result-type) " request))"))

(defn- hosted [transport]
  (let [provider (datagram/provider {:allowed-destinations #{"127.0.0.1:9999"}
                                     :transport transport})
        kir (ir/lower (:hir (compiler/check-source source {:allow #{[:cap/call 27]}})))]
    (runtime/instantiate kir {:allow #{27} :providers {27 provider}})))

(deftest send-crosses-a-bounded-typed-boundary
  (let [seen (atom nil)
        runtime (hosted (fn [request]
                          (reset! seen request)
                          {:bytes-sent 4}))
        payload (value/utf8-string->bytes "ping")
        request [datagram/request-type :send
                 [datagram/send-request-type "127.0.0.1" 9999 payload 5000]]]
    (is (= [datagram/result-type :sent [datagram/sent-type 4]]
           ((:invoke runtime) 'transmit [request])))
    (is (= :send (:op @seen)))
    (is (= "127.0.0.1" (:host @seen)))
    (is (= 9999 (:port @seen)))
    (is (= 5000 (:timeout-ms @seen)))
    (is (zero? (value/compare-typed-values :bytes payload (:payload @seen))))))

(deftest receive-crosses-a-bounded-typed-boundary
  (let [payload (value/utf8-string->bytes "pong")
        runtime (hosted (fn [_] {:host "127.0.0.1" :port 9999 :payload payload}))
        request [datagram/request-type :receive
                 [datagram/receive-request-type "127.0.0.1" 9999 1472 5000]]]
    (is (= [datagram/result-type :received
            [datagram/received-type "127.0.0.1" 9999 payload]]
           ((:invoke runtime) 'receive [request])))))

(deftest destination-and-port-and-timeout-fail-closed-before-transport
  (let [called? (atom false)
        runtime (hosted (fn [_] (reset! called? true) {:bytes-sent 0}))
        payload (value/utf8-string->bytes "x")]
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"denied"
         ((:invoke runtime) 'transmit
          [[datagram/request-type :send
            [datagram/send-request-type "10.0.0.1" 9999 payload 1000]]])))
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"denied"
         ((:invoke runtime) 'transmit
          [[datagram/request-type :send
            [datagram/send-request-type "127.0.0.1" 70000 payload 1000]]])))
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"denied"
         ((:invoke runtime) 'transmit
          [[datagram/request-type :send
            [datagram/send-request-type "127.0.0.1" 9999 payload 0]]])))
    (is (false? @called?))))

(deftest payload-exceeding-the-kit-limit-fails-closed-before-transport
  (let [called? (atom false)
        runtime (hosted (fn [_] (reset! called? true) {:bytes-sent 0}))
        oversized (byte-array (inc datagram/max-payload-bytes))]
    (is (thrown? clojure.lang.ExceptionInfo
                 ((:invoke runtime) 'transmit
                  [[datagram/request-type :send
                    [datagram/send-request-type "127.0.0.1" 9999 oversized 1000]]])))
    (is (false? @called?))))

(deftest transport-errors-remain-typed-values
  (let [runtime (hosted (fn [_] {:error {:code :net.datagram/timeout
                                         :message "deadline exceeded"
                                         :retryable true}}))
        payload (value/utf8-string->bytes "x")]
    (is (= [datagram/result-type :error
            [datagram/error-type :net.datagram/timeout "deadline exceeded" true]]
           ((:invoke runtime) 'transmit
            [[datagram/request-type :send
              [datagram/send-request-type "127.0.0.1" 9999 payload 1000]]])))))

(deftest host-transport-exceptions-are-redacted-and-typed
  (let [runtime (hosted (fn [_] (throw (ex-info "secret bind detail" {}))))
        payload (value/utf8-string->bytes "x")]
    (is (= [datagram/result-type :error
            [datagram/error-type :net.datagram/transport
             "net/datagram transport failed" false]]
           ((:invoke runtime) 'transmit
            [[datagram/request-type :send
              [datagram/send-request-type "127.0.0.1" 9999 payload 1000]]])))))

(deftest missing-grant-denies-before-provider-invoke
  (let [kir (ir/lower (:hir (compiler/check-source
                             source {:allow #{[:cap/call 27]}})))
        runtime (runtime/instantiate kir)
        called? (atom false)
        payload (value/utf8-string->bytes "x")]
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"capability denied"
         ((:invoke runtime) 'transmit
          [[datagram/request-type :send
            [datagram/send-request-type "127.0.0.1" 9999 payload 1000]]])))
    (is (false? @called?))))

;; ---------------------------------------------------------------------------
;; Real loopback UDP: net/datagram is the highest-priority capability this
;; change adds, so its reference proof goes one step further than every
;; other kit's reference test in this repository -- the transport function
;; wired into the SAME provider used above is backed by a real JVM
;; `java.net.DatagramSocket` bound on 127.0.0.1, not an in-memory mock, and
;; the assertion is that the exact bytes handed to `typed-cap-call` are the
;; exact bytes a real OS socket receives.
;; ---------------------------------------------------------------------------

(defn- real-udp-send-transport [^DatagramSocket socket ^InetAddress address]
  (fn [{:keys [host port payload]}]
    (let [len (alength ^bytes payload)
          packet (DatagramPacket. ^bytes payload len address (int port))]
      (.send socket packet)
      {:bytes-sent len})))

(deftest send-round-trips-over-a-real-loopback-udp-socket
  (let [receiver (DatagramSocket.)
        _ (.setSoTimeout receiver 5000)
        receiver-port (.getLocalPort receiver)
        loopback (InetAddress/getByName "127.0.0.1")
        sender (DatagramSocket.)
        transport (real-udp-send-transport sender loopback)
        provider (datagram/provider
                  {:allowed-destinations #{(str "127.0.0.1:" receiver-port)}
                   :transport transport})
        kir (ir/lower (:hir (compiler/check-source source {:allow #{[:cap/call 27]}})))
        runtime (runtime/instantiate kir {:allow #{27} :providers {27 provider}})
        payload-bytes (value/utf8-string->bytes "hello-over-a-real-udp-socket")
        request [datagram/request-type :send
                 [datagram/send-request-type "127.0.0.1" receiver-port
                  payload-bytes 5000]]]
    (try
      (is (= [datagram/result-type :sent
              [datagram/sent-type (alength ^bytes payload-bytes)]]
             ((:invoke runtime) 'transmit [request])))
      (let [buf (byte-array 4096)
            recv-packet (DatagramPacket. buf (alength buf))]
        (.receive receiver recv-packet)
        (let [received (byte-array (.getLength recv-packet))]
          (System/arraycopy (.getData recv-packet) 0 received 0 (.getLength recv-packet))
          (is (zero? (value/compare-typed-values :bytes payload-bytes received)))
          (is (= "hello-over-a-real-udp-socket" (String. received "UTF-8")))))
      (finally
        (.close sender)
        (.close receiver)))))
