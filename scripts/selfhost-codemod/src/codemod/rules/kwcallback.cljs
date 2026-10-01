;; Rule (d): a keyword used as the callback of a higher-order core function.
;;
;;   (map :k xs)              ->  (map (fn [e] (:k e)) xs)           ;; step 1: the callback becomes a lambda
;;   (map :k xs)              ->  (map (fn [e] (fe-get e :k)) xs)    ;; step 2 (opts :lower-accessor): Form accessor
;;   (juxt :a :b)             ->  (fn [e] [(:a e) (:b e)])
;;
;; The keyword's value is looked up by `get` either way, so the host result is unchanged.
(ns codemod.rules.kwcallback
  (:require [clojure.string :as str]
            [codemod.cst :as cst]
            [codemod.edit :as edit]))

;; head -> index (in the argument list) of the callback
(def callback-index
  {"map" 0 "mapv" 0 "filter" 0 "filterv" 0 "remove" 0 "keep" 0 "mapcat" 0 "some" 0 "every?" 0 "not-any?" 0
   "not-every?" 0 "sort-by" 0 "group-by" 0 "take-while" 0 "drop-while" 0 "partition-by" 0 "split-with" 0
   "max-key" 0 "min-key" 0 "run!" 0 "keep-indexed" 0 "update-vals" 1 "update-keys" 1})

(defn- lambda-text [kw-texts accessor?]
  (let [call (fn [k] (if accessor? (str "(fe-get e " k ")") (str "(" k " e)")))]
    (if (= 1 (count kw-texts))
      (str "(fn [e] " (call (first kw-texts)) ")")
      (str "(fn [e] [" (str/join " " (map call kw-texts)) "])"))))

(defn find-all [{:keys [src nodes opts]}]
  (let [out (atom [])
        starts (edit/line-starts src)
        accessor? (:lower-accessor opts)]
    (cst/walk
     (fn [n {:keys [region path]}]
       (when (cst/lst? n)
         (let [h (cst/head-text n)
               as (cst/args n)
               fin (fn [status extra]
                     (swap! out conj (merge {:rule :kwcallback :s (:s n) :e (:e n) :region region :status status
                                             :line (edit/offset->line starts (:s n)) :context h} extra)))]
           (cond
             (and h (contains? callback-index h) (< (callback-index h) (count as)) (cst/kw? (nth as (callback-index h))))
             (let [i (callback-index h) k (nth as i)
                   colls (- (count as) i 1)]
               (if (and (contains? #{"map" "mapv" "mapcat" "keep"} h) (> colls 1))
                 (fin :human {:reason "multi-collection map with a keyword callback ((:k a b) is get-with-default)"})
                 (fin :auto {:edits [(edit/replace-node k (lambda-text [(:text k)] accessor?) :kwcallback)]})))
             (and (= h "juxt") (seq as) (every? cst/kw? as) (cst/lst? (last path))
                  (contains? #{"->" "->>" "some->" "cond->" "as->"} (cst/head-text (last path))))
             (fin :human {:reason "juxt as a threading step: the threaded value is its argument, not a callback"})
             (and (= h "juxt") (seq as) (every? cst/kw? as))
             (fin :auto {:edits [(edit/replace-node n (lambda-text (map :text as) accessor?) :kwcallback)]})
             (and (contains? #{"comp" "partial" "some-fn" "every-pred"} h) (some cst/kw? as))
             (fin :human {:reason (str "keyword inside (" h " ...): a composed callback needs a hand-written lambda")})
             (and (= h "apply") (>= (count as) 2) (contains? #{"max-key" "min-key"} (:text (first as))) (cst/kw? (second as)))
             (let [k (second as)]
               (fin :auto {:edits [(edit/replace-node k (lambda-text [(:text k)] accessor?) :kwcallback)]}))))))
     nodes)
    @out))

(def rule {:id :kwcallback :find find-all})
