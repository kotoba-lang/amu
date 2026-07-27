(ns kotoba.compiler.document-digest-style-test
  "W4 second slice (ADR-2607279200 Delivery 4):

  After document→HTML (compiler#339), lock two more exit-gate pieces:

  1. Deterministic structural identity of a logical document without a host
     object — a pure guest FNV-1a-style i64 fingerprint over the canonical
     tagged tree (code-point content, sorted map order). Equal documents
     agree; content-distinct documents disagree. (A first-class
     document-sha256 host op remains a follow-up; this proves the *identity*
     requirement with existing document-* ops.)

  2. Style vocabulary as ordinary :document values rendered to a CSS stream
     (selector + declaration list), parallel to the UI→HTML path — the Style
     half of 'Document/Style fixtures' in the W4 exit gate.

  DOM reconciliation remains out of scope."
  (:require [clojure.java.shell :as shell]
            [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]
            [kotoba.kir :as ir]
            [kotoba.kir.value :as value]))

(def fingerprint-source-fixed
  "(ns ui.document-fingerprint (:export [main same different world-fp other-fp]))
   (defn mix [h :i64 x :i64] :i64
     (bit-xor (* h 16777619) x))
   (defn hash-str-at [s :string i :i64 n :i64 h :i64] :i64
     (if (>= i n) h
       (hash-str-at s (+ i 1) n (mix h (string-code-point-at s i)))))
   (defn hash-str [s :string] :i64
     (hash-str-at s 0 (string-byte-length s) 2166136261))
   (defn hash-doc [d :document] :i64
     (if (= (document-kind d) :null) 1
     (if (= (document-kind d) :bool)
       (if (option-value-of [:option :bool] (document-bool-value d) false) 3 5)
     (if (= (document-kind d) :i64)
       (mix 7 (option-value-of [:option :i64] (document-i64-value d) 0))
     (if (= (document-kind d) :string)
       (mix 11 (hash-str (option-value-of [:option :string]
                          (document-string-value d) \"\")))
     (if (= (document-kind d) :keyword)
       (mix 13 (hash-str (keyword-name
                           (option-value-of [:option :keyword]
                             (document-keyword-value d) :missing))))
     (if (= (document-kind d) :vector)
       (hash-vec d 0 (document-count d) 17)
     (if (= (document-kind d) :map)
       (hash-map-entries d 0 (document-count d) 19)
       0))))))))
   (defn hash-vec [v :document i :i64 n :i64 h :i64] :i64
     (if (>= i n) h
       (hash-vec v (+ i 1) n
         (mix h (hash-doc (option-value-of [:option :document]
                           (document-vector-at v i) (document-null)))))))
   (defn hash-map-entries [m :document i :i64 n :i64 h :i64] :i64
     (if (>= i n) h
       (match-option (document-map-entry-at m i) [:option :document]
         (none h)
         (some entry
           (hash-map-entries m (+ i 1) n
             (mix (mix h (hash-doc (option-value-of [:option :document]
                                    (document-vector-at entry 0) (document-null))))
                  (hash-doc (option-value-of [:option :document]
                             (document-vector-at entry 1) (document-null)))))))))
   (defn page [] :document
     (document-map :tag (document-string \"div\")
       :children (document-vector
         (document-map :tag (document-string \"h1\") :text (document-string \"Hello\"))
         (document-map :tag (document-string \"p\") :text (document-string \"World\")))))
   (defn other-page [] :document
     (document-map :tag (document-string \"div\")
       :children (document-vector
         (document-map :tag (document-string \"h1\") :text (document-string \"Hello\"))
         (document-map :tag (document-string \"p\") :text (document-string \"Other\")))))
   (defn main [] :i64 (hash-doc (page)))
   (defn same [] :bool (if (= (hash-doc (page)) (hash-doc (page))) true false))
   (defn different [] :bool
     (if (= (hash-doc (page)) (hash-doc (other-page))) true false))
   (defn world-fp [] :i64 (hash-doc (document-string \"World\")))
   (defn other-fp [] :i64 (hash-doc (document-string \"Other\")))")

(def style-source
  "(ns ui.document-style (:export [main rule-card same different]))
   (defn prop-of [d :document] :string
     (option-value-of [:option :string]
       (document-string-value
         (option-value-of [:option :document]
           (document-get d :prop) (document-null)))
       \"\"))
   (defn value-of [d :document] :string
     (option-value-of [:option :string]
       (document-string-value
         (option-value-of [:option :document]
           (document-get d :value) (document-null)))
       \"\"))
   (defn sel-of [d :document] :string
     (option-value-of [:option :string]
       (document-string-value
         (option-value-of [:option :document]
           (document-get d :selector) (document-null)))
       \"*\"))
   (defn decls-of [d :document] :document
     (option-value-of [:option :document]
       (document-get d :decls) (document-vector)))
   (defn render-decl [d :document] :string
     (string-concat (prop-of d)
       (string-concat \": \" (string-concat (value-of d) \";\"))))
   (defn render-decls [decls :document i :i64 n :i64 acc :string] :string
     (if (>= i n) acc
       (render-decls decls (+ i 1) n
         (string-concat acc
           (string-concat
             (if (string=? acc \"\") \"\" \" \")
             (render-decl (option-value-of [:option :document]
                            (document-vector-at decls i) (document-null))))))))
   (defn render-rule [d :document] :string
     (string-concat (sel-of d)
       (string-concat \" { \"
         (string-concat (render-decls (decls-of d) 0 (document-count (decls-of d)) \"\")
           \" }\"))))
   (defn decl [prop :string value :string] :document
     (document-map :prop (document-string prop) :value (document-string value)))
   (defn rule [sel :string decls :document] :document
     (document-map :selector (document-string sel) :decls decls))
   (defn card [] :document
     (rule \".card\"
       (document-vector
         (decl \"color\" \"#fff\")
         (decl \"padding\" \"16px\"))))
   (defn main [] :string (render-rule (card)))
   (defn rule-card [] :string (render-rule (card)))
   (defn same [] :bool (document-equal? (card) (card)))
   (defn different [] :bool
     (document-equal? (card)
       (rule \".card\"
         (document-vector
           (decl \"color\" \"#000\")
           (decl \"padding\" \"16px\")))))")

(defn- script-probe [compiled javascript]
  (let [encoded (.encodeToString (java.util.Base64/getEncoder)
                                 (.getBytes ^String (:source compiled) "UTF-8"))]
    (shell/sh "node" "--input-type=module" "-e"
              (str "import('data:text/javascript;base64," encoded
                   "').then(m=>{const x=m.instantiateKotoba({});" javascript
                   "}).catch(e=>{console.error(e);process.exit(70)})"))))

(deftest structural-document-fingerprint-is-deterministic-and-content-sensitive
  (let [wasm (compiler/compile-source fingerprint-source-fixed :wasm32-kotoba-v1 {})
        script (compiler/compile-source fingerprint-source-fixed :js-kotoba-v1 {})
        kir (:kir wasm)
        page-fp (ir/execute kir 'main [])]
    (testing "KIR fingerprint is stable and content-sensitive"
      (is (int? page-fp))
      (is (true? (ir/execute kir 'same [])))
      (is (false? (ir/execute kir 'different [])))
      (is (not= (ir/execute kir 'world-fp [])
                (ir/execute kir 'other-fp []))))
    (testing "restricted ESM agrees on content-sensitive string fingerprints
              (full-page same/different stay KIR-only — ESM fuel budget is
              tight for deep recursive charge accounting)"
      (let [probe (script-probe script
                                (str "const w=x['world-fp'](); const o=x['other-fp']();"
                                     "if(typeof w!=='bigint'||typeof o!=='bigint')process.exit(2);"
                                     "if(w===o)process.exit(3);"))]
        (is (zero? (:exit probe)) (str (:err probe) "\n" (:out probe)))))))

(deftest style-document-renders-to-css-stream
  (let [wasm (compiler/compile-source style-source :wasm32-kotoba-v1 {})
        script (compiler/compile-source style-source :js-kotoba-v1 {})
        kir (:kir wasm)
        css ".card { color: #fff; padding: 16px; }"]
    (testing "KIR style document → CSS string"
      (is (= css (ir/execute kir 'main [])))
      (is (true? (ir/execute kir 'same [])))
      (is (false? (ir/execute kir 'different []))))
    (testing "restricted ESM agrees"
      (let [probe (script-probe script
                                (str "if(x.main()!==" (pr-str css) ")process.exit(2);"
                                     "const s=x.same(); const d=x.different();"
                                     "if(!(s===1n||s===true||s===1))process.exit(3);"
                                     "if(!(d===0n||d===false||d===0))process.exit(4);"))]
        (is (zero? (:exit probe)) (str (:err probe) "\n" (:out probe)))))
    (testing "style document admits under the same budgets as UI documents"
      (let [canon (fn [entries] ["map" (vec (sort-by (comp str first) entries))])
            color (canon [[:prop ["string" "color"]] [:value ["string" "#fff"]]])
            pad (canon [[:prop ["string" "padding"]] [:value ["string" "16px"]]])
            tree (canon [[:selector ["string" ".card"]]
                         [:decls ["vector" [color pad]]]])]
        (is (= (value/bounded-document! tree)
               (value/bounded-document! tree)))))))
