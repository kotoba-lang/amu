(ns kotoba.compiler.ios-aot-test
  (:require [clojure.test :refer [deftest is]]
            [kotoba.artifact.core :as artifact]
            [kotoba.compiler.core :as compiler]
            [kotoba.compiler.ios-aot :as ios-aot]))

(def source
  "(defn helper [x] (+ x 1)) (defn main [] (helper 41))")

(deftest packages-verified-ios-code-as-deterministic-macho-object
  (let [ios (:artifact (compiler/compile-source source :aarch64-ios-kotoba-v1))
        first (ios-aot/package ios 'main)
        second (ios-aot/package ios 'main)]
    (is (= (seq (:object first)) (seq (:object second))))
    (is (= (:manifest first) (:manifest second)))
    (is (= [0xcf 0xfa 0xed 0xfe]
           (mapv #(bit-and (int %) 0xff) (take 4 (:object first)))))
    (is (= :kotoba.ios-aot/v2 (get-in first [:manifest :format])))
    (is (= :aarch64-ios-kotoba-v1 (get-in first [:manifest :target])))
    (is (= :ios (get-in first [:manifest :platform])))
    (is (= [15 0 0] (get-in first [:manifest :minimum-os])))
    (is (= 0 (get-in first [:manifest :entry :arity])))
    (is (= (artifact/sha256
            (mapv #(bit-and (int %) 0xff) (:object first)))
           (get-in first [:manifest :object-sha256])))))

(deftest packages-device-and-simulator-platforms-explicitly
  (let [ios (:artifact (compiler/compile-source source :aarch64-ios-kotoba-v1))]
    (is (= :ios-simulator
           (get-in (ios-aot/package ios 'main {:platform :ios-simulator})
                   [:manifest :platform])))
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"platform is unsupported"
                          (ios-aot/package ios 'main {:platform :invented})))))

(deftest rejects-non-ios-and-substituted-artifacts
  (let [android (:artifact (compiler/compile-source source :aarch64-android-kotoba-v1))
        ios (:artifact (compiler/compile-source source :aarch64-ios-kotoba-v1))]
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"explicit iOS target"
                          (ios-aot/package android 'main)))
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"target profile"
                          (ios-aot/package
                           (artifact/seal
                            (assoc ios :target-profile (:target-profile android))) 'main)))
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"not exported"
                          (ios-aot/package ios 'missing)))))
