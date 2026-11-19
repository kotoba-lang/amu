;; Loaderless Amu selfhost bootstrap on arm64 Linux. No C compiler or C loader.
;;
;; The pinned root (seed/bootstrap/aarch64-linux-static-root.elf) is F, the combined compiler (seed/FULL-MANIFEST)
;; packed as a static image. Tiers (--tier) say how much is re-derived: pr (F rebuilds itself to a fixed point; F's
;; Linux targets; F's core route and refusals; runtime boundary corpus, runtime cases, hardening, capabilities),
;; main (+ G2/G3 through the runner, packed core P, the Linux selfhost closure S = S') and full (+ the deep
;; provenance C0/Kw/Pw from source). --wasm32-browser --bootstrap BOOT compiles the runtime cases and probes as
;; wasm32-browser modules with the fixed point F of a passing native bootstrap output (KOTOBA-174).
;; Orchestrates processes and hashes only. Ported from selfhost-bootstrap.py (Basilisp, JUN-974); the Python
;; docstring has the full tier contract. check-runtime-boundary, check-net-runtime and check-spawn-runtime (all Basilisp now) and
;; check-wasm32-browser stay Python and are launched as subprocesses.
;; Library: content_reuse.cljc (named here so the CI derivation closure covers it).
;; Run (arm64 Linux): basilisp run -p scripts/seed scripts/seed/selfhost-bootstrap.cljc -- --output OUT --tier pr
(ns selfhost-bootstrap
  (:require [basilisp.string :as str]
            [content-reuse :as cr]
            [gate-util :as u])
  (:import hashlib json operator os pathlib platform re shutil sys))

(def root u/root)
(defn rp [rel] (pathlib/Path root rel))
(def selfhost "seed/X86_64-LINUX-SELFHOST-MANIFEST")
(def full "seed/FULL-MANIFEST")
(def tiers ["pr" "main" "full"])
(def adopted "seed/MANIFEST")
(def root-image "seed/bootstrap/aarch64-linux-static-root.elf")
(def root-receipt-path "seed/bootstrap/aarch64-linux-static-root.json")
(def core-static "seed/CORE-STATIC-MANIFEST")
(def ns- "seed/00-ns.kotoba")
(def ns-static "seed/00-ns-static.kotoba")
(def runner-src "seed/x86_64-kx64-runner.kotoba")
(def cases-path "seed/static-cases.json")
(def float-cases-path "seed/float-cases.json")
(def wasm-check "scripts/seed/check-wasm32-browser.py")
(def static-capacities
  (re/compile (.encode "\\(def MM-(WORDS|(TOK|NODE|SIR|CODE|FIX|LITB|OUT)-CAP|(NODE|SYM|HASH|FN|SCOPE|SIR|LABEL|CODE|FIX|LIT|LITB|EXP|OUT|HEAP)-BASE|HEAP-END) [0-9]+\\)")))
(def adopted-stack "8388608")

(defn g [m & ks] (reduce (fn [a k] (operator/getitem a k)) m ks))
(defn has? [m k] (operator/contains m k))
(defn put! [m k v] (operator/setitem m k v) m)
(defn pin [p] (cr/pin p))
(defn read-json [p] (json/loads (.read_text (pathlib/Path p))))
(defn chk [c m] (u/chk c m))
(defn lines-of [m] (vec (filter #(and (seq %) (not (.startswith % "#"))) (.splitlines (.read_text (rp m))))))
(defn pyenv [& kvs] (apply u/pydict kvs))
(defn out-path [out n] (pathlib/Path out n))
(defn host-triple [] (python/list [(platform/system) (platform/machine) (platform/release)]))
(defn arm64-linux? [] (and (= (platform/system) "Linux") (contains? #{"aarch64" "arm64"} (platform/machine))))
(defn b [s] (.encode s))
(defn bhas? [needle hay] (u/has-bytes? (b needle) hay))
(defn dec- [bs] (.decode bs "utf-8" "replace"))

(defn unity
  "Write the concatenated manifest sources to dst; {path pin} for the manifest and every source."
  [manifest dst]
  (let [paths (lines-of manifest)]
    (.write_bytes dst (.join (u/bytes-of) (python/list (map #(operator/add (.read_bytes (rp %)) (u/bytes-of 10)) paths))))
    (u/pydict-from (for [p (cons manifest paths)] [p (pin (rp p))]))))

(defn strip-static [raw]
  (.sub static-capacities (u/bytes-of)
        (.join (u/bytes-of)
               (python/list (filter (fn [line] (not (.startswith line (python/tuple [(b ";; seed/00-ns-static") (b ";; CORE-STATIC") (b ";; (CODE, FIX") (b ";; (TOK, CODE, FIX")]))))
                                    (.splitlines raw true))))))

(defn constants [raw]
  (into {} (for [m (re/findall (b "\\(def (MM-[A-Z0-9-]+) ([0-9]+)\\)") raw)]
             [(.decode (operator/getitem m 0)) (python/int (operator/getitem m 1))])))

(defn static-capacity-layout []
  (let [normal (.read_bytes (rp ns-)) static (.read_bytes (rp ns-static))
        a (constants normal) bb (constants static)
        overrides {"TOK" 1048576 "NODE" 786432 "SIR" 589824 "CODE" 2097152 "FIX" 262144 "LITB" 1048576 "OUT" 12582912}
        regions (str/split "TOK NODE SYM HASH FN SCOPE SIR LABEL CODE FIX LIT LITB EXP OUT" #" ")]
    (chk (= (set (keys a)) (set (keys bb))) "static constant names")
    (doseq [name regions]
      (chk (= (bb (str "MM-" name "-W")) (a (str "MM-" name "-W"))) "region width")
      (chk (= (bb (str "MM-" name "-CAP")) (get overrides name (a (str "MM-" name "-CAP")))) "region capacity"))
    (doseq [layout [a bb]]
      (let [next-base (reduce (fn [nb name]
                                (chk (= (layout (str "MM-" name "-BASE")) nb) (str name " overlap or gap"))
                                (+ nb (* (layout (str "MM-" name "-W")) (layout (str "MM-" name "-CAP")))))
                              256 regions)]
        (chk (= (layout "MM-HEAP-BASE") next-base) "heap base")
        (chk (and (= (layout "MM-HEAP-END") (layout "MM-WORDS")) (< (layout "MM-WORDS") (python/pow 2 25))) "heap end")))
    (chk (= (- (a "MM-HEAP-END") (a "MM-HEAP-BASE")) (- (bb "MM-HEAP-END") (bb "MM-HEAP-BASE"))) "heap changed")
    (chk (u/deq (strip-static normal) (strip-static static)) "static source differs beyond checked capacities")
    (u/pydict "words" (bb "MM-WORDS") "tokenCapacity" (bb "MM-TOK-CAP") "nodeCapacity" (bb "MM-NODE-CAP")
              "literalBytes" (bb "MM-LITB-CAP") "outputBytes" (bb "MM-OUT-CAP") "heapWords" (- (bb "MM-HEAP-END") (bb "MM-HEAP-BASE")))))

(def wasm-probes
  [["spin" "(defn main [] :i64 (loop [i 0] (if (< i 0) i (recur (inc i)))))"]
   ["deep" "(defn- f [n :i64] :i64 (if (= n 0) 0 (+ 1 (f (dec n)))))\n(defn main [] :i64 (f 100000000))"]
   ["local-stdio" "(defn main [] :i64\n  (let [hello (typed-cap-call :io/write :string :string \"READY\\n\")\n        flush (typed-cap-call :io/write-error :string :string \"\")\n        first (typed-cap-call :io/read :string :string \"1\")\n        second (typed-cap-call :io/read :string :string \"1\")\n        eof (typed-cap-call :io/read :string :string \"1\")\n        done (typed-cap-call :io/write :string :string \"DONE\\n\")]\n    (if (and (string=? first \"😀\") (string=? second \"x\") (string=? eof \"\")) 42 1)))"]
   ["local-output-bound" (str "(defn main [] :i64 (let [x (typed-cap-call :io/write :string :string \"" (apply str (repeat 70000 "x")) "\")] 42))")]
   ["local-read-bound" "(defn main [] :i64 (loop [i 0] (if (= i 257) 42 (let [x (typed-cap-call :io/read :string :string \"1\")] (recur (+ i 1))))))"]
   ["local-read-all" "(defn main [] :i64 (let [x (typed-cap-call :io/read :string :string \"\")] (if (string=? x \"😀x\") 42 1)))"]
   ["local-broker-isolation" "(defn main [] :i64 (let [r (typed-cap-call :net/dial :string :string \"GET /v1/items/abc\") x (typed-cap-call :io/write :string :string (string-concat r \"\\n\"))] (string-byte-length r)))"]
   ["document" "(defn- verify-keywords [i :i64] :i64\n  (if (= i 200) 1 (let [name (string-concat \"dynamic-\" (string-from-i64 i))\n    k (keyword-from-string name)]\n    (if (string=? (keyword-name k) name) (verify-keywords (+ i 1)) 0))))\n(defn main [] :i64 (let [k (keyword-from-string \"remote/識別\")\n  d (document-map k (document-string \"言葉\"))\n  v (option-or (document-get d k) (document-null))]\n  (if (and (= (verify-keywords 0) 1) (string=? (keyword-name k) \"識別\")\n           (string=? (option-or (document-string-value v) \"\") \"言葉\")) 2 0)))"]
   ["entry" "(defn main [] :i64 (let [p (typed-cap-call :cli/args :string :string \"0\")\n  s (typed-cap-call :fs/app-data :string :string p) w (typed-cap-call :io/write :string :string s)]\n  (string-length s)))"]
   ["cap" "(defn main [] :i64 (let [r (typed-cap-call :net/dial :string :string \"GET /v1/items/abc\")\n  w (typed-cap-call :io/write :string :string r)]\n  (string-length r)))"]
   ["cap-twice" "(defn main [] :i64 (let [a (typed-cap-call :net/dial :string :string \"GET /v1/items/abc\")\n  w (typed-cap-call :io/write :string :string a)\n  b (typed-cap-call :net/dial :string :string \"GET /v1/items/abc\")\n  x (typed-cap-call :io/write :string :string b)]\n  (+ (string-length a) (string-length b))))"]])

(defn main [out tier reuse store]
  (chk (arm64-linux?) "run on arm64 Linux")
  (let [level (.index (python/list tiers) tier)
        static-profile (static-capacity-layout)
        _ (.mkdir out ** :parents true :exist_ok false)
        run (cr/runs out reuse store)
        scope (pyenv "KEXE_CAP_RESOURCES_35" (str out))
        senv (let [d (python/dict scope)] (put! d "KEXE_STACK_BYTES" adopted-stack) d)
        root-receipt (read-json (rp root-receipt-path))
        _ (chk (u/deq (pin (rp root-image)) (g root-receipt "image")) "pinned root image mismatch")
        o (fn [n] (out-path out n))
        _ (.write_bytes (o "root.elf") (.read_bytes (rp root-image)))
        _ (.chmod (o "root.elf") 0755)
        _ (.write_bytes (o "runner.kotoba") (.read_bytes (rp runner-src)))
        runner (o "runner.kotoba")
        full-src (o "full-unity.kotoba") source (o "selfhost-unity.kotoba") adopted-src (o "adopted-unity.kotoba")
        full-pins (unity full full-src) source-pins (unity selfhost source) adopted-pins (unity adopted adopted-src)
        core (vec (for [p (lines-of adopted) :when (not= p "seed/99-entry.kotoba")] (.replace p ns- ns-static)))
        _ (chk (= (vec (take (count core) (lines-of full))) core) "FULL-MANIFEST's core section differs from seed/MANIFEST")
        adoption-doc (read-json (rp (g (read-json (rp "seed/compiler-core.json")) "adoptionReceipt")))
        _ (chk (= (g (pin adopted-src) "sha256") (g adoption-doc "sourceUnitySHA256")) "adopted source drift")
        compile- (fn [prod src dst target fmt name & [env]]
                   (cr/run run name (concat [prod "compile" src "--target" target "--output" dst] (when fmt ["--format" fmt])) (or env senv))
                   (when fmt (.chmod dst 0755))
                   (pin dst))
        pack (fn [prod kseed dst name]
               (cr/run run name [prod "compile" runner "--target" "aarch64-linux" "--output" dst "--format" "packed" "--payload" kseed] senv)
               (.chmod dst 0755)
               (pin dst))
        generation (fn [i producer]
                     (u/pydict "name" (str "F" i)
                               "container" (compile- producer full-src (o (str "F" i ".kseed")) "aarch64-macos" nil (str "F" i "-compile"))
                               "image" (pack producer (o (str "F" i ".kseed")) (o (str "F" i ".elf")) (str "F" i "-pack"))))
        gens (atom [(generation 1 (o "root.elf"))])
        root-reproduces (u/deq (g (first @gens) "image") (pin (rp root-image)))]
    ;; 1. F rebuilds itself until an image reproduces itself
    (loop [converged root-reproduces]
      (when-not converged
        (chk (< (count @gens) 4) "combined compiler fixed point not reached")
        (swap! gens conj (generation (inc (count @gens)) (o (str "F" (count @gens) ".elf"))))
        (let [cur (peek @gens) prev (peek (pop @gens))
              prev2 (let [d (python/dict prev)] (put! d "name" (g cur "name")) d)]
          (recur (u/deq cur prev2)))))
    (let [F (o (str "F" (count @gens) ".elf"))
          ;; 2. F's Linux targets
          built (u/pydict "aarch64Runner" (compile- F runner (o "R-aarch64.elf") "aarch64-linux" "runner" "R-aarch64" senv)
                          "x86_64Compiler" (compile- F source (o "S-x86_64.elf") "x86_64-linux" "static" "S-x86_64" senv)
                          "x86_64Runner" (compile- F runner (o "R-x86_64.elf") "x86_64-linux" "kx64-runner" "R-x86_64" senv))]
      ;; 3. F's core route, the packed refusal and a named diagnostic
      (compile- F adopted-src (o "G1.kseed") "aarch64-macos" nil "G1-compile")
      (cr/run run "G1-extract" [F "extract-native" (o "G1.kseed") "--symbol" "main" "--output" (o "G1.bin")] senv)
      (chk (= (g (pin (o "G1.bin")) "sha256") (g adoption-doc "nativeImageSHA256")) "F's core route differs from the adoption image")
      (let [adopted-gens (atom [(u/pydict "generation" 1 "producedBy" "F" "native" (pin (o "G1.bin")) "container" (pin (o "G1.kseed")))])]
        (.write_text (o "arity1.kotoba") "(ns arity1 (:export [main]))\n(defn main [x :i64] :i64 x)\n")
        (compile- F (o "arity1.kotoba") (o "arity1.kseed") "aarch64-macos" nil "arity1-compile")
        (let [r (cr/run run "arity1-pack" [F "compile" runner "--target" "aarch64-linux" "--output" (o "arity1.elf") "--format" "packed" "--payload" (o "arity1.kseed")]
                        senv :success false)]
          (chk (and (= (.-returncode r) 1) (bhas? "E7105" (.-stderr r)) (not (.exists (o "arity1.elf")))) "packed arity refusal")
          (let [arity-refusal (u/pydict "exit" (.-returncode r) "stderr" (.strip (.decode (.-stderr r))))]
            ;; JUN-334: a diagnostic with a source span reads the whole file
            (.write_text (o "undefined.kotoba") "(ns undefined (:export [main]))\n(defn main [] :i64 (nope-fn))\n")
            (let [r (cr/run run "diagnostic-span" [F "check" (o "undefined.kotoba")] senv :success false)]
              (chk (and (= (.-returncode r) 1) (bhas? "E2101 unknown or unsupported form 'nope-fn'" (.-stderr r)))
                   (str ["named diagnostic" (.-returncode r) (dec- (u/bslice (.-stderr r) (max 0 (- (python/len (.-stderr r)) 300)) (python/len (.-stderr r))))]))
              (let [diagnostic (u/pydict "exit" (.-returncode r) "stderr" (.strip (.decode (.-stderr r))))]
                ;; JUN-325: the shared call/function-value boundary corpus through F
                (cr/run run "runtime-boundary" [(str (pathlib/Path (.-parent (pathlib/Path sys/executable)) "basilisp")) "run" "-p" (rp "scripts/seed")
                                                (rp "scripts/seed/check-runtime-boundary.cljc") "--" "--compiler" F
                                                "--output" (o "runtime-boundary") "--payload" (o "G1.kseed")]
                        (pyenv "AMU_ROOT" (str root)))
                (let [runtime-boundary (read-json (o "runtime-boundary/runtime-boundary.json"))
                      ;; 4. runtime cases as static images against the pinned loader results
                      results (atom [])]
                  (doseq [case (g (read-json (rp cases-path)) "cases")]
                    (let [n (g case "name")
                          src (o (str "case-" n ".kotoba"))]
                      (.write_text src (g case "source"))
                      (compile- F src (o (str "case-" n ".elf")) "aarch64-linux" "static" (str "case-" n "-compile") senv)
                      (let [r (cr/run run (str "case-" n) [(o (str "case-" n ".elf"))]
                                      (pyenv "KEXE_STRUCTURED_REPORT" "1" "KEXE_FUEL" "1000000" "KEXE_ALLOW" "-") :success false)
                            fuel (re/search (b ":remaining ([0-9]+)") (.-stdout r))
                            observed (u/pydict "exit" (.-returncode r) "remainingFuel" (when fuel (python/int (.group fuel 1))))]
                        (chk (u/deq observed (g case "reference")) (str [n observed (g case "reference")]))
                        (if (g case "trap")
                          (chk (bhas? ":status :trap" (.-stdout r)) "trap status")
                          (chk (= (python/int (.group (re/search (b ":result (-?[0-9]+)") (.-stdout r)) 1)) (g case "result")) "case result"))
                        (swap! results conj (let [row (u/pydict "name" n)] (.update row observed) row)))))
                  ;; JUN-292: the native TCP/spawn acceptance corpus on the same bootstrap route
                  (let [io-acceptance (python/dict)]
                    (doseq [[name script] [["net-runtime" "check-net-runtime.cljc"] ["spawn-runtime" "check-spawn-runtime.cljc"]]]
                      ;; the Basilisp gates run through the basilisp executable beside this interpreter (the run's PATH is minimal);
                      ;; AMU_ROOT because the gate resolves the repository from its cwd, which is the output directory here
                      (cr/run run name [(str (pathlib/Path (.-parent (pathlib/Path sys/executable)) "basilisp")) "run" "-p" (rp "scripts/seed")
                                        (rp (str "scripts/seed/" script)) "--" "--compiler" F "--output" (o name)
                                        "--target" "aarch64-linux" "--seccomp-if-available"]
                              (pyenv "AMU_ROOT" (str root)))
                      (put! io-acceptance name (read-json (o (str name "/" name ".json")))))
                    ;; hardening, natively
                    (doseq [[name body] [["value" "(defn main [] :i64 42)"]
                                         ["spin" "(defn main [] :i64 (loop [i 0] (if (< i 0) i (recur (inc i)))))"]
                                         ["deep" "(defn- f [n :i64] :i64 (if (= n 0) 0 (+ 1 (f (dec n)))))\n(defn main [] :i64 (f 100000000))"]]]
                      (let [src (o (str "probe-" name ".kotoba"))]
                        (.write_text src (str "(ns probe-" name " (:export [main]))\n" body "\n"))
                        (compile- F src (o (str "probe-" name ".elf")) "aarch64-linux" "static" (str "probe-" name "-compile") senv)))
                    (let [observe (fn [name image env]
                                    (let [r (cr/run run (str "probe-" name) [(o (str "probe-" image ".elf"))]
                                                    (let [d (pyenv "KEXE_STRUCTURED_REPORT" "1")] (.update d env) d) :success false)]
                                      (u/pydict "exit" (.-returncode r) "stderr" (.strip (.decode (.-stderr r) "utf-8" "replace")))))
                          hardening (u/pydict "seccompDefault" (observe "seccomp-default" "value" (python/dict))
                                              "sandboxProbe" (observe "sandbox-probe" "value" (pyenv "KEXE_SANDBOX_PROBE" "1"))
                                              "cpuSeconds1" (observe "cpu" "spin" (pyenv "KEXE_CPU_SECONDS" "1"))
                                              "wallSeconds3" (observe "wall" "spin" (pyenv "KEXE_WALL_SECONDS" "3"))
                                              "stack1MiB" (observe "stack" "deep" (python/dict)))]
                      (chk (= (g hardening "seccompDefault" "exit") 0) "seccomp must install on this kernel")
                      (chk (and (= (g hardening "sandboxProbe" "exit") 120) (str/includes? (g hardening "sandboxProbe" "stderr") "SIGSYS")) "sandbox probe")
                      (chk (and (= (g hardening "cpuSeconds1" "exit") 120) (str/includes? (g hardening "cpuSeconds1" "stderr") "SIGXCPU")) "cpu probe")
                      (chk (and (= (g hardening "wallSeconds3" "exit") 120) (str/includes? (g hardening "wallSeconds3" "stderr") "SIGALRM")) "wall probe")
                      (chk (and (= (g hardening "stack1MiB" "exit") 120) (str/includes? (g hardening "stack1MiB" "stderr") "SIGSEGV")) "stack probe")
                      ;; capabilities: wire 3 and multiple KEXE_CAP_RESOURCES_35 roots
                      (let [roots [(o "cap-missing") (o "cap-a") (o "cap-b")]
                            _ (doseq [d (rest roots)] (.mkdir d))
                            vectors ["abc" "" (apply str (repeat 200 "x"))]
                            body (str/join "\n" (map-indexed (fn [i t] (str "(if (string=? (typed-cap-call :hash/sha256 :string :string \"" t "\") \""
                                                                            (u/sha256-hex (.encode t)) "\") " (bit-shift-left 1 i) " 0)")) vectors))
                            hash-src (pathlib/Path (nth roots 2) "hash.kotoba")
                            _ (.write_text hash-src (str "(ns hash-check (:export [main]))\n(defn main [] :i64 (+ " body "))\n"))
                            cap-env (pyenv "KEXE_CAP_RESOURCES_35" (str/join ":" (map str roots)))]
                        (cr/run run "cap-compile" [F "compile" hash-src "--target" "aarch64-linux" "--output" (pathlib/Path (nth roots 2) "hash.elf") "--format" "static"] cap-env)
                        (.chmod (pathlib/Path (nth roots 2) "hash.elf") 0755)
                        (let [granted (cr/run run "cap-hash-granted" [(pathlib/Path (nth roots 2) "hash.elf")] (pyenv "KEXE_ALLOW" "3") :success false)
                              refused (cr/run run "cap-hash-refused" [(pathlib/Path (nth roots 2) "hash.elf")] (pyenv "KEXE_ALLOW" "37") :success false)
                              outside (cr/run run "cap-outside-roots" [F "compile" hash-src "--target" "aarch64-linux" "--output" (pathlib/Path (nth roots 1) "x.elf") "--format" "static"]
                                              (pyenv "KEXE_CAP_RESOURCES_35" (str (nth roots 1))) :success false)]
                          (chk (= (.-returncode granted) 7) (str ["sha256 vectors" (.-returncode granted)]))
                          (chk (and (= (.-returncode refused) 120) (bhas? "SIGILL" (.-stderr refused))) "wire 3 refusal")
                          (chk (bhas? "KEXE_CAP {:wire 3 :refused :not-granted}\n" (.-stderr refused)) "wire 3 refusal text")
                          (chk (and (not= (.-returncode outside) 0) (not (.exists (pathlib/Path (nth roots 1) "x.elf")))) "outside roots")
                          (let [capabilities (u/pydict "sha256Vectors" (count vectors) "granted" (.-returncode granted) "refused" (.-returncode refused)
                                                       "scopeRoots" (count roots) "sourceUnderRoot" 3 "outsideRootsExit" (.-returncode outside))
                                packed (atom nil) closure (atom nil) provenance (atom nil)]
                            ;; main: the runner, the packed core and the Linux selfhost closure
                            (when (>= level 1)
                              (let [renv (pyenv "KEXE_CAP_RESOURCES_35" (str out) "KEXE_COMMAND" "1" "KEXE_STACK_BYTES" adopted-stack)]
                                (loop [payload (o "G1.bin") gs [2 3]]
                                  (when (seq gs)
                                    (let [gn (first gs)
                                          prefix [(o "R-aarch64.elf") payload 0 0 "aarch64" "35,37,38,39" "--"]
                                          container (o (str "G" gn ".kseed")) native (o (str "G" gn ".bin"))]
                                      (cr/run run (str "G" gn "-compile") (concat prefix ["compile" adopted-src "--target" "aarch64-macos" "--output" container]) renv)
                                      (cr/run run (str "G" gn "-extract") (concat prefix ["extract-native" container "--symbol" "main" "--output" native]) renv)
                                      (chk (= (g (pin native) "sha256") (g adoption-doc "nativeImageSHA256")) "adopted fixed point mismatch (runner)")
                                      (swap! adopted-gens conj (u/pydict "generation" gn "producedBy" "runner" "native" (pin native) "container" (pin container)))
                                      (recur native (rest gs))))))
                              (let [P (o "P-aarch64.elf")]
                                (pack F (o "G3.kseed") P "P-pack")
                                (compile- P adopted-src (o "P.kseed") "aarch64-macos" nil "P-compile")
                                (cr/run run "P-extract" [P "extract-native" (o "P.kseed") "--symbol" "main" "--output" (o "P.bin")] senv)
                                (chk (= (g (pin (o "P.bin")) "sha256") (g adoption-doc "nativeImageSHA256")) "packed compiler output mismatch")
                                (chk (u/deq (pin (o "P.kseed")) (g (peek @adopted-gens) "container")) "packed compiler container mismatch")
                                (reset! packed (u/pydict "image" (pin P) "container" (pin (o "P.kseed")) "native" (pin (o "P.bin")))))
                              (let [s1 (compile- F source (o "S.elf") "aarch64-linux" "static" "S" senv)
                                    s2 (compile- (o "S.elf") source (o "S2.elf") "aarch64-linux" "static" "S2" senv)]
                                (chk (u/deq s1 s2) "Linux selfhost closure fixed point mismatch")
                                (reset! closure (u/pydict "S" s1))))
                            ;; full: the deep provenance of the core from source
                            (when (>= level 2)
                              (chk (u/deq (strip-static (.read_bytes (rp ns-))) (strip-static (.read_bytes (rp ns-static)))) "00-ns-static differs from 00-ns beyond the static capacities")
                              (let [S (o "S.elf")
                                    core-static-src (o "core-static-unity.kotoba")
                                    core-static-pins (unity core-static core-static-src)
                                    c0 (compile- S core-static-src (o "C0.elf") "aarch64-linux" "static" "C0")]
                                (cr/run-cached run "C0-core" [(o "C0.elf") "compile" adopted-src "--target" "aarch64-macos" "--output" (o "C0-core.kseed")]
                                               senv [(o "C0-core.kseed")] :timeout 10800)
                                (cr/run-cached run "C0-extract" [(o "C0.elf") "extract-native" (o "C0-core.kseed") "--symbol" "main" "--output" (o "C0-core.bin")]
                                               senv [(o "C0-core.bin")] :timeout 3600)
                                (chk (= (g (pin (o "C0-core.bin")) "sha256") (g adoption-doc "nativeImageSHA256")) "C0's core differs from the adoption image")
                                (cr/run-cached run "C0-Kw" [(o "C0.elf") "compile" core-static-src "--target" "aarch64-macos" "--output" (o "Kw.kseed")]
                                               senv [(o "Kw.kseed")] :timeout 10800)
                                (let [pw (pack S (o "Kw.kseed") (o "Pw.elf") "Pw-pack")]
                                  (compile- (o "Pw.elf") full-src (o "Pw-F.kseed") "aarch64-macos" nil "Pw-F")
                                  (chk (u/deq (pin (o "Pw-F.kseed")) (g (peek @gens) "container")) "F from the C0 lineage differs from F")
                                  (reset! provenance (u/pydict "coreStatic" (u/pydict "sourceGraph" core-static-pins "C0" c0) "core" (pin (o "C0-core.bin"))
                                                               "Kw" (pin (o "Kw.kseed")) "Pw" pw "F" (pin (o "Pw-F.kseed")))))))
                            (let [calls (cr/calls run)
                                  report (u/pydict
                                          "status" "PASS_LOADERLESS_SELFHOST_BOOTSTRAP" "tier" tier "capabilities" capabilities "staticProfile" static-profile
                                          "host" (host-triple)
                                          "root" (u/pydict "image" (pin (rp root-image)) "receipt" root-receipt)
                                          "sourceGraph" (u/pydict "full" full-pins "selfhost" source-pins)
                                          "generations" (python/list @gens) "rootReproduces" root-reproduces
                                          "built" built
                                          "adopted" (u/pydict "sourceGraph" adopted-pins "runnerStackBytes" (python/int adopted-stack) "generations" (python/list @adopted-gens)
                                                              "packed" @packed "arityRefusal" arity-refusal "expectedNativeImage" (g adoption-doc "nativeImageSHA256"))
                                          "diagnostic" diagnostic "closure" @closure "provenance" @provenance
                                          "cases" (python/list @results) "ioAcceptance" io-acceptance
                                          "hardening" hardening "runtimeBoundary" runtime-boundary
                                          "steps" (python/list
                                                   (for [c calls]
                                                     (let [row (u/pydict "name" (g c "name") "seconds" (g c "seconds"))]
                                                       (if (has? c "reused")
                                                         (put! row "reused" (g c "reused"))
                                                         (do (put! row "ran" true) (when (has? c "key") (put! row "key" (g c "key")))))
                                                       row)))
                                          "reuse" (u/pydict "read" (boolean reuse) "store" (boolean store)
                                                            "reused" (python/list (for [c calls :when (has? c "reused")]
                                                                                    (let [row (u/pydict "name" (g c "name"))] (.update row (g c "reused")) row))))
                                          "cCompilerOrLoader" false "JVMNodeOrGraalFallback" false "emulation" false)]
                              (.write_text (o "selfhost-bootstrap.json") (u/json-dump report))
                              (println (g report "status") tier "F" (subs (g (peek @gens) "image" "sha256") 0 16)
                                       (if root-reproduces "root reproduces" (str "root differs (re-pin to F" (count @gens) ")"))
                                       "adoption image" (count @results) "cases"))))))))))))))))


(defn wasm32-browser [out boot]
  (chk (arm64-linux?) "run on arm64 Linux")
  (let [receipt (read-json (pathlib/Path boot "selfhost-bootstrap.json"))
        _ (chk (= (g receipt "status") "PASS_LOADERLESS_SELFHOST_BOOTSTRAP") "BOOT is not a passing native bootstrap")
        fixed (operator/getitem (g receipt "generations") -1)
        _ (chk (u/deq (pin (pathlib/Path boot (str (g fixed "name") ".elf"))) (g fixed "image")) "F differs from the native bootstrap receipt")
        _ (.mkdir out ** :parents true :exist_ok false)
        run (cr/runs out)
        scope (pyenv "KEXE_CAP_RESOURCES_35" (str out))
        senv (let [d (python/dict scope)] (put! d "KEXE_STACK_BYTES" adopted-stack) d)
        o (fn [n] (out-path out n))
        F (o "F.elf")
        _ (.write_bytes F (.read_bytes (pathlib/Path boot (str (g fixed "name") ".elf"))))
        _ (.chmod F 0755)
        compile- (fn [src dst name]
                   (cr/run run name [F "compile" src "--target" "wasm32-browser" "--output" dst] senv)
                   (pin dst))
        wasm-dir (o "wasm32")
        _ (.mkdir wasm-dir)
        cases (g (read-json (rp cases-path)) "cases")]
    (doseq [case cases]
      (let [n (g case "name") src (o (str "case-" n ".kotoba"))]
        (.write_text src (g case "source"))
        (compile- src (pathlib/Path wasm-dir (str "case-" n ".wasm")) (str "case-" n "-wasm32"))))
    (doseq [[name body] wasm-probes]
      (let [src (o (str "wasm-probe-" name ".kotoba"))]
        (.write_text src (str "(ns probe-" name " (:export [main]))\n" body "\n"))
        (compile- src (pathlib/Path wasm-dir (str "probe-" name ".wasm")) (str "probe-" name "-wasm32"))))
    ;; Single-source Wasm locks must be verified, not silently discarded.
    (let [src (o "wasm-probe-document.kotoba")
          source-lock (o "wasm-document.ksl")
          _ (.write_text source-lock (str "KSL1\nentry " src "\nfile " (g (pin src) "sha256") " " src "\n"))
          locked-wasm (o "wasm-document-locked.wasm")
          lock-args ["--source-lock" source-lock "--source-lock-sha256" (g (pin source-lock) "sha256")]]
      (cr/run run "wasm-document-locked" (concat [F "compile" src "--target" "wasm32-browser" "--output" locked-wasm] lock-args) senv)
      (chk (u/deq (pin locked-wasm) (pin (pathlib/Path wasm-dir "probe-document.wasm"))) "locked output changed")
      (let [bad-lock (o "wasm-document-bad-source.ksl")]
        (.write_text bad-lock (str "KSL1\nentry " src "\nfile " (apply str (repeat 64 "0")) " " src "\n"))
        (doseq [[name lock digest] [["bad-digest" source-lock (apply str (repeat 64 "0"))] ["bad-source" bad-lock (g (pin bad-lock) "sha256")]]]
          (let [refused (o (str "wasm-document-" name ".wasm"))
                r (cr/run run (str "wasm-document-" name) [F "compile" src "--target" "wasm32-browser" "--output" refused "--source-lock" lock "--source-lock-sha256" digest]
                          senv :success false)]
            (chk (and (not= (.-returncode r) 0) (bhas? "E6015" (.-stderr r)) (not (.exists refused))) (str [name (.-returncode r)])))))
      (doseq [[name flags marker] [["missing-digest" ["--source-lock" source-lock] "E7100"]
                                   ["project-roots" (concat lock-args ["--source-path" out]) "E6015"]]]
        (let [refused (o (str "wasm-document-" name ".wasm"))
              r (cr/run run (str "wasm-document-" name) (concat [F "compile" src "--target" "wasm32-browser" "--output" refused] flags) senv :success false)]
          (chk (and (not= (.-returncode r) 0) (bhas? marker (.-stderr r)) (not (.exists refused))) (str [name (.-returncode r)])))))
    (let [float-refusals (atom [])]
      (doseq [case (g (read-json (rp float-cases-path)) "cases")]
        (let [n (g case "name") src (o (str "float-" n ".kotoba"))
              target (pathlib/Path wasm-dir (str "float-" n ".wasm"))]
          (.write_text src (g case "source"))
          (let [r (cr/run run (str "float-" n "-wasm32") [F "compile" src "--target" "wasm32-browser" "--output" target] scope :success false)
                detail (get {"float-f32-conv" 34 "float-f64-unordered" 19} n (g case "refusalDetail"))]
            (chk (and (= (.-returncode r) 1) (bhas? "E7101" (.-stderr r)) (bhas? (str "detail " detail) (.-stderr r)) (not (.exists target)))
                 (str ["wasm32 float refusal" n (.-returncode r)]))
            (swap! float-refusals conj n))))
      (let [mods (python/sorted (python/list (.glob wasm-dir "*.wasm")) ** :key (fn [p] (.-name p)))
            modules (u/pydict-from (for [p mods] [(.-name p) (pin p)]))]
        (chk (= (python/len modules) (+ (count cases) (count wasm-probes))) (str ["wasm32-browser modules" (python/list (.keys modules))]))
        (let [browser (or (shutil/which (.get os/environ "KOTOBA_BROWSER" ""))
                          (some (fn [bn] (shutil/which bn)) ["chromium" "chromium-browser" "google-chrome" "google-chrome-stable"]))
              browser-run (if browser
                            (do (cr/run run "wasm32-browser" [sys/executable (rp wasm-check) "--modules" wasm-dir "--output" (o "wasm32-browser") "--browser" browser]
                                        (pyenv "HOME" (str out)))
                                (let [d (u/pydict "executed" true)] (.update d (read-json (o "wasm32-browser/wasm32-browser.json"))) d))
                            (u/pydict "executed" false "reason" "no Chromium or Chrome on this host: the workflow's wasm32-browser Chrome job runs these modules"))
              report (u/pydict "status" "PASS_WASM32_BROWSER_TARGET" "target" "wasm32-browser" "host" (host-triple)
                               "nativeBootstrap" (u/pydict "receipt" (pin (pathlib/Path boot "selfhost-bootstrap.json")) "tier" (g receipt "tier")
                                                           "F" (let [d (u/pydict "name" (g fixed "name"))] (.update d (pin F)) d))
                               "modules" modules "floatRefusals" (python/list @float-refusals) "browser" browser-run
                               "steps" (python/list (for [c (cr/calls run)] (u/pydict "name" (g c "name") "seconds" (g c "seconds") "ran" true)))
                               "cCompilerOrLoader" false "JVMNodeOrGraalFallback" false "emulation" false)]
          (.write_text (o "wasm32-browser-target.json") (u/json-dump report))
          (println (g report "status") "F" (g fixed "name") (subs (g (pin F) "sha256") 0 16) (python/len modules) "modules" (count @float-refusals) "float refusals"
                   (if (g browser-run "executed") "executed" "compiled")))))))

(defn -main [& args]
  (let [output (or (u/opt args "--output") (sys/exit "--output is required"))
        tier (or (u/opt args "--tier") "full")
        reuse (u/opt args "--reuse")
        store (u/opt args "--store")
        boot (u/opt args "--bootstrap")
        wasm? (boolean (some #{"--wasm32-browser"} args))]
    (when-not (contains? (set tiers) tier) (sys/exit "--tier must be pr, main or full"))
    (when reuse (sys/exit "--reuse is disabled until the producer and input closure are independently trusted"))
    (if wasm?
      (do (chk (and boot (not store)) "--wasm32-browser takes --bootstrap and no reuse")
          (wasm32-browser (.resolve (pathlib/Path output)) (.resolve (pathlib/Path boot))))
      (do (chk (not boot) "--bootstrap is only for --wasm32-browser")
          (main (.resolve (pathlib/Path output)) tier nil (when store (.resolve (pathlib/Path store))))))))

(when (some #(or (= % "selfhost-bootstrap.cljc") (str/ends-with? % "/selfhost-bootstrap.cljc")) sys/argv)
  (apply -main *command-line-args*))
