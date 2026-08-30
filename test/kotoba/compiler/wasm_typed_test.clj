(ns kotoba.compiler.wasm-typed-test
  (:require [clojure.java.shell :as shell]
            [clojure.string :as str]
            [clojure.test :refer [deftest is testing]]
            [kotoba.wasm.core :as wasm]
            [kotoba.wasm.typed :as typed]
            [kotoba.compiler.core :as compiler]
            [kotoba.kir :as ir]
            [kotoba.kir.value :as value]))

(defn- node-probe [compiled javascript]
  (let [encoded (.encodeToString (java.util.Base64/getEncoder) ^bytes (:bytes compiled))
        probe (str "import('./runtime/browser-host.mjs').then(async m=>{"
                   "const h=await m.instantiateKotoba(Buffer.from(process.argv[1],'base64'));"
                   javascript "}).catch(e=>{console.error(e);process.exit(70)})")]
    (shell/sh "node" "--input-type=module" "-e" probe encoded)))

(def option-source
  "(defn main [] (match-option (option-some-of [:option :i64] 7)
                                [:option :i64]
                                (none 0)
                                (some value (+ value 1))))")

(deftest typed-metadata-is-versioned-deterministic-and-bounded
  (let [kir (:kir (compiler/compile-source option-source :js-kotoba-v1))
        table (typed/descriptor-table kir)
        bytes (typed/metadata-bytes kir)]
    (is (= typed/abi-version (first bytes)))
    (is (= bytes (typed/metadata-bytes kir)))
    (is (= (count table) (count (typed/descriptor-indices kir))))
    (is (empty? (typed/literal-table kir)))
    (is (some #{[:option :i64]} table))
    (is (every? #(<= 0 % 255) bytes))))

(deftest typed-custom-section-is-emitted-only-for-kir-v4
  (let [i64-kir (:kir (compiler/compile-source "(defn main [] 7)" :wasm32-kotoba-v1))
        typed-kir (assoc i64-kir :format :kotoba.kir/v4)
        typed-bytes (vec (map #(bit-and (int %) 0xff)
                              (wasm/emit typed-kir :wasm32-kotoba-v1)))
        i64-bytes (vec (map #(bit-and (int %) 0xff)
                            (wasm/emit i64-kir :wasm32-kotoba-v1)))
        marker (mapv int (.getBytes typed/custom-section-name "UTF-8"))]
    (testing "custom section identity is present in typed modules"
      (is (some #(= marker %) (partition (count marker) 1 typed-bytes))))
    (testing "legacy i64 modules do not acquire a typed ABI claim"
    (is (not-any? #(= marker %) (partition (count marker) 1 i64-bytes))))))

(deftest canonical-list-closure-results-run-on-the-browser-wasm-host
  (let [source
        "(defn main []
           (vector-count
             (invoke [:list :i64]
               (fn [x] (list x (+ x 1))) 7)))"
        compiled (compiler/compile-source source :wasm32-browser-kotoba-v1)
        probe (node-probe compiled
                          "if(h.instance.exports.main()!==2n)process.exit(2);")]
    (is (= 2 (ir/execute (:kir compiled) 'main [])))
    (is (zero? (:exit probe)) (:err probe))))

(deftest canonical-bytes-closure-results-cross-all-typed-runtimes
  (let [source
        "(ns bytes.closure (:export [main identity]))
         (defn main [] :bytes
           (invoke :bytes (fn [] (bytes))))
         (defn identity [value :bytes] :bytes value)"
        javascript (:source (compiler/compile-source source :js-kotoba-v1))
        js-encoded (.encodeToString (java.util.Base64/getEncoder)
                                    (.getBytes javascript "UTF-8"))
        js-probe
        (shell/sh
         "node" "--input-type=module" "-e"
         (str "import('data:text/javascript;base64," js-encoded
              "').then(m=>{const x=m.instantiateKotoba({}),empty=x.main(),input=new Uint8Array([1,2,3]);"
              "if(!(empty instanceof Uint8Array)||empty.byteLength!==0||x.identity(input)!==input)process.exit(2);"
              "try{x.identity('not-bytes');process.exit(3)}catch(e){if(e.message!=='invalid-bytes')process.exit(4)}})"))
        compiled (compiler/compile-source source :wasm32-browser-kotoba-v1)
        wasm-probe
        (node-probe
         compiled
         (str "const x=h.instance.exports,empty=x.main(),input=new Uint8Array([1,2,3]);"
              "if(h.typedAbi.version!==14||!h.typedAbi.descriptors.includes('bytes'))process.exit(2);"
              "if(!(empty instanceof Uint8Array)||empty.byteLength!==0||x.identity(input)!==input)process.exit(3);"
              "try{x.identity('not-bytes');process.exit(4)}catch(e){if(e.code!=='invalid-typed-value')process.exit(5)}"))
        reference (ir/execute (:kir compiled) 'main [])]
    (is (value/bytes-value? reference))
    (is (zero? (value/bytes-byte-count reference)))
    (is (zero? (:exit js-probe)) (:err js-probe))
    (is (zero? (:exit wasm-probe)) (:err wasm-probe))))

(deftest parameterized-i64-bitwise-ops-have-wasm-runtime-lowering
  (let [source
        "(ns i64.bitwise (:export [main xor and-bits]))
         (defn main [] :i64 42)
         (defn xor [x :i64 y :i64] :i64 (bit-xor x y))
         (defn and-bits [x :i64 y :i64] :i64 (bit-and x y))"
        compiled (compiler/compile-source source :wasm32-browser-kotoba-v1)
        probe (node-probe
               compiled
               (str "const x=h.instance.exports;"
                    "if(x.xor(-1n,0x5555555555555555n)!==-6148914691236517206n)process.exit(2);"
                    "if(x['and-bits'](-1n,0x5555555555555555n)!==0x5555555555555555n)process.exit(3);"))]
    (is (zero? (:exit probe)) (:err probe))))

(deftest static-multi-arity-has-real-wasm-runtime-parity
  (let [source
        "(ns multi.arity (:export [main offset]))
         (defn main [] (offset 40))
         (defn offset
           ([x] (offset x 1))
           ([x delta] (+ x delta)))"
        compiled (compiler/compile-source source :wasm32-browser-kotoba-v1)
        probe (node-probe
               compiled
               (str "const x=h.instance.exports;"
                    "if(x['offset$arity$1'](40n)!==41n)process.exit(2);"
                    "if(x['offset$arity$2'](40n,2n)!==42n)process.exit(3);"))]
    (is (= ['main 'offset$arity$1 'offset$arity$2] (get-in compiled [:hir :exports])))
    (is (= 41 (ir/execute (:kir compiled) 'main [])))
    (is (= 41 (ir/execute (:kir compiled) 'offset$arity$1 [40])))
    (is (= 42 (ir/execute (:kir compiled) 'offset$arity$2 [40 2])))
    (is (zero? (:exit probe)) (:err probe))))

(deftest bounded-xml-queries-have-reference-and-typed-wasm-runtime-parity
  (let [source
        "(ns xml.query (:export [main count-links count-elements element-text link-text link-name]))
         (defn main [] 0)
         (defn count-links [xml :string] :i64 (xml-path-count xml \"html/robot/link\"))
         (defn count-elements [xml :string name :string] :i64 (xml-name-count xml name))
         (defn element-text [xml :string name :string index :i64] [:option :string]
           (xml-name-text xml name index))
         (defn link-text [xml :string index :i64] [:option :string]
           (xml-path-text xml \"html/robot/link\" index))
         (defn link-name [xml :string index :i64] [:option :string]
           (xml-path-attr xml \"html/robot/link\" index \"name\"))"
        xml "<?xml version=\"1.0\" encoding=\"utf-8\"?><!DOCTYPE html><html><robot><link name=\"base\"> Hello <span>typed</span> Wasm </link><link name=\"tip\"/></robot></html>"
        compiled (compiler/compile-source source :wasm32-browser-kotoba-v1)
        probe (node-probe
               compiled
               (str "const x=h.instance.exports,xml=" (pr-str xml) ";"
                    "const tip=x['link-name'](xml,1n),missing=x['link-name'](xml,2n),text=x['link-text'](xml,0n),named=x['element-text'](xml,'link',0n);"
                    "if(x['count-links'](xml)!==2n||x['count-elements'](xml,'link')!==2n||!tip[1]||tip[2]!=='tip'||missing[1]||!text[1]||text[2]!=='Hello typed Wasm'||!named[1]||named[2]!=='Hello typed Wasm')process.exit(2);"))]
    (is (= 2 (ir/execute (:kir compiled) 'count-links [xml])))
    (is (= [[:option :string] true "tip"]
           (ir/execute (:kir compiled) 'link-name [xml 1])))
    (is (= [[:option :string] true "Hello typed Wasm"]
           (ir/execute (:kir compiled) 'link-text [xml 0])))
    (is (= 2 (ir/execute (:kir compiled) 'count-elements [xml "link"])))
    (is (= [[:option :string] true "Hello typed Wasm"]
           (ir/execute (:kir compiled) 'element-text [xml "link" 0])))
    (is (zero? (:exit probe)) (:err probe))))

(deftest i32-wrapping-shifts-and-xorshift-have-wasm-runtime-parity
  (let [source
        "(ns i32.profile (:export [main signed unsigned add mul xor shl shr ushr next]))
         (defn main [] :i64 42)
         (defn signed [x :i64] :i64 (i32-wrap x))
         (defn unsigned [x :i64] :i64 (u32-wrap x))
         (defn add [x :i64 y :i64] :i64 (i32-wrapping-add x y))
         (defn mul [x :i64 y :i64] :i64 (i32-wrapping-mul x y))
         (defn xor [x :i64 y :i64] :i64 (i32-xor x y))
         (defn shl [x :i64] :i64 (i32-shift-left x 31))
         (defn shr [x :i64] :i64 (i32-shift-right x 31))
         (defn ushr [x :i64] :i64 (u32-shift-right x 1))
         (defn next [x :i64] :i64 (xorshift32 x))"
        compiled (compiler/compile-source source :wasm32-kotoba-v1)
        probe (node-probe
               compiled
               (str "const x=h.instance.exports;"
                    "if(x.main()!==42n||x.signed(4294967295n)!==-1n||x.unsigned(-1n)!==4294967295n)process.exit(2);"
                    "if(x.add(2147483647n,1n)!==-2147483648n||x.mul(2147483647n,2n)!==-2n)process.exit(3);"
                    "if(x.xor(-1n,2147483647n)!==-2147483648n||x.shl(1n)!==-2147483648n)process.exit(4);"
                    "if(x.shr(-2147483648n)!==-1n||x.ushr(-1n)!==2147483647n)process.exit(5);"
                    "if(x.next(1n)!==270369n||x.next(270369n)!==67634689n||x.next(67634689n)!==2647435461n||x.next(2147483648n)!==2148024320n)process.exit(6);"))]
    (is (zero? (:exit probe)) (:err probe))))

(deftest local-indices-above-127-use-canonical-uleb128
  (let [typed-bindings (str/join " " (mapcat (fn [index]
                                                 [(str "x" index) (str (double index))])
                                               (range 131)))
        untyped-bindings (str/join " " (mapcat (fn [index]
                                                   [(str "x" index) (str index)])
                                                 (range 131)))
        typed (compiler/compile-source
               (str "(defn main [] :f64 (let [" typed-bindings "] x130))")
               :wasm32-browser-kotoba-v1)
        untyped (compiler/compile-source
                 (str "(defn main [] (let [" untyped-bindings "] x130))")
                 :wasm32-browser-kotoba-v1)
        typed-encoded (.encodeToString (java.util.Base64/getEncoder) (:bytes typed))
        untyped-encoded (.encodeToString (java.util.Base64/getEncoder) (:bytes untyped))
        result (shell/sh "node" "--input-type=module" "-e"
                         (str "Promise.all(["
                              "WebAssembly.instantiate(Buffer.from('" typed-encoded "','base64'),{}),"
                              "WebAssembly.instantiate(Buffer.from('" untyped-encoded "','base64'),{})"
                              "]).then(([typed,untyped])=>{"
                              "if(typed.instance.exports.main()!==130)process.exit(2);"
                              "if(untyped.instance.exports.main()!==130n)process.exit(3);"
                              "console.log('wasm-local-uleb128-ok')})"
                              ".catch(e=>{console.error(e);process.exit(99)})"))]
    (is (zero? (:exit result)) (:err result))
    (is (= "wasm-local-uleb128-ok\n" (:out result)))))

(deftest compatibility-is-sealed-and-host-admitted-before-instantiation
  (let [compiled (compiler/compile-source "(defn main [] 42)" :wasm32-browser-kotoba-v1)
        encoded (.encodeToString (java.util.Base64/getEncoder) ^bytes (:bytes compiled))
        probe (shell/sh
               "node" "--input-type=module" "-e"
               (str "import('./runtime/browser-host.mjs').then(async m=>{"
                    "const b=Buffer.from(process.argv[1],'base64');"
                    "const h=await m.instantiateKotoba(b);"
                    "if(h.compatibility.compiler!=='kotoba-compiler/1'||"
                    "h.compatibility.language!=='kotoba.language/safe-v1'||"
                    "h.compatibility.target!=='wasm32-browser-kotoba-v1')process.exit(2);"
                    "const marker=Buffer.from('kotoba-compiler/1');const at=b.indexOf(marker);"
                    "if(at<0)process.exit(3);b[at+marker.length-1]=50;"
                    "try{await m.instantiateKotoba(b);process.exit(4)}catch(e){"
                    "if(e.code!=='compatibility-mismatch')process.exit(5)}})"
                    ".catch(e=>{console.error(e);process.exit(70)})")
               encoded)]
    (is (= :kotoba.compatibility/v1 (get-in compiled [:compatibility :format])))
    (is (zero? (:exit probe)) (:err probe))))

(deftest externref-boundaries-reject-forgery-and-cross-schema-substitution
  (let [source "(ns typed.boundary (:export [main make-i64 make-string read-i64]))
                (defn main [] 0)
                (defn make-i64 [] [:option :i64] (option-some-of [:option :i64] 7))
                (defn make-string [] [:option :string] (option-some-of [:option :string] \"bad\"))
                (defn read-i64 [value [:option :i64]] :i64
                  (match-option value [:option :i64] (none 0) (some item item)))"
        compiled (compiler/compile-source source :wasm32-kotoba-v1)
        probe (node-probe
               compiled
               (str "const x=h.instance.exports;"
                    "if(x['read-i64'](x['make-i64']())!==7n)process.exit(2);"
                    "for(const forged of ["
                    "Object.freeze([Object.freeze(['option','i64']),true,7n]),"
                    "x['make-string']()]){let rejected=false;try{x['read-i64'](forged)}catch(e){rejected=true}"
                    "if(!rejected)process.exit(3)}"))]
    (is (= :kotoba.value/typed-v1 (:value-profile compiled)))
    (is (= :kotoba.typed/externref-v1 (:value-abi compiled)))
    (is (= #{:reference-types} (:wasm-features compiled)))
    (is (zero? (:exit probe)) (:err probe))))

(deftest schema-referenced-typed-capability-crosses-the-browser-wasm-boundary
  (let [source
        "(ns typed.capability
           (:export [main make-request make-other invoke])
           (:capabilities #{:http/post})
           (:schemas {:demo/request [:record :demo/request [[:url :string]]]
                      :demo/other [:record :demo/other [[:url :string]]] }))
         (defn main [] 0)
         (defn make-request [] [:record :demo/request [[:url :string]]]
           (record [:record :demo/request [[:url :string]]] \"https://example.test\"))
         (defn make-other [] [:record :demo/other [[:url :string]]]
           (record [:record :demo/other [[:url :string]]] \"https://example.test\"))
         (defn invoke [request [:ref :demo/request]] [:ref :demo/request]
           (typed-cap-call :http/post [:ref :demo/request] [:ref :demo/request] request))"
        compiled (compiler/compile-source source :wasm32-browser-kotoba-v1
                                          {:allow #{[:cap/call 4]}})
        encoded (.encodeToString (java.util.Base64/getEncoder) ^bytes (:bytes compiled))
        probe (shell/sh
               "node" "--input-type=module" "-e"
               (str "import('./runtime/browser-host.mjs').then(async m=>{"
                    "let calls=0;const h=await m.instantiateKotoba(Buffer.from(process.argv[1],'base64'),{"
                    "allowCapabilities:[4],typedCapCall:(id,request,contract)=>{"
                    "calls++;"
                    "if(id!==4||contract.request[0]!=='ref'||contract.result[0]!=='ref')process.exit(2);"
                    "return request}});const x=h.instance.exports;"
                    "const request=x['make-request']();if(x.invoke(request)!==request)process.exit(3);"
                    "try{x.invoke(x['make-other']());process.exit(5)}catch(e){}if(calls!==1)process.exit(6);"
                    "if(h.typedAbi.version!==9||h.typedAbi.schemas.get(':demo/request')===undefined)process.exit(4)"
                    "}).catch(e=>{console.error(e);process.exit(70)})")
               encoded)]
    (is (= typed/schema-abi-version (first (typed/metadata-bytes (:kir compiled)))))
    (is (zero? (:exit probe)) (:err probe))))

(deftest typed-capability-provider-result-is-validated-after-dispatch
  (let [source
        "(ns typed.capability-result (:export [main invoke]) (:capabilities #{:http/post}))
         (defn main [] 0)
         (defn invoke [request :string] :string
           (typed-cap-call :http/post :string :string request))"
        compiled (compiler/compile-source source :wasm32-browser-kotoba-v1
                                          {:allow #{[:cap/call 4]}})
        encoded (.encodeToString (java.util.Base64/getEncoder) ^bytes (:bytes compiled))
        probe (shell/sh
               "node" "--input-type=module" "-e"
               (str "import('./runtime/browser-host.mjs').then(async m=>{"
                    "const h=await m.instantiateKotoba(Buffer.from(process.argv[1],'base64'),{"
                    "allowCapabilities:[4],typedCapCall:()=>7n});"
                    "try{h.instance.exports.invoke('request');process.exit(2)}catch(e){"
                    "if(e.code!=='invalid-typed-value')process.exit(3)}})"
                    ".catch(e=>{console.error(e);process.exit(70)})")
               encoded)]
    (is (zero? (:exit probe)) (:err probe))))

(deftest structured-f64-and-f32-cross-the-sealed-wasm-abi
  (let [source
        "(ns typed.floating-structure
           (:export [main vector-value vector-x vector-y moved-x point point-x point-y graph-x]))
         (defn main [] 0)
         (defn vector-value [] [:vector [:f64 :f32]]
           (hetero-vector [:vector [:f64 :f32]] -0.0 (f64-to-f32-rounded 1.25)))
         (defn vector-x [] :f64
           (hetero-vector-at [:vector [:f64 :f32]] (vector-value) 0))
         (defn vector-y [] :f32
           (hetero-vector-at [:vector [:f64 :f32]] (vector-value) 1))
         (defn moved-x [] :f64
           (hetero-vector-at [:vector [:f64 :f32]]
             (hetero-vector-assoc [:vector [:f64 :f32]] (vector-value) 0 2.5) 0))
         (defn point [] [:record :geometry/point [[:x :f64] [:y :f32]]]
           (record [:record :geometry/point [[:x :f64] [:y :f32]]]
             (f64-div 0.0 0.0) (f64-to-f32-rounded -0.0)))
         (defn point-x [] :f64
           (record-get [:record :geometry/point [[:x :f64] [:y :f32]]] (point) :x))
         (defn point-y [] :f32
           (record-get [:record :geometry/point [[:x :f64] [:y :f32]]] (point) :y))
         (defn graph-x [] :f64
           (record-get [:record :geometry/point [[:x :f64] [:y :f32]]]
             (option-value-of
               [:option [:record :geometry/point [[:x :f64] [:y :f32]]]]
               (typed-map-get
                 [:map :keyword [:record :geometry/point [[:x :f64] [:y :f32]]]]
                 (typed-map-new
                   [:map :keyword [:record :geometry/point [[:x :f64] [:y :f32]]]]
                   :origin
                   (record [:record :geometry/point [[:x :f64] [:y :f32]]]
                     4.5 (f64-to-f32-rounded 6.0)))
                 :origin)
               (record [:record :geometry/point [[:x :f64] [:y :f32]]]
                 0.0 (f64-to-f32-rounded 0.0)))
             :x))"
        js-compiled (compiler/compile-source source :js-kotoba-v1)
        compiled (compiler/compile-source source :wasm32-browser-kotoba-v1)
        probe (node-probe
               compiled
               (str "const x=h.instance.exports,v=x['vector-value'](),p=x.point();"
                    "if(!Object.is(x['vector-x'](),-0)||x['vector-y']()!==1.25||x['moved-x']()!==2.5)process.exit(2);"
                    "if(!Number.isNaN(x['point-x']())||!Object.is(x['point-y'](),-0))process.exit(3);"
                    "if(!Object.isFrozen(v)||!Object.isFrozen(p)||x['graph-x']()!==4.5)process.exit(4);"))]
    (is (= :kotoba.typed/mixed-f32-f64-v3
           (get-in compiled [:compatibility :value-abi])))
    (is (Double/isNaN (double (ir/execute (:kir js-compiled) 'point-x []))))
    (is (= (Double/doubleToRawLongBits -0.0)
           (Double/doubleToRawLongBits
            (double (ir/execute (:kir js-compiled) 'vector-x [])))))
    (is (= 2.5 (ir/execute (:kir js-compiled) 'moved-x [])))
    (is (= 4.5 (ir/execute (:kir js-compiled) 'graph-x [])))
    (is (zero? (:exit probe)) (:err probe))))

(deftest direct-floating-ordered-collections-fail-closed
  (doseq [type ["[:set :f64]" "[:map :keyword :f64]" "[:map :f32 :i64]"]]
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo
         #"direct floating"
         (compiler/compile-source
          (str "(defn main [] " type " 0)")
          :wasm32-browser-kotoba-v1)))))

(deftest algebraic-operations-have-sealed-wasm-runtime-parity
  (let [source
        "(ns typed.operations (:export [main check-option read-option check-result read-result
                                        update-vector compare-vector set-has set-add set-remove compare-set
                                        update-record compare-record nested-set-count]))
         (defn main [] 0)
         (defn check-option [] :bool (option-some?-of [:option :i64] (option-some-of [:option :i64] 7)))
         (defn read-option [] :i64 (option-value-of [:option :i64] (option-some-of [:option :i64] 7) (quot 1 0)))
         (defn check-result [] :bool (result-ok?-of [:result :i64 :string] (result-ok-of [:result :i64 :string] 8)))
         (defn read-result [] :i64 (result-value-of [:result :i64 :string] (result-ok-of [:result :i64 :string] 8) (quot 1 0)))
         (defn update-vector [] :string
           (hetero-vector-at [:vector [:i64 :string]]
             (hetero-vector-assoc [:vector [:i64 :string]]
               (hetero-vector [:vector [:i64 :string]] 1 \"before\") 1 \"after\") 1))
         (defn compare-vector [] :i64
           (hetero-vector-equal [:vector [:i64 :string]]
             (hetero-vector [:vector [:i64 :string]] 1 \"same\")
             (hetero-vector [:vector [:i64 :string]] 1 \"same\")))
         (defn set-has [] :bool
           (typed-set-contains [:set :i64] (typed-set [:set :i64] 1 2) 2))
         (defn set-add [] :i64
           (typed-set-count [:set :i64]
             (typed-set-conj [:set :i64] (typed-set [:set :i64] 1) 2)))
         (defn set-remove [] :i64
           (typed-set-count [:set :i64]
             (typed-set-disj [:set :i64] (typed-set [:set :i64] 1 2) 1)))
         (defn compare-set [] :i64
           (typed-set-equal [:set :i64]
             (typed-set [:set :i64] 2 1) (typed-set [:set :i64] 1 2)))
         (defn update-record [] :i64
           (record-get [:record :demo/person [[:name :string] [:age :i64]]]
             (record-assoc [:record :demo/person [[:name :string] [:age :i64]]]
               (record [:record :demo/person [[:name :string] [:age :i64]]] \"A\" 1) :age 2) :age))
         (defn compare-record [] :i64
           (record-equal [:record :demo/person [[:name :string] [:age :i64]]]
             (record [:record :demo/person [[:name :string] [:age :i64]]] \"A\" 1)
             (record [:record :demo/person [[:name :string] [:age :i64]]] \"A\" 1)))
         (defn nested-set-count [] :i64
           (typed-set-count [:set :keyword]
             (record-get [:record :demo/report [[:covered [:set :keyword]]]]
               (record [:record :demo/report [[:covered [:set :keyword]]]]
                 (typed-set [:set :keyword] :ready :reviewed))
               :covered)))"
        compiled (compiler/compile-source source :wasm32-kotoba-v1)
        probe (node-probe
               compiled
               (str "const x=h.instance.exports;"
                    "const expected={'check-option':true,'read-option':7n,'check-result':true,'read-result':8n,"
                    "'update-vector':'after','compare-vector':1n,'set-has':true,'set-add':2n,"
                    "'set-remove':1n,'compare-set':1n,'update-record':2n,'compare-record':1n,"
                    "'nested-set-count':2n};"
                    "for(const [name,value] of Object.entries(expected))"
                    "if(x[name]()!=value){console.error(name,x[name](),value);process.exit(2)}"))]
    (is (zero? (:exit probe)) (:err probe))))

(deftest typed-control-flow-preserves-bool-and-reference-comparisons
  (let [source
        "(ns typed.control (:export [main strings-match keyword-match]))
         (defn main [] :i64
           (if (string=? \"Kotoba\" \"Kotoba\")
             (if (= :ready :ready) 42 1)
             0))
         (defn strings-match [] :bool
           (if (string=? \"same\" \"same\") true false))
         (defn keyword-match [] :bool (= :ready :ready))"
        compiled (compiler/compile-source source :wasm32-kotoba-v1)
        probe (node-probe
               compiled
               (str "const x=h.instance.exports;"
                    "if(x.main()!==42n||x['strings-match']()!==true||"
                    "x['keyword-match']()!==true)process.exit(2);"))]
    (is (zero? (:exit probe)) (:err probe))))

(deftest string-equality-remains-bool-through-recursive-reference-calls
  (let [source
        "(ns typed.recursive-string (:export [main matches]))
         (defn matches [target :string remaining :i64] :bool
           (if (= remaining 0)
             (string=? target \"root\")
             (matches target (- remaining 1))))
         (defn main [] :i64
           (+ (if (matches \"root\" 3) 1 0)
              (if (matches \"other\" 2) 1 0)))"
        compiled (compiler/compile-source source :wasm32-kotoba-v1)
        probe (node-probe
               compiled
               (str "const x=h.instance.exports;"
                    "if(x.main()!==1n||x.matches('root',4n)!==true||"
                    "x.matches('other',4n)!==false)process.exit(2);"))]
    (is (zero? (:exit probe)) (:err probe))))

(deftest typed-if-needs-no-unsealed-synthetic-boolean-literal
  (let [source
        "(ns typed.import-like (:export [main]))
         (defn covered? [items [:set :keyword]] :bool
           (typed-set-contains [:set :keyword] items :ready))
         (defn main [] :i64
           (if (covered? (typed-set [:set :keyword] :ready)) 42 0))"
        compiled (compiler/compile-source source :wasm32-kotoba-v1)
        probe (node-probe compiled
                          "if(h.instance.exports.main()!==42n)process.exit(2);")]
    (is (not-any? #{[:bool true]} (typed/literal-table (:kir compiled))))
    (is (zero? (:exit probe)) (:err probe))))

(deftest bounded-vector-i64-has-sealed-wasm-runtime-parity
  (let [full (str "(vector-i64 " (str/join " " (range 128)) ")")
        source
        (str "(ns typed.vector-i64 (:export [main bitops make count-items lookup at update append drop-items full]))\n"
             "(defn main [] :i64 42)\n"
             "(defn bitops [] :i64 (bit-xor (bit-and 255 15) 5))\n"
             "(defn make [] :vector-i64 (vector-i64 10 20 30))\n"
             "(defn count-items [items :vector-i64] :i64 (vector-count items))\n"
             "(defn lookup [items :vector-i64 index :i64] :i64 (vector-get items index 99))\n"
             "(defn at [items :vector-i64 index :i64] :i64 (vector-at items index))\n"
             "(defn update [items :vector-i64 index :i64] :vector-i64 (vector-assoc items index 77))\n"
             "(defn append [items :vector-i64] :vector-i64 (vector-conj items 40))\n"
             "(defn drop-items [items :vector-i64 index :i64] :vector-i64 (vector-drop items index))\n"
             "(defn full [] :vector-i64 " full ")")
        compiled (compiler/compile-source source :wasm32-kotoba-v1)
        probe (node-probe
               compiled
               (str "const x=h.instance.exports,v=x.make();"
                    "const binary=h.typedValues.bytes(Buffer.alloc(12171,7));"
                    "if(x.main()!==42n||x.bitops()!==10n||x['count-items'](v)!==3n||x.lookup(v,1n)!==20n||"
                    "x.lookup(v,-1n)!==99n||x.lookup(v,4294967296n)!==99n||x.at(v,2n)!==30n)process.exit(2);"
                    "if(x['count-items'](binary)!==12171n||x.at(binary,12170n)!==7n)process.exit(5);"
                    "const updated=x.update(v,1n),appended=x.append(v),dropped=x['drop-items'](v,2n);"
                    "if(x.at(updated,1n)!==77n||x['count-items'](appended)!==4n||"
                    "x['count-items'](dropped)!==1n||x.at(dropped,0n)!==30n)process.exit(3);"
                    "for(const run of [()=>x.at(v,-1n),()=>x.at(v,4294967296n),"
                    "()=>x.update(v,4294967296n),()=>x['drop-items'](v,4n),"
                    "()=>h.typedValues.bytes(Buffer.alloc(16385)),()=>h.typedValues.bytes([256]),"
                    "()=>h.typedValues.vectorI64([1n,2]),"
                    "()=>x['count-items'](Object.freeze([v[0],10n,20n,30n]))]){"
                    "let rejected=false;try{run()}catch(e){rejected=true}if(!rejected)process.exit(4)}"))]
    (is (= 8 typed/abi-version))
    (is (some #{:vector-i64} (typed/descriptor-table (:kir compiled))))
    (is (zero? (:exit probe)) (:err probe))))

(deftest bounded-vector-f64-has-sealed-wasm-runtime-parity
  (let [source
        (str "(ns typed.vector-f64 (:export [main make count-items lookup lazy-lookup at update append drop-items]))\n"
             "(defn main [] :i64 42)\n"
             "(defn make [] :vector-f64 (vector-f64 -0.0 ##NaN 1.5))\n"
             "(defn count-items [items :vector-f64] :i64 (vector-f64-count items))\n"
             "(defn lookup [items :vector-f64 index :i64 fallback :f64] :f64 (vector-f64-get items index fallback))\n"
             "(defn lazy-lookup [items :vector-f64] :f64 "
             "  (vector-f64-get items 0 (i64-to-f64-checked (f64-to-i64-checked ##NaN))))\n"
             "(defn at [items :vector-f64 index :i64] :f64 (vector-f64-at items index))\n"
             "(defn update [items :vector-f64 index :i64 item :f64] :vector-f64 (vector-f64-assoc items index item))\n"
             "(defn append [items :vector-f64 item :f64] :vector-f64 (vector-f64-conj items item))\n"
             "(defn drop-items [items :vector-f64 count :i64] :vector-f64 (vector-f64-drop items count))")
        compiled (compiler/compile-source source :wasm32-kotoba-v1)
        probe (node-probe
               compiled
               (str "const x=h.instance.exports,v=x.make();"
                    "if(x['count-items'](v)!==3n||!Object.is(x.at(v,0n),-0)||!Number.isNaN(x.at(v,1n))||x.at(v,2n)!==1.5)process.exit(2);"
                    "if(!Object.is(x['lazy-lookup'](h.typedValues.vectorF64([-0])), -0)||x.lookup(v,99n,-2.5)!==-2.5)process.exit(3);"
                    "const updated=x.update(v,2n,-0),appended=x.append(v,Infinity),dropped=x['drop-items'](v,2n);"
                    "if(!Object.is(x.at(updated,2n),-0)||x.at(appended,3n)!==Infinity||x.at(dropped,0n)!==1.5)process.exit(4);"
                    "for(const run of [()=>x.at(v,-1n),()=>x.update(v,3n,0),()=>x['drop-items'](v,4n),"
                    "()=>h.typedValues.vectorF64(Array(16385).fill(0)),()=>h.typedValues.vectorF64([0n])]){"
                    "let rejected=false;try{run()}catch(e){rejected=true}if(!rejected)process.exit(5)}"))]
    (is (some #{:vector-f64} (typed/descriptor-table (:kir compiled))))
    (is (zero? (:exit probe)) (:err probe))))

(deftest bounded-typed-map-has-real-wasm-runtime-parity
  (let [source
        "(ns typed.map (:export [main present missing update remove compare-map]))
         (defn main [] :i64 42)
         (defn present [] :i64
           (option-value-of [:option :i64]
             (typed-map-get [:map :keyword :i64]
               (typed-map-new [:map :keyword :i64] :b 2 :a 1) :b) 0))
         (defn missing [] [:option :i64]
           (typed-map-get [:map :keyword :i64]
             (typed-map-new [:map :keyword :i64]) :missing))
         (defn update [] :i64
           (typed-map-count [:map :keyword :i64]
             (typed-map-assoc [:map :keyword :i64]
               (typed-map-new [:map :keyword :i64] :a 1) :b 2)))
         (defn remove [] :bool
           (typed-map-contains [:map :keyword :i64]
             (typed-map-dissoc [:map :keyword :i64]
               (typed-map-new [:map :keyword :i64] :a 1 :b 2) :a) :b))
         (defn compare-map [] :i64
           (typed-map-equal [:map :keyword :i64]
             (typed-map-new [:map :keyword :i64] :b 2 :a 1)
             (typed-map-new [:map :keyword :i64] :a 1 :b 2)))"
        compiled (compiler/compile-source source :wasm32-kotoba-v1)
        probe (node-probe
               compiled
               (str "const x=h.instance.exports,n=x.missing();"
                    "if(x.main()!==42n||x.present()!==2n||n[1]!==false||"
                    "x.update()!==2n||x.remove()!==true||x['compare-map']()!==1n)process.exit(2);"))]
    (is (= 31 (get-in compiled [:limits :typed-map-entries])))
    (is (zero? (:exit probe)) (:err probe))))

(deftest descriptor-node-budget-is-per-descriptor-with-a-separate-table-bound
  (let [names (mapv #(symbol (str "value-" %)) (range 16))
        exports (str/join " " (cons "main" (map str names)))
        functions
        (str/join
         "\n"
         (map-indexed
          (fn [index name]
            (let [type (str "[:record :budget/type-" index
                            " [[:a :i64] [:b :string] [:c [:option :i64]]]]")]
              (str "(defn " name " [] " type
                   " (record " type " " index " \"v\" (option-none-of [:option :i64])))")))
          names))
        source (str "(ns typed.descriptor-budget (:export [" exports "]))\n"
                    "(defn main [] :i64 42)\n" functions)
        compiled (compiler/compile-source source :wasm32-kotoba-v1)
        probe (node-probe compiled "if(h.instance.exports.main()!==42n)process.exit(2);")]
    (is (> (count (typed/descriptor-table (:kir compiled))) 16))
    (is (zero? (:exit probe)) (:err probe))))

(deftest scalar-option-and-result-ops-have-real-wasm-lowering
  ;; Regression for compiler#258: these monomorphic operations were admitted
  ;; and executed by the reference/JS paths, but fell through the typed Wasm
  ;; emitter with `typed Wasm operation is not qualified`.
  (let [source
        "(ns scalar.adt (:export [main]))
         (defn main [] :i64
           (if (option-some? (option-some 7))
             (+ (option-value (option-some 8) 90)
                (+ (option-value (option-none) 9)
                   (+ (result-value (result-ok 10) 91)
                      (+ (result-error (result-err 8) 92)
                         (if (result-ok? (result-err 1)) 93 0)))))
             94))"
        compiled (compiler/compile-source source :wasm32-browser-kotoba-v1)
        descriptors (set (typed/descriptor-table (:kir compiled)))
        probe (node-probe compiled
                          "if(h.instance.exports.main()!==35n)process.exit(2);")]
    (is (= 35 (ir/execute (:kir compiled) 'main [])))
    (is (contains? descriptors :option-i64))
    (is (contains? descriptors :result-i64))
    (is (= (typed/encode-descriptor [:option :i64])
           (typed/encode-descriptor :option-i64)))
    (is (= (typed/encode-descriptor [:result :i64 :i64])
           (typed/encode-descriptor :result-i64)))
    (is (zero? (:exit probe)) (:err probe))))

(deftest f64-scratch-locals-are-fully-declared-before-instantiation
  ;; Regression for kotoba-lang/amu#206 Bug 1: a typed function that
  ;; needs six-or-more f64 scratch locals (each `f64-from-bits` constant
  ;; allocates one for its NaN canonicalization) declared too few of them,
  ;; because the locals declaration read `@locals` before the lazy body
  ;; emission had realized all `allocate!` side effects. The module compiled
  ;; ({:ok true}) but failed to instantiate with `invalid local index: N`.
  ;; A five-`:f64`-param callee (at the max-parameters limit) plus a caller
  ;; whose comparison introduces a sixth f64 constant reproduces exactly six
  ;; scratch locals in one function.
  (let [source
        "(ns f64.scratch (:export [main]))
         (defn five [a :f64 b :f64 c :f64 d :f64 e :f64] :f64
           (f64-add a (f64-add b (f64-add c (f64-add d e)))))
         (defn main [] :i64
           (if (f64-eq 15.0 (five 1.0 2.0 3.0 4.0 5.0)) 42 1))"
        compiled (compiler/compile-source source :wasm32-browser-kotoba-v1)
        probe (node-probe compiled
                          "if(h.instance.exports.main()!==42n)process.exit(2);")]
    (is (zero? (:exit probe)) (:err probe))))

(deftest scalar-f64-body-ops-select-the-typed-kir-even-with-i64-signatures
  ;; Regression: a function whose exported signature is scalar :i64 but whose
  ;; BODY uses scalar f64 ops (f64-from-bits, f64-eq, f64-add, ...) was
  ;; classified :kotoba.kir/v3 (untyped) because the typed-values? scan looked
  ;; at signatures + structured body ops but NOT scalar f64/f32 ops. The
  ;; untyped v3 emitter has no lowering for them, so it emitted `call nil`
  ;; (a null function index) -> NullPointerException at module byte assembly.
  (testing "the module is promoted to the typed KIR"
    (let [kir (:kir (compiler/compile-source
                     "(ns t (:export [main]))
                      (defn main [] :i64
                        (if (f64-eq (f64-from-bits 1) (f64-from-bits 2)) 42 1))"
                     :js-browser-kotoba-v1))]
      (is (= :kotoba.kir/v4 (:format kir)))))
  (testing "a purely-i64 body is NOT promoted"
    (let [kir (:kir (compiler/compile-source
                     "(ns t (:export [main])) (defn main [] :i64 (+ 40 2))"
                     :js-browser-kotoba-v1))]
      (is (= :kotoba.kir/v3 (:format kir)))))
  (testing "it now emits and runs on wasm32-browser (3.0 == 1.0 + 2.0)"
    (let [three "(f64-from-bits 4613937818241073152)"
          one "(f64-from-bits 4607182418800017408)"
          two "(f64-from-bits 4611686018427387904)"
          source (str "(ns t (:export [main]))"
                      "(defn main [] :i64 (if (f64-eq " three
                      " (f64-add " one " " two ")) 42 99))")
          compiled (compiler/compile-source source :wasm32-browser-kotoba-v1)
          probe (node-probe compiled
                            "if(h.instance.exports.main()!==42n)process.exit(2);")]
      (is (zero? (:exit probe)) (:err probe)))))

(deftest clock-now-wasm32-imports-kotoba-cap-and-validates
  ;; amu elaborates `(clock/now seed)` to `(typed-cap-call 7 :i64 :i64 seed)`.
  ;; After kotoba-wasm aac02618 that is a valid `kotoba:cap`/`call` module,
  ;; not the ill-typed `kotoba:typed`/`cap-call` externref fallback.
  (let [source (str "(ns t (:export [main]) (:capabilities #{:clock/now}))\n"
                    "(defn main [] (clock/now 0))\n")
        compiled (compiler/compile-source source :wasm32-kotoba-v1
                                          {:allow #{[:cap/call 7]}})
        text (String. (byte-array (map unchecked-byte (:bytes compiled)))
                      "ISO-8859-1")
        tmp (java.io.File/createTempFile "amu-clock-now-" ".wasm")]
    (try
      (with-open [out (java.io.FileOutputStream. tmp)]
        (.write out ^bytes (:bytes compiled)))
      (is (str/includes? text (str "kotoba:cap" (char 4) "call")))
      (is (not (str/includes? text (str "kotoba:typed" (char 8) "cap-call"))))
      (let [validated (shell/sh "wasm-tools" "validate" (.getPath tmp))]
        (is (zero? (:exit validated)) (:err validated)))
      (finally
        (.delete tmp)))))

;; ADR 0285. A structural position inside a heterogeneous value arrives as a
;; KIR i64 literal. The Wasm emitter used it directly as a host `nth` index,
;; which is a no-op cast here and a throw on cljs, so `bin/amu compile
;; --target wasm32` answered `:kotoba/internal-error` for every source using
;; `hetero-vector-at`/`hetero-vector-assoc` while this runtime compiled the
;; same source fine.
;;
;; These assertions cannot see that defect -- nothing on the JVM could, which
;; is why it lasted. The falsifying test is `test/nbb`'s
;; `hetero-vector-position` case, on the runtime that was broken. What this
;; test establishes instead is the thing exit 0 does not: that the emitted
;; module AGREES WITH THE KIR REFERENCE INTERPRETER, at every export, by
;; export NAME rather than by a guessed offset.
(def ^:private hetero-position-fixture
  "test/nbb/fixtures/hetero-vector-position.kotoba")

(def ^:private hetero-position-arguments
  "Arguments per export. Positions in the fixture are non-zero and its members
  differ in both value and type, so a misread position is a wrong result here,
  not merely a throw."
  {'main [] 'head [3 2.5] 'tail [3 2.5] 'swapped-tail [3 2.5 9.25]})

(defn- javascript-argument [value]
  (if (integer? value) (str value "n") (str value)))

(deftest heterogeneous-positions-agree-with-the-kir-interpreter
  (let [source (slurp hetero-position-fixture)
        compiled (compiler/compile-source source :wasm32-browser-kotoba-v1)
        exports (:exports (:kir compiled))
        expected (into {} (for [name exports]
                            [(str name)
                             (str (ir/execute (:kir compiled) name
                                              (get hetero-position-arguments name)))]))
        ;; Call by the name the ARTIFACT declares, not by a guessed position:
        ;; calling index 0 would silently exercise a different function.
        calls (str/join
               (for [name exports]
                 (str "console.log(" (pr-str (str name)) "+'='+String(x["
                      (pr-str (str name)) "]("
                      (str/join "," (map javascript-argument
                                         (get hetero-position-arguments name)))
                      ")));")))
        probe (node-probe compiled (str "const x=h.instance.exports;" calls))
        observed (into {} (for [line (str/split-lines (str/trim (:out probe)))
                                :when (str/includes? line "=")]
                            (let [[k v] (str/split line #"=" 2)] [k v])))]
    (testing "every export the artifact declares is exercised"
      (is (= #{'main 'head 'tail 'swapped-tail} (set exports)))
      (is (every? hetero-position-arguments exports)))
    (testing "the reference interpreter reads the positions the fixture names"
      (is (= {"main" "327" "head" "3" "tail" "2.5" "swapped-tail" "9.25"} expected)))
    (testing "the emitted module returns what the reference interpreter returns"
      (is (zero? (:exit probe)) (:err probe))
      (is (= expected observed) (:out probe)))))
