;; The static runtimes' durable file replace (wire 35 FSYNC_SEP, RENAME_SEP, UNLINK_SEP) and sleep (wire 7
;; "sleep <ms>"). Linear JUN-359, JUN-360. Ported from check-durable-sleep.py (Basilisp, JUN-974); the Python
;; docstring has the full contract (the replace, the "0" refusals, sleep, and the sandbox control compilers without
;; fsync / clock_nanosleep in the seccomp filter).
;; Run (Linux): basilisp run -p scripts/seed scripts/seed/check-durable-sleep.cljc -- --compiler F --output DIR
;;      [--target aarch64-linux|x86_64-linux] [--seccomp-if-available]
(ns check-durable-sleep
  (:require [basilisp.string :as str]
            [gate-util :as u])
  (:import json operator os pathlib platform subprocess sys))

(def root u/root)
(defn rp [rel] (pathlib/Path root rel))
(def selfhost "seed/X86_64-LINUX-SELFHOST-MANIFEST")
(def fuel "100000000")
(defn g [m & ks] (reduce (fn [a k] (operator/getitem a k)) m ks))
(defn pin [p] (let [d (.read_bytes (pathlib/Path p))] (u/pydict "bytes" (python/len d) "sha256" (u/sha256-hex d))))
(defn chk [c m] (u/chk c (str m)))
(defn pyenv [& kvs] (apply u/pydict kvs))
(defn b [s] (.encode s "utf-8"))
(defn tailb [bs n] (.decode (u/bslice bs (max 0 (- (python/len bs) n)) (python/len bs)) "utf-8" "replace"))
(defn headdec [bs n] (let [s (.decode bs "utf-8" "replace")] (subs s 0 (min n (count s)))))

(def src-head "(ns t (:export [main]))\n(defn- fs [s :string] :string (typed-cap-call :fs/app-data :string :string s))\n(defn- clock [s :string] :string (typed-cap-call :clock/now :string :string s))\n(defn- say [s :string] :i64 (let [x (typed-cap-call :io/write :string :string (string-concat s \"|\"))] 0))\n(defn- decimal [s :string] :i64\n  (loop [i 0 n 0] (if (= i (string-length s)) n (recur (+ i 1) (+ (* n 10) (- (string-code-point-at s i) 48))))))\n")
(def src-unlink-malformed "(ns t (:export [main]))\n(defn- fs [s :string] :string (typed-cap-call :fs/app-data :string :string s))\n(defn- clock [s :string] :string (typed-cap-call :clock/now :string :string s))\n(defn- say [s :string] :i64 (let [x (typed-cap-call :io/write :string :string (string-concat s \"|\"))] 0))\n(defn- decimal [s :string] :i64\n  (loop [i 0 n 0] (if (= i (string-length s)) n (recur (+ i 1) (+ (* n 10) (- (string-code-point-at s i) 48))))))\n(defn main [] :i64\n  (let [x (typed-cap-call :fs/app-data :string :string \"badUNLINK_SEPUNLINK_SEP\")] 7))\n")
(def src-sleep "(ns t (:export [main]))\n(defn- fs [s :string] :string (typed-cap-call :fs/app-data :string :string s))\n(defn- clock [s :string] :string (typed-cap-call :clock/now :string :string s))\n(defn- say [s :string] :i64 (let [x (typed-cap-call :io/write :string :string (string-concat s \"|\"))] 0))\n(defn- decimal [s :string] :i64\n  (loop [i 0 n 0] (if (= i (string-length s)) n (recur (+ i 1) (+ (* n 10) (- (string-code-point-at s i) 48))))))\n(defn main [] :i64\n  (let [t0 (decimal (clock \"monotonic\")) t1 (decimal (clock \"sleep 200\")) t2 (decimal (clock \"sleep 0\"))\n        a (say (if (>= (- t1 t0) 200000000) \"slept\" \"short\")) b (say (if (>= t2 t1) \"ok\" \"back\"))]\n    7))\n")
(def src-sleep-req "(ns t (:export [main]))\n(defn- fs [s :string] :string (typed-cap-call :fs/app-data :string :string s))\n(defn- clock [s :string] :string (typed-cap-call :clock/now :string :string s))\n(defn- say [s :string] :i64 (let [x (typed-cap-call :io/write :string :string (string-concat s \"|\"))] 0))\n(defn- decimal [s :string] :i64\n  (loop [i 0 n 0] (if (= i (string-length s)) n (recur (+ i 1) (+ (* n 10) (- (string-code-point-at s i) 48))))))\n(defn main [] :i64 (let [a (say (clock (typed-cap-call 38 :string :string \"0\")))] 7))\n")
(def src-fsync-only "(ns t (:export [main]))\n(defn- fs [s :string] :string (typed-cap-call :fs/app-data :string :string s))\n(defn- clock [s :string] :string (typed-cap-call :clock/now :string :string s))\n(defn- say [s :string] :i64 (let [x (typed-cap-call :io/write :string :string (string-concat s \"|\"))] 0))\n(defn- decimal [s :string] :i64\n  (loop [i 0 n 0] (if (= i (string-length s)) n (recur (+ i 1) (+ (* n 10) (- (string-code-point-at s i) 48))))))\n(defn main [] :i64 (let [a (say (fs (typed-cap-call 38 :string :string \"0\")))] 7))\n")
(def no-fsync-rule [["(kxrt-allow-nr-at p 82) (kxrt-allow-nr-at p 278)", "(kxrt-allow-nr-at p 278)", 1], ["(kxrt-allow-nr-at p 74) (kxrt-allow-nr-at p 318)", "(kxrt-allow-nr-at p 318)", 1]])
(def no-sleep-rule [["        i8 (if (kxrt-admitted? 7) (kxrt-allow-nr p (kxrt-allow-nr p i7 115) 128) i7)\n", "        i8 (if (kxrt-admitted? 7) (kxrt-allow-nr p i7 128) i7)\n", 1], ["        i8 (if (kxrt-admitted? 7) (kxrt-allow-nr p (kxrt-allow-nr p i7 230) 219) i7)\n", "        i8 (if (kxrt-admitted? 7) (kxrt-allow-nr p i7 219) i7)\n", 1]])

(defn lit [s] (str "\"" (.replace (.replace s "\\" "\\\\") "\"" "\\\"") "\""))

(defn guest-of [steps]
  (str src-head "(defn main [] :i64\n  (let [" (str/join " " (map-indexed (fn [k x] (str "s" k " " x)) steps)) "]\n    7))\n"))

(defn fs-guest [scope outside]
  (let [p (fn [rest-] (lit (str scope "/" rest-)))]
    (guest-of [(str "(fs " (p "tmpWRITE_SEPhello") ")")
               (str "(say (fs " (p "tmpFSYNC_SEP") "))")
               (str "(say (fs " (lit (str scope "/tmpRENAME_SEP" scope "/final")) "))")
               (str "(say (fs " (p "final") "))")
               (str "(say (fs " (p "tmpEXISTS_SEP") "))")
               (str "(fs " (p "oldWRITE_SEPold") ")") (str "(fs " (p "newWRITE_SEPnew") ")")
               (str "(say (fs " (lit (str scope "/newRENAME_SEP" scope "/old")) "))")
               (str "(say (fs " (p "old") "))")
               (str "(fs " (p "sub/aWRITE_SEPa") ")")
               (str "(say (fs " (lit (str scope "/sub/aRENAME_SEP" scope "/b")) "))")
               (str "(say (fs " (p "b") "))")
               (str "(say (fs " (lit (str scope "FSYNC_SEP")) "))")
               (str "(say (fs " (p "missingFSYNC_SEP") "))")
               (str "(say (fs " (lit (str scope "/missingRENAME_SEP" scope "/x")) "))")
               (str "(say (fs " (lit (str scope "/finalRENAME_SEP" outside "/stolen")) "))")
               (str "(say (fs " (lit (str scope "/finalRENAME_SEP" scope "/link/stolen")) "))")
               (str "(say (fs " (p "finalEXISTS_SEP") "))")])))

(defn unlink-guest [scope outside]
  (let [p (fn [rest-] (lit (str scope "/" rest-)))]
    (guest-of [(str "(say (fs " (p "remove-meUNLINK_SEP") "))")
               (str "(say (fs " (p "remove-meEXISTS_SEP") "))")
               (str "(say (fs " (p "absentUNLINK_SEP") "))")
               (str "(say (fs " (lit (str outside "/outside-fileUNLINK_SEP")) "))")
               (str "(say (fs " (p "parent-link/parent-targetUNLINK_SEP") "))")
               (str "(say (fs " (p "final-linkUNLINK_SEP") "))")
               (str "(say (fs " (p "final-linkEXISTS_SEP") "))")])))

(defn unity-text []
  (let [paths (vec (filter #(and (seq %) (not (.startswith % "#"))) (.splitlines (.read_text (rp selfhost)))))]
    [(apply str (map #(str (.read_text (rp %)) "\n") paths))
     (u/pydict-from (for [p (cons selfhost paths)] [p (pin (rp p))]))]))

(defn patched [text edits]
  (reduce (fn [text [old new n]]
            (chk (= (.count text old) n) ["patch anchor" (subs old 0 (min 60 (count old))) (.count text old)])
            (.replace text old new))
          text edits))

(defn run [compiler output target seccomp?]
  (chk (= (platform/system) "Linux") "run on Linux")
  (.mkdir output ** :parents true :exist_ok false)
  (let [art (pathlib/Path output "artifacts") raw (pathlib/Path output "raw")
        scope (pathlib/Path output "scope") outside (pathlib/Path output "outside")
        _ (doseq [d [art raw scope outside (pathlib/Path scope "sub")]] (.mkdir d))
        _ (os/symlink outside (pathlib/Path scope "link"))
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
        rows (python/list [])
        sigill (b ":signal :SIGILL")
        case (fn [name elf env & {:keys [args want-exit stdout-is stderr-has] :or {args [] want-exit 0 stderr-has []}}]
               (let [x (subprocess/run (python/list (map str (cons elf args))) ** :env (let [d (python/dict base-env)] (.update d env) d) :capture_output true :timeout 120)]
                 (.write_bytes (pathlib/Path raw (str name ".stdout")) (.-stdout x))
                 (.write_bytes (pathlib/Path raw (str name ".stderr")) (.-stderr x))
                 (chk (= (.-returncode x) want-exit) [name (.-returncode x) (tailb (.-stdout x) 300) (tailb (.-stderr x) 300)])
                 (when (some? stdout-is)
                   (chk (.startswith (.-stdout x) (operator/add stdout-is (b "{:status :ok :result 7 "))) [name (tailb (.-stdout x) 300)]))
                 (doseq [s stderr-has] (chk (u/has-bytes? s (.-stderr x)) [name s (tailb (.-stderr x) 300)]))
                 (.append rows (pyenv "name" name "args" (python/list args) "exit" (.-returncode x)
                                      "stdout" (headdec (.-stdout x) 400) "stderr" (headdec (.-stderr x) 400)))))
        fs-env (pyenv "KEXE_ALLOW" "35,37,38" "KEXE_CAP_RESOURCES_35" (str scope))
        rd (fn [p] (.read_bytes p))]
    (case "replace-and-refusals" (compile- producer "replace" (fs-guest scope outside) target) fs-env :stdout-is (b "1|1|hello|0|1|new|1|a|1|0|0|0|0|1|"))
    (chk (and (u/deq (rd (pathlib/Path scope "final")) (b "hello")) (not (.exists (pathlib/Path scope "tmp"))) (not (.exists (pathlib/Path outside "stolen")))) "replace result")
    (chk (and (u/deq (rd (pathlib/Path scope "old")) (b "new")) (not (.exists (pathlib/Path scope "new"))) (u/deq (rd (pathlib/Path scope "b")) (b "a"))) "rename results")
    (let [unlink-scope (pathlib/Path output "unlink-scope") unlink-outside (pathlib/Path output "unlink-outside")
          _ (do (.mkdir unlink-scope) (.mkdir unlink-outside))
          _ (.write_text (pathlib/Path unlink-scope "remove-me") "inside")
          _ (.write_text (pathlib/Path unlink-outside "outside-file") "outside")
          _ (.write_text (pathlib/Path unlink-outside "parent-target") "outside-parent")
          _ (os/symlink unlink-outside (pathlib/Path unlink-scope "parent-link") ** :target_is_directory true)
          _ (os/symlink (pathlib/Path unlink-outside "outside-file") (pathlib/Path unlink-scope "final-link"))
          unlink-env (pyenv "KEXE_ALLOW" "35,37,38" "KEXE_CAP_RESOURCES_35" (str unlink-scope))
          unlink (compile- producer "unlink" (unlink-guest unlink-scope unlink-outside) target)]
      (case "unlink-positive-absent-outside-symlink" unlink unlink-env :stdout-is (b "1|0|0|0|0|1|0|"))
      (chk (and (not (.exists (pathlib/Path unlink-scope "remove-me"))) (not (.exists (pathlib/Path unlink-scope "final-link")))) "unlink effects")
      (chk (and (= (.read_text (pathlib/Path unlink-outside "outside-file")) "outside") (= (.read_text (pathlib/Path unlink-outside "parent-target")) "outside-parent")) "outside untouched")
      (let [ungranted (compile- producer "unlink-ungranted" (unlink-guest unlink-scope unlink-outside) target)]
        (case "unlink-wire-not-granted" ungranted (pyenv "KEXE_ALLOW" "37,38" "KEXE_CAP_RESOURCES_35" (str unlink-scope))
              :want-exit 120 :stderr-has [sigill (b "KEXE_CAP {:wire 35 :refused :not-granted}\n")]))
      (case "unlink-malformed-duplicate-token" (compile- producer "unlink-malformed" src-unlink-malformed target) unlink-env :want-exit 120 :stderr-has [sigill]))
    (let [fsync-one (compile- producer "fsync-one" src-fsync-only target)]
      (case "fsync-trailing-bytes" fsync-one fs-env :args [(str scope "/finalFSYNC_SEPx")] :want-exit 120 :stderr-has [sigill]))
    (let [clock-env (pyenv "KEXE_ALLOW" "7,37,38")]
      (case "sleep" (compile- producer "sleep" src-sleep target) clock-env :stdout-is (b "slept|ok|"))
      (let [req (compile- producer "sleep-request" src-sleep-req target)]
        (doseq [[name arg] [["sleep-over-60000" "sleep 60001"] ["sleep-not-decimal" "sleep 1x"] ["sleep-no-number" "sleep "]]]
          (case name req clock-env :args [arg] :want-exit 120 :stderr-has [sigill]))
        (case "sleep-wire-not-granted" req (pyenv "KEXE_ALLOW" "37,38") :args ["sleep 1"] :want-exit 120
              :stderr-has [sigill (b "KEXE_CAP {:wire 7 :refused :not-granted}\n")]))
      (let [host (get {"aarch64" "aarch64-linux" "arm64" "aarch64-linux" "x86_64" "x86_64-linux" "AMD64" "x86_64-linux"} (platform/machine))
            [text unity-pins] (unity-text)
            no-fsync (compile- producer "control-compiler-no-fsync-rule" (patched text no-fsync-rule) host)
            no-sleep (compile- producer "control-compiler-no-sleep-rule" (patched text no-sleep-rule) host)
            enforced (not seccomp?)]
        (when enforced
          (.write_bytes (pathlib/Path scope "ctl") (b "x"))
          (case "control-no-fsync-rule" (compile- no-fsync "control-fsync" src-fsync-only target) fs-env :args [(str scope "/ctlFSYNC_SEP")] :want-exit 120 :stderr-has [(b ":signal :SIGSYS")])
          (case "control-no-sleep-rule" (compile- no-sleep "control-sleep" src-sleep-req target) clock-env :args ["sleep 10"] :want-exit 120 :stderr-has [(b ":signal :SIGSYS")]))
        (let [report (pyenv "status" "PASS_DURABLE_SLEEP_RUNTIME" "target" target "compiler" (pin compiler)
                            "host" (python/list [(platform/system) (platform/machine) (platform/release)])
                            "imageSeccomp" (if seccomp? "if-available" "required") "cases" rows
                            "controlCompilers" (pyenv "no-fsync-rule" (pyenv "mutation" "no fsync in the scope's seccomp set, in both runtimes" "pin" (pin no-fsync))
                                                      "no-sleep-rule" (pyenv "mutation" "no clock_nanosleep; current restart_syscall retained, in both runtimes" "pin" (pin no-sleep)))
                            "unity" unity-pins "cCompilerOrLoader" false
                            "notCovered" (python/list (concat ["durability across a power cut: fsync returning is what is checked, not the device"
                                                               "a sleep interrupted by a signal (EINTR resumes it with the remaining time)"]
                                                              (when-not enforced ["the seccomp controls: this kernel does not enforce seccomp (KEXE_SECCOMP=if-available)"]))))]
          (.write_text (pathlib/Path output "durable-sleep.json") (u/json-dump report))
          (println (g report "status") target (python/len rows) "cases")
          (.flush sys/stdout))))))

(defn -main [& args]
  (let [target (or (u/opt args "--target") "aarch64-linux")]
    (when-not (#{"aarch64-linux" "x86_64-linux"} target) (sys/exit "--target must be aarch64-linux or x86_64-linux"))
    (run (.resolve (pathlib/Path (or (u/opt args "--compiler") (sys/exit "--compiler is required"))))
         (.resolve (pathlib/Path (or (u/opt args "--output") (sys/exit "--output is required"))))
         target (boolean (some #{"--seccomp-if-available"} args)))))

(when (some #(or (= % "check-durable-sleep.cljc") (str/ends-with? % "/check-durable-sleep.cljc")) sys/argv)
  (apply -main *command-line-args*))
