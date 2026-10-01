;; Rule (e) (extension of (a)): destructuring in `let` binding vectors, flattened in place.
;;
;;   (let [[a b] (f x) m 1] ...)   ->   (let [dd__N_1 (f x) a (fe-nth dd__N_1 0) b (fe-nth dd__N_1 1) m 1] ...)
;;
;; Same expansion as Clojure's own `let` destructuring (nth with nil not-found, get, nthnext), so the host result is the
;; same.  The body is untouched.  `loop` / `doseq` / `for` / `when-let` / `if-let` are not rewritten: their binding forms
;; carry a test or a recur target, which is a restructuring and not a flattening.
(ns codemod.rules.letdestructure
  (:require [clojure.string :as str]
            [codemod.cst :as cst]
            [codemod.edit :as edit]
            [codemod.rules.destructure :as d]))

(defn find-all [{:keys [src nodes]}]
  (let [out (atom []) starts (edit/line-starts src)]
    (cst/walk
     (fn [n {:keys [region]}]
       (when (and (cst/lst? n) (= "let" (cst/head-text n)) (cst/vec? (second (:kids n))))
         (let [bv (second (:kids n)) pairs (partition 2 (:kids bv))]
           (when (some (fn [[p _]] (d/pat? p)) pairs)
             (let [counter (atom 0)
                   gen (fn [] (str "dd__" (:s n) "_" (swap! counter inc)))
                   res (for [[p v] pairs :when (d/pat? p)]
                         (let [vt (cst/text src v)
                               plain? (re-matches #"[^\s()\[\]{}]+" vt)
                               g (if plain? vt (gen))
                               r (d/expand src p g gen false)]
                           (if (:human r) r
                               {:p p :v v :binds (into (if plain? [] [[g vt]]) (:binds r))})))
                   line (edit/offset->line starts (:s n))]
               (if-let [h (some :human res)]
                 (swap! out conj {:rule :let :s (:s n) :e (:e n) :region region :status :human :reason h :line line})
                 (swap! out conj
                        {:rule :let :s (:s n) :e (:e n) :region region :status :auto :line line :kind "let"
                         :edits (vec (for [{:keys [p v binds]} res
                                           :let [col (- (:s p) (nth starts (dec (edit/offset->line starts (:s p)))))
                                                 flat (map (fn [[nm e]] (str nm " " e)) binds)
                                                 one (str/join " " flat)
                                                 txt (if (< (+ col (count one)) 100) one
                                                         (str/join (str "\n" (apply str (repeat col " "))) flat))]]
                                       (edit/replace-node {:s (:s p) :e (:e v)} txt :let)))}))))))
       nil)
     nodes)
    @out))

(def rule {:id :let :find find-all})
