(ns test.nbb.log-provider
  "W5 first slice — dual-runtime semantic vectors for `log-v1` on `:cljs`.

  Mirrors `test/kotoba/compiler/log_provider_test.clj` (the `:clj` oracle)
  through the same typed `typed-cap-call` + reference-runtime boundary.
  `clojure -M:test` never loads cljs, so this is the place the log kit's
  `:cljs` provider path (bounds, retention truncation, denial) actually runs.

  Run from the repo root: `npm run test-nbb-log-provider`."
  (:require [kotoba.kir.admission :as admission]
            [kotoba.kir.cljs-i64 :as i64]
            [kotoba.sema :as sema]
            [kotoba.kir :as ir]
            [provider.log :as log]
            [kotoba.compiler.reference-runtime :as runtime]))

(def source
  (str "(ns app.log (:export [append read]) "
       "(:capabilities #{:log/append :log/read}))"
       "(defn append [request " (pr-str log/append-request-type) "] "
       (pr-str log/append-result-type) " (typed-cap-call :log/append "
       (pr-str log/append-request-type) " " (pr-str log/append-result-type) " request))"
       "(defn read [request " (pr-str log/read-request-type) "] "
       (pr-str log/read-result-type) " (typed-cap-call :log/read "
       (pr-str log/read-request-type) " " (pr-str log/read-result-type) " request))"))

(defn- hosted []
  (let [kit (log/create-provider)
        hir (sema/analyze source)
        _ (admission/check hir {:allow #{[:cap/call (js/BigInt 5)] [:cap/call (js/BigInt 6)]}})
        kir (ir/lower hir)]
    {:kit kit
     :runtime (runtime/instantiate kir {:allow #{5 6} :providers (:providers kit)})}))

(defn- check [name ok? detail]
  {:name name :ok? (boolean ok?) :detail (when-not ok? detail)})

(defn- refusal
  "What THUNK refused with: the exception's ex-data plus its :message, or nil
  when it did not refuse.

  Cases assert the structured keys where the provider carries one that
  identifies the guard -- :phase plus the operand it rejected -- and the
  message only where it does not. A message is not the contract: measured
  2026-08-18, three cases in this directory matched wording that belonged to a
  guard behind the one that actually fired, and failed while the property in
  their own name still held."
  [thunk]
  (try (thunk) nil (catch :default e (assoc (or (ex-data e) {}) :message (.-message e)))))

(defn- append-and-read-case []
  (try
    (let [{:keys [runtime]} (hosted)
          fields [log/field-set-type [[log/field-type :request/id "r-1"]]]
          request [log/append-request-type :log/info :app/started "ready" fields]
          entry [log/entry-type i64/one :log/info :app/started "ready" fields]
          append-result ((:invoke runtime) 'append [request])
          read-result ((:invoke runtime) 'read [[log/read-request-type i64/zero (js/BigInt 8)]])]
      (check "cljs-append-and-read-use-structured-bounded-values"
             (and (= [log/append-result-type i64/one] append-result)
                  (= [log/read-result-type i64/one i64/one false
                      [log/entry-set-type [entry]]]
                     read-result))
             (pr-str {:append append-result :read read-result})))
    (catch :default e
      (check "cljs-append-and-read-use-structured-bounded-values" false (.-message e)))))

(defn- field-and-read-limits-case []
  (try
    (let [{:keys [kit runtime]} (hosted)
          fields (mapv (fn [index]
                         [log/field-type (keyword "field" (str index)) "value"])
                       (range 5))
          append-denial
          (refusal #((:invoke runtime) 'append
                     [[log/append-request-type :log/info :app/event "message"
                       [log/field-set-type fields]]]))
          read-denial
          (refusal #((:invoke runtime) 'read
                     [[log/read-request-type i64/zero (js/BigInt 9)]]))
          cursor-denial
          (refusal #((:invoke runtime) 'read
                     [[log/read-request-type (js/BigInt -1) i64/one]]))]
      (check "cljs-field-and-read-limits-fail-before-mutation"
             ;; The two read refusals carry the operand they rejected, so that
             ;; is what they assert. The field-limit refusal carries only
             ;; :phase (measured 2026-08-18), so its message stays -- with
             ;; :phase beside it, which the wording alone did not check.
             (and (= :log-provider (:phase append-denial))
                  (re-find #"field limit" (:message append-denial))
                  (= :log-provider (:phase read-denial))
                  (= (js/BigInt 9) (:limit read-denial))
                  (= :log-provider (:phase cursor-denial))
                  (= (js/BigInt -1) (:after-sequence cursor-denial))
                  (empty? ((:snapshot kit))))
             (pr-str {:append append-denial :read read-denial
                      :cursor cursor-denial :snapshot ((:snapshot kit))})))
    (catch :default e
      (check "cljs-field-and-read-limits-fail-before-mutation" false (.-message e)))))

(defn- retained-window-case []
  (try
    (let [{:keys [runtime]} (hosted)
          fields [log/field-set-type []]
          _ (dotimes [index (inc log/max-retained-entries)]
              ((:invoke runtime) 'append
               [[log/append-request-type :log/info :app/event (str index) fields]]))
          [_ oldest latest truncated [_ entries]]
          ((:invoke runtime) 'read [[log/read-request-type i64/zero i64/one]])]
      (check "cljs-retained-window-signals-truncation"
             (and (= (js/BigInt 2) oldest)
                  (= (js/BigInt 257) latest)
                  (true? truncated)
                  (= (js/BigInt 2) (second (first entries))))
             (pr-str {:oldest oldest :latest latest :truncated truncated
                      :first-entry (first entries)})))
    (catch :default e
      (check "cljs-retained-window-signals-truncation" false (.-message e)))))

(defn- denial-case []
  (try
    (let [hir (sema/analyze source)
          _ (admission/check hir {:allow #{[:cap/call (js/BigInt 5)] [:cap/call (js/BigInt 6)]}})
          kir (ir/lower hir)
          runtime (runtime/instantiate kir)
          append-denial
          (refusal #((:invoke runtime) 'append
                     [[log/append-request-type :log/info :app/started "ready"
                       [log/field-set-type []]]]))
          read-denial
          (refusal #((:invoke runtime) 'read
                     [[log/read-request-type i64/zero i64/one]]))]
      (check "cljs-missing-grant-denies-before-provider-invoke"
             ;; WHICH capability each call was denied for. Two ids are in play
             ;; and they are NOT in the order the `#{:log/append :log/read}`
             ;; literal above reads: capability-kits/log-v1.edn assigns
             ;; :log/read id 5 and :log/append id 6, which is what the denials
             ;; carry. Matching only the message could never have said so.
             (and (= :reference-runtime (:phase append-denial))
                  (= (js/BigInt 6) (:capability append-denial))
                  (= :reference-runtime (:phase read-denial))
                  (= (js/BigInt 5) (:capability read-denial)))
             (pr-str {:append append-denial :read read-denial})))
    (catch :default e
      (check "cljs-missing-grant-denies-before-provider-invoke" false (.-message e)))))

(let [results [(append-and-read-case)
               (field-and-read-limits-case)
               (retained-window-case)
               (denial-case)]
      failures (remove :ok? results)]
  (doseq [{:keys [name ok? detail]} results]
    (println (if ok? "PASS" "FAIL") name (or detail "")))
  (println (count results) "cases," (count failures) "failed")
  (when (seq failures) (.exit js/process 1)))
