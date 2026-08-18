(ns kotoba.compiler.state-wasm-aot-test
  "The state kit's own variant/record ABI runs on the typed hosts.

  `state-v1` names capability id 8, one capability, `:state/transact`.
  Its :request and :result are :kotoba.state/request and
  :kotoba.state/result -- variants over records carrying :keyword,
  :string and :i64, plus two arms whose whole payload is a bare :bool
  (:missing and :deleted). The bool is the part this kit turns on that
  storage's option did not: `erase` returns 1 or 0 purely from the
  :deleted payload, so a host that dropped or widened that bool could
  not produce the 1/0 alternation the round trip asserts.

  The record shapes are this kit's, not storage's: state's :put record
  is [key value] where storage's is [key value expected-version], and
  state's :delete is [key] where storage's is [key expected-version].
  The inject counts those arities, so a schema copied from the
  neighbouring kit exits rather than passing.

  :wasm-aot names the typed kit ABI (kotoba:typed/cap-call, id 8) on
  :wasm32-browser-kotoba-v1, the same seam storage-wasm-aot-test and
  dataspace-wasm-aot-test use. It is not clock's i64 kotoba:cap/call
  surface, which is what :wasm32-kotoba-v1 means (ADR 0084 / 0257) --
  this guest does compile to :wasm32-kotoba-v1, but compiling to a
  target is not the same claim as running on that target's host-time
  surface, so that key stays :pending.

  :jit is the existing kotoba-script :js-kotoba-v1 path under V8.

  :native-aot stays :pending and native-aot-refuses-the-state-kit-abi
  measures WHY rather than assuming it. dataspace IS qualified on
  native, so native is not categorically closed to kits; state is
  refused for a reason the test records -- see that test's docstring
  for the exact ex-data. Nothing in src/ reads :qualification, so the
  only thing keeping that map honest is this namespace.

  Breaks, measured 2026-08-18 -- control exits 0, each break exits
  non-zero, and the reported failure is the one that was broken:

    guest reads the :deleted bool as (if d 1 0) -> constant 1   exit 3
    host returns :deleted true for a missing key                exit 3
    host returns a bare 0n/1n instead of the :deleted bool      exit 70 invalid-typed-value
    host returns a storage-shaped 3-field :delete record        (guest cannot build it; inject arity check exits 27)
    host never reaches typedCapCall                             exit 31
    kit flips :wasm-aot back to :pending                        1 failure, named
    kit surface :import becomes kotoba:cap                      1 failure, named

  The bool breaks are the ones worth keeping: they are what shows the
  :deleted payload really crosses rather than being reconstructed
  guest-side, and the never-reached break is what shows this runs
  through typedCapCall at all."
  (:require [clojure.edn :as edn]
            [clojure.java.io :as io]
            [clojure.java.shell :as shell]
            [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]
            [provider.state :as state]))

(def policy {:allow #{[:cap/call 8]}})

(def guest-source
  (let [req (pr-str state/request-type)
        res (pr-str state/result-type)
        put (pr-str state/put-type)
        get-rec (pr-str state/get-type)
        del (pr-str state/delete-type)
        entry (pr-str state/entry-type)
        err (pr-str state/error-type)]
    (str "(ns app.state (:export [main store fetch erase])"
         " (:capabilities #{:state/transact}))"
         "(defn main [] 0)"
         ;; :put -- the written version comes back out of the entry record.
         "(defn store [value :string] :i64"
         " (variant-match " res
         "  (typed-cap-call :state/transact " req " " res
         "    (variant-new " req " :put"
         "      (record-new " put " :profile/name value)))"
         "  [[:found e (record-get " entry " e :version)]"
         "   [:missing m -1]"
         "   [:written w (record-get " entry " w :version)]"
         "   [:deleted d -2]"
         "   [:error x -4]]))"
         ;; :get -- :missing and :found are different arms of the same variant,
         ;; and :error's record carries the string this arm returns.
         "(defn fetch [] :string"
         " (variant-match " res
         "  (typed-cap-call :state/transact " req " " res
         "    (variant-new " req " :get (record-new " get-rec " :profile/name)))"
         "  [[:found e (record-get " entry " e :value)]"
         "   [:missing m \"\"]"
         "   [:written w (record-get " entry " w :value)]"
         "   [:deleted d \"\"]"
         "   [:error x (record-get " err " x :message)]]))"
         ;; :delete -- the WHOLE payload of the :deleted arm is a bare :bool.
         ;; 1 vs 0 is decided by that bool and by nothing else the guest knows.
         "(defn erase [] :i64"
         " (variant-match " res
         "  (typed-cap-call :state/transact " req " " res
         "    (variant-new " req " :delete (record-new " del " :profile/name)))"
         "  [[:found e -1]"
         "   [:missing m -1]"
         "   [:written w -1]"
         "   [:deleted d (if d 1 0)]"
         "   [:error x -4]]))")))

(defn- load-kit []
  (edn/read-string
   (slurp (io/resource "kotoba/lang/capability-kits/state-v1.edn"))))

;; One in-memory cell. Records are [type field0 field1 ...], so a record's
;; first field is at index 1. The :deleted / :missing arms carry a bare
;; JS boolean, which is the whole payload of those arms.
;;
;; The arity checks are this kit's schema and not storage's: state's :put
;; record is [key value] (length 3 with the descriptor) and :get / :delete
;; are [key] (length 2). Storage's would be 4 and 3.
(defn- inject-body [request-expr]
  (str "const result=contract.result;"
       "const rec=name=>result[2].find(([n])=>n===name)[1];"
       "const record=(name,...fields)=>[rec(name),...fields];"
       "const request=" request-expr ";"
       "const tag=request[1];const payload=request[2];"
       "if(tag===':put'){if(payload.length!==3)process.exit(25);"
       "cell.value=payload[2];cell.version+=1n;"
       "return [result,':written',"
       "record(':written',payload[1],cell.value,cell.version)];}"
       "if(tag===':get'){if(payload.length!==2)process.exit(26);"
       "if(cell.value===null)return [result,':missing',false];"
       "return [result,':found',"
       "record(':found',payload[1],cell.value,cell.version)];}"
       "if(tag===':delete'){if(payload.length!==2)process.exit(27);"
       "const present=cell.value!==null;cell.value=null;"
       "return [result,':deleted',present];}"
       "process.exit(21);"))

;; The browser host passes (id, request, contract); kotoba-script passes
;; (request, contract). Same body, two arities.
(def wasm-inject-js
  (str "const cell={version:0n,value:null};"
       "function stateInject(id,rawRequest,contract){"
       "if(id!==8)process.exit(20);"
       (inject-body "rawRequest")
       "}"))

(def jit-inject-js
  (str "const cell={version:0n,value:null};"
       "function stateInject(rawRequest,contract){"
       (inject-body "rawRequest")
       "}"))

(defn- node-probe [compiled javascript]
  (let [encoded (.encodeToString (java.util.Base64/getEncoder)
                                 ^bytes (:bytes compiled))
        probe (str "import('./runtime/browser-host.mjs').then(async m=>{"
                   javascript
                   "}).catch(e=>{console.error(e);process.exit(70)})")]
    (shell/sh "node" "--input-type=module" "-e" probe encoded)))

;; erase on an absent key -> 0, erase on a present key -> 1. Both answers
;; come out of the :deleted arm's bare :bool and nowhere else, so a host
;; that lost that payload cannot produce the alternation.
(def ^:private round-trip-js
  (str "const x=h.instance.exports;"
       "if(x.fetch()!=='')process.exit(2);"
       "if(x.erase()!==0n)process.exit(3);"
       "if(x.store('Kotoba')!==1n)process.exit(4);"
       "if(x.store('Kotoba2')!==2n)process.exit(5);"
       "if(x.fetch()!=='Kotoba2')process.exit(6);"
       "if(x.erase()!==1n)process.exit(7);"
       "if(x.fetch()!=='')process.exit(8);"
       "if(x.erase()!==0n)process.exit(9);"))

(deftest state-guest-compiles-to-both-wasm32-targets
  (doseq [target [:wasm32-browser-kotoba-v1 :wasm32-kotoba-v1]]
    (testing (str target)
      (let [compiled (compiler/compile-source guest-source target policy)]
        (is (= :wasm/v1 (:format compiled)))
        (is (= :kotoba.typed/externref-v1 (:value-abi compiled)))
        (is (pos? (alength ^bytes (:bytes compiled))))))))

(deftest state-guest-runs-on-browser-wasm-typedCapCall
  (let [compiled (compiler/compile-source guest-source
                                          :wasm32-browser-kotoba-v1 policy)
        probe (node-probe
               compiled
               (str wasm-inject-js
                    "const h=await m.instantiateKotoba(Buffer.from(process.argv[1],'base64'),{"
                    "allowCapabilities:[8],"
                    "typedCapCall:(id,request,contract)=>stateInject(id,request,contract)});"
                    "if(!h.typedAbi.contracts.has(8))process.exit(22);"
                    round-trip-js))]
    (is (zero? (:exit probe)) (str (:err probe) \newline (:out probe)))))

(deftest wasm-state-without-allow-8-is-denied
  (let [compiled (compiler/compile-source guest-source
                                          :wasm32-browser-kotoba-v1 policy)
        probe (node-probe
               compiled
               (str "const h=await m.instantiateKotoba(Buffer.from(process.argv[1],'base64'),{"
                    "allowCapabilities:[],"
                    "typedCapCall:()=>process.exit(2)});"
                    "try{h.instance.exports.fetch();process.exit(3)}"
                    "catch(e){if(e.code!=='capability-denied')process.exit(4)}"))]
    (is (zero? (:exit probe)) (:err probe))))

(deftest forged-scalar-state-result-is-rejected
  (let [compiled (compiler/compile-source guest-source
                                          :wasm32-browser-kotoba-v1 policy)
        probe (node-probe
               compiled
               (str "const h=await m.instantiateKotoba(Buffer.from(process.argv[1],'base64'),{"
                    "allowCapabilities:[8],typedCapCall:()=>7n});"
                    "try{h.instance.exports.fetch();process.exit(2)}"
                    "catch(e){if(e.code!=='invalid-typed-value')process.exit(3)}"))]
    (is (zero? (:exit probe)) (:err probe))))

(deftest jit-state-guest-round-trips-on-kotoba-script-v8
  (let [compiled (compiler/compile-source guest-source :js-kotoba-v1 policy)
        encoded (.encodeToString (java.util.Base64/getEncoder)
                                 (.getBytes ^String (:source compiled) "UTF-8"))
        js (str jit-inject-js
                "import('data:text/javascript;base64," encoded
                "').then(m=>{const x=m.instantiateKotoba({8:stateInject});"
                "if(x.fetch()!=='')process.exit(2);"
                "if(x.erase()!==0n)process.exit(3);"
                "if(x.store('Kotoba')!==1n)process.exit(4);"
                "if(x.store('Kotoba2')!==2n)process.exit(5);"
                "if(x.fetch()!=='Kotoba2')process.exit(6);"
                "if(x.erase()!==1n)process.exit(7);"
                "if(x.fetch()!=='')process.exit(8);"
                "if(x.erase()!==0n)process.exit(9)})")
        probe (shell/sh "node" "--input-type=module" "-e" js)]
    (is (string? (:source compiled)))
    (is (zero? (:exit probe)) (str (:err probe) \newline (:out probe)))))

(deftest native-aot-refuses-the-state-kit-abi
  "Why :native-aot is :pending, measured rather than assumed, on all four
  native targets.

    \"typed values currently require the kotoba-script web target, typed
     Wasm/CLJS target, or the qualified native one-word
     string/record/variant/option/result slice\"
    {:phase :target :target <target> :backend <backend>
     :value-profile :kotoba.value/typed-v1}

  dataspace-v1 IS qualified on native, so native is not categorically
  closed to kits. It is closed to THIS one because
  kotoba.kir/only-native-word-typed-features? admits a typed-cap-call only
  when its [request result] pair is one of [:i64 :i64] / [:string :string]
  / [:option-i64 :option-i64] / [:result-i64 :result-i64], or when
  native-provider-contract? matches -- and that predicate is a two-entry
  allowlist naming capability 7 (clock) and capability 24 (dataspace) with
  their exact schemas. Capability 8 is in neither set, so no rewriting of
  this guest reaches native while the kit's own variant request/result is
  what crosses."
  (doseq [target [:x86_64-kotoba-v1 :aarch64-kotoba-v1
                  :x86_64-macos-kotoba-v1 :aarch64-macos-kotoba-v1]]
    (testing (str target)
      (let [thrown (try (compiler/compile-source guest-source target policy)
                        nil
                        (catch clojure.lang.ExceptionInfo e e))]
        (is (some? thrown) "native must not silently accept the kit ABI")
        (is (= :target (:phase (ex-data thrown))))
        (is (= target (:target (ex-data thrown))))
        (is (= :kotoba.value/typed-v1 (:value-profile (ex-data thrown))))))))

(deftest state-kit-wasm-aot-is-the-typed-browser-surface
  (let [kit (load-kit)
        q (:qualification kit)
        surface (:wasm-aot-surface kit)]
    (is (= :implemented (:reference q)))
    (is (= :implemented (:wasm-aot q)))
    (is (= :pending (:wasm32-kotoba-v1 q))
        "i64 kotoba:cap/call is not this kit ABI")
    (is (= :pending (:native-aot q))
        "native-aot-refuses-the-state-kit-abi is why")
    (is (= :implemented (:jit q)))
    (is (= ["kotoba:typed" "cap-call"] (:import surface)))
    (is (= 8 (:capability-id surface)))
    (is (= (:id (:capability kit)) (:capability-id surface)))
    (is (= :state/transact (:grant surface)))
    (is (= (:name (:capability kit)) (:grant surface)))
    (is (= :wasm32-browser-kotoba-v1 (:target surface)))
    (is (= "(typed-cap-call :state/transact request-type result-type request)"
           (:elaboration surface)))))

(deftest state-surface-names-the-kits-own-schemas
  "The surface must name THIS kit's request/result, not a shape copied from
  another kit. Both are read straight back out of the kit's own :request and
  :result, and the provider the reference path uses agrees with them."
  (let [kit (load-kit)
        surface (:wasm-aot-surface kit)]
    (is (= (second (:request kit)) (:request-schema surface)))
    (is (= (second (:result kit)) (:result-schema surface)))
    (is (= :kotoba.state/request (:request-schema surface)))
    (is (= :kotoba.state/result (:result-schema surface)))
    (is (= state/request-type (:request kit)))
    (is (= state/result-type (:result kit)))))
