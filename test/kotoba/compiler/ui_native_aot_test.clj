(ns kotoba.compiler.ui-native-aot-test
  "Native process runs typed-cap-call 9 and 10 (wire :ui/commit :ui/next-event).

  The guest returns a packed i64 because a native entry cannot return the
  commit record or the event option. Bits prove poll-before-commit is none,
  commit base 0 yields revision 1 and node-count 1, and poll-after-commit
  returns some event at revision 1.

  Break: make commit return the request handle (identity). The guest then
  treats a node-set handle as a commit-result, traps SIGILL, and does not
  return 15."
  (:require [clojure.edn :as edn]
            [clojure.java.io :as io]
            [clojure.test :refer [deftest is]]
            [kotoba.compiler.atomic-output :as atomic-output]
            [kotoba.compiler.core :as compiler]
            [kotoba.artifact.runtime-identity :as runtime-identity]
            [kotoba.verifier.signing :as signing]
            [kototama.native.executor :as executor]
            [provider.ui :as ui]))

(def policy {:allow #{[:cap/call 9] [:cap/call 10]}})

(def guest-source
  (let [creq (pr-str ui/commit-request-type)
        cres (pr-str ui/commit-result-type)
        ereq (pr-str ui/event-request-type)
        eres (pr-str ui/event-result-type)
        nset (pr-str ui/node-set-type)
        node (pr-str ui/node-type)
        parent (pr-str ui/parent-type)
        evt (pr-str ui/event-type)]
    (str "(ns app.ui (:export [main]) (:capabilities #{:ui/commit :ui/next-event}))"
         "(defn main [] :i64"
         "  (let [pending (option-match " eres
         "                  (typed-cap-call :ui/next-event " ereq " " eres
         "                    (record-new " ereq " 0))"
         "                  1 e 0)"
         "        committed (typed-cap-call :ui/commit " creq " " cres
         "                    (record-new " creq " 0"
         "                      (typed-set-conj " nset " (typed-set-new " nset ")"
         "                        (record-new " node " :view/title"
         "                          (option-none-of " parent ") :ui/text \"ready\"))))"
         "        rev (record-get " cres " committed :revision)"
         "        count (record-get " cres " committed :node-count)"
         "        after (option-match " eres
         "                 (typed-cap-call :ui/next-event " ereq " " eres
         "                   (record-new " ereq " 0))"
         "                 0 e (record-get " evt " e :revision))"
         "        bit1 (if (< rev 2) (if (< 0 rev) 1 0) 0)"
         "        bit2 (if (< count 2) (if (< 0 count) 1 0) 0)"
         "        bit3 (if (< after 2) (if (< 0 after) 1 0) 0)]"
         "    (+ pending"
         "       (+ (* 2 bit1)"
         "          (+ (* 4 bit2) (* 8 bit3))))))")))

(defn- target []
  (if (contains? #{"aarch64" "arm64"} (.toLowerCase (System/getProperty "os.arch")))
    :aarch64-kotoba-v1
    :x86_64-kotoba-v1))

(defn- signed [source]
  (let [artifact (:artifact (compiler/compile-source source (target) policy))
        key (signing/generate-keypair)
        envelope (signing/sign artifact key {:not-before 1000 :expires 2000})
        trust {:format :kotoba.trust/v1 :trusted-signers #{(:signer key)}
               :revoked-signers #{} :revoked-artifacts #{}}]
    {:artifact artifact :envelope envelope :trust trust}))

(defonce measured-runtime
  (delay
    (let [{:keys [runtime loader-bytes]} (executor/measure-runtime)
          loader (doto (java.io.File/createTempFile "kotoba-ui-loader-" "")
                   (.deleteOnExit))]
      (atomic-output/write-bytes! (.getPath loader) loader-bytes {:executable? true})
      {:runtime runtime :loader-path (.getPath loader)})))

(defn- execution-options [trust]
  (let [{:keys [runtime loader-path]} @measured-runtime]
    {:trust (assoc trust :trusted-runtime-sha256
                   #{(runtime-identity/identity-sha256 runtime)})
     :options {:now 1500 :entry 'main :runtime runtime :loader-path loader-path}}))

(defn- load-kit []
  (edn/read-string
   (slurp (io/resource "kotoba/lang/capability-kits/ui-v1.edn"))))

(deftest native-ui-guest-round-trips-through-real-kexe-loader
  (let [{:keys [envelope trust]} (signed guest-source)
        {:keys [trust options]} (execution-options trust)
        result (executor/execute envelope trust policy {:args []} options)]
    (is (= :ok (get-in result [:evidence :status]))
        (pr-str (select-keys (:evidence result) [:status :trap :result])))
    (is (= 15 (get-in result [:evidence :result]))
        "bits: pending-none, rev==1, count==1, event-rev==1")))

(deftest ui-kit-native-aot-is-implemented-only-after-the-process-ran
  (let [kit (load-kit)
        q (:qualification kit)]
    (is (= :implemented (:native-aot q)))))
