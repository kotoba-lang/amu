;; JUN-31: the aiueos kernel object route through the C-free selfhost compiler.
;;
;; Runs on Linux x86-64 (no C loader is built or run; Basilisp orchestrates and hashes only). Takes the
;; loaderless selfhost build produced by `selfhost-bootstrap.py` (arm64 Linux; Amu-produced root, no C compiler
;; or loader anywhere in the lineage) and compiles the aiueos kernel-object probe fixtures with two C-free
;; producers: the x86_64 static selfhost compiler `S-x86_64.elf`, and the C-free KX64V1 runner `R-x86_64.elf`
;; carrying the G1 payload.
;;
;; Every object is validated against the fail-closed aiueos kernel object ABI (x86_64-aiueos-kernel-v1),
;; embedded here so this gate is self-contained. The fixtures and refusals are the same suite on both routes,
;; and the harness asserts the two routes emit byte-identical objects.
;;
;; Boundary (do not round it up): the seed route emits the kernel OBJECT ABI only. It is not the kernel IMAGE
;; route, and no emitted object has run in a kernel.
;; Ported from check-x86_64-aiueos-object-cfree.py (Basilisp). The library part (verify-abi, cases, shape-refusals)
;; is also loaded by check-aiueos-image-native.cljc, as the Python original was loaded by the image observer.
;; Run: basilisp run scripts/seed/check-x86_64-aiueos-object-cfree.cljc -- --build DIR --output OUT
(ns check-x86-64-aiueos-object-cfree
  (:require [basilisp.string :as str]
            [gate-util :as u])
  (:import json operator os pathlib platform re shutil struct subprocess sys))

(def target "x86_64-aiueos-kernel-v1")

(defn extract-kx64
  "KX64V1 container -> bare payload (from the retired check-x86_64-selfhost.py)."
  [src dst]
  (let [[header payload] (.split (.read_bytes (pathlib/Path src)) (.encode "\n\n") 1)
        match (re/fullmatch (.encode "KX64V1 x86_64-linux sysv-ctx-v11 ([0-9]+) 0") header)]
    (u/chk (and match (< 0 (python/len payload) 4194304) (= (python/len payload) (python/int (.group match 1))))
           "invalid x86 runtime container")
    (u/chk (= 0xE9 (u/geti payload 0)) "missing bounded entry trampoline")
    (.write_bytes (pathlib/Path dst) payload)))

(defn verify-abi
  "The aiueos x86_64-aiueos-kernel-v1 object ABI, fail-closed."
  [blob expected-symbol]
  (u/chk (and (>= (python/len blob) 64)
              (= (u/bslice blob 0 16) (operator/add (u/bytes-of 0x7f 0x45 0x4c 0x46 2 1 1 0) (u/bytes-of-n 8 0))))
         "not canonical ELF64 LE SysV")
  (let [[etype machine version entry phoff shoff flags ehsize phentsize phnum shentsize shnum shstrndx]
        (vec (struct/unpack_from "<HHIQQQIHHHHHH" blob 16))
        _ (u/chk (= [1 62 1 0 0 0 0 64 64] [etype machine version entry phoff phnum flags ehsize shentsize])
                 "header is not ET_REL/EM_X86_64 without program headers")
        _ (u/chk (and (pos? shnum) (<= shnum 16) (< shstrndx shnum) (<= (+ shoff (* shnum 64)) (python/len blob)))
                 "invalid section table bounds")
        sections (vec (for [i (range shnum)] (vec (struct/unpack_from "<IIQQQQIIQQ" blob (+ shoff (* i 64))))))
        section-bytes (fn [index]
                        (let [[_ stype _ _ offset size] (nth sections index)]
                          (if (= stype 8)
                            (u/bytes-of)
                            (do (u/chk (<= (+ offset size) (python/len blob)) "section exceeds file")
                                (u/bslice blob offset (+ offset size))))))
        strings (section-bytes shstrndx)
        string-at (fn [table offset]
                    (u/chk (< offset (python/len table)) "string offset exceeds table")
                    (let [end (.find table (u/bytes-of 0) offset)]
                      (u/chk (>= end 0) "unterminated string")
                      (.decode (u/bslice table offset end) "ascii")))
        names (mapv #(string-at strings (first %)) sections)
        allowed #{"" ".text" ".data" ".rela.text" ".symtab" ".strtab" ".shstrtab"}
        _ (u/chk (and (= (set names) allowed) (= (count names) (count allowed))) (str "section set " (pr-str names)))
        by-name (into {} (map-indexed (fn [i n] [n i]) names))
        text (nth sections (by-name ".text")) data (nth sections (by-name ".data"))
        _ (u/chk (and (= 1 (nth text 1)) (not (zero? (bit-and (nth text 2) 4)))) ".text must be executable PROGBITS")
        _ (u/chk (and (= 1 (nth data 1)) (zero? (bit-and (nth data 2) 4))) ".data must be non-exec PROGBITS")
        sym-index (by-name ".symtab")
        sym (nth sections sym-index)
        _ (u/chk (and (= 2 (nth sym 1)) (= 24 (nth sym 9)) (= (nth sym 6) (by-name ".strtab")) (zero? (mod (nth sym 5) 24)))
                 "invalid symbol table")
        symbol-strings (section-bytes (by-name ".strtab"))
        sym-bytes (section-bytes sym-index)
        symbols (vec (for [offset (range 0 (python/len sym-bytes) 24)]
                       (let [[name info other shndx value size] (vec (struct/unpack_from "<IBBHQQ" sym-bytes offset))]
                         [(string-at symbol-strings name) info other shndx value size])))
        ;; expected_symbol is one name, or several joined by commas (a multi-export object, JUN-556); each must
        ;; be exactly one GLOBAL FUNC in .text.
        expected-symbols (vec (.split expected-symbol ","))
        _ (u/chk (and (<= 1 (count expected-symbols) 8) (= (count (set expected-symbols)) (count expected-symbols))) "export list")]
    (doseq [name expected-symbols]
      (let [probes (filterv #(= name (first %)) symbols)]
        (u/chk (= 1 (count probes)) (str "requires exactly one " name " symbol"))
        (let [[_ info other shndx _ size] (first probes)]
          (u/chk (and (= info 0x12) (zero? other) (= shndx (by-name ".text")) (not (zero? size)))
                 "export must be a default-visibility GLOBAL FUNC defined in .text"))))
    (u/chk (not-any? #(and (zero? (nth % 3)) (seq (nth % 0))) symbols) "undefined/imported symbols are forbidden")
    (let [rela (nth sections (by-name ".rela.text"))
          cnt (count expected-symbols)
          _ (u/chk (and (= 4 (nth rela 1)) (= 24 (nth rela 9)) (= (nth rela 6) sym-index) (= (nth rela 7) (by-name ".text"))
                        (= (nth rela 5) (* 24 cnt)))
                   "requires exactly one .rela.text entry per export")
          rela-bytes (section-bytes (by-name ".rela.text"))
          context-symbols
          (set (for [entry (range cnt)]
                 (let [[rel-offset rel-info addend] (vec (struct/unpack_from "<QQq" rela-bytes (* entry 24)))
                       symbol-index (bit-shift-right rel-info 32)
                       relocation-type (bit-and rel-info 0xFFFFFFFF)]
                   (u/chk (and (< symbol-index (count symbols)) (= relocation-type 2) (= addend -4))
                          "relocation must be R_X86_64_PC32 with addend -4")
                   (u/chk (= (nth (nth symbols symbol-index) 3) (by-name ".data")) "relocation target must be defined in .data")
                   (u/chk (<= (+ rel-offset 4) (python/len (section-bytes (by-name ".text")))) "relocation offset exceeds .text")
                   symbol-index)))]
      (u/chk (= 1 (count context-symbols)) "every relocation must name the same context symbol"))))

(def cases
  (u/pydict-from
    [["probe" ["(ns kernel-probe (:export [kotoba_aiueos_probe]))\n(defn kotoba_aiueos_probe [] :i64 42)\n" "kotoba_aiueos_probe"]]
     ["flat-args" ["(ns kernel-flat (:export [kotoba_aiueos_flat]))\n(defn kotoba_aiueos_flat [a :i64 n :i64] :i64 (+ a n))\n" "kotoba_aiueos_flat"]]
     ["helper-loop" [(str "(ns kernel-loop (:export [kotoba_aiueos_loop]))\n"
                         "(defn- sum [n :i64 s :i64] :i64 (if (= n 0) s (sum (dec n) (+ s n))))\n"
                         "(defn kotoba_aiueos_loop [] :i64 (sum 10 0))\n") "kotoba_aiueos_loop"]]
     ["big-fuel" ["(ns kernel-big (:export [kotoba_aiueos_big]))\n(defn kotoba_aiueos_big [] :i64 7)\n" "kotoba_aiueos_big"]]
     ["two-exports" [(str "(ns kernel-two (:export [kotoba_aiueos_a kotoba_aiueos_b]))\n"
                          "(defn kotoba_aiueos_a [] :i64 1)\n(defn kotoba_aiueos_b [x :i64] :i64 (+ x 2))\n")
                     "kotoba_aiueos_a,kotoba_aiueos_b"]]]))

(def shape-refusals
  (u/pydict-from
    [["no-export" "(ns refused)\n(defn- helper [] :i64 1)\n"]
     ["nine-exports" (str "(ns refused (:export [" (str/join " " (for [i (range 9)] (str "kotoba_aiueos_" i))) "]))\n"
                          (apply str (for [i (range 9)] (str "(defn kotoba_aiueos_" i " [] :i64 " i ")\n"))))]
     ["six-params" (str "(ns refused (:export [kotoba_aiueos_six]))\n"
                        "(defn kotoba_aiueos_six [a :i64 b :i64 c :i64 d :i64 e :i64 f :i64] :i64 (+ a b c d e f))\n")]
     ["float" (str "(ns refused (:export [kotoba_aiueos_f]))\n"
                   "(defn kotoba_aiueos_f [] :i64 (f64-to-i64-truncating (f64-add 1.0 2.0)))\n")]
     ["string" (str "(ns refused (:export [kotoba_aiueos_s]))\n"
                    "(defn kotoba_aiueos_s [] :i64 (string-length \"hello\"))\n")]
     ["vector" (str "(ns refused (:export [kotoba_aiueos_v]))\n"
                    "(defn kotoba_aiueos_v [] :i64 (vector-count [1 2]))\n")]
     ["capability" (str "(ns refused (:export [kotoba_aiueos_c]))\n"
                        "(defn kotoba_aiueos_c [p :string] :string (typed-cap-call :fs/app-data :string :string p))\n")]
     ["unused-bad-helper" (str "(ns refused (:export [kotoba_aiueos_u]))\n"
                               "(defn- unused [v :vector-i64] :i64 (vector-count v))\n"
                               "(defn kotoba_aiueos_u [] :i64 42)\n")]]))

(def flag-refusals
  [["policy" ["--policy" "unknown"]] ["source-path" ["--source-path" "unknown"]] ["format-kx64" ["--format" "kx64-v1"]]
   ["zero-fuel" ["--fuel" "0"]] ["bad-fuel" ["--fuel" "12x"]] ["overflow-fuel" ["--fuel" "99999999999999999"]]])

(defn command-env
  "The loader-suite command environment (retired check-x86_64-aiueos-object.py). KEXE_COMMAND=1 makes the guest
  exit status the process exit status; KEXE_SECCOMP=if-available is required on qemu-user hosts."
  [scope]
  (python/dict {"PATH" "/usr/bin:/bin" "TMPDIR" (str scope) "KEXE_COMMAND" "1" "KEXE_SECCOMP" "if-available"
                "KEXE_CAP_RESOURCES_35" (str scope) "KEXE_FUEL" "off" "KEXE_VECTORS" "4194304"
                "KEXE_VECTOR_ITEMS" "134217728" "KEXE_STRING_POOL" "268435456" "KEXE_PAIRS" "16777216"
                "KEXE_CPU_SECONDS" "120" "KEXE_WALL_SECONDS" "120"}))

(defn compile-case
  [prefix scope name source extra expect-ok & {:keys [sentinel]}]
  (let [src (.joinpath scope (str name ".kotoba")) obj (.joinpath scope (str name ".o"))]
    (.write_text src source)
    (when sentinel (.write_bytes obj sentinel))
    (let [result (u/run-process (concat prefix ["compile" src "--target" target "--output" obj] extra)
                                (command-env scope) 600 :cwd scope)]
      (when expect-ok
        (u/chk (and (zero? (.-returncode result)) (not (u/nonempty? (.-stderr result)))) [name (.-returncode result) (.-stderr result)]))
      [obj result])))

(defn run-route [label prefix scope route-rows]
  (.mkdir scope ** :parents true :exist_ok true)
  (let [rows (python/list) refused (python/list)]
    (doseq [[name [source symbol]] (.items cases)]
      (let [extra (if (= name "big-fuel") ["--fuel" "3000000000"] ["--fuel" "1024"])
            [obj result] (compile-case prefix scope name source extra true)
            fields (into {} (for [[k v] (re/findall (.encode ":([a-z-]+) (\\d+)") (.-stdout result))] [(.decode k) (python/int v)]))
            blob (.read_bytes obj)]
        (u/chk (= (get fields "bytes") (python/len blob)) [name fields (python/len blob)])
        (verify-abi blob symbol)
        (.append rows (u/pydict "name" name "symbol" symbol "bytes" (python/len blob)
                                "textBytes" (get fields "text-bytes") "objectPin" (u/pin obj)))))
    (doseq [[name text] (.items shape-refusals)]
      (let [[obj result] (compile-case prefix scope (str "refuse-" name) text ["--fuel" "1024"] false)]
        (u/chk (and (not (zero? (.-returncode result))) (not (.exists obj))) [name (.-stdout result) (.-stderr result)])
        (let [code (re/search (.encode "E(\\d{4})") (.-stderr result))]
          (u/chk code [name (.-stderr result)])
          (.append refused (u/pydict "name" name "code" (str "E" (.decode (.group code 1))))))))
    (doseq [[name extra] flag-refusals]
      (let [[obj result] (compile-case prefix scope (str "refuse-" name) (first (u/geti cases "probe")) extra false)]
        (u/chk (and (= 2 (.-returncode result)) (u/has-bytes? (.encode "E7100") (.-stderr result)) (not (.exists obj))) [name (.-stderr result)])
        (.append refused (u/pydict "name" name "code" "E7100"))))
    (let [[obj result] (compile-case prefix scope "existing-output" (first (u/geti cases "probe")) ["--fuel" "1024"] false
                                     :sentinel (.encode "preserve original"))]
      (u/chk (and (= 2 (.-returncode result)) (= (.encode "preserve original") (.read_bytes obj))))
      (.append refused (u/pydict "name" "existing-output" "code" "E7100")))
    (.append route-rows (u/pydict "route" label "prefix" (python/list (map str prefix)) "cases" rows "refusals" refused))))

(defn main [build output]
  (u/chk (and (= "Linux" (platform/system)) (contains? #{"x86_64" "AMD64"} (platform/machine))) (platform/platform))
  (.mkdir output ** :parents true :exist_ok false)
  (let [receipt (u/read-json (.joinpath build "selfhost-bootstrap.json"))
        _ (u/chk (and (= "PASS_LOADERLESS_SELFHOST_BOOTSTRAP" (u/geti receipt "status")) (false? (u/geti receipt "cCompilerOrLoader")))
                 "the producer lineage must be the loaderless selfhost bootstrap")
        compiler (.joinpath build "S-x86_64.elf")
        runner (.joinpath build "R-x86_64.elf")
        _ (u/chk (u/deq (u/pin compiler) (u/geti (u/geti receipt "built") "x86_64Compiler")) "x86_64 compiler pin drift")
        _ (u/chk (u/deq (u/pin runner) (u/geti (u/geti receipt "built") "x86_64Runner")) "x86_64 runner pin drift")
        unity (.joinpath build "selfhost-unity.kotoba")
        source-graph (u/geti receipt "sourceGraph")]
    ;; The unity source must be the exact concatenation of the manifest's modules, and the repo copies must not
    ;; have drifted from the receipt's pins.
    (doseq [[path expected] (.items source-graph)]
      (u/chk (u/deq (u/pin (.joinpath u/root path)) expected) ["source pin drift" path]))
    (let [manifest-key (first (python/list source-graph))
          module-paths (u/manifest-paths (.joinpath u/root manifest-key))]
      (u/chk (= (set (cons manifest-key module-paths)) (set (python/list source-graph))) "source graph shape drift")
      (u/chk (= (.read_bytes unity)
                (.join (u/bytes-of) (python/list (for [p module-paths] (operator/add (.read_bytes (.joinpath u/root p)) (.encode "\n"))))))
             "selfhost unity source drift"))
    ;; Containment parity with the loader-run suite: producer and payload live inside the declared capability root.
    (let [static-scope (.joinpath output "static")
          _ (.mkdir static-scope ** :parents true :exist_ok true)
          compiler-copy (.joinpath static-scope "S-x86_64.elf")
          _ (do (shutil/copyfile compiler compiler-copy) (.chmod compiler-copy 0755))
          ;; The G1 payload: the selfhost source as a KX64V1 image, emitted C-free by the static compiler itself
          ;; and carried by the C-free runner.
          payload-scope (.joinpath output "payload")
          _ (.mkdir payload-scope ** :parents true :exist_ok true)
          payload-producer (.joinpath payload-scope "S-x86_64.elf")
          _ (do (shutil/copyfile compiler payload-producer) (.chmod payload-producer 0755))
          payload-src (.joinpath payload-scope "selfhost-unity.kotoba")
          _ (shutil/copyfile unity payload-src)
          g1k (.joinpath payload-scope "G1.kx64")
          result (u/run-process [payload-producer "compile" payload-src "--target" "x86_64-linux" "--output" g1k "--format" "kx64-v1"]
                                (command-env payload-scope) 600 :cwd payload-scope)
          _ (u/chk (and (zero? (.-returncode result)) (not (u/nonempty? (.-stderr result)))) [(.-returncode result) (.-stderr result)])
          runner-scope (.joinpath output "runner")
          _ (.mkdir runner-scope ** :parents true :exist_ok true)
          runner-copy (.joinpath runner-scope "R-x86_64.elf")
          _ (do (shutil/copyfile runner runner-copy) (.chmod runner-copy 0755))
          g1 (.joinpath runner-scope "G1.bin")
          _ (extract-kx64 g1k g1)
          ;; Was the guest sandbox actually enforced on this host? The runtime's own diagnostic (KEXE_SANDBOX_PROBE)
          ;; traps SIGSYS/exit 120 when seccomp is installed and passes through when not.
          probe-env (command-env payload-scope)
          _ (operator/setitem probe-env "KEXE_SANDBOX_PROBE" "1")
          probe (u/run-process [payload-producer] probe-env 600 :cwd payload-scope)
          seccomp-enforced (and (= 120 (.-returncode probe)) (u/has-bytes? (.encode "SIGSYS") (.-stderr probe)))
          routes (python/list)]
      (run-route "static-image-x86_64" [compiler-copy] static-scope routes)
      (run-route "kx64-runner-x86_64" [runner-copy g1 0 0 "x86_64" "35,37,38,39" "--"] runner-scope routes)
      ;; Route parity: the same source graph, two C-free producers, identical objects.
      (let [by-route (into {} (for [r routes]
                                [(u/geti r "route") (into {} (for [c (u/geti r "cases")] [(u/geti c "name") (python/str (u/geti c "objectPin"))]))]))]
        (u/chk (= (get by-route "static-image-x86_64") (get by-route "kx64-runner-x86_64")) "static and runner routes disagree"))
      (let [report (u/pydict
                     "status" "PASS_LINUX_X86_CFREE_AIUEOS_KERNEL_OBJECT_ROUTE"
                     "host" (python/list [(platform/system) (platform/machine)])
                     "linear" "JUN-31" "target" target
                     "lineage" (u/pydict "bootstrap" "selfhost-bootstrap.py (Amu-produced root, no C compiler or loader)"
                                         "bootstrapReceipt" (u/pin (.joinpath build "selfhost-bootstrap.json"))
                                         "root" (u/geti (u/geti receipt "root") "image")
                                         "aarch64FixedPoint" (u/geti receipt "generations"))
                     "compiler" (u/pydict "staticImage" (u/pin compiler) "producedBy" "S3.elf aarch64 selfhost fixed point")
                     "runner" (u/pydict "R" (u/pin runner) "G1kx64" (u/pin g1k) "G1payload" (u/pin g1))
                     "sourcePins" (u/geti receipt "sourceGraph")
                     "routes" routes
                     "seccomp" (u/pydict "mode" "if-available" "sandboxProbeExit" (.-returncode probe) "enforced" (boolean seccomp-enforced))
                     "executionHost" (u/pydict "note" (str "x86_64 images run under qemu-user binfmt (podman --platform linux/amd64); "
                                                           "seccomp(2) returns ENOSYS there and RLIMIT_AS/RLIMIT_STACK are not applied "
                                                           "to the guest. The aarch64 bootstrap measured enforcement natively "
                                                           "(selfhost-bootstrap.json hardening.sandboxProbe = SIGSYS/120); native x86_64 "
                                                           "enforcement is unmeasured until a native x86_64 host runs this gate "
                                                           "(JUN-34 OCI VM)."))
                     "trustedCLoader" false "JVMNodeOrGraalFallback" false "kernelImage" false "kernelExecution" false
                     "performanceMeasured" false
                     "boundary" "kernel OBJECT ABI only; not the kernel image route; no emitted object has run in a kernel")]
        (.write_text (.joinpath output "cfree-kernel-object.json") (u/json-dump report))
        (println (u/geti report "status") (reduce + (map #(python/len (u/geti % "cases")) routes)) "objects"
                 (reduce + (map #(python/len (u/geti % "refusals")) routes)) "refusals")))))

(defn -main [& args]
  (main (.resolve (pathlib/Path (or (u/opt args "--build") (sys/exit "--build is required"))))
        (.resolve (pathlib/Path (or (u/opt args "--output") (sys/exit "--output is required"))))))

(when (some #(or (= % "check-x86_64-aiueos-object-cfree.cljc") (str/ends-with? % "/check-x86_64-aiueos-object-cfree.cljc")) sys/argv)
  (apply -main *command-line-args*))
