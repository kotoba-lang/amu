;; Check the boot packager's layout admission rule on Mac (ADR-0276 part A, JUN-479 b).
;;
;; A real kernel-v3 guest image is compiled, then its ELF program headers are changed one clause at a time. The
;; unchanged image and a kernel above the old text ceiling that still fits the budget are admitted; every other image
;; is refused with E7111. This checks the packager only; it executes no guest.
;; Ported from check-aiueos-layout-rule-macos-native.py (Basilisp, JUN-974).
;; Run: basilisp run -p scripts/seed scripts/seed/check-aiueos-layout-rule-macos-native.cljc -- --mac-build DIR
;;      --user-v5-slot FILE --output DIR
(ns check-aiueos-layout-rule-macos-native
  (:require [basilisp.string :as str]
            [aiueos-value-fixture :as value]
            [gate-util :as u]
            [macos-native-lib :as mac])
  (:import operator pathlib struct sys))

(def old-text-cap (- (* 2 1024 1024) 4096))   ; slot-v4 text ceiling before the rule
(def new-text-cap (- (* 3 1024 1024) 4096))   ; RW file offset minus the ELF header page
(defn- q [b off] (first (struct/unpack_from "<Q" b off)))

(defn main [{:keys [mac-build user-v5-slot output]}]
  (let [descriptor (u/read-json mac/root-descriptor)
        mac-build (pathlib/Path mac-build)
        report (u/read-json (.joinpath mac-build "mac-aiueos-user-target.json"))
        rows (vec (.get report "generations" (python/list)))
        _ (when (or (not= (.get report "status") "PASS_MAC_NATIVE_USER_TARGET_SELFHOST")
                    (not (u/deq (.get report "source") (u/geti descriptor "fullSource")))
                    (< (count rows) 2)
                    (not (u/deq (u/geti (last rows) "raw") (u/geti (nth rows (- (count rows) 2)) "raw"))))
            (mac/fail "Mac compiler is not bound to the current fixed point"))
        compiler (.joinpath mac-build (str "F" (u/geti (last rows) "number") "-signed.macho"))
        _ (when-not (u/deq (mac/verify-macho compiler) (u/geti (last rows) "signed")) (mac/fail "Mac fixed point changed"))
        out (.resolve (pathlib/Path output))
        _ (.mkdir out ** :parents false :exist_ok false)
        _ (.mkdir (.joinpath out "fixture"))
        source (.encode (value/user-source))
        _ (.write_bytes (.joinpath out "fixture/guest.kotoba") source)
        lock (.encode (str "KSL1\nentry /fixture/guest.kotoba\nroot /fixture\n"
                           "file " (u/sha256-hex source) " /fixture/guest.kotoba\n"))
        _ (.write_bytes (.joinpath out "guest.ksl") lock)
        _ (mac/native-run compiler out ["compile" "/fixture/guest.kotoba" "--target" "x86_64-aiueos-kernel-v3" "--artifact" "image"
                                        "--output" "guest-v3.elf" "--fuel" "1000000" "--source-path" "/fixture"
                                        "--source-lock" "guest.ksl" "--source-lock-sha256" (u/sha256-hex lock)])
        base (.read_bytes (.joinpath out "guest-v3.elf"))
        slot (.read_bytes (pathlib/Path user-v5-slot))
        _ (.write_bytes (.joinpath out "user-v5.slot") slot)
        _ (.write_bytes (.joinpath out "font.bin") (operator/add (struct/pack "<II" 0x46554941 1) (u/bytes-of-n (- 524288 8) 0)))
        ph (q base 32)
        rx-at ph
        rw-at (+ ph 56)
        rx-size (q base (+ rx-at 32))
        _ (when-not (and (< 77 rx-size) (<= rx-size old-text-cap)) (mac/fail "the guest kernel is not below the old text ceiling"))
        calls (python/list)
        attempt (fn [[name raw] admitted]
                  (.write_bytes (.joinpath out (str name ".elf")) raw)
                  (let [result (mac/native-run compiler out ["package-aiueos-boot" (str name ".elf") "--output" (str name ".efi")
                                                             "--font" "font.bin" "--user-slot" "user-v5.slot" "--pci-resources" "v1"]
                                               :expected (if admitted 0 1))
                        exists (.exists (.joinpath out (str name ".efi")))]
                    (when (or (not= admitted exists) (and (not admitted) (not (u/has-bytes? (.encode "E7111") (.-stderr result)))))
                      (mac/fail (str name (if admitted " was refused" " was admitted"))))
                    (.append calls (u/pydict "name" name "admitted" admitted))))
        edits (fn [name & changes]
                (let [raw (python/bytearray base)]
                  (doseq [[offset fmt v] changes] (struct/pack_into fmt raw offset v))
                  [name (python/bytes raw)]))
        rx-off (q base (+ rx-at 8))
        rw-vaddr (q base (+ rw-at 16))
        rw-memsz (q base (+ rw-at 40))]
    (attempt [ "unchanged" base ] true)
    ;; Positive control: text above the old 2 MiB ceiling, inside the budget (the RW offset is 3 MiB).
    (let [wide (+ old-text-cap 8192)]
      (attempt (edits "text-above-old-ceiling" [(+ rx-at 32) "<Q" wide] [(+ rx-at 40) "<Q" wide]) true))
    ;; Negative controls, one clause each.
    (attempt (edits "text-past-rw-offset" [(+ rx-at 32) "<Q" (+ new-text-cap 16)] [(+ rx-at 40) "<Q" (+ new-text-cap 16)]) false)
    (attempt (edits "overlap-by-file-offset" [(+ rw-at 8) "<Q" (- (+ rx-off rx-size) 4096)]) false)
    (attempt (edits "overlap-by-address" [(+ rx-at 32) "<Q" (+ (- rw-vaddr 0x101000) 4096)] [(+ rx-at 40) "<Q" (+ (- rw-vaddr 0x101000) 4096)]) false)
    (attempt (edits "rw-and-x" [(+ rw-at 4) "<I" 7]) false)
    (attempt (edits "rx-and-w" [(+ rx-at 4) "<I" 7]) false)
    (attempt (edits "misaligned-rw" [(+ rw-at 16) "<Q" (+ rw-vaddr 16)] [(+ rw-at 24) "<Q" (+ rw-vaddr 16)]) false)
    (attempt (edits "past-budget" [(+ rw-at 16) "<Q" 0x1000000] [(+ rw-at 24) "<Q" 0x1000000]) false)
    (attempt (edits "entry-in-rw" [24 "<Q" rw-vaddr]) false)
    (attempt (edits "fixed-region-inside-segment" [(+ rw-at 40) "<Q" (- rw-memsz 4096)]) false)
    (let [receipt (u/pydict "schema" "amu.mac-aiueos-layout-rule.v1" "status" "PASS_MAC_NATIVE_LAYOUT_RULE"
                            "compiler" (mac/pin compiler) "baseKernel" (u/pydict "bytes" (python/len base) "sha256" (u/sha256-hex base))
                            "oldTextCap" old-text-cap "newTextCap" new-text-cap
                            "calls" calls "guestExecution" false "releaseQualified" false)]
      (.write_text (.joinpath out "mac-aiueos-layout-rule.json") (u/json-dump receipt))
      (println (u/geti receipt "status") (u/geti (u/geti receipt "baseKernel") "sha256"))
      (.flush sys/stdout))))

(defn -main [& args]
  (main {:mac-build (or (u/opt args "--mac-build") (sys/exit "--mac-build is required"))
         :user-v5-slot (or (u/opt args "--user-v5-slot") (sys/exit "--user-v5-slot is required"))
         :output (or (u/opt args "--output") (sys/exit "--output is required"))}))

(when (some #(or (= % "check-aiueos-layout-rule-macos-native.cljc") (str/ends-with? % "/check-aiueos-layout-rule-macos-native.cljc")) sys/argv)
  (apply -main *command-line-args*))
