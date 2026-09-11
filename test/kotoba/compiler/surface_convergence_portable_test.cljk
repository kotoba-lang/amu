(ns kotoba.compiler.surface-convergence-portable-test
  "Two spellings of one meaning must mint one DefCID -- measured over the
  construct families that were NOT measured when the claim was accepted.

  Root ADR `adr-2609081400-a-grammar-is-a-surface-not-a-language` discharged
  surface convergence for three pairs (a beta redex, threading, cond) and
  stated the limit in the same breath: *destructuring, protocol dispatch,
  match and the document forms are unmeasured, and this ADR does not claim
  them*. It then named what would be needed before a third grammar is
  registered -- *a conformance corpus that pairs each of its constructs with
  a canonical-core spelling and asserts equal DefCIDs, with a negative
  control in it*. This namespace is four of those families.

  ## What a case is

  Each case is three sources: the SUGAR spelling, the CORE spelling that
  `lang/guest-grammar.edn` documents as the sugar's desugar target, and a
  CONTROL that changes the meaning. Convergence alone proves nothing -- a
  comparison that only ever reports agreement cannot be told from one that
  never ran -- so every case asserts both directions.

  ## The core spelling is the DOCUMENTED target, not an equivalent one

  Measured 2026-09-10 on amu fe9d394a. The first attempt at two of these
  cases reported DIVERGENCE, and the divergence was in the probe:

  | family | first core spelling | result |
  |---|---|---|
  | vector destructuring | `(let [v [1 2] a (nth v 0 0) b (nth v 1 0)] ...)` | DIFF |
  | match | `(if (= n 0) 10 20)` | DIFF |

  Both are *semantically* equivalent to their sugar and neither is what the
  grammar says the sugar becomes. `:nested-destructuring` desugars to
  \"sequential temp-bound pair/map lookups\" -- one temp, and `nth` without a
  default, where the first spelling supplied a default and so lowered a
  different call. `:match` desugars to \"SINGLE-EVALUATION nested let/if
  tests\" -- the scrutinee is let-bound once, which `(if (= n 0) ...)` skips.
  Writing the documented shape converged both, 2/2 definitions each.

  That is worth keeping in front of whoever extends this corpus: **a case
  that reports divergence is a claim about the probe until the core spelling
  is checked against `lang/guest-grammar.edn`.** Reported the other way round
  it would enter the record as a language defect that does not exist.

  ## What the control is allowed to leave alone

  `:protocol-impl-spelling`'s control changes a method body, so the record
  CONSTRUCTOR does not move -- correctly, since nothing about `->Box`
  changed. The assertion is therefore that the control moves at least one
  definition, not every one. A control asserted to move all of them would be
  false for the right reason, and would get \"fixed\" by weakening the case."
  (:require #?(:clj [clojure.test :refer [deftest is testing]]
               :cljs [cljs.test :refer [deftest is testing] :include-macros true])
            [kotoba.compiler.definition-identity :as di]
            [kotoba.kir :as ir]
            [kotoba.sema :as sema]))

(defn- cids
  "Definition name -> DefCID, through the same seam `amu definition-cids`
  uses. File-free, so this runs on nbb as well as the JVM."
  [source]
  (let [hir (sema/analyze source {})]
    (into {} (map (fn [[k v]] [k (:cid v)])) (:entries (di/definitions hir (ir/lower hir))))))

(def ^:private header "(ns d (:export [main]))\n")

(defn- module [& forms] (apply str header (interpose "\n" forms)))

(def ^:private cases
  [{:id :vector-destructuring
    :sugar-doc ":nested-destructuring -> sequential temp-bound pair/map lookups"
    :sugar   (module "(defn run [] (let [[a b] [1 2]] (+ a b)))"
                     "(defn main [] (run))")
    :core    (module "(defn run [] (let [t [1 2] a (nth t 0) b (nth t 1)] (+ a b)))"
                     "(defn main [] (run))")
    :control (module "(defn run [] (let [[a b] [2 2]] (+ a b)))"
                     "(defn main [] (run))")}

   {:id :map-keys-destructuring
    :sugar-doc ":nested-destructuring, map :keys with the :or the typed map requires"
    :sugar   (module "(defn run [] (let [{:keys [x y] :or {x 0 y 0}} (typed-map-new [:map :keyword :i64] :x 2 :y 3)] (+ x y)))"
                     "(defn main [] (run))")
    :core    (module "(defn run [] (let [m (typed-map-new [:map :keyword :i64] :x 2 :y 3) x (get m :x 0) y (get m :y 0)] (+ x y)))"
                     "(defn main [] (run))")
    :control (module "(defn run [] (let [{:keys [x y] :or {x 0 y 0}} (typed-map-new [:map :keyword :i64] :x 2 :y 4)] (+ x y)))"
                     "(defn main [] (run))")}

   {:id :match
    :sugar-doc ":match -> single-evaluation nested let/if tests"
    :sugar   (module "(defn run [n :i64] :i64 (match n 0 10 :else 20))"
                     "(defn main [] (run 0))")
    :core    (module "(defn run [n :i64] :i64 (let [t n] (if (= t 0) 10 20)))"
                     "(defn main [] (run 0))")
    :control (module "(defn run [n :i64] :i64 (match n 0 11 :else 20))"
                     "(defn main [] (run 0))")}

   {:id :protocol-impl-spelling
    :sugar-doc ":protocol-extension -- inline in defrecord and extend-type are both static additions to the closed protocol table"
    :sugar   (module "(defprotocol Value (value [this]))"
                     "(defrecord Box [x] Value (value [this] (get this :x)))"
                     "(defn main [] (value (->Box 7)))")
    :core    (module "(defprotocol Value (value [this]))"
                     "(defrecord Box [x])"
                     "(extend-type Box Value (value [this] (get this :x)))"
                     "(defn main [] (value (->Box 7)))")
    :control (module "(defprotocol Value (value [this]))"
                     "(defrecord Box [x] Value (value [this] (+ (get this :x) 1)))"
                     "(defn main [] (value (->Box 7)))")}])

(deftest two-spellings-of-one-meaning-mint-one-definition-cid
  ;; Evidence floor: a run that compiled nothing must not read as a clean run.
  (is (= 4 (count cases)) "the corpus is the four families the root ADR left unmeasured")
  (doseq [{:keys [id sugar core control sugar-doc]} cases]
    (testing (str id " -- " sugar-doc)
      (let [s (cids sugar)
            c (cids core)
            n (cids control)
            shared (sort (filter (set (keys c)) (keys s)))]
        (is (seq shared)
            (str id ": neither spelling produced a definition; nothing was compared"))
        (is (= (select-keys s shared) (select-keys c shared))
            (str id ": the sugar and its documented core spelling minted different DefCIDs. "
                 "Check the core spelling against lang/guest-grammar.edn BEFORE reading this "
                 "as a language defect -- see this namespace's docstring."))
        (is (some (fn [k] (not= (get s k) (get n k))) shared)
            (str id ": the control changed the meaning and no DefCID moved, so this case "
                 "cannot discriminate and its agreement half proves nothing"))
        (println (str "CONVERGED\t" (name id) "\t" (count shared)))))))
