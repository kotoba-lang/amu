(ns kotoba.compiler.native-aot-qualification-test
  "Locks native-aot / jit as pending on every application kit.

  Production native-aot is C-free aiueos (ADR 0265 / 0266). Hosted kexe C
  loader is a rejected production surface. The hosted clock-v1 oracle in
  `clock-native-kexe-oracle-test` does not close the four native backend
  gaps and must not flip a kit flag (ADR 0266). `:jit` is a future
  KIR→native runtime compiler, not wasmtime Cranelift."
  (:require [clojure.edn :as edn]
            [clojure.java.io :as io]
            [clojure.test :refer [deftest is testing]]))

(def application-kit-files
  ["clock-v1.edn" "http-v1.edn" "http-ingress-v1.edn" "storage-v1.edn"
   "log-v1.edn" "llm-v1.edn" "ui-v1.edn" "state-v1.edn"])

(def native-gaps
  #{:typed-provider-syscall-abi
    :nested-request-result-host-codec
    :native-provider-semantic-vectors
    :c-free-aiueos-cpl3-syscall-substrate})

(defn- load-kit [filename]
  (edn/read-string
   (slurp (io/resource (str "kotoba/lang/capability-kits/" filename)))))

(deftest every-application-kit-keeps-native-aot-and-jit-pending
  (doseq [filename application-kit-files]
    (testing filename
      (let [q (:qualification (load-kit filename))]
        (is (= :pending (:native-aot q)))
        (is (= :pending (:jit q)))))))

(deftest native-backend-still-names-the-c-free-syscall-gaps
  (let [claims (edn/read-string
                (slurp (io/resource "kotoba/lang/backend-provider-qualification-v2.edn")))
        native (get-in claims [:backends :native])]
    (is (= :pending (:execution-status native)))
    (is (= :aiueos-c-free-bare-metal-v1 (:execution-surface native)))
    (is (= native-gaps (set (:gaps native))))))
