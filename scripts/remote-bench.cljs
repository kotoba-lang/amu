#!/usr/bin/env nbb
;; scripts/remote-bench.cljs — run an amu benchmark on a quiet fleet node.
;;
;; The co-scientist loop's judge (`perfgate.core/qualify`) needs a host-qualified
;; run. Before this script the loop had no way to reach one: the bots run on the
;; operator workstation, and `scripts/quiet-host.cljs`'s header records what that
;; cost -- 10+ consecutive ticks refused while eight idle 10-core nodes sat
;; unused.
;;
;; This ships the working tree's HEAD commit to a chosen node, runs one
;; benchmark there, and copies the JSON back. It does not decide WHICH
;; hypothesis to measure; that stays with the loop.
;;
;;   nbb scripts/remote-bench.cljs --bench runtime --fixture kernel
;;   nbb scripts/remote-bench.cljs --bench compile --host judah
;;   nbb scripts/remote-bench.cljs --bench multidomain --out /tmp/r.json
;;
;; --bench:
;;   runtime      scripts/runtime-comparison.mjs        generated-program runtime
;;   compile      scripts/performance-baseline.mjs      cold/loaded COMPILE time
;;   launcher     scripts/launcher-comparison.mjs       nbb front vs node front
;;   multidomain  scripts/runtime-multidomain-suite.mjs the six-domain claim path
;;
;; exit 0 = a report was produced;  1 = the benchmark ran and failed;
;; exit 2 = could not get to a host or could not stage (refused to answer).

(require '[clojure.string :as str])
(def cp (js/require "node:child_process"))
(def fs (js/require "node:fs"))

(defn argv [] (js->clj (.-argv js/process)))
(defn arg [flag fallback]
  (let [v (argv) i (.lastIndexOf (to-array v) flag)]
    (if (neg? i) fallback (nth v (inc i) fallback))))

(defn sh [cmd & [{:keys [timeout] :or {timeout 900000}}]]
  (try {:exit 0 :out (str (.execSync cp cmd #js {:encoding "utf8" :timeout timeout
                                                 :maxBuffer 64000000
                                                 :stdio #js ["pipe" "pipe" "pipe"]}))}
       (catch :default e
         {:exit (or (.-status e) 1)
          :out (str (or (.-stdout e) "") (or (.-stderr e) ""))})))

(defn die! [code msg] (binding [*print-fn* *print-err-fn*] (println msg)) (.exit js/process code))

(def benches
  {"runtime"     {:script "scripts/runtime-comparison.mjs"      :out-flag "--output"}
   "compile"     {:script "scripts/performance-baseline.mjs"    :out-flag "--output"}
   "launcher"    {:script "scripts/launcher-comparison.mjs"     :out-flag "--output"}
   "multidomain" {:script "scripts/runtime-multidomain-suite.mjs" :out-flag "--output"}})

(let [bench-name (arg "--bench" "runtime")
      spec (get benches bench-name)
      _ (when-not spec
          (die! 2 (str "unknown --bench " bench-name
                       "; expected one of " (str/join ", " (sort (keys benches))))))
      ;; Extra args after `--` go verbatim to the benchmark.
      passthru (let [v (argv) i (.indexOf (to-array v) "--")]
                 (if (neg? i) [] (vec (drop (inc i) v))))
      host (or (arg "--host" nil)
               (let [{:keys [exit out]} (sh "nbb scripts/quiet-host.cljs" {:timeout 240000})]
                 (case exit
                   0 (second (re-find #":chosen \"([^\"]+)\"" out))
                   1 (die! 1 "no fleet node is quiet enough right now (probe succeeded)")
                   (die! 2 (str "could not probe for a quiet host; refusing to measure\n" out)))))
      _ (when (str/blank? host) (die! 2 "quiet-host returned no host"))
      head (str/trim (:out (sh "git rev-parse HEAD")))
      _ (when (str/blank? head) (die! 2 "cannot resolve HEAD"))
      remote "~/amu-bench"
      ;; The node needs the commit, not the dirty tree: a benchmark whose input
      ;; is not a named commit cannot be re-run to check a later claim. Refuse
      ;; rather than silently measure uncommitted work.
      dirty (str/trim (:out (sh "git status --porcelain -- src bench scripts deps.edn")))
      _ (when (seq dirty)
          (die! 2 (str "refusing to measure an uncommitted tree; commit first:\n" dirty)))
      env (str "export JAVA_HOME=/opt/homebrew/opt/openjdk; "
               "export PATH=$JAVA_HOME/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin; ")
      stage (sh (str "ssh -o BatchMode=yes " host " " (pr-str
                 (str env "set -e; "
                      "if [ ! -d " remote "/.git ]; then git clone -q https://github.com/kotoba-lang/amu.git " remote "; fi; "
                      "cd " remote "; git fetch -q origin; git checkout -q " head "; "
                      "[ -d node_modules ] || npm install --silent --no-audit --no-fund >/dev/null 2>&1; "
                      "git rev-parse HEAD")))
                {:timeout 900000})
      _ (when-not (zero? (:exit stage))
          (die! 2 (str "staging " head " on " host " failed:\n" (:out stage))))
      staged (str/trim (last (remove str/blank? (str/split-lines (:out stage)))))
      _ (when-not (= staged head)
          (die! 2 (str "host has " staged " but HEAD is " head)))
      remote-json (str "~/amu-evidence/" bench-name "-" (subs head 0 12) "-" (.now js/Date) ".json")
      cmd (str env "set -e; mkdir -p ~/amu-evidence; cd " remote "; "
               "echo BUSY_BEFORE=$(iostat -c2 -w1 | tail -1 | awk '{print 100-$6}'); "
               "node " (:script spec) " " (:out-flag spec) " " remote-json " "
               (str/join " " passthru) "; "
               "echo BUSY_AFTER=$(iostat -c2 -w1 | tail -1 | awk '{print 100-$6}'); "
               "echo REPORT=" remote-json)
      run (sh (str "ssh -o BatchMode=yes " host " " (pr-str cmd)) {:timeout 3600000})
      local-out (arg "--out" (str "/tmp/amu-" bench-name "-" (subs head 0 12) ".json"))]
  (println (:out run))
  (when-let [report (second (re-find #"REPORT=(\S+)" (:out run)))]
    (let [c (sh (str "scp -q " host ":" report " " local-out))]
      (when (zero? (:exit c))
        (println (pr-str {:format :amu.remote-bench/v1 :host host :commit head
                          :bench bench-name :report local-out})))))
  (.exit js/process (if (zero? (:exit run)) 0 1)))
