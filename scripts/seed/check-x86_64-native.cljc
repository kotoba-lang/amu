;; Qualify the loaderless x86_64 artifacts on a native x86_64 Linux kernel. Ported from check-x86_64-native.py
;; (Basilisp, JUN-974); the Python docstring has the full contract.
;;
;; Input (--bootstrap) is a selfhost-bootstrap output produced on arm64 Linux from the pinned root: S-x86_64.elf,
;; R-x86_64.elf and selfhost-unity.kotoba. No C compiler or loader, no emulation. Records natively: the X2/X3 fixed
;; point, the runtime cases, hardening (seccomp, cpu/wall/stack), the KX64V1 runner (G1 = G2 = G3), the scalar ELF
;; suite and aiueos object checks with X2, the static launcher check (every tier) and, in the full tier, the adopted
;; core as an x86_64 static image. Library: content_reuse.cljc (named so the CI closure covers it). The checks it
;; launches (check-runtime-boundary.cljc, check-static-launcher.py, check-x86_64-scalar.py,
;; check-x86_64-aiueos-object.py) stay Python.
;; Run (native x86_64 Linux): basilisp run -p scripts/seed scripts/seed/check-x86_64-native.cljc -- --bootstrap DIR
;;      --output DIR [--tier pr|main|full]
(ns check-x86-64-native
  (:require [basilisp.string :as str]
            [content-reuse :as cr]
            [gate-util :as u])
  (:import json operator os pathlib platform re shutil subprocess sys time))

(def root u/root)
(defn rp [rel] (pathlib/Path root rel))
(def adr0371 [["check-static-launcher.py" []]])

(defn g [m & ks] (reduce (fn [a k] (operator/getitem a k)) m ks))
(defn pin [p] (cr/pin p))
(defn chk [c m] (u/chk c m))
(defn read-json [p] (json/loads (.read_text (pathlib/Path p))))
(defn b [s] (.encode s))
(defn bhas? [needle hay] (u/has-bytes? (b needle) hay))
(defn tailb [bs n] (.decode (u/bslice bs (max 0 (- (python/len bs) n)) (python/len bs)) "utf-8" "replace"))
(defn lines-of [m] (vec (filter #(and (seq %) (not (.startswith % "#"))) (.splitlines (.read_text (rp m))))))
(defn pyenv [& kvs] (apply u/pydict kvs))
(defn merge-env [base extra] (let [d (python/dict base)] (.update d extra) d))

(defn run-suites [out X scripts]
  (let [suites (python/dict)]
    (doseq [[script args] scripts]
      (let [dst (pathlib/Path out (.replace script ".py" ""))
            r (subprocess/run (python/list (concat [sys/executable (str (rp (str "scripts/seed/" script))) "--compiler" (str X) "--output" (str dst)] args))
                              ** :capture_output true :timeout 3600)]
        (.write_bytes (pathlib/Path out "raw" (str script ".log")) (operator/add (.-stdout r) (.-stderr r)))
        (chk (= (.-returncode r) 0) (str [script (tailb (.-stdout r) 400) (tailb (.-stderr r) 400)]))
        (operator/setitem suites script (last (.splitlines (.strip (.decode (.-stdout r)))))))) 
    suites))

(defn payload-of [container dst]
  (let [parts (.split (.read_bytes container) (b "\n\n") 1)
        header (operator/getitem parts 0) body (operator/getitem parts 1)]
    (chk (and (re/fullmatch (b "KX64V1 x86_64-linux sysv-ctx-v11 ([0-9]+) 0") header) (= (operator/getitem body 0) 0xE9)) "kx64 payload")
    (.write_bytes dst body)
    (pin dst)))

(defn kx64-and-suites [run out X source scope]
  (let [o (fn [n] (pathlib/Path out n))]
    (run "G1-kx64" [X "compile" source "--target" "x86_64-linux" "--output" (o "G1.kx64") "--format" "kx64-v1"] scope)
    (let [gens (python/list [(u/pydict "native" (payload-of (o "G1.kx64") (o "G1.bin")) "container" (pin (o "G1.kx64")))])
          renv (merge-env scope (pyenv "KEXE_COMMAND" "1"))]
      (loop [producer (o "G1.bin") gs [2 3]]
        (when (seq gs)
          (let [gn (first gs)]
            (run (str "G" gn "-kx64") [(o "R-x86_64.elf") producer 0 0 "x86_64" "35,37,38,39" "--" "compile" source "--target" "x86_64-linux"
                                       "--output" (o (str "G" gn ".kx64")) "--format" "kx64-v1"] renv)
            (.append gens (u/pydict "native" (payload-of (o (str "G" gn ".kx64")) (o (str "G" gn ".bin"))) "container" (pin (o (str "G" gn ".kx64")))))
            (recur (o (str "G" gn ".bin")) (rest gs)))))
      (chk (and (u/deq (operator/getitem gens 0) (operator/getitem gens 1)) (u/deq (operator/getitem gens 1) (operator/getitem gens 2))) "KX64V1 runner fixed point")
      [gens (run-suites out X [["check-x86_64-scalar.py" []] ["check-x86_64-aiueos-object.py" []]])])))

(defn main [boot out tier reuse-dir store-dir]
  (chk (and (= (platform/system) "Linux") (contains? #{"x86_64" "AMD64"} (platform/machine))) "run on native x86_64 Linux")
  (.mkdir out ** :parents true :exist_ok false)
  (.mkdir (pathlib/Path out "raw"))
  (let [calls (python/list [])
        reuse (cr/runs out reuse-dir store-dir)
        o (fn [n] (pathlib/Path out n))
        run (fn [name argv env & {:keys [ok timeout] :or {ok true timeout 3600}}]
              (let [started (time/monotonic)
                    argv (mapv str argv)
                    r (subprocess/run (python/list argv) ** :cwd out :env (merge-env (pyenv "PATH" "/nonexistent") env) :capture_output true :timeout timeout)]
                (.write_bytes (pathlib/Path out "raw" (str name ".stdout")) (.-stdout r))
                (.write_bytes (pathlib/Path out "raw" (str name ".stderr")) (.-stderr r))
                (.append calls (u/pydict "name" name "argv" (python/list argv) "exit" (.-returncode r) "seconds" (python/round (- (time/monotonic) started) 3)))
                (.write_text (o "calls.json") (u/json-dump calls))
                (when ok
                  (chk (and (= (.-returncode r) 0) (zero? (python/len (.-stderr r)))) (str [name (.-returncode r) (tailb (.-stderr r) 400)])))
                r))
        scope (pyenv "KEXE_CAP_RESOURCES_35" (str out))]
    (doseq [name ["S-x86_64.elf" "R-x86_64.elf" "selfhost-unity.kotoba"]] (shutil/copy2 (pathlib/Path boot name) (o name)))
    (.chmod (o "S-x86_64.elf") 0755)
    (.chmod (o "R-x86_64.elf") 0755)
    (let [source (o "selfhost-unity.kotoba")
          paths (lines-of "seed/X86_64-LINUX-SELFHOST-MANIFEST")
          _ (chk (u/deq (.read_bytes source) (.join (u/bytes-of) (python/list (map #(operator/add (.read_bytes (rp %)) (u/bytes-of 10)) paths)))) "source graph differs from this checkout")
          compile- (fn [prod src dst fmt name & [target]]
                     (run name [prod "compile" src "--target" (or target "x86_64-linux") "--output" dst "--format" fmt] scope)
                     (.chmod dst 0755)
                     (pin dst))
          ;; 1. fixed point on x86_64
          s-cross (pin (o "S-x86_64.elf"))
          x2 (compile- (o "S-x86_64.elf") source (o "X2.elf") "static" "X2")
          _ (chk (u/deq s-cross x2) "x86_64 static compiler: cross-built = self-built")
          x3 (when (not= tier "pr")
               (let [x3 (compile- (o "X2.elf") source (o "X3.elf") "static" "X3")]
                 (chk (u/deq x2 x3) "x86_64 static fixed point")
                 x3))
          X (o "X2.elf")
          packed-payload (fn [name arity]
                           (let [src (o (str name ".kotoba"))]
                             (.write_text src (str "(ns " name " (:export [main]))\n(defn main [] :i64 42)\n"))
                             (let [kx64 (o (str name ".kx64"))]
                               (run (str name "-kx64") [X "compile" src "--target" "x86_64-linux" "--output" kx64 "--format" "kx64-v1"] scope)
                               (let [parts (.split (.read_bytes kx64) (b "\n\n") 1)
                                     header (operator/getitem parts 0) code (operator/getitem parts 1)
                                     m (re/fullmatch (b "KX64V1 x86_64-linux sysv-ctx-v11 ([0-9]+) 0") header)]
                                 (chk (and m (= (python/int (.group m 1)) (python/len code)) (u/deq (u/bslice code 0 1) (u/bytes-of 0xe9))) name)
                                 (let [kseed (o (str name ".kseed"))]
                                   (.write_bytes kseed (operator/add (operator/add (.encode (str "KSEED1 " (python/len code) " 1\nmain 0 " arity "\n\n")) (u/bytes-of)) code))
                                   kseed)))))
          packed-kseed (packed-payload "packed-main" 0)
          bad-packed-kseed (packed-payload "packed-main-arity1" 1)
          packed-output (o "packed-main.elf")
          runner (o "x86_64-kx64-runner.kotoba")
          _ (shutil/copy2 (rp "seed/x86_64-kx64-runner.kotoba") runner)
          packed-refusal (run "packed-main-arity-refusal" [X "compile" runner "--target" "x86_64-linux" "--output" (o "packed-arity1.elf") "--format" "packed" "--payload" bad-packed-kseed] scope :ok false)]
      (chk (and (= (.-returncode packed-refusal) 1) (bhas? "E7105" (.-stderr packed-refusal)) (not (.exists (o "packed-arity1.elf"))))
           (str [(.-returncode packed-refusal) (tailb (.-stderr packed-refusal) 400)]))
      (run "packed-main-compile" [X "compile" runner "--target" "x86_64-linux" "--output" packed-output "--format" "packed" "--payload" packed-kseed] scope)
      (.chmod packed-output 0755)
      (let [packed-run (run "packed-main-run" [packed-output] (pyenv "KEXE_STRUCTURED_REPORT" "1" "KEXE_ALLOW" "-" "KEXE_FUEL" "1000000"))]
        (chk (and (bhas? ":status :ok" (.-stdout packed-run)) (bhas? ":result 42" (.-stdout packed-run))) (tailb (.-stdout packed-run) 300)))
      (run "runtime-boundary" [(str (pathlib/Path (.-parent (pathlib/Path sys/executable)) "basilisp")) "run" "-p" (rp "scripts/seed")
                               (rp "scripts/seed/check-runtime-boundary.cljc") "--" "--compiler" X "--output" (o "runtime-boundary") "--payload" packed-kseed]
            (pyenv "AMU_ROOT" (str root)))
      (let [runtime-boundary (read-json (o "runtime-boundary/runtime-boundary.json"))
            ;; 2. runtime cases
            results (atom [])]
        (doseq [case (g (read-json (rp "seed/static-cases.json")) "cases")]
          (let [n (g case "name") src (o (str "case-" n ".kotoba"))]
            (.write_text src (g case "source"))
            (compile- X src (o (str "case-" n ".elf")) "static" (str "case-" n "-compile"))
            (let [r (run (str "case-" n) [(o (str "case-" n ".elf"))] (pyenv "KEXE_STRUCTURED_REPORT" "1" "KEXE_FUEL" "1000000" "KEXE_ALLOW" "-") :ok false)
                  fuel (re/search (b ":remaining ([0-9]+)") (.-stdout r))
                  observed (u/pydict "exit" (.-returncode r) "remainingFuel" (when fuel (python/int (.group fuel 1))))]
              (chk (u/deq observed (g case "reference")) (str [n observed (g case "reference")]))
              (when-not (g case "trap")
                (chk (= (python/int (.group (re/search (b ":result (-?[0-9]+)") (.-stdout r)) 1)) (g case "result")) "case result"))
              (swap! results conj (let [row (u/pydict "name" n)] (.update row observed) row)))))
        ;; 3. hardening, natively on x86_64
        (doseq [[name body] [["value" "(defn main [] :i64 42)"]
                             ["spin" "(defn main [] :i64 (loop [i 0] (if (< i 0) i (recur (inc i)))))"]
                             ["deep" "(defn- f [n :i64] :i64 (if (= n 0) 0 (+ 1 (f (dec n)))))\n(defn main [] :i64 (f 100000000))"]]]
          (let [src (o (str "probe-" name ".kotoba"))]
            (.write_text src (str "(ns probe-" name " (:export [main]))\n" body "\n"))
            (compile- X src (o (str "probe-" name ".elf")) "static" (str "probe-" name "-compile"))))
        (let [observe (fn [name image env]
                        (let [r (run (str "probe-" name) [(o (str "probe-" image ".elf"))] (merge-env (pyenv "KEXE_STRUCTURED_REPORT" "1") env) :ok false)]
                          (u/pydict "exit" (.-returncode r) "stderr" (.strip (.decode (.-stderr r) "utf-8" "replace")))))
              hardening (u/pydict "seccompDefault" (observe "seccomp-default" "value" (python/dict))
                                  "sandboxProbe" (observe "sandbox-probe" "value" (pyenv "KEXE_SANDBOX_PROBE" "1"))
                                  "cpuSeconds1" (observe "cpu" "spin" (pyenv "KEXE_CPU_SECONDS" "1"))
                                  "wallSeconds3" (observe "wall" "spin" (pyenv "KEXE_WALL_SECONDS" "3"))
                                  "stack1MiB" (observe "stack" "deep" (python/dict)))]
          (chk (= (g hardening "seccompDefault" "exit") 0) "seccomp must install on this kernel")
          (doseq [[k sig] [["sandboxProbe" "SIGSYS"] ["cpuSeconds1" "SIGXCPU"] ["wallSeconds3" "SIGALRM"] ["stack1MiB" "SIGSEGV"]]]
            (chk (and (= (g hardening k "exit") 120) (str/includes? (g hardening k "stderr") sig)) k))
          ;; This entry must not reintroduce a C loader/runtime prerequisite.
          (let [platform-output (o "platform-refused.elf")
                linked-refusal (run "refuse-platform-linked" [X "compile" (o "probe-value.kotoba") "--target" "x86_64-linux" "--output" platform-output "--format" "platform-linked"] scope :ok false)]
            (chk (and (= (.-returncode linked-refusal) 1) (bhas? "E2" (.-stderr linked-refusal)) (not (.exists platform-output))) "platform-linked refusal")
            ;; every tier: ADR 0371's checks; main and full tiers: the KX64V1 runner and the suites
            (let [suites (run-suites out X adr0371)
                  gens (atom (python/list []))]
              (when (not= tier "pr")
                (let [[gs more] (kx64-and-suites run out X source scope)]
                  (reset! gens gs)
                  (.update suites more)))
              ;; full tier: the adopted compiler core as an x86_64 static image (JUN-330)
              (let [core-x86
                    (when (= tier "full")
                      (let [adoption (read-json (rp (g (read-json (rp "seed/compiler-core.json")) "adoptionReceipt")))
                            unity-of (fn [manifest dst]
                                       (.write_bytes dst (.join (u/bytes-of) (python/list (map #(operator/add (.read_bytes (rp %)) (u/bytes-of 10)) (lines-of manifest)))))
                                       (pin dst))
                            core-static (o "core-static-unity.kotoba") adopted (o "adopted-unity.kotoba")]
                        (unity-of "seed/CORE-STATIC-MANIFEST" core-static)
                        (chk (= (g (unity-of "seed/MANIFEST" adopted) "sha256") (g adoption "sourceUnitySHA256")) "adopted source drift")
                        (let [senv (merge-env scope (pyenv "KEXE_STACK_BYTES" "8388608"))]
                          (run "X0" [X "compile" core-static "--target" "x86_64-linux" "--output" (o "X0.elf") "--format" "static"] senv)
                          (.chmod (o "X0.elf") 0755)
                          (let [t0 (time/monotonic)]
                            (run "X0-core" [(o "X0.elf") "compile" adopted "--target" "aarch64-macos" "--output" (o "X0-core.kseed")] senv :timeout 10800)
                            (let [seconds (python/round (- (time/monotonic) t0) 1)]
                              (run "X0-extract" [(o "X0.elf") "extract-native" (o "X0-core.kseed") "--symbol" "main" "--output" (o "X0-core.bin")] senv)
                              (chk (= (g (pin (o "X0-core.bin")) "sha256") (g adoption "nativeImageSHA256")) "x86_64 core output mismatch")
                              (u/pydict "X0" (pin (o "X0.elf")) "container" (pin (o "X0-core.kseed")) "native" (pin (o "X0-core.bin")) "coreCompileSeconds" seconds))))))
                    report (u/pydict "status" "PASS_NATIVE_X86_64_LOADERLESS" "tier" tier
                                     "host" (python/list [(platform/system) (platform/machine) (platform/release)])
                                     "nativeX86_64Kernel" true "emulation" false "cCompilerOrLoader" false
                                     "compiler" (u/pydict "crossBuiltOnArm64" s-cross "X2" x2 "X3" x3)
                                     "cases" (python/list @results) "hardening" hardening "runtimeBoundary" runtime-boundary
                                     "platformLinkedRefusal" (u/pydict "exit" (.-returncode linked-refusal) "diagnostic" "E2")
                                     "coreOnX86_64" core-x86
                                     "kx64Runner" (u/pydict "runner" (pin (o "R-x86_64.elf")) "generations" @gens)
                                     "suites" suites
                                     "reuse" (u/pydict "read" (boolean reuse-dir) "store" (boolean store-dir)
                                                       "steps" (python/list (for [c (cr/calls reuse)]
                                                                              (u/pydict-from (for [k ["name" "seconds" "key" "reused"] :when (operator/contains c k)] [k (operator/getitem c k)])))))
                                     "bootstrapReceipt" (g (read-json (pathlib/Path boot "selfhost-bootstrap.json")) "root" "image"))]
                (.write_text (o "x86_64-native.json") (u/json-dump report))
                (println (g report "status") tier "X2" (subs (g x2 "sha256") 0 16) (count @results) "cases")))))))))

(defn -main [& args]
  (let [boot (or (u/opt args "--bootstrap") (sys/exit "--bootstrap is required"))
        output (or (u/opt args "--output") (sys/exit "--output is required"))
        tier (or (u/opt args "--tier") "full")
        reuse (u/opt args "--reuse")
        store (u/opt args "--store")]
    (when-not (contains? #{"pr" "main" "full"} tier) (sys/exit "--tier must be pr, main or full"))
    (when reuse (sys/exit "--reuse is disabled until the producer and input closure are independently trusted"))
    (main (.resolve (pathlib/Path boot)) (.resolve (pathlib/Path output)) tier nil (when store (.resolve (pathlib/Path store))))))

(when (some #(or (= % "check-x86_64-native.cljc") (str/ends-with? % "/check-x86_64-native.cljc")) sys/argv)
  (apply -main *command-line-args*))
