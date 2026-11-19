;; Observe native regular-file source-lock acceptance/refusal; no compiler fallback. Ported from
;; source_lock_checks.py (Basilisp, JUN-974). Linux filesystem fixtures (FIFO, unix socket, symlink, oversized,
;; empty and binary locks) are created in a temporary directory; a macOS shared mount can reject mknod.
(ns source-lock-checks
  (:require [gate-util :as u])
  (:import json operator os pathlib socket subprocess tempfile))

(defn g [m k] (operator/getitem m k))
(defn sha-of [p] (u/sha256-hex (.read_bytes (pathlib/Path p))))

(defn- check* [compilers observations out]
  (let [src (pathlib/Path out "good.kotoba")
        _ (.write_text src "(ns lock-boundary (:export [main]))\n(defn main [] :i64 42)\n")
        text (str "KSL1\nentry " src "\nfile " (sha-of src) " " src "\n")
        positives (vec (for [name ["valid.ksl" "lock-WRITE_SEP-APPEND_SEP-EXISTS_SEP.ksl" "lock-言葉-é.ksl"]]
                         (let [p (pathlib/Path out name)] (.write_text p text) p)))
        directory (pathlib/Path out "directory.ksl")
        _ (.mkdir directory)
        fifo (pathlib/Path out "fifo.ksl")
        _ (os/mkfifo fifo)
        endpoint (pathlib/Path out "socket.ksl")
        sock (socket/socket socket/AF_UNIX socket/SOCK_STREAM)
        original-cwd (pathlib/Path (os/getcwd))
        _ (try (os/chdir out) (.bind sock (.-name endpoint)) (finally (os/chdir original-cwd)))
        link (pathlib/Path out "symlink.ksl")
        _ (.symlink_to link (.-name (first positives)))
        oversized (pathlib/Path out "oversized.ksl")
        _ (.write_bytes oversized (.encode (operator/mul "x" 1048577)))
        empty (pathlib/Path out "empty.ksl")
        _ (.write_bytes empty (u/bytes-of))
        binary (pathlib/Path out "binary.ksl")
        _ (.write_bytes binary (u/bytes-of 0x4b 0x53 0x4c 0x31 10 0xff 10))
        failures [directory fifo endpoint link oversized empty binary (pathlib/Path out "missing.ksl")]
        env (u/pydict "PATH" "/nonexistent" "KEXE_ALLOW" "35,37,38,39" "KEXE_CAP_RESOURCES_35" (str out) "KEXE_STACK_BYTES" "8388608")
        rows (python/list [])
        call (fn [name argv expected]
               (let [p (subprocess/run (python/list (map str argv)) ** :cwd out :env env :capture_output true :timeout 20)]
                 (.write_bytes (pathlib/Path observations (str name ".stdout")) (.-stdout p))
                 (.write_bytes (pathlib/Path observations (str name ".stderr")) (.-stderr p))
                 (u/chk (= (.-returncode p) expected) (str [name (.-returncode p) (.-stderr p)]))
                 (if (not (zero? expected))
                   (u/chk (and (u/has-bytes? (.encode "E6015") (.-stderr p)) (not (u/has-bytes? (.encode "KEXE_TRAP") (.-stderr p)))) (str [name (.-stderr p)]))
                   (u/chk (zero? (python/len (.-stderr p))) (str [name (.-stderr p)])))
                 (.append rows (u/pydict "name" name "exit" (.-returncode p)
                                         "stdoutSHA256" (u/sha256-hex (.-stdout p)) "stderrSHA256" (u/sha256-hex (.-stderr p))))))]
    (try
      (doseq [[i compiler] (map-indexed vector compilers)]
        (let [containers (atom [])]
          (doseq [[j lock] (map-indexed vector positives)]
            (call (str "alias-" i "-valid-" j) [compiler "check" src "--source-lock" lock "--source-lock-sha256" (sha-of lock)] 0)
            (let [output (pathlib/Path out (str "valid-" i "-" j ".kseed"))]
              (call (str "alias-" i "-compile-valid-" j) [compiler "compile" src "--target" "aarch64-macos" "--source-lock" lock "--source-lock-sha256" (sha-of lock) "--output" output] 0)
              (swap! containers conj (sha-of output))))
          (u/chk (= (count (set @containers)) 1) "lock path changed compiled program bytes")
          (doseq [[j lock] (map-indexed vector failures)]
            (call (str "alias-" i "-refuse-" j) [compiler "check" src "--source-lock" lock] 1)
            (let [output (pathlib/Path out (str "refused-" i "-" j ".kseed"))]
              (call (str "alias-" i "-compile-refuse-" j) [compiler "compile" src "--target" "aarch64-macos" "--source-lock" lock "--output" output] 1)
              (u/chk (not (.exists output)) (str output))
              (call (str "alias-" i "-project-refuse-" j) [compiler "check" src "--source-path" out "--source-lock" lock] 1)))))
      (u/chk (not (.exists (pathlib/Path out "lock-"))) "legacy token scan wrote a path prefix")
      (finally (.close sock)))
    (let [result (u/pydict "status" "PASS_NATIVE_SOURCE_LOCK_FILE_BOUNDARY" "aliases" (count compilers)
                           "positivePaths" (count positives) "invalidPathKinds" (count failures)
                           "namedRefusal" "E6015" "cases" rows "noRefusalOutput" true
                           "singleAndProjectRoutes" true "unicodeAndSeparatorPaths" true
                           "positiveCompilePathIdentity" true
                           "observerSourceSHA256" (sha-of (pathlib/Path u/root "scripts/seed/source_lock_checks.cljc"))
                           "compilerLegacyFallback" false)]
      (.write_text (pathlib/Path observations "source-lock-boundary.json") (u/json-dump result))
      result)))

(defn check-source-locks [compilers out]
  (let [out (pathlib/Path out)]
    (.mkdir out ** :mode 0700)
    (let [d (tempfile/TemporaryDirectory ** :prefix "amu-lock-")
          fixtures (pathlib/Path (.__enter__ d))]
      (try (check* compilers out fixtures) (finally (.__exit__ d nil nil nil))))))
