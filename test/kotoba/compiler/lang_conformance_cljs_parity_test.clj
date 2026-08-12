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
     :nested-typed-destructuring :nested-let-destructuring :wide-nominal-records})

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
          :when (not refused)]
    (testing (name id)
      (is (:ok? cljs) (pr-str cljs))
      (is (:ok? kir) (pr-str kir))
      ;; The parity assertion proper: the two backends against each other.
      (is (= (:result kir) (:result cljs)))
      ;; And against the manifest, so a shared wrong answer is still caught.
      (is (= expect (:result cljs))))))
