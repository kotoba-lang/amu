;; Build/observe the native Darwin CLI service; this script only stages bytes.
;; Every compiler, emitter, filesystem/process operation and probe runs as an Amu-built Mach-O. No C compiler,
;; assembler, Linux process or hosted launcher. Ported from check-macos-cli-host-native.py (Basilisp, JUN-974). Apple
;; Silicon macOS only. The escape-heavy Kotoba sources below are extracted from the Python original's AST so the
;; \u0000 / \n escapes stay byte-exact.
;; Run: basilisp run -p scripts/seed scripts/seed/check-macos-cli-host-native.cljc -- --output DIR
(ns check-macos-cli-host-native
  (:require [basilisp.string :as str]
            [gate-util :as u]
            [macos-native-lib :as mac])
  (:import json operator os pathlib platform re resource signal subprocess sys))

(def string-fs2-lock-src "(ns string-fs2-lock (:export [main]))\n(defn main [] :i64\n  (let [d (typed-cap-call 35 :string :string \"\\u0000FS2\\u0000D/regular\\u0000\")]\n    (if (= d \"\\u0000FS2\\u00001\")\n      (let [x (typed-cap-call 37 :string :string \"PASS_STRING_FS2\\n\")] 0) 1)))\n")
(def legacy-lock-src "(ns legacy-lock (:export [main]))\n(defn- fs [r :string] :string (typed-cap-call 35 :string :string r))\n(defn main [] :i64\n  (cond (not (= (fs \"/lockedFLOCK_SEP\") \"1\")) 1\n        (not (= (fs \"/lockedFLOCK_SEP\") \"0\")) 2\n        (not (= (fs \"/otherFLOCK_SEP\") \"0\")) 3\n        (not (= (fs \"/otherUNLOCK_SEP\") \"0\")) 4\n        (not (= (fs \"/linkFLOCK_SEP\") \"0\")) 5\n        (not (= (fs \"/../escapeFLOCK_SEP\") \"0\")) 6\n        (not (= (fs \"/lockedUNLOCK_SEP\") \"1\")) 7\n        (not (= (fs \"/lockedUNLOCK_SEP\") \"0\")) 8\n        (not (= (fs \"/lockedFLOCK_SEP\") \"1\")) 9\n        :else (let [x (typed-cap-call 37 :string :string \"PASS_STRING_FS35_LOCK\\n\")] 0)))\n")
(def legacy-lock-noscope-src "(ns legacy-lock-noscope (:export [main]))\n(defn main [] :i64\n  (if (= (typed-cap-call 35 :string :string \"/lockedFLOCK_SEP\") \"0\")\n    (let [x (typed-cap-call 37 :string :string \"PASS_STRING_FS35_NOSCOPE\\n\")] 0) 1))\n")
(def bad-abi-src "(ns bad (:export [main]))\n(defn main [] :i64 (let [s (typed-cap-call :fs/app-data :string :string \"anything\")] 0))\n")

(defn- b [s] (.encode s))
(defn- inf [path] (b (str path "\n")))

(defn main [out]
  (u/chk (and (= "Darwin" (platform/system)) (= "arm64" (platform/machine))))
  (let [root u/root
        d (u/read-json mac/root-descriptor)
        compiler (.joinpath root (u/geti (u/geti d "compiler") "path"))
        bootstrap (.joinpath root (u/geti (u/geti d "packager") "path"))
        _ (doseq [[key image] [["compiler" compiler] ["packager" bootstrap]]]
            (u/chk (u/deq (mac/verify-macho image) (u/pydict "bytes" (u/geti (u/geti d key) "bytes") "sha256" (u/geti (u/geti d key) "sha256")))))
        _ (.mkdir out ** :parents true :mode 0700 :exist_ok false)
        sources (u/pydict)
        build (fn [paths stem pk mode]
                (let [data (.join (u/bytes-of) (python/list (for [p paths] (operator/add (.read_bytes (.joinpath root p)) (b "\n")))))]
                  (.write_bytes (.joinpath out (str stem ".kotoba")) data)
                  (operator/setitem sources stem (u/pydict-from (for [p paths] [p (mac/pin (.joinpath root p))])))
                  (mac/native-run compiler out ["compile" (str stem ".kotoba") "--target" "aarch64-macos" "--output" (str stem ".kseed")])
                  (let [r (mac/native-run compiler out ["extract-native" (str stem ".kseed") "--symbol" "main" "--output" (str stem ".raw")])
                        m (re/search (b ":offset (\\d+), :length (\\d+), :arity 0}") (.-stdout r))]
                    (u/chk (and m (= (python/int (.group m 2)) (.-st_size (.stat (.joinpath out (str stem ".raw")))))))
                    (mac/native-run pk out [(str stem "-unsigned.macho") (str stem ".raw") mode (.decode (.group m 1))])
                    (let [image (.joinpath out (str stem ".macho"))]
                      (mac/sign (.joinpath out (str stem "-unsigned.macho")) image)
                      (mac/verify-macho image)
                      image))))
        packager (build ["seed/macos-fs2-runtime-packager.kotoba"] "packager" bootstrap "fs2-cli-stdio-general")
        images (u/pydict)
        _ (doseq [case ["info" "files" "spawn" "refusals" "fds" "timeout" "loop" "write-failure"]]
            (operator/setitem images case (build [(str "seed/tests/macos-cli-host-" case ".kotoba") "seed/macos-cli-api.kotoba"] case packager "amu-cli-host")))
        img (fn [k] (operator/getitem images k))
        calls (python/list)
        secret (atom nil)
        run (fn run [case args & {:keys [expected inherited alarm file-limit exit-code diagnostic scope-fd cwd] :or {exit-code 0}}]
              ;; Intentionally no inherited directory FD, external environment or PATH.
              (let [setup (fn []
                            (when (some? scope-fd) (os/dup2 scope-fd 3 ** :inheritable true))
                            (when inherited (os/dup2 @secret 3) (os/dup2 @secret 91))
                            (when alarm
                              (signal/signal signal/SIGALRM signal/SIG_IGN)
                              (signal/pthread_sigmask signal/SIG_BLOCK (python/set [signal/SIGALRM])))
                            (when (some? file-limit)
                              (signal/signal signal/SIGXFSZ signal/SIG_IGN)
                              (resource/setrlimit resource/RLIMIT_FSIZE (python/tuple [file-limit file-limit]))))
                    need-setup (or inherited alarm (some? file-limit) (some? scope-fd))
                    r (subprocess/run (python/list (map str (cons (img case) args))) ** :cwd (if (nil? cwd) out cwd)
                                      :env (python/dict {"PATH" "/nonexistent" "LANG" "C"}) :capture_output true :timeout 20
                                      :close_fds (not (or inherited (some? scope-fd)))
                                      :preexec_fn (when need-setup setup))
                    name (str (python/format (python/len calls) "02d") "-" case)]
                (.write_bytes (.joinpath out (str name ".stdout")) (.-stdout r))
                (.write_bytes (.joinpath out (str name ".stderr")) (.-stderr r))
                (u/chk (= exit-code (.-returncode r)) (str [name (.-returncode r) (.-stdout r) (.-stderr r)]))
                (if (nil? diagnostic)
                  (u/chk (not (u/nonempty? (.-stderr r))) (str [name (.-stderr r)]))
                  (u/chk (u/has-bytes? diagnostic (.-stderr r)) (str [name (.-stderr r)])))
                (when (some? expected) (u/chk (u/deq (.-stdout r) expected)))
                (.append calls (u/pydict "name" name "exit" (.-returncode r) "stdout" (mac/pin (.joinpath out (str name ".stdout")))))))
        p (fn [n] (.joinpath out n))
        original (.read_text (.joinpath root "seed/macos-fs2-runtime-packager.kotoba"))
        info-line (inf (img "info"))]
    (run "info" [] :expected info-line)
    (run "files" [(p "native paths 日本語")] :expected (b "PASS_NATIVE_HOST_FILES\n"))
    (run "spawn" [out (img "info")] :expected (b "PASS_NATIVE_HOST_SPAWN\n"))
    (u/chk (u/deq (.read_bytes (p "child.stdout")) info-line))
    (.unlink (p "child.stdout"))
    (reset! secret (os/open (p "info.kotoba") os/O_RDONLY))
    (try (os/set_inheritable @secret true)
         (run "spawn" [out (img "fds")] :expected (b "PASS_NATIVE_HOST_SPAWN\n") :inherited true)
         (finally (os/close @secret)))
    (u/chk (u/deq (.read_bytes (p "child.stdout")) (b "PASS_NATIVE_CHILD_FDS_CLOSED\n")))
    (run "timeout" [out (img "loop")] :expected (b "PASS_NATIVE_CHILD_DEADLINE\n") :alarm true)
    (let [regular (p "regular")
          link (p "symlink")
          fifo (p "fifo")
          oversized (p "oversized")]
      (.write_bytes regular (b "private"))
      (.symlink_to link regular)
      (os/mkfifo fifo 0600)
      (let [f (.open oversized "wb")] (try (.truncate f 8388608) (finally (.close f))))
      (doseq [path [(p "missing") link fifo out oversized]] (run "refusals" [path]))
      (u/chk (u/deq (.read_bytes regular) (b "private")))
      (u/chk (not (.exists (p "native paths 日本語"))))
      (let [partial (p "partial-write-must-not-remain")
            chmod "(mh-imm 1 384) (mh-sys 124) (mh-b 0x54000002 45)"]
        (run "write-failure" [partial "write"] :file-limit 4 :expected (b "PASS_NATIVE_WRITE_FAILURE_CLEANUP\n"))
        (u/chk (not (.exists partial)))
        (u/chk (= 1 (.count original chmod)))
        (.write_text (p "failed-fchmod.kotoba") (.replace original chmod "(mh-imm 1 384) (mh-i 0x92800000) (mh-sys 124) (mh-b 0x54000002 45)"))
        (let [failed (build [(str (p "failed-fchmod.kotoba"))] "failed-fchmod-packager" bootstrap "fs2-cli-stdio-general")]
          (operator/setitem images "failed-fchmod"
                            (build ["seed/tests/macos-cli-host-write-failure.kotoba" "seed/macos-cli-api.kotoba"] "failed-fchmod" failed "amu-cli-host")))
        (run "failed-fchmod" [(p "failed-fchmod-must-not-remain") "fchmod"] :expected (b "PASS_NATIVE_WRITE_FAILURE_CLEANUP\n"))
        (u/chk (not (.exists (p "failed-fchmod-must-not-remain"))))
        (let [cleanup "(mh-label 47) (mh-ldr 0 23 272) (mh-sys 10)"]
          (u/chk (= 1 (.count original cleanup)))
          (.write_text (p "removed-write-cleanup.kotoba") (.replace original cleanup "(mh-label 47) (mh-ldr 0 23 272) (mh-i 0xd503201f)"))
          (let [removed (build [(str (p "removed-write-cleanup.kotoba"))] "removed-write-cleanup-packager" bootstrap "fs2-cli-stdio-general")]
            (operator/setitem images "removed-write-cleanup"
                              (build ["seed/tests/macos-cli-host-write-failure.kotoba" "seed/macos-cli-api.kotoba"] "removed-write-cleanup" removed "amu-cli-host")))
          (run "removed-write-cleanup" [partial "write"] :file-limit 4 :exit-code 3)
          (u/chk (u/deq (.read_bytes partial) (u/bytes-of 0 255 128 42)))
          (.unlink partial))))
    (let [no-grant (.replace original "0xf9400a68 0xd2a00209" "0xf9400a68 0xd2800009")]
      (u/chk (not= no-grant original))
      (.write_text (p "no-grant.kotoba") no-grant)
      (let [no-grant-packager (build [(str (p "no-grant.kotoba"))] "no-grant-packager" bootstrap "fs2-cli-stdio-general")]
        (operator/setitem images "denied" (build ["seed/tests/macos-cli-host-denied.kotoba" "seed/macos-cli-api.kotoba"] "denied" no-grant-packager "amu-cli-host")))
      (run "denied" [out (img "info")] :expected (b "PASS_NATIVE_PROCESS_GRANT_DENIED\n"))
      (u/chk (not (.exists (p "must-not-exist"))))
      (let [guard "(mh-b (bit-or 0xb4000000 8) 91)"]
        (u/chk (= 1 (.count no-grant guard)))
        (.write_text (p "removed-guard.kotoba") (.replace no-grant guard "(mh-i 0xd503201f)"))
        (let [removed (build [(str (p "removed-guard.kotoba"))] "removed-guard-packager" bootstrap "fs2-cli-stdio-general")]
          (operator/setitem images "removed-guard" (build ["seed/tests/macos-cli-host-denied.kotoba" "seed/macos-cli-api.kotoba"] "removed-guard" removed "amu-cli-host")))
        (run "removed-guard" [out (img "info")] :exit-code 1)
        (u/chk (u/deq (.read_bytes (p "must-not-exist")) info-line))))
    (let [close "(mh-mov 0 8) (mh-sys 6)"]
      (u/chk (= 1 (.count original close)))
      (.write_text (p "removed-fd-close.kotoba") (.replace original close "(mh-i 0xd503201f)"))
      (let [removed (build [(str (p "removed-fd-close.kotoba"))] "removed-fd-close-packager" bootstrap "fs2-cli-stdio-general")]
        (operator/setitem images "removed-fd-close" (build ["seed/tests/macos-cli-host-spawn.kotoba" "seed/macos-cli-api.kotoba"] "removed-fd-close" removed "amu-cli-host")))
      (.unlink (p "child.stdout"))
      (reset! secret (os/open (p "regular") os/O_RDONLY))
      (try (os/set_inheritable @secret true)
           (run "removed-fd-close" [out (img "fds")] :exit-code 1 :inherited true)
           (finally (os/close @secret)))
      (u/chk (u/deq (.read_bytes (p "child.stdout")) (u/bytes-of))))
    (.write_text (p "bad-abi.kotoba") bad-abi-src)
    (operator/setitem images "bad-abi" (build [(str (p "bad-abi.kotoba"))] "bad-abi" packager "amu-cli-host"))
    (run "bad-abi" [] :exit-code 70 :diagnostic (b "EHOST invalid host ABI"))
    ;; String wire 35 in the macOS host profiles serves the scoped FS2 grammar and, through the FS35 helper, the legacy
    ;; "/path" grammar beneath FD3 (FLOCK_SEP / UNLOCK_SEP: one nonblocking exclusive flock per process, openat
    ;; O_RESOLVE_BENEATH|O_NOFOLLOW_ANY). Wire-35 strings that are neither FS2-framed nor "/"-rooted remain a host ABI
    ;; error. These diagnostics supply FD3 explicitly (amu-cli-host) or use the cwd profile's own FD3; neither is
    ;; automatic host setup.
    (.write_text (p "string-fs2-lock.kotoba") string-fs2-lock-src)
    (.write_text (p "legacy-lock.kotoba") legacy-lock-src)
    (.write_text (p "legacy-lock-noscope.kotoba") legacy-lock-noscope-src)
    (doseq [[k src pk mode] [["legacy-lock" "legacy-lock.kotoba" packager "amu-cli-host"]
                             ["legacy-lock-cwd" "legacy-lock.kotoba" packager "amu-cli-host-cwd"]
                             ["legacy-lock-noscope" "legacy-lock-noscope.kotoba" packager "amu-cli-host"]
                             ["string-fs2-lock" "string-fs2-lock.kotoba" packager "amu-cli-host"]
                             ["string-fs2-lock-cwd" "string-fs2-lock.kotoba" packager "amu-cli-host-cwd"]]]
      (operator/setitem images k (build [(str (p src))] k pk mode)))
    (operator/setitem images "spawn-cwd" (build ["seed/tests/macos-cli-host-spawn.kotoba" "seed/macos-cli-api.kotoba"] "spawn-cwd" packager "amu-cli-host-cwd"))
    ;; Negative control: a built-and-executed host packager whose FS35 route is removed (every non-FS2 wire-35 string is
    ;; a host ABI error again) must fail the legacy lock gate.
    (let [route "(mh-lb 8 21 0) (mh-cmpi 8 47) (mh-b 0x54000001 98)"]
      (u/chk (= 1 (.count original route)))
      (.write_text (p "removed-fs35-route.kotoba") (.replace original route "(mh-lb 8 21 0) (mh-cmpi 8 47) (mh-b 0x14000000 98)"))
      (let [removed-route (build [(str (p "removed-fs35-route.kotoba"))] "removed-fs35-route-packager" bootstrap "fs2-cli-stdio-general")]
        (operator/setitem images "removed-fs35-route" (build [(str (p "legacy-lock.kotoba"))] "removed-fs35-route" removed-route "amu-cli-host"))))
    (let [scope-fd (os/open out (bit-or os/O_RDONLY os/O_DIRECTORY))]
      (try
        (os/set_inheritable scope-fd true)
        (run "string-fs2-lock" [] :expected (b "PASS_STRING_FS2\n") :scope-fd scope-fd)
        (run "legacy-lock" [] :expected (b "PASS_STRING_FS35_LOCK\n") :scope-fd scope-fd)
        (run "removed-fs35-route" [] :exit-code 70 :diagnostic (b "EHOST invalid host ABI") :scope-fd scope-fd)
        ;; Without an FD3 scope the legacy lock is refused (no ambient authority).
        (run "legacy-lock-noscope" [] :expected (b "PASS_STRING_FS35_NOSCOPE\n"))
        ;; The opt-in cwd profile must open its own FD3, and must refuse an already occupied FD3 rather than silently
        ;; replacing it.
        (run "string-fs2-lock-cwd" [] :expected (b "PASS_STRING_FS2\n"))
        (run "legacy-lock-cwd" [] :expected (b "PASS_STRING_FS35_LOCK\n"))
        (run "string-fs2-lock-cwd" [] :scope-fd scope-fd :exit-code 70)
        (finally (os/close scope-fd))))
    (.unlink (p "child.stdout"))
    (run "spawn-cwd" [out (img "info")] :expected (b "PASS_NATIVE_HOST_SPAWN\n"))
    (u/chk (u/deq (.read_bytes (p "child.stdout")) info-line))
    (.unlink (p "child.stdout"))
    (run "spawn-cwd" [out (img "fds")] :expected (b "PASS_NATIVE_HOST_SPAWN\n"))
    (u/chk (u/deq (.read_bytes (p "child.stdout")) (b "PASS_NATIVE_CHILD_FDS_CLOSED\n")))
    ;; Scope startup must refuse a cwd that grants group or other access.
    (let [unsafe-cwd (p "unsafe-cwd")]
      (.mkdir unsafe-cwd ** :mode 0700)
      (.chmod unsafe-cwd 0755)
      (run "string-fs2-lock-cwd" [] :cwd unsafe-cwd :exit-code 70))
    (let [report (u/pydict "schema" "amu.macos-cli-host-observation.v1" "status" "PASS_NATIVE_MACOS_CLI_HOST"
                           "compiler" (mac/pin compiler) "bootstrap" (mac/pin bootstrap) "packager" (mac/pin packager)
                           "sources" sources "images" (u/pydict-from (for [[k v] (.items images)] [k (mac/pin v)]))
                           "calls" calls "manualFD3" true "hostAutomaticFD3" false "fs35HostHelper" true "fs2DiagnosticManualFD3" true
                           "cwdHostDiagnostic" true "linuxProcess" false "hostedFallback" false
                           "builtExecutedMutants" (python/list ["removed-process-grant-guard" "removed-child-fd-close"
                                                                "removed-write-failure-cleanup" "removed-fs35-route"])
                           "publicCLIIntegrated" false "independentUserQualified" false)]
      (.write_text (p "host-service.json") (u/json-dump report))
      (println (u/geti report "status") (python/len calls) "native observations")
      (.flush sys/stdout))))

(defn -main [& args]
  (main (.resolve (pathlib/Path (or (u/opt args "--output") (sys/exit "--output is required"))))))

(when (some #(or (= % "check-macos-cli-host-native.cljc") (str/ends-with? % "/check-macos-cli-host-native.cljc")) sys/argv)
  (apply -main *command-line-args*))
