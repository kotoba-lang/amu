(ns kotoba.compiler.ipld-adl
  "Synchronous io-ipld ADL capability backed by the bounded Wasmtime C engine."
  (:require [clojure.data.json :as json]
            [clojure.java.shell :as shell]
            [ipld.schema :as schema])
  (:import (java.nio.file Files Path)
           (java.nio.file.attribute FileAttribute)))

(def engine-id "kotoba.ipld-adl-wasmtime/v1")
(def receipt-format "kotoba.ipld-adl-wasmtime-receipt/v1")

(def ^:private operation-code
  {:validate-representation 0 :decode 1 :encode 2 :validate-logical 3})

(defn- byte-array-value [value]
  (cond
    (instance? (Class/forName "[B") value) value
    (sequential? value) (byte-array (map byte value))
    :else (throw (ex-info "ADL engine requires byte input"
                          {:phase :ipld-adl :code :invalid-bytes}))))

(defn- delete-tree! [^Path directory]
  (when directory
    (doseq [name ["output.cbor" "input.cbor" "module.wasm"]]
      (Files/deleteIfExists (.resolve directory name)))
    (Files/deleteIfExists directory)))

(defn- invoke-engine
  [runner timeout-ms module-size
   {:keys [module-bytes module-cid operation input-bytes fuel-limit
           max-output-bytes max-memory-pages]}]
  (let [directory (Files/createTempDirectory
                   "kotoba-ipld-adl-" (make-array FileAttribute 0))
        module-path (.resolve directory "module.wasm")
        input-path (.resolve directory "input.cbor")
        output-path (.resolve directory "output.cbor")]
    (try
      (Files/write module-path (byte-array-value module-bytes) (make-array java.nio.file.OpenOption 0))
      (Files/write input-path (byte-array-value input-bytes) (make-array java.nio.file.OpenOption 0))
      (let [result (shell/sh runner
                             (str module-path) (str input-path) (str output-path)
                             (str (operation-code operation)) (str fuel-limit)
                             (str max-output-bytes) (str max-memory-pages)
                             (str timeout-ms) (str module-size))
            receipt (try
                      (json/read-str (:out result) :key-fn keyword)
                      (catch Exception _ nil))]
        (when-not (and (zero? (:exit result))
                       (= #{:format :status :engineId :engineVersion :fuelUsed
                            :memoryPages :outputBytes}
                          (set (keys receipt)))
                       (= receipt-format (:format receipt))
                       (= "ok" (:status receipt))
                       (= engine-id (:engineId receipt))
                       (and (string? (:engineVersion receipt))
                            (seq (:engineVersion receipt)))
                       (and (integer? (:fuelUsed receipt))
                            (pos? (:fuelUsed receipt))
                            (<= (:fuelUsed receipt) fuel-limit))
                       (and (integer? (:memoryPages receipt))
                            (<= 0 (:memoryPages receipt) max-memory-pages))
                       (and (integer? (:outputBytes receipt))
                            (<= 0 (:outputBytes receipt) max-output-bytes)))
          (throw (ex-info "Wasmtime ADL execution failed"
                          {:phase :ipld-adl
                           :code (keyword (or (:code receipt) "engine-failed"))})))
        (let [output (Files/readAllBytes output-path)]
          (when-not (= (alength output) (:outputBytes receipt))
            (throw (ex-info "Wasmtime ADL output receipt mismatch"
                            {:phase :ipld-adl :code :output-receipt-mismatch})))
          {:status :ok :engine-id engine-id :module-cid module-cid
           :output-bytes output :fuel-used (:fuelUsed receipt)
           :memory-pages (:memoryPages receipt)}))
      (finally (delete-tree! directory)))))

(defn wasmtime-capability
  "Create an `ipld-adl-wasm-v1` capability backed by RUNNER.

  RUNNER is the binary built by `scripts/build-ipld-adl-wasmtime.sh`. Every
  invocation uses a fresh Wasmtime Store, admits no guest imports, enforces the
  request fuel/output/memory limits in the engine, and interrupts at TIMEOUT-MS.
  MODULE-CID remains independently re-derived by io-ipld before this adapter is
  called."
  [{:keys [runner module-bytes module-cid operations timeout-ms] :as options}]
  (when-not (= #{:runner :module-bytes :module-cid :operations :timeout-ms}
               (set (keys options)))
    (throw (ex-info "invalid Wasmtime ADL capability options"
                    {:phase :ipld-adl :code :invalid-options})))
  (when-not (and (string? runner) (.canExecute (java.io.File. runner)))
    (throw (ex-info "Wasmtime ADL runner is not executable"
                    {:phase :ipld-adl :code :runner-unavailable})))
  (when-not (and (integer? timeout-ms) (pos? timeout-ms) (<= timeout-ms 60000))
    (throw (ex-info "invalid Wasmtime ADL timeout"
                    {:phase :ipld-adl :code :invalid-timeout})))
  (let [module (byte-array-value module-bytes)
        invoke #(invoke-engine runner timeout-ms (alength module) %)]
    (schema/wasm-adl-capability
     {:engine-id engine-id :module-bytes module :module-cid module-cid
      :operations operations :invoke invoke})))
