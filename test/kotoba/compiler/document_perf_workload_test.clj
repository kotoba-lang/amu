(ns kotoba.compiler.document-perf-workload-test
  "W4 ninth slice (ADR-2607279200 Delivery 4 / migration plan W4):

  Harder performance evidence for recursive logical documents *before*
  selecting HAMT / vector-trie / arena / rope implementations.

  Sixth slice only recorded a soft 200× render of a 16-leaf tree under 5s.
  This slice runs a fuller W4 pipeline (construct → HTML → sha256 → print →
  read → equal?) on a larger admitted tree, against KIR (elevated fuel) and
  restricted ESM (default fuel envelope), with tighter wall-clock budgets.

  Complements slices 1–8. Does not claim HAMT selection or :ui/commit (W5)."
  (:require [clojure.java.shell :as shell]
            [clojure.string :as str]
            [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]
            [kotoba.kir :as ir]
            [kotoba.kir.value :as value]))

;; ~4 sections × 8 leaves — stays under document-node-limit 256 and ESM
;; default fuel 512 for a single pipeline iteration of main.
(def heavy-source
  (str
   "(ns ui.document-heavy (:export [html dig printed round-ok kids main]))"
   " (defn leaf [tag :string text :string] :document"
   "   (document-map :tag (document-string tag) :text (document-string text)))"
   " (defn node [tag :string children :document] :document"
   "   (document-map :tag (document-string tag) :children children))"
   " (defn section [prefix :string] :document"
   "   (node \"section\""
   "     (document-vector"
   "       (leaf \"li\" (string-concat prefix \"-0\"))"
   "       (leaf \"li\" (string-concat prefix \"-1\"))"
   "       (leaf \"li\" (string-concat prefix \"-2\"))"
   "       (leaf \"li\" (string-concat prefix \"-3\"))"
   "       (leaf \"li\" (string-concat prefix \"-4\"))"
   "       (leaf \"li\" (string-concat prefix \"-5\"))"
   "       (leaf \"li\" (string-concat prefix \"-6\"))"
   "       (leaf \"li\" (string-concat prefix \"-7\")))))"
   " (defn page [] :document"
   "   (node \"div\""
   "     (document-vector"
   "       (section \"s00\") (section \"s01\")"
   "       (section \"s02\") (section \"s03\"))))"
   " (defn tag-of [d :document] :string"
   "   (option-value-of [:option :string]"
   "     (document-string-value"
   "       (option-value-of [:option :document]"
   "         (document-get d :tag) (document-null)))"
   "     \"div\"))"
   " (defn text-of [d :document] :string"
   "   (option-value-of [:option :string]"
   "     (document-string-value"
   "       (option-value-of [:option :document]"
   "         (document-get d :text) (document-null)))"
   "     \"\"))"
   " (defn kids-of [d :document] :document"
   "   (option-value-of [:option :document]"
   "     (document-get d :children) (document-vector)))"
   " (defn render-kids [kids :document i :i64 n :i64 acc :string] :string"
   "   (if (>= i n) acc"
   "     (render-kids kids (+ i 1) n"
   "       (string-concat acc"
   "         (render (option-value-of [:option :document]"
   "                   (document-vector-at kids i) (document-null)))))))"
   " (defn render [d :document] :string"
   "   (if (string=? (text-of d) \"\")"
   "     (string-concat \"<\""
   "       (string-concat (tag-of d)"
   "         (string-concat \">\""
   "           (string-concat (render-kids (kids-of d) 0 (document-count (kids-of d)) \"\")"
   "             (string-concat \"</\" (string-concat (tag-of d) \">\"))))))"
   "     (string-concat \"<\""
   "       (string-concat (tag-of d)"
   "         (string-concat \">\""
   "           (string-concat (text-of d)"
   "             (string-concat \"</\" (string-concat (tag-of d) \">\"))))))))"
   " (defn html [] :string (render (page)))"
   " (defn dig [] :string (document-sha256 (page)))"
   " (defn printed [] :string (document-print (page)))"
   " (defn round-ok [] :bool"
   "   (document-equal? (page) (document-read (document-print (page)))))"
   " (defn kids [] :i64 (document-count (kids-of (page))))"
   ;; Single-pass main: build once, dig+print+read+eq without re-rendering HTML
   ;; so default ESM fuel 512 can complete one iteration.
   " (defn main [] :i64"
   "   (let [p (page)"
   "         pr (document-print p)"
   "         r (document-read pr)]"
   "     (if (document-equal? p r)"
   "       (+ (document-count (kids-of p)) 1)"
   "       0)))"))

(def ^:private kir-fuel 65536)

(defn- run
  ([kir sym] (ir/execute kir sym [] {:fuel kir-fuel}))
  ([kir sym args] (ir/execute kir sym args {:fuel kir-fuel})))

(defn- script-probe [compiled javascript]
  (let [encoded (.encodeToString (java.util.Base64/getEncoder)
                                 (.getBytes ^String (:source compiled) "UTF-8"))]
    (shell/sh "node" "--input-type=module" "-e"
              (str "import('data:text/javascript;base64," encoded
                   "').then(m=>{" javascript
                   "}).catch(e=>{console.error(e);process.exit(70)})"))))

(defn- ms-since [t0]
  (/ (double (- (System/nanoTime) t0)) 1.0e6))

(defn- truthy? [v]
  (or (true? v) (= v 1) (= v 1N)))

(deftest heavy-document-pipeline-kir-workload
  (let [compiled (compiler/compile-source heavy-source :js-kotoba-v1)
        kir (:kir compiled)
        _ (run kir 'main)
        kids (run kir 'kids)
        html (run kir 'html)
        dig (run kir 'dig)
        printed (run kir 'printed)
        t0 (System/nanoTime)
        results (doall (repeatedly 100 #(run kir 'main)))
        elapsed (ms-since t0)
        sample (first results)]
    (testing "heavy tree shape is admitted and non-trivial"
      (is (= 4 kids))
      (is (str/includes? html "<section>"))
      (is (str/includes? html "s03-7"))
      (is (re-matches #"[0-9a-f]{64}" dig))
      (is (re-matches #"[0-9a-f]+" printed))
      (is (truthy? (run kir 'round-ok)))
      (is (pos? sample))
      (is (every? #(= sample %) results)))
    (testing "100× construct/print/read/eq under harder budget (elevated fuel)"
      (is (< elapsed 3000.0)
          (str "100 pipelines took " elapsed " ms (harder budget 3000 ms)"))
      (println "W4-ninth KIR heavy pipeline:" elapsed "ms for 100 iters; main=" sample))))

(deftest heavy-document-pipeline-esm-workload
  (let [compiled (compiler/compile-source heavy-source :js-kotoba-v1)
        t0 (System/nanoTime)
        ;; Fresh instantiateKotoba per iter restores default fuel=512 (shared
        ;; fuel would exhaust mid-loop on a multi-section tree).
        probe (script-probe
               compiled
               (str "let last=null;"
                    "for(let i=0;i<50;i++){"
                    "  const x=m.instantiateKotoba({});"
                    "  const v=x.main();"
                    "  if(last!==null&&v!==last)process.exit(2);"
                    "  last=v;"
                    "}"
                    "if(typeof last!=='bigint'||last<=0n)process.exit(3);"
                    "if(m.instantiateKotoba({}).kids()!==4n)process.exit(4);"
                    "const h=m.instantiateKotoba({}).html();"
                    "if(!h.includes('s03-7')||!h.includes('<section>'))process.exit(5);"
                    "if(!/^[0-9a-f]{64}$/.test(m.instantiateKotoba({}).dig()))process.exit(6);"
                    "const p=m.instantiateKotoba({}).printed();"
                    "if(!/^[0-9a-f]+$/.test(p))process.exit(7);"
                    "const t=v=>v===true||v===1n||v===1;"
                    "if(!t(m.instantiateKotoba({})['round-ok']()))process.exit(8);"
                    "console.log('ok '+String(last));"))
        elapsed (ms-since t0)]
    (testing "50× construct/print/read/eq on restricted ESM under harder budget"
      (is (zero? (:exit probe)) (str (:err probe) (:out probe)))
      (is (str/starts-with? (:out probe) "ok "))
      (is (< elapsed 4000.0)
          (str "ESM 50 pipelines took " elapsed " ms (harder budget 4000 ms)"))
      (println "W4-ninth ESM heavy pipeline:" elapsed "ms;" (str/trim (:out probe))))))

(deftest host-value-path-near-budget-workload
  (let [leaf (fn [i]
               ["map" [[:tag ["string" "span"]]
                       [:text ["string" (str "n" i)]]]])
        group (fn [g]
                ["map" [[:children
                         ["vector" (mapv leaf (range (* g 4) (+ (* g 4) 4)))]]
                        [:tag ["string" "g"]]]])
        tree ["map" [[:children ["vector" (mapv group (range 16))]]
                     [:tag ["string" "root"]]]]
        t0 (System/nanoTime)
        digests (doall
                 (repeatedly 100
                   (fn []
                     (let [d (value/bounded-document! tree)
                           p (value/document-print d)
                           r (value/document-read p)]
                       (assert (= d r))
                       (value/document-sha256-hex r)))))
        elapsed (ms-since t0)]
    (testing "100× host construct/print/read/sha256 under 2s"
      (is (= 1 (count (set digests))))
      (is (re-matches #"[0-9a-f]{64}" (first digests)))
      (is (< elapsed 2000.0)
          (str "100 host round-trips took " elapsed " ms (harder budget 2000 ms)"))
      (println "W4-ninth host value plane:" elapsed "ms for 100 iters"))))
