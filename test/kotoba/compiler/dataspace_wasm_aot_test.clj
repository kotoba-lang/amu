(ns kotoba.compiler.dataspace-wasm-aot-test
  "Named :dataspace/transact compiles to wasm32 and runs on the typed
  browser host. The inject is typedCapCall — the same seam http's wasm
  proof uses — not JVM provider.dataspace inside V8.

  :wasm-aot names that typed kit ABI (kotoba:typed/cap-call, id 24).
  It is not clock's i64 kotoba:cap/call surface (:wasm32-kotoba-v1).
  :native-aot / :jit stay pending. Matcher stays .cljc (:document is
  not a native-word type in kotoba-kir)."
  (:require [clojure.edn :as edn]
            [clojure.java.io :as io]
            [clojure.java.shell :as shell]
            [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]
            [kotoba.compiler.reference-runtime :as runtime]
            [kotoba.kir :as ir]
            [provider.dataspace :as dataspace]))

(def sugar-source
  (str "(ns app.ds (:export [main publish-edn subscribe-edn enter leave])"
       " (:capabilities #{:dataspace/transact}))"
       "(defn main [] 0)"
       "(defn publish-edn [s :string] (assert! (document-edn-read s)))"
       "(defn subscribe-edn [s :string] (observe! (document-edn-read s)))"
       "(defn enter [] (facet-enter!))"
       "(defn leave [facet :i64] (facet-leave! facet))"))

(def coord-source
  (str "(ns app.dataspace (:export [main coord])"
       " (:capabilities #{:dataspace/transact}))"
       "(defn main [] 0)"
       "(defn coord [request " (pr-str dataspace/request-type) "] "
       (pr-str dataspace/result-type)
       " (typed-cap-call :dataspace/transact "
       (pr-str dataspace/request-type) " "
       (pr-str dataspace/result-type) " request))"))

(def policy {:allow #{[:cap/call 24]}})

(defn- load-kit []
  (edn/read-string
   (slurp (io/resource "kotoba/lang/capability-kits/dataspace-v1.edn"))))

(defn- node-probe [compiled javascript]
  (let [encoded (.encodeToString (java.util.Base64/getEncoder)
                                 ^bytes (:bytes compiled))
        probe (str "import('./runtime/browser-host.mjs').then(async m=>{"
                   javascript
                   "}).catch(e=>{console.error(e);process.exit(70)})")]
    (shell/sh "node" "--input-type=module" "-e" probe encoded)))

(def inject-js
  (str "function dataspaceInject(values){"
       "let next=1n;const live=new Set([0n]);"
       "return (id,request,contract)=>{"
       "if(id!==24)process.exit(20);"
       "const result=contract.result;"
       "const rec=name=>result[2].find(([n])=>n===name)[1];"
       "const record=(name,...fields)=>[rec(name),...fields];"
       "const empty=values.document(['vector',[]]);"
       "const tag=request[1];"
       "if(tag===':facet-enter'){const fid=next++;live.add(fid);"
       "return [result,':facet',record(':facet',fid)]}"
       "if(tag===':facet-leave'){const fid=request[2];"
       "if(!live.has(fid)||fid===0n)"
       "return [result,':error',record(':error',':dataspace/unknown-facet','unknown facet')];"
       "live.delete(fid);return [result,':retracted',record(':retracted',1n)]}"
       "if(tag===':observe'){const matches=rec(':matches');"
       "const payload=[matches,empty];if(matches[2].length>1)payload.push(empty);"
       "return [result,':matches',payload]}"
       "if(tag===':assert'){const asserted=rec(':asserted');"
       "const payload=[asserted,1n];if(asserted[2].length>1)payload.push(empty);"
       "return [result,':asserted',payload]}"
       "if(tag===':retract')return [result,':retracted',record(':retracted',1n)];"
       "process.exit(21)}}"))

(deftest named-dataspace-guest-compiles-to-both-wasm32-targets
  (doseq [target [:wasm32-browser-kotoba-v1 :wasm32-kotoba-v1]]
    (testing (str target)
      (let [compiled (compiler/compile-source sugar-source target policy)]
        (is (= :wasm/v1 (:format compiled)))
        (is (= :kotoba.typed/externref-v1 (:value-abi compiled)))
        (is (pos? (alength ^bytes (:bytes compiled))))))))

(deftest kit-abi-coord-guest-compiles-to-wasm32-browser
  (let [compiled (compiler/compile-source coord-source
                                          :wasm32-browser-kotoba-v1 policy)]
    (is (= :wasm/v1 (:format compiled)))
    (is (pos? (alength ^bytes (:bytes compiled))))))

(deftest named-dataspace-guest-runs-on-browser-wasm-typedCapCall
  (let [compiled (compiler/compile-source sugar-source
                                          :wasm32-browser-kotoba-v1 policy)
        probe (node-probe
               compiled
               (str inject-js
                    "let values,inject;"
                    "const h=await m.instantiateKotoba(Buffer.from(process.argv[1],'base64'),{"
                    "allowCapabilities:[24],"
                    "typedCapCall:(id,request,contract)=>inject(id,request,contract)});"
                    "values=h.typedValues;inject=dataspaceInject(values);"
                    "if(!h.typedAbi.contracts.has(24))process.exit(22);"
                    "const x=h.instance.exports;"
                    "const entered=x.enter();"
                    "if(entered[1]!==':facet'||entered[2][1]!==1n)process.exit(2);"
                    "const unknown=x.leave(99n);"
                    "if(unknown[1]!==':error'||unknown[2][1]!==':dataspace/unknown-facet')process.exit(3);"
                    "if(x['subscribe-edn']('[:temperature :room/a ?t]')[1]!==':matches')process.exit(4);"
                    "const asserted=x['publish-edn']('[:temperature :room/a 21]');"
                    "if(asserted[1]!==':asserted'||asserted[2][1]!==1n)process.exit(5);"
                    "if(x.leave(1n)[1]!==':retracted')process.exit(6);"))]
    (is (zero? (:exit probe)) (str (:err probe) \newline (:out probe)))))

(deftest wasm-dataspace-without-allow-24-is-denied
  (let [compiled (compiler/compile-source sugar-source
                                          :wasm32-browser-kotoba-v1 policy)
        probe (node-probe
               compiled
               (str "const h=await m.instantiateKotoba(Buffer.from(process.argv[1],'base64'),{"
                    "allowCapabilities:[],"
                    "typedCapCall:()=>process.exit(2)});"
                    "try{h.instance.exports.enter();process.exit(3)}"
                    "catch(e){if(e.code!=='capability-denied')process.exit(4)}"))]
    (is (zero? (:exit probe)) (:err probe))))

(deftest host-built-dataspace-variant-is-admitted
  "Break: revert cap-call to assertValue (no admitHostResult) and this
  fails with forged compound typed value rejected. Echo-only http still
  passes in that state, so this is the discriminator for kit ABI results."
  (let [compiled (compiler/compile-source sugar-source
                                          :wasm32-browser-kotoba-v1 policy)
        probe (node-probe
               compiled
               (str inject-js
                    "let values,inject;"
                    "const h=await m.instantiateKotoba(Buffer.from(process.argv[1],'base64'),{"
                    "allowCapabilities:[24],"
                    "typedCapCall:(id,request,contract)=>inject(id,request,contract)});"
                    "values=h.typedValues;inject=dataspaceInject(values);"
                    "try{h.instance.exports.enter()}catch(e){"
                    "if(String(e.message||e).includes('forged'))process.exit(2);"
                    "process.exit(3)}"))]
    (is (zero? (:exit probe)) (:err probe))))

(deftest forged-scalar-dataspace-result-is-rejected
  (let [compiled (compiler/compile-source sugar-source
                                          :wasm32-browser-kotoba-v1 policy)
        probe (node-probe
               compiled
               (str "const h=await m.instantiateKotoba(Buffer.from(process.argv[1],'base64'),{"
                    "allowCapabilities:[24],typedCapCall:()=>7n});"
                    "try{h.instance.exports.enter();process.exit(2)}"
                    "catch(e){if(e.code!=='invalid-typed-value')process.exit(3)}"))]
    (is (zero? (:exit probe)) (:err probe))))

(deftest coord-guest-runs-against-jvm-provider-host
  "Kit-ABI coord guest still runs on JVM provider. Sugar observe!
  notices delivery is proved in dataspace-provider-test against
  kotoba-sema f4de940e (includes 91eff5a :notices)."
  (let [kir (ir/lower (:hir (compiler/check-source coord-source policy)))
        runtime (runtime/instantiate kir {:allow #{24}
                                          :providers {24 (dataspace/provider)}})
        entered ((:invoke runtime) 'coord
                 [[dataspace/request-type :facet-enter true]])
        unknown ((:invoke runtime) 'coord
                 [[dataspace/request-type :facet-leave 99]])]
    (is (= :kotoba.kir/v4 (:format kir)))
    (is (= :facet (second entered)))
    (is (pos? (last (nth entered 2))))
    (is (= :error (second unknown)))
    (is (= :dataspace/unknown-facet (second (nth unknown 2))))))

(deftest dataspace-kit-wasm-aot-is-the-typed-browser-surface
  (let [kit (load-kit)
        q (:qualification kit)
        surface (:wasm-aot-surface kit)]
    (is (= :implemented (:reference q)))
    (is (= :implemented (:wasm-aot q)))
    (is (= :pending (:wasm32-kotoba-v1 q))
        "i64 kotoba:cap/call is not this kit ABI")
    (is (= :pending (:native-aot q)))
    (is (= :pending (:jit q)))
    (is (= ["kotoba:typed" "cap-call"] (:import surface)))
    (is (= 24 (:capability-id surface)))
    (is (= :dataspace/transact (:grant surface)))
    (is (= :wasm32-browser-kotoba-v1 (:target surface)))))
