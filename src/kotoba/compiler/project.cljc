(ns kotoba.compiler.project
  (:require [clojure.string :as str]
            [kotoba.compiler.frontend :as frontend]
            [kotoba.kir.value :as value]))

(def max-project-modules 256)
(def max-project-functions 1024)
(def max-project-source-bytes (* 8 1024 1024))
(def max-linked-source-bytes (* 1024 1024))
(def max-project-dependency-edges 256)
(def max-project-depth 64)
(def max-project-exports 1024)
(def max-project-expression-nodes 200000)
(def max-project-literals 65536)
(def max-project-string-literal-bytes (* 1024 1024))

(defn- reject! [message data]
  (throw (ex-info message (assoc data :phase :project-link))))

(defn module-info
  "Return the bounded declared namespace, exports, alias-only requires and
  declared capability set for one project module. This is also the authority
  used by filesystem graph discovery; discovery and linking therefore cannot
  disagree on syntax.

  `:capabilities` is admitted here because `frontend/namespace-parts` has
  always admitted it for a single-module compile -- without this clause a
  project could hold either multiple modules or a capability, never both,
  which put every effectful application outside project mode entirely. The
  set is validated against the SAME bounds the frontend applies
  (`max-namespace-capabilities`, namespaced keywords only) so a module cannot
  smuggle a wider declaration in through the project path than it could
  through the single-module path.

  Still not admitted here: `:schemas`. The frontend takes it, but linking
  several modules' schema tables into one namespace needs a collision rule
  for identically-named schemas across modules, which is a separate decision
  from this one -- a project module that declares `:schemas` is still
  rejected rather than silently having the clause dropped."
  [forms]
  (let [ns-forms (filter #(and (seq? %) (= 'ns (first %))) forms)]
    (when-not (= 1 (count ns-forms))
      (reject! "project module requires exactly one namespace" {:count (count ns-forms)}))
    (let [[_ name & raw-clauses] (first ns-forms)
          [docstring clauses] (if (string? (first raw-clauses))
                                [(first raw-clauses) (next raw-clauses)]
                                [nil raw-clauses])]
      (when-not (and (simple-symbol? name) (not (str/blank? (str name))))
        (reject! "invalid project namespace" {:namespace name}))
      (when (and docstring (> (count docstring) frontend/max-namespace-docstring-chars))
        (reject! "namespace docstring exceeds admission limit" {:namespace name}))
      (loop [remaining clauses exports nil requires [] capabilities nil]
        (if-let [clause (first remaining)]
          (cond
            (and (seq? clause) (= :export (first clause)) (= 2 (count clause))
                 (vector? (second clause)) (nil? exports))
            (recur (next remaining) (vec (second clause)) requires capabilities)

            (and (seq? clause) (= :capabilities (first clause)) (= 2 (count clause))
                 (set? (second clause)) (nil? capabilities))
            (let [declared (second clause)]
              (when (or (> (count declared) frontend/max-namespace-capabilities)
                        (not-every? #(and (keyword? %) (namespace %)) declared))
                (reject! "namespace :capabilities must be a bounded set of namespaced keywords"
                         {:namespace name :capabilities declared}))
              (recur (next remaining) exports requires declared))

            (and (seq? clause) (= :require (first clause)))
            (let [parsed
                  (mapv (fn [spec]
                          (when-not (and (vector? spec) (= 3 (count spec))
                                         (simple-symbol? (first spec))
                                         (= :as (second spec))
                                         (simple-symbol? (nth spec 2)))
                            (reject! "imports require [namespace :as alias]"
                                     {:namespace name :spec spec}))
                          {:namespace (first spec) :alias (nth spec 2)})
                        (rest clause))]
              (recur (next remaining) exports (into requires parsed) capabilities))

            :else
            (reject! "only one :export, one :capabilities and alias-only :require clauses are admitted"
                     {:namespace name :clause clause}))
          (do
            (when-not (some? exports)
              (reject! "project module requires an explicit :export vector" {:namespace name}))
            (when-not (= (count requires) (count (set (map :alias requires))))
              (reject! "duplicate import alias" {:namespace name :requires requires}))
            (when-not (= (count requires) (count (set (map :namespace requires))))
              (reject! "duplicate imported namespace" {:namespace name :requires requires}))
            ;; nil when the clause is absent, mirroring the frontend: nil
            ;; means "no declare-then-check runs here", an explicit empty set
            ;; means "this module must use no capability at all". Collapsing
            ;; the two would silently turn the second into the first.
            {:namespace name :exports exports :requires requires
             :capabilities capabilities}))))))

(defn- without-requires [forms]
  (mapv (fn [form]
          (if (and (seq? form) (= 'ns (first form)))
            (let [[op name & clauses] form]
              (list* op name (remove #(and (seq? %) (= :require (first %))) clauses)))
            form))
        forms))

(defn- interface-of [{:keys [name params param-types result effects]} linked-name]
  {:name name :params params
   :param-types (or param-types (vec (repeat (count params) :i64)))
   :result (or result :i64) :effects effects :linked-name linked-name})

(defn- typed-params [params types]
  (if (every? #{:i64} types) params (vec (mapcat vector params types))))

(defn- stub-value [type]
  (cond
    (= type :i64) 0
    (= type :f64) '(f64-from-bits 0)
    (= type :f32) '(f32-from-bits 0)
    (= type :string) ""
    (= type :keyword) :kotoba.stub/value
    (= type :symbol) '(symbol "kotoba.stub/value")
    (= type :map) {}
    (= type :bool) false
    (= type :option-i64) '(option-none)
    (= type :result-i64) '(result-ok 0)
    (= type :vector-i64) '(vector-i64)
    (= type :vector-f64) '(vector-f64)
    (= type :string-index) '(string-index)
    (= type :disjoint-set-i64) '(disjoint-set-i64)
    (and (vector? type) (= :result (first type)))
    (list 'result-ok-of type (stub-value (second type)))
    (and (vector? type) (= :option (first type)))
    (list 'option-none-of type)
    (and (vector? type) (= :variant (first type)))
    (let [[tag payload-type] (first (nth type 2))]
      (list 'variant-new type tag (stub-value payload-type)))
    (and (vector? type) (= :vector (first type)))
    (list* 'hetero-vector type (map stub-value (second type)))
    (and (vector? type) (= :set (first type)))
    (list 'typed-set type)
    (and (vector? type) (= :map (first type)))
    (list 'typed-map-new type)
    (and (vector? type) (= :record (first type)))
    (list* 'record type (map (comp stub-value second) (nth type 2)))
    :else (reject! "project import result type has no closed stub value"
                   {:type type})))

(defn- stub-form [stub {:keys [params param-types result]}]
  (list 'defn- stub (typed-params params param-types) result (stub-value result)))

(defn- capability-operation?
  "True for a friendly capability operation such as `clock/now`.

  These are namespaced calls that are not module references: the frontend
  elaborates them into typed abilities against the capability catalog. The
  linker used to see only `<ns>/<name>` and conclude that anything qualified
  had to be an imported export, which made a friendly operation impossible to
  write inside a project — the single-file path accepted it and the project
  path rejected it with `qualified call is not an admitted exported import`.

  Module imports are still resolved first, so an explicit `:require` alias
  always wins over a capability of the same name; a project can never have a
  capability silently displace a module it asked for."
  [op]
  (contains? frontend/capability-registry
             (keyword (namespace op) (name op))))

(defn- rewrite-import-calls [form imported]
  (cond
    (seq? form)
    (let [[op & args] form
          op' (if (and (symbol? op) (namespace op))
                (or (get imported op)
                    ;; Left as written: elaboration into a typed ability is the
                    ;; frontend's job, and it runs identically on linked source.
                    (when (capability-operation? op) op)
                    (reject! "qualified call is not an admitted exported import" {:call op}))
                op)]
      (list* op' (map #(rewrite-import-calls % imported) args)))
    (vector? form) (mapv #(rewrite-import-calls % imported) form)
    (map? form) (into (empty form)
                      (map (fn [[k v]] [(rewrite-import-calls k imported)
                                       (rewrite-import-calls v imported)]))
                      form)
    :else form))

(defn- rewrite-calls [form names]
  (cond
    (seq? form) (let [[op & args] form]
                  (list* (get names op op) (map #(rewrite-calls % names) args)))
    (vector? form) (mapv #(rewrite-calls % names) form)
    (map? form) (into (empty form)
                      (map (fn [[k v]] [(rewrite-calls k names) (rewrite-calls v names)]))
                      form)
    :else form))

(defn- source-text [forms]
  (str (str/join "\n" (map pr-str forms)) "\n"))

(defn- admit-project-forms!
  [forms counters]
  (loop [pending (seq forms)]
    (when-let [node (first pending)]
      (let [rest-pending (next pending)]
        (cond
          (coll? node)
          (do
            (when (and (seq? node)
                       (> (vswap! (:expressions counters) inc)
                          max-project-expression-nodes))
              (reject! "project expression nodes exceed limit"
                       {:count @(:expressions counters)
                        :limit max-project-expression-nodes}))
            (recur (concat (seq node) rest-pending)))

          (not (symbol? node))
          (do
            (when (> (vswap! (:literals counters) inc) max-project-literals)
              (reject! "project literals exceed limit"
                       {:count @(:literals counters) :limit max-project-literals}))
            (when (string? node)
              (let [bytes (vswap! (:literal-bytes counters)
                                  + (value/utf8-byte-count! node))]
                (when (> bytes max-project-string-literal-bytes)
                  (reject! "project string literal bytes exceed limit"
                           {:bytes bytes :limit max-project-string-literal-bytes}))))
            (recur rest-pending))

          :else (recur rest-pending))))))

(defn- analyze-module [forms info dependencies module-index]
  (let [available
        (into {}
              (mapcat (fn [{dep-name :namespace alias :alias}]
                        (let [dependency (get dependencies dep-name)]
                          (when-not dependency
                            (reject! "imported namespace was not resolved"
                                     {:module (:namespace info) :dependency dep-name}))
                          (map (fn [[export interface]]
                                 [(symbol (str alias) (str export)) interface])
                               (:interface dependency))))
                      (:requires info)))
        stub-pairs (map-indexed (fn [index [qualified interface]]
                                  [qualified (symbol (str "kotoba_import__" index)) interface])
                                (sort-by (comp str key) available))
        import->stub (into {} (map (fn [[qualified stub _]] [qualified stub]) stub-pairs))
        stub->target (into {} (map (fn [[_ stub interface]] [stub (:linked-name interface)]) stub-pairs))
        rewritten (mapv #(rewrite-import-calls % import->stub) (without-requires forms))
        augmented (into rewritten (map (fn [[_ stub interface]] (stub-form stub interface)) stub-pairs))
        hir (frontend/analyze (source-text augmented))
        stubs (set (vals import->stub))
        locals (vec (remove #(contains? stubs (:name %)) (:functions hir)))
        local-names (into {} (map-indexed (fn [function-index {:keys [name]}]
                                            [name (symbol (str "kotoba_module__"
                                                               module-index "__"
                                                               function-index))])
                                          locals))
        call-names (merge local-names stub->target)
        functions (mapv (fn [function]
                          (-> function
                              (update :name local-names)
                              (update :body rewrite-calls call-names)))
                        locals)
        by-name (into {} (map (juxt :name identity) locals))
        interface
        (into {}
              (map (fn [export]
                     (let [function (get by-name export)]
                       (when-not function
                         (reject! "export does not name a declared function"
                                  {:module (:namespace info) :export export}))
                       [export (interface-of function (get local-names export))])))
              (:exports info))]
    {:namespace (:namespace info) :requires (:requires info)
     :functions functions :interface interface}))

(defn- wrapper-form [[export {:keys [linked-name params param-types result]}]]
  (list 'defn export (typed-params params param-types) result (list* linked-name params)))

(defn link-source
  "Link a closed namespace->source map into one bounded source unit."
  [sources root]
  (when-not (and (map? sources) (pos? (count sources))
                 (<= (count sources) max-project-modules))
    (reject! "project source map is empty or exceeds module limit"
             {:count (when (map? sources) (count sources))}))
  (let [source-bytes (reduce (fn [total source]
                               (when-not (string? source)
                                 (reject! "project source must be text" {}))
                               (+ total (value/utf8-byte-count! source)))
                             0 (vals sources))
        _ (when (> source-bytes max-project-source-bytes)
            (reject! "project source bytes exceed limit" {:bytes source-bytes}))
        counters {:expressions (volatile! 0)
                  :literals (volatile! 0)
                  :literal-bytes (volatile! 0)}
        parsed (into {}
                     (map (fn [[declared source]]
                            (let [forms (frontend/read-forms source)
                                  _ (admit-project-forms! forms counters)
                                  info (module-info forms)]
                              (when-not (= declared (:namespace info))
                                (reject! "source-map key does not match declared namespace"
                                         {:key declared :declared (:namespace info)}))
                              [declared {:forms forms :info info}])))
                     sources)
        visiting (volatile! #{}) linked (volatile! {}) order (volatile! [])
        edge-count (volatile! 0)]
    (letfn [(visit [name depth]
              (when (> depth max-project-depth)
                (reject! "project dependency depth exceeds limit"
                         {:module name :depth depth}))
              (when-not (contains? parsed name)
                (reject! "required module is outside the closed project" {:module name}))
              (when (contains? @visiting name)
                (reject! "cyclic module dependency rejected" {:module name}))
              (when-not (contains? @linked name)
                (vswap! visiting conj name)
                (doseq [{dependency :namespace} (get-in parsed [name :info :requires])]
                  (when (> (vswap! edge-count inc) max-project-dependency-edges)
                    (reject! "project dependency edges exceed limit"
                             {:edges @edge-count}))
                  (visit dependency (inc depth)))
                (let [module (analyze-module (get-in parsed [name :forms])
                                             (get-in parsed [name :info])
                                             @linked (count @order))]
                  (vswap! linked assoc name module)
                  (vswap! order conj name))
                (vswap! visiting disj name)))]
      (visit root 1))
    (let [root-module (get @linked root)
          functions (vec (mapcat #(get-in @linked [% :functions]) @order))
          export-count (reduce + (map #(count (get-in @linked [% :interface])) @order))
          exports (sort-by (comp str key) (:interface root-module))
          wrappers (mapv wrapper-form exports)
          function-count (+ (count functions) (count wrappers))
          ;; The linked namespace deliberately carries NO `:capabilities`
          ;; clause even when its modules declared one. That clause is a
          ;; source-level declare-then-check over NAMED `(cap-call :some/name)`
          ;; forms, and it has already run once per module inside
          ;; `analyze-module`. By the time bodies reach here the frontend has
          ;; lowered every named cap-call to its integer id, so the linked
          ;; source contains only `(cap-call 9 ...)`, which populates no
          ;; used-keyword set -- re-declaring the union would fail its own
          ;; check with "declares a capability never used via cap-call".
          ;; Nothing is weakened by the omission: the effects the policy and
          ;; the artifact's requiredCapabilities are computed from come from
          ;; the integer cap-call forms, not from this clause.
          linked-source
          (source-text
           (into [(list 'ns root (list :export (vec (map first exports))))]
                 (concat
                  (map (fn [{:keys [name params param-types result body]}]
                         (list 'defn- name (typed-params params param-types) result body))
                       functions)
                  wrappers)))
          linked-bytes (value/utf8-byte-count! linked-source)]
      (when (> function-count max-project-functions)
        (reject! "linked project exceeds function limit" {:count function-count}))
      (when (> export-count max-project-exports)
        (reject! "linked project exports exceed limit" {:count export-count}))
      (when (> linked-bytes max-linked-source-bytes)
        (reject! "linked project source exceeds byte limit" {:bytes linked-bytes}))
      {:source
       linked-source
       :root root :module-order @order :modules (set @order)})))
