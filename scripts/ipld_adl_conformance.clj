(ns ipld-adl-conformance
  (:require [clojure.string :as str]
            [ipld.schema :as schema]
            [ipld.schema-dsl :as dsl]
            [kotoba.compiler.ipld-adl :as adl]
            [kotoba.verifier.signing :as signing]
            [multiformats.core :as mf])
  (:import (java.nio.file Files Paths)))

(defn- ensure! [condition message]
  (when-not condition (throw (ex-info message {:phase :ipld-adl-conformance}))))

(defn- hex->vec [text]
  (mapv #(Integer/parseInt (apply str %) 16) (partition 2 text)))

(defn -main
  "RUNNER MODULE [EXPECTED [VALUE-HEX]].

   EXPECTED is the logical value the ADL should decode to: `empty`, a hex byte
   string, `reject:<text>` to require the roundtrip to refuse the output with
   that text in its reason, or omitted for \"the input value unchanged\".

   The reason rather than a code, because the schema boundary does not pass an
   ADL's ex-data through: it keeps the message under `:message` and reports its
   own `:problem`. The structured code is asserted where it is raised, in
   `kotoba.compiler.ipld-adl-test`. VALUE-HEX is
   the representation fed to the schema, defaulting to 01 02 03. Both are
   parameters rather than constants because a subrange only round-trips
   through the schema when the subrange is itself a DAG-CBOR node, which
   depends on the value."
  [& [runner module-path expected value-hex]]
  (let [module (Files/readAllBytes (Paths/get module-path (make-array String 0)))
        module-cid (mf/cidv1-raw module)
        executor-key (signing/generate-keypair)
        trust {:format :kotoba.trust/v1
               :trusted-signers #{(:signer executor-key)}
               :revoked-signers #{} :revoked-artifacts #{}}
        runner-policy {:trusted-runner-sha256 #{(adl/runner-sha256 runner)}}
        execution-receipts (atom [])
        capability (adl/wasmtime-capability
                    {:runner runner :module-bytes module :module-cid module-cid
                     :operations #{:validate-representation :decode :encode
                                   :validate-logical}
                     :timeout-ms 1000 :executor-key executor-key
                     :receipt-sink #(swap! execution-receipts conj %)})
        compiled (schema/compile-schema
                  (dsl/parse "advanced Identity\ntype Item bytes representation advanced Identity"))
        limits {:max-depth 8 :max-nodes 16
                :adl-capabilities {"Identity" capability}
                :max-adl-fuel 100000 :max-adl-output-nodes 16
                :max-adl-output-bytes 128 :max-adl-module-bytes 1048576
                :max-adl-memory-pages 2 :check-adl-determinism? true}
        reject-reason (when (and (seq expected) (str/starts-with? expected "reject:"))
                        (subs expected (count "reject:")))
        value-bytes (if (seq value-hex) (hex->vec value-hex) [1 2 3])
        value (byte-array value-bytes)
        expected-logical (cond
                           reject-reason nil
                           (= "empty" expected) []
                           (seq expected) (hex->vec expected)
                           :else value-bytes)
        refusal (when reject-reason
                  (let [thrown (try (schema/representation->logical!
                                     compiled "Item" value limits)
                                    nil
                                    (catch clojure.lang.ExceptionInfo error error))
                        data (ex-data thrown)]
                    (ensure! (some? thrown)
                             "ADL output was accepted but should have been refused")
                    ;; The reason has to be the one the roundtrip gives, not
                    ;; merely "something threw": a wrong expectation, a fuel
                    ;; exhaustion and a refused output otherwise look identical
                    ;; from here.
                    (ensure! (= :adl-capability-failed (:problem data))
                             (str "ADL refusal problem mismatch: "
                                  (pr-str (:problem data))))
                    (ensure! (and (string? (:message data))
                                  (str/includes? (:message data) reject-reason))
                             (str "ADL refusal reason mismatch: "
                                  (pr-str (:message data))))
                    (println "ipld-adl-conformance: refused --" (:message data))
                    thrown))
        decoded (when-not reject-reason
                  (schema/representation->logical! compiled "Item" value limits))
        encoded (when-not reject-reason
                  (schema/logical->representation! compiled "Item" value limits))
        receipts (concat (:adl-receipts decoded) (:adl-receipts encoded))]
    (when refusal (System/exit 0))
    (ensure! (= expected-logical (vec (:logical-value decoded)))
             "ADL decode result mismatch")
    (ensure! (= value-bytes (vec (:value encoded))) "ADL encode result mismatch")
    (ensure! (every? #(and (= :wasm (:execution %))
                           (= adl/engine-id (:engine-id %))
                           (= module-cid (:module-cid %))
                           (<= 1 (:memory-pages %) 2)
                           (pos? (:fuel %)))
                    receipts)
             "ADL engine receipt mismatch")
    (ensure! (seq @execution-receipts) "signed ADL execution receipts missing")
    (ensure! (every? #(and (:verified? (adl/verify-execution-receipt!
                                        % trust runner-policy))
                           (= module-cid (:module-cid %)))
                    @execution-receipts)
             "signed ADL execution receipt verification failed")
    (ensure! (= 1 (count (set (map :runner-sha256 @execution-receipts))))
             "ADL runner artifact identity changed during execution")
    (println "ipld-adl-wasmtime: io-ipld projection and signed measured receipts passed")
    (shutdown-agents)))
