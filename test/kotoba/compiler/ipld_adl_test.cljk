(ns kotoba.compiler.ipld-adl-test
  (:require [clojure.test :refer [deftest is testing]]
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

(defn- runner-emitting
  "A runner that ignores its input and writes exactly ESCAPES."
  [escapes byte-count]
  (let [path (Files/createTempFile "kotoba-ipld-adl-runner-" ".sh"
                                   (make-array FileAttribute 0))
        source (str "#!/bin/sh\n"
                    "printf '" escapes "' > \"$3\"\n"
                    "printf '%s\\n' '"
                    "{\"format\":\"kotoba.ipld-adl-wasmtime-receipt/v1\","
                    "\"status\":\"ok\","
                    "\"engineId\":\"kotoba.ipld-adl-wasmtime/v1\","
                    "\"engineVersion\":\"47.0.3\","
                    "\"fuelUsed\":7,\"memoryPages\":1,\"outputBytes\":"
                    byte-count "}'\n")]
    (Files/write path (.getBytes source StandardCharsets/UTF_8)
                 (make-array java.nio.file.OpenOption 0))
    (.setExecutable (.toFile path) true true)
    path))

(defn- decode-through [runner receipts]
  (let [module (byte-array [0 97 115 109 1 0 0 0])
        capability (adl/wasmtime-capability
                    (cond-> {:runner (str runner) :module-bytes module
                             :module-cid "bafk-test"
                             :operations #{:decode} :timeout-ms 100}
                      receipts (assoc :executor-key (signing/generate-keypair)
                                      :receipt-sink #(swap! receipts conj %))))]
    ((:invoke capability)
     {:abi "ipld-adl-wasm-v1" :engine-id adl/engine-id
      :module-bytes module :module-cid "bafk-test"
      :operation :decode :input-bytes (byte-array [161 97 97 1])
      :fuel-limit 20 :max-output-bytes 8 :max-memory-pages 2})))

(deftest guest-output-must-be-canonical-dag-cbor
  ;; The source grammar is closed over byte strings, so a transform can be
  ;; lowered faithfully and still return bytes the codec would not have
  ;; written. Decoding alone does not separate those cases. These assert at the
  ;; capability, which is where the structured reason exists -- `ipld.schema`
  ;; refuses too, but flattens an ADL's ex-data into its own `:problem` plus a
  ;; `:message`.
  (testing "a canonical node passes"
    (let [runner (runner-emitting "\\101\\005" 2)]
      (try
        (is (= [0x41 0x05] (mapv #(bit-and 0xff %)
                                 (:output-bytes (decode-through runner nil)))))
        (finally (Files/deleteIfExists runner)))))
  (testing "a truncated node is refused as not a node"
    (let [runner (runner-emitting "\\101" 1)]
      (try
        (is (= :adl-output-not-a-node
               (:code (ex-data (try (decode-through runner nil)
                                    (catch clojure.lang.ExceptionInfo e e))))))
        (finally (Files/deleteIfExists runner)))))
  (testing "trailing bytes after a node are refused"
    (let [runner (runner-emitting "\\101\\005\\005" 3)]
      (try
        (is (= :adl-output-not-a-node
               (:code (ex-data (try (decode-through runner nil)
                                    (catch clojure.lang.ExceptionInfo e e))))))
        (finally (Files/deleteIfExists runner)))))
  (testing "a non-canonical encoding decodes cleanly and is still refused"
    ;; 18 05 reads as the integer 5, so decoding alone accepts it. Only
    ;; re-encoding shows the codec would have written 05.
    (let [runner (runner-emitting "\\030\\005" 2)]
      (try
        (let [data (ex-data (try (decode-through runner nil)
                                 (catch clojure.lang.ExceptionInfo e e)))]
          (is (= :adl-output-not-canonical (:code data)))
          (is (= :decode (:operation data)))
          (is (= [2 1] [(:output-bytes data) (:canonical-bytes data)])))
        (finally (Files/deleteIfExists runner))))))

(deftest a-refused-output-is-never-attested
  ;; A receipt says this module produced these bytes. It must not say so about
  ;; bytes the codec refuses, so the check runs before the receipt is signed.
  (let [runner (runner-emitting "\\030\\005" 2)
        receipts (atom [])]
    (try
      (is (thrown? clojure.lang.ExceptionInfo (decode-through runner receipts)))
      (is (empty? @receipts))
      (finally (Files/deleteIfExists runner)))))

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
