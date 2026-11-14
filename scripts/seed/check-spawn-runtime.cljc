;; The static runtime's wire 20 (:process/spawn), through the spawn helper. Linear JUN-292. Ported from
;; check-spawn-runtime.py (Basilisp, JUN-974); the Python docstring has the three-part contract (the grant at
;; start, the wire end to end, and the sandbox/SIGPIPE/read-error control compilers).
;; Run (Linux): basilisp run -p scripts/seed scripts/seed/check-spawn-runtime.cljc -- --compiler F --output DIR
;;      [--target aarch64-linux|x86_64-linux] [--seccomp-if-available]
(ns check-spawn-runtime
  (:require [basilisp.string :as str]
            [gate-util :as u])
  (:import json operator pathlib platform subprocess sys))

(def root u/root)
(defn rp [rel] (pathlib/Path root rel))
(def selfhost "seed/X86_64-LINUX-SELFHOST-MANIFEST")
(def fuel "100000000")
(def s "ARG_SEP")
(def t "STDIN_SEP")
(defn g [m & ks] (reduce (fn [a k] (operator/getitem a k)) m ks))
(defn pin [p] (let [d (.read_bytes (pathlib/Path p))] (u/pydict "bytes" (python/len d) "sha256" (u/sha256-hex d))))
(defn chk [c m] (u/chk c (str m)))
(defn pyenv [& kvs] (apply u/pydict kvs))
(defn b [x] (.encode x "utf-8"))
(defn tailb [bs n] (.decode (u/bslice bs (max 0 (- (python/len bs) n)) (python/len bs)) "utf-8" "replace"))
(defn dec- [bs] (.decode bs "utf-8" "replace"))

(def sigpipe-bit "m=$(grep SigIgn /proc/self/status | cut -f2); echo $(( (0x$m >> 12) & 1 ))")
(def src-plain "(ns t (:export [main]))\n(defn main [] :i64 42)\n")
(def src-head "(ns t (:export [main]))\n(defn- spawn [s :string] :string (typed-cap-call :process/spawn :string :string s))\n(defn- say [s :string] :i64 (let [x (typed-cap-call :io/write :string :string s)] 0))\n(defn- dbl [s :string k :i64] :string (if (= k 0) s (dbl (string-concat s s) (dec k))))\n")
(def no-read-rule ["(if (> (kxrt-gl 2096) 2) (kxrt-allow-read-fd p i4 (kxrt-gl 2096)) i4)", "i4", 2])
(def no-sigpipe-reset ["        dfl (kxrt-signal 13 q)\n", "        dfl 0\n", 2])
(def read-error-arm ["m (kxrt-syscall 63 fd (+ o got) (- 16385 got) 0 0 0)", "m (if (> got 0) -5 (kxrt-syscall 63 fd (+ o got) (- 16385 got) 0 0 0))"])
(def read-error-x86 ["m (kxrt-syscall 0 fd (+ o got) (- 16385 got) 0 0 0)", "m (if (> got 0) -5 (kxrt-syscall 0 fd (+ o got) (- 16385 got) 0 0 0))"])
(def read-error-old ["(< m 0) -5", "(< m 0) got", 2])

(defn guest [& requests]
  (str src-head "(defn main [] :i64\n  (let [" (str/join " " (map-indexed (fn [k r] (str "a" k " (say (spawn " r "))")) requests)) "]\n    7))\n"))
(defn lit [& parts] (str "\"" (str/join s parts) "\""))
(defn lit-in [parts payload] (str "\"" (str/join s parts) t payload "\""))

(defn unity-text []
  (let [paths (vec (filter #(and (seq %) (not (.startswith % "#"))) (.splitlines (.read_text (rp selfhost)))))]
    [(apply str (map #(str (.read_text (rp %)) "\n") paths))
     (u/pydict-from (for [p (cons selfhost paths)] [p (pin (rp p))]))]))

(defn patched [text edits]
  (reduce (fn [text [old new n]]
            (let [n (or n 1)]
              (chk (= (.count text old) n) ["patch anchor" (subs old 0 (min 60 (count old))) (.count text old)])
              (.replace text old new)))
          text edits))

(defn run-main [compiler output target seccomp?]
  (chk (= (platform/system) "Linux") "run on Linux")
  (.mkdir output ** :parents true :exist_ok false)
  (let [art (pathlib/Path output "artifacts") raw (pathlib/Path output "raw") scope (pathlib/Path output "scope")
        _ (doseq [d [art raw scope]] (.mkdir d))
        producer (pathlib/Path art "compiler.elf")
        _ (.write_bytes producer (.read_bytes compiler))
        _ (.chmod producer 0755)
        base-env (let [d (pyenv "PATH" "/usr/bin:/bin" "KEXE_STRUCTURED_REPORT" "1" "KEXE_FUEL" fuel)]
                   (when seccomp? (operator/setitem d "KEXE_SECCOMP" "if-available"))
                   d)
        compile- (fn [prod name source tgt]
                   (let [src (pathlib/Path art (str name ".kotoba")) out (pathlib/Path art (str name ".elf"))
                         _ (.write_text src source)
                         r (subprocess/run (python/list [(str prod) "compile" (str src) "--target" tgt "--output" (str out) "--format" "static"])
                                           ** :cwd art :env (pyenv "PATH" "/usr/bin:/bin" "KEXE_CAP_RESOURCES_35" (str art) "KEXE_STACK_BYTES" "8388608")
                                           :capture_output true :timeout 1800)]
                     (.write_bytes (pathlib/Path raw (str name ".compile.stdout")) (.-stdout r))
                     (.write_bytes (pathlib/Path raw (str name ".compile.stderr")) (.-stderr r))
                     (chk (and (= (.-returncode r) 0) (zero? (python/len (.-stderr r))) (u/has-bytes? (b ":ok true") (.-stdout r))) [name (.-returncode r) (tailb (.-stderr r) 400)])
                     (.chmod out 0755)
                     out))
        run (fn [name elf env]
              (let [x (subprocess/run (python/list [(str elf)]) ** :env (let [d (python/dict base-env)] (.update d env) d) :capture_output true :timeout 120)]
                (.write_bytes (pathlib/Path raw (str name ".stdout")) (.-stdout x))
                (.write_bytes (pathlib/Path raw (str name ".stderr")) (.-stderr x))
                x))
        ;; ---- part 1: the grant at start ----
        plain (compile- producer "plain" src-plain target)
        knob-rows (python/list [])
        knob (fn [name & {:keys [programs names lookup allow want-exit] :or {allow "20,37" want-exit 2}}]
               (let [env (pyenv "KEXE_ALLOW" allow)]
                 (doseq [[k v] [["KEXE_CAP_RESOURCES_20" programs] ["KEXE_SPAWN_ENV" names] ["KEXE_SPAWN_PATH_LOOKUP" lookup]]]
                   (when (some? v) (operator/setitem env k v)))
                 (let [x (run (str "knob-" name) plain env)]
                   (chk (= (.-returncode x) want-exit) [name (.-returncode x) (.-stdout x) (.-stderr x)])
                   (when (zero? want-exit) (chk (u/has-bytes? (b ":status :ok :result 42") (.-stdout x)) [name (.-stdout x)]))
                   (.append knob-rows (pyenv "name" name "programs" programs "names" names "lookup" lookup "allow" allow "exit" (.-returncode x))))))]
    (knob "relative-program" :programs "bin/echo")
    (knob "root-alone" :programs "/")
    (knob "empty-segment" :programs "/bin//echo")
    (knob "dot-segment" :programs "/bin/./echo")
    (knob "dotdot-segment" :programs "/bin/../echo")
    (knob "trailing-slash" :programs "/bin/echo/")
    (knob "empty-entry" :programs "/bin/echo::/bin/sh")
    (knob "duplicate" :programs "/bin/echo:/bin/echo")
    (knob "seventeen-programs" :programs (str/join ":" (map #(str "/p/" %) (range 17))))
    (knob "name-with-equals" :programs "/bin/echo" :names "A=B")
    (knob "empty-name" :programs "/bin/echo" :names "A::B")
    (knob "seventeen-names" :programs "/bin/echo" :names (str/join ":" (map #(str "N" %) (range 17))))
    (knob "lookup-two" :programs "/bin/echo" :lookup "2")
    (knob "lookup-same-base" :programs "/bin/echo:/usr/bin/echo" :lookup "1")
    (knob "valid" :programs "/bin/echo:/bin/sh" :names "FOO" :lookup "0" :want-exit 0)
    (knob "sixteen-programs" :programs (str/join ":" (map #(str "/p/" %) (range 16))) :want-exit 0)
    (knob "absent" :want-exit 0)
    (knob "not-granted-ignored" :programs "x" :names "=" :lookup "9" :allow "37" :want-exit 0)
    ;; ---- part 2: the wire ----
    (let [rows (python/list [])
          grant "/bin/echo:/bin/sh:/bin/cat:/bin/ls:/usr/bin/env:/bin/pwd:/bin/sleep:/nonexistent/program"
          e2e (fn [name source & {:keys [want-exit stdout-is stdout-has stderr-has prod env] :or {want-exit 0 stdout-has [] stderr-has []}}]
                (let [elf (compile- (or prod producer) (str "e2e-" name) source target)
                      e (let [d (pyenv "KEXE_ALLOW" "20,37" "KEXE_CAP_RESOURCES_20" grant)] (when env (.update d env)) d)
                      x (run (str "e2e-" name) elf e)]
                  (chk (= (.-returncode x) want-exit) [name (.-returncode x) (tailb (.-stdout x) 300) (tailb (.-stderr x) 300)])
                  (when (some? stdout-is) (chk (.startswith (.-stdout x) (operator/add stdout-is (b "{:status :ok :result 7 "))) [name (.-stdout x)]))
                  (doseq [x- stdout-has] (chk (u/has-bytes? x- (.-stdout x)) [name x- (tailb (.-stdout x) 300)]))
                  (doseq [x- stderr-has] (chk (u/has-bytes? x- (.-stderr x)) [name x- (tailb (.-stderr x) 300)]))
                  (.append rows (pyenv "name" name "exit" (.-returncode x) "stdout" (dec- (.-stdout x)) "stderr" (dec- (.-stderr x)) "image" (pin elf)))))
          x40k "(dbl \"0123456789\" 12)"]
      (e2e "arguments-and-exit" (guest (lit "/bin/echo" "hello" "world") (lit "/bin/sh" "-c" "exit 3") (lit "/bin/sh" "-c" "kill -9 $$"))
           :stdout-is (b "0\nhello world\n3\n-1\n"))
      (e2e "stdin-at-eof" (guest (lit "/bin/cat")) :stdout-is (b "0\n"))
      (e2e "stdin-payload" (guest (lit-in ["/bin/cat"] "hello\\nworld")) :stdout-is (b "0\nhello\nworld"))
      (e2e "stdin-payload-with-arguments" (guest (lit-in ["/bin/sh" "-c" "tr a-z A-Z"] "abc")) :stdout-is (b "0\nABC"))
      (e2e "stdin-payload-holds-arg-sep" (guest (lit-in ["/bin/cat"] (str "x" s "y"))) :stdout-is (b (str "0\nx" s "y")))
      (e2e "stdin-payload-empty" (guest (lit-in ["/bin/cat"] "")) :stdout-is (b "0\n"))
      (e2e "stdin-sep-ends-argv" (guest (str "\"/bin/echo" s "a" t "b\"")) :stdout-is (b "0\na\n"))
      (e2e "stdin-payload-40k-read" (guest (str "(string-concat \"/bin/sh" s "-c" s "wc -c" t "\" " x40k ")")) :stdout-has [(b "40960")])
      (e2e "stdin-payload-40k-unread-exit" (guest (str "(string-concat \"/bin/sh" s "-c" s "exit 0" t "\" " x40k ")")) :stdout-is (b "0\n"))
      (e2e "stdin-payload-40k-unread-sleep" (guest (str "(string-concat \"/bin/sleep" s "1" t "\" " x40k ")")) :stdout-is (b "0\n"))
      ;; bit 12 of SigIgn is SIGPIPE (13); the rest of the mask is the host's
      (e2e "sigpipe-default" (guest (lit "/bin/sh" "-c" sigpipe-bit)) :stdout-is (b "0\n0\n"))
      (e2e "only-granted-variables" (guest (lit "/usr/bin/env")) :stdout-is (b "0\nFOO=bar\n")
           :env (pyenv "KEXE_SPAWN_ENV" "FOO:MISSING" "FOO" "bar" "BAZ" "qux"))
      (e2e "only-stdio-open" (guest (lit "/bin/ls" "/proc/self/fd")) :stdout-is (b "0\n0\n1\n2\n3\n"))
      (e2e "no-new-privs" (guest (lit "/bin/sh" "-c" "grep NoNewPrivs /proc/self/status")) :stdout-is (b "0\nNoNewPrivs:\t1\n"))
      (e2e "no-address-space-limit" (guest (lit "/bin/sh" "-c" "ulimit -v")) :stdout-is (b "0\nunlimited\n"))
      (e2e "scope-root-directory" (guest (lit "/bin/pwd")) :stdout-is (b (str "0\n" scope "\n"))
           :env (pyenv "KEXE_ALLOW" "20,35,37" "KEXE_CAP_RESOURCES_35" (str scope)))
      (e2e "lookup-by-name" (guest (lit "echo" "hi")) :stdout-is (b "0\nhi\n") :env (pyenv "KEXE_SPAWN_PATH_LOOKUP" "1"))
      (let [trap (b "KEXE_TRAP {:kind :capability :capability :process/spawn :reason :spawn/")]
        (doseq [[name source reason env] [["program-not-granted" (guest (lit "/bin/true")) "program-not-granted" nil]
                                          ["path-lookup-denied" (guest (lit "echo" "hi")) "path-lookup-denied" nil]
                                          ["lookup-name-not-granted" (guest (lit "true")) "program-not-granted" (pyenv "KEXE_SPAWN_PATH_LOOKUP" "1")]
                                          ["argv-budget" (guest (apply lit "/bin/echo" (repeat 33 "x"))) "argv-budget" nil]
                                          ["argv-bytes-budget" (guest (str "(string-concat \"/bin/echo" s "\" (dbl \"x\" 12))")) "argv-budget" nil]
                                          ["output-budget" (guest (lit "/bin/sh" "-c" "yes")) "output-budget" nil]
                                          ["timeout" (guest (lit "/bin/sleep" "11")) "timeout" nil]
                                          ["exec-failed" (guest (lit "/nonexistent/program")) "exec-failed" nil]
                                          ["no-programs-granted" (guest (lit "/bin/echo")) "program-not-granted" (pyenv "KEXE_CAP_RESOURCES_20" "")]]]
          (e2e name source :want-exit 126 :stderr-has [(operator/add (operator/add trap (b reason)) (b "}\n"))] :env env))
        (e2e "empty-program" (guest (lit "" "x")) :want-exit 120 :stderr-has [(b ":signal :SIGILL")])
        (e2e "request-over-65536" (guest (str "(string-concat \"/bin/echo" s "\" (dbl \"x\" 16))")) :want-exit 120 :stderr-has [(b ":signal :SIGILL")])
        (e2e "wire-not-granted" (guest (lit "/bin/echo")) :want-exit 120
             :stderr-has [(b "KEXE_CAP {:wire 20 :refused :not-granted}\n") (b ":signal :SIGILL")] :env (pyenv "KEXE_ALLOW" "37"))
        ;; ---- part 3: the guest stays sandboxed ----
        (let [host (get {"aarch64" "aarch64-linux" "arm64" "aarch64-linux" "x86_64" "x86_64-linux" "AMD64" "x86_64-linux"} (platform/machine))
              [text unity-pins] (unity-text)
              control (compile- producer "control-compiler-no-read-rule" (patched text [no-read-rule]) host)
              enforced (not seccomp?)]
          (when enforced
            (e2e "control-no-read-rule" (guest (lit "/bin/echo" "x")) :want-exit 120 :prod control :stderr-has [(b ":signal :SIGSYS")]))
          (let [control-pipe (compile- producer "control-compiler-no-sigpipe-reset" (patched text [no-sigpipe-reset]) host)]
            (e2e "control-no-sigpipe-reset" (guest (lit "/bin/sh" "-c" sigpipe-bit)) :prod control-pipe :stdout-is (b "0\n1\n"))
            ;; Inject a read error after a real stdout chunk. The old EOF treatment returned that partial chunk
            ;; as success; the candidate must refuse it.
            (let [read-error [read-error-arm read-error-x86]
                  error-compiler (compile- producer "compiler-output-read-error" (patched text read-error) host)]
              (e2e "output-read-error" (guest (lit "/bin/echo" "partial")) :prod error-compiler :want-exit 126
                   :stderr-has [(operator/add trap (b "setup-failed}\n"))])
              (let [old-compiler (compile- producer "control-compiler-output-read-error" (patched text (concat read-error [read-error-old])) host)]
                (e2e "control-output-read-error" (guest (lit "/bin/echo" "partial")) :prod old-compiler :stdout-is (b "0\npartial\n"))
                (let [machine (platform/machine)
                      report (pyenv "status" "PASS_SPAWN_RUNTIME" "target" target "compiler" (pin compiler)
                                    "host" (python/list [(platform/system) machine (platform/release)])
                                    "executionNative" (= (first (str/split target #"-")) (get {"arm64" "aarch64" "AMD64" "x86_64"} machine machine))
                                    "imageSeccomp" (if seccomp? "if-available" "required")
                                    "grant" grant "knob" knob-rows "wire" rows
                                    "controlCompiler" (pyenv "mutation" "no read rule for the helper's answer fd, in both runtimes" "pin" (pin control))
                                    "controlCompilerSigpipe" (pyenv "mutation" "the child keeps the helper's ignored SIGPIPE, in both runtimes" "pin" (pin control-pipe))
                                    "outputReadErrorCompiler" (pyenv "mutation" "read error after a stdout chunk, in both runtimes" "pin" (pin error-compiler))
                                    "outputReadErrorOldControl" (pyenv "mutation" "read error treated as EOF, in both runtimes" "pin" (pin old-compiler))
                                    "unity" unity-pins "cCompilerOrLoader" false
                                    "notCovered" (python/list (concat ["spawn/isolation-unavailable and spawn/setup-failed: no case here drives the child's setup to fail; check-spawn-fault-injection.py covers close_range and fchdir under injected seccomp faults, not prctl or dup3"
                                                                       "the stdin payload's deadline: a request holds at most 65536 bytes, which a default 64 KiB pipe takes whole, so no case blocks the feeding"]
                                                                      (when-not enforced ["control-no-read-rule: this kernel does not enforce seccomp (KEXE_SECCOMP=if-available)"]))))]
                  (.write_text (pathlib/Path output "spawn-runtime.json") (u/json-dump report))
                  (println (g report "status") target (python/len knob-rows) "grant cases" (python/len rows) "wire cases")
                  (.flush sys/stdout))))))))))

(defn -main [& args]
  (let [target (or (u/opt args "--target") "aarch64-linux")]
    (when-not (#{"aarch64-linux" "x86_64-linux"} target) (sys/exit "--target must be aarch64-linux or x86_64-linux"))
    (run-main (.resolve (pathlib/Path (or (u/opt args "--compiler") (sys/exit "--compiler is required"))))
              (.resolve (pathlib/Path (or (u/opt args "--output") (sys/exit "--output is required"))))
              target (boolean (some #{"--seccomp-if-available"} args)))))

(when (some #(or (= % "check-spawn-runtime.cljc") (str/ends-with? % "/check-spawn-runtime.cljc")) sys/argv)
  (apply -main *command-line-args*))
