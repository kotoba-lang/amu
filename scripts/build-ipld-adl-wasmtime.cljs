#!/usr/bin/env nbb
;; Build the synchronous Wasmtime reference engine for io-ipld ADLs.
;;
;; Ported from the POSIX shell script this replaces: nothing in this workspace
;; may execute a `.sh`, and `scripts/check-workflows.cljs` enforces that by
;; refusing any `.sh` file in the tree.
(ns build-ipld-adl-wasmtime
  (:require [clojure.string :as str]
            [scripts.lib :as lib]
            ["node:fs" :as fs]
            ["node:path" :as path]))

(defn prefix
  "Where libwasmtime lives. `WASMTIME_PREFIX` wins so a runner that installed
   the engine outside Homebrew does not have to have `brew` at all."
  []
  (or (aget js/process.env "WASMTIME_PREFIX")
      (str/trim (:stdout (lib/run "brew" ["--prefix" "wasmtime"])))))

(defn build!
  "Compile runtime/ipld-adl-wasmtime.c to OUTPUT and answer OUTPUT."
  [output]
  (let [wasmtime (prefix)]
    (.mkdirSync fs (.dirname path output) #js {:recursive true})
    (lib/run "cc"
             ["-std=c11" "-O2" "-Wall" "-Wextra" "-Werror" "-pthread"
              (str "-I" wasmtime "/include")
              (lib/join lib/root "runtime" "ipld-adl-wasmtime.c")
              (str "-L" wasmtime "/lib")
              (str "-Wl,-rpath," wasmtime "/lib")
              "-lwasmtime" "-o" output])
    output))

(let [output (or (first *command-line-args*)
                 (lib/join lib/root "target" "ipld-adl-wasmtime"))]
  (build! output)
  (println (str "ipld-adl-wasmtime: built " output)))
