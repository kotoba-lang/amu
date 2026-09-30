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
            with-status (map (fn [c] [c (unencodable? (:form c))]) (concat unique synthetic-forms deep-forms))
            cases (vec (take limit (map first (filter (comp nil? second) with-status))))
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
