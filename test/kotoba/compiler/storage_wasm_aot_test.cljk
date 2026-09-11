(ns kotoba.compiler.storage-wasm-aot-test
  "The storage kit's own variant/record ABI runs on the typed hosts.

  `storage-v1` names capability id 12. Its :request and :result are
  :kotoba.storage/request and :kotoba.storage/result -- variants over
  records that carry :keyword, :string, :i64 and, uniquely among the
  kits proved so far, an [:option :i64] (put/delete expected-version and
  conflict current-version). Those cross the boundary whole here; the
  guest reads the conflict option back out with option-value-of, so a
  host that dropped the option payload could not produce 102.

  :wasm-aot names the typed kit ABI (kotoba:typed/cap-call, id 12) on
  :wasm32-browser-kotoba-v1, the same seam dataspace-wasm-aot-test uses.
  It is not clock's i64 kotoba:cap/call surface, which is what
  :wasm32-kotoba-v1 means (ADR 0084 / 0257) -- this guest does compile to
  :wasm32-kotoba-v1, but compiling to a target is not the same claim as
  running on that target's host-time surface, so that key stays :pending.

  :jit is the existing kotoba-script :js-kotoba-v1 path under V8.

  :native-aot stays :pending and native-aot-refuses-the-storage-kit-abi
  measures WHY rather than assuming it: the native targets reject this
  guest at :phase :target. Nothing in src/ reads :qualification, so the
  only thing keeping that map honest is this namespace.

  Breaks, measured 2026-08-18 -- control exits 0, each break exits
  non-zero, and the reported failure is the one that was broken:

    guest drops the +100 on :conflict          exit 6
    host returns an ABSENT conflict option     exit 6
    host returns a bare i64 for that option    exit 70 invalid-typed-value
    host never reaches typedCapCall            exit 31
    kit flips :wasm-aot back to :pending       2 failures, both named
    kit surface :import becomes kotoba:cap     2 failures, both named

  The middle two are the ones worth keeping: the absent-option break is
  what shows the [:option :i64] payload really crosses rather than being
  reconstructed guest-side, and the never-reached break is what shows
  this runs through typedCapCall at all."
  (:require [clojure.edn :as edn]
            [clojure.java.io :as io]
            [clojure.java.shell :as shell]
            [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]
            [provider.storage :as storage]))

(def policy {:allow #{[:cap/call 12]}})

(def guest-source
  (let [req (pr-str storage/request-type)
        res (pr-str storage/result-type)
        put (pr-str storage/put-type)
        get-rec (pr-str storage/get-type)
        del (pr-str storage/delete-type)
        entry (pr-str storage/entry-type)
        conflict (pr-str storage/conflict-type)
        err (pr-str storage/error-type)
        opt (pr-str storage/expected-version-type)]
    (str "(ns app.storage (:export [main store fetch erase])"
         " (:capabilities #{:storage/transact}))"
         "(defn main [] 0)"
         ;; :put with an absent expected-version; the written version comes
         ;; back out of the entry record.
         "(defn store [value :string] :i64"
         " (variant-match " res
         "  (typed-cap-call :storage/transact " req " " res
         "    (variant-new " req " :put"
         "      (record-new " put " :profile/name value (option-none-of " opt "))))"
         "  [[:found e (record-get " entry " e :version)]"
         "   [:missing m -1]"
         "   [:written w (record-get " entry " w :version)]"
         "   [:deleted d -2]"
         "   [:conflict c -3]"
         "   [:error x -4]]))"
         ;; :get -- :missing and :found are different arms of the same variant.
         "(defn fetch [] :string"
         " (variant-match " res
         "  (typed-cap-call :storage/transact " req " " res
         "    (variant-new " req " :get (record-new " get-rec " :profile/name)))"
         "  [[:found e (record-get " entry " e :value)]"
         "   [:missing m \"\"]"
         "   [:written w (record-get " entry " w :value)]"
         "   [:deleted d \"\"]"
         "   [:conflict c \"\"]"
         "   [:error x (record-get " err " x :message)]]))"
         ;; :delete carries a PRESENT expected-version out, and reads the
         ;; conflict current-version option back in. +100 keeps :conflict
         ;; distinguishable from :deleted.
         "(defn erase [version :i64] :i64"
         " (variant-match " res
         "  (typed-cap-call :storage/transact " req " " res
         "    (variant-new " req " :delete"
         "      (record-new " del " :profile/name (option-some-of " opt " version))))"
         "  [[:found e 0]"
         "   [:missing m 0]"
         "   [:written w 0]"
         "   [:deleted d 1]"
         "   [:conflict c (+ 100 (option-value-of " opt
         "                  (record-get " conflict " c :current-version) 0))]"
         "   [:error x -4]]))")))

(defn- load-kit []
  (edn/read-string
   (slurp (io/resource "kotoba/lang/capability-kits/storage-v1.edn"))))

;; One in-memory cell. Records are [type field0 field1 ...], so a record's
;; first field is at index 1; an option value is [descriptor false] or
;; [descriptor true payload]. The conflict arm hands back a PRESENT option
;; so the guest's option-value-of has something to unwrap.
(defn- inject-body [request-expr]
  (str "const result=contract.result;"
       "const rec=name=>result[2].find(([n])=>n===name)[1];"
       "const record=(name,...fields)=>[rec(name),...fields];"
       "const optDesc=rec(':conflict')[2][1][1];"
       "const request=" request-expr ";"
       "const tag=request[1];const payload=request[2];"
       "if(tag===':put'){if(payload[3][1]===true)process.exit(23);"
       "cell.value=payload[2];cell.version+=1n;"
       "return [result,':written',"
       "record(':written',':profile/name',cell.value,cell.version)];}"
       "if(tag===':get'){if(cell.value===null)return [result,':missing',false];"
       "return [result,':found',"
       "record(':found',':profile/name',cell.value,cell.version)];}"
       "if(tag===':delete'){const expected=payload[2];"
       "if(expected[1]!==true)process.exit(24);"
       "if(expected[2]!==cell.version)"
       "return [result,':conflict',"
       "record(':conflict',':profile/name',[optDesc,true,cell.version])];"
       "cell.value=null;return [result,':deleted',true];}"
       "process.exit(21);"))

;; The browser host passes (id, request, contract); kotoba-script passes
;; (request, contract). Same body, two arities.
(def wasm-inject-js
  (str "const cell={version:0n,value:null};"
       "function storageInject(id,rawRequest,contract){"
       "if(id!==12)process.exit(20);"
       (inject-body "rawRequest")
       "}"))

(def jit-inject-js
  (str "const cell={version:0n,value:null};"
       "function storageInject(rawRequest,contract){"
       (inject-body "rawRequest")
       "}"))

(defn- node-probe [compiled javascript]
  (let [encoded (.encodeToString (java.util.Base64/getEncoder)
                                 ^bytes (:bytes compiled))
        probe (str "import('./runtime/browser-host.mjs').then(async m=>{"
                   javascript
                   "}).catch(e=>{console.error(e);process.exit(70)})")]
    (shell/sh "node" "--input-type=module" "-e" probe encoded)))

;; put -> get -> conflicting delete -> matching delete -> get. Two stores so
;; the conflict answer (102) and the deleted answer (1) cannot coincide.
(def ^:private round-trip-js
  (str "const x=h.instance.exports;"
       "if(x.fetch()!=='')process.exit(2);"
       "if(x.store('Kotoba')!==1n)process.exit(3);"
       "if(x.store('Kotoba2')!==2n)process.exit(4);"
       "if(x.fetch()!=='Kotoba2')process.exit(5);"
       "if(x.erase(9n)!==102n)process.exit(6);"
       "if(x.erase(2n)!==1n)process.exit(7);"
       "if(x.fetch()!=='')process.exit(8);"))

(deftest storage-guest-compiles-to-both-wasm32-targets
  (doseq [target [:wasm32-browser-kotoba-v1 :wasm32-kotoba-v1]]
    (testing (str target)
      (let [compiled (compiler/compile-source guest-source target policy)]
        (is (= :wasm/v1 (:format compiled)))
        (is (= :kotoba.typed/externref-v1 (:value-abi compiled)))
        (is (pos? (alength ^bytes (:bytes compiled))))))))

(deftest storage-guest-runs-on-browser-wasm-typedCapCall
  (let [compiled (compiler/compile-source guest-source
                                          :wasm32-browser-kotoba-v1 policy)
        probe (node-probe
               compiled
               (str wasm-inject-js
                    "const h=await m.instantiateKotoba(Buffer.from(process.argv[1],'base64'),{"
                    "allowCapabilities:[12],"
                    "typedCapCall:(id,request,contract)=>storageInject(id,request,contract)});"
                    "if(!h.typedAbi.contracts.has(12))process.exit(22);"
                    round-trip-js))]
    (is (zero? (:exit probe)) (str (:err probe) \newline (:out probe)))))

(deftest wasm-storage-without-allow-12-is-denied
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

(deftest forged-scalar-storage-result-is-rejected
  (let [compiled (compiler/compile-source guest-source
                                          :wasm32-browser-kotoba-v1 policy)
        probe (node-probe
               compiled
               (str "const h=await m.instantiateKotoba(Buffer.from(process.argv[1],'base64'),{"
                    "allowCapabilities:[12],typedCapCall:()=>7n});"
                    "try{h.instance.exports.fetch();process.exit(2)}"
                    "catch(e){if(e.code!=='invalid-typed-value')process.exit(3)}"))]
    (is (zero? (:exit probe)) (:err probe))))

(deftest jit-storage-guest-round-trips-on-kotoba-script-v8
  (let [compiled (compiler/compile-source guest-source :js-kotoba-v1 policy)
        encoded (.encodeToString (java.util.Base64/getEncoder)
                                 (.getBytes ^String (:source compiled) "UTF-8"))
        js (str jit-inject-js
                "import('data:text/javascript;base64," encoded
                "').then(m=>{const x=m.instantiateKotoba({12:storageInject});"
                "if(x.fetch()!=='')process.exit(2);"
                "if(x.store('Kotoba')!==1n)process.exit(3);"
                "if(x.store('Kotoba2')!==2n)process.exit(4);"
                "if(x.fetch()!=='Kotoba2')process.exit(5);"
                "if(x.erase(9n)!==102n)process.exit(6);"
                "if(x.erase(2n)!==1n)process.exit(7);"
                "if(x.fetch()!=='')process.exit(8)})")
        probe (shell/sh "node" "--input-type=module" "-e" js)]
    (is (string? (:source compiled)))
    (is (zero? (:exit probe)) (str (:err probe) \newline (:out probe)))))

(deftest native-aot-refuses-the-storage-kit-abi
  "Why :native-aot is :pending, measured rather than assumed. The refusal is
  the compiler's own word-typed native admission gate, at :phase :target."
  (doseq [target [:x86_64-macos-kotoba-v1 :aarch64-macos-kotoba-v1]]
    (testing (str target)
      (let [thrown (try (compiler/compile-source guest-source target policy)
                        nil
                        (catch clojure.lang.ExceptionInfo e e))]
        (is (some? thrown) "native must not silently accept the kit ABI")
        (is (= :target (:phase (ex-data thrown))))
        (is (= target (:target (ex-data thrown))))))))

(deftest storage-kit-wasm-aot-is-the-typed-browser-surface
  (let [kit (load-kit)
        q (:qualification kit)
        surface (:wasm-aot-surface kit)]
    (is (= :implemented (:reference q)))
    (is (= :implemented (:wasm-aot q)))
    (is (= :pending (:wasm32-kotoba-v1 q))
        "i64 kotoba:cap/call is not this kit ABI")
    (is (= :pending (:native-aot q))
        "native-aot-refuses-the-storage-kit-abi is why")
    (is (= :implemented (:jit q)))
    (is (= ["kotoba:typed" "cap-call"] (:import surface)))
    (is (= 12 (:capability-id surface)))
    (is (= (:id (:capability kit)) (:capability-id surface)))
    (is (= :storage/transact (:grant surface)))
    (is (= (:name (:capability kit)) (:grant surface)))
    (is (= :wasm32-browser-kotoba-v1 (:target surface)))
    (is (= "(typed-cap-call :storage/transact request-type result-type request)"
           (:elaboration surface)))))

(deftest storage-surface-names-the-kits-own-schemas
  "The surface must name THIS kit's request/result, not a shape copied from
  another kit. Both are read straight back out of the kit's own :request and
  :result, and the provider the reference path uses agrees with them."
  (let [kit (load-kit)
        surface (:wasm-aot-surface kit)]
    (is (= (second (:request kit)) (:request-schema surface)))
    (is (= (second (:result kit)) (:result-schema surface)))
    (is (= :kotoba.storage/request (:request-schema surface)))
    (is (= :kotoba.storage/result (:result-schema surface)))
    (is (= storage/request-type (:request kit)))
    (is (= storage/result-type (:result kit)))))
