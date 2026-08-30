(ns kotoba.compiler.check-cli-test
  "T9.2 / T3.4: check-source pure-product + human diagnostics."
  (:require [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]
            [kotoba.compiler.diagnostic :as diagnostic]
            [kotoba.compiler.project :as project]
            [kotoba.sema :as sema]))

(def pure-ok
  "(ns demo (:export [main]))\n(defn main [] :i64 (+ 1 2))\n")

(def pure-eval-bad
  "(ns demo (:export [main]))\n(defn main [] (eval 1))\n")

(def pure-caps-bad
  "(ns demo (:export [main]) (:capabilities #{:clock/now}))\n(defn main [] 0)\n")

(deftest check-source-default-admits-pure
  (let [r (compiler/check-source pure-ok)]
    (is (true? (get-in r [:admission :admitted?])))
    (is (nil? (:language-profile r)))
    (is (empty? (get-in r [:hir :effects])))))

(deftest check-source-pure-product-admits-pure
  (let [r (compiler/check-source pure-ok {:language-profile :pure-product})]
    (is (= :pure-product (:language-profile r)))
    (is (true? (get-in r [:admission :admitted?])))))

(deftest check-source-pure-product-rejects-eval
  (is (thrown-with-msg? clojure.lang.ExceptionInfo #"pure-product|eval|forbidden"
        (compiler/check-source pure-eval-bad {:language-profile :pure-product}))))

(deftest check-source-pure-product-rejects-capabilities
  (try
    (compiler/check-source pure-caps-bad {:language-profile :pure-product})
    (is false "expected reject")
    (catch clojure.lang.ExceptionInfo e
      (is (= :kotoba.error/pure-product-capabilities
             (:kotoba.error/code (ex-data e)))))))

(deftest format-human-includes-code-and-message
  (try
    (sema/analyze pure-caps-bad {:language-profile :pure-product})
    (is false)
    (catch clojure.lang.ExceptionInfo e
      (let [s (diagnostic/format-human e "demo.kotoba")]
        (is (re-find #"error: pure-product-capabilities" s))
        (is (re-find #"demo\.kotoba" s))
        (is (re-find #"capabilities" s))))))

;; ---------------------------------------------------------------------------
;; A module of a multi-file project (2026-08-30). `(:require [ns :as alias])`
;; is admitted by `kotoba.compiler.project` and reached by
;; `compile`/`check --source-path` and `--module-lock`; the single-module
;; frontend rejects it through the same fall-through as a malformed `:export`,
;; so the caller was told the one thing that is not the problem.

(def require-module
  "(ns app.root (:require [app.util :as util]) (:export [main]))\n(defn main [] :i64 (util/answer))\n")

;; `or` matters: `project/link-source` re-emits the desugared form as a
;; `__kotoba_or_*` synthetic, which is the reserved prefix authored source may
;; not use. Without it this module links to source containing no synthetic at
;; all, and the check-project test below passes whether or not `check-source`
;; can accept one -- measured 2026-08-30, the first version of that test did
;; exactly that.
(def util-module
  "(ns app.util (:export [answer]))\n(defn answer [] :i64 (if (or (< 1 0) (> 1 999)) 0 42))\n")

(defn- analyze-error [source]
  (try (sema/analyze source {}) nil
       (catch clojure.lang.ExceptionInfo e e)))

(deftest require-clause-rejection-names-the-project-path
  (let [e (analyze-error require-module)
        refined (diagnostic/refine e)]
    (is (some? e) "a (:require ...) module must not pass the single-module path")
    ;; The frontend's own code is untouched: subset corpora keep asserting it.
    (is (= :kotoba.error/namespace-export-clause (:kotoba.error/code (ex-data e))))
    (is (= :kotoba.error/namespace-require-needs-project (:code refined)))
    (is (= :kotoba.error/namespace-require-needs-project
           (:code (diagnostic/from-error e "root.kotoba"))))
    (is (re-find #"multi-file project" (:message refined)))
    ;; Every command named here is measured working in ADR 0287.
    (is (= "module-lock <entry> --source-path <dir> --blocks <dir>"
           (get-in refined [:details :pin])))
    (is (= "compile --module-lock <lock> --blocks <dir>"
           (get-in refined [:details :then])))
    (is (= "check <entry> --source-path <dir>" (get-in refined [:details :check])))
    (let [human (diagnostic/format-human e "root.kotoba")]
      (is (re-find #"namespace-require-needs-project" human))
      (is (re-find #"--source-path" human)))))

(deftest refinement-stops-at-clauses-with-no-supported-path
  ;; `:import` and `:use` are forbidden outright (guest-grammar diagnostic
  ;; hints): naming a project invocation for them would advertise a path that
  ;; does not exist. A malformed `:export` is a real malformed `:export`.
  (doseq [source ["(ns t (:import [java.lang String]) (:export [f]))\n(defn f [] :i64 1)\n"
                  "(ns t (:use [other]) (:export [f]))\n(defn f [] :i64 1)\n"
                  "(ns t (:export f))\n(defn f [] :i64 1)\n"]]
    (let [e (analyze-error source)]
      (is (some? e) source)
      (is (nil? (diagnostic/refine e)) source)
      (is (= :kotoba.error/namespace-export-clause
             (:code (diagnostic/from-error e "t.kotoba")))
          source))))

(deftest check-project-admits-a-linked-closed-graph
  ;; Same link `compile-project` performs, stopped before lowering. Without
  ;; `:admit-linked-synthetics?` this refuses its own linker's output with
  ;; "symbol uses the reserved __kotoba_ prefix" (measured before the fix).
  ;;
  ;; The first assertion is the discrimination floor: if linking ever stops
  ;; emitting a reserved-prefix symbol for this input, the rest of this test
  ;; would still pass while testing nothing.
  (let [linked (project/link-source {'app.root require-module 'app.util util-module}
                                    'app.root)
        r (compiler/check-project {'app.root require-module 'app.util util-module}
                                  'app.root)]
    (is (re-find #"__kotoba_" (:source linked))
        "linking no longer emits a reserved-prefix synthetic; this test no longer discriminates")
    (is (true? (get-in r [:admission :admitted?])))
    (is (= 'app.root (:root r)))
    (is (= ['app.util 'app.root] (:module-order r)))
    (is (= ['main] (get-in r [:hir :exports])))
    (is (empty? (get-in r [:hir :effects])))))

(deftest check-project-still-refuses-a-module-it-should
  ;; The gate is not widened by linking: a forbidden head inside a dependency
  ;; is still refused, and refused for its own reason.
  (let [bad "(ns app.util (:export [answer]))\n(defn answer [] :i64 (eval 1))\n"]
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"eval|forbidden|ambient"
          (compiler/check-project {'app.root require-module 'app.util bad}
                                  'app.root)))))

(deftest project-link-refusals-are-not-reported-as-internal-errors
  ;; `amu check <entry> --source-path <dir>` on a project naming a module it
  ;; does not ship exits 65 with :error :project-link and a specific message,
  ;; but the structured :diagnostic :code fell through to
  ;; :kotoba/internal-error -- indistinguishable from a compiler crash.
  (let [d (diagnostic/from-error
           (ex-info "required module is missing from the explicit source paths"
                    {:phase :project-link :module 'app.gone})
           "root.kotoba")]
    (is (= :kotoba/project-link-failed (:code d)))
    (is (not= :kotoba/internal-error (:code d))))
  ;; The fallback itself must survive: an error with no phase is still internal.
  (is (= :kotoba/internal-error
         (:code (diagnostic/from-error (ex-info "boom" {}) "root.kotoba")))))
