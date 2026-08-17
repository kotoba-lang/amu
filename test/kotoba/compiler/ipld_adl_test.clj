(ns kotoba.compiler.ipld-adl-test
  (:require [clojure.test :refer [deftest is]]
            [kotoba.compiler.ipld-adl :as adl]
            [kotoba.verifier.signing :as signing])
  (:import (java.nio.charset StandardCharsets)
           (java.nio.file Files)
           (java.nio.file.attribute FileAttribute)))

(defn- fake-runner []
  (let [path (Files/createTempFile "kotoba-ipld-adl-runner-" ".sh"
                                   (make-array FileAttribute 0))
        source (str "#!/bin/sh\n"
                    "cp \"$2\" \"$3\"\n"
                    "printf '%s\\n' '"
                    "{\"format\":\"kotoba.ipld-adl-wasmtime-receipt/v1\","
                    "\"status\":\"ok\","
                    "\"engineId\":\"kotoba.ipld-adl-wasmtime/v1\","
                    "\"engineVersion\":\"47.0.3\","
                    "\"fuelUsed\":7,\"memoryPages\":1,\"outputBytes\":4}'\n")]
    (Files/write path (.getBytes source StandardCharsets/UTF_8)
                 (make-array java.nio.file.OpenOption 0))
    (.setExecutable (.toFile path) true true)
    path))

(deftest adapter-produces-the-closed-io-ipld-response
  (let [runner (fake-runner)]
    (try
      (let [module (byte-array [0 97 115 109 1 0 0 0])
            capability (adl/wasmtime-capability
                        {:runner (str runner) :module-bytes module
                         :module-cid "bafk-test"
                         :operations #{:decode} :timeout-ms 100})
            response ((:invoke capability)
                      {:abi "ipld-adl-wasm-v1" :engine-id adl/engine-id
                       :module-bytes module :module-cid "bafk-test"
                       :operation :decode :input-bytes (byte-array [161 97 97 1])
                       :fuel-limit 20 :max-output-bytes 8 :max-memory-pages 2})]
        (is (= #{:status :engine-id :module-cid :output-bytes
                 :fuel-used :memory-pages}
               (set (keys response))))
        (is (= :ok (:status response)))
        (is (= adl/engine-id (:engine-id response)))
        (is (= 7 (:fuel-used response)))
        (is (= 1 (:memory-pages response)))
        (is (= [161 97 97 1] (mapv #(bit-and 0xff %) (:output-bytes response)))))
      (finally (Files/deleteIfExists runner)))))

(deftest execution-receipt-binds-the-snapshotted-runner-and-measurements
  (let [runner (fake-runner)
        module (byte-array [0 97 115 109 1 0 0 0])
        key (signing/generate-keypair)
        trust {:format :kotoba.trust/v1 :trusted-signers #{(:signer key)}
               :revoked-signers #{} :revoked-artifacts #{}}
        expected-runner (adl/runner-sha256 (str runner))
        runner-policy {:trusted-runner-sha256 #{expected-runner}}
        receipts (atom [])]
    (try
      (let [capability (adl/wasmtime-capability
                        {:runner (str runner) :module-bytes module
                         :module-cid "bafk-test" :operations #{:decode}
                         :timeout-ms 100 :executor-key key
                         :receipt-sink #(swap! receipts conj %)})]
        ;; The capability executes the runner bytes admitted at construction,
        ;; so a later path replacement cannot change the attested artifact.
        (Files/write runner (.getBytes "#!/bin/sh\nexit 99\n" StandardCharsets/UTF_8)
                     (make-array java.nio.file.OpenOption 0))
        ((:invoke capability)
         {:abi "ipld-adl-wasm-v1" :engine-id adl/engine-id
          :module-bytes module :module-cid "bafk-test"
          :operation :decode :input-bytes (byte-array [161 97 97 1])
          :fuel-limit 20 :max-output-bytes 8 :max-memory-pages 2})
        (is (= 1 (count @receipts)))
        (let [receipt (first @receipts)
              verified (adl/verify-execution-receipt! receipt trust runner-policy)]
          (is (:verified? verified))
          (is (= (:runner-sha256 receipt) (:runner-sha256 verified)))
          (is (= :decode (:operation receipt)))
          (is (= 7 (:fuel-used receipt)))
          (is (= 1 (:memory-pages receipt)))
          (is (= 4 (:output-bytes receipt)))
          (is (thrown-with-msg?
               clojure.lang.ExceptionInfo #"execution receipt rejected"
               (adl/verify-execution-receipt!
                (update receipt :fuel-used inc) trust runner-policy)))
          (is (thrown-with-msg?
               clojure.lang.ExceptionInfo #"execution receipt rejected"
               (adl/verify-execution-receipt!
                receipt (assoc trust :revoked-signers #{(:signer key)})
                runner-policy)))
          (is (thrown-with-msg?
               clojure.lang.ExceptionInfo #"execution receipt rejected"
               (adl/verify-execution-receipt!
                receipt trust {:trusted-runner-sha256 #{(apply str (repeat 64 "0"))}})))))
      (finally (Files/deleteIfExists runner)))))
