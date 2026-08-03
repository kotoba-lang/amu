(ns kotoba.compiler.document-edn-test
  (:require [clojure.java.shell :as shell]
            [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]
            [kotoba.kir :as ir]))

(def source
  "(ns data.document-edn
     (:export [main value printed same commented symbol-doc symbol-text parsed-symbol symbol-value bad-symbol bad-tag bad-set bad-duplicate bad-limit]))
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
   (defn bad-symbol [] :string (document-edn-print (document-symbol (symbol \"nil\"))))
   (defn bad-tag [] :document (document-edn-read \"#inst \\\"2026-08-03\\\"\"))
   (defn bad-set [] :document (document-edn-read \"#{:a}\"))
   (defn bad-duplicate [] :document (document-edn-read \"{:a 1 :a 2}\"))
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
       "for(const name of ['bad-symbol','bad-tag','bad-set','bad-duplicate','bad-limit']){"
       "let denied=false;try{x[name]()}catch(e){denied=true}if(!denied)process.exit(5);}"
       "console.log('ok');"))

(deftest textual-edn-document-codec-is-backend-identical
  (let [wasm (compiler/compile-source source :wasm32-browser-kotoba-v1)
        script (compiler/compile-source source :js-kotoba-v1)
        kir (:kir wasm)]
    (testing "reference KIR"
      (is (= expected (ir/execute kir 'printed [])))
      (is (true? (ir/execute kir 'same [])))
      (doseq [name ['bad-tag 'bad-set 'bad-duplicate 'bad-limit]]
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
