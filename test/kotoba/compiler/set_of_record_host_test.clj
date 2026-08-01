(ns kotoba.compiler.set-of-record-host-test
  "T8.3 ADR 0195: browser-host compareValue resolves schema refs so
  set-of-record conj/sort has a canonical order."
  (:require [clojure.java.shell :as shell]
            [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]
            [kotoba.kir :as ir]))

(def ^:private pair-set-src
  (str
   "(ns hdr-pair-set\n"
   "  (:export [main])\n"
   "  (:schemas {:hdr/pair [:record :hdr/pair\n"
   "                        [[:name :string] [:value :string]]]}))\n"
   "\n"
   "(defn main [] :i64\n"
   "  (let [empty (typed-set-new [:set [:ref :hdr/pair]])\n"
   "        h1 (record-new [:ref :hdr/pair] \"Host\" \"ex.com\")\n"
   "        h2 (record-new [:ref :hdr/pair] \"Accept\" \"*/*\")\n"
   "        s1 (typed-set-conj [:set [:ref :hdr/pair]] empty h1)\n"
   "        s2 (typed-set-conj [:set [:ref :hdr/pair]] s1 h2)\n"
   "        s3 (typed-set-conj [:set [:ref :hdr/pair]] s2 h1)\n"
   "        n (typed-set-count [:set [:ref :hdr/pair]] s3)]\n"
   "    (if (= n 2) -9195 -1)))\n"))

(deftest set-of-record-conj-kir-execute
  (testing "KIR path: set of header-record refs uniqueness + count"
    (let [c (compiler/compile-source pair-set-src :wasm32-kotoba-v1 {})
          out (ir/execute (:kir c) 'main [] {})]
      (is (= -9195 out)))))

(deftest set-of-record-conj-browser-host-live
  (testing "browser-host: compareValue resolves :ref so set-op-ref works"
    (let [c (compiler/compile-source pair-set-src :wasm32-kotoba-v1 {})
          encoded (.encodeToString (java.util.Base64/getEncoder) ^bytes (:bytes c))
          probe (shell/sh
                 "node" "--input-type=module" "-e"
                 (str "import('./runtime/browser-host.mjs').then(async m=>{"
                      "const h=await m.instantiateKotoba(Buffer.from(process.argv[1],'base64'));"
                      "const v=h.instance.exports.main();"
                      "if(v!==-9195n){console.error('got',v);process.exit(2)}"
                      "console.log(JSON.stringify([-9195]))"
                      "}).catch(e=>{console.error(e);process.exit(70)})")
                 encoded)]
      (is (zero? (:exit probe)) (str (:err probe) (:out probe)))
      (is (= "[-9195]\n" (:out probe))))))
