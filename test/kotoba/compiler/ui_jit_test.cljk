(ns kotoba.compiler.ui-jit-test
  "Existing kotoba-script :js-kotoba-v1 path (V8 JIT) runs wires 9 and 10.

  This is not KIR ir/execute and not a second jit engine. callTypedCapability
  interns the host result with assertTypedValue, which is what makes the
  returned commit-result a record rather than a bare i64, and what carries the
  present/absent discriminant of the [:option event] rather than a payload
  alone.

  The same guest source and the same injects as the wasm proof, so the only
  thing that differs between the two is the backend. `main` is not used --
  each export is called directly and given its own exit code, because a
  single packed return cannot say WHICH wire failed, and this kit's second
  wire has two outcomes (some/none) that must both be seen.

  commit's two answers are DERIVED from the request (base+1, and the size of
  the node set the guest built), so a guest that dropped either argument
  cannot earn them. next-event answers some below revision 9 and none at or
  above it, so `poll` and `pending` are two different facts.

  Break: emit typed-cap-call as callCapability (i64 only), or return the host
  result without assertTypedValue, and this Node probe exits non-zero."
  (:require [clojure.edn :as edn]
            [clojure.java.io :as io]
            [clojure.java.shell :as shell]
            [clojure.test :refer [deftest is]]
            [kotoba.compiler.core :as compiler]
            [kotoba.compiler.ui-wasm-aot-test :as w]))

(def inject-js
  (str "function commitInject(request,contract){"
       "const result=contract.result;"
       "const nodes=request[2][1];"
       "if(nodes.length!==1)process.exit(30);"
       "if(nodes[0][1]!==':view/title')process.exit(31);"
       "if(nodes[0][2][1]!==false)process.exit(32);"
       "if(nodes[0][3]!==':ui/text')process.exit(33);"
       "if(nodes[0][4]!=='ready')process.exit(34);"
       "return [result,request[1]+1n,BigInt(nodes.length)]}"
       "function eventInject(request,contract){"
       "const result=contract.result;const event=result[1];"
       "if(request[1]>=9n)return [result,false];"
       "return [result,true,[event,request[1]+3n,':view/title',':ui/click','open']]}"))

(defn- load-kit []
  (edn/read-string
   (slurp (io/resource "kotoba/lang/capability-kits/ui-v1.edn"))))

(deftest jit-ui-guest-round-trips-both-wires-on-kotoba-script-v8
  (let [compiled (compiler/compile-source w/guest-source :js-kotoba-v1 w/policy)
        encoded (.encodeToString (java.util.Base64/getEncoder)
                                 (.getBytes ^String (:source compiled) "UTF-8"))
        js (str inject-js
                "import('data:text/javascript;base64," encoded
                "').then(m=>{const x=m.instantiateKotoba("
                "{9:commitInject,10:eventInject});"
                ;; commit: revision is base+1, node-count is the set the guest built
                "if(x.rev(1n,'ready')!==2n)process.exit(2);"
                "if(x.size(1n,'ready')!==1n)process.exit(3);"
                ;; next-event: some below 9 carries the event's revision back
                "if(x.poll(0n)!==3n)process.exit(4);"
                ;; next-event: none at or above 9 takes the option's other arm
                "if(x.pending(9n)!==1n)process.exit(5);"
                ;; and the some-arm must NOT be read as none
                "if(x.pending(0n)!==0n)process.exit(6);"
                "}).catch(e=>{console.error(e);process.exit(70)})")
        probe (shell/sh "node" "--input-type=module" "-e" js)]
    (is (string? (:source compiled)))
    (is (zero? (:exit probe)) (str (:err probe) \newline (:out probe)))))

(deftest ui-kit-jit-is-implemented-only-after-v8-ran-wires-9-and-10
  (is (= :implemented (:jit (:qualification (load-kit))))))
