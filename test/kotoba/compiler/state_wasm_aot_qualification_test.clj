(ns kotoba.compiler.state-wasm-aot-qualification-test
  "Binds state-v1 :wasm-aot to live wasmtime semantic vectors.

  The in-component store is the production source of truth (no host KV).
  ADR 0060/0061 already packaged the 14-step driver; this ns actually
  runs it. A self-compared bitmask is not evidence."
  (:require [clojure.edn :as edn]
            [clojure.java.io :as io]
            [clojure.java.shell :as shell]
            [clojure.string :as str]
            [clojure.test :refer [deftest is]]
            [kotoba.component.composition :as composition]
            [kotoba.compiler.component-composition-test :as state-comp])
  (:import [java.nio.file Files]
           [java.nio.file.attribute FileAttribute]))

(def ^:private wasmtime-binary
  (let [pinned (io/file ".tools" "wasmtime" "wasmtime")]
    (if (.canExecute pinned) (.getPath pinned) "wasmtime")))

(defn- compose-state-driver
  ([]
   (let [{:keys [descriptor result-descriptor schemas]}
         (#'state-comp/state-v1-descriptors)
         driver (#'state-comp/package-state-driver result-descriptor schemas)
         provider (composition/package-state-provider
                   :state/transact descriptor result-descriptor schemas 4)]
     (composition/compose-closed driver [provider])))
  ([steps]
   (with-redefs [state-comp/state-driver-steps steps]
     (compose-state-driver))))

(defn- run-closed [closed]
  (let [path (Files/createTempFile "amu-state-wasm-aot-" ".wasm"
                                   (make-array FileAttribute 0))]
    (try
      (Files/write path ^bytes (:bytes closed)
                   (make-array java.nio.file.OpenOption 0))
      (shell/sh wasmtime-binary "run" "--invoke" "run()" (str path))
      (finally
        (Files/deleteIfExists path)))))

(deftest state-kit-flag-is-bound-to-this-evidence
  (let [kit (edn/read-string
             (slurp (io/resource "kotoba/lang/capability-kits/state-v1.edn")))]
    (is (= :implemented (get-in kit [:qualification :wasm-aot])))
    (is (= :pending (get-in kit [:qualification :wasm32-kotoba-v1])))
    (is (= :pending (get-in kit [:qualification :native-aot])))
    (is (= :pending (get-in kit [:qualification :jit])))))

(deftest wasmtime-state-kit-runs-the-fourteen-step-vector
  (let [closed (compose-state-driver)
        run (run-closed closed)
        mask (parse-long (str/trim (:out run)))]
    (is (zero? (:exit run)) (str "wasmtime err: " (:err run)))
    (is (= state-comp/state-driver-expected-mask mask)
        (str "state vector mask " mask " != "
             state-comp/state-driver-expected-mask))))

(deftest wasmtime-state-kit-vector-clears-a-corrupted-step
  (let [steps (assoc-in state-comp/state-driver-steps [2 3 :version] 999)
        closed (compose-state-driver steps)
        run (run-closed closed)
        mask (parse-long (str/trim (:out run)))]
    (is (zero? (:exit run)) (str "wasmtime err: " (:err run)))
    (is (= (- state-comp/state-driver-expected-mask 4) mask)
        (str "corrupted step 2 should clear bit 2; got " mask))))
