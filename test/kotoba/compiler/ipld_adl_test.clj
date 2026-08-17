(ns kotoba.compiler.ipld-adl-test
  (:require [clojure.test :refer [deftest is]]
            [kotoba.compiler.ipld-adl :as adl])
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
