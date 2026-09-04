;; J-A groundwork (jit-cosientist, 2026-09-04 ~21:30 JST): measure how long a
;; kotoba wasm module takes to (a) instantiate under Chicory and (b) execute
;; N calls of an exported kernel through the interpreter. Compiled once;
;; run later on a quiet host. Harness-validity probe ONLY: no JIT claim, no
;; perfgate verdict. Numbers produced under load are labeled as such.
;;
;; JVM route note: this is NOT a Q9 compiler route. It drives the existing
;; chicory test dependency (kotoba/test/kotoba/wasm_exec_test.clj) as a
;; diagnostic, exactly like that suite does.
;;
;; Usage: clojure -M -m ja.chicory-probe <wasm-bytes-file> <n> <calls>
(ns ja.chicory-probe
  (:require [clojure.edn :as edn]
            [clojure.java.io :as io]
            [kotoba.wasm-exec :as wasm-exec]))

(defn read-wasm [path]
  (let [edn (edn/read-string (slurp path))
        v   (or (when (vector? edn) edn)                ; persisted plain byte vector
                (:kotoba.wasm/bytes edn)
                (when-let [b (:kotoba.wasm/binary edn)] (vec b)))]
    (when-not (and (sequential? v) (pos? (count v)))
      (throw (ex-info "no wasm bytes in artifact" {:path path})))
    (byte-array (map #(unchecked-byte %) v))))

(defn now-ns []
  (System/nanoTime))

(defn -main [& [wasm-path n-text calls-text]]
  (let [wasm (read-wasm wasm-path)
        n    (Long/parseLong n-text)
        calls (Long/parseLong calls-text)
        ;; instantiate once (timed separately from execution)
        t0 (now-ns)
        ;; call-export with empty extra-host-fns; kernel takes one i64 arg
        instance (wasm-exec/instantiate wasm [] nil)
        t1 (now-ns)
        _ (wasm-exec/call-export instance "kernel" [n] :i64) ; warm/jit-priming call
        t2 (now-ns)
        ;; timed steady-state loop
        t3 (now-ns)
        last (loop [i 0 acc (long 0)]
               (if (< i calls)
                 (recur (inc i)
                        (unchecked-add acc (wasm-exec/call-export instance "kernel" [n] :i64)))
                 acc))
        t4 (now-ns)]
    (println (format "instantiation-ms %.1f warmup-call-ms %.1f steady-us-per-call %.3f calls %d checksum %d"
                     (/ (- t1 t0) 1e6) (/ (- t2 t1) 1e6)
                     (/ (- t4 t3) 1000.0 calls) calls last))
    (flush)))
