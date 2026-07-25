(ns kotoba.compiler.general-capability-component-test
  "ADR 0076 increment 1: a capability-using component is no longer restricted to
  four hand-written single-function shapes.

  The blocker was that the general component path imported the generic
  `kotoba:typed`/`cap-call` intrinsic, which no WIT interface can be bound to.
  Each `typed-cap-call` now becomes a call to its own typed import, so any
  program shape works as long as its exports and capability calls are scalar."
  (:require [clojure.test :refer [deftest is testing]]
            [clojure.string :as str]
            [kotoba.compiler.core :as compiler]
            [kotoba.compiler.component-core :as component-core]
            [kotoba.compiler.frontend :as frontend]
            [kotoba.compiler.ir :as ir]))

;; A shape that was rejected before this increment: several functions, real
;; computation on both sides of the capability call, and two exports.
(def ^:private multi-function-source
  "(ns app)
   (defn scale [x :i64] :i64 (* x 2))
   (defn offset [x :i64] :i64 (+ x 7))
   (defn measure [request :i64] :i64
     (offset (typed-cap-call 211 :i64 :i64 (scale request))))
   (defn twice [request :i64] :i64
     (+ (typed-cap-call 211 :i64 :i64 request)
        (typed-cap-call 211 :i64 :i64 request)))")

(defn- kir [source] (ir/lower (frontend/analyze source)))

(deftest multi-function-capability-program-is-admitted
  (testing "the general lowering claims this shape"
    (is (= :scalar-with-capabilities
           (component-core/assert-supported! (kir multi-function-source)))))
  (testing "the four hand-written shapes still win where they applied"
    ;; A bare passthrough is still :scalar-capability-call, so this increment
    ;; changes no existing artifact.
    (is (= :scalar-capability-call
           (component-core/assert-supported!
            (kir "(ns app)
                  (defn measure [request :i64] :i64
                    (typed-cap-call 211 :i64 :i64 request))"))))))

(deftest capability-imports-are-typed-and-deduplicated
  (let [imports (component-core/scalar-capability-imports (kir multi-function-source))]
    (testing "one import per capability id, not per call site"
      (is (= 1 (count imports)))
      (is (= 211 (:id (first imports)))))
    (testing "named for the standard32 binding wasm-tools resolves"
      (is (str/starts-with? (:module (first imports)) "cm32p2|kotoba:application/"))
      (is (str/ends-with? (:module (first imports)) "@1")))
    (testing "signature is the scalar lowering: one param, one result"
      ;; 0x60 = functype, then param count / types, then result count / types.
      (is (= [0x60 1 0x7e 1 0x7e] (:type (first imports)))))))

(deftest non-scalar-capability-is-still-fail-closed
  (testing "a capability id with no contract entry is refused"
    (is (nil? (component-core/scalar-capability-imports
               (kir "(ns app)
                     (defn measure [request :i64] :i64
                       (typed-cap-call 9999 :i64 :i64 request))")))))
  (testing "a program with no capability call has no capability imports"
    (is (nil? (component-core/scalar-capability-imports
               (kir "(ns app) (defn main [] :i64 42)"))))))

(deftest emitted-core-module-binds-the-capability-directly
  (let [bytes (component-core/emit (kir multi-function-source) :wasm32-wasi-kotoba-v1)
        text (String. (byte-array (map unchecked-byte bytes)) "ISO-8859-1")]
    (testing "the module imports the typed capability, not the generic intrinsic"
      (is (str/includes? text "cm32p2|kotoba:application/")
          "per-capability import name is absent")
      (is (not (str/includes? text "kotoba:typed"))
          "the generic cap-call intrinsic must not be imported once bound"))))

(deftest declared-fuel-still-reaches-a-capability-component
  ;; The new lowering goes through the real backend, so it must keep the
  ;; property ADR 0075 established rather than silently becoming host-only.
  (is (= :module-global
         (component-core/fuel-enforcement (kir multi-function-source)))))
