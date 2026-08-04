(ns kotoba.compiler.value-codec-test
  (:require [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]
            [kotoba.compiler.reference-runtime :as runtime]
            [kotoba.compiler.value-codec :as codec]
            [kotoba.kir :as ir]
            [kotoba.kir.value :as kir-value]
            [kotoba.value.codec :as value]))

(deftest org-codec-is-the-only-bounded-value-wire-contract
  (is (= {:format :kotoba.value-boundary/v1
          :codec "kotoba.value.v1"
          :representation :bytes
          :limit-authority :ability-max-bytes}
         codec/wire-contract))
  (let [value {:actor/id 7 :message ["ready" true]}
        encoded (codec/encode-bounded value 256)]
    (is (= value (codec/decode-bounded encoded 256)))))

(deftest ability-byte-limit-is-checked-before-and-after-the-boundary
  (let [value {:payload (apply str (repeat 64 "x"))}
        encoded (codec/encode-bounded value 256)]
    (testing "encode cannot exceed the declared ability limit"
      (is (thrown-with-msg? clojure.lang.ExceptionInfo #"exceeds ability max-bytes"
                            (codec/encode-bounded value 8))))
    (testing "decode rejects the same payload under a narrower grant"
      (is (thrown-with-msg? clojure.lang.ExceptionInfo #"exceeds ability max-bytes"
                            (codec/decode-bounded encoded 8))))
    (testing "zero, negative, and non-integer limits fail closed"
      (doseq [limit [0 -1 1.5 nil]]
        (is (thrown-with-msg? clojure.lang.ExceptionInfo #"positive max-bytes"
                              (codec/encode-bounded value limit)))))))

(deftest generated-ability-adapter-keeps-physical-wire-out-of-source
  (let [source
        "(ns app.canonical-wire
           (:export [invoke])
           (:capabilities #{:http/post}))
         (defn invoke [request :document] :document
           (http/post request))"
        kir (-> (compiler/check-source source {:allow #{[:cap/call 4]}})
                :hir
                ir/lower)
        seen (atom nil)
        provider
        (codec/ability-provider
         {:request-type :document
          :result-type :document
          :max-bytes 256
          :invoke-wire
          (fn [request-bytes]
            (reset! seen (value/decode-value request-bytes))
            (value/encode-value {:accepted true :request @seen}))})
        host (runtime/instantiate kir {:allow #{4} :providers {4 provider}})
        request {:actor/id 7 :message ["ready" true]}
        runtime-request (kir-value/document-edn-read (pr-str request))
        expected-result
        (kir-value/document-edn-read
         (pr-str {:accepted true :request request}))]
    (is (= {:format :kotoba.ability-wire-adapter/v1
            :source-boundary :typed-ability
            :wire codec/wire-contract
            :types #{:i64 :f64 :string :keyword :symbol :bool :document}
            :provider-shape #{:request-type :result-type :invoke}}
           codec/ability-adapter-contract))
    (is (= expected-result
           ((:invoke host) 'invoke [runtime-request])))
    (is (= request @seen))
    (is (= #{:request-type :result-type :invoke} (set (keys provider))))))

(deftest ability-adapter-is-exact-and-bounded-in-both-directions
  (testing "unknown specification fields cannot smuggle host policy"
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"specification is not exact"
         (codec/ability-provider
          {:request-type :document :result-type :document :max-bytes 32
           :invoke-wire identity :ambient-authority true}))))
  (testing "request encoding and result decoding share the ability limit"
    (let [oversized (apply str (repeat 64 "x"))
          echo (codec/ability-provider
                {:request-type :document :result-type :document :max-bytes 16
                 :invoke-wire identity})
          oversized-result
          (codec/ability-provider
           {:request-type :document :result-type :document :max-bytes 16
            :invoke-wire (fn [_] (value/encode-value {:payload oversized}))})]
      (is (thrown-with-msg? clojure.lang.ExceptionInfo #"exceeds ability max-bytes"
                            ((:invoke echo)
                             (kir-value/document-edn-read
                              (pr-str {:payload oversized})))))
      (is (thrown-with-msg? clojure.lang.ExceptionInfo #"exceeds ability max-bytes"
                            ((:invoke oversized-result) ["null"]))))))

(deftest adapter-rejects-unstandardized-aggregate-wire-shapes
  (is (thrown-with-msg?
       clojure.lang.ExceptionInfo #"does not support this value type"
       (codec/ability-provider
        {:request-type [:record :demo/request [[:body :string]]]
         :result-type :document
         :max-bytes 256
         :invoke-wire identity})))
  (testing "document distinctions cannot collapse into host equality"
    (let [provider (codec/ability-provider
                    {:request-type :document :result-type :document
                     :max-bytes 256 :invoke-wire identity})]
      (is (thrown-with-msg?
           clojure.lang.ExceptionInfo #"(duplicate|ambiguous on the canonical value wire)"
           ((:invoke provider)
            (kir-value/bounded-document!
             ["set" [["i64" 1] ["f64" 1.0]]])))))))
