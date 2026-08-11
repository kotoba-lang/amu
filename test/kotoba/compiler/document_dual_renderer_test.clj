(ns kotoba.compiler.document-dual-renderer-test
  "W4 sixth slice (ADR-2607279200 Delivery 4 / migration plan W4):

  Dual-renderer qualification on one shared logical UI `:document`:

  1. Pure guest HTML *stream* (data → string recursion; same contract as
     document_ui_render_test)
  2. Host DOM reconcile (`reconcileUiDocument`; same contract as
     document_dom_reconcile_test)

  Both renderers consume the *same* ordinary document value. The guest never
  holds a host object; handles stay host-side. After a persistent
  `document-assoc` update of a leaf, both renderers agree on the new structure.
  A lightweight performance workload (repeated build+render of a bounded tree)
  records that construction/render stays under a current-thread CPU budget
  before any HAMT/arena selection — the other remaining W4 exit item.

  Complements slices 1–5. Does not claim full :ui/commit kit qualification (W5)."
  (:require [clojure.string :as str]
            [clojure.java.shell :as shell]
            [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]
            [kotoba.kir :as ir]))

(def source
  "(ns ui.document-dual (:export [page updated html html-updated dig dig-updated depth-ok]))
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
   (defn updated [] :document
     (node \"div\"
       (document-vector
         (leaf \"h1\" \"Hello\")
         (document-assoc (leaf \"p\" \"World\") :text (document-string \"Other\")))))
   (defn html [] :string (render (page)))
   (defn html-updated [] :string (render (updated)))
   (defn dig [] :string (document-sha256 (page)))
   (defn dig-updated [] :string (document-sha256 (updated)))
   (defn depth-ok [] :i64 (document-count (kids-of (page))))")

(def expected-html "<div><h1>Hello</h1><p>World</p></div>")
(def expected-html-updated "<div><h1>Hello</h1><p>Other</p></div>")

(def perf-source
  "(ns ui.document-perf (:export [html main]))
   (defn leaf [tag :string text :string] :document
     (document-map :tag (document-string tag) :text (document-string text)))
   (defn node [tag :string children :document] :document
     (document-map :tag (document-string tag) :children children))
   (defn page [] :document
     (node \"ul\"
       (document-vector
         (leaf \"li\" \"item-00\") (leaf \"li\" \"item-01\")
         (leaf \"li\" \"item-02\") (leaf \"li\" \"item-03\")
         (leaf \"li\" \"item-04\") (leaf \"li\" \"item-05\")
         (leaf \"li\" \"item-06\") (leaf \"li\" \"item-07\")
         (leaf \"li\" \"item-08\") (leaf \"li\" \"item-09\")
         (leaf \"li\" \"item-10\") (leaf \"li\" \"item-11\")
         (leaf \"li\" \"item-12\") (leaf \"li\" \"item-13\")
         (leaf \"li\" \"item-14\") (leaf \"li\" \"item-15\"))))
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
     (if (>= i n) acc
       (render-kids kids (+ i 1) n
         (string-concat acc
           (render (option-value-of [:option :document]
                     (document-vector-at kids i) (document-null)))))))
   (defn render [d :document] :string
     (if (string=? (text-of d) \"\")
       (string-concat \"<\" (string-concat (tag-of d)
         (string-concat \">\" (string-concat
           (render-kids (kids-of d) 0 (document-count (kids-of d)) \"\")
           (string-concat \"</\" (string-concat (tag-of d) \">\"))))))
       (string-concat \"<\" (string-concat (tag-of d)
         (string-concat \">\" (string-concat (text-of d)
           (string-concat \"</\" (string-concat (tag-of d) \">\"))))))))
   (defn html [] :string (render (page)))
   (defn main [] :string (html))")

(defn- script-probe [compiled javascript]
  (let [encoded (.encodeToString (java.util.Base64/getEncoder)
                                 (.getBytes ^String (:source compiled) "UTF-8"))]
    (shell/sh "node" "--input-type=module" "-e"
              (str "import('data:text/javascript;base64," encoded
                   "').then(async m=>{"
                   "const {reconcileUiDocument,createMockDom}="
                   "await import('./runtime/browser-host.mjs');"
                   "const x=m.instantiateKotoba({});"
                   ;; Serialize mock DOM elements to the same tag/text HTML
                   ;; shape the guest stream renderer emits (no attributes).
                   "function serialize(el){"
                   "  if(!el||el.nodeType!==1)return '';"
                   "  const tag=String(el.tagName).toLowerCase();"
                   "  const kids=el.children||[];"
                   "  if(kids.length===0){"
                   "    return '<'+tag+'>'+(el.textContent||'')+'</'+tag+'>';"
                   "  }"
                   "  let body='';"
                   "  for(const c of kids) body+=serialize(c);"
                   "  return '<'+tag+'>'+body+'</'+tag+'>';"
                   "}"
                   javascript
                   "}).catch(e=>{console.error(e);process.exit(70)})"))))

(deftest dual-renderers-agree-on-one-logical-document
  (let [wasm (compiler/compile-source source :wasm32-kotoba-v1 {})
        script (compiler/compile-source source :js-kotoba-v1)
        kir (:kir wasm)
        probe
        (script-probe
         script
         (str "const pageHtml=x.html();"
              "const updHtml=x['html-updated']();"
              "if(pageHtml!==" (pr-str expected-html) ")process.exit(2);"
              "if(updHtml!==" (pr-str expected-html-updated) ")process.exit(3);"
              "const dom=createMockDom();"
              "const root=dom.createContainer();"
              "const r1=reconcileUiDocument(root,x.page(),dom);"
              "const domHtml=serialize(r1);"
              "if(domHtml!==pageHtml){console.error('dom!=stream',domHtml,pageHtml);process.exit(4);}"
              "const r2=reconcileUiDocument(root,x.updated(),dom);"
              "if(r2!==r1)process.exit(5);"
              "const domUpd=serialize(r2);"
              "if(domUpd!==updHtml){console.error('upd mismatch',domUpd,updHtml);process.exit(6);}"
              "if(x.dig()===x['dig-updated']())process.exit(7);"
              "console.log('ok');"))]
    (testing "guest stream renderer (KIR)"
      (is (= expected-html (ir/execute kir 'html [])))
      (is (= expected-html-updated (ir/execute kir 'html-updated [])))
      (is (= 2 (ir/execute kir 'depth-ok [])))
      (is (not= (ir/execute kir 'dig []) (ir/execute kir 'dig-updated []))))
    (testing "stream ⇄ DOM dual-renderer parity + persistent update (ESM+host)"
      (is (zero? (:exit probe)) (str (:err probe) (:out probe)))
      (is (= "ok\n" (:out probe))))))

(defn- current-thread-cpu-nanos []
  (let [bean (java.lang.management.ManagementFactory/getThreadMXBean)]
    (when-not (.isCurrentThreadCpuTimeSupported bean)
      (throw (ex-info "current-thread CPU time is unavailable" {})))
    (when-not (.isThreadCpuTimeEnabled bean)
      (.setThreadCpuTimeEnabled bean true))
    (.getCurrentThreadCpuTime bean)))

(deftest dual-renderer-soft-performance-workload
  (let [wasm (compiler/compile-source perf-source :wasm32-kotoba-v1 {})
        kir (:kir wasm)
        _ (dotimes [_ 20] (ir/execute kir 'html []))
        wall-t0 (System/nanoTime)
        cpu-t0 (current-thread-cpu-nanos)
        _ (dotimes [_ 200] (ir/execute kir 'html []))
        cpu-ms (/ (double (- (current-thread-cpu-nanos) cpu-t0)) 1.0e6)
        wall-ms (/ (double (- (System/nanoTime) wall-t0)) 1.0e6)
        sample (ir/execute kir 'html [])]
    (testing "build+render 200× of a 16-leaf tree stays under soft budget"
      (is (string? sample))
      (is (str/includes? sample "<li>item-00</li>"))
      (is (str/includes? sample "<li>item-15</li>"))
      ;; CPU time measures the single-threaded guest evaluator itself. Wall time
      ;; remains diagnostic evidence, but scheduler pauses cannot fail the gate.
      (is (< cpu-ms 5000.0)
          (str "200 renders used " cpu-ms " CPU ms and " wall-ms
               " wall ms (CPU budget 5000 ms)"))
      (println "W4-sixth KIR render:" cpu-ms "CPU ms;" wall-ms "wall ms"))))
