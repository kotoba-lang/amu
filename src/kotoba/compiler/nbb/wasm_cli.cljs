(ns kotoba.compiler.nbb.wasm-cli
  "Primary JDK-free entrypoint for `check` and Wasm compilation. Native
  emitters and the native verifier stay outside this namespace's dependency
  closure, while Wasm provenance is emitted from the same checked HIR/KIR,
  policy, target profile, compatibility descriptor, and bytes as the JVM
  compiler."
  (:require [kotoba.compiler.nbb.cli-support :as support]
            [kotoba.compiler.nbb.compile-cache :as compile-cache]
            [kotoba.sema :as sema]
            [kotoba.compiler.nbb.io :as io]
            [kotoba.artifact.core :as artifact]
            [kotoba.compiler.provenance :as provenance]
            [kotoba.kir :as ir]
            [kotoba.kir.admission :as admission]
            [kotoba.kir.compatibility :as compatibility]
            [kotoba.kir.target :as target-profile]
            [kotoba.wasm.core :as wasm]
            [kotoba.wasm.typed :as typed]))

(def targets
  {"wasm32" :wasm32-kotoba-v1
   "wasm32-browser" :wasm32-browser-kotoba-v1
   "wasm32-wasi" :wasm32-wasi-kotoba-v1})

(defn- resolve-hir! [source policy stage-cache]
  (support/timed "frontend"
                 #(compile-cache/resolve-stage!
                   stage-cache :hir
                   (pr-str [:kotoba.hir-cache/v2 source
                            (:language-profile policy)])
                   (fn [] (sema/analyze source (support/analyze-options policy))))))

(defn- resolve-kir! [hir stage-cache]
  (support/timed "kir-lower"
                 #(compile-cache/resolve-stage!
                   ;; Source spelling is deliberately excluded: a frontend-
                   ;; equivalent edit still reruns admission, then reuses KIR.
                   stage-cache :kir (pr-str hir) (fn [] (ir/lower hir)))))

(defn- stage-status [hir-result kir-result]
  {:hir (:cache hir-result) :kir (:cache kir-result)})

(def ^:private floating-point-policy
  :kotoba.floating-point/ieee-754-f32-f64-v7)

(defn- compile-wasm!
  "Keep the primary Node result and provenance identity aligned with
  `kotoba.compiler.core/compile-source*`'s Wasm branch. In particular, the
  policy fuel budget is an emitter input, not admission-only metadata."
  [source target policy hir admission-result kir]
  (let [profile (target-profile/profile target)
        typed-values? (= :kotoba.kir/v4 (:format kir))
        value-abi (cond (ir/uses-f32? hir) :kotoba.typed/mixed-f32-f64-v3
                        (ir/uses-f64? hir) :kotoba.typed/mixed-f64-v2
                        typed-values? :kotoba.typed/externref-v1
                        :else :kotoba.i64/direct-v1)
        fuel (or (get-in policy [:budgets :fuel]) 512)
        compat (compatibility/descriptor
                {:hir-format (:format hir) :kir-format (:format kir)
                 :target target :target-profile profile :value-abi value-abi})
        result {:format :wasm/v1 :target target :target-profile profile
                :hir hir :kir kir :admission admission-result
                :compatibility compat
                :floating-point-policy floating-point-policy
                :value-profile (if typed-values?
                                 :kotoba.value/typed-v1 :kotoba.value/i64-v1)
                :value-abi value-abi
                :wasm-features (cond-> #{}
                                 (typed/requires-host-runtime? kir)
                                 (conj :reference-types)
                                 (ir/uses-f32? kir) (conj :ieee-754-f32)
                                 (ir/uses-f64? kir) (conj :ieee-754-f64))
                :limits (cond-> {:fuel fuel :replenishable? false}
                          typed-values?
                          (assoc :parametric-adt-depth 12
                                 :parametric-adt-nodes 64
                                 :variant-cases 32
                                 :heterogeneous-vector-items 32
                                 :typed-set-items 32
                                 :typed-map-entries 31
                                 :record-fields 32
                                 :vector-i64-items 16384
                                 :vector-f64-items 16384
                                 :compact-graph-items 128
                                 :string-index-key-bytes 65536))
                :bytes (support/timed "wasm-emit"
                                      #(wasm/emit kir target {:fuel fuel}))}]
    (support/timed "provenance"
                   #(provenance/attach source policy {} result))))

(defn- serialized-wasm [result]
  {:bytes (.from js/Buffer (:bytes result))
   :provenance-text (support/timed
                     "provenance-serialize"
                     #(pr-str (artifact/edn-safe (:provenance result))))})

(defn- write-wasm! [output {:keys [bytes provenance-text]}]
  (let [provenance-output (str output ".provenance.edn")]
    (support/timed "artifact-write" #(io/write-bytes! output bytes))
    (support/timed "provenance-write"
                   #(io/write-text! provenance-output provenance-text))
    provenance-output))

(defn- check! [args context]
  (let [input (support/timed "source-admit" #(support/source! (second args)))
        source (support/timed "source-read" #(io/read-text-file input))
        policy (support/timed "policy-read" #(support/read-policy args))
        hir-result (resolve-hir! source policy (:stages context))
        hir (:value hir-result)
        result (support/timed
                "admission"
                #(admission/check hir (support/capability-policy policy)))]
    ;; Same keys as the JVM `check --json` in kotoba.compiler.cli. This path
    ;; used to answer with :ok/:effects/:admission only, so a consumer keying
    ;; on :format -- the versioned output contract -- saw nothing to key on,
    ;; and :exports was simply absent. Same command, same file, two shapes.
    (cond-> {:ok true
             :format :kotoba.check/v1
             :language-profile (:language-profile hir)
             :effects (:effects hir)
             :exports (:exports hir)
             :admission result}
      context (assoc :stage-cache {:hir (:cache hir-result)}))))

(defn- compile-uncached! [args target output source]
  (let [policy (support/timed "policy-read" #(support/read-policy args))
        hir (:value (resolve-hir! source policy nil))
        admission-result (support/timed
                          "admission"
                          #(admission/check hir (support/capability-policy policy)))
        kir (support/timed "kir-lower" #(ir/lower hir))
        serialized (serialized-wasm
                    (compile-wasm! source target policy hir admission-result kir))
        provenance-output (write-wasm! output serialized)]
    {:ok true :target target :output output
     :provenance-output provenance-output}))

(defn- compile-cached! [args target output source context]
  ;; Policy material is part of artifact identity. Declarative policy controls
  ;; also affect HIR and emission, so decode them before consulting either
  ;; stage cache; otherwise a language-profile change could reuse the wrong HIR.
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
            artifact-valid? (support/timed
                             "cache-artifact-integrity"
                             #(= (:sha256 cached) (compile-cache/sha256 bytes)))
            provenance-valid? (support/timed
                               "cache-provenance-integrity"
                               #(= (:provenance-sha256 cached)
                                   (compile-cache/sha256
                                    (:provenance-text cached))))]
        (when-not (and artifact-valid? provenance-valid?)
          (compile-cache/remove! artifact-cache key)
          (throw (ex-info "compiler cache integrity mismatch" {:cache-key key})))
        (let [provenance-output (write-wasm! output cached)]
          {:ok true :target target :output output
           :provenance-output provenance-output :cache :hit :cache-key key}))
      (let [_ (when-let [error (:error policy-attempt)] (throw error))
            policy (support/timed "policy-decode"
                                  #(support/parse-policy-material material))
            hir-result (resolve-hir! source policy stage-cache)
            hir (:value hir-result)
            admission-result (support/timed
                              "admission"
                              #(admission/check hir
                                                (support/capability-policy policy)))
            kir-result (resolve-kir! hir stage-cache)
            kir (:value kir-result)
            serialized (serialized-wasm
                        (compile-wasm! source target policy hir admission-result kir))
            bytes (:bytes serialized)
            provenance-output (write-wasm! output serialized)
            sealed (assoc serialized
                          :sha256 (compile-cache/sha256 bytes)
                          :provenance-sha256
                          (compile-cache/sha256 (:provenance-text serialized)))
            size (+ (.-length bytes)
                    (.byteLength js/Buffer (:provenance-text serialized) "utf8"))]
        (support/timed "cache-store"
                       #(compile-cache/put! artifact-cache key sealed size))
        {:ok true :target target :output output
         :provenance-output provenance-output :cache :miss :cache-key key
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
