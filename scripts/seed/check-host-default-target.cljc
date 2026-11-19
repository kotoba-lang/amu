;; An omitted --target is the entry's own host; the roots still refuse it (KOTOBA-174, ADR 0396).
;;
;; Each public entry names its own fixed host. The engine-neutral compiler roots keep refusing an omitted target
;; with E2. This stages bytes, launches the native processes and compares what they wrote; Amu does every check,
;; compile and refusal. Every assertion has a control that would fail if the property were absent. Ported from
;; check-host-default-target.py (Basilisp, JUN-974); the Python docstring has the full per-ISA contract.
;; Run: basilisp run -p scripts/seed scripts/seed/check-host-default-target.cljc -- --isa x86_64|aarch64|macos
;;      --output OUT [--compiler F] [--host H] [--reproduce]
(ns check-host-default-target
  (:require [basilisp.string :as str]
            [gate-util :as u]
            [macos-native-lib :as mac])
  (:import json operator os pathlib platform re subprocess sys))

(def source (.encode "(ns hello (:export [main]))\n(defn main [] :i64 42)\n"))
(defn rp [rel] (pathlib/Path u/root rel))

(defn sha [data] (u/sha256-hex data))
(defn pin [path] (let [raw (.read_bytes (pathlib/Path path))] (u/pydict "bytes" (python/len raw) "sha256" (sha raw))))
(defn need [c m] (when-not c (sys/exit (str "FAIL " m))))
(defn g [m & ks] (reduce (fn [a k] (operator/getitem a k)) m ks))
(defn read-json [p] (json/loads (.read_text p)))
(defn tail [b n] (.decode (u/bslice b (max 0 (- (python/len b) n)) (python/len b)) "utf-8" "replace"))
(defn starts? [raw prefix] (.startswith raw prefix))

(defn kind [raw]
  (cond (starts? raw (u/bytes-of 0 0x61 0x73 0x6d)) "wasm"
        (and (pos? (python/len raw)) (<= 0xa0 (operator/getitem raw 0) 0xbf)) "cbor"
        (starts? raw (u/bytes-of 0x7f 0x45 0x4c 0x46)) "elf"
        (starts? raw (u/hex->bytes "cffaedfe")) "macho"
        :else "other"))

(defn lane [calls out name]
  (let [d (pathlib/Path out name)]
    (.mkdir d ** :mode 0700)
    (.write_bytes (pathlib/Path d "hello.kotoba") source)
    d))

(defn run-proc
  "Run image in d; records the call; returns the CompletedProcess."
  [calls name image d args & {:keys [env timeout] :or {timeout 1200}}]
  (let [env (or env (u/pydict "PATH" "/nonexistent" "KEXE_ALLOW" "35,37,38,39" "KEXE_CAP_RESOURCES_35" (str d) "KEXE_STACK_BYTES" "8388608"))
        r (subprocess/run (python/list (concat [(str image)] (map str args))) ** :cwd d :env env :capture_output true :timeout timeout)]
    (swap! calls conj (u/pydict "name" name "image" (.-name (pathlib/Path image)) "argv" (python/list (map str args))
                                "exit" (.-returncode r) "stdoutSHA256" (sha (.-stdout r)) "stderrSHA256" (sha (.-stderr r))))
    r))

(defn outcome [r d output]
  (let [p (when output (pathlib/Path d output))]
    [(.-returncode r) (.-stdout r) (.-stderr r) (when (and p (.is_file p)) (.read_bytes p))]))

(defn same? [a b] (and (= (nth a 0) (nth b 0)) (u/deq (nth a 1) (nth b 1)) (u/deq (nth a 2) (nth b 2))
                       (if (and (nth a 3) (nth b 3)) (u/deq (nth a 3) (nth b 3)) (= (nil? (nth a 3)) (nil? (nth b 3))))))

(defn explicit
  ([args] (explicit args "x86_64-linux"))
  ([args target] (vec (concat [(nth args 0) (nth args 1) "--target" target] (drop 2 args)))))

(def refusals
  {"bare" [["compile" "hello.kotoba"] 1 "seed: E2 "]
   "default-format" [["compile" "hello.kotoba" "--output" "a.out"] 1 "seed: E2 "]
   "static" [["compile" "hello.kotoba" "--output" "a.out" "--format" "static"] 2 "seed: E1 "]})

(defn refuse-omitted [calls out image]
  (let [seen (python/dict)]
    (doseq [name ["bare" "default-format" "static"]]
      (let [[args code marker] (get refusals name)
            d (lane calls out (str "refuse-" name "-" (.-name (pathlib/Path image))))
            r (run-proc calls (str "refuse-omitted-" name) image d args)]
        (need (and (= (.-returncode r) code) (u/has-bytes? (.encode marker) (.-stderr r))
                   (not (u/has-bytes? (.encode "KEXE_TRAP") (.-stderr r))))
              (str (.-name (pathlib/Path image)) " must refuse an omitted target (" name ") with " (python/repr (.encode marker)) ": "
                   (.-returncode r) " " (tail (.-stderr r) 200)))
        (need (not (.exists (pathlib/Path d "a.out"))) (str name ": the refusal wrote output"))
        (operator/setitem seen name (u/pydict "exit" (.-returncode r) "diagnostic" (.strip marker)))))
    seen))

(defn linux? [machines] (and (= (platform/system) "Linux") (contains? machines (platform/machine))))

(defn check-x86 [compiler host out reproduce?]
  (need (linux? #{"x86_64"}) "native Linux x86_64 required")
  (let [product (read-json (rp "native-product.json"))
        calls (atom [])]
    (need (u/deq (pin compiler) (g product "image")) "compiler is not the pinned engine-neutral image")
    (need (u/deq (pin host) (g product "hostEntry" "image")) "host entry is not the pinned image")
    (need (and (= (g product "hostEntry" "target") (g product "hostEntry" "omittedTarget")) (= (g product "hostEntry" "target") "x86_64-linux"))
          "descriptor does not name x86_64-linux")
    (need (not (u/deq (pin host) (pin compiler))) "control: host entry and compiler are distinct images")
    (let [report (u/pydict "isa" "x86_64" "compiler" (pin compiler) "hostEntry" (pin host))]
      (when reproduce?
        (let [d (lane calls out "reproduce")
              names (filter #(and (seq %) (not (str/starts-with? % "#"))) (.splitlines (.read_text (rp "seed/FULL-MANIFEST"))))
              _ (.write_bytes (pathlib/Path d "full-unity.kotoba")
                              (.join (u/bytes-of) (python/list (map #(operator/add (.read_bytes (rp %)) (u/bytes-of 10)) names))))
              r (run-proc calls "reproduce-host-entry" compiler d
                          ["compile" "full-unity.kotoba" "--target" "x86_64-linux" "--output" "H.elf" "--format" "host-entry"]
                          :env (u/pydict "PATH" "/nonexistent" "KEXE_CAP_RESOURCES_35" (str d) "KEXE_STACK_BYTES" "8388608"))]
          (need (and (= (.-returncode r) 0) (zero? (python/len (.-stderr r)))) (str "native host-entry build failed: " (tail (.-stderr r) 400)))
          (need (u/deq (pin (pathlib/Path d "H.elf")) (pin host)) "native x86 compiler does not reproduce the host entry")
          (operator/setitem report "reproducedHostEntry" (pin (pathlib/Path d "H.elf")))))
      (let [forms [["static" ["compile" "hello.kotoba" "--output" "a.out" "--format" "static"]]
                   ["kx64-v1" ["compile" "hello.kotoba" "--output" "a.out" "--format" "kx64-v1"]]
                   ["kx64-runner" ["compile" "hello.kotoba" "--output" "a.out" "--format" "kx64-runner"]]
                   ["default-format" ["compile" "hello.kotoba" "--output" "a.out"]]
                   ["bare" ["compile" "hello.kotoba"]]]
            results (python/dict)]
        (doseq [[name args] forms]
          (let [a (lane calls out (str name "-omitted")) b (lane calls out (str name "-explicit")) c (lane calls out (str name "-compiler"))
                omitted (outcome (run-proc calls (str name "-omitted") host a args) a "a.out")
                on-host (outcome (run-proc calls (str name "-explicit") host b (explicit args)) b "a.out")
                on-compiler (outcome (run-proc calls (str name "-compiler") compiler c (explicit args)) c "a.out")]
            (need (and (same? omitted on-host) (same? on-host on-compiler))
                  (str name ": omitted target differs from explicit x86_64-linux " (vec (take 3 omitted)) " " (vec (take 3 on-host)) " " (vec (take 3 on-compiler))))
            (when (nth omitted 3)
              (need (not (#{"wasm" "cbor"} (kind (nth omitted 3)))) (str name ": omitted target wrote Wasm or Kototama")))
            (operator/setitem results name
                              (u/pydict "exit" (nth omitted 0)
                                        "output" (when (nth omitted 3)
                                                   (u/pydict "bytes" (python/len (nth omitted 3)) "sha256" (sha (nth omitted 3)) "kind" (kind (nth omitted 3))))))))
        (need (and (= (g results "static" "exit") 0) (= (g results "static" "output" "kind") "elf"))
              "positive: the omitted-target static compile must succeed with an ELF")
        (operator/setitem report "omittedEqualsExplicit" results)
        (let [program (pathlib/Path out "static-omitted/a.out")
              _ (.chmod program 0700)
              r (run-proc calls "execute-omitted-static" program (pathlib/Path out "static-omitted") []
                          :env (u/pydict "PATH" "/nonexistent" "KEXE_ALLOW" "-" "KEXE_FUEL" "1000000" "KEXE_STRUCTURED_REPORT" "1") :timeout 60)]
          (need (and (= (.-returncode r) 0) (re/search (.encode ":result 42\\b") (.-stdout r))) "omitted-target program did not run to 42")
          (operator/setitem report "nativeResult" 42)
          (let [w1 (lane calls out "wasm-host") w2 (lane calls out "wasm-compiler")
                wasm-args ["compile" "hello.kotoba" "--target" "wasm32-browser" "--output" "a.wasm"]
                wh (outcome (run-proc calls "explicit-wasm-host" host w1 wasm-args) w1 "a.wasm")
                wc (outcome (run-proc calls "explicit-wasm-compiler" compiler w2 wasm-args) w2 "a.wasm")]
            (need (same? wh wc) "explicit wasm32-browser differs between host entry and compiler")
            (need (and (= (nth wh 0) 0) (nth wh 3) (= (kind (nth wh 3)) "wasm")) "control: the Wasm detector must flag an explicit wasm32-browser output"))
          (let [gd (lane calls out "aarch64-explicit")
                arm (outcome (run-proc calls "explicit-aarch64-host" host gd (explicit (second (first forms)) "aarch64-linux")) gd "a.out")]
            (need (and (= (nth arm 0) 0) (nth arm 3) (not (u/deq (nth arm 3) (.read_bytes (pathlib/Path out "static-omitted/a.out")))))
                  "control: aarch64-linux output must differ from the omitted (x86_64-linux) output"))
          (let [static-args (second (first forms))
                default-args (second (nth forms 3))
                same-forms [["aarch64-linux-static" (explicit static-args "aarch64-linux")]
                            ["unknown-target" (explicit static-args "x86_64-bogus")]
                            ["unknown-target-default" (explicit default-args "kototama")]
                            ["target-later" ["compile" "hello.kotoba" "--output" "a.out" "--format" "static" "--target" "x86_64-linux"]]
                            ["check" ["check" "hello.kotoba"]]
                            ["compile-alone" ["compile"]]
                            ["no-arguments" []]]
                explicit-results (python/dict)]
            (doseq [[name args] same-forms]
              (let [a (lane calls out (str "same-" name "-host")) b (lane calls out (str "same-" name "-compiler"))
                    x (outcome (run-proc calls (str "same-" name "-host") host a args) a "a.out")
                    y (outcome (run-proc calls (str "same-" name "-compiler") compiler b args) b "a.out")]
                (need (same? x y) (str "explicit command line " name " differs between host entry and compiler"))
                (operator/setitem explicit-results name (nth x 0))))
            (doseq [name ["unknown-target" "unknown-target-default"]]
              (need (and (not= (g explicit-results name) 0) (not (.exists (pathlib/Path out (str "same-" name "-host/a.out")))))
                    (str name " must be refused without output")))
            (need (= (g explicit-results "check") 0) "control: check must succeed")
            (operator/setitem report "explicitUnchanged" explicit-results))
          (operator/setitem report "compilerRefusesOmitted" (refuse-omitted calls out compiler))
          (operator/setitem report "calls" (python/list @calls))
          report)))))

(defn check-aarch64 [root out]
  (need (linux? #{"aarch64" "arm64"}) "native Linux ARM64 required")
  (let [descriptor (read-json (rp "seed/bootstrap/aarch64-linux-static-root.json"))
        calls (atom [])]
    (need (u/deq (pin root) (g descriptor "image")) "root is not the pinned aarch64 root")
    (let [static-args ["compile" "hello.kotoba" "--output" "a.out" "--format" "static"]
          report (u/pydict "isa" "aarch64" "root" (pin root) "publicLinuxArm64Entry" nil)]
      (operator/setitem report "rootRefusesOmitted" (refuse-omitted calls out root))
      (let [d (lane calls out "explicit")
            r (run-proc calls "explicit-aarch64-linux" root d (explicit static-args "aarch64-linux"))]
        (need (and (= (.-returncode r) 0) (.is_file (pathlib/Path d "a.out")) (= (kind (.read_bytes (pathlib/Path d "a.out"))) "elf"))
              "control: the explicit aarch64-linux compile must succeed")
        (.chmod (pathlib/Path d "a.out") 0700)
        (let [r (run-proc calls "execute-explicit" (pathlib/Path d "a.out") d []
                          :env (u/pydict "PATH" "/nonexistent" "KEXE_ALLOW" "-" "KEXE_FUEL" "1000000" "KEXE_STRUCTURED_REPORT" "1") :timeout 60)]
          (need (and (= (.-returncode r) 0) (re/search (.encode ":result 42\\b") (.-stdout r))) "control: explicit program did not run to 42")))
      (let [d (lane calls out "unknown")
            r (run-proc calls "unknown-target" root d (explicit static-args "aarch64-bogus"))]
        (need (and (not= (.-returncode r) 0) (not (.exists (pathlib/Path d "a.out")))) "unknown target must be refused without output"))
      (operator/setitem report "calls" (python/list @calls))
      report)))

(defn check-macos [out]
  (need (and (= (platform/system) "Darwin") (= (platform/machine) "arm64")) "Apple Silicon required")
  (let [cli-descriptor (read-json (rp "seed/bootstrap/aarch64-macos/cli.json"))
        root-descriptor (read-json (rp "seed/bootstrap/aarch64-macos/root.json"))
        cli (rp (g cli-descriptor "entry"))
        root (rp (g root-descriptor "compiler" "path"))
        calls (atom [])
        report (u/pydict "isa" "macos" "cli" (pin cli) "root" (pin root))
        env (u/pydict "PATH" "/nonexistent" "LANG" "C")
        d (lane calls out "cli")
        r (run-proc calls "cli-compile-omitted" cli d ["compile" "hello.kotoba"] :env env :timeout 150)]
    (need (and (= (.-returncode r) 0) (.is_file (pathlib/Path d "hello"))) "public CLI omitted-target compile failed")
    (let [raw (.read_bytes (pathlib/Path d "hello"))]
      (need (= (kind raw) "macho") "omitted target on the public CLI must write Mach-O, not Wasm or Kototama")
      (let [r (run-proc calls "cli-run-artifact" cli d ["run" "./hello"] :env env :timeout 150)]
        (need (and (= (.-returncode r) 0) (u/deq (.-stdout r) (.encode "42\n")))
              "run must reproduce the artifact by an explicit aarch64-macos recompile"))
      (let [tampered (python/bytearray raw)
            i (quot (python/len tampered) 2)]
        (operator/setitem tampered i (bit-xor (operator/getitem tampered i) 1))
        (.write_bytes (pathlib/Path d "tampered") (python/bytes tampered))
        (.chmod (pathlib/Path d "tampered") 0700)
        (let [r (run-proc calls "cli-run-tampered" cli d ["run" "./tampered"] :env env :timeout 150)]
          (need (and (not= (.-returncode r) 0) (not (u/deq (.-stdout r) (.encode "42\n")))) "control: a tampered artifact must be refused")))
      (doseq [target ["aarch64-macos" "wasm32-browser" "kototama" "aarch64-bogus"]]
        (let [r (run-proc calls (str "cli-explicit-" target) cli d ["compile" "hello.kotoba" "--target" target "-o" (str "x-" target)] :env env :timeout 150)]
          (need (and (= (.-returncode r) 2) (not (.exists (pathlib/Path d (str "x-" target)))))
                (str "public CLI must keep refusing an explicit --target " target " (usage)"))))
      (operator/setitem report "cli" (u/pydict "omittedTarget" "aarch64-macos" "artifact" (u/pydict "bytes" (python/len raw) "sha256" (sha raw)))))
    (let [root-dir (lane calls out "root")
          r (mac/native-run root root-dir ["compile" "hello.kotoba" "--output" "a.kseed"] :expected 1)]
      (need (and (u/has-bytes? (.encode "seed: E2 ") (.-stderr r)) (not (.exists (pathlib/Path root-dir "a.kseed")))) "Mac root must refuse an omitted target with E2")
      (let [r (mac/native-run root root-dir ["compile" "hello.kotoba" "--target" "aarch64-bogus" "--output" "b.kseed"] :expected 1)]
        (need (and (u/has-bytes? (.encode "seed: E2 ") (.-stderr r)) (not (.exists (pathlib/Path root-dir "b.kseed")))) "Mac root must refuse an unknown target with E2, no output"))
      (mac/native-run root root-dir ["compile" "hello.kotoba" "--target" "aarch64-macos" "--output" "c.kseed"])
      (need (.is_file (pathlib/Path root-dir "c.kseed")) "control: the explicit aarch64-macos root compile must succeed")
      (operator/setitem report "rootRefusesOmitted" (u/pydict "E2" true))
      (operator/setitem report "calls" (python/list @calls))
      report)))

(defn -main [& args]
  (let [isa (or (u/opt args "--isa") (sys/exit "--isa is required"))
        out (.resolve (pathlib/Path (or (u/opt args "--output") (sys/exit "--output is required"))))
        compiler (u/opt args "--compiler")
        host (u/opt args "--host")
        _ (when-not (#{"x86_64" "aarch64" "macos"} isa) (sys/exit "--isa must be x86_64, aarch64 or macos"))
        _ (.mkdir out ** :parents true :mode 0700 :exist_ok false)
        report (case isa
                 "x86_64" (check-x86 (.resolve (if compiler (pathlib/Path compiler) (rp "bin/amu-linux-x86_64")))
                                     (.resolve (if host (pathlib/Path host) (rp "bin/x86_64-linux/amu"))) out
                                     (boolean (some #{"--reproduce"} args)))
                 "aarch64" (check-aarch64 (.resolve (if compiler (pathlib/Path compiler) (rp "seed/bootstrap/aarch64-linux-static-root.elf"))) out)
                 (check-macos out))]
    (.update report (u/pydict "schema" "amu.host-default-target.v1" "status" "PASS_HOST_DEFAULT_TARGET" "decision" "KOTOBA-174" "adr" "0396"
                              "kototamaOrWasmDefault" false
                              "observer" (pin (rp "scripts/seed/check-host-default-target.cljc"))))
    (.write_text (pathlib/Path out "host-default-target.json") (u/json-dump report))
    (println "PASS_HOST_DEFAULT_TARGET" isa (python/len (g report "calls")) "native calls")))

(when (some #(or (= % "check-host-default-target.cljc") (str/ends-with? % "/check-host-default-target.cljc")) sys/argv)
  (apply -main *command-line-args*))
