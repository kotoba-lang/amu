(ns kotoba.compiler.dataspace-native-aot-test
  "Native process runs typed-cap-call 24 (wire :dataspace/transact).

  The guest returns a packed i64 because a native entry cannot return the
  dataspace variant. Bits prove facet-enter / empty observe / assert notices /
  observe-after-assert notices / retract-notice / facet-leave.

  Native `:document` is a string-shaped pair over UTF-8 EDN. document-edn-read
  / print are identity at the ABI; the loader inject interns the same bytes.

  Break: make facet-enter return the request handle (identity). The guest
  then treats a bool payload as a facet record, traps SIGILL, and does not
  return 127."
  (:require [clojure.edn :as edn]
            [clojure.java.io :as io]
            [clojure.test :refer [deftest is]]
            [kotoba.compiler.atomic-output :as atomic-output]
            [kotoba.compiler.core :as compiler]
            [kotoba.artifact.runtime-identity :as runtime-identity]
            [kotoba.verifier.signing :as signing]
            [kototama.native.executor :as executor]
            [provider.dataspace :as dataspace]))

(def policy {:allow #{[:cap/call 24]}})

(def empty-notices "[]")
(def assert-notices
  "[{:assertion [:temperature :room/a 21] :bindings {} :kind :assert}]")
(def retract-notices
  "[{:assertion [:temperature :room/a 21] :bindings {} :kind :retract}]")

(def guest-source
  (let [req (pr-str dataspace/request-type)
        res (pr-str dataspace/result-type)
        asserted (pr-str dataspace/asserted-type)
        retracted (pr-str dataspace/retracted-type)
        matches (pr-str dataspace/matches-type)
        facet-rec (pr-str dataspace/facet-type)
        observe-rec (pr-str dataspace/observe-type)
        assert-rec (pr-str dataspace/assert-type)
        retract-rec (pr-str dataspace/retract-type)
        empty-doc "(document-edn-read \"[]\")"]
    (str "(ns app.ds (:export [main]) (:capabilities #{:dataspace/transact}))"
         "(defn main [] :i64"
         "  (let [doc (document-edn-read \"[:temperature :room/a 21]\")"
         "        entered (typed-cap-call :dataspace/transact " req " " res
         "                  (variant-new " req " :facet-enter false))"
         "        facet (variant-match " res " entered"
         "                [[:asserted a 0]"
         "                 [:retracted r 0]"
         "                 [:matches m 0]"
         "                 [:facet f (record-get " facet-rec " f :id)]"
         "                 [:error e 0]])"
         "        bit0 (if (< 0 facet) 1 0)"
         "        observed0 (typed-cap-call :dataspace/transact " req " " res
         "                    (variant-new " req " :observe"
         "                      (record-new " observe-rec " doc facet)))"
         "        notices0 (variant-match " res " observed0"
         "                    [[:asserted a (record-get " asserted " a :notices)]"
         "                     [:retracted r " empty-doc "]"
         "                     [:matches m (record-get " matches " m :notices)]"
         "                     [:facet f " empty-doc "]"
         "                     [:error e " empty-doc "]])"
         "        bit1 (if (string=? (document-edn-print notices0) "
         (pr-str empty-notices) ") 1 0)"
         "        asserted0 (typed-cap-call :dataspace/transact " req " " res
         "                     (variant-new " req " :assert"
         "                       (record-new " assert-rec " doc facet)))"
         "        notices-a (variant-match " res " asserted0"
         "                     [[:asserted a (record-get " asserted " a :notices)]"
         "                      [:retracted r " empty-doc "]"
         "                      [:matches m (record-get " matches " m :notices)]"
         "                      [:facet f " empty-doc "]"
         "                      [:error e " empty-doc "]])"
         "        bit2 (if (string=? (document-edn-print notices-a) "
         (pr-str assert-notices) ") 1 0)"
         "        observed1 (typed-cap-call :dataspace/transact " req " " res
         "                     (variant-new " req " :observe"
         "                       (record-new " observe-rec " doc facet)))"
         "        notices1 (variant-match " res " observed1"
         "                     [[:asserted a (record-get " asserted " a :notices)]"
         "                      [:retracted r " empty-doc "]"
         "                      [:matches m (record-get " matches " m :notices)]"
         "                      [:facet f " empty-doc "]"
         "                      [:error e " empty-doc "]])"
         "        bit3 (if (string=? (document-edn-print notices1) "
         (pr-str assert-notices) ") 1 0)"
         "        retracted0 (typed-cap-call :dataspace/transact " req " " res
         "                      (variant-new " req " :retract"
         "                        (record-new " retract-rec " doc facet)))"
         "        bit4 (variant-match " res " retracted0"
         "                [[:asserted a 0]"
         "                 [:retracted r (if (< 0 (record-get " retracted " r :count)) 1 0)]"
         "                 [:matches m 0]"
         "                 [:facet f 0]"
         "                 [:error e 0]])"
         "        observed2 (typed-cap-call :dataspace/transact " req " " res
         "                     (variant-new " req " :observe"
         "                       (record-new " observe-rec " doc facet)))"
         "        notices2 (variant-match " res " observed2"
         "                     [[:asserted a (record-get " asserted " a :notices)]"
         "                      [:retracted r " empty-doc "]"
         "                      [:matches m (record-get " matches " m :notices)]"
         "                      [:facet f " empty-doc "]"
         "                      [:error e " empty-doc "]])"
         "        bit5 (if (string=? (document-edn-print notices2) "
         (pr-str retract-notices) ") 1 0)"
         "        left (typed-cap-call :dataspace/transact " req " " res
         "                (variant-new " req " :facet-leave facet))"
         "        bit6 (variant-match " res " left"
         "                [[:asserted a 0]"
         "                 [:retracted r 1]"
         "                 [:matches m 0]"
         "                 [:facet f 0]"
         "                 [:error e 0]])]"
         "    (+ bit0"
         "       (+ (* 2 bit1)"
         "          (+ (* 4 bit2)"
         "             (+ (* 8 bit3)"
         "                (+ (* 16 bit4)"
         "                   (+ (* 32 bit5) (* 64 bit6)))))))))")))

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
          loader (doto (java.io.File/createTempFile "kotoba-ds-loader-" "")
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
   (slurp (io/resource "kotoba/lang/capability-kits/dataspace-v1.edn"))))

(deftest native-dataspace-guest-round-trips-through-real-kexe-loader
  (let [{:keys [envelope trust]} (signed guest-source)
        {:keys [trust options]} (execution-options trust)
        result (executor/execute envelope trust policy {:args []} options)]
    (is (= :ok (get-in result [:evidence :status]))
        (pr-str (select-keys (:evidence result) [:status :trap :result])))
    (is (= 127 (get-in result [:evidence :result]))
        "bits: enter, empty observe, assert notices, observe assert, retract count, retract notice, leave")))

(deftest dataspace-kit-native-aot-is-implemented-only-after-the-process-ran
  (let [kit (load-kit)
        q (:qualification kit)]
    (is (= :implemented (:native-aot q)))))
