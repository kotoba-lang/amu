(ns kotoba.compiler.link-frame-provider-test
  "Reference-runtime proof for link/frame (capability id 28,
  resources/kotoba/lang/capability-kits/link-frame-v1.edn). Same method as
  kotoba.compiler.net-datagram-provider-test: lower a KIR-checked guest
  that calls `typed-cap-call :link/frame ...`, instantiate it against
  kotoba.compiler.support.link-frame-provider's provider under
  kotoba.compiler.reference-runtime, and exercise the positive path, the
  interface/ethertype/MAC-allowlist denial (denied BEFORE the transport
  function runs), the payload-bytes limit, and transport-exception
  redaction. The transport here is an injected host function standing in
  for a real AF_PACKET/raw-socket send -- this session did not open a real
  raw Ethernet socket (see the kit's own qualification comment for why:
  no browser or WASI sandbox exposes one)."
  (:require [clojure.test :refer [deftest is]]
            [kotoba.compiler.core :as compiler]
            [kotoba.kir :as ir]
            [kotoba.compiler.support.link-frame-provider :as link-frame]
            [kotoba.kir.value :as value]
            [kotoba.compiler.reference-runtime :as runtime]))

(def source
  (str "(ns app.link-frame (:export [transmit receive]) (:capabilities #{:link/frame}))"
       "(defn transmit [request " (pr-str link-frame/request-type) "] "
       (pr-str link-frame/result-type) " (typed-cap-call :link/frame "
       (pr-str link-frame/request-type) " " (pr-str link-frame/result-type) " request))"
       "(defn receive [request " (pr-str link-frame/request-type) "] "
       (pr-str link-frame/result-type) " (typed-cap-call :link/frame "
       (pr-str link-frame/request-type) " " (pr-str link-frame/result-type) " request))"))

(def goose-ethertype 0x88B8)
(def goose-mac "01:0c:cd:01:00:01")

(defn- hosted [transport]
  (let [provider (link-frame/provider
                  {:allowed-frames #{{:interface "eth0" :ethertype goose-ethertype
                                      :destination-mac goose-mac}}
                   :transport transport})
        kir (ir/lower (:hir (compiler/check-source source {:allow #{[:cap/call 28]}})))]
    (runtime/instantiate kir {:allow #{28} :providers {28 provider}})))

(deftest send-crosses-a-bounded-typed-boundary
  (let [seen (atom nil)
        runtime (hosted (fn [request] (reset! seen request) {:bytes-sent 3}))
        payload (value/utf8-string->bytes "hi!")
        request [link-frame/request-type :send
                 [link-frame/send-request-type "eth0" goose-ethertype goose-mac payload]]]
    (is (= [link-frame/result-type :sent [link-frame/sent-type 3]]
           ((:invoke runtime) 'transmit [request])))
    (is (= :send (:op @seen)))
    (is (= "eth0" (:interface @seen)))
    (is (= goose-ethertype (:ethertype @seen)))
    (is (= goose-mac (:destination-mac @seen)))))

(deftest receive-crosses-a-bounded-typed-boundary
  (let [payload (value/utf8-string->bytes "sv")
        runtime (hosted (fn [_] {:interface "eth0" :source-mac "aa:bb:cc:dd:ee:ff"
                                 :ethertype goose-ethertype :payload payload}))
        request [link-frame/request-type :receive
                 [link-frame/receive-request-type "eth0" goose-ethertype 1500 5000]]]
    (is (= [link-frame/result-type :received
            [link-frame/received-type "eth0" "aa:bb:cc:dd:ee:ff" goose-ethertype payload]]
           ((:invoke runtime) 'receive [request])))))

(deftest frame-not-on-the-allowlist-fails-closed-before-transport
  (let [called? (atom false)
        runtime (hosted (fn [_] (reset! called? true) {:bytes-sent 0}))
        payload (value/utf8-string->bytes "x")]
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"denied"
         ((:invoke runtime) 'transmit
          [[link-frame/request-type :send
            [link-frame/send-request-type "eth1" goose-ethertype goose-mac payload]]])))
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"denied"
         ((:invoke runtime) 'transmit
          [[link-frame/request-type :send
            [link-frame/send-request-type "eth0" 0x0800 goose-mac payload]]])))
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"denied"
         ((:invoke runtime) 'transmit
          [[link-frame/request-type :send
            [link-frame/send-request-type "eth0" goose-ethertype
             "ff:ff:ff:ff:ff:ff" payload]]])))
    (is (false? @called?))))

(deftest malformed-mac-and-ethertype-fail-closed-before-transport
  (let [called? (atom false)
        runtime (hosted (fn [_] (reset! called? true) {:bytes-sent 0}))
        payload (value/utf8-string->bytes "x")]
    (is (thrown? clojure.lang.ExceptionInfo
                 ((:invoke runtime) 'transmit
                  [[link-frame/request-type :send
                    [link-frame/send-request-type "eth0" goose-ethertype
                     "not-a-mac" payload]]])))
    (is (thrown? clojure.lang.ExceptionInfo
                 ((:invoke runtime) 'transmit
                  [[link-frame/request-type :send
                    [link-frame/send-request-type "eth0" 99999 goose-mac payload]]])))
    (is (false? @called?))))

(deftest payload-exceeding-the-kit-limit-fails-closed-before-transport
  (let [called? (atom false)
        runtime (hosted (fn [_] (reset! called? true) {:bytes-sent 0}))
        oversized (byte-array (inc link-frame/max-payload-bytes))]
    (is (thrown? clojure.lang.ExceptionInfo
                 ((:invoke runtime) 'transmit
                  [[link-frame/request-type :send
                    [link-frame/send-request-type "eth0" goose-ethertype
                     goose-mac oversized]]])))
    (is (false? @called?))))

(deftest transport-errors-remain-typed-values
  (let [runtime (hosted (fn [_] {:error {:code :link.frame/no-carrier
                                         :message "interface is down"
                                         :retryable true}}))
        payload (value/utf8-string->bytes "x")]
    (is (= [link-frame/result-type :error
            [link-frame/error-type :link.frame/no-carrier "interface is down" true]]
           ((:invoke runtime) 'transmit
            [[link-frame/request-type :send
              [link-frame/send-request-type "eth0" goose-ethertype goose-mac payload]]])))))

(deftest host-transport-exceptions-are-redacted-and-typed
  (let [runtime (hosted (fn [_] (throw (ex-info "secret NIC detail" {}))))
        payload (value/utf8-string->bytes "x")]
    (is (= [link-frame/result-type :error
            [link-frame/error-type :link.frame/transport
             "link/frame transport failed" false]]
           ((:invoke runtime) 'transmit
            [[link-frame/request-type :send
              [link-frame/send-request-type "eth0" goose-ethertype goose-mac payload]]])))))

(deftest missing-grant-denies-before-provider-invoke
  (let [kir (ir/lower (:hir (compiler/check-source
                             source {:allow #{[:cap/call 28]}})))
        runtime (runtime/instantiate kir)
        called? (atom false)
        payload (value/utf8-string->bytes "x")]
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"capability denied"
         ((:invoke runtime) 'transmit
          [[link-frame/request-type :send
            [link-frame/send-request-type "eth0" goose-ethertype goose-mac payload]]])))
    (is (false? @called?))))
