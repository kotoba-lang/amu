(ns kotoba.compiler.nbb.aarch64-cli
  "AArch64-only nbb native compiler entrypoint."
  (:require [kotoba.compiler.nbb.cli :as native-cli]
            [kotoba.compiler.nbb.cli-support :as support]
            [kotoba.compiler.nbb.compile-cache :as compile-cache]
            [kotoba.native.aarch64 :as aarch64]))

(defn- run! [args context]
  (native-cli/run! args :aarch64-kotoba-v1 aarch64/emit-program context))

(if (= "worker" (first *command-line-args*))
  (let [context (compile-cache/create-context)]
    (support/serve! #(run! % context) :aarch64-kotoba-v1))
  (support/execute! #(run! % nil)))
