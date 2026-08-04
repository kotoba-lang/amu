(ns kotoba.compiler.value-codec
  "Bounded compiler/provider adapter for the org-owned canonical value codec.

  This is deliberately a host boundary, not new Kotoba source sugar. A typed
  ability chooses its own `max-bytes`, then uses the same `kotoba.value.v1`
  bytes as actor and I/O libraries."
  (:require [kotoba.kir.value :as kir-value]
            [kotoba.value.codec :as value]))

(def wire-contract
  {:format :kotoba.value-boundary/v1
   :codec value/codec-id
   :representation :bytes
   :limit-authority :ability-max-bytes})

(def ability-adapter-contract
  {:format :kotoba.ability-wire-adapter/v1
   :source-boundary :typed-ability
   :wire wire-contract
   :types #{:i64 :f64 :string :keyword :symbol :bool :document}
   :provider-shape #{:request-type :result-type :invoke}})

(defn- reject! [message data]
  (throw (ex-info message (assoc data :phase :value-codec))))

(defn- byte-count [bytes]
  #?(:clj (if (bytes? bytes)
            (alength ^bytes bytes)
            (reject! "canonical value payload is not bytes" {}))
     :cljs (if (or (instance? js/Uint8Array bytes)
                   (instance? js/Int8Array bytes))
             (.-length bytes)
             (reject! "canonical value payload is not bytes" {}))))

(defn- checked-limit [max-bytes]
  (when-not (pos-int? max-bytes)
    (reject! "canonical value boundary requires a positive max-bytes"
             {:max-bytes max-bytes}))
  max-bytes)

(defn encode-bounded
  "Encode VALUE and reject an envelope larger than MAX-BYTES."
  [value max-bytes]
  (let [limit (checked-limit max-bytes)
        encoded (value/encode-value value)
        actual (byte-count encoded)]
    (when (> actual limit)
      (reject! "canonical value payload exceeds ability max-bytes"
               {:codec (:codec wire-contract) :bytes actual :max-bytes limit}))
    encoded))

(defn decode-bounded
  "Decode canonical BYTES only after enforcing the ability's MAX-BYTES."
  [bytes max-bytes]
  (let [limit (checked-limit max-bytes)
        actual (byte-count bytes)]
    (when (> actual limit)
      (reject! "canonical value payload exceeds ability max-bytes"
               {:codec (:codec wire-contract) :bytes actual :max-bytes limit}))
    (value/decode-value bytes)))

(def ^:private direct-wire-types
  #{:i64 :f64 :string :keyword :symbol :bool})

(defn- document->value [document]
  (letfn [(walk [[tag payload :as node]]
            (case tag
              "null" nil
              "bool" payload
              "i64" payload
              "f64" payload
              "string" payload
              "keyword" payload
              "symbol" payload
              "vector" (mapv walk payload)
              "list" (apply list (map walk payload))
              "set" (let [items (mapv walk payload)]
                      (when-not (= (count items) (count (set items)))
                        (reject! "document set is ambiguous on the canonical value wire"
                                 {}))
                      (set items))
              "map" (let [entries (mapv (fn [[k v]] [(walk k) (walk v)]) payload)]
                      (when-not (= (count entries)
                                   (count (set (map first entries))))
                        (reject! "document map keys are ambiguous on the canonical value wire"
                                 {}))
                      (into {} entries))
              (reject! "ability wire adapter found an unknown document node"
                       {:node node})))]
    (walk (kir-value/bounded-document! document))))

(defn- value->document [data]
  (letfn [(walk [item]
            (cond
              (nil? item) ["null"]
              (boolean? item) ["bool" item]
              (integer? item) ["i64" item]
              (number? item) ["f64" item]
              (string? item) ["string" item]
              (keyword? item) ["keyword" item]
              (symbol? item) ["symbol" item]
              (vector? item) ["vector" (mapv walk item)]
              (list? item) ["list" (mapv walk item)]
              (set? item) ["set" (->> item (map walk)
                                      (sort kir-value/document-compare) vec)]
              (map? item) ["map" (->> item
                                      (map (fn [[k v]] [(walk k) (walk v)]))
                                      (sort (fn [[a] [b]]
                                              (kir-value/document-map-key-compare a b)))
                                      vec)]
              :else
              (reject! "ability wire result is outside the document value profile"
                       {:value-type (type item)})))]
    (kir-value/bounded-document! (walk data))))

(defn- wire-value [descriptor item]
  (cond
    (contains? direct-wire-types descriptor) item
    (= :document descriptor) (document->value item)
    :else (reject! "ability wire adapter does not support this value type"
                   {:type descriptor
                    :supported (:types ability-adapter-contract)})))

(defn- runtime-value [descriptor item]
  (cond
    (contains? direct-wire-types descriptor) item
    (= :document descriptor) (value->document item)
    :else (reject! "ability wire adapter does not support this value type"
                   {:type descriptor
                    :supported (:types ability-adapter-contract)})))

(defn ability-provider
  "Build the exact typed-provider map accepted by compiler runtimes.

  Generated host adapters supply a closed ability SPEC and an INVOKE-WIRE
  function from canonical request bytes to canonical result bytes. Kotoba
  source continues to call the semantic ability; physical pointer/length or
  codec preparation never becomes source syntax. Runtime type checks surround
  this adapter, while this layer owns the ability byte limit in both
  directions."
  [{:keys [request-type result-type max-bytes invoke-wire] :as spec}]
  (when-not (= #{:request-type :result-type :max-bytes :invoke-wire}
               (set (keys spec)))
    (reject! "ability wire adapter specification is not exact"
             {:keys (set (keys spec))}))
  (when (or (nil? request-type) (nil? result-type))
    (reject! "ability wire adapter requires request and result types" {}))
  (doseq [descriptor [request-type result-type]]
    (when-not (contains? (:types ability-adapter-contract) descriptor)
      (reject! "ability wire adapter does not support this value type"
               {:type descriptor :supported (:types ability-adapter-contract)})))
  (checked-limit max-bytes)
  (when-not (ifn? invoke-wire)
    (reject! "ability wire adapter requires an invoke-wire function" {}))
  {:request-type request-type
   :result-type result-type
   :invoke (fn [request]
             (let [request-bytes (encode-bounded
                                  (wire-value request-type request) max-bytes)
                   result-bytes (invoke-wire request-bytes)
                   result (decode-bounded result-bytes max-bytes)]
               (runtime-value result-type result)))})
