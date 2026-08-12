#!/usr/bin/env nbb
(ns test-output-set-publisher-auth
  (:require [cljs.reader :as reader]
            [clojure.string :as str]
            [scripts.lib :as lib]
            ["node:child_process" :as child]
            ["node:fs" :as fs]
            ["node:os" :as os]
            ["node:path" :as path]))

(def directory (.mkdtempSync fs (.join path (.tmpdir os)
                                        "amu-output-publisher-")))

(defn- invoke [command args]
  (.spawnSync child command (clj->js args)
              #js {:cwd lib/root :encoding "utf8" :timeout 120000
                   :maxBuffer (* 16 1024 1024)}))

(defn- run! [command args]
  (let [result (invoke command args)]
    (when (.-error result) (throw (.-error result)))
    (when-not (zero? (.-status result))
      (throw (js/Error.
              (str command " " (str/join " " args) " failed ("
                   (.-status result) ")\n" (.-stdout result) (.-stderr result)))))
    result))

(defn- amu [& args]
  (invoke js/process.execPath (into [(lib/join lib/root "bin" "amu")] args)))

(defn- run-amu! [& args]
  (run! js/process.execPath (into [(lib/join lib/root "bin" "amu")] args)))

(defn- read-edn [file]
  (reader/read-string (.readFileSync fs file "utf8")))

(defn- write-edn! [file value]
  (.writeFileSync fs file (pr-str value) "utf8"))

(defn- rejected? [result status fragment]
  (and (= status (.-status result))
       (.includes (.-stderr result) fragment)))

(try
  (let [source (lib/join lib/root "examples" "fuel.kotoba")
        artifact (lib/join directory "publisher.wasm")
        second-artifact (lib/join directory "publisher-copy.wasm")
        native-source (lib/join lib/root "examples" "w1-pure.kotoba")
        native-artifact (lib/join directory "publisher.kexe")
        native-attestation (lib/join directory "publisher.kexe.attestation.edn")
        key (lib/join directory "publisher-key.edn")
        other-key (lib/join directory "other-key.edn")
        trust (lib/join directory "trust.edn")
        other-trust (lib/join directory "other-trust.edn")
        attestation (lib/join directory "publisher.attestation.edn")
        tampered-attestation (lib/join directory "tampered.attestation.edn")
        revoked-trust (lib/join directory "revoked-trust.edn")
        revoked-signer-trust (lib/join directory "revoked-signer-trust.edn")
        malformed-trust (lib/join directory "malformed-trust.edn")
        mismatch-key (lib/join directory "mismatch-key.edn")]
    (run-amu! "compile" source "--target" "wasm32" "--output" artifact)
    (run-amu! "compile" source "--target" "wasm32" "--output" second-artifact)
    (run-amu! "compile" native-source "--target" "aarch64"
              "--output" native-artifact)
    ;; Key creation and trust provisioning stay on the existing JVM path;
    ;; output-set signing and verification are the JDK-free Amu path.
    (run-amu! "keygen" "--output" key)
    (run-amu! "keygen" "--output" other-key)
    (run-amu! "trust-key" key "--output" trust)
    (run-amu! "trust-key" other-key "--output" other-trust)
    (let [signed (run-amu! "sign-output-set" artifact "--key" key
                           "--not-before" "1000" "--expires" "2000"
                           "--output" attestation)
          verified (run-amu! "verify-output-set" artifact
                             "--attestation" attestation
                             "--trust" trust "--now" "1500")]
      (lib/ensure! (.includes (.-stdout signed) ":kotoba.output-attestation/v1")
                   "Amu did not emit a versioned output-set attestation")
      (lib/ensure! (and (.includes (.-stdout verified)
                                  ":publisher-authenticated true")
                        (.includes (.-stdout verified) ":publisher "))
                   "trusted output-set admission did not authenticate its publisher"))

    (run-amu! "sign-output-set" native-artifact "--key" key
              "--not-before" "1000" "--expires" "2000"
              "--output" native-attestation)
    (let [verified-native
          (run-amu! "verify-output-set" native-artifact
                    "--attestation" native-attestation
                    "--trust" trust "--now" "1500")]
      (lib/ensure! (and (.includes (.-stdout verified-native)
                                  ":independent-native-verifier")
                        (.includes (.-stdout verified-native)
                                   ":publisher-authenticated true"))
                   "native output did not retain independent verification before publisher authentication"))

    ;; Node's signature must be byte-compatible with the canonical JVM
    ;; verifier rather than defining an NBB-only signature dialect.
    (run! "clojure"
          ["-M" "-e"
           (str "(require '[kotoba.compiler.bounded-edn :as b] "
                "'[kotoba.verifier.signing :as s]) "
                "(let [e (b/read-file \"" attestation "\")] "
                "(when-not (s/verify-value (get-in e [:statement :public-key]) "
                "(:statement e) (:signature e)) (System/exit 9)))")])

    (lib/ensure! (rejected? (amu "verify-output-set" artifact
                                 "--attestation" attestation
                                 "--trust" trust "--now" "2000")
                            77 "signature is expired")
                 "expired publisher attestation was admitted")
    (lib/ensure! (rejected? (amu "verify-output-set" artifact
                                 "--attestation" attestation
                                 "--trust" other-trust "--now" "1500")
                            77 "signer is not trusted")
                 "untrusted publisher was admitted")
    (lib/ensure! (rejected? (amu "verify-output-set" second-artifact
                                 "--attestation" attestation
                                 "--trust" trust "--now" "1500")
                            77 "does not name the admitted output")
                 "attestation was replayed onto a different output-set name")

    (let [envelope (read-edn attestation)
          changed (update-in envelope [:statement :expires] inc)]
      (write-edn! tampered-attestation changed)
      (lib/ensure! (rejected? (amu "verify-output-set" artifact
                                   "--attestation" tampered-attestation
                                   "--trust" trust "--now" "1500")
                              77 "signature is invalid")
                   "modified publisher statement retained authority"))

    (let [envelope (read-edn attestation)
          output-set-sha (get-in envelope [:statement :output-set-sha256])
          trust-value (read-edn trust)
          signer (get-in envelope [:statement :signer])]
      (write-edn! revoked-trust
                  (assoc trust-value :revoked-artifacts #{output-set-sha}))
      (lib/ensure! (rejected? (amu "verify-output-set" artifact
                                   "--attestation" attestation
                                   "--trust" revoked-trust "--now" "1500")
                              77 "output-set identity is revoked")
                   "revoked output-set retained publisher authority")
      (write-edn! revoked-signer-trust
                  (assoc trust-value :revoked-signers #{signer}))
      (lib/ensure! (rejected? (amu "verify-output-set" artifact
                                   "--attestation" attestation
                                   "--trust" revoked-signer-trust "--now" "1500")
                              77 "signer is revoked")
                   "revoked signer retained publisher authority")
      (write-edn! malformed-trust (assoc trust-value :ignored true))
      (lib/ensure! (rejected? (amu "verify-output-set" artifact
                                   "--attestation" attestation
                                   "--trust" malformed-trust "--now" "1500")
                              77 "trust policy is malformed")
                   "open trust schema was admitted"))

    (let [first-key (read-edn key)
          second-key (read-edn other-key)]
      (write-edn! mismatch-key
                  (assoc first-key :private-key (:private-key second-key)))
      (lib/ensure! (rejected? (amu "sign-output-set" artifact
                                   "--key" mismatch-key
                                   "--not-before" "1000" "--expires" "2000")
                              77 "signing key is invalid")
                   "mismatched Ed25519 keypair signed an output set"))

    (lib/ensure! (rejected? (amu "verify-output-set" artifact
                                 "--attestation" attestation)
                            64 "must be supplied together")
                 "partial publisher-verification options were accepted")
    (println "output-set publisher authentication: passed"))
  (finally
    (.rmSync fs directory #js {:recursive true :force true})))
