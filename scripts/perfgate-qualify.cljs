#!/usr/bin/env nbb
;; perfgate-qualify bridge: `nbb scripts/perfgate-qualify.cljs <args...>`
;; Replaced scripts/perfgate-qualify.sh (f9857e8) after check-workflows's
;; repo-wide POSIX-shell ban (7171904) started failing on it -- the rule
;; predates the bridge by six weeks; the shell file just hid under red
;; main runs (amu #705/#707).
;;
;; The JVM is still the executor (perfgate-qualify.clj needs
;; kotoba.native.machine-ir's JVM-only paths); this script only rebuilds
;; the hermetic dependency map the old shell heredoc supplied, as one
;; `-Sdeps EDN` argument (clojure CLI has no -Sdeps-file):
;;    clojure -Sdeps <scripts/perfgate-deps.edn content> -M -m perfgate-qualify "$@"
;;
;; `:paths ["scripts"]` in perfgate-deps.edn is resolved relative to the
;; repo root, so this must run with cwd = repo root -- same contract the
;; bash version had (its `root` computation ended up doing exactly that).
;;
;; The json pin here is the org main (840c35b5), matching deps.edn since
;; #707; the data-json shim is gone and perfgate_qualify.clj uses the
;; map-arity surface only.
(ns perfgate-qualify-bridge
  (:require ["node:child_process" :as child-process]
            ["node:path" :as path]
            ["node:fs" :as fs]))

(def root (str (fs/realpathSync ".")))
;; nbb argv layout for a script: [node, nbb, <script>, ...args] -- the
;; script path itself sits at index 2, so TWO leading items are dropped
;; (measured: `nbb scripts/tmp-argv-probe.cljs a b` -> argv = [node, nbb,
;; script, a, b]; `(rest argv)` alone leaked the script path into the
;; clojure main's args and -main parsed it as the input file).
(def args (drop 3 (js->clj js/process.argv)))
(def deps-path (path/join root "scripts" "perfgate-deps.edn"))

(when-not (fs/existsSync deps-path)
  (binding [*out* *err*]
    (println "perfgate-qualify: missing scripts/perfgate-deps.edn (run from the repo root)"))
  (.exit js/process 3))

(when (empty? args)
  (binding [*out* *err*]
    (println "usage: perfgate-qualify.cljs <benchmark.json> | --validate-manifest-v2 <manifest.json>"))
  (.exit js/process 2))

(def deps-edn (str (fs/readFileSync deps-path "utf8")))

(def result (child-process/spawnSync
             "clojure"
             (clj->js (into ["-Sdeps" deps-edn "-M" "-m" "perfgate-qualify"] args))
             #js {:cwd root
                  :encoding "utf8"
                  :maxBuffer (* 32 1024 1024)
                  :stdio "inherit"}))

(.exit js/process (or (.-status result) 1))
