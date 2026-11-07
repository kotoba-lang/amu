;; Evaluate every rendered `runs-on` expression for event/profile scenarios.
;;
;; Negative controls: a fork pull request never gets a self-hosted label, under any
;; profile; an unset or 'hosted' profile never does either (behaviour unchanged).
;; A tiny evaluator for the GitHub expression subset the template uses keeps the
;; test on the real workflow text.
;; Ported from test_runs_on.py. Run from the repo root:
;;   PYTHONPATH=scripts/ci-runners basilisp test --rootdir scripts/ci-runners scripts/ci-runners/test_runs_on.cljc
(ns test-runs-on
  (:require [basilisp.test :refer [deftest is]]
            [basilisp.string :as str]
            [runs-on :as ro])
  (:import json re))

(def tok-re (re/compile "\\s*(&&|\\|\\||==|!=|\\(|\\)|,|'[^']*'|[A-Za-z_][\\w.]*)"))

(defn tokenize [expr]
  (let [end (count (.rstrip expr))]
    (loop [pos 0 toks []]
      (if (< pos end)
        (let [m (.match tok-re expr pos)]
          (assert m (str "cannot tokenize " (subs expr pos (min (count expr) (+ pos 30)))))
          (recur (.end m) (conj toks (.group m 1))))
        toks))))

(defn evaluate [expr ctx]
  (let [toks (tokenize expr)
        it (atom 0)
        peek (fn [] (get toks @it))
        take (fn [] (let [t (get toks @it)] (swap! it inc) t))
        truthy (fn [v] (not (or (nil? v) (= v "") (false? v))))
        orx (atom nil)
        prim (fn []
               (let [t (take)]
                 (cond
                   (= t "(") (let [v (@orx)] (assert (= (take) ")")) v)
                   (str/starts-with? t "'") (subs t 1 (dec (count t)))
                   (contains? #{"contains" "fromJSON"} t)
                   (do (assert (= (take) "("))
                       (let [args (atom [(@orx)])]
                         (while (= (peek) ",") (take) (swap! args conj (@orx)))
                         (assert (= (take) ")"))
                         (if (= t "fromJSON")
                           (vec (json/loads (first @args)))
                           (boolean (some #{(second @args)} (first @args))))))
                   :else (get ctx t ""))))
        eqx (fn []
              (loop [v (prim)]
                (if (contains? #{"==" "!="} (peek))
                  (let [op (take) w (prim)]
                    (recur (if (= op "==") (= v w) (not= v w))))
                  v)))
        andx (fn []
               (loop [v (eqx)]
                 (if (= (peek) "&&")
                   (do (take) (let [w (eqx)] (recur (if (truthy v) w v))))
                   v)))]
    (reset! orx (fn []
                  (loop [v (andx)]
                    (if (= (peek) "||")
                      (do (take) (let [w (andx)] (recur (if (truthy v) v w))))
                      v))))
    (let [v (@orx)]
      (assert (nil? (peek)))
      v)))

(def repo "kotoba-lang/amu")
(def events
  {"push" {"github.event_name" "push"}
   "merge_group" {"github.event_name" "merge_group"}
   "pr-same" {"github.event_name" "pull_request" "github.event.pull_request.head.repo.full_name" repo}
   "pr-fork" {"github.event_name" "pull_request" "github.event.pull_request.head.repo.full_name" "evil/amu"}
   "pr-fork-name-prefix" {"github.event_name" "pull_request" "github.event.pull_request.head.repo.full_name" (str repo "-x")}})

(defn covered-lines []
  (vec (for [p (sort-by #(.-name %) (python/list (.glob ro/workflows "*.yml")))
             line (.split (.read-text p) "\n")
             :let [m (.match ro/line-re line)]
             :when (and m (.group m 4))]
         [(.-name p) (.group m 2) (.group m 4)])))

(deftest evaluator-negative-control
  ;; the evaluator itself must distinguish branches, otherwise the matrix below is vacuous
  (is (= "a" (evaluate "x == 'p' && 'a' || 'b'" {"x" "p"})))
  (is (= "b" (evaluate "x == 'p' && 'a' || 'b'" {"x" "q"})))
  (is (= true (evaluate "contains(fromJSON('[\"s\",\"t\"]'), v)" {"v" "t"})))
  (is (= false (evaluate "contains(fromJSON('[\"s\",\"t\"]'), v)" {"v" "u"}))))

(deftest every-rendered-runs-on-line
  (let [covered (covered-lines)
        fails (atom [])]
    (is (>= (count covered) 30) (count covered))
    (doseq [[f value tag] covered
            [ev ectx] events
            prof ["" "hosted" "selfhosted-arm" "selfhosted"]
            matrix (if (= tag "${{ matrix.runner }}") ["ubuntu-24.04-arm" "ubuntu-24.04"] [tag])]
      (let [ctx (assoc ectx "github.repository" repo "vars.AMU_RUNNER_PROFILE" prof "matrix.runner" matrix)
            got (evaluate (subs (str/trim value) 3 (- (count (str/trim value)) 2)) ctx)
            arm? (= matrix "ubuntu-24.04-arm")
            selfhost-ok (contains? #{"push" "merge_group" "pr-same"} ev)
            want (cond
                   (and selfhost-ok (contains? #{"selfhosted" "selfhosted-arm"} prof) (or arm? (= matrix "macos-15")))
                   (if (= matrix "macos-15") "amu-macos-arm64" "amu-linux-arm64")
                   (and selfhost-ok (= prof "selfhosted") (= matrix "ubuntu-24.04")) "amu-linux-x86_64"
                   :else matrix)]
        (when (not= got want)
          (swap! fails conj (str "FAIL " f " " tag " ev=" ev " profile=" (pr-str prof) ": got " (pr-str got) " want " (pr-str want))))
        (when (or (str/starts-with? ev "pr-fork") (contains? #{"" "hosted"} prof))
          (is (= got matrix) (str f " " ev " " prof)))))
    (is (empty? @fails) (str/join "\n" @fails))))
