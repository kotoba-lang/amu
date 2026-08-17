(ns ipld-adl-conformance
  (:require [ipld.schema :as schema]
            [ipld.schema-dsl :as dsl]
            [kotoba.compiler.ipld-adl :as adl]
            [multiformats.core :as mf])
  (:import (java.nio.file Files Paths)))

(defn- ensure! [condition message]
  (when-not condition (throw (ex-info message {:phase :ipld-adl-conformance}))))

(defn -main [runner module-path]
  (let [module (Files/readAllBytes (Paths/get module-path (make-array String 0)))
        module-cid (mf/cidv1-raw module)
        capability (adl/wasmtime-capability
                    {:runner runner :module-bytes module :module-cid module-cid
                     :operations #{:validate-representation :decode :encode
                                   :validate-logical}
                     :timeout-ms 1000})
        compiled (schema/compile-schema
                  (dsl/parse "advanced Identity\ntype Item bytes representation advanced Identity"))
        limits {:max-depth 8 :max-nodes 16
                :adl-capabilities {"Identity" capability}
                :max-adl-fuel 100000 :max-adl-output-nodes 16
                :max-adl-output-bytes 128 :max-adl-module-bytes 1048576
                :max-adl-memory-pages 2 :check-adl-determinism? true}
        value (byte-array [1 2 3])
        decoded (schema/representation->logical! compiled "Item" value limits)
        encoded (schema/logical->representation! compiled "Item" value limits)
        receipts (concat (:adl-receipts decoded) (:adl-receipts encoded))]
    (ensure! (= [1 2 3] (vec (:logical-value decoded))) "ADL decode result mismatch")
    (ensure! (= [1 2 3] (vec (:value encoded))) "ADL encode result mismatch")
    (ensure! (every? #(and (= :wasm (:execution %))
                           (= adl/engine-id (:engine-id %))
                           (= module-cid (:module-cid %))
                           (= 1 (:memory-pages %))
                           (pos? (:fuel %)))
                    receipts)
             "ADL engine receipt mismatch")
    (println "ipld-adl-wasmtime: io-ipld projection and measured receipts passed")
    (shutdown-agents)))
