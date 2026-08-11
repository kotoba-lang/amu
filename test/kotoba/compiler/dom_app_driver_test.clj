(ns kotoba.compiler.dom-app-driver-test
  "The application loop closes: a pure `.kotoba` module answers events.

  `document_dom_reconcile_test` proved a guest document reaches the DOM. That
  left the other direction open -- a rendered page that could not respond to a
  click. This exercises `runtime/dom-driver.mjs` end to end against
  `examples/todo-app.kotoba`: mount, type, add, toggle, filter, delete, with
  the state living in the guest between every step.

  Two properties matter as much as the behaviour:

  * The app requires NO capabilities. `init`/`view`/`step` are pure, so the
    host grants nothing and there is no provider on the path.
  * The `:attrs` allowlist keeps ADR 0025's exclusions closed. Event handlers,
    inline CSS and `javascript:` URLs are refused by the reconciler, so the
    attribute support this loop needs did not buy behaviour with it.

  The browser half of the same claim (real trusted events, three engines) is
  `tests/browser/browser.spec.mjs`; this one runs on the Node mock DOM so it
  stays in the ordinary test suite."
  (:require [clojure.java.io :as io]
            [clojure.java.shell :as shell]
            [clojure.string :as str]
            [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]))

(defn- app-source [] (slurp (io/file "examples/todo-app.kotoba")))

(defn- probe
  "Run `javascript` with the compiled app in `m` and the host runtime imported."
  [compiled javascript]
  (let [encoded (.encodeToString (java.util.Base64/getEncoder)
                                 (.getBytes ^String (:source compiled) "UTF-8"))]
    (shell/sh "node" "--input-type=module" "-e"
              (str "import('data:text/javascript;base64," encoded "').then(async m=>{"
                   "const {createMockDom,reconcileUiDocument}="
                   "await import('./runtime/browser-host.mjs');"
                   "const {mountKotobaApp}=await import('./runtime/dom-driver.mjs');"
                   "const dom=createMockDom();"
                   "const root=dom.createContainer();"
                   "const find=k=>{const walk=n=>{"
                   "if(n.nodeType===1&&n.getAttribute&&n.getAttribute('data-k')===k)return n;"
                   "for(const c of n.childNodes||[]){const r=walk(c);if(r)return r}return null};"
                   "return walk(root)};"
                   "const text=()=>root.textContent;"
                   javascript
                   "}).catch(e=>{console.error(e);process.exit(70)})"))))

(def ^:private compiled (delay (compiler/compile-source (app-source) :js-kotoba-v1)))

(deftest app-requires-no-capabilities
  (testing "a pure init/view/step module is granted nothing"
    (let [result (probe @compiled
                        (str "if(m.kotobaArtifact.requiredCapabilities.length!==0)process.exit(2);"
                             "const i=m.instantiateKotoba({});"
                             "if(typeof i.init!=='function')process.exit(3);"
                             "if(typeof i.view!=='function')process.exit(4);"
                             "if(typeof i.step!=='function')process.exit(5);"
                             "console.log('ok');"))]
      (is (zero? (:exit result)) (str (:err result) (:out result)))
      (is (= "ok\n" (:out result))))))

(deftest app-loop-answers-events
  (testing "mount, type, add, toggle, filter, delete"
    (let [result
          (probe @compiled
                 (str "const app=mountKotobaApp({instantiate:()=>m.instantiateKotoba({}),"
                      "container:root,dom});"
                      ;; Seeded with two items, one already done.
                      "if(!/render a kotoba document/.test(text()))process.exit(2);"
                      "if(!/2 left/.test(text()))process.exit(3);"
                      ;; An event on an unlabelled node is dropped, not guessed at.
                      "const before=text();"
                      "dom.dispatch(root,'click');"
                      "if(text()!==before)process.exit(4);"
                      ;; Typing reaches the guest and comes back as an attribute.
                      "const draft=find('draft');draft.value='prove the loop';"
                      "dom.dispatch(draft,'input');"
                      "if(find('draft').getAttribute('value')!=='prove the loop')process.exit(5);"
                      ;; Add clears the draft the guest was holding. The live
                      ;; PROPERTY has to clear, not just the attribute -- a
                      ;; typed-into field stops tracking its attribute, and
                      ;; asserting only the attribute passed while the real
                      ;; browser still showed the old text.
                      "dom.dispatch(find('add'),'click');"
                      "if(!/prove the loop/.test(text()))process.exit(6);"
                      "if(!/3 left/.test(text()))process.exit(7);"
                      "if(find('draft').getAttribute('value')!=='')process.exit(8);"
                      "if(find('draft').value!=='')process.exit(17);"
                      ;; Toggle flips exactly the item that was named.
                      "dom.dispatch(find('tc'),'click');"
                      "if(find('tc').textContent!=='[x]')process.exit(9);"
                      "if(find('ta').textContent!=='[x]')process.exit(10);"
                      "if(find('tb').textContent!=='[ ]')process.exit(11);"
                      ;; Filtering is guest state, so it survives re-render.
                      "dom.dispatch(find('f-active'),'click');"
                      "if(/prove the loop/.test(text()))process.exit(12);"
                      "if(!/carry a click back/.test(text()))process.exit(13);"
                      "dom.dispatch(find('f-all'),'click');"
                      ;; Delete removes one item and renumbers the rest.
                      "dom.dispatch(find('da'),'click');"
                      "if(/render a kotoba document/.test(text()))process.exit(14);"
                      "if(!/2 left/.test(text()))process.exit(15);"
                      ;; Unmount detaches; later events change nothing.
                      "app.unmount();"
                      "const after=text();"
                      "dom.dispatch(find('add'),'click');"
                      "if(text()!==after)process.exit(16);"
                      "console.log('ok');"))]
      (is (zero? (:exit result)) (str (:err result) (:out result)))
      (is (= "ok\n" (:out result))))))

(deftest a-session-outlives-one-instance-budget
  (testing "each interaction gets a fresh, fully-fuelled instance"
    (let [result
          (probe @compiled
                 (str "const app=mountKotobaApp({instantiate:()=>m.instantiateKotoba({}),"
                      "container:root,dom,onError:e=>{throw e}});"
                      ;; A single instance dies of fuel part-way through a
                      ;; session -- measured at the eighth interaction, which
                      ;; is why the driver takes a factory. Pin the shape of
                      ;; that failure so a "reuse the instance, it is faster"
                      ;; change cannot land quietly.
                      "const one=m.instantiateKotoba({});let died=0;"
                      "try{for(let i=0;i<40;i++){one.view(one.init())}}"
                      "catch(e){died=1;if(!/fuel/.test(e.message))process.exit(2)}"
                      "if(!died)process.exit(3);"
                      ;; The driver survives far past that.
                      "for(let i=0;i<100;i++){"
                      "app.dispatch('f-active','click');app.dispatch('f-all','click')}"
                      "if(!/carry a click back/.test(text()))process.exit(4);"
                      "if(app.instantiations()<200)process.exit(5);"
                      ;; The screen budget, not fuel, is what a growing app
                      ;; meets first: a :document holds 256 nodes.
                      "let rows=0,code='';"
                      "try{for(rows=0;rows<30;rows++){"
                      "app.dispatch('draft','input','item');"
                      "if(!app.dispatch('add','click'))break}}"
                      "catch(e){code=e.cause?.message??e.message}"
                      "if(code!=='doc-node-limit')process.exit(6);"
                      "if(rows<3||rows>20)process.exit(7);"
                      "console.log('ok');"))]
      (is (zero? (:exit result)) (str (:err result) (:out result)))
      (is (= "ok\n" (:out result))))))

(deftest attrs_reach_the_dom_without_buying_behaviour
  (testing "allowlisted attributes apply; handlers, CSS and unsafe URLs are refused"
    (let [result
          (probe @compiled
                 (str "const node=(tag,attrs)=>['map',[[':tag',['string',tag]],"
                      "[':attrs',['map',attrs]],[':text',['string','x']]]];"
                      "const code=n=>{try{reconcileUiDocument(dom.createContainer(),n,dom);"
                      "return 'accepted'}catch(e){return e.code}};"
                      ;; Allowed: nominal id, class, aria-*, a relative URL.
                      "const okEl=reconcileUiDocument(root,node('a',["
                      "[':data-k',['string','x']],[':class',['string','c']],"
                      "[':aria-label',['string','l']],[':href',['string','/docs']]]),dom);"
                      "if(okEl.getAttribute('data-k')!=='x')process.exit(2);"
                      "if(okEl.getAttribute('aria-label')!=='l')process.exit(3);"
                      ;; A boolean true is a present, empty attribute; false omits it.
                      "const b=reconcileUiDocument(dom.createContainer(),node('input',["
                      "[':disabled',['bool',true]],[':readonly',['bool',false]]]),dom);"
                      "if(b.getAttribute('disabled')!=='')process.exit(4);"
                      "if(b.getAttribute('readonly')!==null)process.exit(5);"
                      ;; A dropped attribute is removed, not left behind.
                      "const c=dom.createContainer();"
                      "reconcileUiDocument(c,node('div',[[':class',['string','a']]]),dom);"
                      "const kept=reconcileUiDocument(c,node('div',[[':id',['string','i']]]),dom);"
                      "if(kept.getAttribute('class')!==null)process.exit(6);"
                      "if(kept.getAttribute('id')!=='i')process.exit(7);"
                      ;; Refused, every one of them.
                      "if(code(node('div',[[':onclick',['string','x()']]]))!=='invalid-ui-document')process.exit(8);"
                      "if(code(node('div',[[':style',['string','top:0']]]))!=='invalid-ui-document')process.exit(9);"
                      "if(code(node('a',[[':href',['string','javascript:x()']]]))!=='invalid-ui-document')process.exit(10);"
                      "if(code(node('a',[[':src',['string','data:text/html,x']]]))!=='invalid-ui-document')process.exit(11);"
                      "if(code(node('div',[[':srcdoc',['string','x']]]))!=='invalid-ui-document')process.exit(12);"
                      "console.log('ok');"))]
      (is (zero? (:exit result)) (str (:err result) (:out result)))
      (is (= "ok\n" (:out result))))))

(deftest app-source-declares-no-effects
  (testing "the example carries no capability declaration at all"
    (is (not (str/includes? (app-source) ":capabilities")))
    (is (not (str/includes? (app-source) "cap-call")))))
