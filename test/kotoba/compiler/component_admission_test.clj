(ns kotoba.compiler.component-admission-test
  "Component target exposure, declared fuel/memory budgets, and the admission
  request the compiler owes kototama (ADR-2607252500)."
  (:require [clojure.test :refer [deftest is testing]]
            [clojure.string :as str]
            [kotoba.component.admission :as admission]
            [kotoba.wasm.core :as wasm]
            [kotoba.sema :as sema]
            [kotoba.kir :as ir]
            [kotoba.kir.target :as target-profile]
            [kotoba.compiler.core :as compiler])
  (:import [java.nio.charset StandardCharsets]))

(def ^:private scalar-source "(ns t) (defn main [] 42)")

(defn- kir [source] (ir/lower (sema/analyze source)))

(defn- hex [bytes]
  (apply str (map #(format "%02x" (bit-and (int %) 0xff)) bytes)))

;; The fuel global is `(global (mut i64) (i64.const N))`, encoded as
;; count=1, valtype 0x7e, mutable 0x01, 0x42 (i64.const), SLEB128 N, 0x0b.
(defn- fuel-global-hex
  "The fuel global's own entry: valtype i64, mutable, i64.const N, end.

  Deliberately WITHOUT the section's global-count prefix -- that count is 1 for
  a plain core module and 2 for a component (which also declares the bump
  pointer), and baking it in here made this assert the number of globals rather
  than the fuel budget."
  [n]
  (str "7e0142" (hex (loop [n (long n) out []]
                         (let [b (bit-and n 0x7f) n' (bit-shift-right n 7)
                               done (or (and (= n' 0) (zero? (bit-and b 0x40)))
                                        (and (= n' -1) (not (zero? (bit-and b 0x40)))))]
                           (if done (conj out b) (recur n' (conj out (bit-or b 0x80)))))))
       "0b"))

(deftest default-fuel-is-unchanged-by-parameterization
  (testing "a caller that supplies no :fuel gets exactly the historical 512"
    (let [module (hex (wasm/emit (kir scalar-source) :wasm32-kotoba-v1))]
      (is (= 512 wasm/default-fuel))
      (is (str/includes? module (fuel-global-hex 512)))
      (is (= module (hex (wasm/emit (kir scalar-source) :wasm32-kotoba-v1 {})))
          "explicit empty opts must be byte-identical to the two-arity call")
      (is (= module (hex (wasm/emit (kir scalar-source) :wasm32-kotoba-v1
                                    {:fuel 512})))
          "explicitly declaring the default must not change a single byte"))))

(deftest declared-fuel-is-compiled-into-the-module
  (testing "a declared budget reaches the module's fuel global"
    (doseq [budget [1 1000 1000000 4294967296]]
      (is (str/includes? (hex (wasm/emit (kir scalar-source) :wasm32-kotoba-v1
                                         {:fuel budget}))
                         (fuel-global-hex budget))
          (str "fuel budget " budget " is not in the emitted global")))))

(deftest fuel-budget-is-fail-closed
  (testing "a budget that cannot be enforced is rejected, not silently defaulted"
    (doseq [bad [0 -1 -512]]
      (is (thrown? clojure.lang.ExceptionInfo
                   (wasm/emit (kir scalar-source) :wasm32-kotoba-v1 {:fuel bad}))
          (str "non-positive fuel " bad " must be rejected")))
    (is (thrown? clojure.lang.ExceptionInfo
                 (wasm/emit (kir scalar-source) :wasm32-kotoba-v1 {:fuel :unbounded})))
    (is (thrown? clojure.lang.ExceptionInfo
                 (wasm/emit (kir scalar-source) :wasm32-kotoba-v1
                            {:fuel (inc wasm/max-fuel)})))))

(deftest component-target-is-exposed-and-routed
  (testing "the target exists and names kototama's contract exactly"
    (let [profile (target-profile/profile :wasm-component-kotoba-v1)]
      (is (some? profile))
      (is (= :component (:execution profile)))
      (is (= "0.3.0" (:wasi-version profile)))
      (is (false? (:ambient-wasi profile)))))
  (testing "compile-source refuses it instead of emitting a bare core module"
    (let [thrown (try (compiler/compile-source scalar-source :wasm-component-kotoba-v1)
                      nil
                      (catch clojure.lang.ExceptionInfo e (ex-data e)))]
      (is (= :target-routing (:phase thrown)))
      (is (= 'kotoba.compiler.core/compile-component (:entry-point thrown))))))

(deftest typed-v03-clock-component-is-produced-from-source
  (let [ability {:target "clock://monotonic"
                 :operation :clock/now
                 :max-bytes 64
                 :max-items 1
                 :deadline-ms 1000
                 :audit-id "compiler-v03-clock"}
        artifact
        (compiler/compile-component
         "(ns app (:capabilities #{:clock/now}))
          (defn main [] (cap-call :clock/now 0))"
         {:allow #{[:cap/call 7]}}
         {:target :wasm-component-kotoba-v2
          :component-abilities {7 ability}})]
    (is (= :wasm-component-kotoba-v2 (:target artifact)))
    (is (= "aiueos:capability/application@0.3.0"
           (:component-world artifact)))
    (is (= ability
           (get-in artifact
                   [:component-imports :aiueos.component/aiueos-clock-now])))
    (is (= [0 97 115 109 13 0 1 0]
           (mapv #(bit-and (int %) 0xff) (take 8 (:bytes artifact)))))))

(deftest cid-matches-the-canonical-empty-block
  (testing "CIDv1 raw/sha2-256/base32 agrees with the published empty-block CID"
    (is (= "bafkreihdwdcefgh4dqkjv67uzcmw7ojee6xedzdetojuzjevtenxquvyku"
           (admission/cid (byte-array 0)))))
  (testing "identities are CID-shaped for kototama's envelope gate"
    (let [value (admission/cid-of-text "kotoba")]
      (is (str/starts-with? value "b"))
      (is (< 1 (count value)))
      (is (re-matches #"b[a-z2-7]+" value)))))

(deftest admission-request-omits-what-the-compiler-may-not-decide
  (let [result (compiler/compile-component scalar-source {} {})
        request (:admission-request result)]
    (testing "the request carries what the compiler knows"
      (is (= :kotoba.component-admission-request/v1 (:format request)))
      (is (= :wasm-component-kotoba-v1 (:target request)))
      (is (= "0.3.0" (:wasi-version request)))
      (is (= :sync (:profile request)))
      (is (false? (:ambient-wasi request)))
      (is (set? (:exports request)))
      (is (contains? (:exports request) "main")))
    (testing "grants and provider bindings are never self-asserted"
      (is (= #{:grants :provider-bindings} admission/composer-supplied-keys))
      (is (not (contains? request :grants)))
      (is (not (contains? request :provider-bindings))))
    (testing "budgets are positive integers for every key the profile requires"
      (is (every? #(pos-int? (get-in request [:budgets %])) [:fuel :memory-pages])))
    (testing "a missing package lock is reported, not fabricated"
      (is (not (contains? request :identity)))
      (is (= #{:package-lock-cid} (:identity-inputs-missing request))))
    (testing "fuel enforcement location is stated honestly"
      (is (= :module-global (:fuel-enforcement result))))))

(deftest completed-envelope-matches-kototama-key-set
  (let [locked (compiler/compile-component
                scalar-source {}
                {:package-lock-cid (admission/cid-of-text "package-lock")})
        request (:admission-request locked)
        imports (:imports request)
        envelope (admission/complete request imports
                                     (zipmap imports (repeat :test-provider)))]
    (testing "the composed envelope has exactly the ten contract keys"
      (is (= admission/envelope-keys (set (keys envelope)))))
    (testing "identity is bound once a package lock exists"
      (is (= #{:component-cid :package-lock-cid :definition-cids}
             (set (keys (:identity envelope)))))
      (is (seq (get-in envelope [:identity :definition-cids]))))
    ;; The compiled scalar program imports nothing, so asserting the
    ;; grant/binding guards against it would be vacuously true -- `every?` and
    ;; set equality both succeed on the empty set. Compose a request that
    ;; actually declares imports so the guards are exercised.
    (let [with-imports (assoc request :imports #{"cap-a" "cap-b"})
          bound {"cap-a" :test-provider "cap-b" :test-provider}]
      (testing "a fully granted and bound request composes"
        (is (= admission/envelope-keys
               (set (keys (admission/complete with-imports
                                              #{"cap-a" "cap-b"} bound))))))
      (testing "an ungranted import cannot be composed"
        (is (thrown? clojure.lang.ExceptionInfo
                     (admission/complete with-imports #{"cap-a"} bound))))
      (testing "an unbound import cannot be composed"
        (is (thrown? clojure.lang.ExceptionInfo
                     (admission/complete with-imports #{"cap-a" "cap-b"}
                                         {"cap-a" :test-provider}))))
      (testing "a binding for an undeclared import cannot be composed"
        (is (thrown? clojure.lang.ExceptionInfo
                     (admission/complete with-imports #{"cap-a" "cap-b"}
                                         (assoc bound "cap-c" :test-provider))))))
    (testing "a request without bound identity cannot be completed"
      (is (thrown? clojure.lang.ExceptionInfo
                   (admission/complete (:admission-request
                                        (compiler/compile-component scalar-source {} {}))
                                       #{} {}))))))

(deftest declared-component-fuel-reaches-the-component-binary
  (testing "the component's module carries the budget it declares"
    (let [budget 4096
          result (compiler/compile-component scalar-source {} {:budgets {:fuel budget}})]
      (is (= budget (get-in result [:admission-request :budgets :fuel])))
      (is (= :module-global (:fuel-enforcement result)))
      (is (str/includes? (hex (:bytes result)) (fuel-global-hex budget))
          "the declared budget must be the one compiled into the module"))))
