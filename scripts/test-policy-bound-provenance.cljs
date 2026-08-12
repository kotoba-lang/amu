#!/usr/bin/env nbb
(ns test-policy-bound-provenance
  (:require [clojure.string :as str]
            [scripts.lib :as lib]
            ["node:child_process" :as child]
            ["node:fs" :as fs]
            ["node:os" :as os]
            ["node:path" :as path]))

(def directory (.mkdtempSync fs (.join path (.tmpdir os)
                                        "amu-policy-bound-provenance-")))

(defn- invoke [command args]
  (.spawnSync child command (clj->js args)
              #js {:cwd lib/root
                   :encoding "utf8"
                   :timeout 120000
                   :maxBuffer (* 16 1024 1024)}))

(defn- run! [command args]
  (let [result (invoke command args)]
    (when (.-error result) (throw (.-error result)))
    (when-not (zero? (.-status result))
      (throw (js/Error.
              (str command " " (str/join " " args) " failed ("
                   (.-status result) ")\n" (.-stdout result) (.-stderr result)))))
    result))

(defn- same? [left right]
  (.equals (.readFileSync fs left) (.readFileSync fs right)))

(try
  (let [fixture (lib/join lib/root "examples" "fuel.kotoba")
        policy (lib/join lib/root "test" "nbb" "fixtures" "fuel-policy.edn")
        excessive-policy (lib/join lib/root "test" "nbb" "fixtures"
                                   "excessive-native-fuel-policy.edn")
        pure-source (lib/join lib/root "test" "nbb" "fixtures"
                              "pure-product-capability.kotoba")
        pure-policy (lib/join lib/root "test" "nbb" "fixtures"
                              "pure-product-policy.edn")
        amu (lib/join directory "amu.wasm")
        jvm (lib/join directory "jvm.wasm")
        default-fuel (lib/join directory "default.wasm")
        native-fixture (lib/join lib/root "examples" "w1-pure.kotoba")
        amu-native (lib/join directory "amu.kexe")
        jvm-native (lib/join directory "jvm.kexe")
        primary (run! js/process.execPath
                      [(lib/join lib/root "bin" "amu") "compile" fixture
                       "--target" "wasm32" "--policy" policy "--output" amu])
        committed (run! js/process.execPath
                        [(lib/join lib/root "bin" "amu")
                         "verify-output-set" amu])
        pure-result (invoke js/process.execPath
                            [(lib/join lib/root "bin" "amu") "compile" pure-source
                             "--target" "wasm32" "--policy" pure-policy
                             "--output" (lib/join directory "forbidden.wasm")])
        excessive-result (invoke js/process.execPath
                                 [(lib/join lib/root "bin" "amu") "compile"
                                  native-fixture "--target" "aarch64"
                                  "--policy" excessive-policy
                                  "--output" (lib/join directory "excessive.kexe")])]
    (run! "clojure" ["-M:run" "compile" fixture "--target" "wasm32"
                     "--policy" policy "--output" jvm])
    (run! js/process.execPath
          [(lib/join lib/root "bin" "amu") "compile" fixture
           "--target" "wasm32" "--output" default-fuel])
    (run! js/process.execPath
          [(lib/join lib/root "bin" "amu") "compile" native-fixture
           "--target" "aarch64" "--policy" policy "--output" amu-native])
    (run! "clojure" ["-M:run" "compile" native-fixture "--target" "aarch64"
                     "--policy" policy "--output" jvm-native])

    (lib/ensure! (same? amu jvm)
                 "primary Node Wasm bytes ignored or changed policy-bound JVM emission")
    (lib/ensure! (same? (str amu ".provenance.edn")
                        (str jvm ".provenance.edn"))
                 "primary Node Wasm provenance differs from the JVM contract")
    (lib/ensure! (not (same? amu default-fuel))
                 "changing the fuel budget did not change emitted Wasm")
    (lib/ensure! (not (same? (str amu ".provenance.edn")
                             (str default-fuel ".provenance.edn")))
                 "changing policy did not change sealed Wasm provenance")
    (lib/ensure! (and (.includes (.-stdout primary) ":provenance-output")
                      (.includes (.-stdout primary) ":publication-output")
                      (not (.includes (.-stdout primary) ":not-emitted")))
                 "primary compiler did not report its committed Wasm output set")
    (lib/ensure! (.includes (.-stdout committed) ":kotoba.output-set/v1")
                 "primary compiler could not verify its committed output set")
    (lib/ensure! (.validate js/WebAssembly (.readFileSync fs amu))
                 "policy-bound primary output is not valid Wasm")
    (lib/ensure! (>= (.-size (.statSync fs (str amu ".provenance.edn"))) 128)
                 "Wasm provenance sidecar is unexpectedly empty")
    (lib/ensure! (same? amu-native jvm-native)
                 "primary Node native artifact differs from the JVM policy contract")
    (lib/ensure! (same? (str amu-native ".provenance.edn")
                        (str jvm-native ".provenance.edn"))
                 "primary Node native provenance differs from the JVM contract")
    (doseq [output [amu default-fuel amu-native]]
      (lib/ensure! (.isFile (.statSync fs (str output ".publication.edn")))
                   (str "primary compiler omitted output-set commit marker for " output)))
    (lib/ensure! (and (= 65 (.-status pure-result))
                      (.includes (.-stderr pure-result)
                                 ":kotoba.error/pure-product-capabilities"))
                 "primary compiler ignored the declarative language profile")
    (lib/ensure! (and (= 65 (.-status excessive-result))
                      (.includes (.-stderr excessive-result)
                                 "native fuel budget is not admitted"))
                 "primary native compiler admitted fuel beyond the verifier bound")
    (let [extra-argument (invoke js/process.execPath
                                 [(lib/join lib/root "bin" "amu")
                                  "verify-output-set" amu "unexpected"])]
      (lib/ensure! (and (= 64 (.-status extra-argument))
                        (.includes (.-stderr extra-argument)
                                   "exactly one artifact path"))
                   "output-set verifier accepted ambiguous extra arguments"))
    (let [marker-path (str amu ".publication.edn")
          marker-text (.readFileSync fs marker-path "utf8")]
      (.writeFileSync fs marker-path "[]")
      (let [malformed (invoke js/process.execPath
                              [(lib/join lib/root "bin" "amu")
                               "verify-output-set" amu])]
        (lib/ensure! (and (= 65 (.-status malformed))
                          (.includes (.-stderr malformed)
                                     "output set is not committed"))
                     "malformed output-set marker escaped the verify boundary"))
      (.writeFileSync fs marker-path marker-text))
    (.appendFileSync fs amu (.from js/Buffer #js [0]))
    (let [tampered (invoke js/process.execPath
                           [(lib/join lib/root "bin" "amu")
                            "verify-output-set" amu])]
      (lib/ensure! (and (= 65 (.-status tampered))
                        (.includes (.-stderr tampered)
                                   "output set is not committed"))
                   "output-set verification admitted mutated artifact bytes"))
    (println "policy-bound-provenance: fuel, language profile, Wasm/native bytes, and sealed provenance match policy"))
  (finally
    (.rmSync fs directory #js {:recursive true :force true})))
