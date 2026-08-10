#!/usr/bin/env nbb
(ns scripts.test-clean-clone-cli
  "Exercise the shipped CLI from a dependency-empty clone. The fake clojure
  executable makes any fallback to tools.deps fail, so success proves the
  checked-in lock is sufficient after the documented `npm ci` bootstrap."
  (:require [clojure.string :as str]
            ["node:child_process" :as child]
            ["node:fs" :as fs]
            ["node:os" :as os]
            ["node:path" :as path]))

(def root (.resolve path (.dirname path *file*) ".."))
(def tmp (.mkdtempSync fs (.join path (.tmpdir os) "kotoba-clean-clone-")))
(def checkout (.join path tmp "compiler"))
(def fake-bin (.join path tmp "bin"))
(def isolated-gitlibs (.join path tmp "gitlibs"))
(def output (.join path tmp "named-capability.kexe"))
(def normal-output (.join path tmp "named-capability-normal.kexe"))

(defn- run! [command args options]
  (let [result (.spawnSync child command (clj->js args)
                           (js/Object.assign
                            #js {:cwd checkout :encoding "utf8"
                                 :maxBuffer 16777216}
                            options))]
    (when (or (.-error result) (not= 0 (or (.-status result) 70)))
      (throw (js/Error.
              (str command " failed\n" (or (.-stdout result) "")
                   (or (.-stderr result) "")))))
    result))

(try
  (run! "git" ["clone" "--quiet" "--local" "--no-hardlinks" root checkout]
        #js {:cwd tmp})
  (run! "npm" ["ci" "--ignore-scripts"] #js {})
  (.mkdirSync fs fake-bin #js {:recursive true})
  (let [clojure-stub (.join path fake-bin "clojure")]
    (.writeFileSync fs clojure-stub "#!/bin/sh\nexit 99\n")
    (.chmodSync fs clojure-stub 493))
  (let [env (js/Object.assign
             #js {} js/process.env
             #js {:GITLIBS isolated-gitlibs
                  :PATH (str fake-bin (.-delimiter path) (.-PATH js/process.env))})
        result (run! (.join path checkout "bin" "kotoba")
                     ["-M" "compile" "examples/capability-named.kotoba"
                      "--target" "aarch64"
                      "--policy" "examples/capability-named.edn"
                      "--output" output]
                     #js {:env env})
        stdout (or (.-stdout result) "")
        stderr (or (.-stderr result) "")]
    (when-not (.existsSync fs output)
      (throw (js/Error. "clean-clone CLI produced no artifact")))
    (when (str/includes? stderr "falling back to `clojure -Spath`")
      (throw (js/Error. "clean-clone CLI used the JVM fallback")))
    (when-not (str/includes? stdout ":ok true")
      (throw (js/Error. (str "clean-clone CLI returned no success envelope\n" stdout))))
    ;; The isolated invocation must not poison the shared classpath cache with
    ;; paths under TMP, which are deleted when this test exits.
    (run! (.join path root "bin" "kotoba")
          ["-M" "compile" "examples/capability-named.kotoba"
           "--target" "aarch64"
           "--policy" "examples/capability-named.edn"
           "--output" normal-output]
          #js {:cwd root :env js/process.env})
    (when-not (.existsSync fs normal-output)
      (throw (js/Error. "normal CLI failed after isolated clean-clone invocation")))
    (println "PASS clean-clone named-capability native CLI without JVM fallback"))
  (finally
    (.rmSync fs tmp #js {:recursive true :force true})))
