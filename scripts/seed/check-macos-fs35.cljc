;; JUN-593: observe the Mac runtime's legacy wire-35 text requests natively.
;;
;; The packager under test is rebuilt from the current source by the Mac root and the descriptor's packager (a
;; staged packager, as a packager change requires). It packages seed/tests/macos-fs35.kotoba; every case runs in
;; its own process with FD 3 = a fresh scope. This script stages files, launches processes, and plants a symlink
;; that points out of the scope; the verdicts come from the native program's exit code or, for the refusals that
;; must not answer, its trap signal. Ported from check-macos-fs35.py (Basilisp, JUN-974). Apple Silicon macOS only.
;; Run: basilisp run -p scripts/seed scripts/seed/check-macos-fs35.cljc -- --output DIR
(ns check-macos-fs35
  (:require [basilisp.string :as str]
            [gate-util :as u]
            [macos-cli-build :as cli-builder]
            [macos-image :as macos]
            [macos-native-lib :as mac])
  (:import json operator os pathlib re shutil signal subprocess sys time))

(def packager-source (.joinpath u/root "seed/macos-fs2-runtime-packager.kotoba"))
(def test-source (.joinpath u/root "seed/tests/macos-fs35.kotoba"))
(def cases ["roundtrip" "durable" "lock" "paths"])
(def traps ["trap-read-missing" "trap-read-link" "trap-write-dotdot" "trap-unknown" "trap-trailing"])

(defn scope [base name]
  (let [s (.joinpath base name)
        _ (.mkdir s ** :mode 0700)
        _ (.mkdir (.joinpath s "d") ** :mode 0700)
        outside (.joinpath base (str name "-outside"))]
    (.mkdir outside ** :mode 0700)
    (.write_text (.joinpath outside "file") "outside")
    (os/symlink outside (.joinpath s "link"))
    [s outside]))

(defn launch [image s args]
  (let [fd (os/open s (bit-or os/O_RDONLY os/O_DIRECTORY))]
    (try
      (subprocess/Popen (python/list (map str (cons image args))) ** :cwd s
                        :env (python/dict {"PATH" "/usr/bin:/bin" "LANG" "C"})
                        :stdout subprocess/PIPE :stderr subprocess/PIPE :pass_fds (python/tuple [3])
                        :preexec_fn (fn [] (os/dup2 fd 3)))
      (finally (os/close fd)))))

(defn run-cli [argv cwd timeout]
  (subprocess/run (python/list (map str argv)) ** :cwd cwd :capture_output true :timeout timeout))

(defn lock-text [entry module-name]
  (str "KSL2\nentry " entry "\nmodule " module-name " " entry "\nfile " (u/geti (u/pin entry) "sha256") " " entry "\n"))

(defn main [out]
  (u/chk (macos/available?) "Apple Silicon host required")
  (.mkdir out ** :parents false :mode 0700 :exist_ok false)
  (let [[compiler bootstrap] (macos/root-images)
        build (.joinpath out "build")
        _ (.mkdir build ** :mode 0700)
        _ (shutil/copyfile packager-source (.joinpath build "packager.kotoba"))
        [packager _] (macos/build compiler bootstrap build "packager.kotoba" "packager")
        _ (shutil/copyfile test-source (.joinpath build "fs35.kotoba"))
        [image unsigned] (macos/build compiler packager build "fs35.kotoba" "fs35")
        ;; Package the identical native entry in the explicit app-data-granted amu-program-fs35 profile and in
        ;; default amu-program (no wire-35 grant). The bundle fixture tests helper placement/dispatch, not locked replay.
        _ (.write_bytes (.joinpath build "source.bundle") (operator/add (u/bytes-of 0 70 83 50 0) (.encode "fs35-runtime-gate")))
        _ (.write_text (.joinpath build "fs35-program.kotoba")
                       (.replace (.read_text (.joinpath build "fs35.kotoba"))
                                 "(typed-cap-call :cli/args :string :string \"0\")"
                                 "(typed-cap-call :cli/args :string :string \"1\")"))
        _ (mac/native-run compiler build ["compile" "fs35-program.kotoba" "--target" "aarch64-macos" "--output" "fs35-program.kseed"])
        extracted (mac/native-run compiler build ["extract-native" "fs35-program.kseed" "--symbol" "main" "--output" "fs35-program.raw"])
        m (re/search (.encode ":offset (\\d+), :length (\\d+), :arity 0}") (.-stdout extracted))
        _ (u/chk (and m (= (python/int (.group m 2)) (.-st_size (.stat (.joinpath build "fs35-program.raw"))))) (.-stdout extracted))
        entry-arg (.decode (.group m 1))
        package (fn [pk stem profile]
                  (mac/native-run pk build [(str stem "-unsigned.macho") "fs35-program.raw" profile entry-arg "source.bundle"])
                  (let [img (.joinpath build (str stem ".macho"))]
                    (mac/sign (.joinpath build (str stem "-unsigned.macho")) img)
                    (mac/verify-macho img)
                    img))
        program-image (package packager "fs35-program" "amu-program-fs35")
        program-ungranted (package packager "fs35-program-ungranted" "amu-program")
        ;; Negative control: disabling the helper branch leaves the request to the FS2 chain even when the explicit
        ;; profile is selected.
        source (.read_text packager-source)
        hook (str "        fs35 (or (string=? mode \"fs2-cli-stdio-general\") (string=? mode \"fs2-cli-stdio-cwd\")\n"
                  "                 (string=? mode \"fs2-cli-stdio-read\") (amu-program-fs35? mode))\n")
        _ (u/chk (= 1 (.count source hook)) "FS35 hook drifted")
        _ (.write_text (.joinpath build "packager-control.kotoba") (.replace source hook "        fs35 false\n"))
        [packager-control _] (macos/build compiler bootstrap build "packager-control.kotoba" "packager-control")
        [control _] (macos/build compiler packager-control build "fs35.kotoba" "fs35-control")
        program-control (package packager-control "fs35-program-control" "amu-program-fs35")
        report (u/pydict "schema" "amu.macos-fs35.v1" "host" (python/list ["Darwin" (.-machine (os/uname))])
                         "compiler" (u/pin compiler) "bootstrapPackager" (u/pin bootstrap)
                         "packagerSource" (u/pin packager-source) "testSource" (u/pin test-source)
                         "stagedPackager" (u/pin packager) "image" (u/pin unsigned)
                         "amuProgramFs35Image" (u/pin (.joinpath build "fs35-program-unsigned.macho"))
                         "amuProgramUngrantImage" (u/pin (.joinpath build "fs35-program-ungranted-unsigned.macho"))
                         "calls" (python/list))
        save (fn [] (.write_text (.joinpath out "observations.json") (u/json-dump report)))
        observe (fn [name img args scope-name & {:keys [expect trap expected-stdout]}]
                  (let [[s outside] (scope out scope-name)
                        _ (when (and (seq args) (= "paths" (first args)))
                            (.write_text (.joinpath s "d" "a") "a"))
                        p (launch img s args)
                        [stdout stderr] (vec (.communicate p ** :timeout 120))]
                    (.append (u/geti report "calls")
                             (u/pydict "name" name "exit" (.-returncode p) "stderrSHA256" (u/sha256-hex stderr)))
                    (save)
                    (if trap
                      (u/chk (= (- (python/int signal/SIGTRAP)) (.-returncode p)) (str name " " (.-returncode p)))
                      (u/chk (= expect (.-returncode p)) (str name " " (.-returncode p))))
                    (when-not (nil? expected-stdout)
                      (u/chk (u/deq stdout expected-stdout) (str name " unexpected program result")))
                    (u/chk (= "outside" (.read_text (.joinpath outside "file"))) (str name " outside file changed"))
                    (u/chk (= ["file"] (vec (sort (map #(.-name %) (python/list (.iterdir outside)))))) (str name " write escaped the scope"))
                    (println name (.-returncode p))
                    (.flush sys/stdout)
                    s))]
    (doseq [c cases] (observe c image [c] c :expect 0))
    (doseq [c cases]
      (observe (str "amu-program-" c) program-image ["amu-program" c] (str "amu-program-" c) :expect 0 :expected-stdout (.encode "0\n")))
    (let [ungranted-scope (observe "amu-program-no-wire35-grant" program-ungranted ["amu-program" "roundtrip"] "amu-program-ungranted" :trap true)]
      (u/chk (not (.exists (.joinpath ungranted-scope "d" "a"))) "default amu-program performed an ungranted write"))
    (doseq [c traps] (observe c image [c] c :trap true))
    (doseq [c traps] (observe (str "amu-program-" c) program-image ["amu-program" c] (str "amu-program-" c) :trap true))
    ;; Exclusive lock across processes: a holder keeps it, a second process is refused, death releases it.
    (let [[s _] (scope out "hold")
          holder (launch image s ["hold"])
          deadline (+ (time/monotonic) 30)]
      (loop []
        (when-not (.exists (.joinpath s "d" "ready"))
          (u/chk (and (nil? (.poll holder)) (< (time/monotonic) deadline)) "holder did not take the lock")
          (time/sleep 0.01)
          (recur)))
      (let [contender (launch image s ["contended"])]
        (u/chk (zero? (.wait contender ** :timeout 60)) "a second process took a held lock"))
      (.kill holder)
      (.wait holder ** :timeout 10)
      (let [retry (launch image s ["roundtrip"])]
        (u/chk (zero? (.wait retry ** :timeout 60))))
      (let [after (launch image s ["contended"])]
        (u/chk (= 1 (.wait after ** :timeout 60)) "the lock was not released by process death"))
      (.append (u/geti report "calls") (u/pydict "name" "cross-process-lock" "exit" 0)))
    ;; Negative control: without FS35 the legacy request traps instead of answering.
    (observe "control-without-fs35" control ["roundtrip"] "control" :trap true)
    (observe "amu-program-fs35-profile-without-helper" program-control ["amu-program" "roundtrip"] "amu-program-control" :trap true)
    ;; Exercise the public Amu CLI path that Itonami's locked project builder will use. The explicit profile must
    ;; package the scoped wire-35 helper; the default profile must keep refusing the same request.
    (let [cli-dir (.joinpath out "public-cli")
          _ (cli-builder/build cli-dir)
          _ (.write_bytes (.joinpath cli-dir "amu-full-root.macho") (.read_bytes compiler))
          _ (.write_bytes (.joinpath cli-dir "kotoba-packager-root.macho") (.read_bytes bootstrap))
          _ (.chmod (.joinpath cli-dir "amu-full-root.macho") 0755)
          _ (.chmod (.joinpath cli-dir "kotoba-packager-root.macho") 0755)
          project (.joinpath out "locked-fs35-project")
          _ (.mkdir project ** :mode 0700)
          entry (.joinpath project "fs35-program.kotoba")
          _ (.write_text entry (.read_text (.joinpath build "fs35-program.kotoba")))
          lock (.joinpath project "project.ksl")
          _ (.write_text lock (lock-text entry "seed.tests.macos-fs35"))
          public-explicit (.joinpath project "explicit.macho")
          public-default (.joinpath project "default.macho")
          cli (.joinpath cli-dir "amu-cli.macho")
          explicit-build (run-cli [cli "compile" entry "--source-lock" lock "--runtime-profile" "amu-program-fs35" "-o" public-explicit] project 180)
          _ (u/chk (zero? (.-returncode explicit-build)) (.-stderr explicit-build))
          default-build (run-cli [cli "compile" entry "--source-lock" lock "-o" public-default] project 180)
          _ (u/chk (zero? (.-returncode default-build)) (.-stderr default-build))
          refused-build (run-cli [cli "compile" entry "--source-lock" lock "--runtime-profile" "unknown-profile" "-o" (.joinpath project "refused.macho")] project 30)
          _ (u/chk (and (= 2 (.-returncode refused-build)) (u/has-bytes? (.encode "usage:") (.-stderr refused-build))))
          _ (mac/verify-macho public-explicit)
          _ (mac/verify-macho public-default)
          _ (observe "public-cli-fs35-profile-roundtrip" public-explicit ["amu-program" "roundtrip"] "public-cli-fs35"
                     :expect 0 :expected-stdout (.encode "0\n"))
          ;; The command profile keeps native CLI semantics: application stdout is preserved and main's signed result
          ;; is the process status. This matters for Itonami's launcher, which consumes ordinary command exit codes.
          command-project (.joinpath out "locked-fs35-command-project")
          _ (.mkdir command-project ** :mode 0700)
          command-entry (.joinpath command-project "fs35-command.kotoba")
          command-source (-> (.read_text (.joinpath build "fs35-program.kotoba"))
                             (.replace "(:capabilities [:fs/app-data :cli/args])" "(:capabilities [:fs/app-data :cli/args :io/write])")
                             (.replace ":else 99)))" ":else 99)\n    (let [written (typed-cap-call :io/write :string :string \"artifact-output\\n\")] 7)))"))
          _ (.write_text command-entry command-source)
          command-lock (.joinpath command-project "project.ksl")
          _ (.write_text command-lock (lock-text command-entry "seed.tests.macos-fs35"))
          command-image (.joinpath command-project "command.macho")
          command-build (run-cli [cli "compile" command-entry "--source-lock" command-lock "--runtime-profile" "amu-command-fs35" "-o" command-image] command-project 180)
          _ (u/chk (zero? (.-returncode command-build)) (.-stderr command-build))
          _ (mac/verify-macho command-image)
          _ (observe "public-cli-command-fs35-positive" command-image ["amu-program" "roundtrip"] "public-cli-command-positive"
                     :expect 7 :expected-stdout (.encode "artifact-output\n"))
          command-refusal (observe "public-cli-command-fs35-refusal" command-image ["amu-program" "trap-read-missing"]
                                   "public-cli-command-refusal" :trap true :expected-stdout (u/bytes-of))
          ;; A command profile without FS35 is available for Kotoba programs whose declared capabilities are limited
          ;; to CLI arguments and stdio.
          plain-project (.joinpath out "locked-command-project")
          _ (.mkdir plain-project ** :mode 0700)
          plain-entry (.joinpath plain-project "command.kotoba")
          _ (.write_text plain-entry (str "(ns command-gate (:export [main]) (:capabilities [:cli/args :io/write]))\n"
                                          "(defn main [] :i64 (let [written (typed-cap-call :io/write :string :string \"command-output\\n\")] 7))\n"))
          plain-lock (.joinpath plain-project "project.ksl")
          _ (.write_text plain-lock (lock-text plain-entry "command-gate"))
          plain-image (.joinpath plain-project "command.macho")
          plain-build (run-cli [cli "compile" plain-entry "--source-lock" plain-lock "--runtime-profile" "amu-command" "-o" plain-image] plain-project 180)
          _ (u/chk (zero? (.-returncode plain-build)) (.-stderr plain-build))
          _ (mac/verify-macho plain-image)
          _ (observe "public-cli-command-no-fs35" plain-image [] "public-cli-command-no-fs35" :expect 7 :expected-stdout (.encode "command-output\n"))
          default-scope (observe "public-cli-default-no-wire35" public-default ["amu-program" "roundtrip"] "public-cli-default" :trap true)]
      (u/chk (not (.exists (.joinpath default-scope "d" "a"))) "default public CLI profile performed an ungranted write")
      (doseq [[k v] [["publicCli" (u/pin cli)] ["publicCliSourceLock" (u/pin lock)]
                     ["publicCliFs35Artifact" (u/pin public-explicit)] ["publicCliDefaultArtifact" (u/pin public-default)]
                     ["publicCliCommandFs35Artifact" (u/pin command-image)] ["publicCliCommandFs35SourceLock" (u/pin command-lock)]
                     ["publicCliCommandRefusal" (.-name command-refusal)] ["publicCliCommandNoFs35Artifact" (u/pin plain-image)]
                     ["unknownRuntimeProfileRefused" (= 2 (.-returncode refused-build))]]]
        (operator/setitem report k v)))
    (operator/setitem report "status" "PASS_MACOS_FS35")
    (save)
    (println (u/geti report "status"))
    (.flush sys/stdout)))

(defn -main [& args]
  (main (.resolve (pathlib/Path (or (u/opt args "--output") (sys/exit "--output is required"))))))

(when (some #(or (= % "check-macos-fs35.cljc") (str/ends-with? % "/check-macos-fs35.cljc")) sys/argv)
  (apply -main *command-line-args*))
