(ns kotoba.compiler.dom-app-repaint-test
  "What a keystroke costs the DOM in the app that ships.

  `test-reconcile-sharing.mjs` measures the reconciler against documents built
  by hand. This measures it against `examples/todo-app.kotoba` driven through
  `dom-driver`, which is the only arrangement that answers the question the
  content key exists for: a keystroke changes one attribute of one field, and
  the list of items is rebuilt from scratch by a fresh guest instance. Does any
  of that rebuilt list reach the DOM?

  The observation point is `getAttribute`. `applyUiAttrs` reads an attribute
  before writing it, and it runs for every node the reconciler walks -- so the
  attributes read during a repaint name exactly the nodes that were walked. The
  items carry `data-k` values of their own (`t<i>` to toggle, `d<i>` to
  delete), so their absence from that set is what says the list was skipped."
  (:require [clojure.java.io :as io]
            [clojure.java.shell :as shell]
            [kotoba.lang.text :as str]
            [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]))

(defn- app-source [] (slurp (io/file "examples/todo-app.kotoba")))

(def ^:private compiled (delay (compiler/compile-source (app-source) :js-kotoba-v1)))

(defn- probe [compiled javascript]
  (let [encoded (.encodeToString (java.util.Base64/getEncoder)
                                 (.getBytes ^String (:source compiled) "UTF-8"))]
    (shell/sh "node" "--input-type=module" "-e"
              (str "import('data:text/javascript;base64," encoded "').then(async m=>{"
                   "const {createMockDom}=await import('./runtime/browser-host.mjs');"
                   "const {mountKotobaApp}=await import('./runtime/dom-driver.mjs');"
                   "const base=createMockDom();"
                   ;; Every attribute read, tagged with the element that was asked.
                   "let reads=[];"
                   "const dom={createContainer:base.createContainer,"
                   "createTextNode:base.createTextNode,dispatch:base.dispatch,"
                   "createElement:t=>{const el=base.createElement(t);"
                   "const g=el.getAttribute.bind(el);"
                   "el.getAttribute=n=>{const v=g(n);reads.push(el.tagName+'/'+n+'='+(v==null?'':v));return v};return el}};"
                   "const root=dom.createContainer();"
                   "const find=k=>{const walk=n=>{"
                   "if(n.nodeType===1&&n.getAttribute&&n.getAttribute('data-k')===k)return n;"
                   "for(const c of n.childNodes||[]){const r=walk(c);if(r)return r}return null};"
                   "return walk(root)};"
                   "const text=()=>root.textContent;"
                   javascript
                   "}).catch(e=>{console.error(e);process.exit(70)})"))))

(deftest a-keystroke-does-not-repaint-the-list
  (testing "typing walks the field that changed and leaves the items alone"
    (let [result
          (probe @compiled
                 (str "const app=mountKotobaApp({instantiate:()=>m.instantiateKotoba({}),"
                      "container:root,dom,onError:e=>{throw e}});"
                      "if(!/render a kotoba document/.test(text()))process.exit(2);"
                      "if(!/2 left/.test(text()))process.exit(3);"
                      ;; `find` reads data-k all over the tree, so the window
                      ;; starts after it: measure only what the repaint does.
                      "const draft=find('draft');draft.value='ab';"
                      "reads=[];"
                      "dom.dispatch(draft,'input');"
                      "const walked=reads.slice();"
                      ;; The guest saw the keystroke and the field came back controlled.
                      "if(find('draft').getAttribute('value')!=='ab')process.exit(4);"
                      ;; ...and the list is still rendered and still right.
                      "if(!/render a kotoba document/.test(text()))process.exit(5);"
                      "if(!/2 left/.test(text()))process.exit(6);"
                      ;; The items own data-k values t<i> and d<i>. If the
                      ;; reconciler had walked the list it would have read them.
                      ;; Printed first, so a failure shows what was walked
                      ;; rather than only which assertion tripped.
                      "console.log(walked.length+' '+JSON.stringify(walked));"
                      ;; The list is the thing that must not be repainted, so
                      ;; the check is on the list's own elements rather than on
                      ;; a pattern in their ids. An earlier version matched
                      ;; `data-k` values of the form t<digit>; the app numbers
                      ;; its items with letters (there is no integer-to-string
                      ;; builtin), so that assertion matched nothing and passed
                      ;; with the memo disabled. Measured then: 39 attributes
                      ;; read instead of 7.
                      "const list=walked.filter(r=>/^(UL|LI)\\//.test(r));"
                      "if(list.length!==0)process.exit(7);"
                      ;; The field that DID change must have been walked, or the
                      ;; assertion above would pass for the wrong reason -- a
                      ;; repaint that walked nothing at all satisfies it too.
                      ;; getAttribute returns the value being replaced, so the
                      ;; read is recorded with the OLD value, not the new one.
                      "if(!walked.some(r=>r.startsWith('INPUT/value=')))process.exit(8);"))]
      (is (zero? (:exit result)) (str (:err result) (:out result)))
      (println "repaint walked:" (str/trim (:out result))))))
