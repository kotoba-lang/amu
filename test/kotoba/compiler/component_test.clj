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
        ;; This is a Component invocation, not execution of the internal
        ;; core module.  No WASI directory, environment, or network grant is
        ;; supplied, so a successful instantiation demonstrates the closed
        ;; world runs on the single Component runtime boundary.
        (let [executed (shell/sh "wasmtime" "--invoke" "main()" (.toString path))]
          (is (zero? (:exit executed)) (:err executed)))
        (let [wit (Files/createTempFile "kotoba-component-world-" ".wit"
                                        (make-array java.nio.file.attribute.FileAttribute 0))]
          (try
            (Files/writeString wit component/world-wit StandardCharsets/UTF_8
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
