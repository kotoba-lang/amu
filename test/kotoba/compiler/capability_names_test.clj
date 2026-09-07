(ns kotoba.compiler.capability-names-test
  "The user-facing spelling of a capability grant.

  `lang/capability-catalog.edn` says `:numeric-id :not-user-facing`, and the
  `:implicit-ability-elaboration` stage in `lang/elaboration-pipeline.edn`
  carries the rule `:no-user-facing-numeric-ids`. Measured 2026-08-31, `check`
  answered a guest whose source contains no number at all with
  `:effects #{[:cap/call 3]}` and a `:minimal-policy` spelled the same way, so
  writing the `--policy` file it asked for meant knowing that `hash/sha256` is
  3.

  These assert the two halves of the boundary, by exact value: what `check`
  PRINTS, and what `--policy` ACCEPTS. The wire id is deliberately not asserted
  away -- `wire-policy` must still produce it, because admission, KIR and the
  emitted bytes are all agreed on the integer."
  (:require [kotoba.compiler.atomic-output :as atomic-output]
            [clojure.edn :as edn]
            [clojure.test :refer [deftest is testing use-fixtures]]
            [kotoba.compiler.capability-names :as cap-names]
            [kotoba.compiler.cli :as cli])
  (:import [java.io StringWriter]))

;; Same reason as `kotoba.compiler.cli-test`'s: an unexpected `*exit*` would
;; end the JVM mid-suite, which reads as silence rather than as a failure.
(use-fixtures :each
  (fn [run]
    (binding [cli/*exit* (fn [status]
                           (throw (ex-info "cli exited during a test that did not expect it"
                                           {:status status})))]
      (run))))

(def ^:private hash-guest
  "(ns demo (:export [main]))\n(defn main [] :string (hash/sha256 \"x\"))\n")

(defn- temp-file! [contents extension]
  (let [file (atomic-output/temp-file! "kotoba-capability-names-" extension)]
    (spit file contents)
    (.getPath file)))

;; ---------------------------------------------------------------------------
;; Out: what a person reads.

(deftest named-grant-replaces-the-wire-id-with-the-catalog-name
  (is (= [:cap/call :hash/sha256] (cap-names/named-grant [:cap/call 3])))
  (is (= [:cap/call :clock/now] (cap-names/named-grant [:cap/call 7]))))

(deftest named-grant-is-idempotent
  (is (= [:cap/call :hash/sha256]
         (cap-names/named-grant (cap-names/named-grant [:cap/call 3])))))

(deftest an-id-with-no-catalog-name-is-reported-as-written
  ;; The only way to reach one is to write `(cap-call 200 x)` -- a literal
  ;; integer -- in the guest source. Handing that number back is an answer;
  ;; inventing a name for it would be a lie.
  (is (= [:cap/call 200] (cap-names/named-grant [:cap/call 200]))))

(deftest name-grants-reaches-every-grant-in-a-reported-structure
  ;; The shape `check` prints: the effect row, the admission decision, the
  ;; minimal policy, and the ABAC attributes admission echoes back.
  (is (= {:effects #{[:cap/call :hash/sha256]}
          :admission {:required #{[:cap/call :hash/sha256]}
                      :minimal-policy {:allow #{[:cap/call :hash/sha256]}}
                      :abac {:abac/attributes
                             {:action {:capabilities #{[:cap/call :hash/sha256]}}}}}}
         (cap-names/name-grants
          {:effects #{[:cap/call 3]}
           :admission {:required #{[:cap/call 3]}
                       :minimal-policy {:allow #{[:cap/call 3]}}
                       :abac {:abac/attributes
                              {:action {:capabilities #{[:cap/call 3]}}}}}}))))

(deftest name-grants-leaves-everything-that-is-not-a-grant-alone
  (is (= {:exports ['main] :limit 255 :pair [:cap/other 3] :triple [:cap/call 3 4]}
         (cap-names/name-grants
          {:exports ['main] :limit 255 :pair [:cap/other 3] :triple [:cap/call 3 4]}))))

;; ---------------------------------------------------------------------------
;; In: what `--policy` accepts.

(deftest wire-policy-turns-a-named-grant-into-the-wire-id
  (is (= {:allow #{[:cap/call 3]}}
         (cap-names/wire-policy {:allow #{[:cap/call :hash/sha256]}}))))

(deftest wire-policy-leaves-a-numeric-policy-exactly-as-it-was
  ;; This is the artifact-identity claim in unit form: a policy file written
  ;; the old way must reach admission and provenance unchanged.
  (let [numeric {:allow #{[:cap/call 3] [:cap/call 7]} :budgets {:fuel 512}}]
    (is (= numeric (cap-names/wire-policy numeric)))))

(deftest wire-policy-touches-only-allow
  (let [policy {:allow #{[:cap/call :clock/now]}
                :abac {:policy-id :some/policy}
                :attributes {:subject {:id [:cap/call 3]}}}]
    (is (= {:allow #{[:cap/call 7]}
            :abac {:policy-id :some/policy}
            :attributes {:subject {:id [:cap/call 3]}}}
           (cap-names/wire-policy policy)))))

(deftest wire-policy-passes-a-policy-with-no-allow-key-through
  (is (= {} (cap-names/wire-policy {})))
  (is (= {:language-profile :pure-product}
         (cap-names/wire-policy {:language-profile :pure-product}))))

(deftest an-unregistered-name-is-refused-by-that-name
  ;; Closed-world, mirroring the frontend's rejection of an unregistered
  ;; `cap-call` keyword. Admitting it as an opaque grant would let a typo read
  ;; as a grant that is merely never used. Asserted on the MESSAGE, not merely
  ;; on something being thrown.
  (let [error (try (cap-names/wire-policy {:allow #{[:cap/call :hash/sha257]}})
                   (catch clojure.lang.ExceptionInfo e e))]
    (is (instance? clojure.lang.ExceptionInfo error))
    (is (= "policy names an unregistered capability: :hash/sha257"
           (ex-message error)))
    (is (= :admission (:phase (ex-data error))))
    (is (= :hash/sha257 (:capability (ex-data error))))))

;; ---------------------------------------------------------------------------
;; End to end through the CLI a person actually types.

(defn- check-json [source-path & args]
  (let [out (StringWriter.)]
    (binding [*out* out]
      (apply cli/-main "check" source-path "--json" args))
    (edn/read-string (str out))))

(deftest check-json-reports-names-not-wire-ids
  (let [source (temp-file! hash-guest ".kotoba")
        policy (temp-file! (pr-str {:allow #{[:cap/call 3]}}) ".edn")
        report (check-json source "--policy" policy)]
    (is (true? (:ok report)))
    (is (= #{[:cap/call :hash/sha256]} (:effects report)))
    (is (= #{:hash/sha256} (:named-operations report)))
    (is (= #{[:cap/call :hash/sha256]} (get-in report [:admission :required])))
    (is (= {:allow #{[:cap/call :hash/sha256]}}
           (get-in report [:admission :minimal-policy])))
    (testing "no wire id survives anywhere in the printed envelope"
      (is (not (re-find #":cap/call \d" (pr-str report)))))))

(deftest the-minimal-policy-check-prints-is-a-policy-check-accepts
  ;; The round trip is the whole point. Before this, `:minimal-policy` named a
  ;; file the caller could not write without a lookup table -- and under nbb it
  ;; printed `#object[BigInt 3]`, which is not readable EDN at all.
  (let [source (temp-file! hash-guest ".kotoba")
        opening (temp-file! (pr-str {:allow #{[:cap/call 3]}}) ".edn")
        printed (get-in (check-json source "--policy" opening) [:admission :minimal-policy])
        pasted (temp-file! (pr-str printed) ".edn")
        report (check-json source "--policy" pasted)]
    (is (= {:allow #{[:cap/call :hash/sha256]}} printed))
    (is (true? (:ok report)))
    (is (true? (get-in report [:admission :admitted?])))))

(deftest a-numeric-policy-file-is-still-accepted
  (let [source (temp-file! hash-guest ".kotoba")
        policy (temp-file! (pr-str {:allow #{[:cap/call 3]}}) ".edn")
        report (check-json source "--policy" policy)]
    (is (true? (get-in report [:admission :admitted?])))))

(deftest a-named-policy-that-omits-the-required-grant-is-still-denied
  ;; Naming grants must not widen what is admitted. `:clock/now` is a real
  ;; capability and a real grant; it is simply not the one this guest needs.
  ;;
  ;; The refusal is asserted on its whole message, which is also the assertion
  ;; that the denial -- the one sentence telling a caller what to put in
  ;; `--policy` -- no longer answers with a number they would have to look up.
  (let [source (temp-file! hash-guest ".kotoba")
        policy (temp-file! (pr-str {:allow #{[:cap/call :clock/now]}}) ".edn")
        status (atom nil)
        out (StringWriter.)]
    ;; `check --json` prints its error envelope on *out* (see the `json?`
    ;; branch of the "check" case in kotoba.compiler.cli).
    (binding [cli/*exit* #(reset! status %) *out* out]
      (cli/-main "check" source "--json" "--policy" policy))
    (let [report (edn/read-string (str out))]
      (is (= 65 @status))
      (is (= :admission (:error report)))
      (is (= (str "capability policy denies required effects"
                  "; missing grants #{[:cap/call :hash/sha256]}"
                  " (required #{[:cap/call :hash/sha256]}"
                  ", allowed #{[:cap/call :clock/now]})")
             (:message report))))))
