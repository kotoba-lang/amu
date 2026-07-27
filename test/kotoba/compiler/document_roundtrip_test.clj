(ns kotoba.compiler.document-roundtrip-test
  "W4 seventh slice (ADR-2607279200 Delivery 4 / migration plan W4):

  Reader/printer round-trip for recursive logical document values.

  `document-print` emits the deterministic lowercase-hex form of
  `document-canonical-bytes` (same encoding as `document-sha256`);
  `document-read` is the inverse and re-applies depth/node/item/byte budgets.
  A logical UI tree can therefore be inspected as data, printed, re-read, and
  remain structurally equal with a stable sha256 — without host objects or
  handles as the application model.

  Complements slices 1–6 (HTML stream, digest/style, sha256, DOM reconcile,
  sealed recursive ADTs, dual-renderer + persistent update)."
  (:require [clojure.java.shell :as shell]
            [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]
            [kotoba.kir :as ir]
            [kotoba.kir.value :as value]))

(def source
  "(ns ui.document-roundtrip (:export [main same dig-same dig-print empty-ok leaves-ok page bad]))
   (defn leaf [tag :string text :string] :document
     (document-map :tag (document-string tag) :text (document-string text)))
   (defn node [tag :string children :document] :document
     (document-map :tag (document-string tag) :children children))
   (defn page [] :document
     (node \"div\"
       (document-vector
         (leaf \"h1\" \"Hello\")
         (leaf \"p\" \"World\"))))
   (defn round [d :document] :document
     (document-read (document-print d)))
   (defn main [] :bool (document-equal? (page) (round (page))))
   (defn same [] :bool (document-equal? (page) (round (page))))
   (defn dig-same [] :i64
     (if (string=? (document-sha256 (page)) (document-sha256 (round (page)))) 1 0))
   (defn dig-print [] :string (document-print (page)))
   (defn empty-ok [] :bool
     (document-equal? (document-null) (document-read (document-print (document-null)))))
   (defn leaves-ok [] :bool
     (document-equal?
       (document-vector
         (document-bool true)
         (document-i64 -7)
         (document-string \"x\")
         (document-keyword :k))
       (round
         (document-vector
           (document-bool true)
           (document-i64 -7)
           (document-string \"x\")
           (document-keyword :k)))))
   (defn bad [] :document (document-read \"zz\"))")

(defn- script-probe [compiled javascript]
  (let [encoded (.encodeToString (java.util.Base64/getEncoder)
                                 (.getBytes ^String (:source compiled) "UTF-8"))]
    (shell/sh "node" "--input-type=module" "-e"
              (str "import('data:text/javascript;base64," encoded
                   "').then(m=>{const x=m.instantiateKotoba({});" javascript
                   "}).catch(e=>{console.error(e);process.exit(70)})"))))

(defn- truthy? [v]
  (or (true? v) (= v 1) (= v 1N)))

(deftest document-reader-printer-roundtrip
  ;; KIR + restricted ESM first (same cut as W4 fifth). Wasm/browser-host
  ;; import wiring for document-print/document-read follows the
  ;; document-sha256 multi-repo pattern and is a fast follow-up.
  (let [script (compiler/compile-source source :js-kotoba-v1)
        kir (:kir script)]
    (testing "reference KIR: print→read equals original; sha256 stable"
      (is (truthy? (ir/execute kir 'main [])))
      (is (truthy? (ir/execute kir 'same [])))
      (is (= 1 (ir/execute kir 'dig-same [])))
      (is (truthy? (ir/execute kir 'empty-ok [])))
      (is (truthy? (ir/execute kir 'leaves-ok [])))
      (let [page (ir/execute kir 'page [])
            printed (ir/execute kir 'dig-print [])]
        (is (string? printed))
        (is (re-matches #"[0-9a-f]+" printed))
        (is (= printed (value/document-print page)))
        (is (= page (value/document-read printed)))
        (is (= (value/document-sha256-hex page)
               (value/document-sha256-hex (value/document-read printed))))))
    (testing "malformed print fails closed"
      (is (thrown? clojure.lang.ExceptionInfo (ir/execute kir 'bad []))))
    (testing "restricted ESM agrees"
      (let [probe (script-probe script
                                (str "const t=v=>v===true||v===1n||v===1;"
                                     "if(!t(x.main())||!t(x.same())||x['dig-same']()!==1n)process.exit(2);"
                                     "if(!t(x['empty-ok']())||!t(x['leaves-ok']()))process.exit(3);"
                                     "const p=x['dig-print']();"
                                     "if(typeof p!=='string'||!/^[0-9a-f]+$/.test(p))process.exit(4);"
                                     "let denied=false;try{x.bad()}catch(e){denied=true}"
                                     "if(!denied)process.exit(5);"
                                     "console.log('ok');"))]
        (is (zero? (:exit probe)) (str (:err probe) (:out probe)))
        (is (= "ok\n" (:out probe)))))))
