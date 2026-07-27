(ns scripts.test-nbb-storage-provider
  "Launcher for `test/nbb/storage-provider.cljs` (W5 family-4 second slice /
  ADR 0089)."
  (:require [scripts.lib :as lib]
            ["node:child_process" :as child]
            ["node:path" :as path]))

(let [resolved (lib/run "clojure" ["-Spath" "-M:test"])
      nbb-cli (lib/join lib/root "node_modules" "nbb" "cli.js")
      classpath (str lib/root (.-delimiter path) (.trim (:stdout resolved)))
      result (.spawnSync child js/process.execPath
                         (clj->js [nbb-cli "--classpath" classpath
                                  (lib/join lib/root "test" "nbb" "storage-provider.cljs")])
                         #js {:cwd lib/root :stdio "inherit" :env js/process.env})]
  (when (.-error result) (throw (.-error result)))
  (.exit js/process (or (.-status result) 70)))
