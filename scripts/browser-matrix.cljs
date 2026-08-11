#!/usr/bin/env nbb
(ns browser-matrix
  (:require ["node:child_process" :as child]
            ["node:fs" :as fs]
            ["node:os" :as os]
            ["node:path" :as path]))

(def root (.resolve path (.dirname path *file*) ".."))
(def tmp (.mkdtempSync fs (.join path (.tmpdir os) "kotoba-browser-matrix-")))
(def kotoba (.join path root "bin" "kotoba"))
(def nbb-cli (.join path root "node_modules" "nbb" "cli.js"))
(defn run! [command args env]
  (let [result (.spawnSync child command (clj->js args)
                           #js {:cwd root :stdio "inherit"
                                :env (js/Object.assign #js {} js/process.env (clj->js env))})]
    (when (.-error result) (throw (.-error result)))
    (when-not (zero? (or (.-status result) 70))
      (throw (js/Error. (str "browser matrix command failed: " command))))))
(defn nbb! [args env] (run! js/process.execPath (into [nbb-cli] args) env))
(defn compile! [source output & more]
  (nbb! (into [kotoba "-M" "compile" (.join path root source)
               "--target" "wasm32-browser" "--output" (.join path tmp output)] more) {}))

(defn compile-web!
  "Emit a restricted-ESM artifact for the DOM app-driver lane.

  Unlike the wasm32 compiles above this one is NOT on the JDK-free fast path:
  `bin/kotoba` routes every non-wasm/native target to `clojure -M:run`, because
  the web backend (kotoba-lang/kotoba-script) is JVM-only Clojure with no nbb
  entrypoint. Said out loud rather than discovered as a confusing JVM spawn --
  the browser matrix needs a JDK for this artifact and only this one."
  [source output]
  (println (str "browser-matrix: compiling " source
                " for the web target (needs a JDK; the web backend is JVM-only)"))
  (nbb! [kotoba "-M" "compile" (.join path root source)
         "--target" "js-browser" "--output" (.join path tmp output)] {}))

(try
  (compile! "examples/structured.kotoba" "program.wasm")
  (compile! "examples/heap.kotoba" "heap.wasm")
  (compile! "tests/browser/capability.kotoba" "capability.wasm"
            "--policy" (.join path root "examples/capability-policy.edn"))
  (compile-web! "examples/todo-app.kotoba" "todo-app.mjs")
  (run! js/process.execPath [(.join path root "node_modules/@playwright/test/cli.js") "test"]
        {:KOTOBA_BROWSER_ARTIFACTS tmp})
  (nbb! [(.join path root "scripts/check-browser-evidence.cljs")] {})
  (finally (.rmSync fs tmp #js {:recursive true :force true})))
