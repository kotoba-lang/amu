(ns kotoba.compiler.http-wasm-aot-test
  "The http kit's own record/variant/set-of-record ABI runs on the typed hosts.

  `http-v1` names ONE capability, :http/post id 4. Its :request is
  :kotoba.http/post-request -- a record whose :headers field is a
  [:set [:record :kotoba.http/header ...]] -- and its :result is
  :kotoba.http/result, a variant over a response record that carries the
  SAME set-of-record type back. So this kit is the one where a set of
  nominal records has to survive the seam in BOTH directions inside the
  kit's own schemas.

  The inject proves both halves with one value: it reads the guest's
  :accept header text out of the request set and puts it back into a
  host-built response set under a different key (:echo-accept). A host
  that never saw the request set could not produce \"application/json\",
  and a guest that reconstructed the set locally would not see :server.

  :wasm-aot names the typed kit ABI (kotoba:typed/cap-call, id 4) on
  :wasm32-browser-kotoba-v1. It is not clock's i64 kotoba:cap/call
  surface, which is what :wasm32-kotoba-v1 means (ADR 0084 / 0257) --
  `module-imports-the-typed-seam-and-not-the-i64-one` is the
  discriminator: the compiled module has no kotoba:cap/call import at
  all. The guest does compile to :wasm32-kotoba-v1, but compiling to a
  target is not the same claim as running on that target's host-time
  surface, so that key stays :pending.

  :jit is the kotoba-script :js-kotoba-v1 path under node's V8.

  :native-aot stays :pending and `native-aot-refuses-the-http-kit-abi`
  measures WHY rather than assuming it: both native targets reject this
  guest at :phase :target with :value-profile :kotoba.value/typed-v1.
  Nothing in src/ reads :qualification, so this namespace is the only
  thing keeping that map honest.

  Breaks, measured 2026-08-18 -- control is 0 failures / 0 errors, each
  break is non-zero, and the reported failure is the one that was broken:

    host drops the echoed :accept text (returns \"\")   exit 5
    host returns an EMPTY response header set          exit 4 (count 0)
    host answers :error for an https URL               exit 2 (status -1)
    host never reaches typedCapCall                    exit 31
    host returns a bare i64 instead of the variant     exit 70 invalid-typed-value
    kit flips :wasm-aot back to :pending               1 failure, named
    kit surface :capability-id becomes 12              2 failures, named
    kit surface :import becomes kotoba:cap             1 failure, named

  The first two are the ones worth keeping: the dropped-echo break is
  what shows the request's set-of-record payload really crosses rather
  than being invented host-side, and the empty-set break is what shows
  the response set really crosses back rather than being reconstructed
  in the guest."
  (:require [clojure.edn :as edn]
            [clojure.java.io :as io]
            [clojure.java.shell :as shell]
            [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]
            [provider.http :as http]))

(def policy {:allow #{[:cap/call 4]}})

(def guest-source
  (let [req (pr-str http/request-type)
        res (pr-str http/result-type)
        resp (pr-str http/response-type)
        err (pr-str http/error-type)
        hdr (pr-str http/header-type)
        hset (pr-str http/header-set-type)
        ;; The two request headers are written OUT of canonical order so
        ;; typed-set-new has to sort them; index 0 is :accept.
        call (fn [url body]
               (str "(typed-cap-call :http/post " req " " res
                    " (record-new " req " " url
                    "   (typed-set-new " hset
                    "     (record-new " hdr " :content-type \"text/plain\")"
                    "     (record-new " hdr " :accept \"application/json\"))"
                    "   " body " 1000))"))]
    (str "(ns app.http (:export [main status reply hcount hhas])"
         " (:capabilities #{:http/post}))"
         "(defn main [] 0)"
         ;; :ok arm -> the response record's i64 :status field.
         "(defn status [url :string payload :string] :i64"
         " (variant-match " res " " (call "url" "payload")
         "  [[:ok r (record-get " resp " r :status)]"
         "   [:error e -1]]))"
         ;; Both arms return a :string, from two different record types.
         "(defn reply [url :string payload :string] :string"
         " (variant-match " res " " (call "url" "payload")
         "  [[:ok r (record-get " resp " r :body)]"
         "   [:error e (record-get " err " e :message)]]))"
         ;; The response's set-of-record, counted in the guest.
         "(defn hcount [url :string] :i64"
         " (variant-match " res " " (call "url" "\"\"")
         "  [[:ok r (typed-set-count " hset " (record-get " resp " r :headers))]"
         "   [:error e -1]]))"
         ;; ... and indexed into, then read as a nominal record.
         ;; ... and membership-tested against a record the guest rebuilds,
         ;; so both the :name keyword and the :value string of the header
         ;; the host put in the response have to match exactly.
         "(defn hhas [url :string v :string] :i64"
         " (variant-match " res " " (call "url" "\"\"")
         "  [[:ok r (if (typed-set-contains " hset
         "                (record-get " resp " r :headers)"
         "                (record-new " hdr " :accept v))"
         "            1 0)]"
         "   [:error e -1]]))")))

(defn- load-kit []
  (edn/read-string
   (slurp (io/resource "kotoba/lang/capability-kits/http-v1.edn"))))

(defn- compiled-browser []
  (compiler/compile-source guest-source :wasm32-browser-kotoba-v1 policy))

;; Descriptors are dug out of the sealed contract, never rebuilt, so the
;; host-built response set carries trusted nominal descriptors. Records are
;; [descriptor field0 ...]; a set value is [descriptor frozenItems].
(defn- inject-body [request-expr]
  (str "const result=contract.result;"
       "const arm=name=>result[2].find(([n])=>n===name)[1];"
       "const respType=arm(':ok');const errType=arm(':error');"
       "const hsetType=respType[2][1][1];"
       "const request=" request-expr ";"
       "if(request[4]!==1000n)process.exit(25);"
       "const sent=request[2];"
       "if(sent[1].length!==2)process.exit(26);"
       "if(sent[1][0][1]!==':accept')process.exit(27);"
       "if(sent[1][1][1]!==':content-type')process.exit(28);"
       "const accept=sent[1][0][2];const ctype=sent[1][1][2];"
       "const url=request[1];"
       "if(!url.startsWith('https://'))"
       "return [result,':error',[errType,':http/scheme','refused '+url,false]];"
       ;; The response set is BUILT HERE, one item where the guest sent two,
       ;; so a guest that kept its own set could not read a count of 1.
       "const headers=Object.freeze([hsetType,Object.freeze([sent[1][0]])]);"
       "return [result,':ok',[respType,200n,headers,request[3]+'|'+ctype]];"))

;; The browser host passes (id, request, contract); kotoba-script passes
;; (request, contract). Same body, two arities.
(def wasm-inject-js
  (str "function httpInject(id,rawRequest,contract){"
       "if(id!==4)process.exit(20);"
       (inject-body "rawRequest")
       "}"))

(def jit-inject-js
  (str "function httpInject(rawRequest,contract){"
       (inject-body "rawRequest")
       "}"))

(defn- node-probe [compiled javascript]
  (let [encoded (.encodeToString (java.util.Base64/getEncoder)
                                 ^bytes (:bytes compiled))
        probe (str "import('./runtime/browser-host.mjs').then(async m=>{"
                   javascript
                   "}).catch(e=>{console.error(e);process.exit(70)})")]
    (shell/sh "node" "--input-type=module" "-e" probe encoded)))

;; https -> :ok arm; a non-https URL -> :error arm, so both arms of the
;; kit's own variant are exercised against the same guest.
(def ^:private round-trip-js
  (str "const x=h.instance.exports;"
       "if(x.status('https://example.test/v1','hi')!==200n)process.exit(2);"
       "if(x.reply('https://example.test/v1','hi')!=='hi|text/plain')process.exit(3);"
       "if(x.hcount('https://example.test/v1')!==1n)process.exit(4);"
       "if(x.hhas('https://example.test/v1','application/json')!==1n)process.exit(5);"
       "if(x.hhas('https://example.test/v1','text/plain')!==0n)process.exit(6);"
       "if(x.status('http://example.test/v1','hi')!==-1n)process.exit(7);"
       "if(x.reply('http://example.test/v1','hi')!=='refused http://example.test/v1')"
       "process.exit(8);"))

(deftest http-guest-compiles-to-both-wasm32-targets
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

(deftest http-guest-runs-on-browser-wasm-typedCapCall
  (let [probe (node-probe
               (compiled-browser)
               (str wasm-inject-js
                    "const h=await m.instantiateKotoba(Buffer.from(process.argv[1],'base64'),{"
                    "allowCapabilities:[4],"
                    "typedCapCall:(id,request,contract)=>httpInject(id,request,contract)});"
                    "if(!h.typedAbi.contracts.has(4))process.exit(22);"
                    round-trip-js))]
    (is (zero? (:exit probe)) (str (:err probe) \newline (:out probe)))))

(deftest wasm-http-without-allow-4-is-denied
  (let [probe (node-probe
               (compiled-browser)
               (str "const h=await m.instantiateKotoba(Buffer.from(process.argv[1],'base64'),{"
                    "allowCapabilities:[],"
                    "typedCapCall:()=>process.exit(2)});"
                    "try{h.instance.exports.hcount('https://example.test/');process.exit(3)}"
                    "catch(e){if(e.code!=='capability-denied')process.exit(4)}"))]
    (is (zero? (:exit probe)) (:err probe))))

(deftest forged-scalar-http-result-is-rejected
  "A bare i64 is not a :kotoba.http/result variant even though the response
  record's first field is an i64. Without result admission this would pass."
  (let [probe (node-probe
               (compiled-browser)
               (str "const h=await m.instantiateKotoba(Buffer.from(process.argv[1],'base64'),{"
                    "allowCapabilities:[4],typedCapCall:()=>200n});"
                    "try{h.instance.exports.status('https://example.test/','hi');process.exit(2)}"
                    "catch(e){if(e.code!=='invalid-typed-value')process.exit(3)}"))]
    (is (zero? (:exit probe)) (:err probe))))

(deftest jit-http-guest-round-trips-on-kotoba-script-v8
  (let [compiled (compiler/compile-source guest-source :js-kotoba-v1 policy)
        encoded (.encodeToString (java.util.Base64/getEncoder)
                                 (.getBytes ^String (:source compiled) "UTF-8"))
        js (str jit-inject-js
                "import('data:text/javascript;base64," encoded
                "').then(m=>{const x=m.instantiateKotoba({4:httpInject});"
                "if(x.status('https://example.test/v1','hi')!==200n)process.exit(2);"
                "if(x.reply('https://example.test/v1','hi')!=='hi|text/plain')process.exit(3);"
                "if(x.hcount('https://example.test/v1')!==1n)process.exit(4);"
                "if(x.hhas('https://example.test/v1','application/json')!==1n)process.exit(5);"
                "if(x.hhas('https://example.test/v1','text/plain')!==0n)process.exit(6);"
                "if(x.status('http://example.test/v1','hi')!==-1n)process.exit(7)})")
        probe (shell/sh "node" "--input-type=module" "-e" js)]
    (is (string? (:source compiled)))
    (is (zero? (:exit probe)) (str (:err probe) \newline (:out probe)))))

(def ^:private nth-guest-source
  "Same kit ABI, but indexing the response header set instead of testing
  membership. This is what the guest above deliberately does NOT do."
  (let [req (pr-str http/request-type)
        res (pr-str http/result-type)
        resp (pr-str http/response-type)
        hdr (pr-str http/header-type)
        hset (pr-str http/header-set-type)]
    (str "(ns app.httpnth (:export [main hvalue])"
         " (:capabilities #{:http/post}))"
         "(defn main [] 0)"
         "(defn hvalue [url :string i :i64] :string"
         " (variant-match " res
         "  (typed-cap-call :http/post " req " " res
         "    (record-new " req " url (typed-set-new " hset ") \"\" 1000))"
         "  [[:ok r (record-get " hdr
         "            (typed-set-nth " hset " (record-get " resp " r :headers) i)"
         "            :value)]"
         "   [:error e \"\"]]))")))

(deftest kotoba-script-has-no-typed-set-nth
  "Why the guest above membership-tests the response set instead of indexing
  it. typed-set-nth compiles on the wasm targets and is refused by the
  :js-kotoba-v1 emitter, so a guest that used it could reach :wasm-aot but
  not :jit. Measured, not assumed."
  (is (= :wasm/v1 (:format (compiler/compile-source nth-guest-source
                                                    :wasm32-browser-kotoba-v1
                                                    policy)))
      "typed-set-nth is fine on the typed wasm target")
  (let [thrown (try (compiler/compile-source nth-guest-source :js-kotoba-v1 policy)
                    nil
                    (catch clojure.lang.ExceptionInfo e e))]
    (is (some? thrown) "kotoba-script must not silently accept typed-set-nth")
    (is (= :kotoba-script (:phase (ex-data thrown))))
    (is (= http/header-set-type (:node (ex-data thrown))))
    (is (= "unsupported KIR node" (ex-message thrown)))))

(deftest native-aot-refuses-the-http-kit-abi
  "Why :native-aot is :pending, measured rather than assumed. The refusal is
  the compiler's own word-typed native admission gate, at :phase :target."
  (doseq [target [:x86_64-kotoba-v1 :aarch64-kotoba-v1]]
    (testing (str target)
      (let [thrown (try (compiler/compile-source guest-source target policy)
                        nil
                        (catch clojure.lang.ExceptionInfo e e))]
        (is (some? thrown) "native must not silently accept the kit ABI")
        (is (= :target (:phase (ex-data thrown))))
        (is (= target (:target (ex-data thrown))))
        (is (= :kotoba.value/typed-v1 (:value-profile (ex-data thrown))))))
    (is (= :pending (:native-aot (:qualification (load-kit)))))))

(deftest http-kit-wasm-aot-is-the-typed-browser-surface
  (let [kit (load-kit)
        q (:qualification kit)
        surface (:wasm-aot-surface kit)]
    (is (= :implemented (:reference q)))
    (is (= :implemented (:wasm-aot q)))
    (is (= :pending (:wasm32-kotoba-v1 q))
        "i64 kotoba:cap/call is not this kit ABI")
    (is (= :pending (:native-aot q))
        "native-aot-refuses-the-http-kit-abi is why")
    (is (= :implemented (:jit q)))
    (is (= ["kotoba:typed" "cap-call"] (:import surface)))
    (is (= 4 (:capability-id surface)))
    (is (= (:id (:capability kit)) (:capability-id surface))
        "surface id agrees with the kit's declared capability")
    (is (= :http/post (:grant surface)))
    (is (= (:name (:capability kit)) (:grant surface))
        "surface grant agrees with the kit's declared capability name")
    (is (= :wasm32-browser-kotoba-v1 (:target surface)))
    (is (= "(typed-cap-call :http/post request-type result-type request)"
           (:elaboration surface)))))

(deftest http-surface-names-the-kits-own-schemas
  "The surface must name THIS kit's request/result, not a shape copied from
  another kit. Both are read straight back out of the kit's own :request and
  :result, and the provider the reference path uses agrees with them."
  (let [kit (load-kit)
        surface (:wasm-aot-surface kit)]
    (is (= (second (:request kit)) (:request-schema surface)))
    (is (= (second (:result kit)) (:result-schema surface)))
    (is (= :kotoba.http/post-request (:request-schema surface)))
    (is (= :kotoba.http/result (:result-schema surface)))
    (is (= http/request-type (:request kit)))
    (is (= http/result-type (:result kit)))))
