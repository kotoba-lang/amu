;; The combined compiler (JUN-331): the adopted core plus the Linux targets in one image. Ported from
;; check-one-compiler.py (Basilisp, JUN-974); the Python docstring has the full four-step contract.
;;
;; Input (--bootstrap) is a selfhost-bootstrap output (arm64 Linux): S3.elf or F1.elf, P-aarch64.elf (the packed
;; core), S-x86_64.elf and runner.kotoba. No C compiler or loader, no emulation. Records, natively: Pw (the packed
;; static-profile core and its fixed point), F1 = F2 = F3 and the image F packs, F's core route (the adoption
;; image), F's Linux targets against S3's bytes and the pinned runtime cases, the CDCI roles, the public-entry
;; refusals, and the source-lock file boundary (source_lock_checks.cljc, named here for the CI closure).
;; Run (arm64 Linux): basilisp run -p scripts/seed scripts/seed/check-one-compiler.cljc -- --bootstrap DIR --output DIR
(ns check-one-compiler
  (:require [basilisp.string :as str]
            [gate-util :as u]
            [source-lock-checks :as slc])
  (:import json operator os pathlib platform re shutil subprocess sys))

(def root u/root)
(defn rp [rel] (pathlib/Path root rel))
(def stack "8388608")

(defn g [m & ks] (reduce (fn [a k] (operator/getitem a k)) m ks))
(defn pin [p] (let [d (.read_bytes (pathlib/Path p))] (u/pydict "bytes" (python/len d) "sha256" (u/sha256-hex d))))
(defn chk [c m] (u/chk c (str m)))
(defn read-json [p] (json/loads (.read_text p)))
(defn pyenv [& kvs] (apply u/pydict kvs))
(defn tail [b n] (.decode (u/bslice b (max 0 (- (python/len b) n)) (python/len b)) "utf-8" "replace"))

(defn -main [& args]
  (let [boot (.resolve (pathlib/Path (or (u/opt args "--bootstrap") (sys/exit "--bootstrap is required"))))
        out (.resolve (pathlib/Path (or (u/opt args "--output") (sys/exit "--output is required"))))
        o (fn [n] (pathlib/Path out n))]
    (chk (and (= (platform/system) "Linux") (contains? #{"aarch64" "arm64"} (platform/machine))) "run on arm64 Linux")
    (.mkdir out ** :parents true :exist_ok false)
    (.mkdir (o "raw"))
    (let [calls (python/list [])
          run (fn [name argv env & {:keys [ok timeout] :or {ok true timeout 3600}}]
                (let [argv (mapv str argv)
                      full (let [d (pyenv "PATH" "/nonexistent")] (.update d env) d)
                      r (subprocess/run (python/list argv) ** :cwd out :env full :capture_output true :timeout timeout)]
                  (.write_bytes (pathlib/Path out "raw" (str name ".stdout")) (.-stdout r))
                  (.write_bytes (pathlib/Path out "raw" (str name ".stderr")) (.-stderr r))
                  (.append calls (u/pydict "name" name "argv" (python/list argv) "env" env "exit" (.-returncode r)))
                  (when ok (chk (and (= (.-returncode r) 0) (zero? (python/len (.-stderr r)))) [name (.-returncode r) (tail (.-stderr r) 400)]))
                  r))
          ;; Older bootstrap receipts provide S3 and P; tiered F-root receipts provide the complete compiler F1.
          baseline (if (.is_file (pathlib/Path boot "S3.elf")) "S3.elf" "F1.elf")
          core-producer (if (.is_file (pathlib/Path boot "P-aarch64.elf")) "P-aarch64.elf" baseline)
          ;; Keep bootstrap executables separate from the F1/Pw outputs below.
          S (o "bootstrap-target.elf") P (o "bootstrap-core.elf") runner (o "runner.kotoba")
          _ (shutil/copy2 (pathlib/Path boot baseline) S)
          _ (shutil/copy2 (pathlib/Path boot core-producer) P)
          _ (doseq [name ["S-x86_64.elf" "runner.kotoba"]] (shutil/copy2 (pathlib/Path boot name) (o name)))
          _ (.chmod S 0755)
          _ (.chmod P 0755)
          env (pyenv "KEXE_CAP_RESOURCES_35" (str out) "KEXE_STACK_BYTES" stack)
          unity (fn [manifest dst]
                  (let [paths (vec (filter #(and (seq %) (not (.startswith % "#"))) (.splitlines (.read_text (rp manifest)))))]
                    (.write_bytes dst (.join (u/bytes-of) (python/list (map #(operator/add (.read_bytes (rp %)) (u/bytes-of 10)) paths))))
                    (u/pydict-from (for [p (cons manifest paths)] [p (pin (rp p))]))))
          sources (u/pydict-from (for [[m n] [["seed/CORE-STATIC-MANIFEST" "core-static"] ["seed/FULL-MANIFEST" "full"]
                                              ["seed/MANIFEST" "adopted"] ["seed/X86_64-LINUX-SELFHOST-MANIFEST" "selfhost"]]]
                                   [m (unity m (o (str n ".kotoba")))]))
          full-paths (vec (rest (python/list (.keys (g sources "seed/FULL-MANIFEST")))))
          core-paths (vec (filter #(not= % "seed/99-entry.kotoba") (rest (python/list (.keys (g sources "seed/CORE-STATIC-MANIFEST"))))))
          _ (chk (= (vec (take (count core-paths) full-paths)) core-paths) "FULL-MANIFEST must preserve the entire adopted static core in order")
          core (fn [prod src name]
                 (run name [prod "compile" (o (str src ".kotoba")) "--target" "aarch64-macos" "--output" (o (str name ".kseed"))] env)
                 (pin (o (str name ".kseed"))))
          pack (fn [prod kseed name]
                 (run (str name "-pack") [prod "compile" runner "--target" "aarch64-linux" "--output" (o (str name ".elf")) "--format" "packed" "--payload" (o (str kseed ".kseed"))] env)
                 (.chmod (o (str name ".elf")) 0755)
                 (pin (o (str name ".elf"))))
          ;; 1. Pw, the packed core with the static-profile capacities
          kw (core P "core-static" "Kw")
          pw (pack S "Kw" "Pw")
          _ (chk (u/deq (core (o "Pw.elf") "core-static" "K2") kw) "Pw fixed point")
          ;; 2. F, the combined compiler
          f1 (core (o "Pw.elf") "full" "F1")
          f1-image (pack S "F1" "F1")
          f2 (core (o "F1.elf") "full" "F2")
          f2-image (pack (o "F1.elf") "F2" "F2")
          f3 (core (o "F2.elf") "full" "F3")
          _ (chk (and (u/deq f1 f2) (u/deq f2 f3)) "combined compiler fixed point")
          _ (chk (u/deq f1-image f2-image) "the image F packs differs from the one S3 packs")
          F (o "F2.elf")
          ;; 3. F's core route reproduces the adoption image
          adoption (read-json (rp (g (read-json (rp "seed/compiler-core.json")) "adoptionReceipt")))
          _ (chk (= (g (pin (o "adopted.kotoba")) "sha256") (g adoption "sourceUnitySHA256")) "adopted source drift")
          _ (core F "adopted" "A")
          _ (run "A-extract" [F "extract-native" (o "A.kseed") "--symbol" "main" "--output" (o "A.bin")] env)
          _ (chk (= (g (pin (o "A.bin")) "sha256") (g adoption "nativeImageSHA256")) "F's core route differs from the adoption image")
          ;; 4. F's Linux targets emit S3's bytes; the cases run against the pinned results
          results (python/list [])]
      (doseq [case (g (read-json (rp "seed/static-cases.json")) "cases")]
        (let [n (g case "name") src (o (str "case-" n ".kotoba"))
              _ (.write_text src (g case "source"))
              images (vec (for [[who prod] [["S3" S] ["F" F]]]
                            (let [dst (o (str "case-" n "-" who ".elf"))]
                              (run (str "case-" n "-" who) [prod "compile" src "--target" "aarch64-linux" "--output" dst "--format" "static"] env)
                              (.chmod dst 0755)
                              (pin dst))))]
          (chk (u/deq (first images) (second images)) ["case image differs" n])
          (let [r (run (str "case-" n) [(o (str "case-" n "-F.elf"))] (pyenv "KEXE_STRUCTURED_REPORT" "1" "KEXE_FUEL" "1000000" "KEXE_ALLOW" "-") :ok false)
                fuel (re/search (.encode ":remaining ([0-9]+)") (.-stdout r))
                observed (pyenv "exit" (.-returncode r) "remainingFuel" (when fuel (python/int (.group fuel 1))))]
            (chk (u/deq observed (g case "reference")) [n observed (g case "reference")])
            (.append results (let [row (pyenv "name" n "image" (second images))] (.update row observed) row)))))
      ;; Quote operands are data even when they look like qualified operations.
      (doseq [[name source expected] [["quoted-symbol" (rp "seed/tests/quoted-symbol.kotoba") 41]
                                      ["document-sha" (rp "test/fixtures/selfhost/document/native/document_sha256_test.kotoba") 15]
                                      ["keyword-map-keys" (rp "seed/tests/keyword-map-keys.kotoba") 42]
                                      ["keyword-unicode-scan" (rp "seed/tests/keyword-unicode-scan.kotoba") 42]]]
        (let [src (o (str name ".kotoba")) dst (o (str name ".elf"))]
          (shutil/copyfile source src)
          (run (str name "-compile") [F "compile" src "--target" "aarch64-linux" "--output" dst "--format" "static"] env)
          (.chmod dst 0755)
          (let [result (run (str name "-run") [dst] (pyenv "KEXE_STRUCTURED_REPORT" "1" "KEXE_FUEL" "off" "KEXE_ALLOW" "-"))]
            (chk (re/search (.encode (str ":result " expected "\\b")) (.-stdout result)) [name (.-stdout result)]))))
      (run "x86-compiler" [F "compile" (o "selfhost.kotoba") "--target" "x86_64-linux" "--output" (o "X-F.elf") "--format" "static"] env)
      (chk (u/deq (pin (o "X-F.elf")) (pin (o "S-x86_64.elf"))) "F's x86_64 compiler differs from S3's")
      ;; The public compiler and the two privileged CDCI roles are all emitted by this same complete compiler.
      (run "full-x86-compiler" [F "compile" (o "full.kotoba") "--target" "x86_64-linux" "--output" (o "F-x86_64.elf") "--format" "static"] env)
      (let [cdci-sources (python/dict)
            _ (doseq [name ["entry.kotoba" "runtime.kotoba" "controller.kotoba" "kotoba-gate.kotoba"]]
                (let [original (rp (str "seed/cdci/" name))]
                  (shutil/copy2 original (o (str "cdci-" name)))
                  (operator/setitem cdci-sources name (pin original))))
            cdci-images (python/dict)
            amu-gate (o "cdci-amu-selfhost.elf")
            _ (run "build-amu-selfhost-gate" [F "compile" (o "core-static.kotoba") "--target" "x86_64-linux" "--output" amu-gate "--format" "static"] env)
            policy (read-json (rp "seed/cdci/policy.json"))
            actual-amu-gate (pin amu-gate)
            expected-sha (g policy "amuSelfhostGateSHA256")
            _ (chk (= (g actual-amu-gate "sha256") expected-sha)
                   (str "Amu selfhost gate image differs from the pinned policy: expected sha256=" expected-sha ", got sha256=" (g actual-amu-gate "sha256") " bytes=" (g actual-amu-gate "bytes")))
            _ (operator/setitem cdci-images "amu-selfhost" actual-amu-gate)
            _ (doseq [[role source] [["controller" "controller.kotoba"] ["kotoba-native" "kotoba-gate.kotoba"]]]
                (let [dst (o (str "cdci-" role ".elf"))]
                  (run (str "cdci-build-" role) [F "cdci-build" role (o "cdci-entry.kotoba") (o "cdci-runtime.kotoba") (o (str "cdci-" source)) dst] env)
                  (operator/setitem cdci-images role (pin dst))))
            _ (chk (= (g cdci-images "kotoba-native" "sha256") (g policy "kotobaNativeGateSHA256")) "kotoba-native gate pin")
            ;; Public entry refusals are measured, including large diagnostics (JUN-334).
            good (o "public-good.kotoba")
            _ (.write_text good "(ns public-good (:export [main]))\n(defn main [] :i64 42)\n")
            _ (run "public-check" [F "check" good] env)
            source-lock (o "public-good.ksl")
            _ (.write_text source-lock (str "KSL1\nentry " good "\nfile " (g (pin good) "sha256") " " good "\n"))
            lock-digest (g (pin source-lock) "sha256")
            _ (run "public-pinned-check" [F "check" good "--source-lock" source-lock "--source-lock-sha256" lock-digest] env)
            binary-lock (o "public-binary.ksl")
            _ (.write_bytes binary-lock (u/bytes-of 0x4b 0x53 0x4c 0x31 10 0xff 10))
            unknown (o "public-unknown.kotoba")
            _ (.write_text unknown "(ns public-unknown (:export [main]))\n(defn main [] :i64 (amu-unresolved 0))\n")
            unknown-qualified (o "public-unknown-qualified.kotoba")
            _ (.write_text unknown-qualified "(ns public-unknown-qualified (:export [main]))\n(defn main [] :i64 (missing/op 0))\n")
            unsupported-kwmap (o "public-unsupported-kwmap.kotoba")
            _ (shutil/copyfile (rp "seed/tests/keyword-map-keys-unsupported.kotoba") unsupported-kwmap)
            malformed-kwmap (o "public-malformed-kwmap.kotoba")
            _ (shutil/copyfile (rp "seed/tests/keyword-map-keys-malformed.kotoba") malformed-kwmap)
            large (o "public-large-unknown.kotoba")
            _ (.write_bytes large (operator/add (.read_bytes (o "full.kotoba")) (.encode "\n(defn- public-unresolved [] :i64 (amu-unresolved 0))\n")))
            ;; JUN-579: `.cljk` is accepted by a lone `check` (positive control below); `.cljc` is retired.
            legacy (o "public-legacy.cljc")
            _ (.write_bytes legacy (.read_bytes good))
            sugar (o "public-sugar.cljk")
            _ (.write_bytes sugar (.read_bytes good))
            refusals (python/list [])
            containers-before (set (map str (python/list (.glob out "*.kseed"))))
            zeros (apply str (repeat 64 "0"))
            probes (vec (concat
                         [["c-linked-format" ["compile" good "--target" "x86_64-linux" "--output" (o "c-linked.elf") "--format" "platform-linked"] "E2"]
                          ["unknown-small" ["check" unknown] "E2101"]
                          ["unknown-qualified" ["check" unknown-qualified] "E6010"]
                          ["unsupported-keyword-map" ["check" unsupported-kwmap] "E2105"]
                          ["malformed-keyword-map" ["check" malformed-kwmap] "E2105"]
                          ["unknown-large" ["check" large] "E2101"]
                          ["legacy-source" ["check" legacy] "E1"]
                          ["sugar-compile" ["compile" sugar "--target" "aarch64-macos" "--output" (o "sugar.kseed")] "E1"]
                          ["sugar-locked" ["check" sugar "--source-lock" source-lock] "E1"]
                          ["default-target" ["compile" good "--output" (o "default.kseed")] "E2"]
                          ["unknown-target" ["compile" good "--target" "unknown" "--output" (o "target.kseed")] "E2"]
                          ["unknown-verb" ["unknown-verb" good] "E1"]
                          ["lock-digest-without-lock" ["check" good "--source-lock-sha256" lock-digest] "E6015"]
                          ["lock-digest-mismatch" ["check" good "--source-lock" source-lock "--source-lock-sha256" zeros] "E6015"]
                          ["binary-lock" ["check" good "--source-lock" binary-lock] "E6015"]
                          ["duplicate-lock-digest" ["check" good "--source-lock" source-lock "--source-lock-sha256" lock-digest "--source-lock-sha256" lock-digest] "E1"]
                          ["unused-check-target" ["check" good "--target" "unknown"] "E1"]
                          ["duplicate-output" ["compile" good "--target" "aarch64-macos" "--output" (o "one.kseed") "--output" (o "two.kseed")] "E1"]]
                         (for [[flag code] [["--module-lock" "E6015"] ["--source-lock" "E6015"] ["--profile" "E1"] ["--seal" "E1"] ["--unknown-flag" "E1"]]]
                           [(subs flag 2) ["compile" good "--target" "aarch64-macos" "--output" (o (str (subs flag 2) ".kseed")) flag (o "missing")] code])))]
        (doseq [[name pargs code] probes]
          (let [r (run (str "public-refuse-" name) (cons F pargs) env :ok false)]
            (chk (and (contains? #{1 2} (.-returncode r)) (re/search (.encode (str "\\b" code "\\b")) (.-stderr r))) [name (.-returncode r) (tail (.-stderr r) 500)])
            (chk (not (u/has-bytes? (.encode "KEXE_TRAP") (.-stderr r))) [name (tail (.-stderr r) 500)])
            (.append refusals (pyenv "name" name "exit" (.-returncode r) "diagnostic" code))))
        (chk (not (.exists (o "c-linked.elf"))) "c-linked output")
        (chk (= (set (map str (python/list (.glob out "*.kseed")))) containers-before) "refusal produced an artifact")
        (let [lock-boundary (slc/check-source-locks [F] (o "source-lock-boundary"))
              report (pyenv "status" "PASS_COMBINED_COMPILER"
                            "host" (python/list [(platform/system) (platform/machine) (platform/release)])
                            "sources" sources
                            "bootstrap" (pyenv "targetProducer" (let [d (pyenv "name" baseline)] (.update d (pin S)) d)
                                               "coreProducer" (let [d (pyenv "name" core-producer)] (.update d (pin P)) d)
                                               "receipt" (pin (pathlib/Path boot "selfhost-bootstrap.json")))
                            "Pw" (pyenv "container" kw "image" pw)
                            "F" (pyenv "containers" (python/list [f1 f2 f3]) "image" f1-image "packedByF" f2-image)
                            "coreRoute" (pyenv "native" (pin (o "A.bin")) "expected" (g adoption "nativeImageSHA256"))
                            "cases" results "x86_64Compiler" (pin (o "X-F.elf"))
                            "publicEntryRefusals" refusals
                            "completeX86Compiler" (pin (o "F-x86_64.elf"))
                            "cdci" (pyenv "sources" cdci-sources "images" cdci-images "executionQualified" false)
                            "sourceLockBoundary" lock-boundary
                            "cCompilerOrLoader" false "emulation" false)]
          (.write_text (o "calls.json") (str (json/dumps calls ** :indent 1) "\n"))
          (.write_text (o "one-compiler.json") (u/json-dump report))
          (println (g report "status") "F1=F2=F3" (subs (g f1 "sha256") 0 16) "image" (subs (g f1-image "sha256") 0 16) (python/len results) "cases")
          (.flush sys/stdout))))))

(when (some #(or (= % "check-one-compiler.cljc") (str/ends-with? % "/check-one-compiler.cljc")) sys/argv)
  (apply -main *command-line-args*))
