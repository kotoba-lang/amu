(ns test.nbb.run
  "Repeatable, JVM-free regression test for the nbb-native wasm32
  compile/check path (`kotoba.compiler.nbb.cli`, spawned by `bin/kotoba` for
  `wasm32*` targets -- see its own comment). Every case must emit valid Wasm.
  Semantic, ABI, and rejection behavior is covered by the conformance suites;
  emitted bytes are deliberately not treated as the language contract.
  Run from the repo root: `nbb test/nbb/run.cljs`."
  (:require ["node:fs" :as fs]
            [kotoba.sema :as sema]
            [kotoba.kir.admission :as admission]
            [kotoba.kir :as ir]
            [kotoba.wasm.core :as wasm]
            [kotoba.compiler.capability-names :as cap-names]
            [kotoba.compiler.diagnostic :as diagnostic]
            [kotoba.compiler.backend.evm :as evm]
            [kotoba.compiler.packaging.elf-fixture :as elf-fixture]
            [kotoba.compiler.packaging.pe32plus :as pe32plus]
            [kotoba.compiler.kotoba-reader :as kr]
            [test.nbb.cases :as cases]))

(defn- compile-case [{:keys [source target policy]}]
  (let [src (.readFileSync fs source "utf8")
        hir (sema/analyze src)
        policy-value (if policy (first (kr/read-forms (.readFileSync fs policy "utf8"))) {})
        _ (admission/check hir policy-value)
        kir (ir/lower hir)]
    (wasm/emit kir (get cases/target-keyword target))))

(defn- diagnostic-case []
  (try
    (sema/analyze "(defn main []\n  (forbidden-call 1))")
    {:name "structured-diagnostic" :ok? false :detail "unsafe source was admitted"}
    (catch :default error
      (let [value (diagnostic/from-error error "program.cljk")
            span (:span value)
            ;; T3.1 (compiler#422 / ADR 0172): reject! sites carry stable
            ;; :kotoba.error/* codes, default :subset-reject. The JVM twin
            ;; (cli_test/structured-diagnostic-has-stable-code-and-bounded-source-span)
            ;; was updated then; this one was not, and main has been red since.
            ok? (and (= :kotoba.error/subset-reject (:code value))
                     (= "program.cljk" (:source value))
                     (= 2 (:line span)) (= 3 (:column span)))]
        {:name "structured-diagnostic" :ok? ok?
         :detail (when-not ok? (pr-str value))}))))

(defn- named-operation-case []
  (try
    (let [hir (sema/analyze
               "(ns demo (:capabilities #{:http/post}))
                (defn main [] :i64 (http/post 41))")
          body (get-in hir [:functions 0 :body])
          effect-id (second (first (:effects hir)))
          ok? (and (= 'typed-cap-call (first body))
                   (= 4 (js/Number (second body)))
                   (= :i64 (nth body 2))
                   (= :i64 (nth body 3))
                   (= 4 (js/Number effect-id)))]
      {:name "named-operation-elaboration" :ok? ok?
       :detail (when-not ok? (pr-str {:body body :effects (:effects hir)}))})
    (catch :default error
      {:name "named-operation-elaboration" :ok? false
       :detail (str "threw: " (.-message error))})))

(def ^:private evm-source
  "(ns evm.big)\n(defn main [] (+ 1234605616436508552 1))")

;; The bytes and digest the JVM emits for `evm-source`, measured 2026-08-25.
;; Pinned rather than recomputed, because a parity case that computes both
;; sides with the same code proves only that the code is deterministic.
(def ^:private evm-jvm-creation-sha256
  "8af8c288de346d0ad1f404c2bb344038dd69ba193619f33310225c2a923c2bbc")

(def ^:private evm-jvm-push8-operand
  [0x11 0x22 0x33 0x44 0x55 0x66 0x77 0x88])

(defn- capability-name-cases
  "`kotoba.compiler.capability-names` on THIS runtime.

  The JVM twin (kotoba.compiler.capability-names-test) asserts the same values,
  and would not have caught the one failure mode that only exists here: under
  nbb a policy read through `kotoba.compiler.kotoba-reader` carries its integer
  literals as BigInt, and so does the effect row
  (`kotoba.compiler.frontend/effect-capability-id`). `kotoba.kir.admission`
  decides by `set/difference`, and `[:cap/call 3]` with a plain number is not
  equal to `[:cap/call 3n]`. Measured 2026-09-01: writing the id as a plain
  number made every NAMED policy read as denying the very effect it granted.

  These are hand-rolled rather than `clojure.test` because this harness reports
  `{:name :ok? :detail}` maps; the duplication with the JVM namespace is the
  price of running the same claim on both runtimes."
  []
  (let [hir (sema/analyze
             "(ns demo (:export [main]))\n(defn main [] :string (hash/sha256 \"x\"))\n")
        named-policy (first (kr/read-forms "{:allow #{[:cap/call :hash/sha256]}}"))
        numeric-policy (first (kr/read-forms "{:allow #{[:cap/call 3]}}"))
        wired (cap-names/wire-policy named-policy)
        reported (cap-names/name-grants (:effects hir))
        admitted (try {:value (admission/check hir wired)}
                      (catch :default e {:error (.-message e)}))
        numeric-unchanged? (= numeric-policy (cap-names/wire-policy numeric-policy))
        unregistered (try (cap-names/wire-policy
                           (first (kr/read-forms "{:allow #{[:cap/call :hash/sha257]}}")))
                          {:message nil}
                          (catch :default e {:message (.-message e)}))]
    [{:name "capability-names-reports-the-catalog-name"
      :ok? (= #{[:cap/call :hash/sha256]} reported)
      :detail (when-not (= #{[:cap/call :hash/sha256]} reported) (pr-str reported))}
     {:name "capability-names-admits-a-named-policy-on-this-runtime"
      ;; The claim that fails when the id is not a BigInt here.
      :ok? (true? (get-in admitted [:value :admitted?]))
      :detail (when-not (true? (get-in admitted [:value :admitted?]))
                (pr-str admitted))}
     {:name "capability-names-leaves-a-numeric-policy-unchanged"
      :ok? numeric-unchanged?
      :detail (when-not numeric-unchanged?
                (pr-str {:before numeric-policy
                         :after (cap-names/wire-policy numeric-policy)}))}
     {:name "capability-names-refuses-an-unregistered-name-by-that-name"
      :ok? (= "policy names an unregistered capability: :hash/sha257"
              (:message unregistered))
      :detail (when-not (= "policy names an unregistered capability: :hash/sha257"
                           (:message unregistered))
                (pr-str unregistered))}]))

(defn- evm-case
  "`kotoba.compiler.backend.evm` on the second runtime, against the JVM's bytes.

  This backend is `.cljc`, so it claims both runtimes, and until 2026-08-25 the
  claim was false: `Long/MIN_VALUE` in a `:clj`-only form meant the namespace
  did not load here at all. Fixing the load surfaced two more, and neither
  would have failed loudly -- `integer?` does not recognise a bigint, and cljs
  bitwise shifts wrap at 32, so the PUSH8 operand came out as the low four
  bytes twice. The second of those was a bug in `kotoba.kir.cljs-i64/ashr`
  itself, which had one caller (`sleb128`, which shifts by 7) and so had never
  been asked for a shift of 32 or more.

  The literal is 0x1122334455667788 for that reason: all eight bytes differ, so
  a wrapped shift shows up instead of being coincidentally right. Every case in
  the JVM's own `backend-evm-test` uses values below 256, where every one of
  these three defects is invisible."
  []
  (try
    (let [artifact (evm/emit (ir/lower (sema/analyze evm-source)))
          runtime (:runtime-bytes artifact)
          push8 (vec (take 8 (drop (inc (.indexOf (to-array runtime) 0x67)) runtime)))
          ok? (and (= evm-jvm-creation-sha256 (:creation-sha256 artifact))
                   (= evm-jvm-push8-operand push8))]
      {:name "evm-matches-jvm-bytes" :ok? ok?
       :detail (when-not ok?
                 (pr-str {:creation-sha256 (:creation-sha256 artifact)
                          :push8 push8}))})
    (catch :default error
      {:name "evm-matches-jvm-bytes" :ok? false
       :detail (str "threw: " (.-message error))})))

(defn- pe32plus-admission-case
  "`package-embedded-kernel` refusing a kernel it must refuse, on THIS runtime.

  The JVM has always refused it. Until 2026-08-25 nbb accepted it and emitted a
  26 KB boot image, because `read-le` accumulated with `bit-shift-left` and
  cljs takes shift counts mod 32 -- the high bytes of every 64-bit ELF field
  landed in the low bits. See `kotoba.compiler.packaging.elf-fixture`.

  The assertion is on the VALUE the packager read, not merely on the refusal.
  The first version of the fixture was refused here even with the wrong value,
  because that particular misreading happened not to be page-aligned; a
  negative case that passes for a reason other than the one it names would
  have recorded that as a pass."
  []
  (try
    (pe32plus/package-embedded-kernel (elf-fixture/kernel-with-out-of-range-paddr))
    {:name "pe32plus-refuses-an-out-of-range-paddr" :ok? false
     :detail "a kernel outside the PT_LOAD contract was packaged"}
    (catch :default error
      (let [read-back (:paddr (first (:segments (ex-data error))))
            ok? (= elf-fixture/paddr-above-the-bound read-back)]
        {:name "pe32plus-refuses-an-out-of-range-paddr" :ok? ok?
         :detail (when-not ok?
                   (if (= elf-fixture/paddr-as-misread-by-a-wrapped-shift read-back)
                     "refused, but read the shift-wrapped paddr"
                     (pr-str {:paddr read-back :message (.-message error)})))}))))

(let [results
      (conj
       (vec
        (for [{:keys [name] :as case} cases/cases]
          (try
            (let [actual (compile-case case)
                  ok? (js/WebAssembly.validate actual)]
              {:name name :ok? ok?
               :detail (when-not ok? "emitted invalid Wasm")})
            (catch :default e
              {:name name :ok? false :detail (str "threw: " (.-message e))}))))
       (diagnostic-case)
       (named-operation-case)
       (evm-case)
       (pe32plus-admission-case))
      results (into results (capability-name-cases))
      failures (remove :ok? results)]
  (doseq [{:keys [name ok? detail]} results]
    (println (if ok? "PASS" "FAIL") name (or detail "")))
  (println (count results) "cases," (count failures) "failed")
  (when (seq failures) (.exit js/process 1)))
