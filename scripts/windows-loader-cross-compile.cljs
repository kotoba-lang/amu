#!/usr/bin/env nbb
(ns windows-loader-cross-compile
  (:require ["node:child_process" :as child]
            ["node:fs" :as fs]
            ["node:os" :as os]
            ["node:path" :as path]))

(def root (.resolve path (.dirname path *file*) ".."))
(def source (.join path root "tools" "kexe_loader_windows.c"))
(def zig (or (.-KOTOBA_ZIG (.-env js/process)) "zig"))
(def expected-zig "0.15.2")
(def targets [{:triple "x86_64-windows-gnu" :machine 0x8664 :label "x86-64"}
              {:triple "aarch64-windows-gnu" :machine 0xaa64 :label "Arm64"}])
(def flags ["-std=c11" "-O2" "-Wall" "-Wextra" "-Werror"])
(def libraries ["-ladvapi32" "-luserenv" "-lws2_32" "-lfwpuclnt" "-lrpcrt4"])

(defn fail! [message]
  (binding [*print-fn* *print-err-fn*] (println (str "windows-loader-cross: " message)))
  (js/process.exit 1))

(defn ensure! [condition message]
  (when-not condition (fail! message)))

(defn run! [command args]
  (let [result (.spawnSync child command (clj->js args)
                           #js {:cwd root :encoding "utf8" :maxBuffer 1048576})]
    (when (.-error result)
      (fail! (str "cannot execute " command ": " (.-message (.-error result)))))
    (when-not (zero? (or (.-status result) 70))
      (fail! (str command " failed (exit " (.-status result) ")\n"
                  (or (.-stdout result) "") (or (.-stderr result) ""))))
    result))

(defn u16le [buffer offset]
  (.readUInt16LE buffer offset))

(defn u32le [buffer offset]
  (.readUInt32LE buffer offset))

(defn inspect-pe! [file {:keys [machine label]}]
  (let [bytes (.readFileSync fs file)]
    (ensure! (>= (.-length bytes) 256) (str label " output is too small"))
    (ensure! (= "MZ" (.toString bytes "ascii" 0 2)) (str label " lacks DOS header"))
    (let [pe-offset (u32le bytes 0x3c)]
      (ensure! (<= (+ pe-offset 26) (.-length bytes))
               (str label " PE header lies outside the file"))
      (ensure! (= "PE\u0000\u0000" (.toString bytes "binary" pe-offset (+ pe-offset 4)))
               (str label " lacks PE signature"))
      (ensure! (= machine (u16le bytes (+ pe-offset 4)))
               (str label " machine field is not " (.toString machine 16)))
      (ensure! (= 0x20b (u16le bytes (+ pe-offset 24)))
               (str label " is not PE32+")))
    bytes))

(defn compile! [directory target]
  (let [target-directory (.join path directory (:label target))
        _ (.mkdirSync fs target-directory #js {:recursive true})
        output (.join path target-directory "kexe-loader.exe")]
    (run! zig (vec (concat ["cc" "-target" (:triple target)] flags
                           [source "-o" output] libraries)))
    output))

(let [tmp (.mkdtempSync fs (.join path (.tmpdir os) "kotoba-windows-cross-"))]
  (try
    (let [version (.trim (.-stdout (run! zig ["version"])))]
      (ensure! (= expected-zig version)
               (str "expected Zig " expected-zig ", got " version)))
    (doseq [target targets]
      (let [output (compile! tmp target)
            first-bytes (inspect-pe! output target)
            _ (compile! tmp target)
            second-bytes (inspect-pe! output target)]
        (ensure! (.equals first-bytes second-bytes)
                 (str (:label target) " loader cross-build is not reproducible"))
        (println (str "windows-loader-cross: " (:label target)
                      " PE32+ reproducible (" (.-length first-bytes) " bytes)"))))
    (println "windows-loader-cross: OK")
    (finally
      (.rmSync fs tmp #js {:recursive true :force true}))))
