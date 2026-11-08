;; Qualify native Mac AIUEOS font+user-slot EFI packaging and refusals.
;;
;; This stages pinned inputs and observes. The selfhost Amu image packages both payloads and the legacy control without
;; Linux, JVM, Node or C compiler. Ported from check-aiueos-dual-payload-macos-native.py (Basilisp, JUN-974).
;; Run: basilisp run -p scripts/seed scripts/seed/check-aiueos-dual-payload-macos-native.cljc -- --compiler F
;;      --compiler-sha256 H --compiler-receipt F --kernel F --font F --slot F --legacy-efi F --output DIR
(ns check-aiueos-dual-payload-macos-native
  (:require [basilisp.string :as str]
            [gate-util :as u]
            [macos-native-lib :as mac])
  (:import json pathlib shutil sys))

(def observer-path (.joinpath u/root "scripts/seed/check-aiueos-dual-payload-macos-native.cljc"))
(def source-names ["seed/78-full-entry.kotoba" "seed/84-aiueos-boot.kotoba"
                   "seed/86-aiueos-kernel-runtime.kotoba" "seed/97-aiueos-desktop-regions.kotoba"])

(defn main [{:keys [compiler compiler-sha256 compiler-receipt kernel font slot legacy-efi output]}]
  (let [[compiler compiler-receipt kernel font slot legacy-efi output]
        (map #(pathlib/Path %) [compiler compiler-receipt kernel font slot legacy-efi output])
        _ (when (some (fn [p] (or (.is_symlink p) (not (.is_file p)))) [compiler compiler-receipt kernel font slot legacy-efi])
            (mac/fail "all inputs must be regular non-symlink files"))
        _ (when (.exists output) (mac/fail "output must be a new private directory"))
        _ (mac/verify-macho compiler)
        _ (when (not= (u/geti (mac/pin compiler) "sha256") compiler-sha256) (mac/fail "compiler digest mismatch"))
        receipt (u/read-json compiler-receipt)
        gens (.get receipt "generations")
        _ (when (or (not= (.get receipt "status") "PASS_MAC_NATIVE_USER_TARGET_SELFHOST") (not (seq gens))
                    (not (u/deq (.get (last gens) "signed") (mac/pin compiler)))
                    (< (.get receipt "fixedPointGeneration" 0) 2))
            (mac/fail "compiler lacks a matching Mac selfhost fixed-point receipt"))
        sources (into {} (for [row (u/geti receipt "sources")] [(u/geti row "name") row]))]
    (doseq [name source-names]
      (when-not (u/deq (mac/pin (.joinpath u/root name)) (u/pydict "bytes" (u/geti (get sources name) "bytes") "sha256" (u/geti (get sources name) "sha256")))
        (mac/fail (str "fixed-point compiler source drift: " name))))
    (when (or (not= (u/geti (mac/pin font) "bytes") 524288) (not= (u/geti (mac/pin slot) "bytes") 524288))
      (mac/fail "font and user slot must each be 512 KiB"))
    (.mkdir output ** :mode 0700)
    (doseq [[src name] [[kernel "KERNEL.ELF"] [font "font.bin"] [slot "user-slot.bin"]]]
      (shutil/copyfile src (.joinpath output name)))
    (let [compiler (.resolve compiler ** :strict true)
          run (fn [name options expected]
                (mac/native-run compiler output (concat ["package-aiueos-boot" "KERNEL.ELF" "--output" name] options) :expected expected))
          dual ["--font" "font.bin" "--user-slot" "user-slot.bin" "--pci-resources" "v1"]
          p (fn [n] (.joinpath output n))]
      (run "dual.efi" dual 0)
      (run "dual.reproduced.efi" dual 0)
      (let [actual (.read_bytes (p "dual.efi"))]
        (when-not (u/deq actual (.read_bytes (p "dual.reproduced.efi"))) (mac/fail "native dual EFI reproduction mismatch"))
        (let [kernel-b (.read_bytes kernel) font-b (.read_bytes font) slot-b (.read_bytes slot)]
          (when (or (not= (.count actual kernel-b) 1) (not= (.count actual font-b) 1) (not= (.count actual slot-b) 1)
                    (not= (.index actual slot-b) (+ (.index actual font-b) 524288)))
            (mac/fail "dual payload bytes or order mismatch"))
          (run "legacy.efi" ["--payload" "font.bin" "--pci-resources" "v1"] 0)
          (when-not (u/deq (.read_bytes (p "legacy.efi")) (.read_bytes legacy-efi)) (mac/fail "legacy single-font EFI bytes changed"))
          (let [refusals (u/pydict)]
            (doseq [[kind original offset] [["font-magic" font-b 0] ["slot-magic" slot-b 0] ["slot-version" slot-b 8]]]
              (let [changed (python/bytearray original)
                    changed-name (str kind ".bin")
                    font-name (if (= kind "font-magic") changed-name "font.bin")
                    slot-name (if (not= kind "font-magic") changed-name "user-slot.bin")
                    output-name (str kind ".efi")]
                (.__setitem__ changed offset (bit-xor (.__getitem__ changed offset) 1))
                (.write_bytes (p changed-name) changed)
                (let [result (run output-name ["--font" font-name "--user-slot" slot-name "--pci-resources" "v1"] 1)]
                  (when (or (not (u/has-bytes? (.encode "E7111") (.-stderr result))) (.exists (p output-name)))
                    (mac/fail (str kind " did not refuse before output")))
                  (.__setitem__ refusals kind (u/pydict "changedByte" offset "outputAbsent" true "code" "E7111")))))
            (let [result (run "missing.efi" ["--font" "font.bin" "--user-slot" "missing.bin" "--pci-resources" "v1"] 1)]
              (when (or (not (u/has-bytes? (.encode "E3") (.-stderr result))) (.exists (p "missing.efi")))
                (mac/fail "missing user slot did not refuse"))
              (.__setitem__ refusals "missing-slot" (u/pydict "outputAbsent" true "code" "E3")))
            (let [result (run "dual.efi" dual 2)]
              (when-not (u/has-bytes? (.encode "E7110") (.-stderr result)) (mac/fail "existing output was not refused"))
              (.__setitem__ refusals "existing-output" (u/pydict "code" "E7110")))
            (when (some (fn [[src name]] (not (u/deq (mac/pin src) (mac/pin (p name)))))
                        [[kernel "KERNEL.ELF"] [font "font.bin"] [slot "user-slot.bin"]])
              (mac/fail "native input changed during packaging"))
            (let [report (u/pydict "schema" "amu.macos-aiueos-dual-payload.v1" "status" "PASS_MAC_NATIVE_AIUEOS_DUAL_PAYLOAD_AND_REFUSALS"
                                   "compiler" (mac/pin compiler) "compilerReceipt" (mac/pin compiler-receipt)
                                   "kernel" (mac/pin kernel) "font" (mac/pin font) "userSlot" (mac/pin slot)
                                   "dualEfi" (mac/pin (p "dual.efi")) "dualReproducedEfi" (mac/pin (p "dual.reproduced.efi"))
                                   "legacyEfi" (mac/pin (p "legacy.efi")) "legacyReference" (mac/pin legacy-efi)
                                   "refusals" refusals
                                   "sources" (u/pydict-from (for [name source-names] [name (mac/pin (.joinpath u/root name))]))
                                   "observer" (mac/pin observer-path) "macNativePackaging" true
                                   "linuxJVMNodeOrCCompilerInThisGate" false "guestBootQualified" false "releaseQualified" false)]
              (.write_text (p "dual-payload-macos-native.json") (u/json-dump report))
              (println (u/geti report "status") (u/geti (u/geti report "dualEfi") "sha256"))
              (.flush sys/stdout))))))))

(defn -main [& args]
  (let [need (fn [k] (or (u/opt args k) (sys/exit (str k " is required"))))]
    (main {:compiler (need "--compiler") :compiler-sha256 (need "--compiler-sha256") :compiler-receipt (need "--compiler-receipt")
           :kernel (need "--kernel") :font (need "--font") :slot (need "--slot") :legacy-efi (need "--legacy-efi")
           :output (need "--output")})))

(when (some #(or (= % "check-aiueos-dual-payload-macos-native.cljc") (str/ends-with? % "/check-aiueos-dual-payload-macos-native.cljc")) sys/argv)
  (apply -main *command-line-args*))
