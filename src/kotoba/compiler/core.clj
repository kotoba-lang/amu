(ns kotoba.compiler.core
  (:require [clojure.walk :as walk]
            [kotoba.compiler.frontend :as frontend]
            [kotoba.kir.compatibility :as compatibility]
            [kotoba.compiler.provenance :as provenance]
            [kotoba.compiler.cache :as cache]
            [kotoba.compiler.project :as project]
            [kotoba.kir :as ir]
            [kotoba.kir.admission :as admission]
            [kotoba.wasm.core :as wasm]
            [kotoba.wasm.typed :as typed]
            [kotoba.component.wit :as component-wit]
            [kotoba.component.artifact :as component-artifact]
            [kotoba.component.core :as component-core]
            [kotoba.component.admission :as component-admission]
            [kotoba.abi.contract :as abi]
            [kotoba.compiler.backend.cljs :as cljs]
            [kotoba.script :as script]
            [kotoba.native.x86-64 :as x86-64]
            [kotoba.native.aarch64 :as aarch64]
            [kotoba.native.elf64 :as elf64]
            [kotoba.compiler.packaging.pe32plus :as pe32plus]
            [kotoba.artifact.core :as artifact]
            [kotoba.kir.target :as target-profile]
            [kotoba.verifier :as verifier])
  (:import [java.nio.charset StandardCharsets]
           [java.security MessageDigest]))

(def compiler-version compatibility/compiler-version)
(def floating-point-policy :kotoba.floating-point/ieee-754-f32-f64-v7)

(defn- text-sha256 [text]
  (let [digest (.digest (MessageDigest/getInstance "SHA-256")
                        (.getBytes ^String text StandardCharsets/UTF_8))]
    (apply str (map #(format "%02x" (bit-and (int %) 0xff)) digest))))

(def targets target-profile/compatibility-targets)
(def supported-targets (set (keys target-profile/profiles)))

(def source-compilable-targets
  "Targets `compile-source` emits directly.

  A component target is deliberately excluded: a component is a core module
  lifted through the Canonical ABI by `compile-component`, not a backend
  output. Callers that fan out over every target (conformance sweeps, policy
  seal checks) want this set; `supported-targets` remains every declared
  target, so `--target component` still validates as a real target name."
  (into #{} (remove #(= :component (:execution (target-profile/profile %))))
        supported-targets))

;; Native (x86_64/aarch64) targets admit the string slice of "typed values"
;; (string literals + string-byte-length/string=?/string-concat,
;; ADR-2607198300 follow-up) PLUS -- as of the first native record increment
;; (ADR 0062) -- a sealed, all-scalar (`:i64`/`:bool` fields only)
;; `record-new`/`record-get` pair, used only in the one exact nested
;; construction+projection shape `backend/x86-64.cljc`/`backend/aarch64.cljc`
;; implement, PLUS -- as of the second native increment (ADR 0063) -- a
;; sealed, all-scalar-cased `variant-new`/`variant-match` pair, used only in
;; the analogous one exact nested construction+dispatch shape those same two
;; files implement, PLUS sealed typed capability boundaries for i64, bounded
;; UTF-8 strings, `:option-i64`, and `:result-i64`. The structured callback
;; validates pair-backed string pointer/length handles or canonical tagged
;; `(tag,payload)` handles on both sides. Every other typed feature
;; (generic options/results, general/nested/escaping records or variants,
;; typed maps/vectors/sets) has zero native backend codegen and
;; must keep producing the same "requires kotoba-script web target"
;; rejection it always has. This is a content check, not a blanket
;; per-backend allowance:
;; :kotoba.hir/v3 covers ALL typed features uniformly, so admitting the
;; format for native without inspecting which features are actually used
;; would silently let unsupported ops reach the backend and crash confusingly
;; instead of rejecting cleanly. Shared with `kotoba.compiler.nbb.cli` (the
;; nbb-native fast path) via
;; `kotoba.kir/only-native-word-typed-features?` so both
;; compile paths admit the exact same native-typed-feature subset.

(defn check-source
  ([source] (check-source source {}))
  ([source policy]
   (let [hir (frontend/analyze source)]
     {:hir hir :admission (admission/check hir policy)})))

(defn- component-kir
  "Make the source language's legacy scalar `cap-call` explicit at the
  Component boundary. In KIR, untyped cap-call has always been an i64 -> i64
  operation; Component WIT/core lowering intentionally accepts only
  `typed-cap-call`. Keeping this normalization here preserves all ordinary
  backend KIR identities while preventing an effectful Component from falling
  through to the unbindable generic `kotoba:cap::call` core import."
  [kir]
  (-> kir
      (update :functions
              (fn [functions]
                (mapv (fn [function]
                        (-> function
                            (update :param-types
                                    #(or % (vec (repeat (count (:params function)) :i64))))
                            (update :result #(or % :i64))
                            (update :body
                                    #(walk/postwalk
                                      (fn [form]
                                        (if (and (seq? form)
                                                 (= 'cap-call (first form))
                                                 (= 3 (count form)))
                                          (let [[_ id request] form]
                                            (list 'typed-cap-call id :i64 :i64 request))
                                          form))
                                      %))))
                      functions)))))

(defn compile-component-wit
  "Compile source through checked HIR/KIR and emit its deterministic closed WIT
  package. This does not claim to emit a Component binary."
  ([source] (compile-component-wit source {}))
  ([source policy]
   (let [hir (frontend/analyze source)
         checked (admission/check hir policy)
         kir (component-kir (ir/lower hir))]
     (assoc (component-wit/emit kir) :admission checked))))

(declare compile-source)

(def default-component-budgets
  "Declared resource bounds used when a caller supplies none.

  `:fuel` keeps the historical 512-call budget so an unparameterized component
  behaves exactly like every core-wasm module. `:memory-pages` is a DECLARED
  host bound, not a property read back out of the module -- kototama's
  `component-platform.edn` requires the key to be a positive integer for the
  `:sync` profile, and 16 pages (1 MiB) is a default, not a measurement."
  {:fuel wasm/default-fuel :memory-pages 16})

(defn- component-capability-ids [kir]
  (->> (:functions kir)
       (mapcat #(tree-seq coll? seq (:body %)))
       (keep (fn [form]
               (when (and (seq? form) (= 'typed-cap-call (first form)))
                 (second form))))
       set))

(defn compile-component
  "Compile the currently qualified slice to a validated Component Model binary
  plus its admission request. Structured/provider Canonical ABI lowering
  remains fail-closed.

  `opts` takes `:profile` (`:sync`/`:async`), `:budgets`, `:package-lock-cid`.
  The declared `:fuel` budget is compiled into the core module's fuel global
  where the shape allows it; `:fuel-enforcement` in the result reports whether
  that happened or the budget is host-enforced only."
  ([source] (compile-component source {} {}))
  ([source policy] (compile-component source policy {}))
  ([source policy {:keys [profile budgets component-abilities capability-mode target]
                   :or {profile :sync target :wasm-component-kotoba-v1} :as opts}]
   (let [budgets (merge default-component-budgets budgets)
         typed-v3? (= target abi/component-target-v2)
         _ (when-not (contains? #{nil :function :linear-resource} capability-mode)
             (throw (ex-info "Component capability mode is unsupported"
                             {:phase :component-capability-mode
                              :capability-mode capability-mode})))
         hir (frontend/analyze source)
         checked-admission (admission/check hir policy)
         kir (component-kir (ir/lower hir))
         target-profile (target-profile/profile target)
         typed-values? (= :kotoba.kir/v4 (:format kir))
         value-abi (cond (ir/uses-f32? hir) :kotoba.typed/mixed-f32-f64-v3
                         (ir/uses-f64? hir) :kotoba.typed/mixed-f64-v2
                         typed-values? :kotoba.typed/externref-v1
                         :else :kotoba.i64/direct-v1)
         compatibility (compatibility/descriptor
                        {:hir-format (:format hir) :kir-format (:format kir)
                         :target target :target-profile target-profile
                         :value-abi value-abi})
         capability-ids (component-capability-ids kir)
         _ (when (and typed-v3?
                      (not (contains? #{#{6} #{7} #{13}} capability-ids)))
             (throw (ex-info
                     "typed v0.3 lowering currently requires one implemented vertical slice"
                     {:phase :component-abi-v3
                      :target target
                      :implemented [#{6} #{7} #{13}]
                      :supplied capability-ids})))
         _ (when (and component-abilities
                      (not= capability-ids (set (keys component-abilities))))
             (throw (ex-info "Component abilities must exactly match capability calls"
                             {:phase :component-abilities
                              :required capability-ids
                              :supplied (set (keys component-abilities))})))
         _ (when (and component-abilities
                      (not-every? abi/valid-ability? (vals component-abilities)))
             (throw (ex-info "Component ability descriptor is invalid"
                             {:phase :component-abilities})))
         _ (when (and (= capability-mode :linear-resource)
                      (not (contains? #{:scalar-capability-call
                                       :scalar-literal-capability-call}
                                     (component-core/assert-supported! kir))))
             (throw (ex-info "Linear resource mode requires one direct scalar capability call"
                             {:phase :component-capability-mode
                              :capability-mode capability-mode})))
         component-opts {:capability-mode (or capability-mode :function)
                         :typed-capability-v3? typed-v3?}
         wit (component-wit/emit kir component-opts)
         enforcement (component-core/fuel-enforcement kir)
         component-bytes (component-core/emit kir :wasm32-wasi-kotoba-v1
                                              {:fuel (:fuel budgets)
                                               :memory-pages (:memory-pages budgets)
                                               :capability-mode capability-mode
                                               :typed-capability-v3? typed-v3?})
         packaged (component-artifact/package component-bytes kir wit)
         result
         (assoc packaged
            :hir hir
            :kir kir
            :target-profile target-profile
            :capabilities (into #{} (map abi/component-import-key) capability-ids)
            :component-imports
            (into (sorted-map)
                  (map (fn [id]
                         [(abi/component-import-key id)
                          (get component-abilities id)]))
                  capability-ids)
            :wit wit
            :admission checked-admission
            :floating-point-policy floating-point-policy
            :compatibility compatibility
            :budgets budgets
            :capability-mode (or capability-mode :function)
            :fuel-enforcement enforcement
            :admission-request (component-admission/request
                                packaged wit
                                (assoc opts :profile profile :budgets budgets)))]
     (provenance/attach source policy opts result))))

(defn- compile-source*
  ([source target] (compile-source* source target {}))
  ([source target policy] (compile-source* source target policy {}))
  ([source target policy emit-metadata]
   (when-not (contains? supported-targets target)
     (throw (ex-info "unsupported target" {:target target :supported supported-targets})))
   ;; A Component is not a backend output: it is a core module lifted through
   ;; the Canonical ABI and packaged by the pinned wasm-tools toolchain. Route
   ;; it explicitly rather than letting it fall through to the wasm32 backend,
   ;; which would silently emit a bare core module under a component target
   ;; name.
   (when (= :component (:execution (target-profile/profile target)))
     (throw (ex-info "component targets compile through compile-component"
                     {:phase :target-routing :target target
                      :entry-point 'kotoba.compiler.core/compile-component})))
   (let [profile (target-profile/profile target)
        backend (target-profile/backend target)
        hir (frontend/analyze source)
        _ (when (and (or (ir/uses-f32? hir) (ir/uses-f64? hir))
                     (not (contains? #{:js-kotoba-v1 :wasm32-kotoba-v1} backend)))
            (throw (ex-info "floating-point values require the kotoba-script or Wasm target"
                            {:phase :target :target target :backend backend
                             :floating-point-policy floating-point-policy})))
        _ (when (and (= :kotoba.hir/v3 (:format hir))
                     (not (contains? #{:js-kotoba-v1 :wasm32-kotoba-v1} backend))
                     (not (and (= :cljs-kotoba-v1 backend)
                               (ir/only-cljs-provider-typed-features? hir)))
                     (not (and (contains? #{:x86_64-kotoba-v1 :aarch64-kotoba-v1} backend)
                               (ir/only-native-word-typed-features? hir))))
            (throw (ex-info "typed values currently require the kotoba-script web target, typed Wasm/CLJS target, or the qualified native one-word string/record/variant/option/result slice"
                            {:phase :target :target target :backend backend
                             :value-profile :kotoba.value/typed-v1})))
        _ (when (and (nil? (:entry hir))
                     (not (contains? #{:js-kotoba-v1 :wasm32-kotoba-v1
                                      :cljs-kotoba-v1} backend)))
            (throw (ex-info "entryless libraries currently require the kotoba-script web target or Wasm target"
                            {:phase :target :target target :backend backend})))
        admission (admission/check hir policy)
        kir (ir/lower hir)
        value (:oracle-value kir)
        typed-values? (= :kotoba.kir/v4 (:format kir))
        value-abi (cond (ir/uses-f32? hir) :kotoba.typed/mixed-f32-f64-v3
                        (ir/uses-f64? hir) :kotoba.typed/mixed-f64-v2
                        typed-values? :kotoba.typed/externref-v1
                        :else :kotoba.i64/direct-v1)
        compatibility (compatibility/descriptor
                       {:hir-format (:format hir) :kir-format (:format kir)
                        :target target :target-profile profile :value-abi value-abi})]
    (cond
      (= backend :wasm32-kotoba-v1)
      (let [typed-values? (= :kotoba.kir/v4 (:format kir))]
        {:format :wasm/v1 :target target :target-profile profile
         :hir hir :kir kir :admission admission
         :compatibility compatibility
         :floating-point-policy floating-point-policy
         :value-profile (if typed-values? :kotoba.value/typed-v1 :kotoba.value/i64-v1)
         :value-abi value-abi
         :wasm-features (cond-> #{}
                          (typed/requires-host-runtime? kir) (conj :reference-types)
                          (ir/uses-f32? kir) (conj :ieee-754-f32)
                          (ir/uses-f64? kir) (conj :ieee-754-f64))
         :limits (cond-> {:fuel 512 :replenishable? false}
                   typed-values? (assoc :parametric-adt-depth 8
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
         :bytes (wasm/emit kir target)})

      ;; ADR-2607151500: cljs backend emits SOURCE TEXT, not bytes -- no
      ;; kexe sealing (that artifact shape is native-code-specific: raw
      ;; :code bytes + a fuel/context ABI for a machine-code caller). A
      ;; cljs host just requires the returned source's namespace directly.
      (= backend :cljs-kotoba-v1)
      {:format :cljs/v1 :target target :target-profile profile
       :hir hir :kir kir :admission admission
       :compatibility compatibility
       :floating-point-policy floating-point-policy
       :limits {:fuel 512 :replenishable? false} :source (cljs/emit kir)}

      (= backend :js-kotoba-v1)
      (let [source-digest (text-sha256 source)
            kir-digest (artifact/sha256 kir)
            typed-values? (= :kotoba.kir/v4 (:format kir))
            value-profile (if typed-values? :kotoba.value/typed-v1 :kotoba.value/i64-v1)
            limits (cond-> {:fuel 512 :replenishable? false}
                     typed-values? (assoc :string-literal-bytes 4096
                                          :string-module-literal-bytes 65536
                                          :string-value-bytes 65536
                                          :keyword-value-bytes 512
                                          :map-entries 128
                                          :option-i64-slots 2
                                          :result-i64-slots 2
                                          :parametric-adt-depth 8
                                          :parametric-adt-nodes 64
                                          :variant-cases 32
                                          :generic-option-max-slots 3
                                          :heterogeneous-vector-items 32
                                          :typed-set-items 32
                                          :typed-map-entries 31
                                          :record-fields 32
                                          :vector-i64-items 16384
                                          :vector-f64-items 16384
                                          :compact-graph-items 128
                                          :string-index-key-bytes 65536))
            js-source (script/emit kir (merge {:source-digest source-digest
                                               :kir-digest kir-digest
                                               :compiler-version compiler-version}
                                              emit-metadata))
            output-digest (text-sha256 js-source)]
        {:format :javascript/v1 :target target :target-profile profile
         :hir hir :kir kir :admission admission
         :compatibility compatibility
         :floating-point-policy floating-point-policy
         :value-profile value-profile :limits limits :source js-source
         :manifest {:kotoba.artifact/schema "kotoba-js-artifact/v1"
                    :kotoba.artifact/source-digest source-digest
                    :kotoba.artifact/kir-digest kir-digest
                    :kotoba.artifact/output-digest output-digest
                    :kotoba.artifact/compiler-version compiler-version
                    :kotoba.artifact/compatibility compatibility
                    :kotoba.artifact/floating-point-policy floating-point-policy
                    :kotoba.artifact/value-profile value-profile
                    :kotoba.artifact/limits limits
                    :kotoba.artifact/target target
                    :kotoba.artifact/target-profile profile
                    :kotoba.artifact/effects (:effects kir)}})

      :else
      (let [emitted ((case backend
                       :x86_64-kotoba-v1 x86-64/emit-program
                       :aarch64-kotoba-v1 aarch64/emit-program) kir)
            code (:code emitted)
            program (select-keys kir [:format :entry :exports :signature :effects :functions])
            artifact (artifact/seal
                      {:format :kotoba.kexe/v1 :target target :target-profile profile :value value
                       :kir-sha256 (artifact/sha256 program)
                       :lowering (case backend
                                   :x86_64-kotoba-v1 :runtime-sysv-v1
                                   :aarch64-kotoba-v1 :runtime-aapcs64-v1)
                       :fuel-abi (case backend
                                   :x86_64-kotoba-v1 {:mode :hidden-context-r9 :initial 512}
                                   :aarch64-kotoba-v1 {:mode :hidden-context-x7 :initial 512})
                       :context-abi {:version 2 :fuel-offset 8 :allow-bitmap-offset 16
                                     :allow-bitmap-bytes 32 :cap-call-offset 48
                                     :pair-new-offset 56 :pair-first-offset 64
                                     :pair-second-offset 72 :pair-capacity 4096
                                     :kgraph-assert-offset 80 :kgraph-get-offset 88
                                     :kgraph-count-offset 96 :kgraph-entity-at-offset 104
                                     :kgraph-capacity 4096
                                     :string-equal-offset 112 :string-concat-offset 120
                                     :typed-cap-call-offset 128
                                     :string-pool-capacity 65536}
                      :effects (:effects hir)
                       :compatibility compatibility
                       :limits {:memory-bytes 65536
                                :fuel 512
                                :stack-bytes 4096}
                       :code (mapv #(bit-and (int %) 0xff) code)
                       :program program :exports (:exports emitted)})]
        (verifier/verify-artifact! artifact)
        (cond-> {:format :kexe/v1 :target target :hir hir :kir kir
                 :admission admission :artifact artifact
                 :compatibility compatibility
                 :floating-point-policy floating-point-policy}
          (= target :x86_64-aiueos-uefi-v1)
          (assoc :binary (pe32plus/package-efi artifact))

          (= target :x86_64-aiueos-kernel-v1)
          (assoc :binary (elf64/package-kernel artifact)
                 :object (elf64/package-kernel-object artifact))

          (= target :aarch64-aiueos-kernel-v1)
          (assoc :binary (elf64/package-kernel-aarch64 artifact))

          (= target :x86_64-aiueos-user-v1)
          (assoc :binary (elf64/package-user artifact))))))))

(defn compile-source
  ([source target] (compile-source source target {}))
  ([source target policy] (compile-source source target policy {}))
  ([source target policy emit-metadata]
   (provenance/attach source policy emit-metadata
                      (compile-source* source target policy emit-metadata))))

(defn compile-source-cached
  [source target policy build-metadata cache-entry trust now]
  (if cache-entry
    (cache/admit! source target policy build-metadata cache-entry trust now)
    {:hit? false
     :result (compile-source source target policy build-metadata)}))

(defn compile-project
  "Compile a closed namespace-symbol -> source-text map without ambient lookup."
  ([sources root target] (compile-project sources root target {}))
  ([sources root target policy] (compile-project sources root target policy {}))
  ([sources root target policy supply-chain]
   (let [allowed-keys #{:package-lock-digest :trust-policy-digest
                        :package-receipt-digest}
         values (when (map? supply-chain) (vals supply-chain))
         supplied (count (filter some? values))]
     (when-not (and (map? supply-chain)
                    (every? allowed-keys (keys supply-chain))
                    (or (zero? supplied)
                        (and (= allowed-keys (set (keys supply-chain)))
                             (= 3 supplied)
                             (every? #(and (string? %)
                                           (re-matches #"[0-9a-f]{64}" %))
                                     values))))
       (throw (ex-info "invalid verified supply-chain identity"
                       {:phase :project-link
                        :reason :invalid-supply-chain-identity}))))
   (let [linked (project/link-source sources root)
         module-digests (into (sorted-map)
                              (map (fn [[namespace source]]
                                     [namespace (text-sha256 source)]))
                              (select-keys sources (:module-order linked)))
         graph {:kotoba.module/schema :kotoba.module-graph/v1
                :kotoba.module/root root
                :kotoba.module/order (:module-order linked)
                :kotoba.module/source-digests module-digests}
         graph-digest (artifact/sha256 graph)
         compiled (compile-source (:source linked) target policy
                                  (merge {:module-graph-digest graph-digest
                                          :module-source-digests module-digests}
                                         supply-chain))]
     (cond-> (assoc compiled :project graph :project-digest graph-digest)
       (:manifest compiled)
       (update :manifest merge
               (merge {:kotoba.artifact/module-graph-digest graph-digest
                       :kotoba.artifact/module-source-digests module-digests}
                      (when (seq supply-chain)
                        {:kotoba.artifact/package-lock-digest
                         (:package-lock-digest supply-chain)
                         :kotoba.artifact/trust-policy-digest
                         (:trust-policy-digest supply-chain)
                         :kotoba.artifact/package-receipt-digest
                         (:package-receipt-digest supply-chain)})))))))
