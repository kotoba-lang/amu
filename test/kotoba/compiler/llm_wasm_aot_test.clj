(ns kotoba.compiler.llm-wasm-aot-test
  "The llm kit's own record/variant ABI runs on the typed browser host.

  `llm-v1` names one capability, :llm/generate, id 11. Its :request and
  :result are :kotoba.llm/generate-request and :kotoba.llm/result, and the
  provider git dep is the same pair -- provider.llm/request-type and
  provider.llm/result-type -- so the schema proved here is the kit's own.

  What this kit adds over storage's is depth. Storage's variant arms are
  flat records; llm's :ok arm is a record (:kotoba.llm/completion) that
  itself carries a record (:kotoba.llm/usage). The guest reads
  :input-tokens and :output-tokens back out of that inner record, and the
  inject answers with two different numbers, so a host that flattened or
  dropped the nested record could not produce both 11 and 42.

  No model is called. The kit's semantics say :execution
  :synchronous-reference with host-owned credentials; an actual provider
  transport is nondeterministic and would prove nothing about the ABI.
  The host inject here returns fixed values and asserts all five request
  fields, so what is measured is the seam, not a model.

  :wasm-aot names the typed kit ABI (kotoba:typed/cap-call, id 11) on
  :wasm32-browser-kotoba-v1. It is not clock's i64 kotoba:cap/call
  surface, which is what :wasm32-kotoba-v1 means -- this guest does
  compile to :wasm32-kotoba-v1, but compiling to a target is not the same
  claim as running on that target's host-time surface, so that key stays
  :pending. `module-imports-the-typed-seam-and-not-the-i64-one` is the
  discriminator: the compiled module has no kotoba:cap/call import at all.

  :jit is the kotoba-script :js-kotoba-v1 path under node's V8.

  :native-aot stays :pending and `native-aot-refuses-the-llm-kit-abi`
  measures WHY rather than assuming it: all four native targets reject
  this guest at :phase :target with :value-profile :kotoba.value/typed-v1.
  Nothing in src/ reads :qualification, so this namespace is the only
  thing keeping that map honest.

  Breaks, measured 2026-08-18 -- control is 0 failures/0 errors, each
  break is non-zero, and the reported failure is the one that was broken:

    guest reads :input-tokens where it read :output-tokens  exit 4
    inject flattens usage to a bare i64 (drops inner record) exit 70
      invalid-typed-value -- the nested record really crosses
    inject answers :ok where the guest asked for :error       exit 6
    inject never reaches typedCapCall (host returns nothing)  exit 70
    kit flips :wasm-aot back to :pending    1 failure, named
    kit surface :capability-id becomes 12   2 failures, both named
    kit surface :import becomes kotoba:cap  1 failure, named

  The nested-record break is the one worth keeping: it is what shows
  :kotoba.llm/usage crosses the seam as a record rather than being
  reconstructed guest-side."
  (:require [clojure.edn :as edn]
            [clojure.java.io :as io]
            [clojure.java.shell :as shell]
            [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]
            [provider.llm :as llm]))

(def policy {:allow #{[:cap/call 11]}})

;; Every guest export issues the same typed-cap-call and differs only in
;; what it reads back out, so a single inject answers all of them and the
;; export that fails names the field that did not cross.
(def guest-source
  (let [req (pr-str llm/request-type)
        res (pr-str llm/result-type)
        completion (pr-str llm/completion-type)
        usage (pr-str llm/usage-type)
        err (pr-str llm/error-type)
        call (str "(typed-cap-call :llm/generate " req " " res
                  "  (record-new " req " :model/fixture \"be terse\""
                  "    prompt 256 700))")]
    (str "(ns app.llm (:export [main ask out-tokens in-tokens retryable])"
         " (:capabilities #{:llm/generate}))"
         "(defn main [] 0)"
         ;; :ok -> the completion's own :text; :error -> the error record's
         ;; :message. Two different records under two different arms.
         "(defn ask [prompt :string] :string"
         " (variant-match " res " " call
         "  [[:ok c (record-get " completion " c :text)]"
         "   [:error e (record-get " err " e :message)]]))"
         ;; The nested record: completion -> :usage -> :output-tokens.
         "(defn out-tokens [prompt :string] :i64"
         " (variant-match " res " " call
         "  [[:ok c (record-get " usage
         "            (record-get " completion " c :usage) :output-tokens)]"
         "   [:error e -1]]))"
         ;; Same nesting, the other inner field, so the two cannot coincide.
         "(defn in-tokens [prompt :string] :i64"
         " (variant-match " res " " call
         "  [[:ok c (record-get " usage
         "            (record-get " completion " c :usage) :input-tokens)]"
         "   [:error e -1]]))"
         ;; A :bool field inside the error record, read through `if`.
         "(defn retryable [prompt :string] :i64"
         " (variant-match " res " " call
         "  [[:ok c -1]"
         "   [:error e (if (record-get " err " e :retryable) 1 0)]]))")))

(defn- load-kit []
  (edn/read-string
   (slurp (io/resource "kotoba/lang/capability-kits/llm-v1.edn"))))

(defn- compiled-browser []
  (compiler/compile-source guest-source :wasm32-browser-kotoba-v1 policy))

;; Fixed host answers -- no transport, no model. The inject asserts all five
;; request fields (a wrong one exits 30-33 rather than answering), then
;; branches on the prompt so both variant arms are reachable from one host.
;; Records are [descriptor field0 ...]; the runtime rebuilds them from the
;; contract descriptor, so the nested usage record has to be supplied as a
;; record and not as a bare i64.
(defn- inject-body [request-expr]
  (str "const result=contract.result;"
       "const arm=n=>result[2].find(([t])=>t===n)[1];"
       "const ok=arm(':ok');const bad=arm(':error');"
       "const usage=ok[2][2][1];"
       "const request=" request-expr ";"
       "if(request[1]!==':model/fixture')process.exit(30);"
       "if(request[2]!=='be terse')process.exit(31);"
       "if(request[4]!==256n)process.exit(32);"
       "if(request[5]!==700n)process.exit(33);"
       "const prompt=request[3];"
       "if(prompt==='boom')"
       "return [result,':error',[bad,':llm/rate-limited','slow down',true]];"
       "return [result,':ok',[ok,'echo: '+prompt,':stop',[usage,11n,42n]]];"))

;; The browser host passes (id, request, contract); kotoba-script passes
;; (request, contract). Same body, two arities.
(def wasm-inject-js
  (str "function llmInject(id,rawRequest,contract){"
       "if(id!==11)process.exit(20);"
       (inject-body "rawRequest")
       "}"))

(def jit-inject-js
  (str "function llmInject(rawRequest,contract){"
       (inject-body "rawRequest")
       "}"))

(defn- node-probe [compiled javascript]
  (let [encoded (.encodeToString (java.util.Base64/getEncoder)
                                 ^bytes (:bytes compiled))
        probe (str "import('./runtime/browser-host.mjs').then(async m=>{"
                   javascript
                   "}).catch(e=>{console.error(e);process.exit(70)})")]
    (shell/sh "node" "--input-type=module" "-e" probe encoded)))

;; :ok text, both nested usage fields (11 and 42 -- distinct, so reading the
;; wrong one is visible), then the :error arm's message, its :retryable bool,
;; and the -1 an :ok answer gives that same export.
(def ^:private round-trip-js
  (str "const x=h.instance.exports;"
       "if(x.ask('hello')!=='echo: hello')process.exit(2);"
       "if(x['out-tokens']('hello')!==42n)process.exit(3);"
       "if(x['in-tokens']('hello')!==11n)process.exit(4);"
       "if(x.ask('boom')!=='slow down')process.exit(5);"
       "if(x.retryable('boom')!==1n)process.exit(6);"
       "if(x.retryable('hello')!==-1n)process.exit(7);"
       "if(x['out-tokens']('boom')!==-1n)process.exit(8);"))

(deftest llm-guest-compiles-to-both-wasm32-targets
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

(deftest llm-guest-runs-on-browser-wasm-typedCapCall
  (let [probe (node-probe
               (compiled-browser)
               (str wasm-inject-js
                    "const h=await m.instantiateKotoba(Buffer.from(process.argv[1],'base64'),{"
                    "allowCapabilities:[11],"
                    "typedCapCall:(id,request,contract)=>llmInject(id,request,contract)});"
                    "if(!h.typedAbi.contracts.has(11))process.exit(22);"
                    round-trip-js))]
    (is (zero? (:exit probe)) (str (:err probe) \newline (:out probe)))))

(deftest wasm-llm-without-allow-11-is-denied
  (let [probe (node-probe
               (compiled-browser)
               (str "const h=await m.instantiateKotoba(Buffer.from(process.argv[1],'base64'),{"
                    "allowCapabilities:[],"
                    "typedCapCall:()=>process.exit(2)});"
                    "try{h.instance.exports.ask('hello');process.exit(3)}"
                    "catch(e){if(e.code!=='capability-denied')process.exit(4)}"))]
    (is (zero? (:exit probe)) (:err probe))))

(deftest forged-scalar-llm-result-is-rejected
  "A bare i64 is not a :kotoba.llm/result variant. Without result admission
  the guest would read fields off whatever the host handed back."
  (let [probe (node-probe
               (compiled-browser)
               (str "const h=await m.instantiateKotoba(Buffer.from(process.argv[1],'base64'),{"
                    "allowCapabilities:[11],typedCapCall:()=>7n});"
                    "try{h.instance.exports.ask('hello');process.exit(2)}"
                    "catch(e){if(e.code!=='invalid-typed-value')process.exit(3)}"))]
    (is (zero? (:exit probe)) (:err probe))))

(deftest jit-llm-guest-round-trips-on-kotoba-script-v8
  (let [compiled (compiler/compile-source guest-source :js-kotoba-v1 policy)
        encoded (.encodeToString (java.util.Base64/getEncoder)
                                 (.getBytes ^String (:source compiled) "UTF-8"))
        js (str jit-inject-js
                "import('data:text/javascript;base64," encoded
                "').then(m=>{const x=m.instantiateKotoba({11:llmInject});"
                "if(x.ask('hello')!=='echo: hello')process.exit(2);"
                "if(x['out-tokens']('hello')!==42n)process.exit(3);"
                "if(x['in-tokens']('hello')!==11n)process.exit(4);"
                "if(x.ask('boom')!=='slow down')process.exit(5);"
                "if(x.retryable('boom')!==1n)process.exit(6);"
                "if(x.retryable('hello')!==-1n)process.exit(7);"
                "if(x['out-tokens']('boom')!==-1n)process.exit(8)})")
        probe (shell/sh "node" "--input-type=module" "-e" js)]
    (is (string? (:source compiled)))
    (is (zero? (:exit probe)) (str (:err probe) \newline (:out probe)))))

(deftest native-aot-refuses-the-llm-kit-abi
  "Why :native-aot is :pending, measured rather than assumed. The refusal is
  the compiler's own word-typed native admission gate, at :phase :target.
  All four native targets are tried so the gap is not one backend's."
  (doseq [target [:x86_64-kotoba-v1 :aarch64-kotoba-v1
                  :x86_64-macos-kotoba-v1 :aarch64-macos-kotoba-v1]]
    (testing (str target)
      (let [thrown (try (compiler/compile-source guest-source target policy)
                        nil
                        (catch clojure.lang.ExceptionInfo e e))]
        (is (some? thrown) "native must not silently accept the kit ABI")
        (is (= :target (:phase (ex-data thrown))))
        (is (= target (:target (ex-data thrown))))
        (is (= :kotoba.value/typed-v1 (:value-profile (ex-data thrown))))))
    (is (= :pending (:native-aot (:qualification (load-kit)))))))

(deftest llm-kit-wasm-aot-is-the-typed-browser-surface
  (let [kit (load-kit)
        q (:qualification kit)
        surface (:wasm-aot-surface kit)]
    (is (= :implemented (:reference q)))
    (is (= :implemented (:wasm-aot q)))
    (is (= :pending (:wasm32-kotoba-v1 q))
        "i64 kotoba:cap/call is not this kit ABI")
    (is (= :pending (:native-aot q))
        "native-aot-refuses-the-llm-kit-abi is why")
    (is (= :implemented (:jit q)))
    (is (= #{:reference :wasm-aot :wasm32-kotoba-v1 :native-aot :jit}
           (set (keys q)))
        "all five qualification keys stay present")
    (is (= ["kotoba:typed" "cap-call"] (:import surface)))
    (is (= 11 (:capability-id surface)))
    (is (= (:id (:capability kit)) (:capability-id surface)))
    (is (= :llm/generate (:grant surface)))
    (is (= (:name (:capability kit)) (:grant surface)))
    (is (= :wasm32-browser-kotoba-v1 (:target surface)))
    (is (= "(typed-cap-call :llm/generate request-type result-type request)"
           (:elaboration surface)))))

(deftest llm-surface-names-the-kits-own-schemas
  "The surface must name THIS kit's request/result, not a shape copied from
  another kit. Both are read straight back out of the kit's own :request and
  :result, and the provider the reference path uses agrees with them."
  (let [kit (load-kit)
        surface (:wasm-aot-surface kit)]
    (is (= (second (:request kit)) (:request-schema surface)))
    (is (= (second (:result kit)) (:result-schema surface)))
    (is (= :kotoba.llm/generate-request (:request-schema surface)))
    (is (= :kotoba.llm/result (:result-schema surface)))
    (is (= llm/request-type (:request kit)))
    (is (= llm/result-type (:result kit)))
    (is (= llm/capability-id (:id (:capability kit))))))
