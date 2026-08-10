(ns kotoba.compiler.ci7-elaboration-parity-test
  "CI7: a friendly source operation must elaborate to the same typed
  ability/effect KIR whether it is compiled as one file or as a project, and
  no user-facing numeric capability id or host callback may be required to
  write it.

  Two things this found, both recorded below as tests rather than prose:

  1. Friendly capability operations did not compile in project mode at all.
     `project/link-source` treated every namespaced call as a module import
     and rejected `(clock/now seed)` with `qualified call is not an admitted
     exported import`. The single-file path accepted the same source. That is
     now fixed in kotoba.compiler.project/capability-operation?.

  2. Project linking elaborates each module before linking, so the body it
     emitted was already `(typed-cap-call 7 ...)` under a synthetic name. The
     typed ability and the effect closure survived that, but the friendly
     operation did not: `:named-operations` came out empty for a project build
     where a single file reported `#{:clock/now}`, so a diagnostic could not
     name the operation the author wrote. Fixed by
     `project/resugar-capability-calls`, which uses the `:source-operation`
     metadata the elaborated form still carries to restore the source spelling
     for capability calls only -- module-to-module calls keep their synthetic
     names, so per-module isolation is unchanged."
  (:require [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]
            [kotoba.sema :as sema]
            [kotoba.compiler.project :as project]))

;; The same program, written once as a single file and once split across two
;; modules. Both call the friendly operation `clock/now`; neither mentions a
;; capability id.
(def ^:private single-source
  "(ns ci7.single (:export [main]))
   (defn read-clock [seed :i64] :i64 (clock/now seed))
   (defn main [] :i64 (read-clock 42))")

(def ^:private lib-source
  "(ns ci7.clock (:export [read-clock]))
   (defn read-clock [seed :i64] :i64 (clock/now seed))")

(def ^:private app-source
  "(ns ci7.app (:require [ci7.clock :as lib]) (:export [main]))
   (defn main [] :i64 (lib/read-clock 42))")

(def ^:private clock-policy {:allow #{[:cap/call 7]}})

(defn- linked-source []
  (:source (project/link-source {'ci7.app app-source 'ci7.clock lib-source}
                                'ci7.app)))

(defn- ability-call
  "The elaborated typed ability call, wherever it ended up. Project linking
  renames functions to synthetic module symbols, so it cannot be found by the
  author's name."
  [hir]
  (->> (:functions hir)
       (keep (fn [f]
               (let [body (:body f)]
                 (when (and (seq? body) (= 'typed-cap-call (first body))) body))))
       first))

(deftest neither-form-requires-a-numeric-capability-or-a-callback
  (testing "CI7's admission rule is about what an author must write, so it is
            checked against the source text the author wrote"
    (doseq [[label source] [[:single single-source] [:lib lib-source] [:app app-source]]]
      (is (not (re-find #"\((cap-call|typed-cap-call)\b" source)) (str label))
      (is (not (re-find #"\[:cap/call" source)) (str label))
      (is (not (re-find #"provider|callback|host-import" source)) (str label)))
    (is (re-find #"\(clock/now\b" single-source))
    (is (re-find #"\(clock/now\b" lib-source))))

(deftest a-friendly-operation-compiles-in-project-mode
  (testing "regression: link-source used to reject any namespaced call that was
            not an imported export, which made clock/now unwritable inside a
            project even though the single-file path accepted it"
    (is (string? (linked-source)))))

(deftest the-typed-ability-and-effect-are-identical-either-way
  (let [single (sema/analyze single-source)
        project (sema/analyze (linked-source))]
    (testing "inferred effect closure"
      (is (= #{[:cap/call 7]} (:effects single)))
      (is (= (:effects single) (:effects project))))
    (testing "the same typed ability call, with the same wire id and types"
      (is (= '(typed-cap-call 7 :i64 :i64 seed) (ability-call single)))
      (is (= '(typed-cap-call 7 :i64 :i64 seed) (ability-call project))))))

(deftest transitive-effects-cross-a-module-boundary
  (testing "the entry point acquires the effect through a call into another
            module, exactly as it does through a call within one file"
    (let [entry-effects (fn [hir] (some #(when (= 'main (:name %)) (:effects %))
                                        (:functions hir)))]
      (is (= #{[:cap/call 7]} (entry-effects (sema/analyze single-source))))
      (is (= #{[:cap/call 7]} (entry-effects (sema/analyze (linked-source))))))))

(defn- admission-missing
  "check-source throws on denial rather than returning a diagnostic, so the
  denial path has to be observed through the thrown data."
  [source policy]
  (try
    (get-in (compiler/check-source source policy) [:admission :missing])
    (catch clojure.lang.ExceptionInfo e (:missing (ex-data e)))))

(deftest admission-agrees-on-both-paths
  (testing "the same policy admits both"
    (is (true? (get-in (compiler/check-source single-source clock-policy)
                       [:admission :admitted?])))
    (is (true? (get-in (compiler/check-source (linked-source) clock-policy)
                       [:admission :admitted?]))))
  (testing "and an empty policy denies both with the same missing grant --
            linking must not launder an effect past a policy that would have
            refused it in a single file"
    (is (= #{[:cap/call 7]} (admission-missing single-source {})))
    (is (= #{[:cap/call 7]} (admission-missing (linked-source) {})))))

(deftest provenance-survives-project-linking
  (testing "Linking analyzes each module, so the body it emits is already
            elaborated and the friendly name would be gone by the time the
            linked source is re-analyzed. project/resugar-capability-calls puts
            it back, using the :source-operation metadata the elaborated form
            still carries. Without it, :named-operations came out empty for a
            project build where a single file reported #{:clock/now}, and a
            diagnostic could not name the operation the author wrote."
    (let [single (sema/analyze single-source)
          project (sema/analyze (linked-source))]
      (is (= #{:clock/now} (:named-operations single)))
      (is (= (:named-operations single) (:named-operations project)))
      (is (= :clock/now (:source-operation (meta (ability-call single)))))
      (is (= :clock/now (:source-operation (meta (ability-call project))))))))

(deftest resugaring-touches-only-capability-calls
  (testing "module-to-module calls keep their synthetic names, so per-module
            isolation is unchanged -- restoring provenance must not make one
            module's syntax able to mean something different after linking"
    (let [linked (linked-source)]
      (is (re-find #"\(clock/now seed\)" linked))
      (is (re-find #"kotoba_module__" linked))
      (is (not (re-find #"lib/read-clock" linked))))))

(deftest the-author-never-writes-a-wire-id
  (testing "CI7 constrains what an author must write. The friendly form now
            survives into the linked intermediate too, so the wire id is
            confined to the compiler's later stages."
    (is (not (re-find #"typed-cap-call|:cap/call" app-source)))
    (is (not (re-find #"typed-cap-call|:cap/call" lib-source)))
    (is (not (re-find #"typed-cap-call|:cap/call" single-source)))
    (is (not (re-find #"typed-cap-call" (linked-source))))))

;; ---------------------------------------------------------------------------
;; Source map: translating a linked position back to the module that wrote it

(deftest linked-lines-resolve-to-the-authoring-module
  (testing "Every span the frontend derives from linked source refers to the
            synthetic intermediate, so a project-build diagnostic could name
            the operation but not the file it came from. link-source now
            returns a map from linked line to authoring module."
    (let [{:keys [source source-map]}
          (project/link-source {'ci7.app app-source 'ci7.clock lib-source} 'ci7.app)
          ;; the emitted body carrying the capability call
          capability-line (->> (clojure.string/split-lines source)
                               (keep-indexed (fn [i l]
                                               (when (clojure.string/includes? l "clock/now")
                                                 (inc i))))
                               first)
          entry (project/source-position source-map capability-line)]
      (is (some? capability-line))
      (is (= 'ci7.clock (:module entry))
          "the capability call came from the library module, not the root")
      (is (= 'read-clock (:source-name entry))
          "and from the function the author named, not its synthetic rename")
      (testing "the span is the position inside that module's own source"
        (is (= 2 (get-in entry [:source-span :line])))
        (is (= 35 (get-in entry [:source-span :column])))))))

(deftest the-map-attributes-nothing-an-author-did-not-write
  (testing "the ns form and any synthetic dispatcher or export wrapper have no
            authoring module, so they are absent rather than attributed to one"
    (let [{:keys [source-map]}
          (project/link-source {'ci7.app app-source 'ci7.clock lib-source} 'ci7.app)]
      (is (nil? (project/source-position source-map 1)) "line 1 is the ns form")
      (is (nil? (project/source-position source-map 9999)))
      (is (every? #(contains? #{'ci7.app 'ci7.clock} (:module %))
                  (:entries source-map))))))

(deftest module-attribution-is-total-even-where-a-span-is-not
  (testing "Module and function name resolve for every emitted module function.
            The fine-grained span is only present where the frontend attached
            one -- it does so for capability calls, not for every body -- so a
            consumer gets file-level attribution always and line-level where it
            exists. Stated rather than implied, because a map that silently
            returned nil spans would look broken."
    (let [{:keys [source-map]}
          (project/link-source {'ci7.app app-source 'ci7.clock lib-source} 'ci7.app)
          entries (:entries source-map)]
      (is (seq entries))
      (is (every? :module entries))
      (is (every? :source-name entries))
      (is (some :source-span entries) "at least the capability call carries one"))))
