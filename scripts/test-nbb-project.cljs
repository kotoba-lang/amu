(ns scripts.test-nbb-project
  "Run the NBB project integration test against the complete pinned source
  classpath. Semantic-analysis namespaces now come from kotoba-sema rather
  than this repository's src directory."
  (:require [scripts.lib :as lib]
            ["node:child_process" :as child]
            ["node:path" :as path]))

(let [resolved (lib/run "clojure" ["-Spath"])
      nbb-cli (lib/join lib/root "node_modules" "nbb" "cli.js")
      classpath (str lib/root (.-delimiter path) (.trim (:stdout resolved)))
      result (.spawnSync child js/process.execPath
                         (clj->js [nbb-cli "--classpath" classpath
                                  (lib/join lib/root "test" "nbb" "project.cljs")])
                         #js {:cwd lib/root :stdio "inherit" :env js/process.env})]
  (when (.-error result) (throw (.-error result)))
  (.exit js/process (or (.-status result) 70)))
