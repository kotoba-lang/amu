(ns value-codec
  (:require [kotoba.compiler.value-codec :as codec]
            [kotoba.kir.value :as kir-value]
            [kotoba.value.codec :as value]))

(def request-data
  {:actor/id "actor-7" :message ["ready" true]})

(def expected-data
  {:accepted true :request request-data})

(def seen (atom nil))

(def provider
  (codec/ability-provider
   {:request-type :document
    :result-type :document
    :max-bytes 256
    :invoke-wire
    (fn [request-bytes]
      (reset! seen (value/decode-value request-bytes))
      (value/encode-value expected-data))}))

(def result
  ((:invoke provider)
   (kir-value/document-edn-read
    "{:actor/id \"actor-7\" :message [\"ready\" true]}")))

(assert (= request-data @seen))
(assert (= (kir-value/document-edn-read
            "{:accepted true :request {:actor/id \"actor-7\" :message [\"ready\" true]}}")
           result))
(assert (= :kotoba.ability-wire-adapter/v2
           (:format codec/ability-adapter-contract)))

(def request-type
  [:record :demo/request
   [[:id :i64]
    [:next [:option :i64]]]])

(def aggregate-seen (atom nil))

(def aggregate-provider
  (codec/ability-provider
   {:request-type [:ref :demo/request]
    :result-type [:result [:ref :demo/request] :string]
    :schemas {:demo/request request-type}
    :max-bytes 512
    :invoke-wire
    (fn [request-bytes]
      (let [wire (value/decode-value request-bytes)]
        (reset! aggregate-seen wire)
        (value/encode-value
         {:kotoba.result/status :ok
          :kotoba.result/value wire})))}))

(def minimum-i64 (js/BigInt "-9223372036854775808"))

(def aggregate-request
  [request-type minimum-i64 [[:option :i64] true (js/BigInt "7")]])

(assert (= [true aggregate-request]
           ((:invoke aggregate-provider) aggregate-request)))
(assert (= :demo/request (:kotoba.record/type @aggregate-seen)))
(assert (= minimum-i64
           (value/int64-value
            (get-in @aggregate-seen [:kotoba.record/fields :id]))))
(assert (= (js/BigInt "7")
           (value/int64-value
            (get-in @aggregate-seen
                    [:kotoba.record/fields :next :kotoba.option/value]))))

(println "canonical schema-directed ability adapter cljs: pass")
