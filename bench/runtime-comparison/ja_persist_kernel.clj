;; Persist the compiled wasm bytes next to the fixture so the probe (and any
;; later tick) can reload without recompiling.
(require '[clojure.edn :as edn]
         '[clojure.java.io :as io]
         '[kotoba.runtime :as runtime])

(let [forms (runtime/read-forms (slurp "../amu/bench/runtime-comparison/kernel.kotoba") :kotoba)
      wasm  (runtime/wasm-binary forms)]
  (assert (:kotoba.wasm/ok? wasm) (pr-str (:kotoba.wasm/problems wasm)))
  (spit "/tmp/ja-probe/kernel_wasm_bytes.edn"
        (binding [*print-length* nil] (pr-str (vec (:kotoba.wasm/binary wasm)))))
  (println "wrote bytes:" (count (:kotoba.wasm/binary wasm))
           "exports:" (:exports wasm)))
