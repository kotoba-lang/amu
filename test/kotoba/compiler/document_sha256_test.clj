(ns kotoba.compiler.document-sha256-test
  "W4 third slice: first-class document-sha256 host op.

  Completes the identity half of the W4 exit gate that
  document_digest_style_test.clj proved with a pure guest FNV fingerprint.
  Guest source calls (document-sha256 d) and the same hex is produced by:

  - KIR interpreter (kotoba-kir value/document-sha256-hex)
  - restricted ESM (:js-kotoba-v1 via kotoba-script)
  - real wasm + browser-host (:wasm32-browser-kotoba-v1)

  DOM reconciliation remains out of scope."
  (:require [clojure.java.shell :as shell]
            [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]
            [kotoba.kir :as ir]
            [kotoba.kir.value :as value]))

(def source
  "(ns ui.document-sha256 (:export [main null-digest hello world zero-pos zero-neg external]))
   (defn null-digest [] :string (document-sha256 (document-null)))
   (defn hello [] :string
     (document-sha256
       (document-map :tag (document-string \"div\")
                     :text (document-string \"Hello\"))))
   (defn world [] :string
     (document-sha256
       (document-map :tag (document-string \"div\")
                     :text (document-string \"World\"))))
   (defn zero-pos [] :string (document-sha256 (document-f64 0.0)))
   (defn zero-neg [] :string (document-sha256 (document-f64 -0.0)))
   (defn external [value :document] :string (document-sha256 value))
   (defn main [] :string (hello))")
(def null-hex
  "1b16b1df538ba12dc3f97edbb85caa7050d46c148134290feba80f8236c83db9")

(defn- script-probe [compiled javascript]
  (let [encoded (.encodeToString (java.util.Base64/getEncoder)
                                 (.getBytes ^String (:source compiled) "UTF-8"))]
    (shell/sh "node" "--input-type=module" "-e"
              (str "import('data:text/javascript;base64," encoded
                   "').then(m=>{const x=m.instantiateKotoba({});" javascript
                   "}).catch(e=>{console.error(e);process.exit(70)})"))))

(defn- node-probe [compiled javascript]
  (let [encoded (.encodeToString (java.util.Base64/getEncoder) ^bytes (:bytes compiled))]
    (shell/sh "node" "--input-type=module" "-e"
              (str "import('./runtime/browser-host.mjs').then(async m=>{"
                   "const h=await m.instantiateKotoba(Buffer.from(process.argv[1],'base64'));"
                   javascript "}).catch(e=>{console.error(e);process.exit(70)})") encoded)))

(deftest document-sha256-has-kir-script-and-wasm-parity
  (let [wasm (compiler/compile-source source :wasm32-browser-kotoba-v1)
        script (compiler/compile-source source :js-kotoba-v1)
        kir (:kir wasm)
        hello-hex (ir/execute kir 'hello [])
        world-hex (ir/execute kir 'world [])
        null-out (ir/execute kir 'null-digest [])]
    (testing "reference KIR"
      (is (= null-hex null-out))
      (is (re-matches #"[0-9a-f]{64}" hello-hex))
      (is (not= hello-hex world-hex))
      (is (= hello-hex (ir/execute kir 'main [])))
      (is (= (ir/execute kir 'zero-pos []) (ir/execute kir 'zero-neg [])))
      (is (= hello-hex
             (value/document-sha256-hex
              ["map" (vec (sort-by (comp str first)
                                   [[:tag ["string" "div"]]
                                    [:text ["string" "Hello"]]]))]))))
    (testing "restricted ESM agrees"
      (let [probe (script-probe script
                                (str "if(x['null-digest']()!=='" null-hex "')process.exit(2);"
                                     "const h=x.hello(),w=x.world();"
                                     "if(h!==" (pr-str hello-hex) "||w!==" (pr-str world-hex) ")process.exit(3);"
                                     "if(x['zero-pos']()!==x['zero-neg']())process.exit(4);"
                                     "if(x.external(['map',[[':tag',['string','div']],[':text',['string','Hello']]]])!==h)process.exit(5);"))]
        (is (zero? (:exit probe)) (str (:err probe) (:out probe)))))
    (testing "real wasm + browser-host agrees"
      (let [probe (node-probe wasm
                              (str "const x=h.instance.exports;"
                                   "if(x['null-digest']()!=='" null-hex "')process.exit(2);"
                                   "const hsh=x.hello(),w=x.world();"
                                   "if(hsh!==" (pr-str hello-hex) "||w!==" (pr-str world-hex) ")process.exit(3);"
                                   "if(x['zero-pos']()!==x['zero-neg']())process.exit(4);"
                                   "const d=h.typedValues.document(['map',[[':tag',['string','div']],[':text',['string','Hello']]]]);"
                                   "if(x.external(d)!==hsh)process.exit(5);"))]
        (is (zero? (:exit probe)) (str (:err probe) (:out probe)))))))