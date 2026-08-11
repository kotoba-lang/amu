(ns kotoba.compiler.nbb.cli
  "Shared ordinary-native CLI implementation. ISA-specific executable
  entrypoints inject exactly one emitter, so compiling AArch64 never loads
  x86-64 code and vice versa."
  (:require [kotoba.compiler.nbb.cli-support :as support]
            [kotoba.compiler.nbb.compile-cache :as compile-cache]
            [kotoba.sema :as sema]
            [kotoba.compiler.nbb.io :as io]
            [kotoba.kir.admission :as admission]
            [kotoba.artifact.core :as artifact]
            [kotoba.kir.compatibility :as compatibility]
            [kotoba.kir :as ir]
            [kotoba.compiler.provenance :as provenance]
            [kotoba.kir.target :as target-profile]
            [kotoba.verifier :as verifier]))

;; Mirrors `kotoba.compiler.cli`'s `parse-target`, restricted to ORDINARY
;; (non-aiueos) native target names -- everything this fast
;; path claims. The `x86_64-aiueos-*`/`aarch64-aiueos-*` firmware/kernel
;; sub-targets (ELF64/PE32+ packaging via `kotoba.compiler.packaging.*`,
;; only reachable through `clojure -M:run compile` directly, not this
;; usage-documented list) stay JVM-only -- out of scope here, same
;; boundary `kotoba.compiler.core/compile-source*`'s own `cond->` draws
;; between the sealed `:kexe/v1` artifact (every ordinary native target)
;; and the extra `:binary`/`:object` packaging (aiueos targets only).
;; Every other name in the JVM `parse-target` table falls through to the
;; JVM path in `bin/kotoba` before this script is ever spawned.
(def targets
  {"x86_64" :x86_64-kotoba-v1
   "x86_64-linux" :x86_64-linux-kotoba-v1
   "x86_64-macos" :x86_64-macos-kotoba-v1
   "x86_64-windows" :x86_64-windows-kotoba-v1
   "aarch64" :aarch64-kotoba-v1
   "aarch64-linux" :aarch64-linux-kotoba-v1
   "aarch64-macos" :aarch64-macos-kotoba-v1
   "aarch64-windows" :aarch64-windows-kotoba-v1
   "aarch64-android" :aarch64-android-kotoba-v1
   "aarch64-ios" :aarch64-ios-kotoba-v1})

;; Mirrors `kotoba.compiler.core/compile-source*`'s `:else` (native) branch
;; byte-for-byte -- same sealed `:kotoba.kexe/v1` shape, same
;; `fuel-abi`/`context-abi`/`limits` constants, same pre-checks -- so a
;; `.kexe` produced here and one produced by `clojure -M:run compile` for
;; the identical source/target/policy verify identically against either
;; artifact's own `:sha256` seal and against `verifier/verify-artifact!`.
;; Deliberately does NOT replicate the `x86_64-aiueos-*`/`aarch64-aiueos-*`
;; `:binary`/`:object` packaging step (see `targets`' own comment above for
;; why that stays out of scope).
(defn- resolve-hir! [source stage-cache]
  (support/timed "frontend"
                 #(compile-cache/resolve-stage!
                   stage-cache :hir source (fn [] (sema/analyze source)))))

(defn- resolve-kir! [hir stage-cache]
  (support/timed "kir-lower"
                 #(compile-cache/resolve-stage!
                   ;; Native oracle evaluation is reusable only when the
                   ;; admitted HIR is byte-for-byte semantically identical.
                   stage-cache :kir (pr-str hir) (fn [] (ir/lower hir)))))

(defn- compile-native! [hir target backend policy emit-program stage-cache]
  (when (and (= :kotoba.hir/v3 (:format hir))
             (not (and (contains? #{:x86_64-kotoba-v1 :aarch64-kotoba-v1} backend)
                       (ir/only-native-word-typed-features? hir))))
    (throw (ex-info "typed values currently require the kotoba-script web target, typed Wasm target, or qualified native string/scalar-record/option-i64/result-i64 features"
                    {:phase :target :target target :backend backend
                     :value-profile :kotoba.value/typed-v1})))
  ;; Keep the self-hosted driver aligned with the JVM compiler: ordinary
  ;; native artifacts are exportable libraries when their target profile does
  ;; not require an entry symbol. Aiueos firmware/kernel/process profiles still
  ;; fail closed because their declared entry must exist in the image.
  (when (and (nil? (:entry hir))
             (not (and (contains? #{:x86_64-kotoba-v1 :aarch64-kotoba-v1} backend)
                       (nil? (:entry (target-profile/profile target))))))
    (throw (ex-info "entryless libraries currently require the kotoba-script web target, the Wasm target, or an entryless native target"
                    {:phase :target :target target :backend backend})))
  (let [admission (support/timed "admission" #(admission/check hir policy))
        kir-result (resolve-kir! hir stage-cache)
        kir (:value kir-result)
        value (:oracle-value kir)
        profile (target-profile/profile target)
        typed-values? (= :kotoba.kir/v4 (:format kir))
        value-abi (if typed-values? :kotoba.typed/externref-v1 :kotoba.i64/direct-v1)
        compat (compatibility/descriptor
                {:hir-format (:format hir) :kir-format (:format kir)
                 :target target :target-profile profile :value-abi value-abi})
        program (select-keys kir [:format :entry :exports :signature :effects :functions])
        ;; Verification re-emits from this closed program. Do not let
        ;; compiler-private KIR metadata influence the bytes being sealed.
        emitted (support/timed "native-emit" #(emit-program program))
        code (:code emitted)
        artifact-map
        (support/timed
         "artifact-seal"
         (fn []
           (artifact/seal
            {:format :kotoba.kexe/v1 :target target :target-profile profile :value value
             :kir-sha256 (artifact/sha256 program)
             :lowering (case backend
                         :x86_64-kotoba-v1 :runtime-sysv-v1
                         :aarch64-kotoba-v1 :runtime-aapcs64-v1)
             :fuel-abi (case backend
                         :x86_64-kotoba-v1 {:mode :hidden-context-r9 :initial 512}
                         :aarch64-kotoba-v1 {:mode :hidden-context-x7 :initial 512})
             :context-abi {:version 3 :fuel-offset 8 :allow-bitmap-offset 16
                           :allow-bitmap-bytes 32 :cap-call-offset 48
                           :pair-new-offset 56 :pair-first-offset 64
                           :pair-second-offset 72 :pair-capacity 4096
                           :kgraph-assert-offset 80 :kgraph-get-offset 88
                           :kgraph-count-offset 96 :kgraph-entity-at-offset 104
                           :kgraph-capacity 4096
                           :string-equal-offset 112 :string-concat-offset 120
                           :typed-cap-call-offset 128
                           :string-substring-offset 136
                           :string-code-point-at-offset 144
                           :string-pool-capacity 65536
                           :vector-new-empty-offset 152
                           :vector-conj-offset 160
                           :vector-count-offset 168
                           :vector-at-offset 176
                           :vector-assoc-offset 184
                           :vector-drop-offset 192
                           :vector-capacity 4096
                           :vector-item-capacity 65536}
             :effects (:effects hir)
             :compatibility compat
             :limits {:memory-bytes 65536 :fuel 512 :stack-bytes 4096}
             :code (mapv #(bit-and (int %) 0xff) code)
             :program program :exports (:exports emitted)})))]
    (support/timed "native-verify" #(verifier/verify-artifact! artifact-map))
    {:format :kexe/v1 :target target :hir hir :kir kir
     :admission admission :artifact artifact-map :compatibility compat
     :stage-cache {:kir (:cache kir-result)}}))

(defn- serialized-native [source policy result]
  (let [provenance-result (support/timed "provenance"
                                         #(provenance/attach source policy {} result))]
    {:artifact-text (support/timed
                     "artifact-serialize"
                     #(pr-str (artifact/edn-safe (:artifact provenance-result))))
     :provenance-text (support/timed
                       "provenance-serialize"
                       #(pr-str (artifact/edn-safe (:provenance provenance-result))))}))

(defn- write-native! [output {:keys [artifact-text provenance-text]}]
  (let [provenance-output (str output ".provenance.edn")]
    (support/timed "artifact-write" #(io/write-text! output artifact-text))
    (support/timed "provenance-write" #(io/write-text! provenance-output provenance-text))
    provenance-output))

(defn- compile-uncached! [args source target backend output emit-program]
  (let [hir (:value (resolve-hir! source nil))
        policy (support/timed "policy-read" #(support/read-policy args))
        result (compile-native! hir target backend policy emit-program nil)
        serialized (serialized-native source policy result)
        provenance-output (write-native! output serialized)]
    {:ok true :target target :output output :provenance-output provenance-output}))

(defn- compile-cached! [args source target backend output emit-program context]
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
      (let [artifact-valid? (support/timed
                             "cache-artifact-integrity"
                             #(= (:artifact-sha256 cached)
                                 (compile-cache/sha256 (:artifact-text cached))))
            provenance-valid? (support/timed
                               "cache-provenance-integrity"
                               #(= (:provenance-sha256 cached)
                                   (compile-cache/sha256 (:provenance-text cached))))]
        (when-not (and artifact-valid? provenance-valid?)
          (compile-cache/remove! artifact-cache key)
          (throw (ex-info "compiler cache integrity mismatch" {:cache-key key})))
        (let [provenance-output (write-native! output cached)]
          {:ok true :target target :output output :provenance-output provenance-output
           :cache :hit :cache-key key}))
      (let [hir-result (resolve-hir! source stage-cache)
            hir (:value hir-result)
            _ (when-let [error (:error policy-attempt)] (throw error))
            policy (support/timed "policy-decode"
                                  #(support/parse-policy-material material))
            result (compile-native! hir target backend policy emit-program stage-cache)
            serialized (serialized-native source policy result)
            provenance-output (write-native! output serialized)
            sealed (assoc serialized
                          :artifact-sha256 (compile-cache/sha256 (:artifact-text serialized))
                          :provenance-sha256 (compile-cache/sha256 (:provenance-text serialized)))
            size (+ (.byteLength js/Buffer (:artifact-text serialized) "utf8")
                    (.byteLength js/Buffer (:provenance-text serialized) "utf8"))]
        (support/timed "cache-store" #(compile-cache/put! artifact-cache key sealed size))
        {:ok true :target target :output output :provenance-output provenance-output
         :cache :miss :cache-key key
         :stage-cache {:hir (:cache hir-result)
                       :kir (get-in result [:stage-cache :kir])}}))))

(defn run! [args expected-backend emit-program context]
  (case (first args)
    "compile"
    (let [input (support/timed "source-admit" #(support/source! (second args)))
            target-name (support/option args "--target")
            target (get targets target-name)
            _ (when-not target
                (support/usage-error!
                 (str "error: nbb native path does not cover target " target-name)))
            _ (when (and context (not= target (:target context)))
                (support/usage-error!
                 (str "error: worker is locked to target " (name (:target context)))))
            backend (target-profile/backend target)
            _ (when-not (= expected-backend backend)
                (support/usage-error!
                 (str "error: target " target-name " does not match loaded native ISA")))
            output (or (support/option args "--output") (str input ".kexe"))
            source (support/timed "source-read" #(io/read-text-file input))]
        (if context
          (compile-cached! args source target backend output emit-program context)
          (compile-uncached! args source target backend output emit-program)))

    (support/usage-error!
     (str "error: nbb native path does not cover command " (first args)))))
