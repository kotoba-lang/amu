;; Cross-build Linux compiler candidates from the Mac native Amu fixed point.
;;
;; A Mac producer gate. It does not execute or qualify the Linux images. By default the candidates must equal
;; the checked-in root and public images, so a source change is refused here as stale. --produce-candidates
;; skips that comparison, records the receipt status MAC_NATIVE_CROSS_CANDIDATES_UNADOPTED and leaves every
;; descriptor and image untouched. Ported from check-macos-cross-linux-candidates.py (Basilisp, JUN-974).
;; Run: basilisp run -p scripts/seed scripts/seed/check-macos-cross-linux-candidates.cljc -- --mac-build DIR
;;      --output DIR [--produce-candidates]
(ns check-macos-cross-linux-candidates
  (:require [basilisp.string :as str]
            [gate-util :as u]
            [macos-native-lib :as mac])
  (:import json operator os pathlib platform shutil struct sys))

(def root u/root)
(defn rp [rel] (pathlib/Path root rel))
(def descriptor-path (rp "seed/bootstrap/aarch64-macos/root.json"))
(def full-manifest (rp "seed/FULL-MANIFEST"))
(def selfhost-manifest (rp "seed/X86_64-LINUX-SELFHOST-MANIFEST"))
(def runner-source (rp "seed/x86_64-kx64-runner.kotoba"))
(def product-path (rp "native-product.json"))
(def arm-root-path (rp "seed/bootstrap/aarch64-linux-static-root.json"))
(def arm-image (rp "seed/bootstrap/aarch64-linux-static-root.elf"))
(def x86-image (rp "bin/amu-linux-x86_64"))
(def host-image (rp "bin/x86_64-linux/amu"))   ; KOTOBA-174 / ADR 0396

(defn fail [m] (throw (python/ValueError m)))
(defn pin [p] (u/pin p))
(defn jget [m & ks] (reduce (fn [a k] (operator/getitem a k)) m ks))
(defn jhas? [m k] (operator/contains m k))
(defn read-json [p] (json/loads (.read_text p)))

(defn stage [manifest output]
  (let [names (vec (filter #(and (seq %) (not (str/starts-with? % "#"))) (.splitlines (.read_text manifest))))]
    (when (or (empty? names) (not= (count names) (count (set names)))) (fail "empty or duplicate manifest entries"))
    (with-open [stream (.open output "wb")]
      (doseq [name names]
        (let [part (pathlib/Path name)
              parts (vec (.-parts part))]
          (when (or (.is_absolute part) (some #{".."} parts) (empty? parts) (not= (first parts) "seed"))
            (fail "invalid manifest source path"))
          (let [source (pathlib/Path root part)]
            (when (or (.is_symlink source) (not (.is_file source))) (fail "manifest source must be a regular file"))
            (.write stream (operator/add (.read_bytes source) (u/bytes-of 10)))))))
    (u/pydict "modules" (count names) "manifest" (pin manifest) "unity" (pin output))))

(defn static-elf [path machine]
  (let [raw (.read_bytes path)
        bad (fn [m] (fail (str m (.-name path))))]
    (when (or (not (u/deq (u/bslice raw 0 8) (u/bytes-of 0x7f 0x45 0x4c 0x46 2 1 1 0)))
              (not (u/deq (struct/unpack_from "<HH" raw 16) (python/tuple [2 machine]))))
      (bad "wrong static ELF target: "))
    (let [offset (first (struct/unpack_from "<Q" raw 32))
          [size cnt] (struct/unpack_from "<HH" raw 54)]
      (when (or (not= size 56) (not (< 0 cnt 17)) (> (+ offset (* cnt size)) (python/len raw)))
        (bad "invalid ELF program headers: "))
      (let [types (map (fn [i] (first (struct/unpack_from "<I" raw (+ offset (* i size))))) (range cnt))]
        (when (or (some #{2} types) (some #{3} types)) (bad "dynamic image or interpreter: "))))
    (pin path)))

(defn check-product-bindings [full arm x86 host]
  (let [product (read-json product-path)
        rt (read-json arm-root-path)]
    (when (or (not (u/deq (jget full "unity") (jget product "sourceUnity")))
              (not (u/deq (jget full "unity") (jget rt "sourceUnity")))
              (not= (jget full "modules") (jget product "sourceModuleCount"))
              (not= (jget product "sourceManifest") "seed/FULL-MANIFEST")
              (not= (jget rt "sourceManifest") "seed/FULL-MANIFEST"))
      (fail "Mac candidate source differs from root/product descriptors"))
    (when (or (not (u/deq arm (jget rt "image"))) (not (u/deq arm (jget product "rootImage"))) (not (u/deq arm (pin arm-image))))
      (fail "Mac ARM fixed point differs from checked-in root image"))
    (when (or (not (u/deq x86 (jget product "image"))) (not (u/deq x86 (pin x86-image))))
      (fail "Mac x86 fixed point differs from checked-in public image"))
    (when (or (not= (jget product "hostEntry" "target") "x86_64-linux")
              (not (u/deq host (jget product "hostEntry" "image")))
              (not (.is_file host-image)) (.is_symlink host-image)
              (not (u/deq host (pin host-image))))
      (fail "Mac x86 host entry differs from checked-in host entry"))))

(defn run [mac-build output produce?]
  (when (or (not= (platform/system) "Darwin") (not (#{"arm64" "aarch64"} (platform/machine))))
    (fail "Apple Silicon native host required"))
  (when (or (.is_symlink mac-build) (not (.is_dir mac-build))) (fail "regular Mac build directory required"))
  (let [descriptor (read-json descriptor-path)
        report-path (pathlib/Path mac-build "mac-aiueos-user-target.json")
        report (read-json report-path)
        pick (fn [m ks] (u/pydict-from (for [k ks] [k (jget m k)])))
        bd (.get report "bootstrapDescriptor")
        explicit-root (and (nil? bd)
                           (u/deq (.get report "compiler") (pick (jget descriptor "compiler") ["bytes" "sha256"]))
                           (u/deq (.get report "packager") (pick (jget descriptor "packager") ["bytes" "sha256"])))
        desc-pin (pin descriptor-path)]
    (when (or (not= (.get report "status") "PASS_MAC_NATIVE_USER_TARGET_SELFHOST")
              (and (not produce?) (not (u/deq bd desc-pin)))
              (and produce? (not (u/deq bd desc-pin)) (not explicit-root))
              (and (not produce?) (not (u/deq (.get report "source") (jget descriptor "fullSource"))))
              (not= (.get report "fixedPointGeneration") (python/len (jget report "generations")))
              (< (python/len (jget report "generations")) 2))
      (fail "Mac selfhost report is not bound to this source and root"))
    (let [gens (jget report "generations")
          final (operator/getitem gens -1)
          previous (operator/getitem gens -2)]
      (when (some #(not (u/deq (jget final %) (jget previous %))) ["container" "raw" "unsigned"])
        (fail "Mac compiler source fixed point is absent"))
      (let [producer (pathlib/Path mac-build (str "F" (jget final "number") "-signed.macho"))]
        (when-not (u/deq (mac/verify-macho producer) (jget final "signed")) (fail "Mac fixed-point image changed"))
        (.mkdir output ** :parents true :exist_ok false :mode 0700)
        (let [full (stage full-manifest (pathlib/Path output "full-unity.kotoba"))
              selfhost (stage selfhost-manifest (pathlib/Path output "selfhost-unity.kotoba"))
              _ (when-not (u/deq (jget full "unity") (jget report "source")) (fail "current full source differs from Mac gate"))
              _ (shutil/copyfile runner-source (pathlib/Path output "runner.kotoba"))
              runner (pin (pathlib/Path output "runner.kotoba"))
              nr (fn [& args] (mac/native-run producer output (vec args)))]
          (nr "compile" "full-unity.kotoba" "--target" "aarch64-macos" "--output" "F.kseed")
          (let [container (pin (pathlib/Path output "F.kseed"))
                expected (if produce? (jget final "container" "sha256") (jget descriptor "expectedFixedPoint" "compilerContainerSha256"))]
            (when (not= (jget container "sha256") expected) (fail "Mac producer changed the full compiler container"))
            (nr "compile" "runner.kotoba" "--target" "aarch64-linux" "--output" "F-aarch64.elf" "--format" "packed" "--payload" "F.kseed")
            (let [arm (static-elf (pathlib/Path output "F-aarch64.elf") 183)
                  _ (nr "compile" "full-unity.kotoba" "--target" "x86_64-linux" "--output" "F-x86_64.elf" "--format" "static")
                  x86 (static-elf (pathlib/Path output "F-x86_64.elf") 62)
                  _ (nr "compile" "full-unity.kotoba" "--target" "x86_64-linux" "--output" "H-x86_64.elf" "--format" "host-entry")
                  host (static-elf (pathlib/Path output "H-x86_64.elf") 62)]
              (when (u/deq host x86) (fail "host entry is the root image: the host start is missing"))
              (when-not produce? (check-product-bindings full arm x86 host))
              (nr "compile" "selfhost-unity.kotoba" "--target" "x86_64-linux" "--output" "S-x86_64.elf" "--format" "static")
              (let [x86-selfhost (static-elf (pathlib/Path output "S-x86_64.elf") 62)]
                (when (or (not (u/deq (mac/verify-macho producer) (jget final "signed")))
                          (and (not explicit-root) (not (u/deq (pin descriptor-path) (jget report "bootstrapDescriptor")))))
                  (fail "Mac producer inputs changed during cross build"))
                (let [status (if produce? "MAC_NATIVE_CROSS_CANDIDATES_UNADOPTED" "MAC_NATIVE_CROSS_ARTIFACTS_UNEXECUTED")
                      rpt (u/pydict "schema" "amu.mac-cross-linux-candidates.v1" "status" status
                                    "macSelfhostReport" (pin report-path) "producer" (jget final "signed")
                                    "fullSource" full "selfhostSource" selfhost "runnerSource" runner
                                    "container" container "aarch64Root" arm
                                    "x86FullCompiler" x86 "x86HostEntry" host "x86SelfhostCompiler" x86-selfhost
                                    "linuxProcessInThisGate" false "nativeLinuxExecutionQualified" false
                                    "observer" (pin (rp "scripts/seed/check-macos-cross-linux-candidates.cljc")))]
                  (.write_text (pathlib/Path output "cross.json") (u/json-dump rpt))
                  (println status (jget arm "sha256") (jget x86 "sha256")))))))))))

(defn -main [& args]
  (run (.resolve (pathlib/Path (or (u/opt args "--mac-build") (sys/exit "--mac-build is required"))))
       (.resolve (pathlib/Path (or (u/opt args "--output") (sys/exit "--output is required"))))
       (boolean (some #{"--produce-candidates"} args))))

(when (some #(or (= % "check-macos-cross-linux-candidates.cljc") (str/ends-with? % "/check-macos-cross-linux-candidates.cljc")) sys/argv)
  (apply -main *command-line-args*))
