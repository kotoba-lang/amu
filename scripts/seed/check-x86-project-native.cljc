;; Qualify locked typed project linking through the existing native KX64 runner. No declaration is trimmed. The
;; Kotoba fixture owns the result and exercises multi-hop imports, literals in three modules, keyword identity,
;; schema return, eight arguments, a captured callback and document helpers across modules. Ported from
;; check-x86-project-native.py (Basilisp, JUN-974).
;; Run: basilisp run -p scripts/seed scripts/seed/check-x86-project-native.cljc -- --compiler F --output DIR
;;      [--compile-only]
(ns check-x86-project-native
  (:require [basilisp.string :as str]
            [gate-util :as u])
  (:import json operator pathlib platform re shutil subprocess sys time))

(def root u/root)
(defn rp [rel] (pathlib/Path root rel))
(defn g [m & ks] (reduce (fn [a k] (operator/getitem a k)) m ks))
(defn pin [p] (let [d (.read_bytes (pathlib/Path p))] (u/pydict "bytes" (python/len d) "sha256" (u/sha256-hex d))))
(defn chk [c m] (u/chk c (str m)))
(defn pyenv [& kvs] (apply u/pydict kvs))

(defn run-main [compiler out compile-only?]
  (chk (= (platform/system) "Linux") "Linux required")
  (when-not compile-only? (chk (= (platform/machine) "x86_64") "native x86 Linux required"))
  (.mkdir out ** :parents true :exist_ok false)
  (let [source (pathlib/Path out "src/x86_project")
        _ (.mkdir source ** :parents true)
        _ (doseq [p (python/list (.glob (rp "seed/tests/x86-project") "*.kotoba"))] (shutil/copy2 p (pathlib/Path source (.-name p))))
        entry (pathlib/Path source "entry.kotoba")
        paths (python/sorted (python/list (.glob source "*.kotoba")))
        lock (pathlib/Path out "project.ksl")
        write-lock! (fn [] (.write_text lock (str "KSL1\nentry " entry "\nroot " (.-parent source) "\n"
                                                  (apply str (for [p paths] (str "file " (g (pin p) "sha256") " " p "\n"))))))
        _ (write-lock!)
        flags [ "--source-path" (.-parent source) "--source-lock" lock "--source-lock-sha256" (g (pin lock) "sha256")]
        env (pyenv "PATH" "/nonexistent" "KEXE_STACK_BYTES" "8388608" "KEXE_CAP_RESOURCES_35" (str out))
        calls (python/list [])
        run (fn [name args & {:keys [custom ok] :or {ok true}}]
              (let [started (time/monotonic)
                    result (subprocess/run (python/list (map str args)) ** :env (or custom env) :cwd out :capture_output true :timeout 900)]
                (doseq [[suffix data] [["stdout" (.-stdout result)] ["stderr" (.-stderr result)]]]
                  (.write_bytes (pathlib/Path out (str name "." suffix)) data))
                (.append calls (pyenv "name" name "exit" (.-returncode result) "argv" (python/list (map str args))
                                      "seconds" (python/round (- (time/monotonic) started) 3)))
                (.write_text (pathlib/Path out "calls.json") (u/json-dump calls))
                (println name (.-returncode result) (let [e (.decode (.-stderr result) "utf-8" "replace")] (subs e 0 (min 400 (count e)))))
                (.flush sys/stdout)
                (when ok
                  (chk (and (= (.-returncode result) 0) (zero? (python/len (.-stderr result))))
                       [name (.-returncode result) (let [e (.-stderr result)] (.decode (u/bslice e (max 0 (- (python/len e) 1000)) (python/len e)) "utf-8" "replace"))]))
                result))]
    (run "check" (concat [compiler "check" entry] flags))
    (let [artifact (pathlib/Path out "project.kx64")]
      (run "compile" (concat [compiler "compile" entry "--target" "x86_64-linux" "--output" artifact "--format" "kx64-v1"] flags))
      (let [parts (.split (.read_bytes artifact) (.encode "\n\n") 1)
            header (operator/getitem parts 0) body (operator/getitem parts 1)
            m (re/fullmatch (.encode "KX64V1 x86_64-linux sysv-ctx-v11 ([0-9]+) 0") header)]
        (chk (and m (= (python/len body) (python/int (.group m 1))) (= (operator/getitem body 0) 0xe9)) "kx64 header")
        (let [payload (pathlib/Path out "project.bin")
              _ (.write_bytes payload body)
              runner-source (pathlib/Path out "runner.kotoba")
              _ (shutil/copy2 (rp "seed/x86_64-kx64-runner.kotoba") runner-source)
              runner (pathlib/Path out "runner.elf")
              _ (run "runner" [compiler "compile" runner-source "--target" "x86_64-linux" "--output" runner "--format" "kx64-runner"])
              _ (.chmod runner 0755)
              observed (when-not compile-only?
                         (let [result (run "execute" [runner payload 0 0 "x86_64" "-"]
                                           :custom (let [d (python/dict env)] (.update d (pyenv "KEXE_STRUCTURED_REPORT" "1" "KEXE_ALLOW" "-")) d))
                               value (re/search (.encode ":result (-?[0-9]+)") (.-stdout result))]
                           (chk (and value (= (python/int (.group value 1)) 42)) (.-stdout result))
                           42))
              refusal (pathlib/Path out "refused.kx64")
              probes [["wrong-digest" (concat (butlast flags) [(apply str (repeat 64 "0"))]) "E6015"]
                      ["missing-lock" ["--source-path" (.-parent source)] "E6015"]
                      ["unlocked" (concat flags ["--unpinned"]) "E6015"]
                      ["wrong-format" (concat flags ["--format" "static"]) "E1"]
                      ["unknown-option" (concat flags ["--anything" "1"]) "E1"]]
              refusals (python/list [])]
          (doseq [[name options diagnostic] probes]
            (let [result (run name (concat [compiler "compile" entry "--target" "x86_64-linux" "--output" refusal "--format" "kx64-v1"] options) :ok false)]
              (chk (and (contains? #{1 2} (.-returncode result)) (u/has-bytes? (.encode diagnostic) (.-stderr result)) (not (.exists refusal))) [name (.-stderr result)])
              (.append refusals (pyenv "name" name "diagnostic" diagnostic "noArtifact" true))))
          ;; An unreachable bad declaration must still refuse before any artifact.
          (let [middle (pathlib/Path source "middle.kotoba")
                original (.read_bytes middle)]
            (.write_bytes middle (operator/add original (.encode "\n(defn- unused [] :i64 (not-an-operation 1))\n")))
            (write-lock!)
            (let [result (run "unreachable-invalid" [compiler "compile" entry "--target" "x86_64-linux" "--output" refusal "--format" "kx64-v1"
                                                     "--source-path" (.-parent source) "--source-lock" lock "--source-lock-sha256" (g (pin lock) "sha256")] :ok false)]
              (chk (and (= (.-returncode result) 1) (u/has-bytes? (.encode "E2101") (.-stderr result)) (not (.exists refusal))) "unreachable-invalid")
              (.append refusals (pyenv "name" "unreachable-invalid" "diagnostic" "E2101" "noArtifact" true)))
            (.write_bytes middle original))
          (let [report (pyenv "status" (if compile-only? "COMPILED_NOT_EXECUTED" "PASS_LOCKED_X86_PROJECT_NATIVE")
                              "compiler" (pin compiler) "artifact" (pin artifact) "runner" (pin runner) "result" observed
                              "sources" (u/pydict-from (for [p paths] [(.-name p) (pin p)])) "refusals" refusals
                              "emulation" false "nativeX86Qualified" (not compile-only?) "cssomQualified" false "kernelDesktopQualified" false)]
            (.write_text (pathlib/Path out "x86-project.json") (u/json-dump report))
            (println (g report "status"))
            (.flush sys/stdout)))))))

(defn -main [& args]
  (run-main (.resolve (pathlib/Path (or (u/opt args "--compiler") (sys/exit "--compiler is required"))))
            (.resolve (pathlib/Path (or (u/opt args "--output") (sys/exit "--output is required"))))
            (boolean (some #{"--compile-only"} args))))

(when (some #(or (= % "check-x86-project-native.cljc") (str/ends-with? % "/check-x86-project-native.cljc")) sys/argv)
  (apply -main *command-line-args*))
