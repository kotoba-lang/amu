(ns kotoba.compiler.record-projection-sugar-test
  "`(record-get value :field)` — the schema is recovered from the value's
  inferred type and rewritten to the canonical 3-arity form before validation,
  so lowering and the backends are untouched."
  (:require [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]
            [kotoba.kir :as ir]))

(def ^:private S
  "[:record :r/lanes [[:text :i64] [:media :i64] [:postproc :i64]]]")

(defn- run [src fn-sym args]
  (let [c (compiler/compile-source src :wasm32-kotoba-v1 {}
                                   {:language-profile :pure-product})]
    (ir/execute (:kir c) fn-sym (vec args) {})))

(defn- rejection [src]
  (try
    (compiler/compile-source src :wasm32-kotoba-v1 {}
                             {:language-profile :pure-product})
    nil
    (catch clojure.lang.ExceptionInfo e
      {:code (:kotoba.error/code (ex-data e)) :message (.getMessage e)})))

(deftest projects-a-let-bound-record
  (is (= 5 (run (str "(ns p)\n(defn go [t :i64 m :i64 p :i64] :i64\n"
                     "  (let [r (record-new " S " t m p)] (record-get r :media)))\n"
                     "(defn main [] :i64 0)")
                'go [4 5 6]))))

(deftest projects-a-record-parameter
  (is (= 6 (run (str "(ns p)\n(defn pick [r " S "] :i64 (record-get r :postproc))\n"
                     "(defn go [t :i64 m :i64 p :i64] :i64 (pick (record-new " S " t m p)))\n"
                     "(defn main [] :i64 0)")
                'go [4 5 6]))))

(deftest projects-a-call-result-directly
  (is (= 4 (run (str "(ns p)\n(defn mk [t :i64 m :i64 p :i64] " S " (record-new " S " t m p))\n"
                     "(defn go [t :i64 m :i64 p :i64] :i64 (record-get (mk t m p) :text))\n"
                     "(defn main [] :i64 0)")
                'go [4 5 6]))))

(deftest projects-repeatedly-inside-an-expression
  (is (= 15 (run (str "(ns p)\n(defn go [t :i64 m :i64 p :i64] :i64\n"
                      "  (let [r (record-new " S " t m p)]\n"
                      "    (+ (record-get r :text)\n"
                      "       (+ (record-get r :media) (record-get r :postproc)))))\n"
                      "(defn main [] :i64 0)")
                 'go [4 5 6]))))

(deftest three-arity-is-unchanged
  (testing "the canonical form still compiles and still means the same thing"
    (is (= 5 (run (str "(ns p)\n(defn go [t :i64 m :i64 p :i64] :i64\n"
                       "  (record-get " S " (record-new " S " t m p) :media))\n"
                       "(defn main [] :i64 0)")
                  'go [4 5 6])))))

(deftest fails-closed-on-a-non-record-value
  (let [r (rejection "(ns p)\n(defn go [x :i64] :i64 (record-get x :text))\n(defn main [] :i64 0)")]
    (is (= :kotoba.error/record-projection-unresolved (:code r)))
    (is (re-find #"requires a record value" (:message r)))))

(deftest fails-closed-on-a-wrong-arity
  (let [r (rejection "(ns p)\n(defn go [x :i64] :i64 (record-get x))\n(defn main [] :i64 0)")]
    (is (re-find #"record-get requires" (:message r)))))

(deftest fails-closed-on-an-undeclared-field
  (testing "the rewrite supplies the schema; field validation is unchanged"
    (let [r (rejection (str "(ns p)\n(defn go [t :i64 m :i64 p :i64] :i64\n"
                            "  (let [r (record-new " S " t m p)] (record-get r :nope)))\n"
                            "(defn main [] :i64 0)"))]
      (is (some? r))
      (is (re-find #"declared keyword literal" (:message r))))))

(deftest projects-inside-a-let-binding-value
  (testing "regression: elaborate-named-abilities infers each let-bound value's
            type, so the rewrite must run before it. When it ran after, a
            2-arity record-get in a *binding* position reached elaboration and
            crashed on (nth type 2) with the value symbol in the type slot.
            The body-position cases above did not cover this."
    (is (= 9 (run (str "(ns p)\n(defn go [t :i64 m :i64 p :i64] :i64\n"
                       "  (let [r (record-new " S " t m p)\n"
                       "        a (record-get r :text)\n"
                       "        b (record-get r :media)]\n"
                       "    (+ a b)))\n"
                       "(defn main [] :i64 0)")
                  'go [4 5 6])))))

(deftest projects-a-record-parameter-inside-a-let-binding-value
  (testing "the shape murakumo's infer_schedule_core/eligible? actually uses"
    (is (= 1 (run (str "(ns p)\n"
                       "(defn ok? [e " S " free :i64 minf :i64] :i64\n"
                       "  (let [t (record-get e :text)\n"
                       "        m (record-get e :media)]\n"
                       "    (if (= t 0) 0 (if (< free minf) 0 m))))\n"
                       "(defn main [] :i64 0)")
                  'ok? [[[:record :r/lanes [[:text :i64] [:media :i64] [:postproc :i64]]] 1 1 0] 10 5])))))

;; --- named schema references ------------------------------------------------
;;
;; A record threaded through many signatures should not need its descriptor
;; repeated at every site. `[:ref :ns/name]` + the namespace `:schemas` map is
;; the existing mechanism; these lock in that the record operations resolve it.

(def ^:private REF-SRC-PREFIX
  (str "(ns p (:schemas {:m/model [:record :m/model "
       "[[:layers :i64] [:dense :i64] [:frac :i64]]]}))\n"))

(deftest resolves-a-schema-ref-in-a-parameter-annotation
  (is (= 12 (run (str REF-SRC-PREFIX
                      "(defn f [r [:ref :m/model]] :i64 (record-get r :layers))\n"
                      "(defn g [a :i64 b :i64 c :i64] :i64 (f (record-new [:ref :m/model] a b c)))\n"
                      "(defn main [] :i64 0)")
                 'g [12 0 100]))))

(deftest resolves-a-schema-ref-in-a-return-annotation
  (is (= 7 (run (str REF-SRC-PREFIX
                     "(defn mk [a :i64 b :i64 c :i64] [:ref :m/model] (record-new [:ref :m/model] a b c))\n"
                     "(defn f [r [:ref :m/model]] :i64 (record-get r :dense))\n"
                     "(defn g [a :i64 b :i64 c :i64] :i64 (f (mk a b c)))\n"
                     "(defn main [] :i64 0)")
                'g [12 7 100]))))

(deftest resolves-a-schema-ref-in-record-op-type-arguments
  (testing "record-new / 3-arity record-get accept [:ref :ns/name]"
    (is (= 100 (run (str REF-SRC-PREFIX
                         "(defn g [a :i64 b :i64 c :i64] :i64\n"
                         "  (record-get [:ref :m/model] (record-new [:ref :m/model] a b c) :frac))\n"
                         "(defn main [] :i64 0)")
                    'g [12 0 100])))))

(deftest fails-closed-on-an-undeclared-schema-ref
  (let [r (rejection (str "(ns p)\n"
                          "(defn g [a :i64] :i64 (record-get [:ref :m/nope] a :x))\n"
                          "(defn main [] :i64 0)"))]
    (is (= :kotoba.error/record-projection-unresolved (:code r)))
    (is (re-find #"no :record schema declared for" (:message r)))))

(deftest schema-refs-resolve-in-a-parameterless-body
  ;; `rewrite-record-projections` used to skip a body whose `:param-types` was
  ;; empty, on the reading that a function with no parameters has no locals to
  ;; resolve against. True for the 2-arity `record-get` sugar; false for a
  ;; `[:ref :ns/name]` in `record-new`, which resolves through the namespace's
  ;; `:schemas` map and not through locals.
  ;;
  ;; The two programs below differ only by an unused parameter, and only the
  ;; second compiled -- which is the shape of a bug, not a rule.
  (let [s "(ns p (:export [f]) (:schemas {:p/n [:record :p/n [[:a :i64] [:b :i64]]]}))\n"]
    (is (= 5 (run (str s "(defn f [] :i64 (record-get (record-new [:ref :p/n] 1 5) :b))")
                  'f [])))
    (is (= 5 (run (str s "(defn f [x :i64] :i64 (record-get (record-new [:ref :p/n] x 5) :b))")
                  'f [1])))))
