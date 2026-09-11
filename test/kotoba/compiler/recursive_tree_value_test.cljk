(ns kotoba.compiler.recursive-tree-value-test
  "W4 fifth slice (ADR-2607279200 Delivery 4 / migration plan W4):

  Recursive logical values as ordinary schema-checked values — not only
  open `:document` maps. A sealed `:app/node` variant (leaf i64 | branch
  of two [:ref :app/node]) is constructed and walked with variant-new /
  match-variant / hetero-vector under ADT depth/node budgets. Handles are
  not the application model: the guest holds the full tagged tree; [:ref R]
  is a type-level alias resolved against the nominal descriptor carried by
  the value (kotoba-kir + kotoba-script).

  Complements the open `:document` path (slices 1–4) with a closed recursive
  schema path that design-system cutover can target once dual renderers
  qualify."
  (:require [clojure.java.shell :as shell]
            [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]
            [kotoba.kir :as ir]
            [kotoba.kir.value :as value]))

(def node-t
  "[:variant :app/node [[:leaf :i64] [:branch [:vector [[:ref :app/node] [:ref :app/node]]]]]]")

(def pair-t
  "[:vector [[:ref :app/node] [:ref :app/node]]]")

(def source
  (str "(ns ui.recursive-tree (:export [main left-sum right-sum sample-sum])
     (:schemas {:app/node " node-t "}))
   (defn leaf [n :i64] " node-t "
     (variant-new " node-t " :leaf n))
   (defn branch [l " node-t " r " node-t "] " node-t "
     (variant-new " node-t " :branch (hetero-vector " pair-t " l r)))
   (defn sum [n " node-t "] :i64
     (match-variant n " node-t "
       (:leaf x x)
       (:branch pair (+ (sum (hetero-vector-at " pair-t " pair 0))
                        (sum (hetero-vector-at " pair-t " pair 1))))))
   (defn sample [] " node-t "
     (branch (leaf 1) (branch (leaf 2) (leaf 3))))
   (defn main [] :i64 (sum (sample)))
   (defn sample-sum [] :i64 (sum (sample)))
   (defn left-sum [] :i64 (sum (branch (leaf 1) (leaf 2))))
   (defn right-sum [] :i64 (sum (branch (leaf 4) (leaf 5))))"))
(defn- script-probe [compiled javascript]
  (let [encoded (.encodeToString (java.util.Base64/getEncoder)
                                 (.getBytes ^String (:source compiled) "UTF-8"))]
    (shell/sh "node" "--input-type=module" "-e"
              (str "import('data:text/javascript;base64," encoded
                   "').then(m=>{const x=m.instantiateKotoba({});" javascript
                   "}).catch(e=>{console.error(e);process.exit(70)})"))))

(deftest recursive-tree-values-construct-and-walk
  (let [wasm (compiler/compile-source source :wasm32-kotoba-v1 {})
        script (compiler/compile-source source :js-kotoba-v1)
        kir (:kir wasm)]
    (testing "reference KIR walks a recursive nominal tree"
      (is (= 6 (ir/execute kir 'main [])))
      (is (= 6 (ir/execute kir 'sample-sum [])))
      (is (= 3 (ir/execute kir 'left-sum [])))
      (is (= 9 (ir/execute kir 'right-sum [])))
      (is (some? (get-in kir [:schema-identities :app/node]))))
    (testing "restricted ESM agrees"
      (let [probe (script-probe script
                                (str "if(x.main()!==6n)process.exit(2);"
                                     "if(x['sample-sum']()!==6n)process.exit(3);"
                                     "if(x['left-sum']()!==3n||x['right-sum']()!==9n)process.exit(4);"
                                     "console.log('ok');"))]
        (is (zero? (:exit probe)) (str (:err probe) (:out probe)))
        (is (= "ok\n" (:out probe)))))
    (testing "schema-ref value admission rejects wrong nominal root"
      (let [other [:variant :other/node [[:leaf :i64]]]
            value (value/bounded-typed-value! other [other :leaf 1])]
        (is (thrown-with-msg? clojure.lang.ExceptionInfo #"schema ref"
                              (value/bounded-typed-value! [:ref :app/node] value)))))))
