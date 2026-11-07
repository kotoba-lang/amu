;; Report which open PRs form a dependent stack and can be combined (JUN-818, measure 3).
;;
;; Default (and `report`): read-only. Lists PR stacks (PR B is stacked on PR A when B's base branch is A's head
;; branch), whether each stack is mechanically combinable (every PR's head contains its base PR's head, so the
;; top PR already carries the whole stack), and which independent PRs touch the same files (pins in particular),
;; so they would conflict in the merge queue.
;;
;; `combine TOP_PR [--push] [--open-pr]` is the only mutating command and runs only when invoked: it creates a
;; local branch `batch/pr-<TOP>` at the top PR's head and, with --push/--open-pr, pushes it and opens ONE new PR
;; against the stack root's base branch. It never closes, retargets, edits or merges any existing PR; the owner
;; of the stack closes the superseded PRs after the combined PR lands.
;; Ported from pr_batch.py (Basilisp). PR records are JSON string-keyed maps, as `gh` prints them.
;; Run: basilisp run scripts/ci/pr_batch.cljc -- [--repo R] report | combine TOP [--push] [--open-pr]
(ns pr-batch
  (:require [basilisp.set :as set]
            [basilisp.string :as str])
  (:import json subprocess sys))

(def fields "number,title,headRefName,baseRefName,headRefOid,files,mergeStateStatus,isDraft,author")
(def pin-prefixes ["bin/" "native-product.json" "seed/bootstrap/" "seed/cdci/" "seed/compiler-core.json"
                   "seed/adoption-" "examples/foundation-starter/"])

(defn sh
  "Run argv (varargs); returns {:returncode :stdout :stderr}. Exits with the stderr unless :check is false
  (pass a trailing map {:check false})."
  [& cmd]
  (let [[cmd opts] (if (map? (last cmd)) [(butlast cmd) (last cmd)] [cmd {}])
        r (subprocess/run (python/list cmd) ** :capture_output true :text true)
        out {:returncode (.-returncode r) :stdout (.-stdout r) :stderr (.-stderr r)}]
    (when (and (get opts :check true) (not= 0 (:returncode out)))
      (sys/exit (str (str/join " " cmd) ": " (str/trim (:stderr out)))))
    out))

(defn load-prs [repo]
  (vec (json/loads (:stdout (sh "gh" "pr" "list" "--repo" repo "--state" "open" "--limit" "200"
                                "--json" fields)))))

(defn stacks
  "Chains bottom to top. A PR whose base branch is another open PR's head is stacked on it.
  Returns a vector of [chain branched]."
  [prs]
  (let [by-head (into {} (map (juxt #(get % "headRefName") identity)) prs)
        child (reduce (fn [m p]
                        (let [parent (get by-head (get p "baseRefName"))]
                          (if (and parent (not= (get parent "number") (get p "number")))
                            (update m (get parent "number") (fnil conj []) p)
                            m)))
                      {} prs)]
    (vec
      (for [p prs
            :when (not (contains? by-head (get p "baseRefName"))) ; not a stack root otherwise
            :let [[chain cur] (loop [chain [p] cur p]
                                (let [kids (get child (get cur "number") [])]
                                  (if (= 1 (count kids))
                                    (recur (conj chain (first kids)) (first kids))
                                    [chain cur])))
                  branched (get child (get cur "number") [])]
            :when (or (> (count chain) 1) (seq branched))]
        [chain branched]))))

(defn pin? [path] (boolean (some #(str/starts-with? path %) pin-prefixes)))

(defn file-set [p] (set (map #(get % "path") (get p "files" []))))

(defn overlaps [prs in-stack]
  (let [free (vec (remove #(contains? in-stack (get % "number")) prs))]
    (vec (for [i (range (count free))
               j (range (inc i) (count free))
               :let [a (nth free i) b (nth free j)
                     common (set/intersection (file-set a) (file-set b))]
               :when (seq common)]
           [(get a "number") (get b "number") (count common) (vec (sort (filter pin? common)))]))))

(defn combinable
  "[ok why]. True when each PR's head contains the previous PR's head (needs the heads fetched)."
  ([chain] (combinable chain sh))
  ([chain git]
   (let [bad (first (for [[lower upper] (map vector chain (rest chain))
                          :let [r (git "git" "merge-base" "--is-ancestor" (get lower "headRefOid") (get upper "headRefOid")
                                       {:check false})]
                          :when (not= 0 (:returncode r))]
                      [lower upper]))]
     (cond
       bad [false (str "#" (get (second bad) "number") " does not contain the head of #" (get (first bad) "number")
                       " (needs a merge or rebase by its owner)")]
       (contains? (set (map #(get % "mergeStateStatus") chain)) "DIRTY")
       [false "a PR in the stack has merge conflicts with its base"]
       :else [true "top PR head already contains every lower PR"]))))

(defn report
  ([prs] (report prs sh))
  ([prs git]
   (let [sts (stacks prs)
         in-stack (set (for [[chain _] sts p chain] (get p "number")))
         stack-lines
         (if (empty? sts)
           ["no stacked PRs"]
           (vec (mapcat
                  (fn [[chain branched]]
                    (let [[ok why] (combinable chain git)
                          nums (str/join " <- " (map #(str "#" (get % "number")) chain))
                          drafts (map #(get % "number") (filter #(get % "isDraft") chain))
                          pins (set (for [p chain f (file-set p) :when (pin? f)] f))]
                      (concat
                        [(str "stack " nums "  (root base: " (get (first chain) "baseRefName") ")")
                         (str "  combinable: " (if ok "yes" "no") ": " why)]
                        (when (seq branched)
                          [(str "  note: top PR has several children: "
                                (str/join ", " (map #(str "#" (get % "number")) branched)))])
                        (when (seq drafts)
                          [(str "  drafts: " (str/join ", " (map #(str "#" %) drafts)))])
                        [(str "  pin files touched: " (count pins))])))
                  sts)))
         rows (overlaps prs in-stack)]
     (str/join "\n"
               (concat stack-lines
                       [""
                        "independent PRs sharing files (queue conflict risk):"]
                       (if (seq rows)
                         (for [[a b n pins] rows]
                           (str "  #" a " x #" b ": " n " common files"
                                (when (seq pins) (str ", " (count pins) " pin files"))))
                         ["  none"]))))))

(defn combine [prs top repo push open-pr]
  (let [by-num (into {} (map (juxt #(get % "number") identity)) prs)
        _ (when-not (contains? by-num top) (sys/exit (str "PR #" top " is not open")))
        chain (last (for [[c _] (stacks prs) :when (= top (get (last c) "number"))] c))
        _ (when-not chain (sys/exit (str "#" top " is not the top of a linear stack; run `report`")))
        _ (apply sh "git" "fetch" "origin" (map #(str "pull/" (get % "number") "/head") chain))
        [ok why] (combinable chain)
        _ (when-not ok (sys/exit (str "not combinable: " why)))
        branch (str "batch/pr-" top)
        oid (get (last chain) "headRefOid")
        covered (str/join ", " (map #(str "#" (get % "number")) chain))]
    (sh "git" "branch" "-f" branch oid)
    (println (str "created local branch " branch " at " (subs oid 0 12) " covering " covered))
    (if-not (or push open-pr)
      (println "not pushed (pass --push --open-pr to publish)")
      (do
        (sh "git" "push" "origin" (str branch ":refs/heads/" branch))
        (when open-pr
          (let [body (str "Combined stack " covered " (head of #" top "). Original PRs are untouched; "
                          "their owners close them after this lands.\n\n"
                          "🤖 Generated with [Claude Code](https://claude.com/claude-code)")]
            (println (str/trim (:stdout (sh "gh" "pr" "create" "--repo" repo "--base" (get (first chain) "baseRefName")
                                            "--head" branch "--title" (str "batch: combine stack ending at #" top)
                                            "--body" body))))))))))

(defn- parse-args [args]
  (loop [m {:repo "kotoba-lang/amu" :cmd nil :push false :open-pr false} [a & more :as xs] (seq args)]
    (cond
      (empty? xs) m
      (= a "--repo") (recur (assoc m :repo (first more)) (rest more))
      (= a "report") (recur (assoc m :cmd :report) more)
      (= a "combine") (recur (assoc m :cmd :combine :top (python/int (first more))) (rest more))
      (= a "--push") (recur (assoc m :push true) more)
      (= a "--open-pr") (recur (assoc m :open-pr true) more)
      :else (throw (ex-info (str "unknown argument " a) {:arg a})))))

(defn -main [& argv]
  (let [{:keys [repo cmd top push open-pr]} (parse-args argv)
        prs (load-prs repo)]
    (if (= cmd :combine)
      (combine prs top repo push open-pr)
      (do (apply sh "git" "fetch" "-q" "origin" (concat (map #(str "pull/" (get % "number") "/head") prs)
                                                        [{:check false}]))
          (println (report prs))))))

(when (some #(or (= % "pr_batch.cljc") (str/ends-with? % "/pr_batch.cljc")) sys/argv)
  (apply -main *command-line-args*))
