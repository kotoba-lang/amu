;; Differential harness for the Kotoba-route type-model helpers of kotoba-sema's frontend.cljk
;; (selfhost core rewrite S3, docs/selfhost-frontend-typemodel-design.md).
;;
;; HOST side: the frontend's own functions (`hex-text?`, `rodata-literal-content?`, `interrupt-entry-vector`,
;; `alloc-region-bytes`, `map-literal-record-type`, `record-descriptor`, the descriptor predicates,
;; `callable-clauses`, `slice-element-type`, `check-reader-depth!`, `validate-value-type!`,
;; `heterogeneous-vector-index!`, `resolve-ref-type`, `record-field-type`), called on a corpus; each answer
;; is a short line.
;; KOTOBA side: the `:kotoba` branches of the SAME functions, extracted from frontend.cljk by
;; `tm-gen.py` (reader conditionals expanded, definitions picked by name from tm-names.txt) into one
;; module with `tm-tail.cljk` appended, linked as a project and run on the KIR interpreter.
;; Expected values that are Forms (descriptors) are computed on the host, printed to EDN, and compared
;; INSIDE the guest with `form/eq`, so the printed line is `true` when the guest's Form equals the host's data.
;;
;; Env: KROOTS (colon-separated src roots incl. lang/compat), TM_GUEST (path of the generated module).
(ns tm-diff
  (:require ["node:fs" :as fs]
            [clojure.string :as str]
            [kotoba.sema :as sema]
            [kotoba.kir :as kir]
            [kotoba.compiler.project :as project]
            [kotoba.compiler.project-files :as pf]
            [kotoba.compiler.frontend :as fe]))

(set! *print-namespace-maps* false)
(def env js/process.env)
(def roots (vec (str/split (.-KROOTS env) #":")))
(def guest-path (.-TM_GUEST env))
(def show (if-let [v (.-TM_SHOW env)] (js/parseInt v) 10))

(defn fe-var [sym] @(resolve (symbol "kotoba.compiler.frontend" (name sym))))
(defn call [sym & args] (apply (fe-var sym) args))

(defn strip [m] (str/replace (str m) #" ;;DBGFN.*$" ""))
(defn msg [f] (try (f) (catch :default e (str "ERR " (ex-message e)))))
(defn b->s [b] (if b "true" "false"))
(defn edn [x] (pr-str x))

;; ---- corpora ---------------------------------------------------------------------------

(def hex-strings ["" "0" "00" "ab" "AB" "aB09" "abc" "0g" "zz" "0123456789abcdefABCDEF" "0123456789abcdefABCDEFg"
                  "12345678" "1234567" " 1" "-1" "0x" "DEADBEEF" "deadbeeg" "fF" "G0"])
(def guid-strings ["00000000-0000-0000-0000-000000000000" "12345678-1234-1234-1234-123456789abc"
                   "12345678-1234-1234-1234-123456789ABC" "12345678-1234-1234-1234-123456789abg"
                   "12345678-1234-1234-1234-123456789ab" "12345678-1234-1234-1234-123456789abcd"
                   "1234567-81234-1234-1234-123456789abc" "12345678123412341234123456789abc"
                   "12345678-1234-1234-123456789abc" "" "-" "----" "12345678-1234-1234-1234-12345678-abc"
                   "1234567g-1234-1234-1234-123456789abc" "GGGGGGGG-GGGG-GGGG-GGGG-GGGGGGGGGGGG"])
(def rodata-ops '[ucs2 guid bytes-literal bytes-literal-length other])
(def rodata-texts (concat hex-strings guid-strings ["hello" "abc" "a-b"]))
(def isr-names ["aiueos-isr-0" "aiueos-isr-1" "aiueos-isr-63" "aiueos-isr-64" "aiueos-isr-65" "aiueos-isr-00"
                "aiueos-isr-01" "aiueos-isr-" "aiueos-isr-bp" "aiueos-isr-1x" "aiueos-isr--1" "aiueos-isr-99999"
                "aiueos-isr-10" "aiueos-isr-9" "aiueos-isr-007" "isr-1" "x-aiueos-isr-1" "aiueos-isr-123456789012345678" "aiueos-isr-1234567890123456789012"])
(def alloc-forms ['(kernel-uefi-alloc-region a b c d 4 e) '(kernel-uefi-alloc-region a b c d e 3 f)
                  '(kernel-uefi-alloc-region a b c d e 3) '(kernel-uefi-alloc-region a b c d e 1 f)
                  '(kernel-uefi-alloc-region a b c d e 0 f) '(kernel-uefi-alloc-region a b c d e x f)
                  '(kernel-uefi-alloc-region a b c d e "3" f) '(other a b c d e 3 f) 'kernel-uefi-alloc-region
                  '[kernel-uefi-alloc-region a b c d e 3 f] '(kernel-uefi-alloc-region a b c d e -2 f)
                  '(kernel-uefi-alloc-region a b c d e 1099511627776 f)])

(def field-sets [[[:a :i64]] [[:a :i64] [:b :string]] [[:a :i64] [:containment/status :bool]]
                 [[:x/y :i64] [:x/z :string] [:w [:option :i64]]] [[:a [:list :i64]]]
                 [[:aa :i64] [:b [:record :k/R [[:f :i64]]]]]])
(def rec-cases [['x.y 'R [{:name 'a :type :i64}]] ['x.y 'R [{:name 'a :type :i64} {:name 'b :type [:option :string]}]]
                ['a.b.c 'Long-Name [{:name 'field-one :type :string} {:name 'f2 :type [:list :i64]}]]])

(def types [:i64 :string :bool :f64 :bytes [:option :i64] [:option [:list :string]] [:list :i64] [:list [:list :i64]]
            [:stream :i64] [:task :i64] [:vector :i64] [:set :string] [:map :string :i64]
            [:record :a/R [[:x :i64] [:y :string]]] [:record :a/R] [:variant :a/V [[:a :i64] [:b :string]]]
            [:result :i64 :string] [:ref :a/R] [:ref :b] [:ref :a/R :c] [:slice :u8] [:slice :f32]
            [:fn [[:i64] :i64]] [:fn [[:i64] :i64] [[:i64 :i64] :i64]] [:fn 1] [:fn] [:fn 1 2 3 4 5 6]
            [:option] [:list :a :b] [:map :string] nil 1 "x" 'sym {:a 1} :a/b [:x] []
            [:option [:option [:option :i64]]] [:record :a/R [[:x :i64] [:x :string]]]
            [:record :nons [[:x :i64]]] [:list :nonsense] [:set :f64] [:map :f64 :i64]])

(def vt-types
  (concat types
          [[:list [:list [:list [:list [:list :i64]]]]]
           (reduce (fn [t _] [:list t]) :i64 (range 70))
           [:variant :a/V []] [:record :a/R []] [:variant :a/V [[:a :f64]]]
           [:result :i64 :i64] [:option [:fn [[:i64] :i64]]] [:stream :i64] [:stream [:stream :i64]]]))

(def schema-maps [{} {:a/R [:record :a/R [[:x :i64] [:y :string]]]} {:a/R :i64 :b/S [:list :string]} nil {:a/R nil}])
(def ref-types [[:ref :a/R] [:ref :b/S] [:ref :c/T] [:ref :a] [:list :i64] :i64 [:ref :a/R :x] [:ref "s"]
                [:record :a/R [[:x :i64] [:y :string]]] [:record :q/Q [[:z [:option :i64]]]]])
(def field-keys [:x :y :z :nope 'x "x" nil])

(def depth-sources
  ["" "(" "()" "[[[]]]" (apply str (repeat 512 "(")) (apply str (repeat 513 "(")) (str (apply str (repeat 300 "(")) (apply str (repeat 300 ")")) (apply str (repeat 300 "(")))
   (str "\"" (apply str (repeat 600 "(")) "\"") (str ";" (apply str (repeat 600 "(")) "\n(a)")
   (str "\"\\\"" (apply str (repeat 600 "(")) "\"") (apply str (repeat 511 "[")) (apply str (repeat 600 "}"))
   (str (apply str (repeat 400 "{")) (apply str (repeat 400 "}")) (apply str (repeat 400 "{")))
   "(a ; ( ( (\n b)" "\"unterminated ((((" (str "\\" (apply str (repeat 600 "(")))])

(def hidx-items [[] [:i64] [:i64 :string] [:i64 :string :bool]])
(def hidx-indexes [0 1 2 3 -1 100 :a "x" nil 'x])

;; ---- cases: [edn-of-case-for-guest host-answer-line] -----------------------------------------

(defn the-cases []
  (concat
   (for [s hex-strings] [(str "[:hex " (edn s) "]") (b->s (call 'hex-text? s))])
   (for [op rodata-ops t (concat rodata-texts [nil 12 :k])]
     [(str "[:rodata " (edn op) " " (edn t) "]") (b->s (call 'rodata-literal-content? op t))])
   (for [n isr-names]
     [(str "[:interrupt " (edn (symbol n)) "]") (let [v (call 'interrupt-entry-vector (symbol n))] (if (nil? v) "nil" (str v)))])
   (for [f alloc-forms]
     [(str "[:alloc " (edn f) "]") (let [v (call 'alloc-region-bytes f)] (if (nil? v) "nil" (str v)))])
   (for [fs field-sets]
     [(str "[:mlrt " (edn fs) " " (edn (call 'map-literal-record-type fs)) "]") "true"])
   (for [[n r ps] rec-cases]
     [(str "[:rd " (edn n) " " (edn r) " " (edn ps) " " (edn (call 'record-descriptor n r ps)) "]") "true"])
   (for [t types]
     [(str "[:bits " (edn t) "]")
      (apply str (map (comp b->s #(call % t))
                      '[callable-type? parametric-result-type? variant-type? generic-option-type?
                        canonical-list-type? stream-type? task-type? linear-resource-type?
                        heterogeneous-vector-type? typed-set-type? canonical-typed-map-type? record-type?
                        schema-ref-type? slice-type? structured-type? option-vector-type?]))])
   (for [t types]
     [(str "[:clauses " (edn t) " " (edn (call 'callable-clauses t)) "]") "true"])
   (for [t types]
     [(str "[:sliceelt " (edn t) " " (edn (call 'slice-element-type t)) "]") "true"])
   (for [s depth-sources]
     [(str "[:depth " (edn s) "]")
      (b->s (try (call 'check-reader-depth! s) false (catch :default _ true)))])
   (for [t (remove #{[:fn 1]} vt-types)]
     [(str "[:vt " (edn t) "]") (try (call 'validate-value-type! t) "ok" (catch :default e (strip (ex-message e))))])
   (for [i hidx-indexes items hidx-items]
     [(str "[:hidx " (edn i) " " (edn items) "]")
      (try (str (call 'heterogeneous-vector-index! i items nil)) (catch :default e (strip (ex-message e))))])
   (for [i hidx-indexes items hidx-items]
     [(str "[:hslice " (edn i) " " (edn items) "]")
      (try (str (call 'heterogeneous-vector-slice-index! i items nil)) (catch :default e (strip (ex-message e))))])
   (for [x [0 1 -5 "s" :k 'a nil [1] true]]
     [(str "[:intlit " (edn x) "]") (b->s (call 'integer-literal? x))])
   (for [sm schema-maps t ref-types]
     [(str "[:resolve " (edn t) " " (edn sm) " " (edn (binding [fe/*schemas* sm] (call 'resolve-ref-type t))) "]") "true"])
   (for [sm schema-maps t ref-types k field-keys]
     [(str "[:rft " (edn t) " " (edn k) " " (edn sm) " " (edn (binding [fe/*schemas* sm] (call 'record-field-type t k))) "]") "true"])))

;; ---- guest ---------------------------------------------------------------------------------

(defn load-guest []
  (let [graph (pf/load-closed-graph guest-path roots)
        linked (project/link-source (:sources graph) (:root graph))
        hir (sema/analyze (:source linked) {:admit-linked-synthetics? true})]
    (kir/lower hir)))

(defn run-guest [lowered text]
  (kir/execute lowered 'tm-run [text] {:fuel 100000000000 :frames 100000 :cells 1000000000 :bytes 1000000000}))

(defn ascii? [s] (not (re-find #"[^\x09\x0a\x20-\x7e]" s)))

(defn -main []
  (let [cs (vec (remove (fn [[c _]] (str/includes? c "\n")) (map (fn [[c h]] [c (str h)]) (the-cases))))
        cs (vec (filter (fn [[c _]] (ascii? c)) cs))
        _ (println "cases:" (count cs) "linking guest ...")
        lowered (load-guest)
        batch 200
        rows (atom [])]
    (doseq [part (partition-all batch cs)]
      (let [text (str (str/join "\n" (map first part)) "\n")
            out (run-guest lowered text)
            out (if (map? out) (or (:value out) (throw (ex-info "guest trap" {:out (pr-str out)}))) out)
            lines (str/split out #"\n" -1)]
        (doseq [[[c h] g] (map vector part lines)]
          (swap! rows conj [c h g]))))
    (let [rows @rows
          bad (remove (fn [[_ h g]] (= h g)) rows)]
      (println "agree:" (- (count rows) (count bad)) "/" (count rows) " disagree:" (count bad))
      (doseq [[c h g] (take show bad)]
        (println "DISAGREE" (subs c 0 (min 200 (count c))) "\n  host :" h "\n  guest:" g))
      (js/process.exit (if (seq bad) 1 0)))))

(-main)
