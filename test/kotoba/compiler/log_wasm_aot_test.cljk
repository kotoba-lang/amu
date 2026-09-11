(ns kotoba.compiler.log-wasm-aot-test
  "Named :log/append and :log/read compile to wasm32 and run on the typed
  browser host. The inject is typedCapCall -- the same seam dataspace's
  wasm proof uses -- not JVM provider.log inside V8.

  :wasm-aot names that typed kit ABI (kotoba:typed/cap-call, ids 6 and 5).
  It is not clock's i64 kotoba:cap/call surface (:wasm32-kotoba-v1), and
  `module-imports-the-typed-seam-and-not-the-i64-one` is what separates the
  two claims: the compiled module has no kotoba:cap/call import at all.

  Log is the first kit to carry TWO capabilities across this surface, so the
  kit's :wasm-aot-surface is per grant where clock's and dataspace's are
  single. Both ids are proved here; proving only append would leave :log/read
  claimed and unmeasured.

  :native-aot stays :pending and `native-aot-target-still-refuses-this-kit`
  pins the reason, so the gap is a recorded rejection rather than an
  untried backend.

  Break: return a bare 5n from the append inject instead of the sealed
  record and `guest-runs-both-log-capabilities` fails on result admission."
  (:require [clojure.edn :as edn]
            [clojure.java.io :as io]
            [clojure.java.shell :as shell]
            [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]
            [provider.log :as log]))

(def policy {:allow #{[:cap/call 5] [:cap/call 6]}})

(def guest-source
  (let [areq (pr-str log/append-request-type)
        ares (pr-str log/append-result-type)
        rreq (pr-str log/read-request-type)
        rres (pr-str log/read-result-type)
        fset (pr-str log/field-set-type)]
    (str "(ns app.log (:export [main emit tail stale])"
         " (:capabilities #{:log/append :log/read}))"
         "(defn main [] 0)"
         "(defn emit [message :string] :i64"
         "  (record-get " ares
         "    (typed-cap-call :log/append " areq " " ares
         "      (record-new " areq " :log/info :app/started message"
         "        (typed-set-new " fset ")))"
         "    :sequence))"
         "(defn tail [after :i64] :i64"
         "  (record-get " rres
         "    (typed-cap-call :log/read " rreq " " rres
         "      (record-new " rreq " after 8))"
         "    :latest-sequence))"
         "(defn stale [after :i64] :i64"
         "  (if (record-get " rres
         "        (typed-cap-call :log/read " rreq " " rres
         "          (record-new " rreq " after 8))"
         "        :truncated)"
         "    1 0))")))

(defn- load-kit []
  (edn/read-string
   (slurp (io/resource "kotoba/lang/capability-kits/log-v1.edn"))))

(defn- compiled-browser []
  (compiler/compile-source guest-source :wasm32-browser-kotoba-v1 policy))

(defn- node-probe [compiled javascript]
  (let [encoded (.encodeToString (java.util.Base64/getEncoder)
                                 ^bytes (:bytes compiled))
        probe (str "import('./runtime/browser-host.mjs').then(async m=>{"
                   javascript
                   "}).catch(e=>{console.error(e);process.exit(70)})")]
    (shell/sh "node" "--input-type=module" "-e" probe encoded)))

;; append (6) answers with a sealed append-result record; read (5) answers
;; with a read-result whose :entries set is empty but still descriptor-typed.
(def inject-js
  (str "function logInject(id,request,contract){"
       "const result=contract.result;"
       "if(id===6){"
       "if(request[3]!=='ready')process.exit(30);"
       "return [result,5n]}"
       "if(id===5){"
       "if(request[1]!==5n)process.exit(31);"
       "const entries=result[2][3][1];"
       "return [result,1n,9n,true,Object.freeze([entries,Object.freeze([])])]}"
       "process.exit(20)}"))

(deftest named-log-guest-compiles-to-both-wasm32-targets
  (doseq [target [:wasm32-browser-kotoba-v1 :wasm32-kotoba-v1]]
    (testing (str target)
      (let [compiled (compiler/compile-source guest-source target policy)]
        (is (= :wasm/v1 (:format compiled)))
        (is (= :kotoba.typed/externref-v1 (:value-abi compiled)))
        (is (pos? (alength ^bytes (:bytes compiled))))))))

(deftest module-imports-the-typed-seam-and-not-the-i64-one
  "Discriminator between :wasm-aot and :wasm32-kotoba-v1 for this kit."
  (let [probe (node-probe
               (compiled-browser)
               (str "const mod=new WebAssembly.Module(Buffer.from(process.argv[1],'base64'));"
                    "const names=WebAssembly.Module.imports(mod)"
                    ".filter(i=>i.name==='cap-call'||i.name==='call')"
                    ".map(i=>i.module+'/'+i.name);"
                    "if(!names.includes('kotoba:typed/cap-call'))process.exit(2);"
                    "if(names.includes('kotoba:cap/call'))process.exit(3);"))]
    (is (zero? (:exit probe)) (str (:err probe) \newline (:out probe)))))

(deftest guest-runs-both-log-capabilities-on-browser-wasm-typedCapCall
  (let [probe (node-probe
               (compiled-browser)
               (str inject-js
                    "const h=await m.instantiateKotoba(Buffer.from(process.argv[1],'base64'),{"
                    "allowCapabilities:[5,6],"
                    "typedCapCall:(id,request,contract)=>logInject(id,request,contract)});"
                    "if(!h.typedAbi.contracts.has(6))process.exit(22);"
                    "if(!h.typedAbi.contracts.has(5))process.exit(23);"
                    "const x=h.instance.exports;"
                    "if(x.emit('ready')!==5n)process.exit(2);"
                    "if(x.tail(5n)!==9n)process.exit(3);"
                    "if(x.stale(5n)!==1n)process.exit(4);"))]
    (is (zero? (:exit probe)) (str (:err probe) \newline (:out probe)))))

(deftest wasm-log-without-its-grant-is-denied
  (let [probe (node-probe
               (compiled-browser)
               (str "const h=await m.instantiateKotoba(Buffer.from(process.argv[1],'base64'),{"
                    "allowCapabilities:[],"
                    "typedCapCall:()=>process.exit(2)});"
                    "try{h.instance.exports.emit('ready');process.exit(3)}"
                    "catch(e){if(e.code!=='capability-denied')process.exit(4)}"))]
    (is (zero? (:exit probe)) (:err probe))))

(deftest forged-scalar-log-result-is-rejected
  "A bare i64 is not an append-result record even though the record's one
  field is an i64. Without result admission this would silently pass."
  (let [probe (node-probe
               (compiled-browser)
               (str "const h=await m.instantiateKotoba(Buffer.from(process.argv[1],'base64'),{"
                    "allowCapabilities:[5,6],typedCapCall:()=>5n});"
                    "try{h.instance.exports.emit('ready');process.exit(2)}"
                    "catch(e){if(e.code!=='invalid-typed-value')process.exit(3)}"))]
    (is (zero? (:exit probe)) (:err probe))))

(deftest native-aot-target-still-refuses-this-kit
  "Records the measured reason :native-aot is :pending, so the gap cannot be
  mistaken for a backend nobody tried."
  (let [target (if (contains? #{"aarch64" "arm64"}
                              (.toLowerCase (System/getProperty "os.arch")))
                 :aarch64-kotoba-v1
                 :x86_64-kotoba-v1)
        thrown (try (compiler/compile-source guest-source target policy)
                    nil
                    (catch clojure.lang.ExceptionInfo e e))]
    (is (some? thrown) "native backend unexpectedly admitted a set-valued kit")
    (is (= :target (:phase (ex-data thrown))))
    (is (= :kotoba.value/typed-v1 (:value-profile (ex-data thrown))))
    (is (= :pending (:native-aot (:qualification (load-kit)))))))

(deftest log-kit-wasm-aot-surface-matches-what-the-compiler-elaborates
  (let [kit (load-kit)
        q (:qualification kit)
        surface (:wasm-aot-surface kit)
        grants (:grants surface)]
    (is (= :implemented (:reference q)))
    (is (= :implemented (:wasm-aot q)))
    (is (= :pending (:wasm32-kotoba-v1 q))
        "i64 kotoba:cap/call is not this kit ABI")
    (is (= :pending (:native-aot q)))
    (is (= :implemented (:jit q)))
    (is (= ["kotoba:typed" "cap-call"] (:import surface)))
    (is (= :wasm32-browser-kotoba-v1 (:target surface)))
    (is (= 2 (count grants)) "both capabilities carry a surface")
    (is (= #{6 5} (set (map :capability-id grants))))
    (is (= #{:log/append :log/read} (set (map :grant grants))))
    (is (= (set (map (juxt :name :id) (:capabilities kit)))
           (set (map (juxt :grant :capability-id) grants)))
        "surface grants agree with the kit's declared capability ids")
    (doseq [{:keys [grant elaboration]} grants]
      (is (= (str "(typed-cap-call " grant " request-type result-type request)")
             elaboration)))))
