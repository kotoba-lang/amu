;; Observe opt-in FS35/CLI38 project effects, native grants and refusals. An experimental compiler test, not
;; public product/root adoption. Source and native runtime own admission and filesystem results; this stages and
;; observes. Ported from check-x86-project-effects-native.py (Basilisp, JUN-974). Needs native x86_64 Linux.
;; Run: basilisp run -p scripts/seed scripts/seed/check-x86-project-effects-native.cljc -- --compiler F
;;      --compiler-sha256 H --runner R --output DIR
(ns check-x86-project-effects-native
  (:require [basilisp.string :as str]
            [gate-util :as u])
  (:import json operator os pathlib platform re subprocess sys))

(def root u/root)
(defn rp [rel] (pathlib/Path root rel))
(defn g [m & ks] (reduce (fn [a k] (operator/getitem a k)) m ks))
(defn sha [data] (u/sha256-hex data))
(defn chk [c m] (u/chk c (str m)))
(defn pyenv [& kvs] (apply u/pydict kvs))
(defn env+ [base & kvs] (let [d (python/dict base)] (.update d (apply pyenv kvs)) d))
(defn b [s] (.encode s))
(defn tailb [bs n] (.decode (u/bslice bs (max 0 (- (python/len bs) n)) (python/len bs)) "utf-8" "replace"))

(defn run-main [compiler runner out compiler-sha]
  (chk (and (= (platform/system) "Linux") (= (platform/machine) "x86_64")) "native x86_64 Linux required")
  (chk (= (sha (.read_bytes compiler)) compiler-sha) "compiler digest")
  (.mkdir out ** :parents true :exist_ok false :mode 0700)
  (let [observations (python/list [])
        derivation nil
        env (pyenv "PATH" "/nonexistent" "KEXE_CAP_RESOURCES_35" (str out) "KEXE_STACK_BYTES" "8388608")
        original (let [d (python/dict)]
                   (doseq [p (python/list (.glob (rp "seed/tests/x86-project-effects") "*.kotoba"))]
                     (operator/setitem d (.-name p) (.read_bytes p)))
                   d)
        call (fn [label argv & {:keys [custom expected diagnostic timeout] :or {expected 0 timeout 120}}]
               (let [result (subprocess/run (python/list (map str argv)) ** :env (or custom env) :cwd out :capture_output true :timeout timeout)]
                 (.write_bytes (pathlib/Path out (str label ".stdout")) (.-stdout result))
                 (.write_bytes (pathlib/Path out (str label ".stderr")) (.-stderr result))
                 (chk (= (.-returncode result) expected) [label (.-returncode result) (tailb (.-stderr result) 500)])
                 (cond diagnostic (chk (and (u/has-bytes? (b diagnostic) (.-stderr result)) (not (u/has-bytes? (b "KEXE_TRAP") (.-stderr result)))) [label (.-stderr result)])
                       (zero? expected) (chk (zero? (python/len (.-stderr result))) [label (.-stderr result)]))
                 (.append observations (pyenv "name" label "exit" (.-returncode result)
                                              "stdoutSHA256" (sha (.-stdout result)) "stderrSHA256" (sha (.-stderr result))))
                 (println label (.-returncode result))
                 (.flush sys/stdout)
                 result))
        build (fn [label files & {:keys [diagnostic caps] :or {caps "35,38"}}]
                (let [src-root (pathlib/Path out label "src")]
                  (doseq [[name data] (.items files)]
                    (let [path (pathlib/Path src-root "x86_project_fs" name)]
                      (.mkdir (.-parent path) ** :parents true :exist_ok true)
                      (.write_bytes path data)))
                  (let [entry (pathlib/Path src-root "x86_project_fs/entry.kotoba")
                        lock (pathlib/Path out (str label ".ksl"))
                        paths (python/sorted (python/list (.glob src-root "x86_project_fs/*.kotoba")))
                        _ (.write_text lock (str "KSL1\nentry " entry "\nroot " src-root "\n"
                                                 (apply str (for [p paths] (str "file " (sha (.read_bytes p)) " " p "\n")))))
                        artifact (pathlib/Path out (str label ".kx64"))
                        options (if (nil? caps) [] ["--project-capabilities" caps])]
                    (call label (concat [compiler "compile" entry "--target" "x86_64-linux" "--output" artifact "--format" "kx64-v1"
                                         "--source-path" src-root "--source-lock" lock "--source-lock-sha256" (sha (.read_bytes lock))] options)
                          :expected (if diagnostic 1 0) :diagnostic diagnostic)
                    (if diagnostic
                      (do (chk (not (.exists artifact)) label) nil)
                      (let [parts (.split (.read_bytes artifact) (b "\n\n") 1)
                            header (operator/getitem parts 0) payload (operator/getitem parts 1)
                            m (re/fullmatch (b "KX64V1 x86_64-linux sysv-ctx-v11 ([0-9]+) 0") header)]
                        (chk (and m (= (python/len payload) (python/int (.group m 1))) (= (operator/getitem payload 0) 0xe9)) label)
                        (let [image (pathlib/Path out (str label ".bin"))]
                          (.write_bytes image payload)
                          image))))))]
    (build "no-opt-in" original :diagnostic "E7101" :caps nil)
    (build "missing-cli" original :diagnostic "E7101" :caps "35")
    (let [image (build "declared" original)
          entry (pathlib/Path out "declared/src/x86_project_fs/entry.kotoba")
          src-root (pathlib/Path out "declared/src")
          lock (pathlib/Path out "declared.ksl")
          reordered (pathlib/Path out "reordered.kx64")]
      (call "option-before-lock" [compiler "compile" entry "--target" "x86_64-linux" "--project-capabilities" "35,38" "--output" reordered "--format" "kx64-v1"
                                  "--source-path" src-root "--source-lock" lock "--source-lock-sha256" (sha (.read_bytes lock))])
      (chk (u/deq (.read_bytes reordered) (.read_bytes (pathlib/Path out "declared.kx64"))) "reordered options change the artifact")
      (let [args [compiler "compile" entry "--target" "x86_64-linux" "--format" "kx64-v1"
                  "--source-path" src-root "--source-lock" lock "--source-lock-sha256" (sha (.read_bytes lock))]]
        (doseq [[label options] [["unsorted" ["--project-capabilities" "38,35"]]
                                 ["duplicate-wire" ["--project-capabilities" "35,35"]]
                                 ["out-of-range" ["--project-capabilities" "48"]]
                                 ["leading-zero" ["--project-capabilities" "035"]]
                                 ["trailing-comma" ["--project-capabilities" "35,"]]
                                 ["duplicate-flag" ["--project-capabilities" "35" "--project-capabilities" "38"]]]]
          (let [refused (pathlib/Path out (str label ".kx64"))]
            (call label (concat args ["--output" refused] options) :expected 2 :diagnostic "E1")
            (chk (not (.exists refused)) label))))
      (let [net (python/dict original)
            _ (operator/setitem net "io.kotoba" (b (str "(ns x86-project-fs.io (:export [roundtrip]) (:capabilities [:net/write]))\n"
                                                        "(defn roundtrip [base :string] :bool (= (typed-cap-call 47 :string :string base) \"x\"))\n")))
            _ (build "network-not-opted-in" net :diagnostic "E7101" :caps "38")
            network (build "network-opted-in" net :caps "38,47")
            net-env (env+ env "KEXE_ALLOW" "38" "KEXE_STRUCTURED_REPORT" "1" "KEXE_FUEL" "10000000")
            denied (call "network-ungranted" [runner network 0 0 "x86_64" "38" "--" "unused"] :custom net-env :expected 120)]
        (chk (u/has-bytes? (b "KEXE_CAP {:wire 47 :refused :not-granted}") (.-stderr denied)) (.-stderr denied)))
      (let [base (pathlib/Path out "scope")
            _ (.mkdir base)
            execute (fn [label target allow & [expected]]
                      (call label [runner image 0 0 "x86_64" allow "--" target]
                            :custom (env+ env "KEXE_ALLOW" allow "KEXE_STRUCTURED_REPORT" "1" "KEXE_FUEL" "10000000" "KEXE_CAP_RESOURCES_35" (str base))
                            :expected (or expected 0)))
            passed (execute "roundtrip" base "35,38")
            _ (chk (re/search (b ":result 42\\b") (.-stdout passed)) (.-stdout passed))
            missing (execute "ungranted-fs" base "38" 120)
            _ (chk (u/has-bytes? (b "KEXE_CAP {:wire 35 :refused :not-granted}") (.-stderr missing)) "ungranted fs")
            missing-cli (execute "ungranted-cli" base "35" 120)
            _ (chk (u/has-bytes? (b "KEXE_CAP {:wire 38 :refused :not-granted}") (.-stderr missing-cli)) "ungranted cli")
            outside (pathlib/Path out "outside")
            _ (.mkdir outside)
            refused (execute "outside-scope" outside "35,38")
            _ (chk (and (re/search (b ":result 91\\b") (.-stdout refused)) (zero? (python/len (python/list (.iterdir outside))))) "outside scope")
            _ (os/symlink outside (pathlib/Path base "escape") ** :target_is_directory true)
            refused (execute "symlink-escape" (pathlib/Path base "escape") "35,38")]
        (chk (and (re/search (b ":result 91\\b") (.-stdout refused)) (zero? (python/len (python/list (.iterdir outside))))) "symlink escape"))
      (doseq [[label old new diagnostic] [["missing-declaration" "(:capabilities [:fs/app-data])" "" "E2176"]
                                          ["empty-declaration" "(:capabilities [:fs/app-data])" "(:capabilities [])" "E2176"]
                                          ["mismatched-declaration" "(:capabilities [:fs/app-data])" "(:capabilities [:cli/args])" "E2176"]
                                          ["unsupported-wire" ":fs/app-data" ":io/write" "E7101"]]]
        (let [files (python/dict original)]
          (operator/setitem files "io.kotoba" (.replace (operator/getitem files "io.kotoba") (b old) (b new)))
          (build label files :diagnostic diagnostic))))
    (let [report (pyenv "status" "PASS_NATIVE_PROJECT_EFFECTS_FS35_CLI38"
                        "compilerSHA256" (sha (.read_bytes compiler)) "runnerSHA256" (sha (.read_bytes runner))
                        "sources" (u/pydict-from (for [[name data] (.items original)] [name (sha data)])) "derivation" derivation
                        "observations" observations "publicProductAdopted" false)]
      (.write_text (pathlib/Path out "evidence.json") (u/json-dump report))
      (println (g report "status"))
      (.flush sys/stdout))))

(defn -main [& args]
  (run-main (.resolve (pathlib/Path (or (u/opt args "--compiler") (sys/exit "--compiler is required"))))
            (.resolve (pathlib/Path (or (u/opt args "--runner") (sys/exit "--runner is required"))))
            (.resolve (pathlib/Path (or (u/opt args "--output") (sys/exit "--output is required"))))
            (or (u/opt args "--compiler-sha256") (sys/exit "--compiler-sha256 is required"))))

(when (some #(or (= % "check-x86-project-effects-native.cljc") (str/ends-with? % "/check-x86-project-effects-native.cljc")) sys/argv)
  (apply -main *command-line-args*))
