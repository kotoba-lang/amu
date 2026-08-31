;; Launcher for the perfgate qualification entrypoint. Replaces
;; scripts/perfgate-qualify.sh (workspace rule: no POSIX shell execution
;; files; scripts are nbb). Same pinned -Sdeps universe, same entrypoint,
;; same arguments; exits with the child's exit code.
(ns perfgate-qualify
  (:require ["node:child_process" :as child]
            ["node:path" :as path]))

(def root (.resolve path (.dirname path (or js/__filename ".")) ".."))

(def deps
  (pr-str
   '{:paths ["scripts"]
     :deps {org.clojure/clojure {:mvn/version "1.12.0"}
            io.github.kotoba-lang/json
            {:git/url "https://github.com/kotoba-lang/json.git"
             :git/sha "b47b06486b3ad53051bc7d8bf361f4176f467202"}
            io.github.kotoba-lang/perfgate
            {:git/url "https://github.com/kotoba-lang/perfgate.git"
             :git/sha "d4417d77c2333047dd4e478675e5ed13e1c6b1b8"}
            io.github.kotoba-lang/machine
            {:git/url "https://github.com/kotoba-lang/machine.git"
             :git/sha "e7235657c6f6bc4e43e7e6126c1c0912e8dbf5f4"}}}))

(def arguments (vec (drop 3 (.-argv js/process))))

(when (empty? arguments)
  (.error js/console
          "usage: nbb scripts/perfgate-qualify.cljs <benchmark.json> | --validate-manifest-v2 <manifest.json>")
  (.exit js/process 2))

(let [result (.spawnSync child "clojure"
                         (clj->js (into ["-Sdeps" deps "-M" "-m" "perfgate-qualify"]
                                        arguments))
                         #js {:cwd root :stdio "inherit"})]
  (.exit js/process (or (.-status result) 1)))
