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

(defn from-error
  "Build a :kotoba.diagnostic/v1 map from an ExceptionInfo.

  Prefer a specific `:kotoba.error/code` on ex-data when present (T3.1);
  otherwise fall back to coarse `phase-codes`. Keeps the v1 shape stable for CLI
  envelopes (no message/form leakage into :diagnostic)."
  [error source-name]
  (let [data (ex-data error)
        phase (or (:phase data) :internal)
        code (or (:kotoba.error/code data)
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
        msg (or (ex-message error) "error")]
    (if loc
      (str "error: " code " at " loc ": " msg)
      (str "error: " code ": " msg))))
