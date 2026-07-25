(ns kotoba.compiler.component-heap-test
  "ADR 0076 section 4a, step 1: a component module has a real linear memory and
  a real bump `cm32p2_realloc`.

  A component cannot import `kotoba:typed`/`kotoba:heap`, so anything that is
  not a bare scalar must live in the module's own memory. Until now the emitter
  declared a zero-page memory and a realloc whose whole body was `i32.const 0`.
  These tests run the emitted allocator, rather than inspecting it, because a
  byte-level port is exactly the kind of change that can look right and be
  wrong."
  (:require [clojure.test :refer [deftest is testing]]
            [clojure.java.io :as io]
            [clojure.string :as str]
            [kotoba.compiler.backend.wasm :as wasm]
            [kotoba.compiler.wasm-tools :as wasm-tools])
  (:import [java.nio.file Files]
           [java.nio.file.attribute FileAttribute]))

(def ^:private scalar-kir
  {:format :kotoba.kir/v4 :exports ['add] :schemas {}
   :functions [{:name 'add :params ['l 'r] :param-types [:i64 :i64]
                :result :i64 :body '(+ l r)}]})

(defn- component-core-bytes []
  (wasm/emit-component-core scalar-kir :wasm32-wasi-kotoba-v1))

(defn- with-temp-module
  "Write the emitted core module to a temp file and hand the path to `f`."
  [f]
  (let [dir (Files/createTempDirectory "kotoba-heap-" (make-array FileAttribute 0))
        module (.resolve dir "core.wasm")]
    (try
      (Files/write module ^bytes (component-core-bytes)
                   (make-array java.nio.file.OpenOption 0))
      (f (str module))
      (finally
        (Files/deleteIfExists module)
        (Files/deleteIfExists dir)))))

(deftest emitted-component-module-is-valid-wasm
  (testing "the module with a real memory and allocator still validates"
    (with-temp-module
      (fn [path]
        ;; wasm-tools validate exits non-zero on a malformed module, and
        ;; run-command! turns that into an exception -- so reaching the
        ;; assertion at all is the check.
        (is (string? (wasm-tools/run-command!
                      ["wasm-tools" "validate" "--features" "all" path])))))))

(deftest module-declares-a-usable-memory-and-arena
  (with-temp-module
    (fn [path]
      (let [text (wasm-tools/run-command! ["wasm-tools" "print" path])]
        (testing "memory is no longer zero pages"
          ;; wasm-tools prints `(memory (;0;) 1)`; the index comment contains a
          ;; `)`, so match the declared minimum after it rather than before.
          (is (re-find #"\(memory \(;\d+;\) [1-9]" text)
              "a component module must declare at least one page"))
        (testing "the bump pointer is a mutable i32 global, not address 0"
          (is (re-find #"\(global.*mut i32" text))
          (is (= 8 wasm/component-arena-base)
              "address 0 must stay reserved for the Canonical ABI's null old-ptr"))
        (testing "fuel stays global 0 so every prologue is unchanged"
          ;; The fuel global must be declared before the bump pointer.
          (let [fuel-at (str/index-of text "mut i64")
                next-at (str/index-of text "mut i32")]
            (is (and fuel-at next-at (< fuel-at next-at)))))
        (testing "realloc is no longer a stub"
          (is (re-find #"cm32p2_realloc" text))
          (is (re-find #"memory\.copy" text)
              "grow must preserve old content, as the Canonical ABI requires"))))))

(deftest allocator-behaviour-is-exercised-not-assumed
  (with-temp-module
    (fn [path]
      ;; The execution below only means anything if the module can be
      ;; instantiated standalone. Assert that rather than skipping quietly:
      ;; a scalar component core must not carry host imports at all.
      (is (not (str/includes? (wasm-tools/run-command! ["wasm-tools" "print" path])
                              "(import"))
          "a scalar component core module must have no imports")
      ;; This is a core module, not a component: wasmtime takes the export
      ;; name and the arguments as separate positional args. The WAVE call
      ;; syntax `f(a, b)` is for components only.
      (letfn [(call [& args]
                (-> (wasm-tools/run-command!
                     (concat ["wasmtime" "run" "--invoke" "cm32p2_realloc" path]
                             (map str args)))
                    str str/trim))]
        ;; wasmtime prints the returned i32; a trap makes run-command! throw.
        (testing "a zero-sized request returns the null pointer"
          (is (= "0" (call 0 0 8 0))))
        (testing "allocations start at the arena base and advance"
          (let [first-ptr (call 0 0 8 16)]
            (is (= (str wasm/component-arena-base) first-ptr))))
        (testing "an over-capacity request traps rather than corrupting memory"
          (is (thrown? clojure.lang.ExceptionInfo
                       (call 0 0 8 (inc wasm/component-arena-capacity)))))
        (testing "a non-power-of-two alignment traps"
          (is (thrown? clojure.lang.ExceptionInfo (call 0 0 3 8))))
        (testing "an alignment beyond 8 traps"
          (is (thrown? clojure.lang.ExceptionInfo (call 0 0 16 8))))
        (testing "a zero alignment traps"
          (is (thrown? clojure.lang.ExceptionInfo (call 0 0 0 8))))))))
