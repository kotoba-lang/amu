(ns scripts.test-nbb-wasm32
  (:require [scripts.lib :as lib]
            ["node:child_process" :as child]
            ["node:path" :as path]))

(let [resolved (lib/run "clojure" ["-Spath"])
      nbb-cli (lib/join lib/root "node_modules" "nbb" "cli.js")
      classpath (str lib/root (.-delimiter path) (.trim (:stdout resolved)))
      result (.spawnSync child js/process.execPath
                         ;; Match bin/kotoba's bounded NBB compiler stack.
                         (clj->js ["--stack-size=4096"
                                  nbb-cli "--classpath" classpath
                                  (lib/join lib/root "test" "nbb" "run.cljs")])
                         #js {:cwd lib/root :stdio "inherit" :env js/process.env})]
  (when (.-error result) (throw (.-error result)))
  (.exit js/process (or (.-status result) 70)))
