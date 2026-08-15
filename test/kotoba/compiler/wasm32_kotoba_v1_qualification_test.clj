(ns kotoba.compiler.wasm32-kotoba-v1-qualification-test
  "Names the i64 wasm32 host-time surface separately from kit :wasm-aot.

  Clock guest sugar elaborates to `(typed-cap-call 7 :i64 :i64 seed)` and
  that path is E2E on kototama.tender / wasm-webcomponent. Clock :wasm-aot
  is the kit variant/record schema on WASI 0.3 (ADR 0258). The two are
  not the same ABI."
  (:require [clojure.edn :as edn]
            [clojure.java.io :as io]
            [clojure.test :refer [deftest is testing]]))

(def application-kit-files
  ["clock-v1.edn" "http-v1.edn" "http-ingress-v1.edn" "storage-v1.edn"
   "log-v1.edn" "llm-v1.edn" "ui-v1.edn" "state-v1.edn"])

(defn- load-kit [filename]
  (edn/read-string
   (slurp (io/resource (str "kotoba/lang/capability-kits/" filename)))))

(deftest clock-wasm32-kotoba-v1-qualification-is-the-i64-surface
  (let [clock (load-kit "clock-v1.edn")
        q (:qualification clock)
        surface (:wasm32-kotoba-v1-surface clock)]
    (is (= :implemented (:wasm32-kotoba-v1 q)))
    (is (= :implemented (:wasm-aot q))
        "kit variant/record schema on WASI clocks is a separate claim from i64")
    (is (= :implemented (:reference q)))
    (is (= :pending (:native-aot q)))
    (is (= :pending (:jit q)))
    (is (= ["kotoba:cap" "call"] (:import surface)))
    (is (= [:i64 :i64 :i64] (:signature surface)))
    (is (= 7 (:capability-id surface)))
    (is (= :clock-monotonic (:grant surface)))
    (is (= "(typed-cap-call 7 :i64 :i64 seed)" (:elaboration surface)))))

(def wasm-aot-implemented-kits
  "Clock: WASI 0.3 host time (ADR 0258). State/log: in-component store/ring
   (ADR 0259). UI: host enqueue slot (ADR 0260). Http-ingress: host inject
   slot (ADR 0261). Storage: in-component KV (ADR 0262). HTTP post / LLM:
   sync kit-shaped host + echo stub (ADR 0263 / 0264)."
  #{"clock-v1.edn" "state-v1.edn" "log-v1.edn" "ui-v1.edn"
    "http-ingress-v1.edn" "storage-v1.edn" "http-v1.edn" "llm-v1.edn"})

(deftest other-application-kits-keep-wasm32-kotoba-v1-pending
  (doseq [filename (remove #{"clock-v1.edn"} application-kit-files)]
    (testing filename
      (is (= :pending (:wasm32-kotoba-v1 (:qualification (load-kit filename))))))))

(deftest wasm-aot-matches-the-implemented-kit-set
  (doseq [filename application-kit-files]
    (testing filename
      (is (= (if (wasm-aot-implemented-kits filename) :implemented :pending)
             (:wasm-aot (:qualification (load-kit filename))))))))
