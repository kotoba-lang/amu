;; Controls for pr_batch.cljc: stack detection and the refusal to combine a non-contained stack.
;; Ported from test_pr_batch.py.
(ns test-pr-batch
  (:require [basilisp.test :refer [deftest is]]
            [basilisp.string :as str]
            [pr-batch :as b]))

(defn pr
  [n head base & {:keys [files state draft] :or {files [] state "CLEAN" draft false}}]
  {"number" n "title" "t" "headRefName" head "baseRefName" base
   "headRefOid" (python/format n "040d")
   "files" (mapv (fn [f] {"path" f}) files) "mergeStateStatus" state "isDraft" draft "author" {}})

(defn git-ok [& _] {:returncode 0 :stdout "" :stderr ""})
(defn git-no [& _] {:returncode 1 :stdout "" :stderr ""})

(def prs [(pr 1 "a" "main") (pr 2 "b" "a") (pr 3 "c" "b")
          (pr 4 "x" "main" :files ["native-product.json"])
          (pr 5 "y" "main" :files ["native-product.json" "z"])])

(deftest stack-detected
  (is (= [[1 2 3]] (mapv (fn [[c _]] (mapv #(get % "number") c)) (b/stacks prs)))))

(deftest combinable-when-contained
  (is (first (b/combinable (subvec prs 0 3) git-ok))))

(deftest not-combinable-when-not-contained
  (let [[ok why] (b/combinable (subvec prs 0 3) git-no)]
    (is (not ok))
    (is (str/includes? why "#2"))))

(deftest dirty-blocks
  (is (not (first (b/combinable [(pr 1 "a" "main") (pr 2 "b" "a" :state "DIRTY")] git-ok)))))

(deftest overlap-reports-pins-and-skips-stack
  (is (= [[4 5 1 ["native-product.json"]]] (b/overlaps prs #{1 2 3}))))

(deftest report-text
  (let [txt (b/report prs git-ok)]
    (is (str/includes? txt "#1 <- #2 <- #3"))
    (is (str/includes? txt "#4 x #5"))))

(deftest report-negative-controls
  (is (str/includes? (b/report prs git-no) "combinable: no"))
  (is (str/includes? (b/report [(pr 1 "a" "main")] git-ok) "no stacked PRs"))
  (is (str/includes? (b/report [(pr 1 "a" "main") (pr 2 "b" "a" :draft true)] git-ok) "drafts: #2")))
