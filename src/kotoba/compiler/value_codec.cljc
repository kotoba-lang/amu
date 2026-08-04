(ns kotoba.compiler.value-codec
  "Bounded compiler/provider adapter for the org-owned canonical value codec.

  This is deliberately a host boundary, not new Kotoba source sugar. A typed
  ability chooses its own `max-bytes`, then uses the same `kotoba.value.v1`
  bytes as actor and I/O libraries."
  (:require [kotoba.value.codec :as value]))

(def wire-contract
  {:format :kotoba.value-boundary/v1
   :codec value/codec-id
   :representation :bytes
   :limit-authority :ability-max-bytes})

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
