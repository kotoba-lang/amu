(ns kotoba.compiler.component-test
  (:require [clojure.java.shell :as shell]
            [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.component :as component]
            [kotoba.compiler.core :as compiler])
  (:import [java.nio.charset StandardCharsets]
           [java.nio.file Files Path]))

(defn- with-temp-component [bytes f]
  (let [path (Files/createTempFile "kotoba-component-test-" ".wasm"
                                   (make-array java.nio.file.attribute.FileAttribute 0))]
    (try
      (Files/write path bytes (make-array java.nio.file.OpenOption 0))
      (f path)
      (finally (Files/deleteIfExists path)))))

(deftest component-target-emits-a-standard-closed-world
  (let [compiled (compiler/compile-source "(defn main [] 42)" :wasm-component-kotoba-v1)]
    (is (= :wasm-component/v1 (:format compiled)))
    (is (= "kotoba:app/kotoba-app@0.1.0" (:component-world compiled)))
    (is (= #{} (:capabilities compiled)))
    (is (= [0 0x61 0x73 0x6d]
           (mapv #(bit-and (int %) 0xff) (take 4 (:bytes compiled)))))
    (with-temp-component
      (:bytes compiled)
      (fn [path]
        (let [validated (shell/sh "wasm-tools" "validate" (.toString path))]
          (is (zero? (:exit validated)) (:err validated)))
        ;; Native engine execution is qualified independently by the
        ;; cross-platform `test-wasmtime` suite. This test owns only the
        ;; Component artifact/WIT contract and therefore has no ambient CLI
        ;; engine dependency.
        (let [wit (Files/createTempFile "kotoba-component-world-" ".wit"
                                        (make-array java.nio.file.attribute.FileAttribute 0))]
          (try
            (Files/writeString wit (component/world-wit #{}) StandardCharsets/UTF_8
                               (make-array java.nio.file.OpenOption 0))
            (let [targeted (shell/sh "wasm-tools" "component" "targets" (.toString wit) (.toString path)
                                 "--world" "kotoba:app/kotoba-app@0.1.0")]
              (is (zero? (:exit targeted)) (:err targeted)))
            (finally (Files/deleteIfExists wit))))))))

(deftest component-target-fails-closed-outside-the-first-wit-world
  (doseq [source ["(defn helper [] 1) (defn main [] 42)"
                  "(defn main [] (pair-first (pair 1 2)))"]]
    (let [error (try
                  (compiler/compile-source source :wasm-component-kotoba-v1)
                  nil
                  (catch clojure.lang.ExceptionInfo error error))]
      (is error)
      (is (= :component-abi (:phase (ex-data error)))))))

(deftest typed-capability-v2-target-is-pure-until-grant-resource-lowering-exists
  (let [compiled (compiler/compile-source "(defn main [] 42)" :wasm-component-kotoba-v2)]
    (is (= :wasm-component/v2 (:format compiled)))
    (is (= "kotoba:app/kotoba-app@0.2.0" (:component-world compiled))))
  (let [error (try
                (compiler/compile-source
                 "(ns app (:capabilities #{:clock/now})) (defn main [] (cap-call :clock/now 0))"
                 :wasm-component-kotoba-v2
                 {:allow #{[:cap/call 7]} :component-abilities {7 {:target "clock://monotonic"
                                                                      :operation :clock/now
                                                                      :max-bytes 1 :max-items 1
                                                                      :deadline-ms 1 :audit-id "v2"}}})
                nil
                (catch clojure.lang.ExceptionInfo e e))]
    (is (= :component-abi-v2 (:phase (ex-data error))))))

(deftest component-capabilities-are-named-wit-imports-not-an-ambient-wasi-surface
  (let [source "(ns app (:capabilities #{:clock/now})) (defn main [] (cap-call :clock/now 0))"
        compiled (compiler/compile-source source :wasm-component-kotoba-v1
                                          {:allow #{[:cap/call 7]}
                                           :component-abilities
                                           {7 {:target "clock://monotonic"
                                               :operation :clock/now
                                               :max-bytes 1 :max-items 1
                                               :deadline-ms 10 :audit-id "test-clock"}}})]
    (is (= #{:aiueos.component/aiueos-clock-now} (:capabilities compiled)))
    (is (= {:target "clock://monotonic" :operation :clock/now
            :max-bytes 1 :max-items 1 :deadline-ms 10 :audit-id "test-clock"}
           (get-in compiled [:component-imports :aiueos.component/aiueos-clock-now])))
    (is (.contains (component/world-wit #{7}) "import aiueos-clock-now"))
    (is (not (.contains (component/world-wit #{7}) "wasi:")))))

(deftest effectful-components-require-a-fully-scoped-ability-descriptor
  (is (thrown-with-msg? clojure.lang.ExceptionInfo #"descriptor is required"
                        (compiler/compile-source
                         "(defn main [] (cap-call 7 0))"
                         :wasm-component-kotoba-v1
                         {:allow #{[:cap/call 7]}}))))
