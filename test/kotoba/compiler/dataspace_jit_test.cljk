(ns kotoba.compiler.dataspace-jit-test
  "Existing kotoba-script :js-kotoba-v1 path (V8 JIT) runs wire 24.

  This is not KIR ir/execute and not a second jit engine. callTypedCapability
  interns the host result with assertTypedValue.

  Break: emit typed-cap-call as callCapability (i64 only) or return the host
  result without assertTypedValue. Then this Node probe exits non-zero."
  (:require [clojure.edn :as edn]
            [clojure.java.io :as io]
            [clojure.java.shell :as shell]
            [clojure.test :refer [deftest is]]
            [kotoba.compiler.core :as compiler]
            [provider.dataspace :as dataspace]))

(def policy {:allow #{[:cap/call 24]}})

(def empty-notices "[]")
(def assert-notices
  "[{:assertion [:temperature :room/a 21] :bindings {} :kind :assert}]")
(def retract-notices
  "[{:assertion [:temperature :room/a 21] :bindings {} :kind :retract}]")

(def guest-source
  (let [req (pr-str dataspace/request-type)
        res (pr-str dataspace/result-type)
        asserted (pr-str dataspace/asserted-type)
        retracted (pr-str dataspace/retracted-type)
        matches (pr-str dataspace/matches-type)
        facet-rec (pr-str dataspace/facet-type)
        observe-rec (pr-str dataspace/observe-type)
        assert-rec (pr-str dataspace/assert-type)
        retract-rec (pr-str dataspace/retract-type)
        empty-doc "(document-edn-read \"[]\")"]
    (str "(ns app.ds (:export [main]) (:capabilities #{:dataspace/transact}))"
         "(defn main [] :i64"
         "  (let [doc (document-edn-read \"[:temperature :room/a 21]\")"
         "        entered (typed-cap-call :dataspace/transact " req " " res
         "                  (variant-new " req " :facet-enter false))"
         "        facet (variant-match " res " entered"
         "                [[:asserted a 0]"
         "                 [:retracted r 0]"
         "                 [:matches m 0]"
         "                 [:facet f (record-get " facet-rec " f :id)]"
         "                 [:error e 0]])"
         "        bit0 (if (< 0 facet) 1 0)"
         "        observed0 (typed-cap-call :dataspace/transact " req " " res
         "                    (variant-new " req " :observe"
         "                      (record-new " observe-rec " doc facet)))"
         "        notices0 (variant-match " res " observed0"
         "                    [[:asserted a (record-get " asserted " a :notices)]"
         "                     [:retracted r " empty-doc "]"
         "                     [:matches m (record-get " matches " m :notices)]"
         "                     [:facet f " empty-doc "]"
         "                     [:error e " empty-doc "]])"
         "        bit1 (if (string=? (document-edn-print notices0) "
         (pr-str empty-notices) ") 1 0)"
         "        asserted0 (typed-cap-call :dataspace/transact " req " " res
         "                     (variant-new " req " :assert"
         "                       (record-new " assert-rec " doc facet)))"
         "        notices-a (variant-match " res " asserted0"
         "                     [[:asserted a (record-get " asserted " a :notices)]"
         "                      [:retracted r " empty-doc "]"
         "                      [:matches m (record-get " matches " m :notices)]"
         "                      [:facet f " empty-doc "]"
         "                      [:error e " empty-doc "]])"
         "        bit2 (if (string=? (document-edn-print notices-a) "
         (pr-str assert-notices) ") 1 0)"
         "        observed1 (typed-cap-call :dataspace/transact " req " " res
         "                     (variant-new " req " :observe"
         "                       (record-new " observe-rec " doc facet)))"
         "        notices1 (variant-match " res " observed1"
         "                     [[:asserted a (record-get " asserted " a :notices)]"
         "                      [:retracted r " empty-doc "]"
         "                      [:matches m (record-get " matches " m :notices)]"
         "                      [:facet f " empty-doc "]"
         "                      [:error e " empty-doc "]])"
         "        bit3 (if (string=? (document-edn-print notices1) "
         (pr-str assert-notices) ") 1 0)"
         "        retracted0 (typed-cap-call :dataspace/transact " req " " res
         "                      (variant-new " req " :retract"
         "                        (record-new " retract-rec " doc facet)))"
         "        bit4 (variant-match " res " retracted0"
         "                [[:asserted a 0]"
         "                 [:retracted r (if (< 0 (record-get " retracted " r :count)) 1 0)]"
         "                 [:matches m 0]"
         "                 [:facet f 0]"
         "                 [:error e 0]])"
         "        observed2 (typed-cap-call :dataspace/transact " req " " res
         "                     (variant-new " req " :observe"
         "                       (record-new " observe-rec " doc facet)))"
         "        notices2 (variant-match " res " observed2"
         "                     [[:asserted a (record-get " asserted " a :notices)]"
         "                      [:retracted r " empty-doc "]"
         "                      [:matches m (record-get " matches " m :notices)]"
         "                      [:facet f " empty-doc "]"
         "                      [:error e " empty-doc "]])"
         "        bit5 (if (string=? (document-edn-print notices2) "
         (pr-str retract-notices) ") 1 0)"
         "        left (typed-cap-call :dataspace/transact " req " " res
         "                (variant-new " req " :facet-leave facet))"
         "        bit6 (variant-match " res " left"
         "                [[:asserted a 0]"
         "                 [:retracted r 1]"
         "                 [:matches m 0]"
         "                 [:facet f 0]"
         "                 [:error e 0]])]"
         "    (+ bit0"
         "       (+ (* 2 bit1)"
         "          (+ (* 4 bit2)"
         "             (+ (* 8 bit3)"
         "                (+ (* 16 bit4)"
         "                   (+ (* 32 bit5) (* 64 bit6)))))))))")))

(def inject-js
  (str "function dataspaceInject(request,contract){"
       "if(!dataspaceInject.next){dataspaceInject.next=1n;dataspaceInject.live=new Set();"
       "dataspaceInject.asserts=[];dataspaceInject.observers=[];dataspaceInject.mail=[];}"
       "const result=contract.result;"
       "const rec=name=>result[2].find(([n])=>n===name)[1];"
       "const record=(name,...fields)=>[rec(name),...fields];"
       "const empty=['vector',[]];"
       "const notice=(kind,assertion)=>['vector',[['map',["
       "[['keyword',':assertion'],assertion],"
       "[['keyword',':bindings'],['map',[]]],"
       "[['keyword',':kind'],['keyword',kind]]"
       "]]]];"
       "const same=(a,b)=>{const r=(k,v)=>typeof v==='bigint'?String(v):v;"
       "return JSON.stringify(a,r)===JSON.stringify(b,r)};"
       "const tag=request[1];"
       "if(tag===':facet-enter'){const id=dataspaceInject.next++;dataspaceInject.live.add(id);"
       "return [result,':facet',record(':facet',id)];}"
       "if(tag===':facet-leave'){const id=request[2];"
       "if(!dataspaceInject.live.has(id))return [result,':error',record(':error',':dataspace/unknown-facet','unknown facet')];"
       "dataspaceInject.live.delete(id);return [result,':retracted',record(':retracted',1n)];}"
       "const payload=request[2];const doc=payload[1];const facet=payload[2];"
       "if(tag===':assert'){dataspaceInject.asserts.push(doc);"
       "for(const o of dataspaceInject.observers){if(same(o,doc))dataspaceInject.mail.push([':assert',doc]);}"
       "return [result,':asserted',record(':asserted',1n,notice(':assert',doc))];}"
       "if(tag===':retract'){const before=dataspaceInject.asserts.length;"
       "dataspaceInject.asserts=dataspaceInject.asserts.filter(a=>!same(a,doc));"
       "const removed=before===dataspaceInject.asserts.length?0n:1n;"
       "if(removed===1n){for(const o of dataspaceInject.observers){if(same(o,doc))dataspaceInject.mail.push([':retract',doc]);}}"
       "return [result,':retracted',record(':retracted',removed)];}"
       "if(tag===':observe'){if(!dataspaceInject.observers.some(o=>same(o,doc)))dataspaceInject.observers.push(doc);"
       "let notices=empty;"
       "if(dataspaceInject.mail.length){const [kind,assertion]=dataspaceInject.mail.shift();notices=notice(kind,assertion);}"
       "return [result,':matches',record(':matches',empty,notices)];}"
       "return [result,':error',record(':error',':dataspace/unknown-op','unknown')];}"))

(defn- load-kit []
  (edn/read-string
   (slurp (io/resource "kotoba/lang/capability-kits/dataspace-v1.edn"))))

(deftest jit-dataspace-guest-round-trips-on-kotoba-script-v8
  (let [compiled (compiler/compile-source guest-source :js-kotoba-v1 policy)
        encoded (.encodeToString (java.util.Base64/getEncoder)
                                 (.getBytes ^String (:source compiled) "UTF-8"))
        js (str inject-js
                "import('data:text/javascript;base64," encoded
                "').then(m=>{const x=m.instantiateKotoba({24:dataspaceInject});"
                "const n=x.main();if(n!==127n){console.error('got',n);process.exit(2)}})")
        probe (shell/sh "node" "--input-type=module" "-e" js)]
    (is (string? (:source compiled)))
    (is (zero? (:exit probe)) (str (:err probe) \newline (:out probe)))))

(deftest dataspace-kit-jit-is-implemented-only-after-v8-ran-wire-24
  (let [kit (load-kit)
        q (:qualification kit)]
    (is (= :implemented (:jit q)))))
