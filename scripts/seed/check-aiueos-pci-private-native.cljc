;; Stage native private PCI policy fixtures. QEMU execution is separate.
;; Ported from check-aiueos-pci-private-native.py (Basilisp). Linux only.
;; Run: basilisp run scripts/seed/check-aiueos-pci-private-native.cljc -- (--build DIR | --complete DIR) --output OUT
(ns check-aiueos-pci-private-native
  (:require [aiueos-native-proof :as proof]
            [basilisp.string :as str]
            [gate-util :as u])
  (:import json operator sys))

(def access
  "(ns entry (:export [main]))
(defn main [] :i64
 (let [selected (kernel-out-u32 3320 2147485712)
       raw (kernel-in-u32 3324)
       base (bit-and raw 4294967280)
       mmio (kernel-pci-mmio 0 1 0 base 4096)
       old (kernel-load-u32-4k mmio 4096 0)
       wrote (kernel-store-u32-4k mmio 4096 0 305419896)
       actual (kernel-load-u32-4k mmio 4096 0)
       restored (kernel-store-u32-4k mmio 4096 0 old)
       again (kernel-load-u32-4k mmio 4096 0)]
   (if (and (= selected 2147485712) (= wrote 305419896) (= actual 305419896)
            (= restored old) (= again old)) 42 0)))
")

(defn stage [compiler scope]
  (.mkdir scope)
  (let [source (.joinpath scope "entry.kotoba") lock (.joinpath scope "source.ksl")
        calls (python/list) artifacts (python/dict)
        env (python/dict {"PATH" "/nonexistent" "KEXE_STACK_BYTES" "8388608" "KEXE_CAP_RESOURCES_35" (str scope)})
        compile- (fn [name text bad]
                   (.write_text source text)
                   (.write_text lock (u/ksl-text source scope))
                   (let [dst (.joinpath scope (str name ".elf"))
                         args ["compile" (str source) "--target" "x86_64-aiueos-kernel-v1" "--artifact" "image" "--output" (str dst)
                               "--fuel" "1000000" "--source-path" (str scope) "--source-lock" (str lock)
                               "--source-lock-sha256" (u/geti (u/pin lock) "sha256")]
                         r (u/run-process (cons compiler args) env 240)]
                     (.append calls (u/pydict "name" name "exit" (.-returncode r) "stderr" (.decode (.-stderr r)) "sourceText" text))
                     (.write_text (.joinpath scope "calls.json") (u/json-dump calls))
                     (if bad
                       (u/chk (and (= 1 (.-returncode r)) (u/has-bytes? (.encode "E7106") (.-stderr r)) (not (.exists dst))) (u/geti calls -1))
                       (do
                         (u/chk (and (= 0 (.-returncode r)) (not (u/nonempty? (.-stderr r)))) (u/geti calls -1))
                         (let [ef (.joinpath scope (str name ".efi"))
                               q (u/run-process [compiler "package-aiueos-boot" dst "--output" ef "--pci-resources" "v1"] env 180)
                               _ (u/chk (and (= 0 (.-returncode q)) (not (u/nonempty? (.-stderr q)))) (.-stderr q))
                               wrong (.joinpath scope (str name "-missing-v6.efi"))
                               q2 (u/run-process [compiler "package-aiueos-boot" dst "--output" wrong] env 180)]
                           (u/chk (and (= 1 (.-returncode q2)) (u/has-bytes? (.encode "E7111") (.-stderr q2)) (not (.exists wrong))) (.-stderr q2))
                           (operator/setitem artifacts name (u/pydict "kernel" (u/pin dst) "efi" (u/pin ef))))))))]
    (compile- "access" access false)
    (compile- "wrong-identity" (.replace access "mmio 0 1 0" "mmio 0 2 0") false)
    (compile- "outside-bar" (.replace access "0 1 0 base 4096" "0 1 0 (+ base 16777216) 4096") false)
    (compile- "oversized" "(ns entry (:export [main]))\n(defn main [] :i64 (if (> (kernel-pci-mmio 0 1 0 2147483648 65537) 0) 42 0))\n" false)
    (compile- "zero-bytes" "(ns entry (:export [main]))\n(defn main [] :i64 (if (> (kernel-pci-mmio 0 1 0 2147483648 0) 0) 42 0))\n" false)
    (compile- "ram" (.replace access "0 1 0 base 4096" "0 1 0 1048576 4096") false)
    (compile- "literal-root" "(ns entry (:export [main]))\n(defn main [] :i64 (kernel-load-u32 2147483648 512 0))\n" true)
    (u/pydict "compiler" (u/pin compiler) "artifacts" artifacts "regionRefusals" 1 "missingV6Refusals" (python/len artifacts))))

(defn main [build out complete]
  (let [[graph producers _] (proof/load-native-producers :build build :complete complete)
        _ (.mkdir out ** :parents true :exist_ok false)
        routes (python/list (for [c producers] (stage c (.joinpath out (.-stem c)))))]
    (u/chk (u/deq (u/geti (u/geti routes 0) "artifacts") (u/geti (u/geti routes 1) "artifacts")))
    (let [report (u/pydict "status" "PASS_NATIVE_PRIVATE_PCI_PACKAGING"
                           "observer" (u/pin (.joinpath u/root "scripts/seed/check-aiueos-pci-private-native.cljc"))
                           "source" graph "routes" routes "guestExecution" false "fullKernel" false
                           "physicalHardware" false "nativeCDCI" false)]
      (.write_text (.joinpath out "native-private-pci.json") (u/json-dump report))
      (println (u/geti report "status")))))

(defn -main [& args]
  (let [[build out complete] (u/parse-build-complete-output args)]
    (main build out complete)))

(when (some #(or (= % "check-aiueos-pci-private-native.cljc") (str/ends-with? % "/check-aiueos-pci-private-native.cljc")) sys/argv)
  (apply -main *command-line-args*))
