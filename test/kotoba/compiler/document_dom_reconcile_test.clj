(ns kotoba.compiler.document-dom-reconcile-test
  "W4 fourth slice (ADR-2607279200 Delivery 4 / migration plan W4):

  A logical UI `:document` (same shallow shape as document_ui_render_test —
  `:tag` / `:text` / `:children`) is reconciled into a real DOM tree by a
  *host* API (`reconcileUiDocument` on browser-host). The guest never holds a
  host object; handles stay host-side.

  Proves the W4 exit-gate piece 'reconciled to browser DOM' without claiming
  the full :ui/commit capability kit (flat node set + revision). Dangerous
  tags fail closed. Second reconcile updates text/structure in place."
  (:require [clojure.java.shell :as shell]
            [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]
            [kotoba.kir :as ir]))

(def source
  "(ns ui.document-dom (:export [page other script-tag]))
   (defn leaf [tag :string text :string] :document
     (document-map :tag (document-string tag) :text (document-string text)))
   (defn node [tag :string children :document] :document
     (document-map :tag (document-string tag) :children children))
   (defn page [] :document
     (node \"div\"
       (document-vector
         (leaf \"h1\" \"Hello\")
         (leaf \"p\" \"World\"))))
   (defn other [] :document
     (node \"div\"
       (document-vector
         (leaf \"h1\" \"Hello\")
         (leaf \"p\" \"Other\"))))
   (defn script-tag [] :document
     (leaf \"script\" \"alert(1)\"))")

(defn- script-probe [compiled javascript]
  (let [encoded (.encodeToString (java.util.Base64/getEncoder)
                                 (.getBytes ^String (:source compiled) "UTF-8"))]
    (shell/sh "node" "--input-type=module" "-e"
              (str "import('data:text/javascript;base64," encoded
                   "').then(async m=>{"
                   "const {reconcileUiDocument,createMockDom}="
                   "await import('./runtime/browser-host.mjs');"
                   "const x=m.instantiateKotoba({});"
                   javascript
                   "}).catch(e=>{console.error(e);process.exit(70)})"))))

(deftest logical-ui-document-reconciles-to-dom
  (let [script (compiler/compile-source source :js-kotoba-v1)
        kir (:kir (compiler/compile-source source :wasm32-kotoba-v1 {}))
        probe
        (script-probe
         script
         (str "const dom=createMockDom();"
              "const root=dom.createContainer();"
              "const r1=reconcileUiDocument(root,x.page(),dom);"
              "if(r1.tagName!=='DIV')process.exit(2);"
              "if(root.childNodes.length!==1)process.exit(3);"
              "const kids=r1.children;"
              "if(kids.length!==2||kids[0].tagName!=='H1'||kids[1].tagName!=='P')process.exit(4);"
              "if(kids[0].textContent!=='Hello'||kids[1].textContent!=='World')process.exit(5);"
              "const r2=reconcileUiDocument(root,x.other(),dom);"
              "if(r2!==r1)process.exit(6);"
              "if(r2.children[1]!==kids[1])process.exit(7);"
              "if(r2.children[1].textContent!=='Other')process.exit(8);"
              "let denied=false;try{reconcileUiDocument(root,x['script-tag'](),dom)}"
              "catch(e){denied=e.code==='invalid-ui-document'}"
              "if(!denied)process.exit(9);"
              "console.log('ok');"))]
    (testing "guest still builds pure documents (no host objects)"
      (is (vector? (ir/execute kir 'page [])))
      (is (= "map" (first (ir/execute kir 'page [])))))
    (testing "host reconcile: structure, in-place update, deny-list"
      (is (zero? (:exit probe)) (str (:err probe) (:out probe)))
      (is (= "ok\n" (:out probe))))))
