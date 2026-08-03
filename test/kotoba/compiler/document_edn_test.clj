(ns kotoba.compiler.document-edn-test
  (:require [clojure.java.shell :as shell]
            [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]
            [kotoba.kir :as ir]))

(def source
  "(ns data.document-edn
     (:export [main value printed same commented symbol-doc symbol-text parsed-symbol symbol-value list-doc list-text parsed-list list-same list-second set-doc set-text parsed-set set-same set-has-ready general-map general-text general-name general-constructed general-constructed-text bad-symbol bad-tag bad-set-duplicate bad-duplicate bad-general-duplicate bad-limit]))
   (defn main [] :i64 42)
   (defn value [] :document
     (document-map
       :goal (document-string \"言葉\")
       :attempt (document-i64 -7)
       :ready (document-bool true)
       :steps (document-vector (document-null) (document-keyword :actor/run))))
   (defn printed [] :string (document-edn-print (value)))
   (defn same [] :bool
     (document-equal? (value) (document-edn-read (document-edn-print (value)))))
   (defn commented [] :document
     (document-edn-read \"; policy\\n{:b false, :a 1}\"))
   (defn symbol-doc [] :document (document-symbol (symbol \"actor/run\")))
   (defn symbol-text [] :string (document-edn-print (symbol-doc)))
   (defn parsed-symbol [] :document (document-edn-read \"actor/run\"))
   (defn symbol-value [] [:option :symbol] (document-symbol-value (parsed-symbol)))
   (defn list-doc [] :document (document-list (document-symbol (symbol \"actor/run\")) (document-i64 7)))
   (defn list-text [] :string (document-edn-print (list-doc)))
   (defn parsed-list [] :document (document-edn-read \"(actor/run 7)\"))
   (defn list-same [] :bool (document-equal? (list-doc) (parsed-list)))
   (defn list-second [] [:option :document] (document-list-at (parsed-list) 1))
   (defn set-doc [] :document
     (document-set (document-string \"one\") (document-keyword :ready) (document-i64 1)))
   (defn set-text [] :string (document-edn-print (set-doc)))
   (defn parsed-set [] :document (document-edn-read \"#{\\\"one\\\" 1 :ready}\"))
   (defn set-same [] :bool (document-equal? (set-doc) (parsed-set)))
   (defn set-has-ready [] :bool
     (document-set-contains? (parsed-set) (document-keyword :ready)))
   (defn general-map [] :document
     (document-edn-read \"{[1 2] :pair, \\\"name\\\" 7, :ready true}\"))
   (defn general-text [] :string (document-edn-print (general-map)))
   (defn general-name [] :i64
     (option-value-of [:option :i64]
       (document-i64-value
         (option-value-of [:option :document]
           (document-get (general-map) (document-string \"name\"))
           (document-null)))
       -1))
   (defn general-constructed [] :document
     (document-map
       (document-vector (document-i64 1)) (document-string \"vector-key\")
       :legacy (document-bool true)))
   (defn general-constructed-text [] :string (document-edn-print (general-constructed)))
   (defn bad-symbol [] :string (document-edn-print (document-symbol (symbol \"nil\"))))
   (defn bad-tag [] :document (document-edn-read \"#inst \\\"2026-08-03\\\"\"))
   (defn bad-set-duplicate [] :document (document-edn-read \"#{:a :a}\"))
   (defn bad-duplicate [] :document (document-edn-read \"{:a 1 :a 2}\"))
   (defn bad-general-duplicate [] :document (document-edn-read \"{[1] :a [1] :b}\"))
   (defn bad-limit [] :document
     (document-edn-read
       \"[nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil nil]\"))")

(def expected
  "{:attempt -7 :goal \"言葉\" :ready true :steps [nil :actor/run]}")

(defn- script-probe [compiled javascript]
  (let [encoded (.encodeToString (java.util.Base64/getEncoder)
                                 (.getBytes ^String (:source compiled) "UTF-8"))]
    (shell/sh "node" "--input-type=module" "-e"
              (str "import('data:text/javascript;base64," encoded
                   "').then(m=>{" javascript
                   "}).catch(e=>{console.error(e);process.exit(70)})"))))

(defn- wasm-probe [compiled javascript]
  (let [encoded (.encodeToString (java.util.Base64/getEncoder) ^bytes (:bytes compiled))]
    (shell/sh "node" "--input-type=module" "-e"
              (str "import('./runtime/browser-host.mjs').then(async m=>{"
                   "const h=await m.instantiateKotoba(Buffer.from(process.argv[1],'base64'));"
                   javascript "}).catch(e=>{console.error(e);process.exit(70)})")
              encoded)))

(def runtime-probe
  (str "const x=" "RUNTIME" ";"
       "if(x.printed()!==" (pr-str expected) ")process.exit(2);"
       "if(!(x.same()===true||x.same()===1||x.same()===1n))process.exit(3);"
       "if(x['symbol-text']()!=='actor/run'||x['parsed-symbol']()[0]!=='symbol')process.exit(4);"
       "if(x['list-text']()!=='(actor/run 7)'||x['parsed-list']()[0]!=='list'||!(x['list-same']()===true||x['list-same']()===1||x['list-same']()===1n))process.exit(5);"
       "if(x['set-text']()!=='#{1 :ready \\\"one\\\"}'||x['parsed-set']()[0]!=='set'||!(x['set-same']()===true||x['set-same']()===1||x['set-same']()===1n)||!(x['set-has-ready']()===true||x['set-has-ready']()===1||x['set-has-ready']()===1n))process.exit(6);"
       "if(x['general-text']()!=='{:ready true \\\"name\\\" 7 [1 2] :pair}'||x['general-name']()!==7n)process.exit(8);"
       "if(x['general-constructed-text']()!=='{:legacy true [1] \\\"vector-key\\\"}')process.exit(9);"
       "for(const name of ['bad-symbol','bad-tag','bad-set-duplicate','bad-duplicate','bad-general-duplicate','bad-limit']){"
       "let denied=false;try{x[name]()}catch(e){denied=true}if(!denied)process.exit(7);}"
       "console.log('ok');"))

(deftest textual-edn-document-codec-is-backend-identical
  (let [wasm (compiler/compile-source source :wasm32-browser-kotoba-v1)
        script (compiler/compile-source source :js-kotoba-v1)
        kir (:kir wasm)]
    (testing "reference KIR"
      (is (= expected (ir/execute kir 'printed [])))
      (is (true? (ir/execute kir 'same [])))
      (is (= "(actor/run 7)" (ir/execute kir 'list-text [])))
      (is (true? (ir/execute kir 'list-same [])))
      (is (= "#{1 :ready \"one\"}" (ir/execute kir 'set-text [])))
      (is (true? (ir/execute kir 'set-same [])))
      (is (true? (ir/execute kir 'set-has-ready [])))
      (is (= "{:ready true \"name\" 7 [1 2] :pair}" (ir/execute kir 'general-text [])))
      (is (= 7 (ir/execute kir 'general-name [])))
      (is (= "{:legacy true [1] \"vector-key\"}" (ir/execute kir 'general-constructed-text [])))
      (doseq [name ['bad-tag 'bad-set-duplicate 'bad-duplicate 'bad-general-duplicate 'bad-limit]]
        (is (thrown? clojure.lang.ExceptionInfo (ir/execute kir name [])))))
    (testing "restricted ESM"
      (let [result (script-probe script
                                 (.replace runtime-probe "RUNTIME"
                                           "m.instantiateKotoba({})"))]
        (is (zero? (:exit result)) (str (:err result) (:out result)))
        (is (= "ok\n" (:out result)))))
    (testing "typed browser Wasm"
      (let [result (wasm-probe wasm
                               (.replace runtime-probe "RUNTIME"
                                         "h.instance.exports"))]
        (is (zero? (:exit result)) (str (:err result) (:out result)))
        (is (= "ok\n" (:out result)))))))
