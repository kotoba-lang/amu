#!/usr/bin/env nbb
(ns jdk-free-native-conformance
  (:require [clojure.string :as str]
            ["node:child_process" :as child]
            ["node:fs" :as fs]
            ["node:os" :as os]
            ["node:path" :as path]))

(def root (.resolve path (.dirname path *file*) ".."))
(def tmp (.mkdtempSync fs (.join path (.tmpdir os) "amu-jdk-free-native-")))
(def shadow (.join path tmp "shadow"))
(def marker (.join path tmp "jvm-invoked.log"))
(def nbb-cli (.join path root "node_modules" "nbb" "cli.js"))
(def kotoba (.join path root "bin" "kotoba"))
(defn file [name] (.join path tmp name))
(defn ensure! [condition message] (when-not condition (throw (js/Error. message))))

(defn run
  ([command args env] (run command args env false))
  ([command args env allow-failure?]
   (let [result (.spawnSync child command (clj->js args)
                            #js {:cwd root :encoding "utf8" :maxBuffer 16777216
                                 :env env})
         status (if (nil? (.-status result)) 70 (.-status result))]
     (when (.-error result) (throw (.-error result)))
     (when (and (not allow-failure?) (not= 0 status))
       (throw (js/Error. (str "command failed: " command " " (str/join " " args)
                              "\n" (or (.-stderr result) "")))))
     {:status status :stdout (or (.-stdout result) "")
      :stderr (or (.-stderr result) "")})))

(try
  (fs/mkdirSync shadow)
  (doseq [binary ["java" "javac" "clojure" "clj"]]
    (let [target (.join path shadow binary)]
      (fs/writeFileSync target
                        (str "#!/bin/sh\necho '" binary " $*' >> '" marker
                             "'\necho '" binary ": forbidden by JDK-free conformance' >&2\nexit 127\n"))
      (fs/chmodSync target (js/parseInt "755" 8))))
  (let [platform (.platform os)
        arch (.arch os)
        isa (cond
              (contains? #{"arm64" "aarch64"} arch) "aarch64"
              (= "x64" arch) "x86_64"
              :else (throw (js/Error. (str "unsupported native conformance architecture: " arch))))
        _ (ensure! (contains? #{"darwin" "linux"} platform)
                   (str "unsupported native conformance platform: " platform))
        env (js/Object.assign #js {} js/process.env
                              #js {"PATH" (str shadow (.-delimiter path) (.-PATH js/process.env))
                                   "JAVA_HOME" (.join path tmp "no-java-home")})
        invoke (fn [args] (run js/process.execPath (into [nbb-cli kotoba "-M"] args) env))
        artifact (file "program.kexe")
        binary (file "program.bin")
        loader (file "kexe-loader")]
    (invoke ["compile" (.join path root "examples" "structured.kotoba")
             "--target" isa "--output" artifact])
    (let [extracted (:stdout (invoke ["extract-native" artifact "--symbol" "score"
                                     "--output" binary]))
          [_ offset] (re-find #":offset ([0-9]+)" extracted)]
      (ensure! offset "extract-native returned no score offset")
      (run "cc" ["-std=c11" "-O2" "-Wall" "-Wextra" "-Werror"
                  (.join path root "tools" "kexe_loader.c") "-o" loader] env)
      (let [executed (run loader [binary offset "2" isa "-" "-7" "2"] env)]
        (ensure! (= "12" (str/trim (:stdout executed)))
                 (str "native score expected 12, got " (str/trim (:stdout executed))))))
    (when (fs/existsSync marker)
      (throw (js/Error. (str "JVM tool was invoked: " (fs/readFileSync marker "utf8")))))
    (println (str "jdk-free-native: sealed " isa
                  " artifact independently extracted and executed under W^X loader")))
  (finally
    (fs/rmSync tmp #js {:recursive true :force true})))
