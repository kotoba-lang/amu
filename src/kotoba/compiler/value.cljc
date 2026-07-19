(ns kotoba.compiler.value
  #?(:cljs (:require [kotoba.compiler.cljs-i64 :as i64])))

(def string-literal-byte-limit 4096)
(def string-value-byte-limit 65536)

(defn f64-value? [value]
  #?(:clj (instance? Double value)
     :cljs (number? value)))

(defn f64-to-i64-bits [value]
  (when-not (f64-value? value)
    (throw (ex-info "value is not f64" {:phase :value :value value})))
  #?(:clj (Double/doubleToRawLongBits ^double value)
     :cljs (let [buffer (js/ArrayBuffer. 8)
                 view (js/DataView. buffer)]
             (.setFloat64 view 0 value true)
             (.getBigInt64 view 0 true))))

(defn i64-bits-to-f64 [bits]
  #?(:clj (do
            (when-not (and (integer? bits)
                           (<= Long/MIN_VALUE bits Long/MAX_VALUE))
              (throw (ex-info "f64 bit pattern is not i64" {:phase :value :value bits})))
            (Double/longBitsToDouble (long bits)))
     :cljs (let [buffer (js/ArrayBuffer. 8)
                 view (js/DataView. buffer)]
             (when-not (and (i64/bigint-value? bits) (i64/in-i64-range? bits))
               (throw (ex-info "f64 bit pattern is not i64" {:phase :value :value bits})))
             (.setBigInt64 view 0 bits true)
             (.getFloat64 view 0 true))))

(defn utf8-byte-count! [value]
  (when-not (string? value)
    (throw (ex-info "value is not a string" {:phase :value :value value})))
  (loop [index 0 total 0]
    (if (= index (count value))
      total
      (let [unit #?(:clj (int (.charAt ^String value index))
                    :cljs (.charCodeAt value index))]
        (cond
          (<= unit 0x7f) (recur (inc index) (inc total))
          (<= unit 0x7ff) (recur (inc index) (+ total 2))
          (<= 0xd800 unit 0xdbff)
          (if (< (inc index) (count value))
            (let [next-unit #?(:clj (int (.charAt ^String value (inc index)))
                               :cljs (.charCodeAt value (inc index)))]
              (if (<= 0xdc00 next-unit 0xdfff)
                (recur (+ index 2) (+ total 4))
                (throw (ex-info "string contains an unpaired high surrogate" {:phase :value :index index}))))
            (throw (ex-info "string contains an unpaired high surrogate" {:phase :value :index index})))
          (<= 0xdc00 unit 0xdfff)
          (throw (ex-info "string contains an unpaired low surrogate" {:phase :value :index index}))
          :else (recur (inc index) (+ total 3)))))))

(defn bounded-string! [value limit]
  (let [bytes (utf8-byte-count! value)]
    (when (> bytes limit)
      (throw (ex-info "string exceeds UTF-8 byte limit" {:phase :value :bytes bytes :limit limit})))
    value))
