#!/usr/bin/env nbb
;; Bounded-execution conformance for the Wasmtime ADL engine.
;;
;; Ported from the POSIX shell script this replaces; `check-workflows.cljs`
;; refuses any `.sh` in the tree, and a failing lint step skips every test step
;; behind it, so a shell script here silently costs the whole suite.
;;
;; The port keeps the shape of every assertion, including the ones whose reason
;; is the comment above them. Byte-exact expectations are Buffers rather than
;; `printf` octal escapes, and `cmp` is a Buffer comparison, so the checks no
;; longer depend on the host's printf accepting `\241`.
(ns test-ipld-adl-wasmtime
  (:require [clojure.string :as str]
            [scripts.lib :as lib]
            ["node:fs" :as fs]))

(def tmp (lib/temp-dir "kotoba-ipld-adl-"))
(defn at [& parts] (apply lib/join tmp parts))
(def runner (at "runner"))

(defn bytes! [name & values]
  (let [file (at name)]
    (.writeFileSync fs file (js/Buffer.from (clj->js (vec values))))
    file))

(defn zeros! [name n]
  (let [file (at name)]
    (.writeFileSync fs file (.alloc js/Buffer n))
    file))

(defn size [file] (.-size (.statSync fs file)))
(defn same-bytes? [a b] (zero? (.compare js/Buffer (.readFileSync fs a) (.readFileSync fs b))))
(defn is-bytes? [file values]
  (zero? (.compare js/Buffer (.readFileSync fs file) (js/Buffer.from (clj->js (vec values))))))

(defn adl
  "One engine invocation. The positional argument list is the runner's own ABI:
   module, input, output, operation, fuel, allocation, memory pages, timeout
   milliseconds, output limit."
  ([module input output operation] (adl module input output operation {}))
  ([module input output operation
    {:keys [fuel alloc pages timeout max-output]
     :or {fuel 100000 alloc 1024 pages 2 timeout 1000 max-output 1048576}}]
   (lib/run runner
            (mapv str [module input output operation fuel alloc pages timeout max-output])
            {:allow-failure? true})))

(defn ok!
  ([module input output operation] (ok! module input output operation {}))
  ([module input output operation options]
   (let [result (adl module input output operation options)]
     (lib/ensure! (zero? (:status result))
                  (str "ipld-adl-wasmtime: expected success from " module
                       " operation " operation "\n" (:stdout result) (:stderr result)))
     result)))

(defn refused!
  "The engine must refuse for the STATED reason. Checking only that something
   failed would keep passing with the very check under test deleted."
  ([module input operation code] (refused! module input operation code {}))
  ([module input operation code options]
   (let [result (adl module input (at "out") operation options)]
     (lib/ensure! (str/includes? (:stdout result) (str "\"code\":\"" code "\""))
                  (str "ipld-adl-wasmtime: expected " code " from " module
                       " operation " operation "\n" (:stdout result) (:stderr result))))))

(defn wasm!
  "A hand-authored fixture module, assembled by wasm-tools."
  [name text]
  (let [wat (at (str name ".wat")) wasm (at (str name ".wasm"))]
    (lib/write-text! wat (str text "\n"))
    (lib/run "wasm-tools" ["parse" wat "-o" wasm])
    wasm))

(defn from-source!
  "The same ABI compiled from Kotoba source, not a hand-authored fixture."
  ([name] (from-source! name nil))
  ([name variant]
   (let [wasm (at (str "kotoba-" name ".wasm"))]
     (lib/run "clojure"
              (into ["-Sdeps" "{:paths [\"src\" \"resources\" \"scripts\"]}"
                     "-M" "-m" "ipld-adl-source-compile" wasm]
                    (remove nil? [variant])))
     (lib/run "wasm-tools" ["validate" wasm])
     wasm)))

(defn conformance! [& args]
  (lib/run "clojure" (into ["-M:ipld-adl-conformance"] (map str args))))

(try
  (lib/run "nbb" ["scripts/build-ipld-adl-wasmtime.cljs" runner])

  (let [identity-wasm
        (wasm! "identity"
               "(module
  (memory (export \"memory\") 1 2)
  (data (i32.const 0) \"\\f5\")
  (func (export \"adl_alloc\") (param i32) (result i32) i32.const 1024)
  (func (export \"adl_transform\") (param i32 i32 i32) (result i64)
    local.get 0 i32.const 0 i32.eq
    local.get 0 i32.const 3 i32.eq
    i32.or
    if (result i64)
      i64.const 1
    else
      local.get 1 i64.extend_i32_u i64.const 32 i64.shl
      local.get 2 i64.extend_i32_u i64.or
    end))")
        forever-wasm
        (wasm! "forever"
               "(module
  (memory (export \"memory\") 1 1)
  (func (export \"adl_alloc\") (param i32) (result i32) i32.const 0)
  (func (export \"adl_transform\") (param i32 i32 i32) (result i64)
    (loop $again br $again) i64.const 0))")
        imported-wasm
        (wasm! "imported"
               "(module
  (import \"wasi_snapshot_preview1\" \"random_get\" (func))
  (memory (export \"memory\") 1 1)
  (func (export \"adl_alloc\") (param i32) (result i32) i32.const 0)
  (func (export \"adl_transform\") (param i32 i32 i32) (result i64) i64.const 0))")
        growing-wasm
        (wasm! "growing"
               "(module
  (memory (export \"memory\") 1)
  (func (export \"adl_alloc\") (param i32) (result i32)
    i32.const 1 memory.grow drop i32.const 0)
  (func (export \"adl_transform\") (param i32 i32 i32) (result i64) i64.const 0))")

        source-identity (from-source! "identity")
        source-closed (from-source! "closed" "closed")
        source-projection (from-source! "projection" "projection")
        source-input-count (from-source! "input-count" "input-count")
        source-byte-at (from-source! "byte-at" "byte-at")
        source-byte-at-3 (from-source! "byte-at-3" "byte-at-3")
        source-byte-at-cbor (from-source! "byte-at-cbor" "byte-at-cbor")
        source (into {} (for [variant ["slice" "slice-empty" "join" "join-double"
                                       "composed" "slice-of-join" "noncanonical"]]
                          [variant (from-source! variant variant)]))

        input (bytes! "input.cbor" 0xa1 0x61 0x61 0x01)
        short (bytes! "short.cbor" 0x40)
        empty (bytes! "empty.cbor")
        big (zeros! "big.cbor" 200000)
        mid (zeros! "mid.cbor" 4096)
        big50 (zeros! "big50.cbor" 50000)
        output (at "output.cbor")
        kotoba-output (at "kotoba-output.cbor")]

    (let [receipt (:stdout (ok! identity-wasm input output 1))]
      (lib/ensure! (same-bytes? input output) "ipld-adl-wasmtime: identity did not round-trip")
      (doseq [fragment ["\"status\":\"ok\"" "\"fuelUsed\":" "\"memoryPages\":1"]]
        (lib/ensure! (str/includes? receipt fragment)
                     (str "ipld-adl-wasmtime: receipt is missing " fragment "\n" receipt))))

    (doseq [operation [1 2]]
      (ok! source-identity input kotoba-output operation)
      (lib/ensure! (same-bytes? input kotoba-output)
                   (str "ipld-adl-wasmtime: Kotoba identity changed the operand at " operation)))
    (doseq [operation [0 3]]
      (ok! source-identity input kotoba-output operation)
      (lib/ensure! (is-bytes? kotoba-output [0xf5])
                   (str "ipld-adl-wasmtime: Kotoba identity did not validate at " operation)))

    ;; The validator result is derived from the actual ABI input length.
    (doseq [operation [0 3]]
      (ok! source-input-count input kotoba-output operation)
      (lib/ensure! (is-bytes? kotoba-output [0xf5])
                   "ipld-adl-wasmtime: input-count answered false for a four-byte input")
      (ok! source-input-count short kotoba-output operation)
      (lib/ensure! (is-bytes? kotoba-output [0xf4])
                   "ipld-adl-wasmtime: input-count answered true for a one-byte input"))

    ;; bytes-at reads one unsigned byte out of the ABI input. The bound is the
    ;; input length, not the linear memory size: the input sits at offset 1024 of
    ;; a two-page memory, so an out-of-range index would otherwise read whatever
    ;; follows it and answer confidently.
    (doseq [operation [0 3]]
      ;; Byte 0 of the four-byte input is 0xA1 = 161.
      (ok! source-byte-at input kotoba-output operation)
      (lib/ensure! (is-bytes? kotoba-output [0xf5]) "ipld-adl-wasmtime: byte-at 0 of the operand")
      ;; Byte 0 of the one-byte input is 0x40: in range, and a well-formed false.
      (ok! source-byte-at short kotoba-output operation)
      (lib/ensure! (is-bytes? kotoba-output [0xf4]) "ipld-adl-wasmtime: byte-at 0 of a one-byte operand")
      ;; Byte 3 of the four-byte input is 0x01.
      (ok! source-byte-at-3 input kotoba-output operation)
      (lib/ensure! (is-bytes? kotoba-output [0xf5]) "ipld-adl-wasmtime: byte-at 3 of the operand")
      ;; Index 3 of a one-byte input traps rather than reading past the operand.
      (refused! source-byte-at-3 short operation "guest-trap")
      ;; Every index is out of range for an empty input, including index 0.
      (refused! source-byte-at empty operation "guest-trap")
      ;; An input larger than the fixed allocation traps in adl_alloc, before any
      ;; byte is read.
      (refused! source-byte-at big operation "allocation-trap"))

    ;; bytes-slice returns a bounded view into the ABI input: the operand's own
    ;; pointer moved forward, never a copy. Decode is [1,3) of the four-byte input.
    (ok! (source "slice") input kotoba-output 1)
    (lib/ensure! (is-bytes? kotoba-output [0x61 0x61]) "ipld-adl-wasmtime: slice decode")
    ;; encode stays identity, so the same module does not slice both directions.
    (ok! (source "slice") input kotoba-output 2)
    (lib/ensure! (same-bytes? input kotoba-output) "ipld-adl-wasmtime: slice encode is not identity")
    ;; An empty subrange is a well-formed answer, not a trap: start = end is in range.
    (ok! (source "slice-empty") input kotoba-output 1)
    (lib/ensure! (zero? (size kotoba-output)) "ipld-adl-wasmtime: empty subrange is not empty")
    ;; An end past the operand traps rather than returning a pointer into whatever
    ;; follows the input inside the two-page memory.
    (refused! (source "slice") short 1 "guest-trap")
    (refused! (source "slice") empty 1 "guest-trap")
    ;; The runner's own output bound still applies to a view it did not choose.
    (refused! (source "slice") input 1 "output-limit-exceeded" {:alloc 1})

    ;; bytes-concat is the first body that has to write. Rotating the input proves
    ;; the destination does not overlap it: byte 0 is copied *after* bytes 1..2, so
    ;; a destination starting at the operand would have destroyed it first.
    (ok! (source "join") input kotoba-output 1)
    (lib/ensure! (is-bytes? kotoba-output [0x61 0x61 0xa1]) "ipld-adl-wasmtime: join rotation")
    ;; The operand itself is untouched: encode is identity in the same module.
    (ok! (source "join") input kotoba-output 2)
    (lib/ensure! (same-bytes? input kotoba-output) "ipld-adl-wasmtime: join disturbed the operand")
    ;; An offset past the operand traps before anything is written.
    (refused! (source "join") short 1 "guest-trap")

    ;; The join pays per byte moved. Same module, same fuel, two input sizes: the
    ;; small one completes and the large one runs out. A bulk-copy lowering would
    ;; complete both, which is exactly the hole this checks for. The budget below
    ;; was chosen by measuring both ends rather than guessed; do not treat it as a
    ;; fixed cost, since it depends on the engine version. Re-measure by running
    ;; either case with a large budget and reading fuelUsed.
    (ok! (source "join-double") input kotoba-output 1 {:fuel 50000 :alloc 65536})
    (lib/ensure! (= 8 (size kotoba-output)) "ipld-adl-wasmtime: join-double length")
    (refused! (source "join-double") mid 1 "fuel-exhausted" {:fuel 50000 :alloc 65536})
    ;; With fuel to match the work, the same large input completes at 2x length.
    (ok! (source "join-double") mid kotoba-output 1 {:fuel 10000000 :alloc 65536})
    (lib/ensure! (= 8192 (size kotoba-output)) "ipld-adl-wasmtime: join-double large length")
    ;; Operand plus result must fit the module's own memory: 3x50000 exceeds the
    ;; two-page input capacity, and the check runs before the first store.
    (refused! (source "join-double") big50 1 "guest-trap" {:fuel 10000000 :alloc 1048576})

    ;; Composition. The operand is A1 61 61 01. The inner join builds 61 61 A1 at
    ;; the cursor; the outer join writes 01 first and then copies that result, so a
    ;; destination reusing the inner buffer would clobber it and yield 01 01 61 A1.
    (ok! (source "composed") input kotoba-output 1)
    (lib/ensure! (is-bytes? kotoba-output [0x01 0x61 0x61 0xa1]) "ipld-adl-wasmtime: composed join")
    ;; A subrange of a materialised result: bytes [2,5) of the operand doubled.
    (ok! (source "slice-of-join") input kotoba-output 1)
    (lib/ensure! (is-bytes? kotoba-output [0x61 0x01 0xa1]) "ipld-adl-wasmtime: slice of join")
    ;; Every offset in a composed expression is still bounded by the length of the
    ;; thing it indexes, so a short operand traps rather than reading a stale buffer.
    (refused! (source "composed") short 1 "guest-trap")
    (refused! (source "slice-of-join") empty 1 "guest-trap")

    ;; Non-identity source semantics: decode returns the canonical empty bytes node,
    ;; encode stays identity, and validate-logical returns canonical false.
    (ok! source-closed input kotoba-output 1)
    (lib/ensure! (is-bytes? kotoba-output [0x40]) "ipld-adl-wasmtime: closed decode")
    (ok! source-closed input kotoba-output 2)
    (lib/ensure! (same-bytes? input kotoba-output) "ipld-adl-wasmtime: closed encode is not identity")
    (ok! source-closed input kotoba-output 3)
    (lib/ensure! (is-bytes? kotoba-output [0xf4]) "ipld-adl-wasmtime: closed validate")

    (refused! forever-wasm input 1 "fuel-exhausted" {:fuel 5 :pages 1})
    (refused! forever-wasm input 1 "timeout" {:fuel 100000000000 :pages 1 :timeout 10})
    (refused! imported-wasm input 1 "forbidden-import" {:pages 1})
    (let [result (adl growing-wasm input (at "out") 1 {:pages 1})]
      (lib/ensure! (str/includes? (:stdout result) "\"memoryPages\":1")
                   (str "ipld-adl-wasmtime: memory bound not reported\n" (:stdout result))))
    (refused! identity-wasm input 1 "output-limit-exceeded" {:alloc 1})

    (conformance! runner identity-wasm)
    (conformance! runner source-projection "empty")
    ;; The indexed-byte lowering also runs through the schema capability, so its
    ;; bounded execution is covered by the same signed measured receipts. Note the
    ;; operand there is the DAG-CBOR encoded node, not the payload bytes.
    (conformance! runner source-byte-at-cbor)
    ;; A subrange round-trips through the schema only when the subrange is itself a
    ;; node: 42 41 05 is the encoding of the two-byte value 0x41 0x05, and [1,3) is
    ;; the CBOR byte string holding 0x05.
    (conformance! runner (source "slice") "05" "4105")
    ;; The grammar is closed over bytes, so a perfectly faithful lowering can still
    ;; return something canonical DAG-CBOR would not have written. 18 05 decodes as
    ;; the integer 5, so decoding alone accepts it; the roundtrip does not.
    ;; Requiring the capability's own reason, not merely a refusal, is deliberate:
    ;; ipld.schema refuses this too, so an assertion that only checked "something
    ;; threw" would keep passing with the capability's check deleted.
    (conformance! runner (source "noncanonical") "reject:not canonical DAG-CBOR" "1805"))

  (println (str "ipld-adl-wasmtime: Kotoba-source input-dependent validation, "
                "indexed unsigned byte reads, bounded subrange views, per-byte joins, "
                "and composed expressions allocating above every live operand, with "
                "operand-length bounds traps, canonical-codec refusal, non-identity "
                "projection, engine fuel, timeout, import denial, memory, and output "
                "bounds passed"))
  (finally (lib/remove-tree! tmp)))
