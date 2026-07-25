(ns kotoba.compiler.string-operation-test
  (:require [clojure.java.shell :as shell]
            [clojure.test :refer [deftest is]]
            [kotoba.compiler.core :as compiler]
            [kotoba.compiler.ir :as ir]))

(def source
  "(ns string.operation (:export [main concat substring replace]))
   (defn main [] :i64 0)
   (defn concat [left :string right :string] :string
     (string-concat left right))
   (defn substring [value :string start :i64 end :i64] :string
     (string-substring value start end))
   (defn replace [value :string needle :string replacement :string] :string
     (string-replace-all value needle replacement))")

(defn- encoded [bytes]
  (.encodeToString (java.util.Base64/getEncoder) bytes))

(deftest bounded-literal-string-replacement-has-cross-target-conformance
  (let [javascript (compiler/compile-source source :js-kotoba-v1)
        wasm (compiler/compile-source source :wasm32-browser-kotoba-v1)
        kir (:kir wasm)
        js64 (encoded (.getBytes ^String (:source javascript) "UTF-8"))
        wasm64 (encoded (:bytes wasm))
        checks (str "if(x.concat('a','b')!=='ab')process.exit(2);"
                    "if(x.substring('a😀語z',1n,8n)!=='😀語')process.exit(6);"
                    "try{x.substring('a😀',2n,5n);process.exit(7)}catch(e){};"
                    "if(x.replace('a.$a.$','.','$')!=='a$$a$$')process.exit(3);"
                    "try{x.replace('abc','','x');process.exit(4)}catch(e){};"
                    "try{x.replace('x'.repeat(40000),'x','xx');process.exit(5)}catch(e){}")
        js-result (shell/sh "node" "--input-type=module" "-e"
                            (str "import('data:text/javascript;base64," js64
                                 "').then(m=>{const x=m.instantiateKotoba({});" checks "})"))
        wasm-result (shell/sh "node" "--input-type=module" "-e"
                              (str "import('./runtime/browser-host.mjs').then(async m=>{"
                                   "const h=await m.instantiateKotoba(Buffer.from(process.argv[1],'base64'));"
                                   "const x=h.instance.exports;" checks "})") wasm64)]
    (is (= "ab" (ir/execute kir 'concat ["a" "b"])))
    (is (= "😀語" (ir/execute kir 'substring ["a😀語z" 1 8])))
    (is (thrown? clojure.lang.ExceptionInfo
                 (ir/execute kir 'substring ["a😀" 2 5])))
    (is (= "a$$a$$" (ir/execute kir 'replace ["a.$a.$" "." "$"])))
    (is (thrown? clojure.lang.ExceptionInfo (ir/execute kir 'replace ["abc" "" "x"])))
    (is (zero? (:exit js-result)) (:err js-result))
    (is (zero? (:exit wasm-result)) (:err wasm-result))))

;; ADR 0050: mineralplant.governor (cloud-itonami-isco-8114) needs a
;; case-folded substring search over free text for its defense-in-depth
;; scope-exclusion check -- these two primitives compose to provide that:
;; `(string-contains? (string-fold-case haystack) (string-fold-case needle))`.
(def search-source
  "(ns string.search (:export [main contains fold contains-fold]))
   (defn main [] :i64 0)
   (defn contains [haystack :string needle :string] :i64
     (string-contains? haystack needle))
   (defn fold [value :string] :string
     (string-fold-case value))
   (defn contains-fold [haystack :string needle :string] :i64
     (string-contains? (string-fold-case haystack) (string-fold-case needle)))")

(deftest bounded-string-search-and-case-fold-have-cross-target-conformance
  (let [javascript (compiler/compile-source search-source :js-kotoba-v1)
        wasm (compiler/compile-source search-source :wasm32-browser-kotoba-v1)
        kir (:kir wasm)
        js64 (encoded (.getBytes ^String (:source javascript) "UTF-8"))
        wasm64 (encoded (:bytes wasm))
        checks (str "if(x.contains('final decision made','decision')!==1n)process.exit(2);"
                    "if(x.contains('final decision made','banana')!==0n)process.exit(3);"
                    "try{x.contains('abc','');process.exit(4)}catch(e){};"
                    "try{x.contains('','');process.exit(5)}catch(e){};"
                    "if(x.contains('x'.repeat(40000),'y'.repeat(30000))!==0n)process.exit(6);"
                    "if(x.fold('FINAL DECISION')!=='final decision')process.exit(7);"
                    "if(x.fold('CAFÉ')!=='café')process.exit(8);"
                    "if(x.contains('This Is The FINAL Decision','final decision')!==0n)process.exit(9);"
                    "if(x['contains-fold']('This Is The FINAL Decision','final decision')!==1n)process.exit(10);"
                    "if(x['contains-fold']('CAFÉ menu','café')!==1n)process.exit(11)")
        js-result (shell/sh "node" "--input-type=module" "-e"
                            (str "import('data:text/javascript;base64," js64
                                 "').then(m=>{const x=m.instantiateKotoba({});" checks "})"))
        wasm-result (shell/sh "node" "--input-type=module" "-e"
                              (str "import('./runtime/browser-host.mjs').then(async m=>{"
                                   "const h=await m.instantiateKotoba(Buffer.from(process.argv[1],'base64'));"
                                   "const x=h.instance.exports;" checks "})") wasm64)]
    (is (= 1 (ir/execute kir 'contains ["final decision made" "decision"])))
    (is (= 0 (ir/execute kir 'contains ["final decision made" "banana"])))
    (is (thrown? clojure.lang.ExceptionInfo (ir/execute kir 'contains ["abc" ""])))
    (is (thrown? clojure.lang.ExceptionInfo (ir/execute kir 'contains ["" ""])))
    (is (= "final decision" (ir/execute kir 'fold ["FINAL DECISION"])))
    (is (= "café" (ir/execute kir 'fold ["CAFÉ"])))
    (is (= 0 (ir/execute kir 'contains ["This Is The FINAL Decision" "final decision"])))
    (is (= 1 (ir/execute kir 'contains-fold
                         ["This Is The FINAL Decision" "final decision"])))
    (is (= 1 (ir/execute kir 'contains-fold ["CAFÉ menu" "café"])))
    (is (zero? (:exit js-result)) (:err js-result))
    (is (zero? (:exit wasm-result)) (:err wasm-result))))

;; kotoba-lang/search's re-seq tokenizer needs per-code-point classification
;; (a-z0-9 + Japanese Unicode ranges), which the byte-offset string ABI could
;; not express before string-code-point-at. This proves the op works across
;; all three targets AND that it composes with string-byte-length into a
;; real, UTF-8-correct tokenizer: count-alnum-run returns the byte length of
;; the maximal a-z0-9 run starting at byte 0 (the core of one tokenize step).
(def code-point-source
  "(ns string.codepoint (:export [main cp alnum-run-bytes]))
   (defn main [] :i64 0)
   (defn cp [s :string off :i64] :i64 (string-code-point-at s off))
   ;; UTF-8 byte width of a code point (guest-side, from its value).
   (defn cp-width [c :i64] :i64
     (if (< c 128) 1 (if (< c 2048) 2 (if (< c 65536) 3 4))))
   (defn alnum? [c :i64] :i64
     (if (if (< c 48) 0 (if (< c 58) 1 0)) 1
       (if (if (< c 97) 0 (if (< c 123) 1 0)) 1 0)))
   ;; Byte length of the maximal a-z0-9 run starting at byte 0.
   (defn alnum-run-bytes [s :string] :i64
     (let [n (string-byte-length s)]
       (loop [off 0]
         (if (< off n)
           (let [c (string-code-point-at s off)]
             (if (= 1 (alnum? c))
               (recur (+ off (cp-width c)))
               off))
           off))))")

(deftest string-code-point-at-has-cross-target-conformance-and-tokenizes
  (let [javascript (compiler/compile-source code-point-source :js-kotoba-v1)
        wasm (compiler/compile-source code-point-source :wasm32-browser-kotoba-v1)
        kir (:kir wasm)
        js64 (encoded (.getBytes ^String (:source javascript) "UTF-8"))
        wasm64 (encoded (:bytes wasm))
        ;; "aあ𝟘0": a@0=0x61, あ@1=0x3042(3B), 𝟘@4=0x1d7d8(4B), 0@8=0x30
        s "aあ𝟘0"
        checks (str "const s='a\\u3042\\ud835\\udfd80';"
                    "if(x.cp(s,0n)!==97n)process.exit(2);"
                    "if(x.cp(s,1n)!==12354n)process.exit(3);"
                    "if(x.cp(s,4n)!==120792n)process.exit(4);"
                    "if(x.cp(s,8n)!==48n)process.exit(5);"
                    "try{x.cp(s,2n);process.exit(6)}catch(e){}"
                    "try{x.cp(s,9n);process.exit(7)}catch(e){}"
                    ;; 'abc123 xyz' -> first alnum run is 'abc123' = 6 bytes
                    "if(x['alnum-run-bytes']('abc123 xyz')!==6n)process.exit(8);"
                    ;; leading separator -> empty run
                    "if(x['alnum-run-bytes'](' abc')!==0n)process.exit(9);"
                    ;; a Japanese code point is not a-z0-9 -> run stops at byte 0
                    "if(x['alnum-run-bytes'](s)!==1n)process.exit(10)")
        js-result (shell/sh "node" "--input-type=module" "-e"
                            (str "import('data:text/javascript;base64," js64
                                 "').then(m=>{const x=m.instantiateKotoba({});" checks "})"))
        wasm-result (shell/sh "node" "--input-type=module" "-e"
                              (str "import('./runtime/browser-host.mjs').then(async m=>{"
                                   "const h=await m.instantiateKotoba(Buffer.from(process.argv[1],'base64'));"
                                   "const x=h.instance.exports;" checks "})") wasm64)]
    (is (= 97 (ir/execute kir 'cp [s 0])))
    (is (= 0x3042 (ir/execute kir 'cp [s 1])))
    (is (= 0x1d7d8 (ir/execute kir 'cp [s 4])))
    (is (thrown? clojure.lang.ExceptionInfo (ir/execute kir 'cp [s 2])))
    (is (thrown? clojure.lang.ExceptionInfo (ir/execute kir 'cp [s 9])))
    (is (= 6 (ir/execute kir 'alnum-run-bytes ["abc123 xyz"])))
    (is (= 0 (ir/execute kir 'alnum-run-bytes [" abc"])))
    (is (= 1 (ir/execute kir 'alnum-run-bytes [s])))
    (is (zero? (:exit js-result)) (:err js-result))
    (is (zero? (:exit wasm-result)) (:err wasm-result))))
