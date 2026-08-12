(ns kotoba.compiler.lang-conformance-cljs-parity-test
  "Runs each pure-product conformance case on BOTH the KIR oracle and a real
  ClojureScript host, and compares the two results to each other.

  The suite already compared KIR against wasm32. Nothing compared cljs against
  anything: `:kotoba-cljs` is asserted by 19 entries in the language authority's
  surface-status and was entailed by no executed case, because every linked
  case declares `:required-backends #{:kir :wasm32-kotoba-v1}`. Measured
  2026-08-12.

  Parity here means the two backends agree with each other, not merely that
  each agrees with a recorded literal. Those differ: a literal both backends
  reproduce wrongly is still agreement with the literal."
  (:require [clojure.set :as set]
            [clojure.string :as str]
            [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.lang-conformance :as lc]))

;; Cases `:cljs-kotoba-v1` declines to compile, measured 2026-08-12. A refusal
;; is a statement about the backend, not the case: typed values are admitted on
;; this target only where `only-cljs-implemented-typed-features?` holds.
;;
;; This is a ratchet. A case that starts compiling must leave the list, and a
;; case that stops compiling must be added deliberately -- either direction
;; fails, so the set tracks the backend instead of drifting behind it.
(def cljs-refused
  '#{:string-contains-kit :string-fold-case-kit :string-replace-kit :if-some-kit
     :typed-map-kit :string-split-count-kit :typed-map-dissoc-kit :when-ext-kit
     :if-some-string-kit :option-result-kit :type-directed-heterogeneous-nth
     :nested-typed-destructuring :nested-let-destructuring :wide-nominal-records
     ;; Added after the first full run. The initial fourteen were seeded from a
     ;; truncated probe -- the count said eighteen and the names said fourteen,
     ;; and only running it reconciled them. Seeding a register from a summary
     ;; line is how a register starts lying.
     :record-kit :typed-defrecord-fields :composed-surface-kit
     :record-protocol-static-dispatch})

;; Cases the cljs backend ACCEPTS and then cannot run: the emitted source calls
;; runtime helpers it never defines, so nbb fails with "Unable to resolve
;; symbol". Measured 2026-08-12, first full run of this harness.
;;
;; These are defects, not coverage statements, and the distinction matters:
;; `cljs-refused` records a backend declining work it does not claim, while
;; this records a backend claiming work it cannot do. The list may only
;; shrink. Do not add to it to make a run green -- a new entry here means a
;; case that used to execute on cljs no longer does.
;;
;; The unresolved symbols observed across these five, NOT attributed per case:
;;   i64-shift-left  i64-shift-right  u64-shift-right  string-code-point-at
;;
;; The first version of this list also carried :thread-kit, mapped there by
;; counting symbol occurrences in a log rather than by which case produced
;; them. :thread-kit runs. The two-way check is what caught it -- a register
;; that only grew would have kept a working case marked broken indefinitely,
;; which is the same defect as marking a broken one working.
;; :thread-kit is NOT registered anywhere, deliberately, and this comment is
;; why. It compiles to cljs, runs to completion, and returns 336 where KIR
;; returns 36 -- the manifest's expect. A wrong answer, silently.
;;
;; It was briefly listed as unrunnable because the first pass mapped log
;; symbols to cases by counting rather than by reading; removing it from that
;; list is what let the comparison reach it.
;;
;; It is not registered because a register normalises what it holds.
;; `cljs-refused` says a backend declines work it does not claim;
;; `cljs-emitted-but-unrunnable` says a backend claims work it cannot do; both
;; are statements about coverage. A backend that claims work, does it, and
;; returns the wrong number is a correctness defect, and a suite that goes
;; green over it teaches the next reader that 336 is acceptable.
;;
;; So this test stays red until the backend is fixed or an owner decides
;; otherwise. The redness is the finding. The old suite compared KIR against
;; wasm32 and each against a literal, which is why this was invisible: nothing
;; ever compared cljs to anything.
(def cljs-emitted-but-unrunnable
  '#{:shift-kit :shift-right-kit :when-let-u64-kit :loop-deep-kit
     :string-code-point-kit})

(defn- pure-cases []
  (->> (lc/load-manifest) :cases (filter #(= :pure-product-run (:class %)))))

(defn- outcomes []
  (for [{:keys [id entry function args] :as case} (pure-cases)
        :let [source (#'lc/resolve-source entry)]]
    (let [cljs (lc/run-cljs source function args)]
      (if (:refused cljs)
        {:id id :refused true}
        {:id id
         :cljs cljs
         :kir (lc/run-kir source function args case)
         :expect (get-in case [:expect :kotoba])}))))

;; Both deftests need the same 60 compiles, 42 nbb processes and 42 KIR runs.
;; Computed once: running it per-deftest doubled the suite's wall clock for no
;; additional coverage.
(def ^:private outcomes* (delay (outcomes)))

(deftest cljs-emitted-but-unrunnable-is-exactly-the-recorded-set
  (let [broken (into #{} (keep (fn [{:keys [id refused cljs]}]
                                 (when (and (not refused) (not (:ok? cljs))) id)))
                     @outcomes*)]
    (is (empty? (set/difference broken cljs-emitted-but-unrunnable))
        (str "newly unrunnable on cljs: " (set/difference broken cljs-emitted-but-unrunnable)))
    (is (empty? (set/difference cljs-emitted-but-unrunnable broken))
        (str "now runnable, remove from the register: "
             (set/difference cljs-emitted-but-unrunnable broken)))))

(deftest cljs-refusals-are-exactly-the-recorded-set
  (let [results @outcomes*
        refused (into #{} (keep #(when (:refused %) (:id %))) results)]
    (is (seq results) "no pure-product cases were read")
    (is (empty? (set/difference refused cljs-refused))
        (str "newly refused by cljs: " (set/difference refused cljs-refused)))
    (is (empty? (set/difference cljs-refused refused))
        (str "no longer refused, remove from the register: "
             (set/difference cljs-refused refused)))))

(deftest cljs-and-kir-agree-on-every-case-cljs-accepts
  (doseq [{:keys [id refused cljs kir expect]} @outcomes*
          :when (and (not refused)
                     (not (contains? cljs-emitted-but-unrunnable id)))]
    (testing (name id)
      (is (:ok? cljs) (pr-str cljs))
      (is (:ok? kir) (pr-str kir))
      ;; The parity assertion proper: the two backends against each other.
      (is (= (:result kir) (:result cljs)))
      ;; And against the manifest, so a shared wrong answer is still caught.
      (is (= expect (:result cljs))))))
