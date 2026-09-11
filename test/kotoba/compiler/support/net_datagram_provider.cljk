(ns kotoba.compiler.support.net-datagram-provider
  "Reference-runtime provider for `net/datagram` (capability id 27, kit
  resources/kotoba/lang/capability-kits/datagram-v1.edn).

  This is a repository-local (amu-owned) test-support provider, NOT the
  production `provider.*` package (kotoba-lang/provider). That companion
  addition -- a `provider.net-datagram` alongside `provider.http`,
  `provider.storage`, etc. -- is a separate change to that repository and is
  out of scope here. This namespace exists so this repository's own
  reference-runtime tests can exercise the kit's typed boundary end to end
  without depending on that out-of-scope change.

  Connectionless UDP send/receive. `allowed-destinations` is an exact,
  closed set of \"host:port\" strings the :send op may target -- the same
  destination-authority shape http.cljc's `allowed-origins` uses for HTTPS
  origins. The transport receives a plain host map keyed by :op and must
  return `{:bytes-sent i64}` for a completed send, `{:host :port :payload
  bytes}` for a completed receive, or `{:error {:code :message
  :retryable}}`."
  (:require [kotoba.kir.value :as value]))

(def capability-id 27)
(def max-payload-bytes 1472)
(def max-timeout-ms 30000)

(def send-request-type
  [:record :kotoba.net.datagram/send-request
   [[:host :string] [:port :i64] [:payload :bytes] [:timeout-ms :i64]]])
(def receive-request-type
  [:record :kotoba.net.datagram/receive-request
   [[:host :string] [:port :i64] [:max-bytes :i64] [:timeout-ms :i64]]])
(def request-type
  [:variant :kotoba.net.datagram/request
   [[:send send-request-type] [:receive receive-request-type]]])

(def sent-type [:record :kotoba.net.datagram/sent [[:bytes-sent :i64]]])
(def received-type
  [:record :kotoba.net.datagram/received
   [[:host :string] [:port :i64] [:payload :bytes]]])
(def error-type
  [:record :kotoba.net.datagram/error
   [[:code :keyword] [:message :string] [:retryable :bool]]])
(def result-type
  [:variant :kotoba.net.datagram/result
   [[:sent sent-type] [:received received-type] [:error error-type]]])

(def schemas
  {:kotoba.net.datagram/send-request send-request-type
   :kotoba.net.datagram/receive-request receive-request-type
   :kotoba.net.datagram/request request-type
   :kotoba.net.datagram/sent sent-type
   :kotoba.net.datagram/received received-type
   :kotoba.net.datagram/error error-type
   :kotoba.net.datagram/result result-type})

(defn- result [tag payload] [result-type tag payload])

(defn- port-in-range? [port]
  (and (integer? port) (<= 0 port 65535)))

(defn- timeout-in-range? [timeout-ms]
  (and (integer? timeout-ms) (<= 1 timeout-ms max-timeout-ms)))

(defn- error [code message retryable]
  (value/bounded-keyword! code value/keyword-value-byte-limit)
  (value/bounded-string! message value/string-value-byte-limit)
  (result :error [error-type code message retryable]))

(defn- deny! [code context]
  (throw (ex-info "net/datagram request denied"
                  (merge {:phase :net-datagram-provider :code code} context))))

(defn- invoke-transport [transport request]
  (try
    (transport request)
    (catch Throwable _
      {:error {:code :net.datagram/transport
               :message "net/datagram transport failed" :retryable false}})))

(defn provider
  "Creates a UDP provider around a host-supplied synchronous transport.
  `allowed-destinations` is an exact set of \"host:port\" strings."
  [{:keys [allowed-destinations transport]}]
  (when-not (and (set? allowed-destinations) (every? string? allowed-destinations))
    (throw (ex-info "net/datagram allowed-destinations must be a set of strings"
                    {:phase :net-datagram-provider})))
  (when-not (fn? transport)
    (throw (ex-info "net/datagram transport must be a function"
                    {:phase :net-datagram-provider})))
  {:request-type request-type
   :result-type result-type
   :invoke
   (fn [[actual-type operation payload]]
     (when-not (= actual-type request-type)
       (throw (ex-info "net/datagram request contract mismatch"
                       {:phase :net-datagram-provider})))
     (case operation
       :send
       (let [[_ host port bytes timeout-ms] payload
             destination (str host ":" port)]
         (value/bounded-string! host value/string-value-byte-limit)
         (when-not (port-in-range? port)
           (deny! :net.datagram/invalid-port {:port port}))
         (when-not (contains? allowed-destinations destination)
           (deny! :net.datagram/destination-not-allowed {:destination destination}))
         (value/bounded-bytes! bytes max-payload-bytes)
         (when-not (timeout-in-range? timeout-ms)
           (deny! :net.datagram/invalid-timeout {:timeout-ms timeout-ms}))
         (let [reply (invoke-transport transport
                                       {:op :send :host host :port port
                                        :payload bytes :timeout-ms timeout-ms})]
           (if-let [{:keys [code message retryable]} (:error reply)]
             (error code message retryable)
             (result :sent [sent-type (:bytes-sent reply)]))))

       :receive
       (let [[_ host port max-bytes timeout-ms] payload]
         (value/bounded-string! host value/string-value-byte-limit)
         (when-not (port-in-range? port)
           (deny! :net.datagram/invalid-port {:port port}))
         (when (> max-bytes max-payload-bytes)
           (deny! :net.datagram/max-bytes-exceeds-limit {:max-bytes max-bytes}))
         (when-not (timeout-in-range? timeout-ms)
           (deny! :net.datagram/invalid-timeout {:timeout-ms timeout-ms}))
         (let [reply (invoke-transport transport
                                       {:op :receive :host host :port port
                                        :max-bytes max-bytes :timeout-ms timeout-ms})]
           (if-let [{:keys [code message retryable]} (:error reply)]
             (error code message retryable)
             (let [{:keys [host port payload]} reply]
               (value/bounded-bytes! payload max-payload-bytes)
               (result :received [received-type host port payload])))))

       (deny! :net.datagram/unknown-operation {:operation operation})))})
