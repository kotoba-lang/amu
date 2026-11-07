;; Stage public metadata forgery and an intentionally corrupted PCI handoff.
;;
;; Only fixed test inputs and one declared EFI corruption are staged here.
;; The admitted native compiler emits every kernel and loader instruction.
;; The corrupted EFI is a refusal control and cannot qualify a device grant.
;; Ported from check-aiueos-pci-forgery-native.py (Basilisp). Linux only.
;; Run: basilisp run scripts/seed/check-aiueos-pci-forgery-native.cljc -- (--build DIR | --complete DIR) --output OUT
(ns check-aiueos-pci-forgery-native
  (:require [aiueos-native-proof :as proof]
            [basilisp.string :as str]
            [gate-util :as u])
  (:import json operator sys))

;; ACCESS is the fixture of the private-PCI gate (the Python original read it with runpy).
(load-file (str (.joinpath u/root "scripts/seed/check-aiueos-pci-private-native.cljc")))
(def access @(resolve 'check-aiueos-pci-private-native/access))

(def fields [0x31494350534f4941 1 1 64 1048576 4096 0 0 1 0 0 286331444])

(def prefix
  (str "(let [boot (kernel-subregion (kernel-boot-info) 16544 0 160)\n fake (kernel-owned-page 14)\n"
       (apply str (map-indexed (fn [i value] (str " f" i " (kernel-store-u64-4k fake 4096 " (* 8 i) " " value ")\n")) fields))
       " fp (kernel-store-u64 boot 160 144 fake)\n fn (kernel-store-u64 boot 160 152 96)\n selected"))

(def forged (.replace access "(let [selected" prefix))
(def absent "(ns entry (:export [main]))\n(defn main [] :i64 (if (= (kernel-pci-mmio 0 1 0 0 4096) 0) 42 0))\n")

(defn main [build out complete]
  (let [[graph producers _] (proof/load-native-producers :build build :complete complete)
        _ (.mkdir out ** :parents true :exist_ok false)
        routes (python/list)]
    (doseq [c producers]
      (let [scope (.joinpath out (.-stem c))
            _ (.mkdir scope)
            src (.joinpath scope "entry.kotoba") lock (.joinpath scope "source.ksl")
            calls (python/list) artifacts (python/dict)
            env (python/dict {"PATH" "/nonexistent" "KEXE_CAP_RESOURCES_35" (str scope) "KEXE_STACK_BYTES" "8388608"})]
        (doseq [[name text] [["public-forgery" forged]
                             ["forged-ram" (.replace forged "0 1 0 base 4096" "0 1 0 1048576 4096")]
                             ["absent" absent]
                             ["protected-overlap" access]]]
          (.write_text src text)
          (.write_text lock (u/ksl-text src scope))
          (let [image (.joinpath scope (str name ".elf")) efi (.joinpath scope (str name ".efi"))
                args ["compile" src "--target" "x86_64-aiueos-kernel-v1" "--artifact" "image" "--output" image "--fuel" "1000000"
                      "--source-path" scope "--source-lock" lock "--source-lock-sha256" (u/geti (u/pin lock) "sha256")]
                r (u/run-process (cons c args) env 240)]
            (.append calls (u/pydict "name" name "exit" (.-returncode r) "stderr" (.decode (.-stderr r)) "sourceText" text))
            (u/chk (and (= 0 (.-returncode r)) (not (u/nonempty? (.-stderr r)))) (u/geti calls -1))
            (let [r2 (u/run-process [c "package-aiueos-boot" image "--output" efi "--pci-resources" "v1"] env 180)]
              (u/chk (and (= 0 (.-returncode r2)) (not (u/nonempty? (.-stderr r2)))) (.-stderr r2)))
            (operator/setitem artifacts name (u/pydict "kernel" (u/pin image) "originalEfi" (u/pin efi)))
            (when (= name "protected-overlap")
              (let [raw (.read_bytes efi)
                    before (u/hex->bytes "488d7c0720488b860e000000")]
                (u/chk (= 1 (.count raw before)) "unique collector record writer required")
                (let [at (+ (.index raw before) 5)
                      changed (operator/add (operator/add (u/bslice raw 0 at) (u/hex->bytes "b8000010009090")) (u/bslice raw (+ at 7) nil))]
                  (u/chk (and (= 1 (.count changed (.read_bytes image))) (= (python/len changed) (python/len raw))))
                  (.write_bytes efi changed)
                  (let [art (u/geti artifacts name)]
                    (operator/setitem art "mutatedEfi" (u/pin efi))
                    (operator/setitem art "mutation"
                                      (u/pydict "offset" at "before" (.hex (u/bslice raw at (+ at 7))) "after" (.hex (u/bslice changed at (+ at 7)))
                                                "meaning" "replace collected BAR base with RAM1048576; negative handoff control only"))))))))
        (.write_text (.joinpath scope "calls.json") (u/json-dump calls))
        (.append routes (u/pydict "compiler" (u/pin c) "artifacts" artifacts))))
    (u/chk (u/deq (u/geti (u/geti routes 0) "artifacts") (u/geti (u/geti routes 1) "artifacts")))
    (let [report (u/pydict "status" "PASS_NATIVE_PCI_FORGERY_PACKAGING"
                           "observer" (u/pin (.joinpath u/root "scripts/seed/check-aiueos-pci-forgery-native.cljc"))
                           "source" graph "routes" routes "guestExecution" false "fullKernel" false "nativeCDCI" false)]
      (.write_text (.joinpath out "native-pci-forgery.json") (u/json-dump report))
      (println (u/geti report "status")))))

(defn -main [& args]
  (let [[build out complete] (u/parse-build-complete-output args)]
    (main build out complete)))

(when (some #(or (= % "check-aiueos-pci-forgery-native.cljc") (str/ends-with? % "/check-aiueos-pci-forgery-native.cljc")) sys/argv)
  (apply -main *command-line-args*))
