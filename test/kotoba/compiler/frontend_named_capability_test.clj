(ns kotoba.compiler.frontend-named-capability-test
  "Tests for ADR-2607182410: named `cap-call` capabilities. A `.kotoba`
  program may write `(cap-call :identity/sign msg)` instead of a magic
  integer -- the keyword is resolved against
  `kotoba.compiler.sema/capability-registry` at parse/desugar time,
  strictly BEFORE HIR/KIR construction, so every assertion below is really
  checking that nothing downstream (HIR :functions/:effects,
  admission.cljc) can tell the two forms apart."
  (:require [clojure.test :refer [deftest is]]
            [kotoba.abi.contract :as abi]
            [kotoba.compiler.core :as compiler]
            [kotoba.sema :as sema]))

(defn- rejection-message [source]
  (try (compiler/check-source source) nil
       (catch clojure.lang.ExceptionInfo e (ex-message e))))

;; `:identity/sign` is seeded to id 1 in the language-owned semantic catalog
;; supplied by kotoba-sema as kotoba/lang/capability-catalog.edn -- asserted
;; directly here (not just relied upon) so a future re-numbering of the registry
;; fails this test loudly instead of silently changing what the other
;; assertions below actually exercise.
(deftest registry-seeds-identity-sign-as-id-1
  (is (= 1 (get sema/capability-registry :identity/sign))))

(deftest registry-covers-the-shared-typed-v03-operation-set
  (is (= abi/typed-capability-ids
         (->> sema/capability-registry
              (keep (fn [[_ id]]
                      (when (contains? abi/typed-capability-ids id) id)))
              set)))
  (is (= 13 (get sema/capability-registry :http/get-stream)))
  (is (= 16 (get sema/capability-registry
                 :object/compare-and-set-ref)))
  (is (= 17 (get sema/capability-registry :http/accept)))
  (is (= 18 (get sema/capability-registry :http/reply)))
  ;; T8.3 ops kits — catalog authority ids 19–23 (provider kits; ADR 0198)
  (is (= 19 (get sema/capability-registry :fs/transact)))
  (is (= 20 (get sema/capability-registry :process/spawn)))
  (is (= 21 (get sema/capability-registry :secret/get)))
  (is (= 22 (get sema/capability-registry :git/run)))
  (is (= 23 (get sema/capability-registry :entropy/draw))))

(deftest linear-task-stream-types-are-admitted-only-as-direct-moves
  (let [checked
        (compiler/check-source
         "(ns app (:export [open]))
          (defn open [request :i64] [:task [:stream :bytes]]
            (typed-cap-call :http/get-stream :i64
              [:task [:stream :bytes]] request))"
         {:allow #{[:cap/call 13]}})]
    (is (= [:task [:stream :bytes]]
           (get-in checked [:hir :functions 0 :result]))))
  (is (thrown-with-msg?
       clojure.lang.ExceptionInfo #"move-aware parameters"
       (compiler/check-source
        "(ns app (:export [copy]))
         (defn copy [task [:task [:stream :bytes]]]
           [:task [:stream :bytes]] task)")))
  ;; ADR 0137: single affine let-move is admitted
  (let [checked
        (compiler/check-source
         "(ns app (:export [open]))
          (defn open [request :i64] [:task [:stream :bytes]]
            (let [task (typed-cap-call :http/get-stream :i64
                         [:task [:stream :bytes]] request)]
              task))"
         {:allow #{[:cap/call 13]}})]
    (is (= 'let (first (get-in checked [:hir :functions 0 :body])))))
  ;; Multi-use of the affine binding is still rejected
  (is (thrown-with-msg?
       clojure.lang.ExceptionInfo #"one direct typed capability move"
       (compiler/check-source
        "(ns app (:export [bad]))
         (defn bad [request :i64] :i64
           (let [task (typed-cap-call :http/get-stream :i64
                        [:task [:stream :bytes]] request)]
             (+ (bytes-task-byte-count task)
                (bytes-task-byte-count task))))"
        {:allow #{[:cap/call 13]}}))))

;; ───────────────────────── round-trip equivalence ─────────────────────────

(deftest named-cap-call-lowers-to-the-identical-kir-shape-as-the-int-form
  (let [named-source "(defn audit [x] (cap-call :identity/sign x))
                       (defn helper [x] (audit x))
                       (defn main [] 42)"
        int-source "(defn audit [x] (cap-call 1 x))
                     (defn helper [x] (audit x))
                     (defn main [] 42)"
        named-hir (:hir (compiler/check-source named-source {:allow #{[:cap/call 1]}}))
        int-hir (:hir (compiler/check-source int-source {:allow #{[:cap/call 1]}}))]
    ;; Function bodies and effect rows must match. :named-operations is a
    ;; W1 diagnostic surface present only when capability keywords (or
    ;; friendly namespaced ops) appear in source, so compare without it.
    (is (= (dissoc int-hir :named-operations)
           (dissoc named-hir :named-operations)))
    (is (= #{:identity/sign} (:named-operations named-hir)))
    (is (= #{} (:named-operations int-hir)))
    (is (= #{[:cap/call 1]} (:effects named-hir)))
    (let [by-name (into {} (map (juxt :name identity) (:functions named-hir)))]
      (is (= '(cap-call 1 x) (:body (get by-name 'audit))))))
  ;; Same check at the fully-lowered KIR level (post ir/lower), across every
  ;; backend target this profile supports -- not just the wasm one.
  (doseq [target compiler/targets]
    (let [named (compiler/compile-source
                 "(defn audit [x] (cap-call :identity/sign x))
                  (defn main [] (audit 0))"
                 target {:allow #{[:cap/call 1]}})
          int' (compiler/compile-source
                "(defn audit [x] (cap-call 1 x))
                 (defn main [] (audit 0))"
                target {:allow #{[:cap/call 1]}})]
      (is (= (:kir int') (:kir named)) (str "kir mismatch for target " target)))))

;; ───────────────────────── unregistered names are rejected ─────────────────────────

(deftest unregistered-capability-keyword-is-a-hard-parse-time-error
  (is (= "cap-call names an unregistered capability: :nonsense/capability"
         (rejection-message
          "(defn main [] (cap-call :nonsense/capability 0))")))
  (is (thrown-with-msg? clojure.lang.ExceptionInfo #"unregistered capability"
                        (compiler/check-source
                         "(defn main [] (cap-call :nonsense/capability 0))"))))

(deftest malformed-named-cap-call-arity-still-rejects-with-the-original-message
  ;; A keyword in the operator position is caught by this special-cased
  ;; desugar path only when it's actually the FIRST cap-call arg; wrong
  ;; arity around it must still fail with validate-expr's ORIGINAL, arity-
  ;; generic message (not a capability-specific one) -- proving the new
  ;; desugar step doesn't mask the pre-existing arity check.
  (is (thrown-with-msg? clojure.lang.ExceptionInfo
                        #"cap-call requires a literal capability id in \[0,255\] and one value"
                        (compiler/check-source "(defn main [] (cap-call :identity/sign))")))
  (is (thrown-with-msg? clojure.lang.ExceptionInfo
                        #"cap-call requires a literal capability id in \[0,255\] and one value"
                        (compiler/check-source
                         "(defn main [] (cap-call :identity/sign 1 2))"))))

;; ───────────────────────── admission.cljc is unaffected ─────────────────────────

(deftest admission-grants-and-denies-a-named-cap-call-exactly-like-the-int-form
  (let [named-source "(defn audit [x] (cap-call :identity/sign x))
                       (defn main [] (audit 0))"
        int-source "(defn audit [x] (cap-call 1 x))
                     (defn main [] (audit 0))"]
    ;; Same allow-list grants both forms identically.
    (let [{:keys [hir admission]} (compiler/check-source named-source {:allow #{[:cap/call 1]}})]
      (is (:admitted? admission))
      (is (= #{[:cap/call 1]} (:effects hir)))
      (is (= {:allow #{[:cap/call 1]}} (:minimal-policy admission))))
    (is (= (:admission (compiler/check-source int-source {:allow #{[:cap/call 1]}}))
           (:admission (compiler/check-source named-source {:allow #{[:cap/call 1]}}))))
    ;; A policy that only grants a DIFFERENT id denies both forms identically
    ;; (deny-by-default is untouched by naming).
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"denies required effects"
                          (compiler/check-source named-source {:allow #{[:cap/call 2]}})))
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"denies required effects"
                          (compiler/check-source int-source {:allow #{[:cap/call 2]}})))
    ;; No policy at all denies both forms identically (deny-by-default).
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"denies required effects"
                          (compiler/check-source named-source)))
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"denies required effects"
                          (compiler/check-source int-source)))))

;; ───────────────────────── optional ns :capabilities declaration ─────────────────────────

(deftest ns-capabilities-declaration-accepts-a-matching-declare-then-check
  (let [source "(ns app.core (:capabilities #{:identity/sign}))
                (defn audit [x] (cap-call :identity/sign x))
                (defn main [] (audit 0))"
        {:keys [hir admission]} (compiler/check-source source {:allow #{[:cap/call 1]}})]
    (is (:admitted? admission))
    (is (= #{[:cap/call 1]} (:effects hir)))))

(deftest ns-capabilities-declaration-rejects-used-but-undeclared
  (is (thrown-with-msg? clojure.lang.ExceptionInfo
                        #"not declared in namespace :capabilities"
                        (compiler/check-source
                         "(ns app.core (:capabilities #{:hash/sha256}))
                          (defn audit [x] (cap-call :identity/sign x))
                          (defn main [] (audit 0))"
                         {:allow #{[:cap/call 1]}}))))

(deftest ns-capabilities-declaration-rejects-declared-but-unused
  (is (thrown-with-msg? clojure.lang.ExceptionInfo
                        #"never used via cap-call"
                        (compiler/check-source
                         "(ns app.core (:capabilities #{:identity/sign :hash/sha256}))
                          (defn audit [x] (cap-call :identity/sign x))
                          (defn main [] (audit 0))"
                         {:allow #{[:cap/call 1]}}))))

(deftest ns-capabilities-declaration-is-optional-and-backward-compatible
  ;; No `:capabilities` clause at all -- the pre-existing `ns` grammar
  ;; (bare symbol, optional docstring, optional `:export`) keeps working
  ;; unchanged, and named cap-call still resolves normally.
  (is (:admitted? (:admission (compiler/check-source
                               "(ns app.core)
                                (defn audit [x] (cap-call :identity/sign x))
                                (defn main [] (audit 0))"
                               {:allow #{[:cap/call 1]}})))))

(deftest ops-kit-named-cap-call-lowers-like-int-form
  "T8.3 catalog 19–23: named ops kit keyword lowers identically to numeric id."
  (let [named-source "(defn run [x] (cap-call :process/spawn x))
                       (defn main [] (run 0))"
        int-source "(defn run [x] (cap-call 20 x))
                     (defn main [] (run 0))"
        named-hir (:hir (compiler/check-source named-source {:allow #{[:cap/call 20]}}))
        int-hir (:hir (compiler/check-source int-source {:allow #{[:cap/call 20]}}))]
    (is (= (dissoc int-hir :named-operations)
           (dissoc named-hir :named-operations)))
    (is (= #{:process/spawn} (:named-operations named-hir)))
    (is (= #{[:cap/call 20]} (:effects named-hir)))))
