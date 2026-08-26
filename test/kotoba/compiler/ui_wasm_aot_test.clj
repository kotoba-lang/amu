(ns kotoba.compiler.ui-wasm-aot-test
  "Named :ui/commit and :ui/next-event compile to wasm32 and run on the typed
  browser host. The inject is typedCapCall -- the same seam log's and
  dataspace's wasm proofs use -- not a JVM provider.ui inside V8.

  :wasm-aot names that typed kit ABI (kotoba:typed/cap-call, ids 9 and 10).
  It is not clock's i64 kotoba:cap/call surface (:wasm32-kotoba-v1), and
  `module-imports-the-typed-seam-and-not-the-i64-one` is what separates the
  two claims: the compiled module has no kotoba:cap/call import at all.

  Two capabilities, so the kit's :wasm-aot-surface is per grant, as log's is.
  Both ids are proved here; proving only :ui/commit would leave
  :ui/next-event claimed and unmeasured.

  Unlike log, this kit's second wire answers with an [:option record]. The
  host has to carry the present/absent discriminant, not just a payload, so
  `poll` (some) and `pending` (none) are both exported and both asserted --
  an inject stuck on either answer fails one of them.

  :native-aot is proved by kotoba.compiler.ui-native-aot-test on a real
  kexe process, the same way dataspace was qualified.

  Break: return a bare 5n from the commit inject instead of the sealed
  record and `guest-runs-both-ui-capabilities` fails on result admission."
  (:require [clojure.edn :as edn]
            [clojure.java.io :as io]
            [clojure.java.shell :as shell]
            [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]
            [provider.ui :as ui]))

(def policy {:allow #{[:cap/call 9] [:cap/call 10]}})

(def guest-source
  (let [creq (pr-str ui/commit-request-type)
        cres (pr-str ui/commit-result-type)
        ereq (pr-str ui/event-request-type)
        eres (pr-str ui/event-result-type)
        nset (pr-str ui/node-set-type)
        node (pr-str ui/node-type)
        parent (pr-str ui/parent-type)
        evt (pr-str ui/event-type)
        commit (fn [] (str "(typed-cap-call :ui/commit " creq " " cres
                           "  (record-new " creq " base"
                           "    (typed-set-conj " nset " (typed-set-new " nset ")"
                           "      (record-new " node " :view/title"
                           "        (option-none-of " parent ") :ui/text text))))"))
        poll (fn [] (str "(typed-cap-call :ui/next-event " ereq " " eres
                         "  (record-new " ereq " after))"))]
    (str "(ns app.ui (:export [main rev size poll pending])"
         " (:capabilities #{:ui/commit :ui/next-event}))"
         "(defn main [] 0)"
         "(defn rev [base :i64 text :string] :i64"
         "  (record-get " cres " " (commit) " :revision))"
         "(defn size [base :i64 text :string] :i64"
         "  (record-get " cres " " (commit) " :node-count))"
         "(defn poll [after :i64] :i64"
         "  (option-match " eres " " (poll)
         "    0 e (record-get " evt " e :revision)))"
         "(defn pending [after :i64] :i64"
         "  (option-match " eres " " (poll) " 1 e 0))")))

(defn- load-kit []
  (edn/read-string
   (slurp (io/resource "kotoba/lang/capability-kits/ui-v1.edn"))))

(defn- compiled-browser []
  (compiler/compile-source guest-source :wasm32-browser-kotoba-v1 policy))

(defn- node-probe [compiled javascript]
  (let [encoded (.encodeToString (java.util.Base64/getEncoder)
                                 ^bytes (:bytes compiled))
        probe (str "import('./runtime/browser-host.mjs').then(async m=>{"
                   javascript
                   "}).catch(e=>{console.error(e);process.exit(70)})")]
    (shell/sh "node" "--input-type=module" "-e" probe encoded)))

;; commit (9) answers with a sealed commit-result whose two i64 fields are
;; DERIVED from the request the guest sent -- base-revision + 1 and the size
;; of the node set -- so a guest that dropped either argument cannot earn the
;; expected answer. next-event (10) answers with the [:option event] the kit
;; declares: some below revision 9, none at or above it, which is what makes
;; `poll` and `pending` two different assertions rather than one repeated.
(def inject-js
  (str "function uiInject(id,request,contract){"
       "const result=contract.result;"
       "if(id===9){"
       "const nodes=request[2][1];"
       "if(nodes.length!==1)process.exit(30);"
       "if(nodes[0][1]!==':view/title')process.exit(31);"
       "if(nodes[0][2][1]!==false)process.exit(32);"
       "if(nodes[0][3]!==':ui/text')process.exit(33);"
       "if(nodes[0][4]!=='ready')process.exit(34);"
       "return [result,request[1]+1n,BigInt(nodes.length)]}"
       "if(id===10){"
       "const event=result[1];"
       "if(request[1]>=9n)return [result,false];"
       "return [result,true,[event,request[1]+3n,':view/title',':ui/click','open']]}"
       "process.exit(20)}"))

(deftest named-ui-guest-compiles-to-both-wasm32-targets
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

(deftest guest-runs-both-ui-capabilities-on-browser-wasm-typedCapCall
  (let [probe (node-probe
               (compiled-browser)
               (str inject-js
                    "const h=await m.instantiateKotoba(Buffer.from(process.argv[1],'base64'),{"
                    "allowCapabilities:[9,10],"
                    "typedCapCall:(id,request,contract)=>uiInject(id,request,contract)});"
                    "if(!h.typedAbi.contracts.has(9))process.exit(22);"
                    "if(!h.typedAbi.contracts.has(10))process.exit(23);"
                    "const x=h.instance.exports;"
                    "if(x.rev(0n,'ready')!==1n)process.exit(2);"
                    "if(x.rev(6n,'ready')!==7n)process.exit(3);"
                    "if(x.size(0n,'ready')!==1n)process.exit(4);"
                    "if(x.poll(1n)!==4n)process.exit(5);"
                    "if(x.pending(1n)!==0n)process.exit(6);"
                    "if(x.poll(9n)!==0n)process.exit(7);"
                    "if(x.pending(9n)!==1n)process.exit(8);"))]
    (is (zero? (:exit probe)) (str (:err probe) \newline (:out probe)))))

(deftest wasm-ui-without-its-grant-is-denied
  (let [probe (node-probe
               (compiled-browser)
               (str "const h=await m.instantiateKotoba(Buffer.from(process.argv[1],'base64'),{"
                    "allowCapabilities:[],"
                    "typedCapCall:()=>process.exit(2)});"
                    "try{h.instance.exports.rev(0n,'ready');process.exit(3)}"
                    "catch(e){if(e.code!=='capability-denied')process.exit(4)}"
                    "try{h.instance.exports.poll(1n);process.exit(5)}"
                    "catch(e){if(e.code!=='capability-denied')process.exit(6)}"))]
    (is (zero? (:exit probe)) (:err probe))))

(deftest forged-scalar-ui-results-are-rejected
  "A bare i64 is not a commit-result record even though both of that record's
  fields are i64, and it is not an [:option event] either. Without result
  admission both of these would silently pass."
  (let [probe (node-probe
               (compiled-browser)
               (str "const h=await m.instantiateKotoba(Buffer.from(process.argv[1],'base64'),{"
                    "allowCapabilities:[9,10],typedCapCall:()=>5n});"
                    "try{h.instance.exports.rev(0n,'ready');process.exit(2)}"
                    "catch(e){if(e.code!=='invalid-typed-value')process.exit(3)}"
                    "try{h.instance.exports.poll(1n);process.exit(4)}"
                    "catch(e){if(e.code!=='invalid-typed-value')process.exit(5)}"))]
    (is (zero? (:exit probe)) (:err probe))))

(deftest ui-kit-wasm-aot-surface-matches-what-the-compiler-elaborates
  (let [kit (load-kit)
        q (:qualification kit)
        surface (:wasm-aot-surface kit)
        grants (:grants surface)]
    (is (= :implemented (:reference q)))
    (is (= :implemented (:wasm-aot q)))
    (is (= :pending (:wasm32-kotoba-v1 q))
        "i64 kotoba:cap/call is not this kit ABI")
    (is (= :implemented (:native-aot q)))
    (is (= :implemented (:jit q)))
    (is (= ["kotoba:typed" "cap-call"] (:import surface)))
    (is (= :wasm32-browser-kotoba-v1 (:target surface)))
    (is (= 2 (count grants)) "both capabilities carry a surface")
    (is (= #{9 10} (set (map :capability-id grants))))
    (is (= #{:ui/commit :ui/next-event} (set (map :grant grants))))
    (is (= (set (map (juxt :name :id) (:capabilities kit)))
           (set (map (juxt :grant :capability-id) grants)))
        "surface grants agree with the kit's declared capability ids")
    (doseq [{:keys [grant elaboration]} grants]
      (is (= (str "(typed-cap-call " grant " request-type result-type request)")
             elaboration)))))
