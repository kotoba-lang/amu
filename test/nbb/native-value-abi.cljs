(ns test.nbb.native-value-abi
  "`kotoba.compiler.nbb.cli/native-value-abi` must select from the SAME four
  branches the JVM compiler, the wasm CLI and the verifier select from.

  It selected from two. Measured 2026-08-30 against `bin/amu` on this repo's
  own reproduction: a module using `vector-f64` compiled to `aarch64-macos`
  exited 65 with `native compatibility metadata rejected`, because this driver
  stamped `:kotoba.typed/externref-v1` while `kotoba.verifier` re-derived
  `:kotoba.typed/mixed-f64-v2` from the KIR it had just sealed. After the fix
  the same file exits 0 and the artifact carries `mixed-f64-v2`.

  The diagnostic named the metadata rather than the missing branch, so the
  failure read as an unsupported program rather than a driver that could not
  describe it -- which is why it survived: nothing about it says `f64`."
  (:require [kotoba.compiler.nbb.cli :as cli]))

(def ^:private failures (atom 0))

(defn- check! [label expected actual]
  (if (= expected actual)
    (println (str "ok   " label " => " actual))
    (do (swap! failures inc)
        (println (str "FAIL " label " expected " expected " got " actual)))))

(defn- module [body result]
  {:format :kotoba.kir/v4 :entry 'main :exports ['main]
   :functions [{:name 'main :params [] :param-types [] :result result :body body}]})

;; Every branch, including the two that were unreachable. `uses-f32?`/`uses-f64?`
;; are kotoba-kir's, so this pins agreement with the producer rather than
;; restating its answer.
(check! "no floating point, typed values"
        :kotoba.typed/externref-v1
        (cli/native-value-abi (module '(+ 1 2) :i64) true))
(check! "no floating point, untyped"
        :kotoba.i64/direct-v1
        (cli/native-value-abi (module '(+ 1 2) :i64) false))
(check! "f64 present"
        :kotoba.typed/mixed-f64-v2
        (cli/native-value-abi (module '(f64-add 1 2) :i64) true))
(check! "f32 present outranks f64"
        :kotoba.typed/mixed-f32-f64-v3
        (cli/native-value-abi (module '(f32-add 1 2) :i64) true))

;; The shape that actually failed. An f64 LITERAL is desugared by the frontend
;; into `f64-from-bits`, so a vector-f64 module carrying one is an f64 program
;; even though nothing in it is spelled f64 at a boundary. Before the fix this
;; returned externref-v1 and the artifact was refused.
(check! "vector-f64 module carrying an f64 literal is an f64 program"
        :kotoba.typed/mixed-f64-v2
        (cli/native-value-abi
         (module '(vector-f64-count (vector-f64-conj (vector-f64-new)
                                                     (f64-from-bits 4609434218613702656)))
                 :i64)
         true))

;; A driver that answered `mixed-f64-v2` unconditionally would pass every
;; assertion above except this one.
(check! "the f64 branch is conditional, not the default"
        :kotoba.i64/direct-v1
        (cli/native-value-abi (module '(* 3 4) :i64) false))

(if (pos? @failures)
  (do (println (str "\n" @failures " failure(s)")) (.exit js/process 1))
  (println "\nnative-value-abi: all branches reachable"))
