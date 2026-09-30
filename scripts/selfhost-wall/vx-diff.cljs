;; Differential harness for the Kotoba-route `validate-expr` (kotoba-sema
;; src/kotoba/compiler/validate_expr.cljk, selfhost core rewrite S3 slice 2).
;;
;; HOST side: `kotoba.compiler.frontend/validate-expr` itself, called on each case with a fresh
;; budget; its outcome is "OK <nodes charged>" or "<:kotoba.error/code> <ex-message>".
;; KOTOBA side: the guest module linked as a project, lowered, and run on the KIR interpreter
;; (`kir/execute`), one batch of cases per call; its outcome is the same two-part line.
;;
;; CORPUS (all from the sema tests, nothing invented): every string literal in
;; kotoba-sema/test/**/*.cljk (and every fixture) is tried as a program (as written when it starts
;; with `(ns`, else under a bare `(ns m.p)`); `sema/analyze` is run on it with `validate-expr`
;; wrapped, and each OUTERMOST call the analyser makes -- the desugared expression with the locals
;; and function arities it really had -- becomes a case. --nested also records every nested call.
;; A small hand-written set of refusal probes is added (the SYNTHETIC group) so every message the
;; slice can produce is exercised at least once.
;;
;; Usage (see vx-diff.sh):  KROOTS=<colon-separated src roots> KTEST=<kotoba-sema/test dir> \
;;   nbb ... vx-diff.cljs [--nested] [--limit N] [--show K]
(ns vx-diff
  (:require ["node:fs" :as fs]
            [cljs.reader]
            [clojure.string :as str]
            [clojure.walk :as walk]
            [kotoba.sema :as sema]
            [kotoba.kir :as kir]
            [kotoba.compiler.project :as project]
            [kotoba.compiler.project-files :as pf]
            [kotoba.compiler.frontend :as fe]))

(def env js/process.env)
(def roots (vec (str/split (.-KROOTS env) #":")))
(def test-dir (.-KTEST env))
(def argv (vec (drop 1 (js->clj (.-argv js/process)))))
(def opt-nested? (some #{"--nested"} argv))
(defn opt [k default] (if-let [i (some (fn [[a i]] (when (= a k) i)) (map vector argv (range)))]
                        (js/parseInt (nth argv (inc i))) default))
(def limit (opt "--limit" 1000000))
(def show (opt "--show" 12))
(def skip-batches (opt "--skip-batches" 0))
(def batch-bytes (opt "--batch-bytes" 60000))
;; --only-file F: rerun only the cases a previous results file answered with `vx/unsupported` or a disagreement
(defn opt-str [k] (when-let [i (some (fn [[a i]] (when (= a k) i)) (map vector argv (range)))] (nth argv (inc i))))
(def only-forms
  (when-let [f (opt-str "--only-file")]
    (set (keep (fn [line]
                 (let [[_ form h g] (cljs.reader/read-string line)]
                   (when (or (str/starts-with? g "vx/unsupported") (not= h g)) form)))
               (remove str/blank? (str/split-lines (fs/readFileSync f "utf8")))))))
;; every answered case is appended here as [synthetic? form host-line guest-line], batch by batch
(def results-file (or (.-VX_RESULTS env) "/tmp/vx-diff-results.edn"))
(when-not (some #{"--append"} argv) (try (fs/writeFileSync results-file "") (catch :default _ nil)))

;; ---- corpus: strings out of the test sources --------------------------------

(defn files-under [dir suffixes]
  (mapcat (fn [n]
            (let [p (str dir "/" n)]
              (cond (.isDirectory (fs/statSync p)) (files-under p suffixes)
                    (some #(str/ends-with? n %) suffixes) [p]
                    :else [])))
          (sort (js->clj (fs/readdirSync dir)))))

(defn unescape [s]
  (str/replace s #"\\(.)" (fn [[_ c]] (case c "n" "\n" "t" "\t" "r" "\r" c))))

(defn regex-strings [text]
  (map (comp unescape second) (re-seq #"\"((?:[^\"\\]|\\.)*)\"" text)))

(defn strings-of-file [f]
  (let [text (fs/readFileSync f "utf8")]
    (try (let [acc (atom [])]
           (walk/postwalk (fn [y] (when (string? y) (swap! acc conj y)) y) (vec (fe/read-forms text)))
           @acc)
         (catch :default _ (regex-strings text)))))

(def test-files (files-under test-dir [".cljk"]))
(def fixture-programs
  (keep (fn [f] (try (fs/readFileSync f "utf8") (catch :default _ nil)))
        (files-under test-dir [".kotoba"])))

(def candidate-strings
  (distinct (concat (mapcat strings-of-file test-files) fixture-programs)))

(defn program-variants [s]
  (cond (not (str/includes? s "(")) []
        (str/starts-with? (str/triml s) "(ns ") [s]
        :else [(str "(ns m.p {:kotoba/export [main]})\n" s)]))

;; ---- the tap ------------------------------------------------------------------

(def orig fe/validate-expr)
(def captured (atom []))
(def nest (atom 0))
(defn arities [functions] (into {} (map (fn [[k v]] [k (count v)])) functions))
(set! fe/validate-expr
      (fn [form locals functions depth budget]
        (when (or opt-nested? (zero? @nest))
          (swap! captured conj {:form form :locals locals :functions (arities functions) :depth depth}))
        (swap! nest inc)
        (try (orig form locals functions depth budget) (finally (swap! nest dec)))))

(defn harvest! [programs]
  (doseq [p programs]
    (reset! nest 0)
    (try (sema/analyze p) (catch :default _ nil))))

;; ---- synthetic refusal probes ---------------------------------------------------

(def synthetic-forms
  (let [L '#{x y} F {'f 2 'g 0}]
    (mapv (fn [[form locals fns]] {:form form :locals locals :functions fns :depth 0 :synthetic true})
          [['(+ x 1) L F] ['x L F] ['zed L F] ['xx L F] ['(f x y) L F] ['(f x) L F] ['(g x) L F]
           ['(frob x) L F] ['(fro x) L F] ['(pair x y) L F] ['(pair x) L F] ['(quot x) L F]
           ['(+) L F] ['(/ x) L F] ['(< x) L F] ['(< x y) L F] ['(i64-shift-left x 64) L F]
           ['(i64-shift-left x y) L F] ['(i64-shift-left x 3) L F] ['(i32-shift-left x y) L F]
           ['(i32-shift-left x 3) L F] ['(i32-shift-left x 32) L F] ['(bit-not x y) L F]
           ['(let [x 1 x 2] x) L F] ['(let [z 1] z) L F] ['(let [z] z) L F] ['(let x 1) L F]
           ['(let [z 1] z z) L F] ['(let [z 1]) L F] ['(let [z zz] z) L F] ['(let [f/z 1] 1) L F]
           ['(let [load 1] 1) L F] ['(let [z 1 w (+ z 1)] (+ z w)) L F] ['(let [z (+ z 1)] z) L F]
           ['(if x y) L F] ['(if x y y y) L F] ['(if x y y) L F] ['(do) L F] ['(do x y) L F]
           ['(cap-call 3 x) L F] ['(cap-call 300 x) L F] ['(cap-call 3) L F] ['(cap-call x x) L F]
           ['(kotoba.reader/regex "a") L F] ['(kotoba.reader/js 1) L F] ['(kotoba.reader/set 1) L F]
           ['(kotoba.reader/char 1) L F] ['(a/b x) L F] ['(load x) L F] ['(foo.bar x) L F] ['(.x y) L F]
           ['(() x) L F] ['(1 x) L F] ['(:k x) L F] ['() L F] ['[x] L F] ['{:a x} L F] ['nil L F]
           ["s" L F] [:kw L F] [true L F] [7 L F]
           ['(map-new :a) L F] ['(map-get 1 2) L F] ['(map-assoc x :a) L F] ['(map-assoc x :a y) L F]
           ['(bytes-empty x) L F] ['(bytes-empty) L F] ['(bytes-count) L F] ['(bytes-at x) L F]
           ['(bytes-slice x y) L F] ['(bytes-concat x) L F] ['(string-from-utf8 x y) L F]
           ['(string-from-utf8 x) L F] ['(vector-new x y) L F]
           ['(string-byte-length x y) L F] ['(string-substring x) L F] ['(string=? x y) L F]
           ['(document-map x) L F] ['(document-vector x y) L F] ['(document-map x y) L F]
           ['(kernel-uefi-alloc-region 1 2 3 4 x 6) L F] ['(kernel-uefi-alloc-region 1 2 3 4 0 6) L F]
           ['(kernel-uefi-alloc-region 1 2 3 4 5 6) L F] ['(kernel-uefi-alloc-region 1 2) L F]
           ['(kernel-function-address f) L F] ['(kernel-function-address x) L F]
           ['(kernel-function-address nope) L F] ['(kernel-function-address 3) L F]
           ['(when x y) L F] ['(cond x y) L F] ['(loop [] 1) L F] ['(fn [] 1) L F]
           ['(typed-list-new [:list :i64] x) L F] ['(record-get [:record :a/b [[:x :i64]]] x :x) L F]
           ['(kernel-store-u8 x y) L F] ['(kernel-store-u8 x y 1) L F]
           ['(vector-i64 x) L F] ['(vector-at x) L F] ['(vector-count x y) L F]
           ['(a b c d e f g h i j k l m) L F]
           ['(if (< x y) (let [q (+ x y)] (* q q)) (f x y)) L F]
           ['(zzzzzzzzzz x) L F] ['(string-substrin x y z) L F] ['(string-substrng x y z) L F]])))

(defn nested-deep [n]
  (nth (iterate (fn [f] (list 'do f)) 1) n))
;; Not probed: a keyword longer than 512 bytes. The host refuses it in `validate-expr`
;; ("keyword exceeds UTF-8 byte limit"); on the Kotoba route it cannot reach the pass, because
;; `keyword-from-string` (the Form reader) traps first -- a Form holds no over-limit keyword.
(def deep-forms
  [{:form (nested-deep 100) :locals #{} :functions {} :depth 0 :synthetic true}
   {:form (nested-deep 300) :locals #{} :functions {} :depth 0 :synthetic true}
   {:form (nested-deep 10) :locals #{} :functions {} :depth 250 :synthetic true}
   {:form (apply list '+ (repeat 300 1)) :locals #{} :functions {} :depth 0 :synthetic true}
   {:form (apply list 'vector-new (repeat 129 1)) :locals #{} :functions {} :depth 0 :synthetic true}
   {:form (apply list 'document-vector (repeat 33 1)) :locals #{} :functions {} :depth 0 :synthetic true}])


;; ---- descriptor probes: every type-descriptor head, mutated -----------------------------------
;; Each template is a valid form; the mutations drop / add an operand, swap the descriptor for a
;; bad one, a wrong-kind one, one with a bad inside, and make the last operand unbound.
(def tl '[:list :i64])
(def ts '[:set :i64])
(def tm '[:map :i64 :i64])
(def tr '[:record :a/r [[:f :i64] [:g :i64]]])
(def th '[:vector [:i64 :string]])
(def to '[:option :i64])
(def tv '[:variant :a/v [[:p :i64] [:q :string]]])
(def tres '[:result :i64 :string])

(def head-templates
  [(list 'typed-list-new tl) (list 'typed-list-new tl 'x 'y) (list 'typed-list-conj tl 'x 'y) (list 'typed-list-nth tl 'x 'y)
   (list 'typed-set-new ts 'x) (list 'typed-set-count ts 'x) (list 'typed-set-contains ts 'x 'y)
   (list 'typed-set-conj ts 'x 'y) (list 'typed-set-disj ts 'x 'y) (list 'typed-set-equal ts 'x 'y)
   (list 'typed-set-nth ts 'x 'y)
   (list 'typed-map-new tm 1 2) (list 'typed-map-count tm 'x) (list 'typed-map-contains tm 'x 'y)
   (list 'typed-map-get tm 'x 'y) (list 'typed-map-dissoc tm 'x 'y) (list 'typed-map-entry-at tm 'x 'y)
   (list 'typed-map-keys tm 'x) (list 'typed-map-vals tm 'x) (list 'typed-map-assoc tm 'x 'y 'y)
   (list 'typed-map-equal tm 'x 'y)
   (list 'record-new tr 'x 'y) (list 'record-get tr 'x :f) (list 'record-assoc tr 'x :f 'y) (list 'record-equal tr 'x 'y)
   (list 'hetero-vector-new th 'x 'y) (list 'hetero-vector-count th 'x) (list 'hetero-vector-at th 'x 0)
   (list 'hetero-vector-assoc th 'x 1 'y) (list 'hetero-vector-equal th 'x 'y)
   (list 'option-none-of to) (list 'option-some-of to 'x) (list 'option-some?-of to 'x) (list 'option-value-of to 'x 'y)
   (list 'option-match to 'x 'y 'z '(+ z 1))
   (list 'variant-new tv :p 'x) (list 'variant-match tv 'x '[[:p a a] [:q b 1]])
   (list 'result-match-of tres 'x 'a 'a 'b 1)
   (list 'result-ok-of tres 'x) (list 'result-err-of tres 'x) (list 'result-ok?-of tres 'x)
   (list 'result-value-of tres 'x 'y) (list 'result-error-of tres 'x 'y)
   (list 'typed-cap-call 3 :i64 :i64 'x) (list 'typed-cap-call 3 tl to 'x)])

(defn wrong-kind [t] (if (= t tl) ts tl))
(defn head-mutations [form]
  (let [[op t & more] form
        args (vec more)]
    (concat
     [form
      (apply list op t (conj args 'x))
      (list* op :banana more)
      (list* op (wrong-kind t) more)
      (list* op '[:list :banana] more)
      (list* op 'x more)]
     (when (seq args)
       [(apply list op t (pop args))
        (apply list op t (conj (pop args) 'zed))
        (apply list op t (conj (vec (butlast args)) 'zed 'x))]))))

(def type-probes
  (let [rec (fn [n] (vec (concat [:record :a/r] [(vec (for [i (range n)] [(keyword (str "f" i)) :i64]))])))
        deep (fn [n] (nth (iterate (fn [t] [:list t]) :i64) n))
        big-rec (fn [k] [:vector (vec (repeat k (rec 32)))])]
    ['[:fn [[:i64] :i64]] '[:fn [[:i64] [:fn [[:i64] :i64]]]] '[:fn [[:i64] :keyword]] '[:fn [[:keyword] :i64]]
     '[:fn [[:i64] :i64] [[:i64] :i64]] '[:fn [[:i64] :i64 :i64]] '[:fn [[[:fn [[:i64] :i64]]] :i64]]
     '[:fn [[[:stream :bytes]] :i64]] '[:fn [[:i64] [:record :a/r [[:x :i64]]]]]
     '[:fn [[:i64] [:variant :a/v [[:p :bool]]]]] '[:fn [[:i64] [:result :bool :bool]]]
     '[:fn [[:i64] [:result :bool :i64]]] '[:fn [[:i64] [:option :bool]]] '[:fn [[:i64] [:vector [:bool]]]]
     '[:fn [[:i64] [:record :a/r [[:x [:ref :a/q]]]]]] '[:fn [[:i64] [:ref :a/q]]]
     '[:fn [[:i64 :i64 :i64 :i64] :i64] [[:i64] :i64] [[:i64 :i64] :i64] [[:i64 :i64 :i64] :i64] [[] :i64]]
     '[:fn [[:i64 :i64 :i64 :i64 :i64] :i64]] '[:fn [[:i64] :banana]] '[:fn [[:banana] :i64]]
     '[:fn [[:i64] [:set :i64]]] '[:fn [[:i64] [:map :string :i64]]] '[:fn [[:i64] [:list :keyword]]]
     '[:fn [[:i64] [:variant :a/v [[:p :bool] [:q :string]]]]] '[:fn [[:i64] [:result :string :bool]]]
     '[:fn [[:i64] [:task [:stream :bytes]]]] '[:fn [[:i64] [:stream :bytes]]]
     ;; not probed: a callable clause that is not a vector (`[:fn 1]`). The host computes the clause arities
     ;; BEFORE its shape check, so it dies with an internal "1 is not ISeqable" where the guest refuses with
     ;; kotoba.error/callable-type. That is a host defect on malformed input, not behaviour to reproduce.
     '[:stream :bytes] '[:stream :i64] '[:task [:stream :bytes]] '[:task :i64]
     '[:slice :u8] '[:slice :f32] '[:slice :i64] '[:slice [:slice :u8]] '[:slice :u64]
     '[:set :f64] '[:set :f32] '[:set :i64] '[:set :string] '[:map :f32 :i64] '[:map :i64 :f64] '[:map :string :i64]
     '[:record x [[:a :i64]]] '[:record :a/r []] '[:record :a/r [[:a :i64] [:a :string]]] '[:record :a/r [1]]
     '[:record :a/r [[:a :i64 :i64]]] '[:record :a/r [[:a :i64]] 3] '[:record :a/r :x]
     '[:variant x [[:a :i64]]] '[:variant :a/v []] '[:variant :a/v [[:a :i64] [:a :string]]] '[:variant :a/v [[:a :banana]]]
     '[:ref :a/b] '[:ref :b] '[:ref] '[:vector :i64] '[:vector [:i64 :banana]]
     '[:option :i64] '[:option :banana] '[:option] '[:list] '[:banana :i64] :i64 :banana :string-index :document
     'x 3 "s" '(:list :i64) '[]
     (rec 32) (rec 33) (deep 60) (deep 64) (deep 65) (deep 70)
     [:vector (vec (repeat 32 :i64))] [:vector (vec (repeat 33 :i64))] (big-rec 3) (big-rec 8) (big-rec 15) (big-rec 16)
     [:vector (vec (repeat 32 '[:vector [:i64 :i64 :i64 :i64 :i64 :i64 :i64 :i64 :i64 :i64 :i64 :i64 :i64 :i64 :i64 :i64]]))]])) 

(def descriptor-specials
  [(list 'typed-list-new tl) (apply list 'typed-list-new tl (repeat 128 'x)) (apply list 'typed-list-new tl (repeat 129 'x))
   (apply list 'typed-set-new ts (repeat 32 'x)) (apply list 'typed-set-new ts (repeat 33 'x))
   (apply list 'typed-map-new tm (repeat 62 'x)) (apply list 'typed-map-new tm (repeat 64 'x)) (list 'typed-map-new tm 1)
   (list 'typed-map-new) (list 'typed-list-new) (list 'record-new tr 'x) (list 'record-new tr 'x 'y 'x) (list 'record-new tr)
   (list 'record-get tr 'x :nope) (list 'record-get tr 'x 'f) (list 'record-get tr 'x 3) (list 'record-get ts 'x :f)
   (list 'record-assoc tr 'x :nope 'y) (list 'record-assoc tr 'x :g 'zed) (list 'record-assoc tr 'zed :g 'zed)
   (list 'hetero-vector-new th 'x) (list 'hetero-vector-new th 'x 'y 'x) (list 'hetero-vector-new tl 'x)
   (list 'hetero-vector-at th 'x 2) (list 'hetero-vector-at th 'x -1) (list 'hetero-vector-at th 'x 'y)
   (list 'hetero-vector-at th 'x "a") (list 'hetero-vector-at th 'x 1) (list 'hetero-vector-assoc th 'x 2 'y)
   (list 'hetero-vector-assoc th 'x 'y 'y) (list 'hetero-vector-assoc tl 'x 0 'y)
   (list 'option-match to 'x 'y 'z 'z) (list 'option-match to 'x 'y 'a/z 'z) (list 'option-match to 'x 'y 3 'z)
   (list 'option-match to 'x 'zed 'z 'z) (list 'option-match to 'x 'y 'z 'zed) (list 'option-match to 'x 'y 'z 'x)
   (list 'option-match to 'x 'y 'z) (list 'option-match ts 'x 'y 'z 'z)
   (list 'variant-new tv :p 'x) (list 'variant-new tv 'p 'x) (list 'variant-new tv :p) (list 'variant-new tl :p 'x)
   (list 'variant-new tv :nope 'x) (list 'variant-new tv :p 'zed)
   (list 'variant-match tv 'x '[[:p a a] [:q b b]]) (list 'variant-match tv 'x '[[:q a a] [:p b b]])
   (list 'variant-match tv 'x '[[:p a a]]) (list 'variant-match tv 'x '[[:p a a] [:q b b] [:r c c]])
   (list 'variant-match tv 'x '[[:p a/a a] [:q b b]]) (list 'variant-match tv 'x '[[:p a] [:q b b]])
   (list 'variant-match tv 'x '[[:p 1 a] [:q b b]]) (list 'variant-match tv 'x '[[:p a a] [:q b zed]])
   (list 'variant-match tv 'x '[[:p a a] [:q b a]]) (list 'variant-match tv 'x '([:p a a] [:q b b]))
   (list 'variant-match tv 'x 5) (list 'variant-match tl 'x '[[:p a a]]) (list 'variant-match tv 'zed '[[:p a a] [:q b b]])
   (list 'result-match-of tres 'x 'a 'a 'b 'b) (list 'result-match-of tres 'x 'a/a 'a 'b 'b)
   (list 'result-match-of tres 'x 'a 'a 'b 'a) (list 'result-match-of tres 'x 'a 'b 'b 'a) (list 'result-match-of tres 'x 'a 'a 'b 'zed)
   (list 'result-match-of ts 'x 'a 'a 'b 'b) (list 'result-match-of '[:result :i64 :banana] 'x 'a 'a 'b 'b)
   (list 'result-match-of tres 'x 3 'a 'b 'b) (list 'result-match-of tres 'x 'a 'a 'b)
   (list 'result-ok-of ts 'x) (list 'result-ok-of '[:result :banana :i64] 'x) (list 'result-ok-of tres 'zed)
   (list 'result-value-of tres 'x) (list 'result-value-of tres 'x 'y 'z)
   (list 'typed-cap-call 3 :i64 :i64 'x) (list 'typed-cap-call 256 :i64 :i64 'x) (list 'typed-cap-call -1 :i64 :i64 'x)
   (list 'typed-cap-call 'x :i64 :i64 'x) (list 'typed-cap-call 3 :i64 :i64) (list 'typed-cap-call 3 :i64 :i64 'x 'y)
   (list 'typed-cap-call 3 :banana :i64 'x) (list 'typed-cap-call 3 :i64 :banana 'x) (list 'typed-cap-call 3 :i64 :i64 'zed)
   (list 'typed-cap-call 3 :banana :banana 'zed)])

(defn probe-case [form] {:form form :locals '#{x y} :functions {'f 2 'g 0} :depth 0 :synthetic true})
(def descriptor-forms
  (vec (concat (map probe-case (mapcat head-mutations head-templates))
               (map probe-case descriptor-specials)
               (map (fn [t] (probe-case (list 'typed-list-new t))) type-probes)
               (map (fn [t] (probe-case (list 'typed-cap-call 1 t :i64 'x))) (filter vector? type-probes)))))

;; ---- host outcome ------------------------------------------------------------------

(defn clip [s] (if (> (count s) 200) (subs s 0 200) s))
(defn host-line [{:keys [form locals functions depth]}]
  (let [budget (volatile! 0)
        fns (into {} (map (fn [[k n]] [k (vec (repeat n 'p))])) functions)]
    (clip
     (try (orig form locals fns depth budget)
          (str "OK " @budget)
          (catch :default e
            (let [d (ex-data e)]
              (if (:phase d)
                (str (subs (str (:kotoba.error/code d)) 1) " " (ex-message e))
                (str "HOST-INTERNAL " (ex-message e)))))))))

;; ---- EDN for the guest -----------------------------------------------------------

(def safe-int (js/BigInt 9007199254740991))
(defn unencodable? [x]
  (let [bad (atom nil)]
    (walk/postwalk
     (fn [y]
       (cond (nil? y) y
             (boolean? y) y
             (or (string? y) (keyword? y) (symbol? y)) (do (when (re-find #"[^\x20-\x7e]" (str y)) (reset! bad :non-ascii)) y)
             (or (integer? y) (identical? js/BigInt (type y))) (do (when (> (js/Math.abs (js/Number y)) 9007199254740991) (reset! bad :big-int)) y)
             (number? y) (do (reset! bad :float) y)
             (or (seq? y) (vector? y) (set? y) (map? y) (map-entry? y)) y
             :else (do (reset! bad (str "type " (type y))) y)))
     x)
    @bad))

(defn enc [x]
  (cond (nil? x) "nil"
        (boolean? x) (str x)
        (string? x) (pr-str x)
        (or (keyword? x) (symbol? x)) (str x)
        (or (integer? x) (identical? js/BigInt (type x))) (str x)
        (set? x) (str "#{" (str/join " " (map enc x)) "}")
        (map? x) (str "{" (str/join " " (mapcat (fn [[k v]] [(enc k) (enc v)]) x)) "}")
        (vector? x) (str "[" (str/join " " (map enc x)) "]")
        (seq? x) (str "(" (str/join " " (map enc x)) ")")
        :else (throw (ex-info "cannot encode" {:x (str x)}))))

(defn case-edn [{:keys [form locals functions depth]}]
  (str "[" (enc form) " " (enc (vec (sort-by str locals))) " " (enc functions) " " depth "]"))

;; ---- the guest ----------------------------------------------------------------------

(def guest-main
  (str "(ns probe.vx-main\n  {:kotoba/export [vx-run]}\n  (:require [kotoba.compiler.validate-expr :as vx])\n"
       "  (:schemas {:form/r [:record :form/r [[:tag :i64] [:s :string] [:n :i64] [:k :keyword] [:kids [:list [:ref :form/r]]] [:span :i64] [:data :bytes]]]}))\n"
       "(defn vx-run [text :string] :string (vx/run-batch text))\n"))

(defn load-guest []
  (let [root "/tmp/probe_vx_main.cljk"]
    (.writeFileSync fs root guest-main)
    (let [graph (pf/load-closed-graph root roots)
          linked (project/link-source (:sources graph) (:root graph))
          hir (sema/analyze (:source linked) {:admit-linked-synthetics? true})]
      (kir/lower hir))))

(defn run-batch [lowered text]
  (kir/execute lowered 'vx-run [text] {:fuel 100000000000 :frames 100000 :cells 1000000000 :bytes 1000000000}))

(defn batches [cases]
  (let [prefix (str "[" (enc (set fe/forbidden-heads))
                    " " (enc (set fe/grammar-declared-heads)) "]\n")]
    (loop [cs cases cur [] size 0 out []]
      (if-let [c (first cs)]
        (let [s (case-edn c) n (+ (count s) 2)]
          (cond
            ;; a case that cannot fit in a batch of its own is dropped (counted by the caller)
            (> (+ n (count prefix)) batch-bytes)
            (recur (rest cs) cur size out)
            (or (>= (count cur) 250) (> (+ size n (count prefix)) batch-bytes))
            (recur cs [] 0 (conj out cur))
            :else (recur (rest cs) (conj cur [c s]) (+ size n) out)))
        (if (seq cur) (conj out cur) out)))))

;; ---- main -------------------------------------------------------------------------------

(defn classify [host guest]
  (cond (str/starts-with? guest "vx/unsupported") :unsupported
        (= host guest) :agree
        :else :disagree))

(defn batch-text [b]
  (str "[" (enc (set fe/forbidden-heads)) " " (enc (set fe/grammar-declared-heads)) "]\n"
       (str/join "\n" (map second b))))

;; Run batch B; if the guest raises (a trap, a limit), halve the batch until the offending case
;; stands alone, and report that case's answer as "GUEST-ERROR <message>".
(defn run-guarded [lowered b]
  (try (let [out (str/split-lines (run-batch lowered (batch-text b)))]
         (if (= (count out) (count b))
           out
           (throw (ex-info "line count mismatch" {:got (count out) :want (count b)}))))
       (catch :default e
         (if (<= (count b) 1)
           [(clip (str "GUEST-ERROR " (ex-message e)))]
           (let [h (quot (count b) 2)]
             (println "  batch raised (" (ex-message e) "); splitting" (count b) "->" h "+" (- (count b) h))
             (vec (concat (run-guarded lowered (subvec b 0 h)) (run-guarded lowered (subvec b h)))))))))

(defn report []
  (let [rows (mapv cljs.reader/read-string (remove str/blank? (str/split-lines (fs/readFileSync results-file "utf8"))))
        by (group-by (fn [[_ _ h g]] (classify h g)) rows)
        stat (fn [label xs]
               (let [g (group-by (fn [[_ _ h g]] (classify h g)) xs)]
                 (println (format "%-22s cases=%5d agree=%5d disagree=%4d unsupported=%5d"
                                  label (count xs) (count (:agree g)) (count (:disagree g)) (count (:unsupported g))))))]
    (println "----")
    (stat "ALL" rows)
    (stat "from sema tests" (remove first rows))
    (stat "synthetic probes" (filter first rows))
    (let [in-slice (remove (fn [[_ _ h g]] (= :unsupported (classify h g))) rows)]
      (println (format "in-slice agreement: %d / %d" (count (filter (fn [[_ _ h g]] (= h g)) in-slice)) (count in-slice))))
    (println "host OK:" (count (filter (fn [[_ _ h _]] (str/starts-with? h "OK ")) rows))
             " host refusals:" (count (remove (fn [[_ _ h _]] (str/starts-with? h "OK ")) rows)))
    (println "distinct host refusal messages agreeing with the guest:"
             (count (distinct (map (fn [[_ _ h _]] h) (filter (fn [[_ _ h g]] (and (= h g) (not (str/starts-with? h "OK ")))) rows)))))
    (doseq [[_ f h g] (take show (:disagree by))]
      (println "\nDISAGREE form:" (subs f 0 (min 300 (count f))) "\n  host :" h "\n  guest:" g))
    (println "\nguest-unsupported heads:"
             (pr-str (take 30 (sort-by (comp - val) (frequencies (map (fn [[_ _ _ g]] g) (:unsupported by)))))))))

(defn -main []
  (if (some #{"--report"} argv)
    (report)
    (do
      (println "test files:" (count test-files) " candidate strings:" (count candidate-strings))
      (harvest! (mapcat program-variants candidate-strings))
      (set! fe/validate-expr orig)
      (let [harvested @captured
            _ (println "captured validate-expr calls:" (count harvested) (if opt-nested? "(all)" "(outermost)"))
            keyed (reduce (fn [m c] (let [k (pr-str [(:form c) (sort-by str (:locals c)) (sort-by str (:functions c)) (:depth c)])]
                                      (if (contains? m k) m (assoc m k c))))
                          (array-map) harvested)
            unique (vec (vals keyed))
            with-status (map (fn [c] [c (unencodable? (:form c))]) (if (some #{"--descriptors-only"} argv) descriptor-forms (concat unique synthetic-forms deep-forms (if (some #{"--descriptors"} argv) descriptor-forms []))))
            cases (vec (take limit (filter #(or (nil? only-forms) (contains? only-forms (pr-str (:form %))))
                                           (map first (filter (comp nil? second) with-status)))))
            skipped (frequencies (keep second with-status))
            lowered (do (println "linking guest ...") (load-guest))]
        (println "unique cases:" (count unique) "+ synthetic" (+ (count synthetic-forms) (count deep-forms))
                 " unencodable (skipped):" skipped)
        (let [bs (batches cases)]
          (println "batches:" (count bs))
          (doseq [[bi b] (map-indexed vector bs) :when (>= bi skip-batches)]
            (let [t0 (js/Date.now)
                  out (run-guarded lowered b)]
              (println (str "batch " bi "/" (count bs) ": " (count b) " cases, " (- (js/Date.now) t0) " ms"))
              (doseq [[[c _] g] (map vector b out)]
                (fs/appendFileSync results-file
                                   (str (pr-str [(boolean (:synthetic c)) (pr-str (:form c)) (host-line c) g]) "\n")))))
          (report))))))

(-main)
