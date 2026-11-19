;; Check locked Wasm project discovery; success still refuses unimplemented linking. Ported from
;; check-wasm-project-admission.py (Basilisp, JUN-974).
;; Run: basilisp run -p scripts/seed scripts/seed/check-wasm-project-admission.cljc -- --compiler F --output OUT
(ns check-wasm-project-admission
  (:require [basilisp.string :as str]
            [gate-util :as u])
  (:import json operator pathlib subprocess sys))

(defn sha [b] (u/sha256-hex b))

(defn -main [& args]
  (let [compiler (.resolve (pathlib/Path (or (u/opt args "--compiler") (sys/exit "--compiler is required"))) ** :strict true)
        root (.resolve (pathlib/Path (or (u/opt args "--output") (sys/exit "--output is required"))))
        _ (.mkdir root ** :parents true :exist_ok false)
        entry (pathlib/Path root "app.kotoba") dep (pathlib/Path root "util.kotoba") lock (pathlib/Path root "source.ksl")
        dep-text "(ns util (:export [add]))\n(defn add [x :i64] :i64 (+ x 1))\n"
        _ (.write_text entry "(ns app (:require [util :as u]) (:export [main]))\n(defn main [] :i64 (u/add 41))\n")
        _ (.write_text dep dep-text)
        make-lock (fn [& [extra]]
                    (let [files (python/sorted (python/list (concat [entry dep] (when extra [extra]))))
                          text (str "KSL1\nentry " entry "\nroot " root "\n"
                                    (apply str (for [p files] (str "file " (sha (.read_bytes p)) " " p "\n"))))]
                      (.write_text lock text)
                      (sha (.encode text))))
        env (u/pydict "PATH" "/nonexistent" "KEXE_ALLOW" "35,37,38,39" "KEXE_CAP_RESOURCES_35" (str root) "KEXE_STACK_BYTES" "8388608")
        calls (python/list [])
        exec- (fn [argv] (subprocess/run (python/list (map str argv)) ** :cwd root :env env :capture_output true :timeout 120))
        run (fn [name tail status marker]
              (let [image (pathlib/Path root (str name ".wasm"))
                    proc (exec- (concat [compiler "compile" entry "--target" "wasm32-browser" "--output" image] tail))]
                (u/chk (and (= (.-returncode proc) status) (u/has-bytes? (.encode marker) (.-stderr proc)) (not (.exists image)))
                       (str [name (.-returncode proc) (.-stderr proc)]))
                (.append calls (u/pydict "case" name "exit" (.-returncode proc) "stderr" (.decode (.-stderr proc))))))
        scalar (pathlib/Path root "scalar.kotoba") wasm (pathlib/Path root "scalar.wasm")]
    (.write_text scalar "(ns scalar (:export [main]))\n(defn main [] :i64 42)\n")
    (let [basic (exec- [compiler "compile" scalar "--target" "wasm32-browser" "--output" wasm])]
      (u/chk (and (= (.-returncode basic) 0) (zero? (python/len (.-stderr basic)))
                  (.startswith (.read_bytes wasm) (u/bytes-of 0 0x61 0x73 0x6d 1 0 0 0)))
             (str [(.-returncode basic) (.-stderr basic)]))
      (.append calls (u/pydict "case" "single-source" "exit" (.-returncode basic) "wasmSha256" (sha (.read_bytes wasm)))))
    (let [single-text (str "KSL2\nentry " scalar "\nmodule scalar " scalar "\nfile " (sha (.read_bytes scalar)) " " scalar "\n")
          single-wasm (pathlib/Path root "single-mapped.wasm")]
      (.write_text lock single-text)
      (let [single (exec- [compiler "compile" scalar "--target" "wasm32-browser" "--output" single-wasm "--source-lock" lock "--source-lock-sha256" (sha (.encode single-text))])]
        (u/chk (and (= (.-returncode single) 0) (zero? (python/len (.-stderr single))) (u/deq (.read_bytes single-wasm) (.read_bytes wasm)))
               (str [(.-returncode single) (.-stderr single)]))
        (.append calls (u/pydict "case" "single-mapped-source" "exit" (.-returncode single) "wasmSha256" (sha (.read_bytes single-wasm))))))
    (let [digest (make-lock)
          prefix ["--source-path" root "--source-lock" lock "--source-lock-sha256"]
          positive (exec- (concat [compiler "check" entry] prefix [digest]))]
      (u/chk (and (= (.-returncode positive) 0) (zero? (python/len (.-stderr positive)))) (str [(.-returncode positive) (.-stderr positive)]))
      (run "valid" (concat prefix [digest]) 2 "E7107")
      (run "wrong-digest" (concat prefix [(apply str (repeat 64 "0"))]) 1 "E6015")
      (.write_text dep (str (.read_text dep) "\n;; changed\n"))
      (run "changed-source" (concat prefix [digest]) 1 "E6015")
      (.write_text dep dep-text)
      (let [extra (pathlib/Path root "unused.kotoba")
            _ (.write_text extra "(ns unused)\n")
            digest (make-lock extra)]
        (run "extra-source" (concat prefix [digest]) 1 "E6015"))
      (make-lock)
      (run "missing-digest" ["--source-path" root "--source-lock" lock] 2 "E7100")
      (run "unpinned" ["--source-path" root "--unpinned"] 2 "E7100"))
    (let [mapped (str "KSL2\nentry " entry "\nmodule app " entry "\nmodule util " dep "\n"
                      (apply str (for [p (python/sorted (python/list [entry dep]))] (str "file " (sha (.read_bytes p)) " " p "\n"))))
          _ (.write_text lock mapped)
          mapped-digest (sha (.encode mapped))
          mapped-args ["--source-lock" lock "--source-lock-sha256" mapped-digest]
          mapped-check (exec- (concat [compiler "check" entry] mapped-args))]
      (u/chk (and (= (.-returncode mapped-check) 0) (zero? (python/len (.-stderr mapped-check)))) (str [(.-returncode mapped-check) (.-stderr mapped-check)]))
      (run "mapped-project" mapped-args 2 "E7107")
      (run "mapped-wrong-digest" ["--source-lock" lock "--source-lock-sha256" (apply str (repeat 64 "0"))] 1 "E6015")
      (run "mapped-missing-digest" ["--source-lock" lock] 2 "E7100")
      (run "mapped-unpinned" ["--source-lock" lock "--source-lock-sha256" mapped-digest "--unpinned"] 2 "E7100")
      (.write_text dep (str (.read_text dep) "\n;; changed mapped dependency\n"))
      (run "mapped-changed-source" mapped-args 1 "E6015"))
    (.write_text (pathlib/Path root "receipt.json")
                 (u/json-dump (u/pydict "status" "PASS_LOCKED_WASM_PROJECT_ADMISSION" "compilerSha256" (sha (.read_bytes compiler))
                                        "cases" calls
                                        "limitations" (python/list ["valid project still refuses E7107; no Wasm project linker or artifact" "no browser graph or x86 qualification"]))))
    (println "PASS_LOCKED_WASM_PROJECT_ADMISSION")))

(when (some #(or (= % "check-wasm-project-admission.cljc") (str/ends-with? % "/check-wasm-project-admission.cljc")) sys/argv)
  (apply -main *command-line-args*))
