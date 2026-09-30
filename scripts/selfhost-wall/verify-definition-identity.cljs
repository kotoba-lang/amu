;; Byte-for-byte check of the Kotoba reading of kotoba.compiler.definition-identity (and, through it,
;; kotoba.kir.definition-identity, alpha-normalization, cbor and multiformats) against the host.
;;
;; For each ROOT source file it links the project, analyzes it on the host (the module's own functions are
;; the repo's real definitions), asks the HOST for the per-definition identity report, then hands the same
;; HIR / KIR (as `:form/r` Forms) to the Kotoba `definitions` running on the KIR interpreter, and compares the
;; listing (`name<TAB>cid`) and the SCANNED line. CIDs are hashes of the canonical bytes, so equal CIDs are
;; equal bytes.
;;
;;   KROOTS=<colon-separated source roots: every classpath src dir, this repo's src, kotoba-lang lang/compat>
;;   FILES=<comma-separated root .cljk files>          (default: kotoba/kir/alpha_normalization.cljk of KROOTS)
;;   SYNTH=1                                            also run the synthetic cases (cycles, refusals, f32)
;;   run with a large stack: ulimit -s 65500; node --stack-size=60000 nbb ... verify-definition-identity.cljs
;;
;; Prints one line per case, `ok` or `FAIL <first differing line>`; exits 1 on any failure.
(ns verify-definition-identity
  (:require ["node:fs" :as fs]
            [clojure.string :as str]
            [kotoba.sema :as sema]
            [kotoba.kir :as kir]
            [kotoba.compiler.project :as project]
            [kotoba.compiler.project-files :as pf]
            [kotoba.compiler.definition-identity :as host-di]
            [kotoba.compiler.capability-names :as cap-names]))

(def roots (vec (str/split (.-KROOTS js/process.env) #":")))

;; ---- the wire format the guest decoder reads (see `decoder-source`) ---------------------------------------
;; 0 nil | 1 false | 2 true | 3 i64 (8 bytes, big endian) | 4 string (u32 len, utf-8) | 5 keyword (u32 len,
;; ns/name) | 6 symbol | 7 list (u32 n, n items) | 8 vector | 9 set | 10 map (u32 pairs, 2n items) | 11 f64 bits (8)

(defn- push-u32 [out n]
  (doseq [s [24 16 8 0]] (.push out (bit-and (unsigned-bit-shift-right n s) 255))))

(defn- push-i64 [out x]
  (let [hex (.padStart (.toString (js/BigInt.asUintN 64 (js/BigInt x)) 16) 16 "0")]
    (doseq [i (range 8)] (.push out (js/parseInt (subs hex (* 2 i) (+ 2 (* 2 i))) 16)))))

(defn- push-text [out tag text]
  (let [b (js/Array.from (.encode (js/TextEncoder.) text))]
    (.push out tag)
    (push-u32 out (.-length b))
    (doseq [c b] (.push out c))))

(defn- f64-bits [x]
  (let [buf (js/ArrayBuffer. 8)]
    (.setFloat64 (js/DataView. buf) 0 x false)
    (.getBigUint64 (js/DataView. buf) 0 false)))

(defn- enc [out x]
  (cond
    (nil? x) (.push out 0)
    (false? x) (.push out 1)
    (true? x) (.push out 2)
    (keyword? x) (push-text out 5 (subs (str x) 1))
    (symbol? x) (push-text out 6 (str x))
    (string? x) (push-text out 4 x)
    (identical? js/BigInt (.-constructor x)) (do (.push out 3) (push-i64 out x))
    (number? x) (if (js/Number.isInteger x)
                  (do (.push out 3) (push-i64 out x))
                  (do (.push out 11) (push-i64 out (f64-bits x))))
    (map? x) (do (.push out 10) (push-u32 out (count x))
                 (doseq [[k v] x] (enc out k) (enc out v)))
    (set? x) (do (.push out 9) (push-u32 out (count x)) (doseq [e x] (enc out e)))
    (vector? x) (do (.push out 8) (push-u32 out (count x)) (doseq [e x] (enc out e)))
    (or (seq? x) (list? x)) (do (.push out 7) (push-u32 out (count x)) (doseq [e x] (enc out e)))
    :else (throw (ex-info "cannot encode" {:x (pr-str x)}))))

(defn- bytes-of [x]
  (let [out (array)]
    (enc out x)
    out))

;; ---- the guest: a decoder for the wire format and a main that runs `definitions` ----------------------------

(def decoder-source
  "(ns probe.di-verify
  {:kotoba/export [check-case]}
  (:require [kotoba.compiler.definition-identity :as cdi]
            [kotoba.form :as form]
            [multiformats.core :as mf])
  (:schemas {:form/r [:record :form/r [[:tag :i64] [:s :string] [:n :i64] [:k :keyword]
                                       [:kids [:list [:ref :form/r]]] [:span :i64] [:data :bytes]]]
             :dec/r [:record :dec/r [[:form [:ref :form/r]] [:pos :i64]]]}))

(defn- dr [f [:ref :form/r] p :i64] [:ref :dec/r] (record-new [:ref :dec/r] f p))
(defn- dr-form [r [:ref :dec/r]] [:ref :form/r] (record-get [:ref :dec/r] r :form))
(defn- dr-pos [r [:ref :dec/r]] :i64 (record-get [:ref :dec/r] r :pos))

(defn- rd-u32 [d :vector-i64 p :i64] :i64
  (+ (+ (* (vector-at d p) 16777216) (* (vector-at d (+ p 1)) 65536))
     (+ (* (vector-at d (+ p 2)) 256) (vector-at d (+ p 3)))))

(defn- rd-i64 [d :vector-i64 p :i64] :i64
  (loop [i 0 acc 0]
    (if (>= i 8)
      acc
      (recur (+ i 1) (+ (* acc 256) (vector-at d (+ p i)))))))

(defn- slice-bytes [d :vector-i64 p :i64 n :i64] :bytes
  (bytes-from-vector-i64
   (loop [i 0 acc (vector-i64)]
     (if (>= i n)
       acc
       (recur (+ i 1) (vector-conj acc (vector-at d (+ p i))))))))

(defn- rd-text [d :vector-i64 p :i64 n :i64] :string
  (string-from-utf8 (slice-bytes d p n)))

(defn- dec-kids [d :vector-i64 p :i64 n :i64] [:ref :dec/r]
  (loop [i 0 q p acc (form/no-forms)]
    (if (>= i n)
      (dr (form/form-vec acc) q)
      (let [r (dec-one d q)]
        (recur (+ i 1) (dr-pos r) (form/append-form acc (dr-form r)))))))

(defn- coll-of [k :i64 kids [:ref :form/r]] [:ref :form/r]
  (if (= k 7)
    (form/form-seq (form/kids-of kids))
    (if (= k 8)
      (form/form-vec (form/kids-of kids))
      (if (= k 9)
        (form/form-set (form/kids-of kids))
        (form/form-map (form/kids-of kids))))))

(defn- dec-one [d :vector-i64 p :i64] [:ref :dec/r]
  (let [k (vector-at d p)]
    (cond
      (= k 0) (dr (form/nil-form) (+ p 1))
      (= k 1) (dr (form/bool-form false) (+ p 1))
      (= k 2) (dr (form/bool-form true) (+ p 1))
      (= k 3) (dr (form/int-form (rd-i64 d (+ p 1))) (+ p 9))
      (= k 11) (dr (form/f64-form (rd-i64 d (+ p 1))) (+ p 9))
      (= k 4) (let [n (rd-u32 d (+ p 1))]
                (dr (form/string-form (rd-text d (+ p 5) n)) (+ (+ p 5) n)))
      (= k 5) (let [n (rd-u32 d (+ p 1))]
                (dr (form/keyword-form (keyword-from-string (rd-text d (+ p 5) n))) (+ (+ p 5) n)))
      (= k 6) (let [n (rd-u32 d (+ p 1))]
                (dr (form/symbol-form (rd-text d (+ p 5) n)) (+ (+ p 5) n)))
      (= k 10) (let [n (rd-u32 d (+ p 1))
                     r (dec-kids d (+ p 5) (* n 2))]
                 (dr (coll-of 10 (dr-form r)) (dr-pos r)))
      :else (let [n (rd-u32 d (+ p 1))
                  r (dec-kids d (+ p 5) n)]
              (dr (coll-of k (dr-form r)) (dr-pos r))))))

(defn- join-forms [xs [:ref :form/r] i :i64 out :string] :string
  (if (>= i (form/count-of xs))
    out
    (join-forms xs (+ i 1)
                (if (= i 0)
                  (form/string-value (form/nth-of xs i))
                  (string-concat (string-concat out \",\") (form/string-value (form/nth-of xs i)))))))

(defn- material-line [m [:ref :form/r]] :string
  (if (= 0 (form/tag-of m))
    \"MATERIAL nil\"
    (string-concat
     (string-concat (string-concat \"MATERIAL \" (string-from-i64 (cdi/definition-count m))) \" \")
     (string-concat (join-forms (form/form-get m (form/keyword-form :definitions)) 0 \"\")
                    (string-concat \" | \" (join-forms (form/form-get m (form/keyword-form :exports)) 0 \"\"))))))

(defn check-case [d :vector-i64] :string
  (let [root (dr-form (dec-one d 0))
        hir (form/nth-of root 0)
        kir (form/nth-of root 1)
        catalog (form/nth-of root 2)
        report (cdi/definitions hir kir catalog)
        result (form/assoc-form (form/assoc-form (form/form-map (form/no-forms)) (form/keyword-form :hir) hir)
                                (form/keyword-form :kir) kir)
        described (cdi/describe result catalog)]
    (string-concat
     (string-concat (string-concat (cdi/joined report) \"\\n\") (cdi/scanned-line report))
     (string-concat (string-concat \"\\n\" (material-line (cdi/cache-material report (form/nth-of root 3))))
                    (string-concat \"\\n\" (cdi/joined described))))))
")

(defn- fn-keys [f ks] (into {} (keep (fn [k] (when (contains? f k) [k (get f k)]))) ks) )

(defn- guest-input [hir k]
  [{:functions (mapv #(fn-keys % [:name :param-types :result :body]) (:functions hir))
    :named-operations (:named-operations hir)}
   {:functions (mapv #(fn-keys % [:name :params :param-types :result :effects :body]) (:functions k))
    :schemas (:schemas k)}
   cap-names/id->name
   (mapv :name (take 2 (:functions k)))])

(defn- vector-arg [bytes]
  (into [] (map js/BigInt) bytes))

;; One link of the guest for all the cases (the compiler chain is the slow part, not the run). The wire bytes
;; arrive as a `:vector-i64` argument: a module's string literals are capped (65536 bytes), a vector is not.
(defn- run-guests [inputs]
  (let [args (mapv (fn [[hir k]] (vector-arg (bytes-of (guest-input hir k)))) inputs)
        path "/tmp/probe_di_verify.cljk"
        _ (.writeFileSync fs path decoder-source)
        graph (pf/load-closed-graph path roots)
        linked (project/link-source (:sources graph) (:root graph))
        ghir (sema/analyze (:source linked) {:admit-linked-synthetics? true})
        program (kir/lower ghir)]
    (mapv (fn [arg]
            (try (kir/execute program 'check-case [arg]
                              {:fuel 100000000000 :frames 20000 :cells 1000000000 :bytes 1000000000})
                 (catch :default e
                   (str "ERROR " (ex-message e) " " (some-> (ex-data e) pr-str (subs 0 300))))))
          args)))

(defn- host-listing [hir k]
  (let [report (host-di/definitions hir k)
        material (host-di/cache-material report (mapv :name (take 2 (:functions k))))]
    (str (host-di/joined report) "\n" (host-di/scanned-line report) "\n"
         (if material
           (str "MATERIAL " (host-di/definition-count material) " " (str/join "," (:definitions material))
                " | " (str/join "," (:exports material)))
           "MATERIAL nil")
         "\n" (host-di/joined (host-di/describe {:hir hir :kir k})))))

(defn- compare-case [label hir k got]
  (let [want (host-listing hir k)
        ok (= want got)]
    (println (if ok "ok  " "FAIL") label (count (:functions k)) "definitions")
    (when-not ok
      (let [wl (str/split-lines want) gl (str/split-lines (str got))
            i (count (take-while true? (map = wl gl)))]
        (println "  first difference at line" i)
        (println "  want:" (nth wl i nil))
        (println "  got: " (nth gl i nil))))
    ok))

(defn- node-count [form] (count (tree-seq coll? seq form)))

;; The KIR interpreter running the Kotoba `definitions` is slow, so a run can be bounded: MAX_NODES keeps only
;; the functions whose body has at most that many nodes and MAX_FNS at most that many of them. A function that
;; calls a dropped one sees a free symbol, on the host and on the guest alike, so the comparison stays exact.
(defn- bounded [hir k]
  (let [max-nodes (some-> (.-MAX_NODES js/process.env) js/parseInt)
        max-fns (some-> (.-MAX_FNS js/process.env) js/parseInt)
        keep? (fn [f] (or (nil? max-nodes) (<= (node-count (:body f)) max-nodes)))
        kept (cond->> (filter keep? (:functions k)) max-fns (take max-fns))
        names (set (map :name kept))]
    [(update hir :functions (fn [fs] (filterv #(contains? names (:name %)) fs)))
     (assoc k :functions (vec kept))]))

(defn- analyze-file [path]
  (let [graph (pf/load-closed-graph path roots)
        linked (project/link-source (:sources graph) (:root graph))
        hir (sema/analyze (:source linked) {:admit-linked-synthetics? true})]
    (bounded hir (kir/lower hir))))

;; ---- synthetic modules: cycles, refusals, f32, blocked callees ---------------------------------------------

(defn- fnm [nm params body & {:as extra}]
  (merge {:name nm :params params :param-types (vec (repeat (count params) :i64)) :result :i64
          :effects #{} :body body} extra))

(def synthetic
  {"cycle-2" {:hir {:functions [] :named-operations #{}}
              :kir {:functions [(fnm 'even? '[n] '(if (= n 0) 1 (odd? (- n 1))))
                                (fnm 'odd? '[n] '(if (= n 0) 0 (even? (- n 1))))
                                (fnm 'main '[] '(even? 10))]}}
   "cycle-3-renamed" {:hir {:functions [] :named-operations #{}}
                      :kir {:functions [(fnm 'a '[n] '(b (+ n 1)))
                                        (fnm 'b '[n] '(c (+ n 2)))
                                        (fnm 'c '[n] '(if (> n 9) n (a n)))]}}
   "self-recursion" {:hir {:functions [] :named-operations #{}}
                     :kir {:functions [(fnm 'fact '[n] '(if (<= n 1) 1 (* n (fact (- n 1)))))]}}
   "shadowed-binders" {:hir {:functions [] :named-operations #{}}
                       :kir {:functions [(fnm 'f '[x] '(let [x (+ x 1) y (* x 2)] (+ x y)))
                                         (fnm 'g '[a b] '(let [t (+ a b)] (let [t (* t t)] t)))]}}
   "refusals" {:hir {:functions [] :named-operations #{}}
               :kir {:functions [(fnm 'ok-fn '[] '(+ 1 2))
                                 (fnm 'bad-row '[] '(cap-call 200 1) :effects #{[:cap/call 200]})
                                 (fnm 'caller-of-bad '[] '(bad-row))
                                 (fnm 'aborts '[] '(assert false) :effects #{:abort})]}}
   "big-and-f64" {:hir {:functions [] :named-operations #{}}
                  :kir {:functions [(fnm 'k1 '[] (list '+ (js/BigInt "9007199254740993") (js/BigInt "-9223372036854775808")))
                                    (fnm 'k2 '[] '(f64-add 1.5 2.25) :result :f64)]}}
   "f32-module" {:hir {:functions [{:name 'h :param-types [:f32] :result :i64 :body '(f32-to-bits x)}]
                       :named-operations #{}}
                 :kir {:functions [(fnm 'h '[x] '(f32-to-bits x))]}}})

;; ---- driver ---------------------------------------------------------------------------------------------------

(defn- default-files []
  (let [rel "kotoba/kir/alpha_normalization.cljk"]
    [(some (fn [r] (let [p (str r "/" rel)] (when (.existsSync fs p) p))) roots)]))

(let [files (if-let [f (.-FILES js/process.env)] (remove empty? (str/split f #",")) (default-files))
      cases (concat
             (for [f files
                   :let [[hir k] (analyze-file f)]]
               [f hir k])
             (when (.-SYNTH js/process.env)
               (for [[label {:keys [hir kir]}] synthetic]
                 [(str "synthetic " label) hir kir])))
      got (run-guests (map (fn [[_ hir k]] [hir k]) cases))
      results (doall (map (fn [[label hir k] g] (compare-case label hir k g)) cases got))]
  (when-not (every? true? results)
    (js/process.exit 1)))
