(ns kotoba.compiler.log-jit-test
  "Existing kotoba-script :js-kotoba-v1 path (V8 JIT) runs wires 6 and 5.

  This is not KIR ir/execute and not a second jit engine. callTypedCapability
  interns the host result with assertTypedValue, which is what makes the
  returned append-result a record rather than a bare i64.

  `main` packs three bits so a partial pass cannot read as a full one:
  1 = append answered with a sequence, 2 = the read cursor the guest sent was
  the sequence it just received, 4 = the :truncated bool survived the round
  trip. 7 is the only value that means all three happened.

  Break: emit typed-cap-call as callCapability (i64 only) or return the host
  result without assertTypedValue. Then this Node probe exits non-zero."
  (:require [clojure.edn :as edn]
            [clojure.java.io :as io]
            [clojure.java.shell :as shell]
            [clojure.test :refer [deftest is]]
            [kotoba.compiler.core :as compiler]
            [provider.log :as log]))

(def policy {:allow #{[:cap/call 5] [:cap/call 6]}})

(def guest-source
  (let [areq (pr-str log/append-request-type)
        ares (pr-str log/append-result-type)
        rreq (pr-str log/read-request-type)
        rres (pr-str log/read-result-type)
        fset (pr-str log/field-set-type)]
    (str "(ns app.log (:export [main]) (:capabilities #{:log/append :log/read}))"
         "(defn main [] :i64"
         "  (let [appended (typed-cap-call :log/append " areq " " ares
         "                    (record-new " areq " :log/info :app/started \"ready\""
         "                      (typed-set-new " fset ")))"
         "        seq (record-get " ares " appended :sequence)"
         "        bit0 (if (< 0 seq) 1 0)"
         "        r (typed-cap-call :log/read " rreq " " rres
         "             (record-new " rreq " seq 8))"
         "        latest (record-get " rres " r :latest-sequence)"
         "        bit1 (if (< seq latest) 2 0)"
         "        bit2 (if (record-get " rres " r :truncated) 4 0)]"
         "    (+ bit0 (+ bit1 bit2))))")))

;; The read inject asserts the cursor equals the sequence append just handed
;; back, so bit1 cannot be earned by a guest that dropped the value.
(def inject-js
  (str "function appendInject(request,contract){"
       "if(request[3]!=='ready')process.exit(30);"
       "return [contract.result,5n]}"
       "function readInject(request,contract){"
       "if(request[1]!==5n)process.exit(31);"
       "const entries=contract.result[2][3][1];"
       "return [contract.result,1n,9n,true,"
       "Object.freeze([entries,Object.freeze([])])]}"))

(defn- load-kit []
  (edn/read-string
   (slurp (io/resource "kotoba/lang/capability-kits/log-v1.edn"))))

(deftest jit-log-guest-round-trips-both-wires-on-kotoba-script-v8
  (let [compiled (compiler/compile-source guest-source :js-kotoba-v1 policy)
        encoded (.encodeToString (java.util.Base64/getEncoder)
                                 (.getBytes ^String (:source compiled) "UTF-8"))
        js (str inject-js
                "import('data:text/javascript;base64," encoded
                "').then(m=>{const x=m.instantiateKotoba("
                "{5:readInject,6:appendInject});"
                "const n=x.main();if(n!==7n){console.error('got',n);process.exit(2)}})")
        probe (shell/sh "node" "--input-type=module" "-e" js)]
    (is (string? (:source compiled)))
    (is (zero? (:exit probe)) (str (:err probe) \newline (:out probe)))))

(deftest log-kit-jit-is-implemented-only-after-v8-ran-wires-6-and-5
  (let [kit (load-kit)
        q (:qualification kit)]
    (is (= :implemented (:jit q)))))
