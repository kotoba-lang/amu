(ns kotoba.compiler.document-ui-render-test
  "W4 first slice (ADR-2607279200 Delivery 4 / migration plan W4):

  A logical UI tree is an ordinary `:document` value (not a host object, not a
  string-only call graph). It can be:

  - inspected as data (document-get / document-vector-at / document-kind)
  - rendered to an HTML *stream* (string) by pure guest recursion
  - compared with document-equal?
  - rejected when node/depth budgets are exceeded at construction

  Handles are not the application model: the guest builds and walks the
  document tree with the existing document-* operations. Full DOM
  reconciliation remains a follow-up; document-sha256 is first-class
  (document_sha256_test). This slice locks the data→HTML half of the W4 exit
  gate that design-system form-A (string-only call graphs) could not express."
  (:require [clojure.java.shell :as shell]
            [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]
            [kotoba.kir :as ir]
            [kotoba.kir.value :as value]))

(def render-source
  "(ns ui.document-render (:export [main same different depth-ok]))
   (defn tag-of [d :document] :string
     (option-value-of [:option :string]
       (document-string-value
         (option-value-of [:option :document]
           (document-get d :tag) (document-null)))
       \"div\"))
   (defn text-of [d :document] :string
     (option-value-of [:option :string]
       (document-string-value
         (option-value-of [:option :document]
           (document-get d :text) (document-null)))
       \"\"))
   (defn kids-of [d :document] :document
     (option-value-of [:option :document]
       (document-get d :children) (document-vector)))
   (defn render-kids [kids :document i :i64 n :i64 acc :string] :string
     (if (>= i n)
       acc
       (render-kids kids (+ i 1) n
         (string-concat acc
           (render (option-value-of [:option :document]
                     (document-vector-at kids i) (document-null)))))))
   (defn render [d :document] :string
     (if (string=? (text-of d) \"\")
       (string-concat \"<\"
         (string-concat (tag-of d)
           (string-concat \">\"
             (string-concat (render-kids (kids-of d) 0 (document-count (kids-of d)) \"\")
               (string-concat \"</\" (string-concat (tag-of d) \">\"))))))
       (string-concat \"<\"
         (string-concat (tag-of d)
           (string-concat \">\"
             (string-concat (text-of d)
               (string-concat \"</\" (string-concat (tag-of d) \">\"))))))))
   (defn leaf [tag :string text :string] :document
     (document-map :tag (document-string tag) :text (document-string text)))
   (defn node [tag :string children :document] :document
     (document-map :tag (document-string tag) :children children))
   (defn page [] :document
     (node \"div\"
       (document-vector
         (leaf \"h1\" \"Hello\")
         (leaf \"p\" \"World\"))))
   (defn main [] :string (render (page)))
   (defn same [] :bool (document-equal? (page) (page)))
   (defn different [] :bool
     (document-equal? (page)
       (node \"div\"
         (document-vector
           (leaf \"h1\" \"Hello\")
           (leaf \"p\" \"Other\")))))
   (defn depth-ok [] :i64 (document-count (page)))")

(defn- script-probe [compiled javascript]
  (let [encoded (.encodeToString (java.util.Base64/getEncoder)
                                 (.getBytes ^String (:source compiled) "UTF-8"))]
    (shell/sh "node" "--input-type=module" "-e"
              (str "import('data:text/javascript;base64," encoded
                   "').then(m=>{const x=m.instantiateKotoba({});" javascript
                   "}).catch(e=>{console.error(e);process.exit(70)})"))))

(deftest logical-ui-document-renders-to-html-stream
  (let [wasm (compiler/compile-source render-source :wasm32-kotoba-v1 {})
        script (compiler/compile-source render-source :js-kotoba-v1 {})
        kir (:kir wasm)
        html "<div><h1>Hello</h1><p>World</p></div>"]
    (testing "reference KIR renders the logical tree to an HTML string"
      (is (= html (ir/execute kir 'main [])))
      (is (true? (ir/execute kir 'same [])))
      (is (false? (ir/execute kir 'different [])))
      (is (= 2 (ir/execute kir 'depth-ok []))))
    (testing "restricted ESM agrees with the KIR interpreter"
      (let [probe (script-probe script
                                (str "const html=" (pr-str html) ";"
                                     "if(x.main()!==html)process.exit(2);"
                                     "const s=x.same(); const d=x.different();"
                                     "if(!(s===1n||s===true||s===1))process.exit(3);"
                                     "if(!(d===0n||d===false||d===0))process.exit(4);"))]
        (is (zero? (:exit probe)) (str (:err probe) "\n" (:out probe)))))))

(defn- canon-map [entries]
  ["map" (vec (sort-by (comp str first) entries))])

(deftest document-budgets-reject-unbounded-ui-trees
  (testing "depth budget (document-depth-limit 8) fails closed"
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"depth limit"
          (value/bounded-document!
           (reduce (fn [item _] (canon-map [[:child item]]))
                   ["string" "leaf"]
                   (range 9))))))
  (testing "container item budget fails closed"
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"invalid document vector|item limit"
          (value/bounded-document!
           ["vector" (vec (repeat 33 ["string" "x"]))]))))
  (testing "a small UI tree is admitted and equal to itself after revalidation"
    (let [tree (canon-map
                [[:tag ["string" "div"]]
                 [:children
                  ["vector"
                   [(canon-map [[:tag ["string" "h1"]] [:text ["string" "Hello"]]])
                    (canon-map [[:tag ["string" "p"]] [:text ["string" "World"]]])]]]])]
      (is (= (value/bounded-document! tree)
             (value/bounded-document! tree))))))
