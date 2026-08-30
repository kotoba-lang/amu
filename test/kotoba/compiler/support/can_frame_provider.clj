(ns kotoba.compiler.support.can-frame-provider
  "Reference-runtime provider for `can/frame` (capability id 29, kit
  resources/kotoba/lang/capability-kits/can-frame-v1.edn).

  Repository-local (amu-owned) test-support provider, not the production
  `provider.*` package -- see net_datagram_provider.clj's docstring for the
  full explanation, which applies here unchanged.

  CAN 2.0B frame send/receive with 29-bit extended identifiers, addressed
  by (interface, CAN arbitration id) on a shared bus rather than by IP
  host/port or EtherType. `allowed-interfaces` is an exact, closed set of
  interface-name strings the :send/:receive ops may use -- CAN has no
  per-destination address to allowlist beyond the bus/interface itself,
  unlike net/datagram (host:port) or link/frame (interface+ethertype+MAC).
  The transport receives a plain host map keyed by :op and must return
  `true` for a completed send, `{:can-id :extended :payload bytes}` for a
  completed receive, or `{:error {:code :message :retryable}}`."
  (:require [kotoba.kir.value :as value]))

(def capability-id 29)
(def max-payload-bytes 8)
(def max-can-id-extended 536870911)
(def max-can-id-standard 2047)
(def max-timeout-ms 30000)

(def send-request-type
  [:record :kotoba.can.frame/send-request
   [[:interface :string] [:can-id :i64] [:extended :bool] [:payload :bytes]]])
(def receive-request-type
  [:record :kotoba.can.frame/receive-request
   [[:interface :string] [:timeout-ms :i64]]])
(def request-type
  [:variant :kotoba.can.frame/request
   [[:send send-request-type] [:receive receive-request-type]]])

(def received-type
  [:record :kotoba.can.frame/received
   [[:interface :string] [:can-id :i64] [:extended :bool] [:payload :bytes]]])
(def error-type
  [:record :kotoba.can.frame/error
   [[:code :keyword] [:message :string] [:retryable :bool]]])
(def result-type
  [:variant :kotoba.can.frame/result
   [[:sent :bool] [:received received-type] [:error error-type]]])

(def schemas
  {:kotoba.can.frame/send-request send-request-type
   :kotoba.can.frame/receive-request receive-request-type
   :kotoba.can.frame/request request-type
   :kotoba.can.frame/received received-type
   :kotoba.can.frame/error error-type
   :kotoba.can.frame/result result-type})

(defn- result [tag payload] [result-type tag payload])

(defn- can-id-in-range? [can-id extended?]
  (and (integer? can-id)
       (<= 0 can-id (if extended? max-can-id-extended max-can-id-standard))))

(defn- timeout-in-range? [timeout-ms]
  (and (integer? timeout-ms) (<= 1 timeout-ms max-timeout-ms)))

(defn- error [code message retryable]
  (value/bounded-keyword! code value/keyword-value-byte-limit)
  (value/bounded-string! message value/string-value-byte-limit)
  (result :error [error-type code message retryable]))

(defn- deny! [code context]
  (throw (ex-info "can/frame request denied"
                  (merge {:phase :can-frame-provider :code code} context))))

(defn- invoke-transport [transport request]
  (try
    (transport request)
    (catch Throwable _
      {:error {:code :can.frame/transport
               :message "can/frame transport failed" :retryable false}})))

(defn provider
  "Creates a raw-CAN-bus provider around a host-supplied synchronous
  transport. `allowed-interfaces` is an exact set of interface-name
  strings (e.g. \"can0\")."
  [{:keys [allowed-interfaces transport]}]
  (when-not (and (set? allowed-interfaces) (every? string? allowed-interfaces))
    (throw (ex-info "can/frame allowed-interfaces must be a set of strings"
                    {:phase :can-frame-provider})))
  (when-not (fn? transport)
    (throw (ex-info "can/frame transport must be a function"
                    {:phase :can-frame-provider})))
  {:request-type request-type
   :result-type result-type
   :invoke
   (fn [[actual-type operation payload]]
     (when-not (= actual-type request-type)
       (throw (ex-info "can/frame request contract mismatch"
                       {:phase :can-frame-provider})))
     (case operation
       :send
       (let [[_ interface can-id extended bytes] payload]
         (value/bounded-string! interface value/string-value-byte-limit)
         (when-not (contains? allowed-interfaces interface)
           (deny! :can.frame/interface-not-allowed {:interface interface}))
         (when-not (can-id-in-range? can-id extended)
           (deny! :can.frame/invalid-can-id {:can-id can-id :extended extended}))
         (value/bounded-bytes! bytes max-payload-bytes)
         (let [reply (invoke-transport transport
                                       {:op :send :interface interface
                                        :can-id can-id :extended extended
                                        :payload bytes})]
           (if-let [{:keys [code message retryable]} (:error reply)]
             (error code message retryable)
             (result :sent true))))

       :receive
       (let [[_ interface timeout-ms] payload]
         (value/bounded-string! interface value/string-value-byte-limit)
         (when-not (contains? allowed-interfaces interface)
           (deny! :can.frame/interface-not-allowed {:interface interface}))
         (when-not (timeout-in-range? timeout-ms)
           (deny! :can.frame/invalid-timeout {:timeout-ms timeout-ms}))
         (let [reply (invoke-transport transport
                                       {:op :receive :interface interface
                                        :timeout-ms timeout-ms})]
           (if-let [{:keys [code message retryable]} (:error reply)]
             (error code message retryable)
             (let [{:keys [can-id extended payload]} reply]
               (when-not (can-id-in-range? can-id extended)
                 (throw (ex-info "can/frame transport returned an invalid can-id"
                                {:phase :can-frame-provider :can-id can-id
                                 :extended extended})))
               (value/bounded-bytes! payload max-payload-bytes)
               (result :received
                       [received-type interface can-id extended payload])))))

       (deny! :can.frame/unknown-operation {:operation operation})))})
