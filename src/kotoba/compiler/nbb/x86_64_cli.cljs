(ns kotoba.compiler.nbb.x86-64-cli
  "x86-64-only nbb native compiler entrypoint."
  (:require [kotoba.compiler.nbb.cli :as native-cli]
            [kotoba.compiler.nbb.cli-support :as support]
            [kotoba.compiler.nbb.compile-cache :as compile-cache]
            [kotoba.native.x86-64 :as x86-64]))

(defn- run! [args context]
  (native-cli/run! args :x86_64-kotoba-v1 x86-64/emit-program context))

(if (= "worker" (first *command-line-args*))
  (let [context (compile-cache/create-context)]
    (support/serve! #(run! % context) :x86_64-kotoba-v1))
  (support/execute! #(run! % nil)))
