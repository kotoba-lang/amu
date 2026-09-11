(ns kotoba.compiler.recursive-tree-update-test
  "W4 sixth slice companion (ADR-2607279200 Delivery 4):

  Persistent update + structural equality on sealed recursive logical trees
  (complements recursive_tree_value_test construct/walk). Uses
  hetero-vector-assoc to replace a child without host handles, and a pure
  guest tree-eq walk for structural equality. KIR + restricted ESM parity."
  (:require [clojure.java.shell :as shell]
            [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]
            [kotoba.kir :as ir]))

(def node-t
  "[:variant :app/node [[:leaf :i64] [:branch [:vector [[:ref :app/node] [:ref :app/node]]]]]]")

(def pair-t
  "[:vector [[:ref :app/node] [:ref :app/node]]]")

(def source
  (str "(ns ui.recursive-update (:export [main sample-sum replaced-sum same diff])
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
   ;; Persistent update: replace the right child of the root with leaf 9.
   (defn replaced [] " node-t "
     (match-variant (sample) " node-t "
       (:leaf x (leaf x))
       (:branch pair
         (variant-new " node-t " :branch
           (hetero-vector-assoc " pair-t " pair 1 (leaf 9))))))
   (defn tree-eq [a " node-t " b " node-t "] :i64
     (match-variant a " node-t "
       (:leaf x
         (match-variant b " node-t "
           (:leaf y (if (= x y) 1 0))
           (:branch _ 0)))
       (:branch pa
         (match-variant b " node-t "
           (:leaf _ 0)
           (:branch pb
             (if (= (tree-eq (hetero-vector-at " pair-t " pa 0)
                             (hetero-vector-at " pair-t " pb 0)) 1)
               (tree-eq (hetero-vector-at " pair-t " pa 1)
                        (hetero-vector-at " pair-t " pb 1))
               0))))))
   (defn sample-sum [] :i64 (sum (sample)))
   (defn replaced-sum [] :i64 (sum (replaced)))
   (defn same [] :i64 (tree-eq (sample) (sample)))
   (defn diff [] :i64 (tree-eq (sample) (replaced)))
   (defn main [] :i64 (replaced-sum))"))

(defn- script-probe [compiled javascript]
  (let [encoded (.encodeToString (java.util.Base64/getEncoder)
                                 (.getBytes ^String (:source compiled) "UTF-8"))]
    (shell/sh "node" "--input-type=module" "-e"
              (str "import('data:text/javascript;base64," encoded
                   "').then(m=>{const x=m.instantiateKotoba({});" javascript
                   "}).catch(e=>{console.error(e);process.exit(70)})"))))

(deftest recursive-tree-persistent-update-and-equality
  (let [wasm (compiler/compile-source source :wasm32-kotoba-v1 {})
        script (compiler/compile-source source :js-kotoba-v1)
        kir (:kir wasm)]
    (testing "reference KIR: update + structural equality"
      ;; sample = 1+(2+3)=6; replaced right with 9 → 1+9=10
      (is (= 6 (ir/execute kir 'sample-sum [])))
      (is (= 10 (ir/execute kir 'replaced-sum [])))
      (is (= 10 (ir/execute kir 'main [])))
      (is (= 1 (ir/execute kir 'same [])))
      (is (= 0 (ir/execute kir 'diff []))))
    (testing "restricted ESM agrees"
      (let [probe (script-probe script
                                (str "if(x['sample-sum']()!==6n)process.exit(2);"
                                     "if(x['replaced-sum']()!==10n||x.main()!==10n)process.exit(3);"
                                     "if(x.same()!==1n)process.exit(4);"
                                     "if(x.diff()!==0n)process.exit(5);"
                                     "console.log('ok');"))]
        (is (zero? (:exit probe)) (str (:err probe) (:out probe)))
        (is (= "ok\n" (:out probe)))))))
