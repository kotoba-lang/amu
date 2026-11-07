;; Report how much of the ADR 0410 denominator has native evidence (JUN-890).
;;
;; This is a report, not a gate. Basilisp reads receipts that native gates wrote and
;; adds up shares. It does not run the compiler, and it does not replace the native
;; controller's verdict. A digest here shows that a stored receipt is unchanged
;; since collection. It does not authenticate the receipt.
;;
;;   collect  copy the receipts the table names from two successful CI runs
;;   report   compute the numbers for a snapshot on a given day
;;   verify   recompute a snapshot on its own day and compare with its report.json
;;
;; A cell without evidence counts as 0. An ISA split nobody has measured gives the
;; OS credit in the lower bound only when every listed target passes.
;; Ported from scoreboard.py (Basilisp). JSON is read into Clojure data (string keys).
;; Run from the repo root: basilisp run scripts/coverage/scoreboard.cljc -- verify
(ns scoreboard
  (:require [basilisp.string :as str])
  (:import datetime hashlib json os pathlib shutil subprocess sys tempfile))

(def root (.resolve (pathlib/Path (or (.get os/environ "AMU_ROOT") "."))))
(def coverage (.joinpath root "docs/qualification/target-coverage"))
(def repo "kotoba-lang/amu")
(def workflows {"selfhost" "selfhost-native" "mac" "mac-selfhost-aiueos"})
(def artifacts {"x86_64-native-receipt" "selfhost"
                "bootstrap-arm64" "selfhost"
                "mac-aiueos-user-root" "mac"})
(def levels ["L1" "L2" "L3"])

(defn refuse [message] (throw (ex-info message {:refused true})))
(defn refused? [e] (boolean (:refused (ex-data e))))

(defn from-py [x]
  (cond
    (instance? python/dict x) (into {} (map (fn [[k v]] [k (from-py v)])) (.items x))
    (instance? python/list x) (mapv from-py x)
    :else x))

(defn to-py [x]
  (cond
    (map? x) (python/dict (python/list (for [[k v] x] (python/tuple [k (to-py v)]))))
    (or (vector? x) (sequential? x) (set? x)) (python/list (map to-py x))
    :else x))

(defn read-json [path] (from-py (json/loads (.read_text path))))
(defn dump [value] (str (json/dumps (to-py value) ** :indent 2 :sort_keys true) "\n"))

(defn digest [path] (.hexdigest (hashlib/sha256 (.read_bytes path))))

(defn table-paths [table]
  (vec (sort (set (for [t (vals (get table "targets")) c (vals (get t "cells")) r (get c "receipts" [])]
                    (get r "path"))))))

(defn check-table [table]
  (when (not= "amu.target-coverage-table.v1" (get table "schema")) (refuse "unknown table schema"))
  (let [slices (get-in table ["denominator" "slices"])
        listed (vec (for [s (vals slices) t (get s "targets")] t))]
    (when (> (reduce + (map #(get % "shareBasisPoints") (vals slices))) 10000)
      (refuse "denominator is over 100%"))
    (when (not= (count listed) (count (set listed))) (refuse "a target is listed in two slices"))
    (doseq [name (concat listed (get table "developmentHosts"))]
      (when-not (contains? (get table "targets") name) (refuse (str "target has no row: " name))))
    (doseq [[name target] (get table "targets")]
      (when (not= (set (keys (get target "cells"))) (set levels))
        (refuse (str name " must have exactly " (python/repr (python/tuple levels))))))
    (doseq [[name part] slices
            :let [split (get part "isaSplitBasisPoints")]]
      (when (and (some? split)
                 (or (not= (set (keys split)) (set (get part "targets")))
                     (not= 10000 (reduce + (vals split)))))
        (refuse (str name ": a measured split must cover its targets and total 100%"))))))

(defn receipt-problems
  "[problems body]."
  [snapshot provenance spec host]
  (let [path (get spec "path")
        file (.joinpath (.joinpath snapshot "receipts") path)]
    (cond
      (not (contains? (get provenance "receipts") path)) [[(str path ": not in provenance")] nil]
      (not (.is_file file)) [[(str path ": missing")] nil]
      (not= (digest file) (get-in provenance ["receipts" path])) [[(str path ": digest differs from provenance")] nil]
      :else
      (let [body (try (read-json file) (catch python/ValueError _ ::not-json))]
        (if (= body ::not-json)
          [[(str path ": not JSON")] nil]
          (let [seen (get body "host")
                gens (get body "generations" [])
                problems
                (cond-> []
                  (and (contains? spec "status") (not= (get body "status") (get spec "status")))
                  (conj (str path ": status " (python/repr (get body "status"))))
                  true
                  (into (for [[key want] (get spec "fields" {})
                              :when (or (not (contains? body key)) (not= (get body key) want))]
                          (str path ": " key " is " (python/repr (get body key)) ", wants " (python/repr want))))
                  (true? (get body "emulation"))
                  (conj (str path ": ran under emulation"))
                  (and (get spec "identicalGenerations")
                       (or (< (count gens) 2) (not= 1 (count (set (map #(get % "sha256") gens))))))
                  (conj (str path ": generations are not identical"))
                  (and (some? seen) (not= (vec (take (count host) seen)) host))
                  (conj (str path ": ran on " (python/repr (python/list seen)) ", wants " (python/repr (python/list host)))))]
            [problems body]))))))

(defn evaluate-cell [snapshot provenance cell host caveat-fields stale]
  (cond
    (contains? cell "prohibited") {"state" "prohibited" "reason" (get cell "prohibited")}
    (not (contains? cell "receipts")) {"state" "missing" "reason" (get cell "missing")}
    :else
    (let [rs (for [spec (get cell "receipts")]
               (let [[found body] (receipt-problems snapshot provenance spec host)]
                 {:found found :body body
                  :caveats (when body
                             (for [k caveat-fields :when (false? (get body k))]
                               (str (get spec "path") ": " k " is false")))}))
          problems (vec (mapcat :found rs))
          caveats (vec (mapcat :caveats rs))
          host-seen (boolean (some #(and (:body %) (contains? (:body %) "host")) rs))
          problems (cond-> problems
                     (and (empty? problems) (not host-seen)) (conj (str "no receipt records the host " (python/repr (python/list host))))
                     stale (conj stale))]
      (if (seq problems)
        {"state" "fail" "problems" problems}
        (cond-> {"state" "pass" "receipts" (mapv #(get % "path") (get cell "receipts"))}
          (seq caveats) (assoc "caveats" (vec (sort (set caveats)))))))))

(defn report [table snapshot as-of]
  (check-table table)
  (let [provenance (read-json (.joinpath snapshot "provenance.json"))
        runs (get provenance "runs")
        heads (set (map #(get % "headSha") (vals runs)))
        _ (when (not= 1 (count heads)) (refuse (str "runs have different heads: " (python/repr (python/list (sort heads))))))
        _ (when (some #(not= "success" (get % "conclusion")) (vals runs)) (refuse "a run did not succeed"))
        _ (when (not= (set (keys runs)) (set (keys workflows))) (refuse "a snapshot needs the selfhost and the mac run"))
        oldest (first (sort (map #(subs (get % "createdAt") 0 10) (vals runs))))
        age (.-days (- (.fromisoformat datetime/date as-of) (.fromisoformat datetime/date oldest)))
        stale (when (> age (get table "maxEvidenceAgeDays")) (str "evidence is " age " days old"))
        targets (into {} (for [[name target] (get table "targets")]
                           [name (into {} (for [level levels]
                                            [level (evaluate-cell snapshot provenance (get-in target ["cells" level])
                                                                  (get target "host") (get table "caveatFields") stale)]))]))
        level (get table "coverageLevel")
        slice-rows (for [[name part] (get-in table ["denominator" "slices"])]
                     (let [share (get part "shareBasisPoints")
                           passing (vec (filter #(= "pass" (get-in targets [% level "state"])) (get part "targets")))
                           split (get part "isaSplitBasisPoints")
                           [low high] (if (nil? split)
                                        [(if (= (count passing) (count (get part "targets"))) share 0)
                                         (if (seq passing) share 0)]
                                        (let [v (quot (* share (reduce + (map #(get split %) passing))) 10000)] [v v]))]
                       [name low high {"shareBasisPoints" share "isaSplitMeasured" (some? split) "passing" passing
                                       "lowerBasisPoints" low "upperBasisPoints" high}]))
        lower (reduce + (map second slice-rows))
        upper (reduce + (map #(nth % 2) slice-rows))
        denominator (reduce + (map #(get % "shareBasisPoints") (vals (get-in table ["denominator" "slices"]))))]
    {"schema" "amu.target-coverage-report.v1"
     "gateVerdict" false
     "asOf" as-of
     "head" (first heads)
     "denominator" (into {} (for [k ["source" "period" "retrieved"]] [k (get-in table ["denominator" k])]))
     "denominatorBasisPoints" denominator
     "thresholdBasisPoints" (get table "thresholdBasisPoints")
     "coverageLevel" level
     "lowerBasisPoints" lower
     "upperBasisPoints" upper
     "meetsThreshold" (>= lower (get table "thresholdBasisPoints"))
     "slices" (into {} (for [[name _ _ m] slice-rows] [name m]))
     "developmentHostsAtL3" (into {} (for [t (get table "developmentHosts")]
                                       [t (every? #(= "pass" (get-in targets [t % "state"])) levels)]))
     "targets" targets}))

(defn gh-json [& args]
  (from-py (json/loads (.-stdout (subprocess/run (python/list (cons "gh" args)) ** :check true :capture_output true :text true)))))

(defn collect [table runs out]
  (when (.exists out) (refuse (str out " already exists")))
  (let [views (into {} (for [[role run] runs]
                         (let [view (gh-json "run" "view" (str run) "--repo" repo "--json"
                                             "headSha,conclusion,workflowName,event,createdAt")]
                           (when (or (not= (get view "workflowName") (get workflows role)) (not= (get view "conclusion") "success"))
                             (refuse (str "run " run " is " (get view "workflowName") ": " (get view "conclusion"))))
                           [role (assoc view "id" run)])))
        _ (when (not= 1 (count (set (map #(get % "headSha") (vals views))))) (refuse "runs have different heads"))
        paths (table-paths table)]
    (with-open [temp (tempfile/TemporaryDirectory)]
      (let [artifact-info
            (into {} (for [[artifact role] artifacts]
                       (let [run (get runs role)
                             listed (get (gh-json "api" (str "repos/" repo "/actions/runs/" run "/artifacts") "--paginate") "artifacts")
                             match (filterv #(and (= (get % "name") artifact) (not (get % "expired"))) listed)]
                         (when (not= 1 (count match)) (refuse (str artifact ": " (count match) " live artifacts in run " run)))
                         (subprocess/run ["gh" "run" "download" (str run) "--repo" repo "-n" artifact
                                          "-D" (str (pathlib/Path temp artifact))] ** :check true)
                         [artifact {"run" run "id" (get (first match) "id") "digest" (get (first match) "digest")}])))
            receipts (into {} (for [path paths]
                                (let [target (.joinpath (.joinpath out "receipts") path)]
                                  (.mkdir (.-parent target) ** :parents true :exist_ok true)
                                  (shutil/copyfile (pathlib/Path temp path) target)
                                  [path (digest target)])))
            provenance {"schema" "amu.target-coverage-provenance.v1" "repository" repo
                        "runs" views "artifacts" artifact-info "receipts" receipts}]
        (.write_text (.joinpath out "provenance.json") (dump provenance))
        provenance))))

(defn percent [bp] (str (quot bp 100) "." (python/format (mod bp 100) "02d") "%"))

(defn table-order
  "Key order of table.json's slices and targets (Clojure maps are unordered, Python dicts keep file order)."
  []
  (let [raw (json/loads (.read_text (.joinpath coverage "table.json")))]
    {:slices (vec (get (get raw "denominator") "slices"))
     :targets (vec (get raw "targets"))}))

(defn show
  "Prints the report. `table` supplies the host order."
  [table result]
  (println (str (get result "coverageLevel") " coverage on " (get result "asOf") ", head " (subs (get result "head") 0 9) ": "
                (percent (get result "lowerBasisPoints")) " lower, " (percent (get result "upperBasisPoints")) " upper, "
                "of " (percent (get result "denominatorBasisPoints")) " listed; threshold " (percent (get result "thresholdBasisPoints"))))
  (doseq [name (:slices (table-order)) :let [part (get-in result ["slices" name])]]
    (println (str "  " (python/format name "8") " " (python/format (percent (get part "shareBasisPoints")) ">7")
                  "  lower " (python/format (percent (get part "lowerBasisPoints")) ">6")
                  "  upper " (python/format (percent (get part "upperBasisPoints")) ">6")
                  "  passing " (if (seq (get part "passing")) (python/repr (python/list (get part "passing"))) "-"))))
  (doseq [name (:targets (table-order)) :let [cells (get-in result ["targets" name])]]
    (println (str "  " (python/format name "16") " "
                  (str/join " " (for [level levels] (str level "=" (get-in cells [level "state"])))))))
  (println (str "  development hosts at L3: "
                (let [hs (for [t (get table "developmentHosts") :when (get-in result ["developmentHostsAtL3" t])] t)] (if (seq hs) (str/join ", " hs) "-")))))

(defn- opt [args k] (second (drop-while #(not= % k) args)))
(defn- today [] (.isoformat (.date (.now datetime/datetime (.-utc datetime/timezone)))))

(defn -main [& args]
  (let [table (read-json (.joinpath coverage "table.json"))
        cmd (first args)]
    (try
      (case cmd
        "collect"
        (let [date (opt args "--date")
              out (.joinpath (.joinpath coverage "snapshots") date)]
          (check-table table)
          (collect table {"selfhost" (python/int (opt args "--selfhost-run")) "mac" (python/int (opt args "--mac-run"))} out)
          (let [result (report table out (str (subs date 0 4) "-" (subs date 4 6) "-" (subs date 6)))]
            (.write_text (.joinpath out "report.json") (dump result))
            (show table result))
          0)
        "report"
        (let [result (report table (pathlib/Path (opt args "--snapshot")) (or (opt args "--as-of") (today)))]
          (when-let [o (opt args "--output")] (.write_text (pathlib/Path o) (dump result)))
          (show table result)
          0)
        "verify"
        (let [snapshots (vec (sort-by #(.-name %) (python/list (.iterdir (.joinpath coverage "snapshots")))))]
          (when (empty? snapshots) (refuse "no snapshot"))
          (doseq [snapshot snapshots]
            (let [stored (read-json (.joinpath snapshot "report.json"))]
              (when (not= (report table snapshot (get stored "asOf")) stored)
                (refuse (str (.-name snapshot) ": report.json differs from a recomputation")))
              (println (str (.-name snapshot) ": report.json matches, lower " (percent (get stored "lowerBasisPoints"))))))
          0)
        (do (.write sys/stderr "usage: scoreboard.cljc collect|report|verify ...\n") 2))
      (catch basilisp.lang.exception/ExceptionInfo e
        (if (refused? e)
          (do (.write sys/stderr (str "refused: " (ex-message e) "\n")) 1)
          (throw e))))))

(when (some #(or (= % "scoreboard.cljc") (str/ends-with? % "/scoreboard.cljc")) sys/argv)
  (sys/exit (apply -main *command-line-args*)))
