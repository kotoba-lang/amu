;; Build the canonical FS2 fixture and observe native Linux qualification.
;;
;; Amu compiles the source; Kotoba asserts bytes and FS form semantics. Basilisp stages files and observes exits,
;; diagnostics, ownership and cleanup. Fault observers affect only their own children, with no hosted runtime
;; fallback.
;; Ported from check-native-fs2.py (Basilisp). Linux only. The two helper observers (check-fs2-observed.py,
;; check-fs2-errno.py) are still Python and are started with the interpreter that runs this script.
;; Run: basilisp run scripts/seed/check-native-fs2.cljc -- --compiler C --output OUT
(ns check-native-fs2
  (:require [basilisp.string :as str]
            [gate-util :as u])
  (:import json operator os pathlib platform signal socket subprocess sys tempfile time))

(defn- glob-vec [p pattern] (vec (python/list (.glob p pattern))))

(defn main [compiler out]
  (let [machine (platform/machine)
        _ (u/chk (and (= "Linux" (platform/system)) (contains? #{"aarch64" "arm64" "x86_64"} machine)))
        root u/root
        _ (.mkdir out ** :parents true :exist_ok false)
        calls (python/list)
        source (.joinpath root "seed/tests/fs2-product.kotoba")
        source-pin (u/pin source)
        image (.joinpath out "fs2.elf")
        env (python/dict {"PATH" "/nonexistent" "KEXE_ALLOW" "35,37,38,39"
                          "KEXE_CAP_RESOURCES_35" (str/join ":" (map str [root out])) "KEXE_STACK_BYTES" "8388608"})
        observe (fn [name args custom & {:keys [expected diagnostic timeout] :or {expected 0 timeout 180}}]
                  (let [p (u/run-process args custom timeout :cwd out)]
                    (.write_bytes (.joinpath out (str name ".stdout")) (.-stdout p))
                    (.write_bytes (.joinpath out (str name ".stderr")) (.-stderr p))
                    (.append calls (u/pydict "name" name "exit" (.-returncode p)))
                    (.write_text (.joinpath out "calls.json") (u/json-dump calls))
                    (u/chk (= expected (.-returncode p)) [name (.-returncode p) (u/bslice (.-stderr p) -1000 nil)])
                    (if diagnostic
                      (u/chk (and (u/has-bytes? diagnostic (.-stderr p)) (not (u/has-bytes? (.encode "KEXE_CLEANUP") (.-stderr p)))))
                      (u/chk (not (u/nonempty? (.-stderr p))) [name (u/bslice (.-stderr p) -1000 nil)]))
                    p))
        target (if (= "x86_64" machine) "x86_64-linux" "aarch64-linux")
        _ (observe "compile" [compiler "compile" source "--target" target "--output" image "--format" "static"] env :timeout 900)
        _ (.chmod image 0755)
        scope-for (fn [name]
                    (let [scope (.joinpath out (str "scope-" name))]
                      (.mkdir scope)
                      [scope (python/dict {"PATH" "/nonexistent" "KEXE_ALLOW" "35,37,38,39" "KEXE_CAP_RESOURCES_35" (str scope) "KEXE_STACK_BYTES" "8388608"})]))
        positives ["original-forms" "raw" "managed" "no-replace" "large" "managed-return" "managed-publish" "managed-publish-exclusive"]]
    (doseq [case positives]
      (let [[scope guest] (scope-for case)
            path (if (contains? #{"raw" "large"} case) (.joinpath scope "data") scope)
            result (observe case [image case path] guest :timeout 300)]
        (u/chk (not (u/nonempty? (.-stdout result))))
        (u/chk (empty? (glob-vec scope "kotoba-output-*")) [case "owned stage remains"])
        (when (contains? #{"managed-publish" "managed-publish-exclusive"} case)
          (u/chk (= (.encode "preserved") (.read_bytes (.joinpath scope "published")))))))
    ;; Form U (draft full-permission no-follow stat): real files with exact modes, a final symlink and a directory;
    ;; the fixture also requires O to keep its old mask.
    (let [[scope guest] (scope-for "full-mode")]
      (doseq [[fname fmode] [["regular" 0644] ["special" 04644] ["group" 02644] ["sticky" 01644]]]
        (.write_bytes (.joinpath scope fname) (.encode "x"))
        (.chmod (.joinpath scope fname) fmode))
      (os/symlink (.joinpath scope "regular") (.joinpath scope "link"))
      (.mkdir (.joinpath scope "directory"))
      (observe "full-mode" [image "full-mode" scope] guest :timeout 60))
    ;; Existence errors: D answers 1 for a readable file, 0 for ENOENT and ? for every other error, a symlink leaf,
    ;; an escaping symlink and a path outside the granted root.
    (let [[scope guest] (scope-for "exists-errors")
          outside (.joinpath out "exists-outside")]
      (.write_bytes outside (.encode "x"))
      (.write_bytes (.joinpath scope "readable") (.encode "x"))
      (.write_bytes (.joinpath scope "denied") (.encode "x"))
      (.chmod (.joinpath scope "denied") 0)
      (.mkdir (.joinpath scope "parent"))
      (.write_bytes (.joinpath (.joinpath scope "parent") "inside") (.encode "x"))
      (.chmod (.joinpath scope "parent") 0)
      (os/symlink (.joinpath scope "readable") (.joinpath scope "link"))
      (os/symlink outside (.joinpath scope "escape"))
      (try
        (observe "exists-errors" [image "exists-errors" scope outside] guest :timeout 60)
        (finally
          ;; the evidence upload must be able to read the scope
          (.chmod (.joinpath scope "parent") 0700)
          (.chmod (.joinpath scope "denied") 0600))))
    (doseq [[name mode extra diagnostic] [["fault" "managed-fault" {} (.encode ":kind :signal")]
                                          ["fuel" "managed-fuel" {"KEXE_FUEL" "1000000"} (.encode ":kind :signal")]
                                          ["cpu" "managed-signal" {"KEXE_CPU_SECONDS" "1"} (.encode ":signal :SIGXCPU")]
                                          ["wall" "managed-signal" {"KEXE_WALL_SECONDS" "2"} (.encode ":signal :SIGALRM")]]]
      (let [[scope guest] (scope-for name)
            e (python/dict guest)]
        (doseq [[k v] extra] (operator/setitem e k v))
        (observe name [image mode scope] e :expected 120 :diagnostic diagnostic :timeout 30)
        (u/chk (empty? (glob-vec scope "kotoba-output-*")) [name "owned stage remains"])))
    (doseq [sig [signal/SIGINT signal/SIGTERM]]
      (let [name (str "external-" (.-name sig))
            [scope guest] (scope-for name)
            p (subprocess/Popen (python/list [(str image) "managed-signal" (str scope)]) ** :cwd out :env guest
                                :stdout subprocess/PIPE :stderr subprocess/PIPE)
            deadline (+ (time/monotonic) 15)
            [stdout stderr]
            (try
              (loop []
                (when (and (not (.exists (.joinpath scope "ready"))) (< (time/monotonic) deadline) (nil? (.poll p)))
                  (time/sleep 0.005)
                  (recur)))
              (u/chk (.exists (.joinpath scope "ready")) [name "fixture did not stage"])
              (.send_signal p sig)
              (vec (.communicate p ** :timeout 15))
              (catch python/BaseException e
                (.kill p)
                (.communicate p)
                (throw e)))]
        (.write_bytes (.joinpath out (str name ".stdout")) stdout)
        (.write_bytes (.joinpath out (str name ".stderr")) stderr)
        (u/chk (and (= 120 (.-returncode p)) (u/has-bytes? (.encode (str ":signal :" (.-name sig))) stderr)
                    (not (u/has-bytes? (.encode "KEXE_CLEANUP") stderr))))
        (u/chk (and (not (u/nonempty? stdout)) (empty? (glob-vec scope "kotoba-output-*"))))
        (.append calls (u/pydict "name" name "exit" (.-returncode p)))))
    ;; FIFO/socket fixtures require a native Linux filesystem. A macOS virtiofs task mount can reject mknod even
    ;; though the guest's /tmp admits it. Only these owned, ephemeral input fixtures live there; all evidence
    ;; remains in the requested output directory.
    (let [refusal-temp (tempfile/TemporaryDirectory ** :prefix "amu-fs2-refusals-")
          scope (pathlib/Path (.-name refusal-temp))
          guest (python/dict {"PATH" "/nonexistent" "KEXE_ALLOW" "35,37,38,39" "KEXE_CAP_RESOURCES_35" (str scope) "KEXE_STACK_BYTES" "8388608"})
          _ (.write_bytes (.joinpath scope "ascii") (.encode "abcdef"))
          _ (.mkdir (.joinpath scope "directory"))
          _ (os/mkfifo (.joinpath scope "fifo"))
          _ (.symlink_to (.joinpath scope "link") "ascii")
          local-socket (socket/socket socket/AF_UNIX socket/SOCK_STREAM)
          ;; sockaddr_un bounds the supplied name, even under a long task path. Change only this observer's cwd
          ;; while staging the relative socket.
          prior-cwd (os/open "." (bit-or os/O_RDONLY os/O_DIRECTORY))
          refusals [["unknown-form" "V" (.joinpath scope "ascii") "" ":stage 8}"]
                    ["empty-path" "A" "" "" ":stage 2}"]
                    ["forbidden-tail" "D" (.joinpath scope "ascii") "x" ":stage 2}"]
                    ["bad-mode" "H" (.joinpath scope "ascii") "8" ":stage 7}"]
                    ["bad-temp-prefix" "N" scope "a/b" ":stage 9}"]
                    ["stage-wrong-shape" "Q" (.joinpath scope "ascii") "644" ":stage 8}"]
                    ["range-outside-file" "E" (.joinpath scope "ascii") "7:0" ":reason :fs/range-unavailable}"]
                    ["range-short-file" "E" (.joinpath scope "ascii") "5:2" ":reason :fs/range-unavailable}"]
                    ["range-directory" "E" (.joinpath scope "directory") "0:0" ":reason :fs/range-unavailable}"]
                    ["range-fifo" "E" (.joinpath scope "fifo") "0:0" ":reason :fs/range-unavailable}"]
                    ["range-socket" "E" (.joinpath scope "socket") "0:0" ":reason :fs/range-unavailable}"]
                    ["range-symlink" "E" (.joinpath scope "link") "0:0" ":reason :fs/range-unavailable}"]
                    ["raw-legacy-refused" "legacy-bytes" (.joinpath scope "ascii") "" ":stage 2}"]]]
      (try
        (try
          (os/chdir scope)
          (.bind local-socket "socket")
          (finally
            (os/fchdir prior-cwd)
            (os/close prior-cwd)))
        (doseq [[name mode path tail diagnostic] refusals]
          (observe name [image mode path tail] guest :expected 126 :diagnostic (.encode diagnostic) :timeout 30))
        (finally
          (.close local-socket)
          (.cleanup refusal-temp)))
      (let [boundary-cases (vec (concat ["close-consumed-eintr" "partial-read" "partial-write"]
                                        (for [window ["directory" "file"] sig ["sigint" "sigterm" "sigalrm" "sigxcpu"]] (str "journal-" window "-" sig))))
            errno-cases ["write-eio" "fsync-eio" "chmod-eperm" "unlink-eacces" "fstat-eio" "entropy-enosys" "rename-enosys" "open-enosys"]]
        (doseq [[script cases] [["check-fs2-observed.py" boundary-cases] ["check-fs2-errno.py" errno-cases]]
                case cases]
          (observe case [sys/executable (.joinpath root (str "scripts/seed/" script)) "--image" image "--output" (.joinpath out case) "--case" case]
                   (python/dict os/environ) :timeout 45))
        (u/chk (u/deq (u/pin source) source-pin))
        (let [report (u/pydict "status" "PASS_NATIVE_FS2_CURRENT_MATRIX" "host" (python/list [(platform/system) machine])
                               "source" source-pin "compiler" (u/pin compiler) "image" (u/pin image) "calls" calls
                               "positiveFixtureCases" (count positives) "observedKernelBoundaries" (count boundary-cases)
                               "kernelErrnoCases" (count errno-cases) "framingRangeShapeRefusals" (count refusals)
                               "nativeGuestOwnsPositiveAssertions" true "legacyRuntimeFallback" false "emulation" false
                               "allFaultRaceParityQualified" false "wholePublicCLIQualified" false)]
          (.write_text (.joinpath out "native-fs2.json") (u/json-dump report))
          (println (u/geti report "status") machine))))))

(defn -main [& args]
  (main (.resolve (pathlib/Path (or (u/opt args "--compiler") (sys/exit "--compiler is required"))))
        (.resolve (pathlib/Path (or (u/opt args "--output") (sys/exit "--output is required"))))))

(when (some #(or (= % "check-native-fs2.cljc") (str/ends-with? % "/check-native-fs2.cljc")) sys/argv)
  (apply -main *command-line-args*))
