(ns kotoba.compiler.clock-native-kexe-oracle-test
  "Hosted kexe clock-v1 oracle: nested codec + host time, not C-free native-aot.

  Production `:native-aot` remains `:aiueos-c-free-bare-metal-v1` (ADR 0266).
  These tests prove the nested request/result codec and semantic vectors on
  the hosted C loader so identity cannot masquerade as wall time. Kit
  `:native-aot` / `:jit` stay pending."
  (:require [clojure.edn :as edn]
            [clojure.java.io :as io]
            [clojure.test :refer [deftest is]]
            [kotoba.compiler.atomic-output :as atomic-output]
            [kotoba.compiler.core :as compiler]
            [kototama.native.executor :as executor]
            [kotoba.artifact.runtime-identity :as runtime-identity]
            [kotoba.verifier.signing :as signing]
            [provider.clock :as clock]))

(defn- target []
  (if (contains? #{"aarch64" "arm64"} (.toLowerCase (System/getProperty "os.arch")))
    :aarch64-kotoba-v1
    :x86_64-kotoba-v1))

(defn- signed [source policy]
  (let [artifact (:artifact (compiler/compile-source source (target) policy))
        key (signing/generate-keypair)
        envelope (signing/sign artifact key {:not-before 1000 :expires 2000})
        trust {:format :kotoba.trust/v1 :trusted-signers #{(:signer key)}
               :revoked-signers #{} :revoked-artifacts #{}}]
    {:artifact artifact :key key :envelope envelope :trust trust}))

(defonce measured-runtime
  (delay
    (let [{:keys [runtime loader-bytes]} (executor/measure-runtime)
          loader (doto (java.io.File/createTempFile "kotoba-clock-kexe-" "")
                   (.deleteOnExit))]
      (atomic-output/write-bytes! (.getPath loader) loader-bytes {:executable? true})
      {:runtime runtime :loader-path (.getPath loader)})))

(defn- execution-options [trust]
  (let [{:keys [runtime loader-path]} @measured-runtime]
    {:trust (assoc trust :trusted-runtime-sha256
                   #{(runtime-identity/identity-sha256 runtime)})
     :options {:now 1500 :entry 'main :runtime runtime :loader-path loader-path}}))

(defn- clock-guest [request-form extract]
  (let [req (pr-str clock/request-type)
        res (pr-str clock/result-type)
        wall (pr-str clock/wall-type)
        mono (pr-str clock/monotonic-type)]
    (str "(ns app.clock (:export [main]) (:capabilities #{:clock/now}))\n"
         "(defn main [] :i64\n"
         "  (variant-match " res "\n"
         "    (typed-cap-call :clock/now " req " " res "\n"
         "      (variant-new " req " " request-form "))\n"
         "    [[:wall w (record-get " wall " w :" extract ")]\n"
         "     [:monotonic m (record-get " mono " m :"
         (if (= extract "unix-millis") "nanos" extract) ")]\n"
         "     [:error e 0]]))\n")))

(defn- two-shot-guest [domain field result-expr]
  (let [req (pr-str clock/request-type)
        res (pr-str clock/result-type)
        wall (pr-str clock/wall-type)
        mono (pr-str clock/monotonic-type)
        tag (if (= domain :wall) ":wall" ":monotonic")
        wall-body (if (= domain :wall)
                    (str "(record-get " wall " w :" field ")")
                    "0")
        mono-body (if (= domain :monotonic)
                    (str "(record-get " mono " m :" field ")")
                    "0")
        observe
        (str "(variant-match " res "\n"
             "     (typed-cap-call :clock/now " req " " res "\n"
             "       (variant-new " req " " tag " false))\n"
             "     [[:wall w " wall-body "]\n"
             "      [:monotonic m " mono-body "]\n"
             "      [:error e 0]])")]
    (str "(ns app.clock (:export [main]) (:capabilities #{:clock/now}))\n"
         "(defn main [] :i64\n"
         "  (let [first " observe "\n"
         "        second " observe "]\n"
         "    " result-expr "))\n")))

(def ^:private clock-policy {:allow #{[:cap/call 7]}})

(deftest clock-kit-keeps-native-aot-and-jit-pending
  (let [kit (edn/read-string
             (slurp (io/resource "kotoba/lang/capability-kits/clock-v1.edn")))]
    (is (= :implemented (get-in kit [:qualification :wasm-aot])))
    (is (= :pending (get-in kit [:qualification :native-aot]))
        "hosted kexe is not the C-free production surface")
    (is (= :pending (get-in kit [:qualification :jit])))))

(deftest clock-v1-guest-emits-on-both-native-isas
  (let [source (clock-guest ":wall false" "unix-millis")]
    (doseq [native-target [:x86_64-kotoba-v1 :aarch64-kotoba-v1]]
      (let [artifact (:artifact (compiler/compile-source source native-target
                                                         clock-policy))]
        (is (seq (:code artifact)) (name native-target))
        (is (= #{[:cap/call 7]} (:effects artifact)) (name native-target))))))

(deftest hosted-kexe-clock-wall-returns-host-unix-millis
  (let [source (clock-guest ":wall false" "unix-millis")
        {:keys [envelope trust]} (signed source clock-policy)
        {:keys [trust options]} (execution-options trust)
        before (System/currentTimeMillis)
        result (executor/execute envelope trust clock-policy {:args []} options)
        after (System/currentTimeMillis)
        millis (get-in result [:evidence :result])]
    (is (= :ok (get-in result [:evidence :status])))
    (is (integer? millis))
    (is (> millis 1000000000000)
        "identity would echo the bool payload 0/1; unix-millis must be a real epoch")
    (is (<= (- before 1000) millis (+ after 1000))
        "hosted oracle must read the host clock, not a synthetic constant")))

(deftest hosted-kexe-clock-observation-sequence-increments
  (let [source (two-shot-guest :wall "observation-sequence" "second")
        {:keys [envelope trust]} (signed source clock-policy)
        {:keys [trust options]} (execution-options trust)
        result (executor/execute envelope trust clock-policy {:args []} options)]
    (is (= {:status :ok :result 2}
           (select-keys (:evidence result) [:status :result]))
        "two wall observations in one process yield sequence 2; identity cannot")))

(deftest hosted-kexe-clock-monotonic-is-nondecreasing
  (let [source (two-shot-guest :monotonic "nanos" "(if (< second first) 0 1)")
        {:keys [envelope trust]} (signed source clock-policy)
        {:keys [trust options]} (execution-options trust)
        result (executor/execute envelope trust clock-policy {:args []} options)]
    (is (= {:status :ok :result 1}
           (select-keys (:evidence result) [:status :result]))
        "second monotonic tick is >= first; identity bools cannot order this way")))

(deftest hosted-kexe-clock-denies-without-grant
  (let [source (clock-guest ":wall false" "unix-millis")
        {:keys [envelope trust]} (signed source clock-policy)
        {:keys [trust options]} (execution-options trust)]
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"capability policy denies"
                          (executor/execute envelope trust {:allow #{}} {:args []} options)))))
