(ns kotoba.compiler.native-aot-qualification-test
  "Locks native-aot as pending on the application kits that still lack a
  hosted kexe process proof.

  Production native-aot is C-free aiueos (ADR 0270 / 0266). Hosted kexe C
  loader is a rejected production surface. dataspace and ui are the
  exceptions: each has a real-process test, the same way, and lives in
  wasm32-kotoba-v1-qualification-test/native-aot-kits (ADR 0272). The
  hosted clock-v1 oracle in `clock-native-kexe-oracle-test` does not
  close the four native backend gaps and must not flip a kit flag
  (ADR 0271).

  This file deliberately says nothing about `:jit`. It once asserted `:jit`
  was pending everywhere, on the reading that `:jit` names a future
  KIR->native runtime compiler. That is not what the key means in this
  repository: `:jit` is kotoba-script `:js-kotoba-v1` executed under V8, and
  six kits are measured `:implemented` on it by their own round-trip tests.
  `wasm32-kotoba-v1-qualification-test` and each kit's
  `*-kit-flag-is-bound-to-this-evidence` govern that key; a second file
  asserting the opposite from a different definition is how one word ends up
  meaning two things."
  (:require [clojure.edn :as edn]
            [clojure.java.io :as io]
            [clojure.test :refer [deftest is testing]]))

(def application-kit-files
  ["clock-v1.edn" "http-v1.edn" "http-ingress-v1.edn" "storage-v1.edn"
   "log-v1.edn" "llm-v1.edn" "state-v1.edn"])

(def native-gaps
  #{:typed-provider-syscall-abi
    :nested-request-result-host-codec
    :native-provider-semantic-vectors
    :c-free-aiueos-cpl3-syscall-substrate})

(defn- load-kit [filename]
  (edn/read-string
   (slurp (io/resource (str "kotoba/lang/capability-kits/" filename)))))

(deftest every-application-kit-keeps-native-aot-pending
  (doseq [filename application-kit-files]
    (testing filename
      (is (= :pending (:native-aot (:qualification (load-kit filename))))))))

(deftest native-backend-still-names-the-c-free-syscall-gaps
  (let [claims (edn/read-string
                (slurp (io/resource "kotoba/lang/backend-provider-qualification-v2.edn")))
        native (get-in claims [:backends :native])]
    (is (= :pending (:execution-status native)))
    (is (= :aiueos-c-free-bare-metal-v1 (:execution-surface native)))
    (is (= native-gaps (set (:gaps native))))))
