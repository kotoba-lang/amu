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
(assert (= :kotoba.ability-wire-adapter/v1
           (:format codec/ability-adapter-contract)))

(println "canonical ability adapter cljs: pass")
