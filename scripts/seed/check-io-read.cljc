;; The static runtime's wire 41 (:io/read): a static image reads its stdin. Linear JUN-354. Ported from
;; check-io-read.py (Basilisp, JUN-974); the Python docstring has the full four-part contract (to end of file,
;; in pieces, traps, and the sandbox control compiler whose seccomp filter has no read(0) rule).
;; Run (Linux): basilisp run -p scripts/seed scripts/seed/check-io-read.cljc -- --compiler F --output DIR
;;      [--target aarch64-linux|x86_64-linux] [--seccomp-if-available]
(ns check-io-read
  (:require [basilisp.string :as str]
            [gate-util :as u])
  (:import json operator pathlib platform subprocess sys))

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

(def src-head "(ns t (:export [main]))\n(defn- rd [s :string] :string (typed-cap-call :io/read :string :string s))\n(defn- say [s :string] :i64 (let [x (typed-cap-call :io/write :string :string s)] 0))\n")
(def src-all "(ns t (:export [main]))\n(defn- rd [s :string] :string (typed-cap-call :io/read :string :string s))\n(defn- say [s :string] :i64 (let [x (typed-cap-call :io/write :string :string s)] 0))\n(defn main [] :i64 (let [a (say (rd \"\"))] 7))\n")
(def src-twice "(ns t (:export [main]))\n(defn- rd [s :string] :string (typed-cap-call :io/read :string :string s))\n(defn- say [s :string] :i64 (let [x (typed-cap-call :io/write :string :string s)] 0))\n(defn main [] :i64 (let [a (say (rd \"\")) b (say \"|\") c (say (rd \"\")) d (say \"|\")] 7))\n")
(def src-length "(ns t (:export [main]))\n(defn- rd [s :string] :string (typed-cap-call :io/read :string :string s))\n(defn- say [s :string] :i64 (let [x (typed-cap-call :io/write :string :string s)] 0))\n(defn main [] :i64 (let [a (say (string-from-i64 (string-byte-length (rd \"\"))))] 7))\n")
(def src-pieces "(ns t (:export [main]))\n(defn- rd [s :string] :string (typed-cap-call :io/read :string :string s))\n(defn- say [s :string] :i64 (let [x (typed-cap-call :io/write :string :string s)] 0))\n(defn- pieces [k :i64] :i64 (let [s (rd \"2\")] (if (= s \"\") k (let [a (say s) b (say \"|\")] (pieces (+ k 1))))))\n(defn main [] :i64 (let [n (pieces 0)] 7))\n")
(def src-zero "(ns t (:export [main]))\n(defn- rd [s :string] :string (typed-cap-call :io/read :string :string s))\n(defn- say [s :string] :i64 (let [x (typed-cap-call :io/write :string :string s)] 0))\n(defn main [] :i64 (let [a (say \"[\") b (say (rd \"0\")) c (say \"]\")] 7))\n")
(def src-malformed "(ns t (:export [main]))\n(defn- rd [s :string] :string (typed-cap-call :io/read :string :string s))\n(defn- say [s :string] :i64 (let [x (typed-cap-call :io/write :string :string s)] 0))\n(defn main [] :i64 (let [a (say (rd \"x\"))] 7))\n")
(def no-read0-old "        i7 (if (kxrt-admitted? 41) (kxrt-allow-read-fd p i6 0) i6)\n")
(def no-read0-new "        i7 i6\n")

(defn unity-text []
  (let [paths (vec (filter #(and (seq %) (not (.startswith % "#"))) (.splitlines (.read_text (rp selfhost)))))]
    [(apply str (map #(str (.read_text (rp %)) "\n") paths))
     (u/pydict-from (for [p (cons selfhost paths)] [p (pin (rp p))]))]))

(defn patched [text old new n]
  (chk (= (.count text old) n) ["patch anchor" (subs old 0 (min 60 (count old))) (.count text old)])
  (.replace text old new))

(defn run [compiler output target seccomp?]
  (chk (= (platform/system) "Linux") "run on Linux")
  (.mkdir output ** :parents true :exist_ok false)
  (let [art (pathlib/Path output "artifacts") raw (pathlib/Path output "raw")
        _ (do (.mkdir art) (.mkdir raw))
        producer (pathlib/Path art "compiler.elf")
        _ (.write_bytes producer (.read_bytes compiler))
        _ (.chmod producer 0755)
        base-env (let [d (pyenv "PATH" "/usr/bin:/bin" "KEXE_STRUCTURED_REPORT" "1" "KEXE_FUEL" fuel "KEXE_ALLOW" "37,41")]
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
        case (fn [name elf data & {:keys [via env want-exit stdout-is stderr-has stderr-lacks] :or {via "file" want-exit 0 stderr-has [] stderr-lacks []}}]
               (let [e (let [d (python/dict base-env)] (when env (.update d env)) d)
                     x (if (= via "file")
                         (let [f (pathlib/Path art (str name ".stdin"))]
                           (.write_bytes f data)
                           (with-open [fh (.open f "rb")]
                             (subprocess/run (python/list [(str elf)]) ** :stdin fh :env e :capture_output true :timeout 120)))
                         (subprocess/run (python/list [(str elf)]) ** :input data :env e :capture_output true :timeout 120))]
                 (.write_bytes (pathlib/Path raw (str name ".stdout")) (.-stdout x))
                 (.write_bytes (pathlib/Path raw (str name ".stderr")) (.-stderr x))
                 (chk (= (.-returncode x) want-exit) [name (.-returncode x) (tailb (.-stdout x) 300) (tailb (.-stderr x) 300)])
                 (when (some? stdout-is)
                   (chk (.startswith (.-stdout x) (operator/add stdout-is (b "{:status :ok :result 7 "))) [name (tailb (.-stdout x) 300)]))
                 (doseq [s stderr-has] (chk (u/has-bytes? s (.-stderr x)) [name s (tailb (.-stderr x) 300)]))
                 (doseq [s stderr-lacks] (chk (not (u/has-bytes? s (.-stderr x))) [name s (tailb (.-stderr x) 300)]))
                 (.append rows (pyenv "name" name "via" via "stdinBytes" (python/len data) "exit" (.-returncode x)
                                      "stdout" (headdec (.-stdout x) 400) "stderr" (headdec (.-stderr x) 400)))))
        text-in (b "hello\nこんにちは\n")
        all- (compile- producer "all" src-all target)]
    (case "all-from-file" all- text-in :stdout-is text-in)
    (case "all-from-pipe" all- text-in :via "pipe" :stdout-is text-in)
    (case "all-empty" all- (u/bytes-of) :stdout-is (u/bytes-of))
    (case "twice" (compile- producer "twice" src-twice target) (b "hello") :stdout-is (b "hello||"))
    (case "two-mib" (compile- producer "length" src-length target) (b (operator/mul "x" 2097152)) :stdout-is (b "2097152"))
    (let [pieces (compile- producer "pieces" src-pieces target)]
      (case "pieces-complete-characters" pieces (b "aこんb") :stdout-is (b "aこ|ん|b|"))
      (case "pieces-ascii" pieces (b "abcde") :stdout-is (b "ab|cd|e|")))
    (case "zero" (compile- producer "zero" src-zero target) (b "abc") :stdout-is (b "[]"))
    (let [sigill (b ":signal :SIGILL")
          named (b "KEXE_CAP {:wire 41 :refused :not-granted}\n")]
      (case "not-utf8" all- (u/bytes-of 0xff 0xfe) :want-exit 120 :stderr-has [sigill])
      ;; an ungranted wire is refused by name (KEXE_CAP, as seed/82 does); a granted wire's bad request is not
      (case "malformed-request" (compile- producer "malformed" src-malformed target) (b "abc") :want-exit 120 :stderr-has [sigill] :stderr-lacks [(b "KEXE_CAP")])
      (case "wire-not-granted" all- (b "abc") :env (pyenv "KEXE_ALLOW" "37") :want-exit 120 :stderr-has [sigill named]))
    (let [host (get {"aarch64" "aarch64-linux" "arm64" "aarch64-linux" "x86_64" "x86_64-linux" "AMD64" "x86_64-linux"} (platform/machine))
          [text unity-pins] (unity-text)
          control (compile- producer "control-compiler-no-read0-rule" (patched text no-read0-old no-read0-new 2) host)
          enforced (not seccomp?)]
      (when enforced
        (case "control-no-read0-rule" (compile- control "control-all" src-all target) (b "abc") :want-exit 120 :stderr-has [(b ":signal :SIGSYS")]))
      (let [report (pyenv "status" "PASS_IO_READ_RUNTIME" "target" target "compiler" (pin compiler)
                          "host" (python/list [(platform/system) (platform/machine) (platform/release)])
                          "imageSeccomp" (if seccomp? "if-available" "required") "cases" rows
                          "controlCompiler" (pyenv "mutation" "no read(0) rule in the seccomp filter, in both runtimes" "pin" (pin control))
                          "unity" unity-pins "cCompilerOrLoader" false
                          "notCovered" (python/list (concat ["a read that fails with an error other than EINTR (EBADF, EIO)"
                                                             "stdin closed in the middle of a UTF-8 sequence that a piece read completes"]
                                                            (when-not enforced ["control-no-read0-rule: this kernel does not enforce seccomp (KEXE_SECCOMP=if-available)"]))))]
        (.write_text (pathlib/Path output "io-read.json") (str (json/dumps report ** :indent 2 :ensure_ascii false) "\n"))
        (println (g report "status") target (python/len rows) "cases")
        (.flush sys/stdout)))))

(defn -main [& args]
  (let [target (or (u/opt args "--target") "aarch64-linux")]
    (when-not (#{"aarch64-linux" "x86_64-linux"} target) (sys/exit "--target must be aarch64-linux or x86_64-linux"))
    (run (.resolve (pathlib/Path (or (u/opt args "--compiler") (sys/exit "--compiler is required"))))
         (.resolve (pathlib/Path (or (u/opt args "--output") (sys/exit "--output is required"))))
         target (boolean (some #{"--seccomp-if-available"} args)))))

(when (some #(or (= % "check-io-read.cljc") (str/ends-with? % "/check-io-read.cljc")) sys/argv)
  (apply -main *command-line-args*))
