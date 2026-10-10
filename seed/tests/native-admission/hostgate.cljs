;; seed/tests/native-admission/hostgate.cljs -- host side of the native-admission differential (BOOTSTRAP-REFERENCE, nbb):
;; per v3 program of the list, the host gate's verdict on every function (alone in the module), on every body sub-form
;; (nbb.cli's probe) and on mutations of each call, written as EDN case files of 400 cases. args: <list> <out-dir>
(ns hostgate (:require [kotoba.sema :as sema] [kotoba.kir :as ir] [kotoba.artifact.core :as artifact]
                       [kotoba.compiler.host-integer :as host-integer]
                       [clojure.string :as str] ["node:fs" :as fs]))
(defn children [form]
  (letfn [(spread [x] (if (vector? x) (mapcat spread x) [x]))]
    (cond (seq? form) (mapcat spread (rest form)) (vector? form) (mapcat spread form) :else [])))
(defn subforms [body] (tree-seq (fn [x] (or (seq? x) (vector? x))) children body))
;; mutations of a call: arity -1/+1, a broken type descriptor or first element in each vector operand, each integer
;; operand at the gate's bounds, each keyword operand an unknown member
(defn mutations [form]
  (when (and (seq? form) (symbol? (first form)))
    (let [v (vec form) n (count v)]
      (concat
       (when (> n 1) [(apply list (pop v))])
       [(apply list (conj v 0))]
       (for [i (range 1 n) :when (vector? (nth v i))]
         (apply list (assoc v i [:record :bad/t [[:a :f32]]])))
       ;; the first element of each non-empty vector operand replaced (a let binder, a match branch's tag)
       (for [i (range 1 n) :when (and (vector? (nth v i)) (seq (nth v i)))]
         (apply list (assoc v i (assoc (nth v i) 0 0))))
       ;; each integer operand (a BigInt on nbb) at the bounds the gate tests (shift 0..63, cap id 0..255, an index)
       (for [i (range 1 n) :when (or (integer? (nth v i)) (host-integer/bigint? (nth v i))) x [-1 0 63 64 255 256]]
         (apply list (assoc v i x)))
       (for [i (range 1 n) :when (keyword? (nth v i))]
         (apply list (assoc v i :no-such-member)))))))
(let [[list-file out] *command-line-args*
      files (remove str/blank? (str/split-lines (str (.readFileSync fs list-file "utf8"))))
      n (atom 0) stats (atom {})]
  (doseq [f files]
    (let [hir (try (sema/analyze (str (.readFileSync fs f "utf8"))) (catch :default _ nil))]
      (when (= :kotoba.hir/v3 (:format hir))
        (let [ctx {:schemas (:schemas hir) :exports (:exports hir) :entry (:entry hir)}
              fcases (for [fun (:functions hir)]
                       [(if (ir/only-native-word-typed-features? (assoc hir :functions [fun])) 1 0) :fn fun])
              bodies (vals (into (sorted-map) (map (fn [b] [(pr-str (artifact/edn-safe b)) b])) (mapcat (comp subforms :body) (:functions hir))))
              bcases (for [b bodies]
                       [(if (ir/only-native-word-typed-features?
                             (assoc hir :functions [{:name '__amu_native_probe :params [] :param-types []
                                                     :result :i64 :body b}])) 1 0) :body b])
              ;; a mutation the host gate itself throws on is not a frontend HIR: left out
              mcases (keep (fn [m]
                             (try [(if (ir/only-native-word-typed-features?
                                        (assoc hir :functions [{:name '__amu_native_probe :params [] :param-types []
                                                                :result :i64 :body m}])) 1 0) :body m]
                                  (catch :default _ (swap! stats update :host-throws (fnil inc 0)) nil)))
                           (mapcat mutations bodies))
              cases (vec (concat fcases bcases mcases))]
          (doseq [chunk (partition-all 400 cases)]
            (let [text (binding [*print-namespace-maps* false] (pr-str (artifact/edn-safe (assoc ctx :source f :cases (vec chunk)))))]
              (swap! n inc)
              (.writeFileSync fs (str out "/case-" (.padStart (str @n) 5 "0") ".edn") text)))
          (swap! stats update :programs (fnil inc 0))
          (swap! stats update :cases (fnil + 0) (count cases))
          (swap! stats update :refused (fnil + 0) (count (filter #(zero? (first %)) cases)))))))
  (prn @stats))
