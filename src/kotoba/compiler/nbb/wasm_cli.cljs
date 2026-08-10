(ns kotoba.compiler.nbb.wasm-cli
  "Lean nbb entrypoint for `check` and Wasm compilation. Native emitters,
  artifact sealing, provenance, and the native verifier are intentionally not
  in this namespace's dependency closure."
  (:require [kotoba.compiler.nbb.cli-support :as support]
            [kotoba.compiler.nbb.compile-cache :as compile-cache]
            [kotoba.compiler.frontend :as frontend]
            [kotoba.compiler.nbb.io :as io]
            [kotoba.kir :as ir]
            [kotoba.kir.admission :as admission]
            [kotoba.kir.target :as target-profile]
            [kotoba.wasm.core :as wasm]))

(def targets
  {"wasm32" :wasm32-kotoba-v1
   "wasm32-browser" :wasm32-browser-kotoba-v1
   "wasm32-wasi" :wasm32-wasi-kotoba-v1})

(defn- resolve-hir! [source stage-cache]
  (support/timed "frontend"
                 #(compile-cache/resolve-stage!
                   stage-cache :hir source (fn [] (frontend/analyze source)))))

(defn- resolve-kir! [hir stage-cache]
  (support/timed "kir-lower"
                 #(compile-cache/resolve-stage!
                   ;; Source spelling is deliberately excluded: a frontend-
                   ;; equivalent edit still reruns admission, then reuses KIR.
                   stage-cache :kir (pr-str hir) (fn [] (ir/lower hir)))))

(defn- stage-status [hir-result kir-result]
  {:hir (:cache hir-result) :kir (:cache kir-result)})

(defn- check! [args context]
  (let [input (support/timed "source-admit" #(support/source! (second args)))
        source (support/timed "source-read" #(io/read-text-file input))
        hir-result (resolve-hir! source (:stages context))
        hir (:value hir-result)
        policy (support/timed "policy-read" #(support/read-policy args))
        result (support/timed "admission" #(admission/check hir policy))]
    (cond-> {:ok true :effects (:effects hir) :admission result}
      context (assoc :stage-cache {:hir (:cache hir-result)}))))

(defn- compile-uncached! [args target output source]
  (let [hir (support/timed "frontend" #(frontend/analyze source))
        policy (support/timed "policy-read" #(support/read-policy args))
        _ (support/timed "admission" #(admission/check hir policy))
        kir (support/timed "kir-lower" #(ir/lower hir))
        bytes (support/timed "wasm-emit" #(wasm/emit kir target))]
    (support/timed "artifact-write" #(io/write-bytes! output bytes))
    {:ok true :target target :output output}))

(defn- compile-cached! [args target output source context]
  ;; Read policy bytes early only to form a cache key. If that read fails, defer
  ;; the exception until after frontend analysis so cache misses preserve the
  ;; ordinary CLI's source-before-policy error precedence.
  (let [policy-attempt (support/timed
                        "policy-read"
                        #(try {:material (support/read-policy-material args)}
                              (catch :default error {:error error})))
        material (:material policy-attempt)
        key (when material
              (support/timed "cache-key"
                             #(compile-cache/key-for target source material)))
        artifact-cache (:artifacts context)
        stage-cache (:stages context)
        cached (when key (support/timed "cache-lookup"
                                        #(compile-cache/lookup! artifact-cache key)))]
    (if cached
      (let [bytes (:bytes cached)
            valid? (support/timed "cache-integrity"
                                  #(= (:sha256 cached) (compile-cache/sha256 bytes)))]
        (when-not valid?
          (compile-cache/remove! artifact-cache key)
          (throw (ex-info "compiler cache integrity mismatch" {:cache-key key})))
        (support/timed "artifact-write" #(io/write-bytes! output bytes))
        {:ok true :target target :output output :cache :hit :cache-key key})
      (let [hir-result (resolve-hir! source stage-cache)
            hir (:value hir-result)
            _ (when-let [error (:error policy-attempt)] (throw error))
            policy (support/timed "policy-decode"
                                  #(support/parse-policy-material material))
            _ (support/timed "admission" #(admission/check hir policy))
            kir-result (resolve-kir! hir stage-cache)
            kir (:value kir-result)
            emitted (support/timed "wasm-emit" #(wasm/emit kir target))
            bytes (.from js/Buffer emitted)
            sealed {:bytes bytes :sha256 (compile-cache/sha256 bytes)}]
        (support/timed "artifact-write" #(io/write-bytes! output bytes))
        (support/timed "cache-store"
                       #(compile-cache/put! artifact-cache key sealed (.-length bytes)))
        {:ok true :target target :output output :cache :miss :cache-key key
         :stage-cache (stage-status hir-result kir-result)}))))

(defn- compile! [args context]
  (let [input (support/timed "source-admit" #(support/source! (second args)))
        target-name (or (support/option args "--target") "wasm32")
        target (get targets target-name)
        _ (when-not target
            (support/usage-error!
             (str "error: nbb Wasm path does not cover target " target-name)))
        _ (when (and context (not= target (:target context)))
            (support/usage-error!
             (str "error: worker is locked to target " (name (:target context)))))
        backend (target-profile/backend target)
        _ (when-not (= :wasm32-kotoba-v1 backend)
            (support/usage-error! (str "error: target is not Wasm: " target-name)))
        output (or (support/option args "--output") (str input ".wasm"))
        source (support/timed "source-read" #(io/read-text-file input))]
    (if context
      (compile-cached! args target output source context)
      (compile-uncached! args target output source))))

(defn- run! [args context]
  (case (first args)
    "check" (check! args context)
    "compile" (compile! args context)
    (support/usage-error!
     (str "error: nbb Wasm path does not cover command " (first args)))))

(if (= "worker" (first *command-line-args*))
  (let [target-name (or (support/option *command-line-args* "--target") "wasm32")
        target (get targets target-name)
        _ (when-not target
            (support/usage-error!
             (str "error: nbb Wasm worker does not cover target " target-name)))
        context (assoc (compile-cache/create-context) :target target)]
    (support/serve! #(run! % context) target))
  (support/execute! #(run! % nil)))
