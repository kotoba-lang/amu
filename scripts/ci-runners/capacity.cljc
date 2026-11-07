;; Runner capacity monitor and hosted fail-over for ADR 0407. Read-only unless --apply.
;;
;; Needs a repository-scoped GH_TOKEN with Administration (read; self-hosted runners), Actions read and
;; Variables read/write (--apply) in the environment.
;; Decision rule (pure function `decide`, unit-tested): fall back to hosted when a needed label has no online
;; runner, or when a queued self-hosted job has waited longer than --max-wait seconds.
;; Ported from capacity.py (Basilisp). Run: basilisp run scripts/ci-runners/capacity.cljc -- [--apply] [--max-wait N]
(ns capacity
  (:require [basilisp.string :as str])
  (:import datetime json subprocess sys))

(def repo "kotoba-lang/amu")
(def needed {"selfhosted-arm" ["amu-linux-arm64" "amu-macos-arm64"]
             "selfhosted"     ["amu-linux-arm64" "amu-macos-arm64" "amu-linux-x86_64"]})

(defn decide
  "Return [new-profile reason]. Never promotes back to self-hosted."
  ([profile online-labels queued-waits] (decide profile online-labels queued-waits 120))
  ([profile online-labels queued-waits max-wait]
   (if-not (contains? needed profile)
     [profile "not self-hosted"]
     (let [missing (remove #(contains? online-labels %) (get needed profile))
           slow    (filter #(> % max-wait) queued-waits)]
       (cond
         (seq missing) ["hosted" (str "no online runner for " (str/join ", " missing))]
         (seq slow)    ["hosted" (str (count slow) " self-hosted job(s) queued > " max-wait
                                      "s (max " (python/format (apply max slow) ".0f") "s)")]
         :else         [profile "ok"])))))

(defn gh [& args]
  (json/loads (subprocess/check_output (python/list (cons "gh" args)))))

(defn- parse-args [args]
  (loop [m {:apply false :max-wait 120} [k v & more :as xs] (seq args)]
    (cond
      (empty? xs) m
      (= k "--apply")    (recur (assoc m :apply true) (rest xs))
      (= k "--max-wait") (recur (assoc m :max-wait (python/int v)) more)
      :else (throw (ex-info (str "unknown argument " k) {:arg k})))))

(defn run [{:keys [max-wait] do-apply :apply}]
  (let [rows   (get (gh "api" (str "repos/" repo "/actions/runners?per_page=100")) "runners")
        online (set (for [r rows :when (= "online" (get r "status")) l (get r "labels")] (get l "name")))
        r      (subprocess/run ["gh" "variable" "get" "AMU_RUNNER_PROFILE" "-R" repo]
                               ** :capture_output true :text true)
        _      (when (and (not= 0 (.-returncode r))
                          (not (str/includes? (.-stderr r) "Not Found"))
                          (not (str/includes? (.-stderr r) "HTTP 404")))
                 (sys/exit (str "cannot read AMU_RUNNER_PROFILE (token needs Variables read): "
                                (str/trim (.-stderr r)))))
        var    (str/trim (.-stdout r))
        now    (.now datetime/datetime (.-utc datetime/timezone))
        ;; Jobs of an in_progress run can still be queued, so look at both run states.
        runs   (for [st ["queued" "in_progress"]
                     run (get (gh "api" (str "repos/" repo "/actions/runs?status=" st "&per_page=50"))
                              "workflow_runs")]
                 run)
        waits  (vec (for [run runs
                          j (get (gh "api" (str "repos/" repo "/actions/runs/" (get run "id") "/jobs?per_page=100"))
                                 "jobs")
                          :when (and (= "queued" (get j "status"))
                                     (some #(str/starts-with? % "amu-") (get j "labels")))]
                      (.total_seconds (- now (.fromisoformat datetime/datetime
                                                             (str/replace (get j "created_at") "Z" "+00:00"))))))
        [new why] (decide var online waits max-wait)]
    (println (str "profile=" (if (seq var) var "(unset)") " online=" (vec (sort online))
                  " queued_self_hosted=" (count waits) " -> " new ": " why))
    (cond
      (and (not= new var) do-apply)
      (do (subprocess/check_call ["gh" "variable" "set" "AMU_RUNNER_PROFILE" "--body" new "-R" repo])
          (println "variable set; re-run stuck jobs with: gh run rerun <id> --failed"))
      (not= new var) (println "dry-run: pass --apply to set the variable"))))

(when (some #(or (= % "capacity.cljc") (str/ends-with? % "/capacity.cljc")) sys/argv)
  (run (parse-args *command-line-args*)))
