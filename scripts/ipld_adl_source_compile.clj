(ns ipld-adl-source-compile
  (:require [kotoba.compiler.core :as compiler])
  (:import (java.nio.file Files Paths)
           (java.nio.file.attribute FileAttribute)))

(def ^:private identity-source
  "(ns adl.identity
       (:export [validate-representation decode encode validate-logical]))
   (defn validate-representation [value :bytes] :bool true)
   (defn decode [value :bytes] :bytes value)
   (defn encode [value :bytes] :bytes value)
   (defn validate-logical [value :bytes] :bool true)")

(def ^:private closed-source
  "(ns adl.closed
       (:export [validate-representation decode encode validate-logical]))
   (defn validate-representation [value :bytes] :bool true)
   (defn decode [value :bytes] :bytes (bytes))
   (defn encode [value :bytes] :bytes value)
   (defn validate-logical [value :bytes] :bool false)")

(def ^:private projection-source
  "(ns adl.projection
       (:export [validate-representation decode encode validate-logical]))
   (defn validate-representation [value :bytes] :bool true)
   (defn decode [value :bytes] :bytes (bytes))
   (defn encode [value :bytes] :bytes value)
   (defn validate-logical [value :bytes] :bool true)")

(def ^:private input-count-source
  "(ns adl.input-count
       (:export [validate-representation decode encode validate-logical]))
   (defn validate-representation [value :bytes] :bool (= (bytes-count value) 4))
   (defn decode [value :bytes] :bytes value)
   (defn encode [value :bytes] :bytes value)
   (defn validate-logical [value :bytes] :bool (= (bytes-count value) 4))")

;; 0xA1 is the first byte of the four-byte ABI input used by the harness.
(def ^:private byte-at-source
  "(ns adl.byte-at
       (:export [validate-representation decode encode validate-logical]))
   (defn validate-representation [value :bytes] :bool (= (bytes-at value 0) 161))
   (defn decode [value :bytes] :bytes value)
   (defn encode [value :bytes] :bytes value)
   (defn validate-logical [value :bytes] :bool (= (bytes-at value 0) 161))")

;; Driven through the schema capability rather than the raw runner, the ADL
;; receives the DAG-CBOR *encoded* node, not the payload bytes. The conformance
;; harness passes a three-byte value, so operand byte 0 is 0x43 = 67 -- the CBOR
;; byte-string header for length 3 -- and not 0x01. Measured, not assumed: a
;; module asserting 1 here is rejected by the schema, and one asserting 67
;; passes with its signed receipts. That is the correct reading for
;; `validate-representation`, which is supposed to see the representation.
(def ^:private byte-at-cbor-source
  "(ns adl.byte-at-cbor
       (:export [validate-representation decode encode validate-logical]))
   (defn validate-representation [value :bytes] :bool (= (bytes-at value 0) 67))
   (defn decode [value :bytes] :bytes value)
   (defn encode [value :bytes] :bytes value)
   (defn validate-logical [value :bytes] :bool (= (bytes-at value 0) 67))")

;; Index 3 is the last byte of that same input and is out of range for any
;; shorter one, so one module covers true, false, and the bounds trap.
(def ^:private byte-at-3-source
  "(ns adl.byte-at-3
       (:export [validate-representation decode encode validate-logical]))
   (defn validate-representation [value :bytes] :bool (= (bytes-at value 3) 1))
   (defn decode [value :bytes] :bytes value)
   (defn encode [value :bytes] :bytes value)
   (defn validate-logical [value :bytes] :bool (= (bytes-at value 3) 1))")

(defn -main [& [output profile]]
  (when-not output
    (throw (ex-info "output path required" {:phase :ipld-adl-source-compile})))
  (Files/write (Paths/get output (make-array String 0))
               (:bytes (compiler/compile-ipld-adl-source
                        (case profile
                          "closed" closed-source
                          "projection" projection-source
                          "input-count" input-count-source
                          "byte-at" byte-at-source
                          "byte-at-cbor" byte-at-cbor-source
                          "byte-at-3" byte-at-3-source
                          identity-source)))
               (make-array java.nio.file.OpenOption 0)))
