(ns kotoba.compiler.diagnostic)

(def phase-codes
  {:usage :kotoba/invalid-usage
   :decode :kotoba/invalid-data
   :read :kotoba/source-read-failed
   :subset :kotoba/source-rejected
   :admission :kotoba/admission-denied
   :ir :kotoba/lowering-failed
   :verify :kotoba/verification-failed
   :coverage :kotoba/coverage-failed
   :signature :kotoba/signature-failed
   :trust :kotoba/trust-failed
   :runtime-identity :kotoba/runtime-identity-failed
   :output :kotoba/output-failed
   :execute :kotoba/execution-failed
   :receipt :kotoba/receipt-failed
   :internal :kotoba/internal-error
   :effect-ceiling :kotoba/effect-ceiling
   :target :kotoba/target-rejected
   :target-routing :kotoba/target-routing})

(declare refine refined-message)

(defn from-error
  "Build a :kotoba.diagnostic/v1 map from an ExceptionInfo.

  Prefer a specific `:kotoba.error/code` on ex-data when present (T3.1);
  otherwise fall back to coarse `phase-codes`. Keeps the v1 shape stable for CLI
  envelopes (no message/form leakage into :diagnostic)."
  [error source-name]
  (let [data (ex-data error)
        phase (or (:phase data) :internal)
        code (or (:code (refine error))
                 (:kotoba.error/code data)
                 (get phase-codes phase :kotoba/internal-error))]
    (cond-> {:format :kotoba.diagnostic/v1
             :code code
             :severity :error}
      (string? source-name) (assoc :source source-name)
      (map? (:span data)) (assoc :span (:span data)))))

(defn format-human
  "T3.4: single-line human diagnostic for CLI default mode.

  Shape: `error: <code> at <source>:<line>:<col>: <message>`
  Falls back gracefully when span/source missing."
  [error source-name]
  (let [data (ex-data error)
        d (from-error error source-name)
        code (name (:code d))
        span (:span d)
        loc (cond
              (and (string? source-name) (map? span)
                   (or (:line span) (:column span)))
              (str source-name
                   (when (:line span) (str ":" (:line span)))
                   (when (:column span) (str ":" (:column span))))
              (string? source-name) source-name
              (map? span)
              (str "line " (:line span) " col " (:column span))
              :else nil)
        msg (or (refined-message error (ex-message error)) "error")]
    (if loc
      (str "error: " code " at " loc ": " msg)
      (str "error: " code ": " msg))))

;; ---------------------------------------------------------------------------
;; Project-mode routing refusals.
;;
;; A module of a multi-file project carries `(:require [ns :as alias])` in its
;; namespace header. `kotoba.sema`'s single-module frontend admits `:export`,
;; `:capabilities` and `:schemas` and rejects every other clause head through
;; ONE fall-through, so the module got the message written for a malformed
;; `:export` vector: "only a bounded :export vector is admitted in namespace
;; clauses". That is true of the path the caller happened to take and says
;; nothing about the path that does admit `:require` -- `kotoba.compiler.project`
;; links exactly this clause, and `compile --source-path` / `--module-lock`
;; reach it. Measured 2026-08-30 on org-iso-h264: the same three files that
;; `check` refused this way compile through project mode.
;;
;; This does not admit anything. It renames one refusal so it names the path
;; that works, and it stops short of `:import` / `:use`, which have no such
;; path and must keep reading as forbidden.

(def ^:private require-clause-remedy
  "Fixed command shapes, not derived from user input, so they are safe to put
  in an error envelope that otherwise redacts ex-data."
  {:problem :namespace/require-needs-project
   :pin "module-lock <entry> --source-path <dir> --blocks <dir>"
   :then "compile --module-lock <lock> --blocks <dir>"
   :check "check <entry> --source-path <dir>"
   :override "compile <entry> --source-path <dir> --unpinned"})

(def ^:private require-clause-message
  (str "this namespace declares (:require ...), so it is a module of a multi-file "
       "project; the single-module path admits only a standalone namespace. "
       "Pin the graph with `amu module-lock <entry> --source-path <dir> --blocks <dir>` "
       "then `amu compile --module-lock <lock> --blocks <dir>`; "
       "`amu check <entry> --source-path <dir>` links and checks it without emitting."))

(defn- require-clause-rejection? [data]
  (and (= :kotoba.error/namespace-export-clause (:kotoba.error/code data))
       (let [form (:form data)]
         (and (seq? form) (= :require (first form))))))

(defn refine
  "Answer `{:code :message :details}` when this error is a project-mode routing
  refusal wearing a single-module message, else nil.

  Callers keep their own fallbacks: this is a rename at the reporting boundary,
  not a second admission decision. `ex-data`'s `:kotoba.error/code` is left as
  the frontend set it, so subset-corpus assertions are unaffected."
  [error]
  (let [data (ex-data error)]
    (when (require-clause-rejection? data)
      {:code :kotoba.error/namespace-require-needs-project
       :message require-clause-message
       :details require-clause-remedy})))

(defn refined-message
  "The refined message when one applies, else `fallback` (the caller's
  `ex-message` on the JVM, `.-message` under nbb)."
  [error fallback]
  (or (:message (refine error)) fallback))
