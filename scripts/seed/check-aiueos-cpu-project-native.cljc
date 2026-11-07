;; Native CPU primitive fixture images; QEMU execution is observed separately.
;; Ported from check-aiueos-cpu-project-native.py (Basilisp). Linux only.
;; Run: basilisp run scripts/seed/check-aiueos-cpu-project-native.cljc -- (--build DIR | --complete DIR) --output OUT
(ns check-aiueos-cpu-project-native
  (:require [aiueos-native-proof :as proof]
            [basilisp.string :as str]
            [gate-util :as u])
  (:import sys))

(def template
  "(ns cpu (:export [main]))
(defn main [] :i64
  (let [leaf (kernel-cpuid-eax 0 0)
        bx (kernel-cpuid-ebx 0 0) cx (kernel-cpuid-ecx 0 0) dx (kernel-cpuid-edx 0 0)
        features (kernel-cpuid-edx 2147483649 0)
        cr0 (kernel-read-cr0) cr3 (kernel-read-cr3) cr4 (kernel-read-cr4)
        wrote0 (kernel-write-cr0 cr0) wrote3 (kernel-write-cr3 cr3) wrote4 (kernel-write-cr4 cr4)
        after0 (kernel-read-cr0) after3 (kernel-read-cr3) after4 (kernel-read-cr4)
        cs (kernel-read-cs) efer (kernel-read-msr 3221225600)
        oldfs (kernel-read-msr 3221225728)
        wrotefs (kernel-write-msr 3221225728 4294971392)
        newfs (kernel-read-msr 3221225728)
        restored (kernel-write-msr 3221225728 oldfs)
        afterfs (kernel-read-msr 3221225728)
        t0 (kernel-rdtsc) paused (kernel-pause) t1 (kernel-rdtsc)
        invalidated (kernel-invlpg 1089536) disabled (kernel-cli)]
    (if (and (> leaf 0) (< leaf 1024) VENDOR
             (= (bit-and features 536870912) 536870912)
             (= (bit-and cr0 2147483649) 2147483649) (> cr3 0) (= (bit-and cr3 4095) 0)
             (= (bit-and cr4 32) 32) (= cs 8) (= (bit-and efer 1280) 1280)
             (= wrote0 cr0) (= wrote3 cr3) (= wrote4 cr4)
             (= after0 cr0) (= after3 cr3) (= after4 cr4)
             (= wrotefs 4294971392) (= newfs 4294971392) (= restored oldfs) (= afterfs oldfs)
             (>= t1 t0) (= paused 0) (= invalidated 1089536) (= disabled 0)) 42 0)))
")

(defn- le32 [vendor i] (.from_bytes python/int (u/bslice vendor i (+ i 4)) "little"))

(def vendors
  (for [vendor [(.encode "GenuineIntel") (.encode "AuthenticAMD")]]
    (str "(and (= bx " (le32 vendor 0) ") (= dx " (le32 vendor 4) ") (= cx " (le32 vendor 8) "))")))

(def text (.replace template "VENDOR" (str "(or " (str/join " " vendors) ")")))

(defn main [build output complete]
  (let [[source producers _] (proof/load-native-producers :build build :complete complete)
        _ (.mkdir output ** :parents true :exist_ok false)
        routes (python/list)]
    (doseq [producer producers]
      (let [out (.joinpath output (.-stem producer))
            _ (.mkdir out)
            src (.joinpath out "cpu.kotoba") lock (.joinpath out "cpu.ksl")
            _ (.write_text src text)
            _ (.write_text lock (u/ksl-text src out))
            image (.joinpath out "cpu.elf") efi (.joinpath out "cpu.efi")
            commands [[(str producer) "compile" (str src) "--target" "x86_64-aiueos-kernel-v1" "--artifact" "image"
                       "--output" (str image) "--fuel" "1000000" "--source-path" (str out)
                       "--source-lock" (str lock) "--source-lock-sha256" (u/geti (u/pin lock) "sha256")]
                      [(str producer) "package-aiueos-boot" (str image) "--output" (str efi)]]
            calls (python/list)]
        (doseq [command commands]
          (let [r (u/run-process command (python/dict {"PATH" "/nonexistent" "KEXE_CAP_RESOURCES_35" (str out) "KEXE_STACK_BYTES" "8388608"}) 180)]
            (.append calls (u/pydict "argv" (python/list command) "exit" (.-returncode r) "stdout" (.decode (.-stdout r)) "stderr" (.decode (.-stderr r))))
            (u/chk (and (zero? (.-returncode r)) (not (u/nonempty? (.-stderr r)))) [command (.-returncode r) (.-stderr r)])))
        (.write_text (.joinpath out "commands.json") (u/json-dump calls))
        (.append routes (u/pydict "producer" (u/pin producer) "source" (u/pin src) "lock" (u/pin lock) "image" (u/pin image) "efi" (u/pin efi)))))
    (u/chk (and (u/deq (u/geti (u/geti routes 0) "image") (u/geti (u/geti routes 1) "image"))
                (u/deq (u/geti (u/geti routes 0) "efi") (u/geti (u/geti routes 1) "efi"))))
    (let [report (u/pydict "status" "PASS_NATIVE_CPU_PROJECT_IMAGES" "source" source "routes" routes
                           "qemuBoot" false "stiHltExecuted" false "fullKernel" false "nativeCDCI" false)]
      (.write_text (.joinpath output "native-cpu-project.json") (u/json-dump report))
      (println (u/geti report "status") "CPUID/CR/MSR/CS/TSC/pause/CLI/invlpg; guest execution pending"))))

(defn -main [& args]
  (let [[build out complete] (u/parse-build-complete-output args)]
    (main build out complete)))

(when (some #(or (= % "check-aiueos-cpu-project-native.cljc") (str/ends-with? % "/check-aiueos-cpu-project-native.cljc")) sys/argv)
  (apply -main *command-line-args*))
