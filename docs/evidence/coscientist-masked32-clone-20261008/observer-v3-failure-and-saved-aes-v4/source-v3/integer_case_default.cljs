(ns integer-case-default
 (:require [kotoba.compiler.refactor.cst :as cst]
           [kotoba.compiler.refactor.edit :as edit]))
;; Malformed native case has no host equivalence claim. This reusable diagnostic
;; authoring rule reports :human and requires explicit authoring authorization.
(defn find-all [{:keys [src nodes opts]}]
 (let [out (atom [])]
  (cst/walk
   (fn [n {:keys [path]}]
    (when (= "case" (cst/head-text n))
     (let [as (cst/args n) sel (first as) clauses (vec (rest as))
           owner (last (filter #(contains? #{"defn" "defn-"} (cst/head-text %)) path))
           params (first (filter cst/vec? (:kids owner)))
           ps (:kids params)
           typed? (some (fn [[a b]] (and (= (:text a) (:text sel)) (= (:text b) ":i64"))) (partition 2 ps))
           pairs (partition 2 (drop-last 2 clauses))]
      (when (and (>= (count clauses) 4) (even? (count clauses))
                 (= ":else" (:text (nth clauses (- (count clauses) 2))))
                 typed? (= :sym (:type sel))
                 (every? #(= :num (:type (first %))) pairs)
                 (= (count pairs) (count (set (map #(:text (first %)) pairs)))))
       (swap! out conj {:status :human :reason "NATIVE_INTEGER_CASE_DEFAULT_AUTHORING"
          :owner (:text (second (:kids owner)))
          :edits [(edit/replace-node (nth clauses (- (count clauses) 2)) "" :integer-case-default)]}))))) nodes)
  @out))
(def rule {:id :integer-case-default :find find-all})
