;; Stage and observe the Amu-native Mac CLI build; no compiler/emitter here.
;; Ported from build-macos-cli.py (Basilisp, JUN-974). Apple Silicon macOS only.
;; Run: basilisp run -p scripts/seed scripts/seed/build-macos-cli.cljc -- --output DIR
(ns build-macos-cli
  (:require [basilisp.string :as str]
            [gate-util :as u]
            [macos-cli-build :as lib])
  (:import pathlib sys))

(defn -main [& args]
  (lib/build (.resolve (pathlib/Path (or (u/opt args "--output") (sys/exit "--output is required"))))))

(when (some #(or (= % "build-macos-cli.cljc") (str/ends-with? % "/build-macos-cli.cljc")) sys/argv)
  (apply -main *command-line-args*))
