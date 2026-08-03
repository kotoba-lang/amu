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

  2. Project linking elaborates each module before linking, so the linked
     source already contains `(typed-cap-call 7 ...)` under synthetic names.
     The typed ability and the effect closure survive that -- which is what
     CI7 requires -- but the friendly-operation provenance does not:
     `:named-operations` and the `:source-operation` metadata are dropped.
     `provenance-is-lost-by-project-linking` pins the current behaviour so the
     gap is measured rather than assumed, and so that closing it is a visible
     change."
  (:require [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]
            [kotoba.compiler.frontend :as frontend]
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
  (let [single (frontend/analyze single-source)
        project (frontend/analyze (linked-source))]
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
      (is (= #{[:cap/call 7]} (entry-effects (frontend/analyze single-source))))
      (is (= #{[:cap/call 7]} (entry-effects (frontend/analyze (linked-source))))))))

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

(deftest provenance-is-lost-by-project-linking
  (testing "KNOWN GAP, pinned deliberately. Linking analyzes each module first,
            so the linked source carries the elaborated (typed-cap-call 7 ...)
            rather than clock/now. The ability and effect survive -- CI7's
            substance -- but the friendly name that produced them does not, so
            a diagnostic raised during a project build cannot point back at the
            operation the author actually wrote. Change these assertions when
            the linker preserves provenance; do not delete them."
    (let [single (frontend/analyze single-source)
          project (frontend/analyze (linked-source))]
      (is (= #{:clock/now} (:named-operations single)))
      (is (= #{} (:named-operations project))
          "if this now reports #{:clock/now}, provenance was fixed — update the note")
      (is (= :clock/now (:source-operation (meta (ability-call single)))))
      (is (nil? (:source-operation (meta (ability-call project))))))))

(deftest the-numeric-id-is-internal-not-user-facing
  (testing "the linked intermediate does contain the wire id, which is fine:
            CI7 constrains what an author must write, not what the compiler
            emits between stages"
    (is (re-find #"typed-cap-call 7" (linked-source)))
    (is (not (re-find #"typed-cap-call|:cap/call" app-source)))
    (is (not (re-find #"typed-cap-call|:cap/call" lib-source)))))
