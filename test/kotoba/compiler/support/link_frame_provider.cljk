(ns kotoba.compiler.support.link-frame-provider
  "Reference-runtime provider for `link/frame` (capability id 28, kit
  resources/kotoba/lang/capability-kits/link-frame-v1.edn).

  Repository-local (amu-owned) test-support provider, not the production
  `provider.*` package -- see net_datagram_provider.clj's docstring for the
  full explanation, which applies here unchanged.

  Raw OSI L2 Ethernet frame send/receive, addressed by (interface,
  EtherType, destination MAC) rather than by IP host/port.
  `allowed-frames` is an exact, closed set of
  `{:interface :ethertype :destination-mac}` maps the :send op may target
  (`:destination-mac` omitted from the allowlist entry when a provider
  wants to allow any MAC for a given interface+EtherType -- not exercised
  by this test-support provider, which requires an exact match on all
  three). The transport receives a plain host map keyed by :op and must
  return `{:bytes-sent i64}` for a completed send, `{:interface
  :source-mac :ethertype :payload bytes}` for a completed receive, or
  `{:error {:code :message :retryable}}`."
  (:require [kotoba.kir.value :as value]))

(def capability-id 28)
(def max-payload-bytes 1500)
(def max-timeout-ms 30000)

(def send-request-type
  [:record :kotoba.link.frame/send-request
   [[:interface :string] [:ethertype :i64]
    [:destination-mac :string] [:payload :bytes]]])
(def receive-request-type
  [:record :kotoba.link.frame/receive-request
   [[:interface :string] [:ethertype :i64] [:max-bytes :i64] [:timeout-ms :i64]]])
(def request-type
  [:variant :kotoba.link.frame/request
   [[:send send-request-type] [:receive receive-request-type]]])

(def sent-type [:record :kotoba.link.frame/sent [[:bytes-sent :i64]]])
(def received-type
  [:record :kotoba.link.frame/received
   [[:interface :string] [:source-mac :string] [:ethertype :i64] [:payload :bytes]]])
(def error-type
  [:record :kotoba.link.frame/error
   [[:code :keyword] [:message :string] [:retryable :bool]]])
(def result-type
  [:variant :kotoba.link.frame/result
   [[:sent sent-type] [:received received-type] [:error error-type]]])

(def schemas
  {:kotoba.link.frame/send-request send-request-type
   :kotoba.link.frame/receive-request receive-request-type
   :kotoba.link.frame/request request-type
   :kotoba.link.frame/sent sent-type
   :kotoba.link.frame/received received-type
   :kotoba.link.frame/error error-type
   :kotoba.link.frame/result result-type})

(defn- result [tag payload] [result-type tag payload])

(def ^:private mac-pattern
  #"^[0-9a-f]{2}(:[0-9a-f]{2}){5}$")

(defn- canonical-mac? [mac]
  (and (string? mac) (re-matches mac-pattern mac)))

(defn- ethertype-in-range? [ethertype]
  (and (integer? ethertype) (<= 0 ethertype 65535)))

(defn- timeout-in-range? [timeout-ms]
  (and (integer? timeout-ms) (<= 1 timeout-ms max-timeout-ms)))

(defn- error [code message retryable]
  (value/bounded-keyword! code value/keyword-value-byte-limit)
  (value/bounded-string! message value/string-value-byte-limit)
  (result :error [error-type code message retryable]))

(defn- deny! [code context]
  (throw (ex-info "link/frame request denied"
                  (merge {:phase :link-frame-provider :code code} context))))

(defn- invoke-transport [transport request]
  (try
    (transport request)
    (catch Throwable _
      {:error {:code :link.frame/transport
               :message "link/frame transport failed" :retryable false}})))

(defn provider
  "Creates a raw-L2-Ethernet provider around a host-supplied synchronous
  transport. `allowed-frames` is an exact set of
  `{:interface :ethertype :destination-mac}` maps."
  [{:keys [allowed-frames transport]}]
  (when-not (and (set? allowed-frames)
                 (every? #(and (map? %) (string? (:interface %))
                              (integer? (:ethertype %))
                              (string? (:destination-mac %)))
                        allowed-frames))
    (throw (ex-info "link/frame allowed-frames must be a set of interface/ethertype/mac maps"
                    {:phase :link-frame-provider})))
  (when-not (fn? transport)
    (throw (ex-info "link/frame transport must be a function"
                    {:phase :link-frame-provider})))
  {:request-type request-type
   :result-type result-type
   :invoke
   (fn [[actual-type operation payload]]
     (when-not (= actual-type request-type)
       (throw (ex-info "link/frame request contract mismatch"
                       {:phase :link-frame-provider})))
     (case operation
       :send
       (let [[_ interface ethertype destination-mac bytes] payload]
         (value/bounded-string! interface value/string-value-byte-limit)
         (when-not (ethertype-in-range? ethertype)
           (deny! :link.frame/invalid-ethertype {:ethertype ethertype}))
         (when-not (canonical-mac? destination-mac)
           (deny! :link.frame/invalid-mac {:destination-mac destination-mac}))
         (when-not (contains? allowed-frames
                              {:interface interface :ethertype ethertype
                               :destination-mac destination-mac})
           (deny! :link.frame/frame-not-allowed
                  {:interface interface :ethertype ethertype
                   :destination-mac destination-mac}))
         (value/bounded-bytes! bytes max-payload-bytes)
         (let [reply (invoke-transport transport
                                       {:op :send :interface interface
                                        :ethertype ethertype
                                        :destination-mac destination-mac
                                        :payload bytes})]
           (if-let [{:keys [code message retryable]} (:error reply)]
             (error code message retryable)
             (result :sent [sent-type (:bytes-sent reply)]))))

       :receive
       (let [[_ interface ethertype max-bytes timeout-ms] payload]
         (value/bounded-string! interface value/string-value-byte-limit)
         (when-not (ethertype-in-range? ethertype)
           (deny! :link.frame/invalid-ethertype {:ethertype ethertype}))
         (when (> max-bytes max-payload-bytes)
           (deny! :link.frame/max-bytes-exceeds-limit {:max-bytes max-bytes}))
         (when-not (timeout-in-range? timeout-ms)
           (deny! :link.frame/invalid-timeout {:timeout-ms timeout-ms}))
         (let [reply (invoke-transport transport
                                       {:op :receive :interface interface
                                        :ethertype ethertype
                                        :max-bytes max-bytes :timeout-ms timeout-ms})]
           (if-let [{:keys [code message retryable]} (:error reply)]
             (error code message retryable)
             (let [{:keys [interface source-mac ethertype payload]} reply]
               (value/bounded-bytes! payload max-payload-bytes)
               (result :received
                       [received-type interface source-mac ethertype payload])))))

       (deny! :link.frame/unknown-operation {:operation operation})))})
