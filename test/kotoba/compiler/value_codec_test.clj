(ns kotoba.compiler.value-codec-test
  (:require [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]
            [kotoba.compiler.reference-runtime :as runtime]
            [kotoba.compiler.value-codec :as codec]
            [kotoba.component.wit :as wit]
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
      (is (thrown-with-msg? clojure.lang.ExceptionInfo #"max-bytes-exceeded"
                            (codec/encode-bounded value 8))))
    (testing "decode rejects the same payload under a narrower grant"
      (is (thrown-with-msg? clojure.lang.ExceptionInfo #"max-bytes-exceeded"
                            (codec/decode-bounded encoded 8))))
    (testing "zero, negative, and non-integer limits fail closed"
      (doseq [limit [0 -1 1.5 nil]]
        (is (thrown-with-msg? clojure.lang.ExceptionInfo #"max-bytes-invalid"
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
    (is (= :kotoba.ability-wire-adapter/v2
           (:format codec/ability-adapter-contract)))
    (is (= {:authority :typed-ability-descriptor
            :physical-wire :wit-canonical-abi
            :byte-tunneling false}
           (:component-parity codec/ability-adapter-contract)))
    (is (= expected-result
           ((:invoke host) 'invoke [runtime-request])))
    (is (value/int64? (:actor/id @seen)))
    (is (= 7 (value/int64-value (:actor/id @seen))))
    (is (= (:message request) (:message @seen)))
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
      (is (thrown-with-msg? clojure.lang.ExceptionInfo #"max-bytes-exceeded"
                            ((:invoke echo)
                             (kir-value/document-edn-read
                              (pr-str {:payload oversized})))))
      (is (thrown-with-msg? clojure.lang.ExceptionInfo #"max-bytes-exceeded"
                            ((:invoke oversized-result) ["null"]))))))

(deftest async-ability-completion-is-observable-without-serializing-handles
  (kir-value/resource-table-reset!)
  (let [complete (atom nil)
        seen (atom nil)
        provider
        (codec/async-ability-provider
         {:request-type :document
          :response-type :document
          :max-bytes 512
          :start-wire
          (fn [request-bytes complete-wire!]
            (reset! seen (value/decode-value request-bytes))
            (reset! complete complete-wire!)
            {:status :pending})})
        request (kir-value/document-edn-read "{:job/id 7}")
        task ((:invoke provider) request)]
    (is (= [:task [:stream :bytes]] (:result-type provider)))
    (is (= :pending (:state (kir-value/task-poll task))))
    (is (= (value/int64 7) (:job/id @seen)))
    (@complete (value/encode-value {:status :ready :count (value/int64 2)}))
    (let [{:keys [state stream]} (kir-value/task-poll task)
          chunk (kir-value/stream-read! stream 512)]
      (is (= :ready state))
      (is (true? (:done? chunk)))
      (is (= {:status :ready :count (value/int64 2)}
             (value/decode-value (:bytes chunk)))))))

(deftest async-ability-contract-fails-closed
  (kir-value/resource-table-reset!)
  (testing "completed means the callback has already made the task ready"
    (let [provider
          (codec/async-ability-provider
           {:request-type :document :response-type :document :max-bytes 64
            :start-wire (fn [_ _] {:status :completed})})]
      (is (thrown-with-msg?
           clojure.lang.ExceptionInfo #"does not match task state"
           ((:invoke provider) (kir-value/document-edn-read "nil"))))))
  (testing "pending cannot hide synchronous completion"
    (let [provider
          (codec/async-ability-provider
           {:request-type :document :response-type :document :max-bytes 64
            :start-wire
            (fn [_ complete-wire!]
              (complete-wire! (value/encode-value nil))
              {:status :pending})})]
      (is (thrown-with-msg?
           clojure.lang.ExceptionInfo #"does not match task state"
           ((:invoke provider) (kir-value/document-edn-read "nil"))))))
  (testing "invalid completion bytes do not transition the task"
    (let [complete (atom nil)
          provider
          (codec/async-ability-provider
           {:request-type :document :response-type :document :max-bytes 64
            :start-wire (fn [_ done]
                          (reset! complete done)
                          {:status :pending})})
          task ((:invoke provider) (kir-value/document-edn-read "nil"))]
      (is (thrown? clojure.lang.ExceptionInfo (@complete (byte-array [1 2 3]))))
      (is (= :pending (:state (kir-value/task-poll task)))))))

(deftest schema-directed-aggregates-cross-the-canonical-byte-wire
  (let [choice-type [:variant :demo/choice [[:text :string] [:count :i64]]]
        attempt-type [:result :i64 :string]
        request-type
        [:record :demo/request
         [[:id :i64]
          [:choice [:option choice-type]]
          [:attempts [:list attempt-type]]]]
        error-type [:record :demo/error [[:code :keyword]]]
        result-type [:result [:ref :demo/request] [:ref :demo/error]]
        schemas {:demo/request request-type :demo/error error-type}
        minimum Long/MIN_VALUE
        maximum Long/MAX_VALUE
        request
        [request-type
         minimum
         [[:option choice-type] true [choice-type :count maximum]]
         [[:list attempt-type] [[true minimum] [false "retry"]]]]
        seen (atom nil)
        provider
        (codec/ability-provider
         {:request-type [:ref :demo/request]
          :result-type result-type
          :schemas schemas
          :max-bytes 2048
          :invoke-wire
          (fn [request-bytes]
            (let [wire (value/decode-value request-bytes)]
              (reset! seen wire)
              (value/encode-value
               {:kotoba.result/status :ok
                :kotoba.result/value wire})))})
        result ((:invoke provider) request)
        fields (:kotoba.record/fields @seen)
        choice (:choice fields)
        variant (:kotoba.option/value choice)
        attempts (:attempts fields)]
    (is (= [true request] result))
    (is (= :demo/request (:kotoba.record/type @seen)))
    (is (= #{:id :choice :attempts} (set (keys fields))))
    (is (= minimum (value/int64-value (:id fields))))
    (is (= true (:kotoba.option/present choice)))
    (is (= :demo/choice (:kotoba.variant/type variant)))
    (is (= :count (:kotoba.variant/case variant)))
    (is (= maximum
           (value/int64-value (:kotoba.variant/value variant))))
    (is (list? attempts))
    (is (= [:ok :error] (mapv :kotoba.result/status attempts)))
    (is (= minimum
           (-> attempts first :kotoba.result/value value/int64-value)))
    (is (= "retry" (-> attempts second :kotoba.result/value)))
    (is (= "result<demo-request, demo-error>" (wit/type-text result-type)))))

(deftest aggregate-wire-envelopes-are-exact-and-nominal
  (let [record-type [:record :demo/request [[:id :i64]]]
        good {:kotoba.record/type :demo/request
              :kotoba.record/fields {:id (value/int64 7)}}]
    (is (= [record-type 7]
           (codec/wire-value->runtime record-type good)))
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"nominal identity"
         (codec/wire-value->runtime
          record-type (assoc good :kotoba.record/type :demo/other))))
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"record fields wire envelope is not exact"
         (codec/wire-value->runtime
          record-type (assoc-in good [:kotoba.record/fields :extra] 1))))
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"option wire envelope is not exact"
         (codec/wire-value->runtime
          [:option :i64]
          {:kotoba.option/present false
           :kotoba.option/value (value/int64 0)})))
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"exact int64 wrapper"
         (codec/wire-value->runtime :i64 7)))
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"cannot resolve schema reference"
         (codec/ability-provider
          {:request-type [:ref :demo/missing]
           :result-type :i64 :max-bytes 32 :invoke-wire identity})))
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"not an exact nominal definition"
         (codec/ability-provider
          {:request-type [:ref :demo/request]
           :result-type :i64
           :schemas {:demo/request [:record :demo/other [[:id :i64]]]}
           :max-bytes 32 :invoke-wire identity})))
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"does not support this value type"
         (codec/ability-provider
          {:request-type [:stream :bytes]
           :result-type :i64 :max-bytes 32 :invoke-wire identity}))))
  (testing "document distinctions cannot collapse into host equality"
    (let [provider (codec/ability-provider
                    {:request-type :document :result-type :document
                     :max-bytes 256 :invoke-wire identity})]
      (is (thrown-with-msg?
           clojure.lang.ExceptionInfo #"(duplicate|ambiguous on the canonical value wire)"
           ((:invoke provider)
            (kir-value/bounded-document!
             ["set" [["i64" 1] ["f64" 1.0]]])))))))
