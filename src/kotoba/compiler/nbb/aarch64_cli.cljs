(ns kotoba.compiler.nbb.aarch64-cli
  "AArch64-only nbb native compiler entrypoint."
  (:require [kotoba.compiler.nbb.cli :as native-cli]
            [kotoba.compiler.nbb.cli-support :as support]
            [kotoba.compiler.nbb.compile-cache :as compile-cache]
            [kotoba.kir.target :as target-profile]
            [kotoba.native.aarch64 :as aarch64]))

(defn- run! [args context]
  (native-cli/run! args :aarch64-kotoba-v1 aarch64/emit-program context))

(defn main! [args]
  (if (= "worker" (first args))
    (let [target-name (support/option args "--target")
        target (get native-cli/targets target-name)
        _ (when-not (= :aarch64-kotoba-v1 (some-> target target-profile/backend))
            (support/usage-error!
             (str "error: AArch64 worker does not cover target " target-name)))
        context (assoc (compile-cache/create-context) :target target)]
      (support/serve! #(run! % context) target))
    (support/execute! #(run! % nil) args)))

(main! (if (= "1" (aget js/process.env "KOTOBA_BUNDLED_ENTRY"))
         (vec (.slice js/process.argv 2))
         (vec *command-line-args*)))
