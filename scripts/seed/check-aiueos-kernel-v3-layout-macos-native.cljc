;; Check kernel-v3 layout, guest mapping and slot-v4 package admission on Mac.
;; The signed native artifact gate does not execute a guest or qualify a typed ABI.
;; Ported from check-aiueos-kernel-v3-layout-macos-native.py (Basilisp, JUN-974).
;; Run: basilisp run -p scripts/seed scripts/seed/check-aiueos-kernel-v3-layout-macos-native.cljc -- --mac-build DIR
;;      --user-v5-slot FILE --output DIR
(ns check-aiueos-kernel-v3-layout-macos-native
  (:require [basilisp.string :as str]
            [aiueos-value-fixture :as value]
            [gate-util :as u]
            [macos-native-lib :as mac])
  (:import operator pathlib struct sys))

(def source (.encode "(ns layout-probe (:export [main]))\n(defn main [] :i64 42)\n"))
(def window-source
  (.encode
   (str "(ns request-window-probe\n"
        "  (:export [main aiueos-value-runtime-entry aiueos-value-runtime-syscall-plan\n"
        "            aiueos-value-runtime-publish-domain aiueos-value-runtime-provider-status\n"
        "            aiueos-value-runtime-capability-grant aiueos-value-runtime-provider-claim\n"
        "            aiueos-value-runtime-provider-complete aiueos-value-runtime-cas-verify]))\n"
        "(defn aiueos-value-runtime-entry [a :i64 b :i64 c :i64 d :i64 e :i64] :i64 0)\n"
        "(defn aiueos-value-runtime-syscall-plan [a :i64 b :i64 c :i64 d :i64 e :i64] :i64 0)\n"
        "(defn aiueos-value-runtime-publish-domain [a :i64] :i64 0)\n"
        "(defn aiueos-value-runtime-provider-status [a :i64 b :i64] :i64 0)\n"
        "(defn aiueos-value-runtime-capability-grant [a :i64 b :i64 c :i64 d :i64 e :i64] :i64 0)\n"
        "(defn aiueos-value-runtime-provider-claim [] :i64 0)\n"
        "(defn aiueos-value-runtime-provider-complete [a :i64 b :i64 c :i64 d :i64 e :i64] :i64 0)\n"
        "(defn aiueos-value-runtime-cas-verify [a :i64 b :i64 c :i64 d :i64 e :i64] :i64 0)\n"
        "(defn main [] :i64\n"
        "  (let [request (kernel-value-domain-request-page 73)\n"
        "        final-page (kernel-subregion request 262144 196608 65536)]\n"
        "    (if (= request 0) 0\n"
        "      (kernel-load-u8-64k final-page 65536 65535))))\n")))

(defn- q [b off] (first (struct/unpack_from "<Q" b off)))
(defn- qs [fmt b off] (vec (struct/unpack_from fmt b off)))
(defn- stderr-has? [result code] (u/has-bytes? (.encode code) (.-stderr result)))
(defn- lock-for [name raw]
  (.encode (str "KSL1\nentry /fixture/" name ".kotoba\nroot /fixture\nfile " (u/sha256-hex raw) " /fixture/" name ".kotoba\n")))

(defn image-layout [raw address]
  (when (or (< (python/len raw) 176) (not (u/deq (u/bslice raw 0 7) (u/hex->bytes "7f454c46020101"))))
    (mac/fail "kernel is not ELF64"))
  (let [ph (q raw 32)
        [rx rw] (for [i (range 2)] (qs "<IIQQQQQQ" raw (+ ph (* i 56))))]
    (when (or (not= (q raw 24) 0x101000)
              (not= (subvec rx 0 5) [1 5 4096 0x101000 0x101000])
              (not (and (< 77 (nth rx 5)) (= (nth rx 5) (nth rx 6))
                        (<= (nth rx 6) (- (if (>= address 0x300000) 2097152 1048576) 4096))))
              (not= (subvec rw 0 5) [1 6 (- address 0x100000) address address])
              (not= (nth rw 5) (nth rw 6)) (not= (nth rw 7) 4096)
              (> (+ (nth rw 2) (nth rw 5)) (python/len raw)))
      (mac/fail "kernel segment boundary changed"))
    (u/pydict "rx" (python/list rx) "rw" (python/list rw))))

(defn main [{:keys [mac-build user-v5-slot output]}]
  (let [descriptor (u/read-json mac/root-descriptor)
        mac-build (pathlib/Path mac-build)
        report (u/read-json (.joinpath mac-build "mac-aiueos-user-target.json"))
        rows (vec (.get report "generations" (python/list)))
        prev (when (>= (count rows) 2) (nth rows (- (count rows) 2)))
        _ (when (or (not= (.get report "status") "PASS_MAC_NATIVE_USER_TARGET_SELFHOST")
                    (not (u/deq (.get report "source") (u/geti descriptor "fullSource")))
                    (not (u/deq (.get report "bootstrapDescriptor") (mac/pin mac/root-descriptor)))
                    (< (count rows) 2)
                    (some (fn [k] (not (u/deq (u/geti (last rows) k) (u/geti prev k)))) ["container" "raw" "unsigned"]))
            (mac/fail "Mac compiler is not bound to the current fixed point"))
        compiler (.joinpath mac-build (str "F" (u/geti (last rows) "number") "-signed.macho"))
        _ (when-not (u/deq (mac/verify-macho compiler) (u/geti (last rows) "signed")) (mac/fail "Mac fixed point changed"))
        reference (u/geti descriptor "kernelV2ReferenceCompiler")
        old (.joinpath u/root (u/geti reference "path"))
        _ (when-not (u/deq (mac/verify-macho old) (u/pydict "bytes" (u/geti reference "bytes") "sha256" (u/geti reference "sha256")))
            (mac/fail "kernel-v2 reference compiler pin changed"))
        out (.resolve (pathlib/Path output))
        _ (.mkdir out ** :parents false :exist_ok false)
        _ (.mkdir (.joinpath out "fixture"))
        _ (.write_bytes (.joinpath out "fixture/entry.kotoba") source)
        lock (lock-for "entry" source)
        _ (.write_bytes (.joinpath out "fixture.ksl") lock)
        calls (python/list)
        compile-with (fn compile-with
                       ([producer version name] (compile-with producer version name 0))
                       ([producer version name expected]
                        (let [dest (str name ".elf")
                              result (mac/native-run producer out ["compile" "/fixture/entry.kotoba" "--target" (str "x86_64-aiueos-kernel-" version)
                                                                   "--artifact" "image" "--output" dest "--fuel" "1000000" "--source-path" "/fixture"
                                                                   "--source-lock" "fixture.ksl" "--source-lock-sha256" (u/sha256-hex lock)]
                                                     :expected expected)]
                          (when (or (u/has-bytes? (.encode "KEXE_TRAP") (.-stderr result)) (and (pos? expected) (.exists (.joinpath out dest))))
                            (mac/fail (str name " failed open")))
                          (.append calls (u/pydict "producer" (mac/pin producer) "target" version "exit" (.-returncode result)
                                                   "stderr" (let [s (.decode (.-stderr result))] (subs s 0 (min 400 (count s))))))
                          (.joinpath out dest))))
        legacy (python/list)
        _ (doseq [[version address] [["v1" 0x200000] ["v2" 0x300000]]]
            (let [baseline (compile-with old version (str "old-" version))
                  current (compile-with compiler version (str "new-" version))]
              (when-not (u/deq (mac/pin baseline) (mac/pin current)) (mac/fail (str version " changed under the new compiler")))
              (image-layout (.read_bytes current) address)
              (.append legacy (u/pydict "target" version "elf" (mac/pin current)))))
        v3 (compile-with compiler "v3" "new-v3")
        layout (image-layout (.read_bytes v3) 0x400000)
        _ (compile-with old "v3" "old-v3-refused" 2)
        ;; Compiler-only control: the linked exports below are inert fixtures, not a guest ValueRuntime. The final byte
        ;; of v5's 64-page RW window must be statically rooted; the same source must fail under the v2 extent.
        _ (.write_bytes (.joinpath out "fixture/window.kotoba") window-source)
        window-lock (lock-for "window" window-source)
        _ (.write_bytes (.joinpath out "window.ksl") window-lock)
        window-args ["--artifact" "image" "--fuel" "1000000" "--source-path" "/fixture" "--source-lock" "window.ksl"
                     "--source-lock-sha256" (u/sha256-hex window-lock)]
        _ (mac/native-run compiler out (concat ["compile" "/fixture/window.kotoba" "--target" "x86_64-aiueos-kernel-v3"] window-args ["--output" "window-v3.elf"]))
        window-v3 (.joinpath out "window-v3.elf")
        _ (image-layout (.read_bytes window-v3) 0x400000)
        refused-window (mac/native-run compiler out (concat ["compile" "/fixture/window.kotoba" "--target" "x86_64-aiueos-kernel-v2"] window-args ["--output" "window-v2.elf"]) :expected 1)
        _ (when (or (not (stderr-has? refused-window "E7106")) (.exists (.joinpath out "window-v2.elf")))
            (mac/fail "v2 admitted the 256 KiB request extent"))
        _ (mac/native-run compiler out ["package-aiueos-boot" (.-name v3) "--output" "kernel-v3.efi"])
        slot (.read_bytes (pathlib/Path user-v5-slot))
        _ (when (or (not= (python/len slot) 524288) (not= (qs "<QQ" slot 0) [0x0031444c50554941 4]))
            (mac/fail "user-v5 slot input changed"))
        _ (.write_bytes (.joinpath out "user-v5.slot") slot)
        _ (.write_bytes (.joinpath out "font.bin") (operator/add (struct/pack "<II" 0x46554941 1) (u/bytes-of-n (- 524288 8) 0)))
        result (mac/native-run compiler out ["package-aiueos-boot" (.-name v3) "--output" "mixed-v3-v5.efi" "--font" "font.bin"
                                             "--user-slot" "user-v5.slot" "--pci-resources" "v1"] :expected 1)
        _ (when (or (not (stderr-has? result "E7111")) (.exists (.joinpath out "mixed-v3-v5.efi")))
            (mac/fail "guest-incompatible slot-v4 admitted"))
        guest-source (.encode (value/user-source))
        _ (.write_bytes (.joinpath out "fixture/guest.kotoba") guest-source)
        guest-lock (lock-for "guest" guest-source)
        _ (.write_bytes (.joinpath out "guest.ksl") guest-lock)
        _ (mac/native-run compiler out ["compile" "/fixture/guest.kotoba" "--target" "x86_64-aiueos-kernel-v3" "--artifact" "image"
                                        "--output" "guest-v3.elf" "--fuel" "1000000" "--source-path" "/fixture"
                                        "--source-lock" "guest.ksl" "--source-lock-sha256" (u/sha256-hex guest-lock)])
        guest (.joinpath out "guest-v3.elf")
        guest-raw (.read_bytes guest)
        guest-layout (image-layout guest-raw 0x400000)
        guest-rw (vec (u/geti guest-layout "rw"))
        guest-rx (vec (u/geti guest-layout "rx"))
        marker (q guest-raw (+ (nth guest-rw 2) 464))
        handler (q guest-raw (+ (nth guest-rw 2) 30400))
        _ (when (or (not= (nth guest-rw 5) 0x240000) (not= marker 0x354c5652)
                    (not (and (<= (nth guest-rx 3) handler) (< handler (+ (nth guest-rx 3) (nth guest-rx 5))))))
            (mac/fail "guest-v3 mapping or syscall handler missing"))
        _ (mac/native-run compiler out ["package-aiueos-boot" (.-name guest) "--output" "guest-v3-v5.efi" "--font" "font.bin"
                                        "--user-slot" "user-v5.slot" "--pci-resources" "v1"])
        efi (.read_bytes (.joinpath out "guest-v3-v5.efi"))
        _ (when (or (not= (.count efi guest-raw) 1) (not= (.count efi slot) 1))
            (mac/fail "guest-v3 EFI lacks pinned kernel or slot"))]
    (doseq [[name offset] [["marker" 464] ["handler" 30400]]]
      (let [changed (python/bytearray guest-raw)]
        (struct/pack_into "<Q" changed (+ (nth guest-rw 2) offset) 0)
        (.write_bytes (.joinpath out (str name ".elf")) changed)
        (let [r (mac/native-run compiler out ["package-aiueos-boot" (str name ".elf") "--output" (str name ".efi") "--font" "font.bin"
                                              "--user-slot" "user-v5.slot" "--pci-resources" "v1"] :expected 1)]
          (when (or (not (stderr-has? r "E7111")) (.exists (.joinpath out (str name ".efi"))))
            (mac/fail (str "changed guest-v3 " name " admitted"))))))
    (let [receipt (u/pydict "schema" "amu.mac-aiueos-kernel-v3-layout-candidate.v2" "status" "PASS_MAC_NATIVE_KERNEL_V3_GUEST_ARTIFACT"
                            "compiler" (mac/pin compiler) "oldCompiler" (mac/pin old)
                            "source" (u/pydict "bytes" (python/len source) "sha256" (u/sha256-hex source))
                            "sourceLock" (mac/pin (.joinpath out "fixture.ksl")) "legacy" legacy
                            "kernelV3" (mac/pin v3) "efiV3" (mac/pin (.joinpath out "kernel-v3.efi"))
                            "windowSource" (u/pydict "bytes" (python/len window-source) "sha256" (u/sha256-hex window-source))
                            "windowSourceLock" (mac/pin (.joinpath out "window.ksl"))
                            "windowKernelV3" (mac/pin window-v3) "windowV2ExtentRefused" true "windowGuestExecution" false
                            "layout" layout "oldCompilerV3Refused" true "dualSlotV4RefusedForScalar" true
                            "guestV5Admission" true "guestExecution" false
                            "guestSource" (u/pydict "bytes" (python/len guest-source) "sha256" (u/sha256-hex guest-source))
                            "guestSourceLock" (mac/pin (.joinpath out "guest.ksl"))
                            "guestKernel" (mac/pin guest) "guestEfi" (mac/pin (.joinpath out "guest-v3-v5.efi"))
                            "guestLayout" guest-layout "guestMarker" marker "guestHandler" handler
                            "changedMarkerRefused" true "changedHandlerRefused" true
                            "releaseQualified" false "linuxJVMNodeCompiler" false "calls" calls)]
      (.write_text (.joinpath out "mac-aiueos-kernel-v3-layout.json") (u/json-dump receipt))
      (println (u/geti receipt "status") (u/geti (u/geti receipt "kernelV3") "sha256"))
      (.flush sys/stdout))))

(defn -main [& args]
  (main {:mac-build (or (u/opt args "--mac-build") (sys/exit "--mac-build is required"))
         :user-v5-slot (or (u/opt args "--user-v5-slot") (sys/exit "--user-v5-slot is required"))
         :output (or (u/opt args "--output") (sys/exit "--output is required"))}))

(when (some #(or (= % "check-aiueos-kernel-v3-layout-macos-native.cljc") (str/ends-with? % "/check-aiueos-kernel-v3-layout-macos-native.cljc")) sys/argv)
  (apply -main *command-line-args*))
