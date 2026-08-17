(ns kotoba.compiler.wasm32-kotoba-v1-qualification-test
  "Names the i64 wasm32 host-time surface separately from kit :wasm-aot.

  Clock guest sugar elaborates to `(typed-cap-call 7 :i64 :i64 seed)` and
  that path is E2E on kototama.tender / wasm-webcomponent. The kit's own
  variant/record request-result schema stays :wasm-aot :pending for clock
  (ADR 0084 / 0257). Dataspace is the first kit whose variant/record ABI
  runs on kotoba:typed/cap-call (wasm32-browser); that is :wasm-aot, not
  :wasm32-kotoba-v1."
  (:require [clojure.edn :as edn]
            [clojure.java.io :as io]
            [clojure.test :refer [deftest is testing]]))

(def application-kit-files
  ["clock-v1.edn" "http-v1.edn" "http-ingress-v1.edn" "storage-v1.edn"
   "log-v1.edn" "llm-v1.edn" "ui-v1.edn" "state-v1.edn" "dataspace-v1.edn"])

(defn- load-kit [filename]
  (edn/read-string
   (slurp (io/resource (str "kotoba/lang/capability-kits/" filename)))))

(deftest clock-wasm32-kotoba-v1-qualification-is-the-i64-surface
  (let [clock (load-kit "clock-v1.edn")
        q (:qualification clock)
        surface (:wasm32-kotoba-v1-surface clock)]
    (is (= :implemented (:wasm32-kotoba-v1 q)))
    (is (= :pending (:wasm-aot q))
        "variant/record kit schema is not the i64 host-time path")
    (is (= :implemented (:reference q)))
    (is (= :pending (:native-aot q)))
    (is (= ["kotoba:cap" "call"] (:import surface)))
    (is (= [:i64 :i64 :i64] (:signature surface)))
    (is (= 7 (:capability-id surface)))
    (is (= :clock-monotonic (:grant surface)))
    (is (= "(typed-cap-call 7 :i64 :i64 seed)" (:elaboration surface)))))

(deftest other-application-kits-keep-wasm32-kotoba-v1-pending
  (doseq [filename (remove #{"clock-v1.edn"} application-kit-files)]
    (testing filename
      (let [q (:qualification (load-kit filename))]
        (is (= :pending (:wasm32-kotoba-v1 q)))
        (when (not= filename "dataspace-v1.edn")
          (is (= :pending (:wasm-aot q))))))))

(deftest only-dataspace-claims-typed-kit-wasm-aot
  (doseq [filename application-kit-files]
    (testing filename
      (let [claimed (:wasm-aot (:qualification (load-kit filename)))]
        (if (= filename "dataspace-v1.edn")
          (is (= :implemented claimed))
          (is (= :pending claimed)))))))
