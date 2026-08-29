(ns scripts.test-nbb-native-value-abi
  "Launcher for `test/nbb/native-value-abi.cljs`, mirroring
  `scripts/test-nbb-clock-transport.cljs` exactly: `clojure -Spath` resolves
  the full dependency closure that `kotoba.compiler.nbb.cli` needs (a literal
  `--classpath src` cannot see `kotoba.compiler.kotoba-reader`), and that
  classpath plus this repo's root is handed to a child `nbb` process."
  (:require [scripts.lib :as lib]
            ["node:child_process" :as child]
            ["node:path" :as path]))

(let [resolved (lib/run "clojure" ["-Spath" "-M:test"])
      nbb-cli (lib/join lib/root "node_modules" "nbb" "cli.js")
      classpath (str lib/root (.-delimiter path) (.trim (:stdout resolved)))
      result (.spawnSync child js/process.execPath
                         (clj->js [nbb-cli "--classpath" classpath
                                   (lib/join lib/root "test" "nbb" "native-value-abi.cljs")])
                         #js {:cwd lib/root :stdio "inherit" :env js/process.env})]
  (when (.-error result) (throw (.-error result)))
  (.exit js/process (or (.-status result) 70)))
