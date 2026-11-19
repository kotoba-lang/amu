;; Qualify the complete public compiler on an actual native Linux x86_64 kernel. Transport/hash/process
;; orchestration only. The product compiler emits every image; the canonical native controller and native Kotoba
;; gate own CDCI's verdict, including all24 result/fuel/refusal cases. Ported from check-complete-x86.py
;; (Basilisp, JUN-974).
;; Run (native x86_64 Linux): basilisp run -p scripts/seed scripts/seed/check-complete-x86.cljc -- --compiler F
;;      --arm-proof one-compiler.json --output DIR
(ns check-complete-x86
  (:require [basilisp.string :as str]
            [gate-util :as u])
  (:import json operator pathlib platform shutil struct subprocess sys time))

(def root u/root)
(defn rp [rel] (pathlib/Path root rel))
(defn g [m & ks] (reduce (fn [a k] (operator/getitem a k)) m ks))
(defn pin [p] (let [d (.read_bytes (pathlib/Path p))] (u/pydict "bytes" (python/len d) "sha256" (u/sha256-hex d))))
(defn chk [c m] (u/chk c (str m)))
(defn read-json [p] (json/loads (.read_text (pathlib/Path p))))
(defn pyenv [& kvs] (apply u/pydict kvs))
(defn lines-of [m] (vec (filter #(and (seq %) (not (.startswith % "#"))) (.splitlines (.read_text (rp m))))))
(defn unity-bytes [paths] (.join (u/bytes-of) (python/list (map #(operator/add (.read_bytes (rp %)) (u/bytes-of 10)) paths))))
(defn tailb [bs n] (.decode (u/bslice bs (max 0 (- (python/len bs) n)) (python/len bs)) "utf-8" "replace"))

(defn static-elf [path]
  (let [bs (.read_bytes (pathlib/Path path))
        u2 (fn [fmt off] (struct/unpack_from fmt bs off))]
    (chk (u/deq (u/bslice bs 0 8) (u/bytes-of 0x7f 0x45 0x4c 0x46 2 1 1 0)) "ELF header")
    (chk (u/deq (u2 "<HH" 16) (python/tuple [2 62])) "ET_EXEC/EM_X86_64")
    (let [off (first (u2 "<Q" 32))
          [size cnt] (u2 "<HH" 54)]
      (chk (and (= size 56) (< 0 cnt 17) (<= (+ off (* cnt size)) (python/len bs))) "program headers")
      (let [types (map (fn [i] (first (u2 "<I" (+ off (* i size))))) (range cnt))]
        (chk (and (not (some #{2} types)) (not (some #{3} types))) "dynamic loader/segment")))
    (let [d (pin path)]
      (.update d (pyenv "elf" "ET_EXEC/EM_X86_64" "interpreter" false "dynamic" false))
      d)))

(defn run-main [compiler arm-proof out]
  (chk (and (= (platform/system) "Linux") (= (platform/machine) "x86_64")) "native Linux x86_64 required")
  (let [proof (read-json arm-proof)
        _ (chk (u/deq (pin compiler) (g proof "completeX86Compiler")) "compiler is not the arm-built complete x86 compiler")
        _ (.mkdir out ** :parents true :exist_ok false)
        _ (.mkdir (pathlib/Path out "raw"))
        o (fn [n] (pathlib/Path out n))
        calls (python/list [])
        env (pyenv "PATH" "/nonexistent" "KEXE_CAP_RESOURCES_35" (str out) "KEXE_STACK_BYTES" "8388608")
        run (fn [name argv & {:keys [custom ok timeout] :or {ok true timeout 900}}]
              (let [started (time/monotonic)
                    r (subprocess/run (python/list (map str argv)) ** :cwd out :env (or custom env) :capture_output true :timeout timeout)]
                (.write_bytes (pathlib/Path out "raw" (str name ".stdout")) (.-stdout r))
                (.write_bytes (pathlib/Path out "raw" (str name ".stderr")) (.-stderr r))
                (.append calls (pyenv "name" name "argv" (python/list (map str argv)) "exit" (.-returncode r)
                                      "seconds" (python/round (- (time/monotonic) started) 3)))
                (.write_text (o "calls.json") (u/json-dump calls))
                (when ok (chk (and (= (.-returncode r) 0) (zero? (python/len (.-stderr r)))) [name (.-returncode r) (tailb (.-stderr r) 600)]))
                r))
        paths (lines-of "seed/FULL-MANIFEST")]
    (doseq [[p identity] (.items (g proof "sources" "seed/FULL-MANIFEST"))]
      (chk (u/deq (pin (rp p)) identity) ["source drift" p]))
    (let [full (o "full.kotoba")
          _ (.write_bytes full (unity-bytes paths))
          f1 (o "F1.elf")
          _ (shutil/copy2 compiler f1)
          _ (.chmod f1 0755)
          generations (python/list [(static-elf f1)])
          previous (atom f1)]
      (doseq [gn [2 3]]
        (let [image (o (str "F" gn ".elf"))]
          (run (str "F" gn) [@previous "compile" full "--target" "x86_64-linux" "--output" image "--format" "static"])
          (.chmod image 0755)
          (.append generations (static-elf image))
          (reset! previous image)))
      (chk (and (u/deq (operator/getitem generations 0) (operator/getitem generations 1)) (u/deq (operator/getitem generations 1) (operator/getitem generations 2)))
           "complete native x86 fixed point")
      (let [F @previous
            roles (python/dict)
            core-source (o "core-static.kotoba")
            _ (.write_bytes core-source (unity-bytes (lines-of "seed/CORE-STATIC-MANIFEST")))
            amu-gate (o "cdci-amu-selfhost.elf")
            _ (run "build-amu-selfhost" [F "compile" core-source "--target" "x86_64-linux" "--output" amu-gate "--format" "static"])
            _ (.chmod amu-gate 0755)
            _ (operator/setitem roles "amu-selfhost" (static-elf amu-gate))
            _ (chk (u/deq (pin amu-gate) (g proof "cdci" "images" "amu-selfhost")) "amu-selfhost image pin")
            _ (doseq [name ["entry.kotoba" "runtime.kotoba" "controller.kotoba" "kotoba-gate.kotoba"]]
                (let [dst (o (str "cdci-" name))]
                  (shutil/copy2 (rp (str "seed/cdci/" name)) dst)
                  (chk (u/deq (pin dst) (g proof "cdci" "sources" name)) name)))
            _ (doseq [[role name] [["controller" "controller.kotoba"] ["kotoba-native" "kotoba-gate.kotoba"]]]
                (let [dst (o (str "cdci-" role ".elf"))]
                  (run (str "build-" role) [F "cdci-build" role (o "cdci-entry.kotoba") (o "cdci-runtime.kotoba") (o (str "cdci-" name)) dst])
                  (.chmod dst 0755)
                  (operator/setitem roles role (static-elf dst))
                  (chk (u/deq (pin dst) (g proof "cdci" "images" role)) ["role differs by producing kernel" role])))
            cases (g (read-json (rp "seed/static-cases.json")) "cases")
            _ (chk (= (python/len cases) 24) "24 cases")
            ledger (python/list [])]
        (doseq [case cases]
          (let [n (g case "name")
                src (o (str "case-" n ".kotoba"))
                _ (.write_text src (g case "source"))
                dst (o (str "case-" n ".elf"))]
            (run (str "compile-case-" n) [F "compile" src "--target" "x86_64-linux" "--output" dst "--format" "static"])
            (.chmod dst 0755)
            (.append ledger (pyenv "name" n "source" (pin src) "image" (static-elf dst) "result" (g case "result") "reference" (g case "reference")))))
        ;; Exercise the actual complete x86 product entry with pinned bytes (supplements the native verdict).
        (let [good (o "public-good.kotoba")
              _ (.write_text good "(ns public-good (:export [main]))\n(defn main [] :i64 42)\n")
              lock (o "public-good.ksl")
              _ (.write_text lock (str "KSL1\nentry " good "\nfile " (g (pin good) "sha256") " " good "\n"))
              digest (g (pin lock) "sha256")
              _ (run "native-public-check" [F "check" good "--source-lock" lock "--source-lock-sha256" digest])
              _ (run "native-public-compile" [F "compile" good "--target" "aarch64-macos" "--output" (o "public-good.kseed") "--source-lock" lock "--source-lock-sha256" digest])
              unknown (o "public-unknown.kotoba")
              _ (.write_text unknown "(ns public-unknown (:export [main]))\n(defn main [] :i64 (amu-unresolved 0))\n")
              refusals (python/list [])]
          (doseq [[name args code] [["digest-mismatch" ["check" good "--source-lock" lock "--source-lock-sha256" (apply str (repeat 64 "0"))] "E6015"]
                                    ["missing-lock" ["check" good "--source-lock" (o "missing.ksl")] "E6015"]
                                    ["unknown-form" ["check" unknown] "E2101"]
                                    ["c-linked-format" ["compile" good "--target" "x86_64-linux" "--output" (o "c-linked.elf") "--format" "platform-linked"] "E2"]
                                    ["unsupported-default" ["compile" good "--output" (o "refused.kseed")] "E2"]
                                    ["unsupported-verb" ["worker"] "E1"]
                                    ["unsupported-seal" ["compile" good "--target" "aarch64-macos" "--output" (o "refused.kseed") "--seal" "unknown"] "E1"]]]
            (let [r (run (str "native-public-refuse-" name) (cons F args) :ok false)]
              (chk (and (contains? #{1 2} (.-returncode r)) (u/has-bytes? (.encode code) (.-stderr r)) (not (u/has-bytes? (.encode "KEXE_TRAP") (.-stderr r)))) name)
              (.append refusals (pyenv "name" name "exit" (.-returncode r) "diagnostic" code))))
          (chk (and (not (.exists (o "refused.kseed"))) (not (.exists (o "c-linked.elf")))) "refusal artifacts")
          (let [report (pyenv "status" "PASS_COMPLETE_NATIVE_X86_COMPILER_BUILD"
                              "host" (python/list [(platform/system) (platform/machine) (platform/release)])
                              "generations" generations "sourceUnity" (pin full) "armBuildReceipt" (pin arm-proof)
                              "coreAdoption" (read-json (rp (g (read-json (rp "seed/compiler-core.json")) "adoptionReceipt")))
                              "cdci" roles "cases" ledger "nativeCDCIExecutionQualified" false
                              "publicNativeEntry" (pyenv "pinnedCheck" true "pinnedCompile" (pin (o "public-good.kseed")) "refusals" refusals)
                              "cCompilerOrLoader" false "JVMNodeOrGraalFallback" false "emulation" false)]
            (.write_text (o "complete-x86.json") (u/json-dump report))
            (println (g report "status") "F1=F2=F3" (g (operator/getitem generations 0) "sha256"))
            (.flush sys/stdout)))))))

(defn -main [& args]
  (run-main (.resolve (pathlib/Path (or (u/opt args "--compiler") (sys/exit "--compiler is required"))))
            (.resolve (pathlib/Path (or (u/opt args "--arm-proof") (sys/exit "--arm-proof is required"))))
            (.resolve (pathlib/Path (or (u/opt args "--output") (sys/exit "--output is required"))))))

(when (some #(or (= % "check-complete-x86.cljc") (str/ends-with? % "/check-complete-x86.cljc")) sys/argv)
  (apply -main *command-line-args*))
