;; Build Amu to a Mac native fixed point and check the user-target ELF (library half of
;; check-aiueos-user-macos-native; also called by the user-v2/v3/v5 and other Mac gates).
;;
;; This stages pinned source bytes and observes native processes. The signed compiler and packager are explicit
;; inputs; no Linux, JVM, Node or C compiler process is part of this Mac gate. This is compiler/artifact evidence,
;; not a guest, Itonami turn or release qualification. Ported from the main half of
;; check-aiueos-user-macos-native.py (Basilisp, JUN-974). Apple Silicon macOS only.
(ns macos-user-target
  (:require [aiueos-user-elf :as elf]
            [gate-util :as u]
            [macos-native-lib :as mac])
  (:import json operator pathlib re shutil struct sys))

(def fs2-product (.joinpath u/root "seed/tests/fs2-product.kotoba"))
(def user-check (.joinpath u/root "scripts/seed/check-aiueos-user-elf-native.cljc"))
(def observer-path (.joinpath u/root "scripts/seed/check-aiueos-user-macos-native.cljc"))
(def root-paths {"compiler" "seed/bootstrap/aarch64-macos/amu-full-root.macho"
                 "packager" "seed/bootstrap/aarch64-macos/kotoba-packager-root.macho"})

(defn- pin-keys [d] (u/pydict "bytes" (u/geti d "bytes") "sha256" (u/geti d "sha256")))
(defn- extract-match [stdout] (re/search (.encode ":offset (\\d+), :length (\\d+), :arity 0}") stdout))

(defn bootstrap-inputs
  "[compiler compiler-sha packager packager-sha descriptor descriptor-pin] from explicit args or the root descriptor."
  [{:keys [compiler-image compiler-sha256 packager-image packager-sha256]}]
  (let [fields [compiler-image compiler-sha256 packager-image packager-sha256]]
    (if (some some? fields)
      (do (when-not (every? some? fields) (mac/fail "explicit bootstrap requires both image paths and SHA-256 pins"))
          [(.resolve (pathlib/Path compiler-image) ** :strict true) compiler-sha256
           (.resolve (pathlib/Path packager-image) ** :strict true) packager-sha256 nil nil])
      (let [descriptor-pin (mac/require-regular mac/root-descriptor)
            descriptor (u/read-json mac/root-descriptor)]
        (when (or (not= (.get descriptor "schema") "amu.macos-arm64-selfhost-root.v1")
                  (not= (.get descriptor "status") "diagnostic-candidate")
                  (not= (.get descriptor "fullManifest") "seed/FULL-MANIFEST"))
          (mac/fail "unsupported Mac bootstrap descriptor"))
        (doseq [[role expected] root-paths]
          (when (not= (u/geti (u/geti descriptor role) "path") expected) (mac/fail (str "Mac bootstrap role path changed: " role)))
          (let [path (.joinpath u/root expected)]
            (when-not (u/deq (mac/require-regular path (u/geti (u/geti descriptor role) "sha256")) (pin-keys (u/geti descriptor role)))
              (mac/fail (str "Mac bootstrap role size changed: " role)))))
        (let [ps (u/geti descriptor "packagerSource")]
          (when (or (not= (u/geti ps "path") "seed/macos-fs2-runtime-packager.kotoba")
                    (not (u/deq (mac/require-regular mac/packager-source (u/geti ps "sha256")) (pin-keys ps))))
            (mac/fail "Mac packager source changed")))
        [(.joinpath u/root (get root-paths "compiler")) (u/geti (u/geti descriptor "compiler") "sha256")
         (.joinpath u/root (get root-paths "packager")) (u/geti (u/geti descriptor "packager") "sha256")
         descriptor descriptor-pin]))))

(defn rebuild-packager [producer packager directory compiler-row]
  (shutil/copyfile mac/packager-source (.joinpath directory "packager.kotoba"))
  (mac/native-run producer directory ["compile" "packager.kotoba" "--target" "aarch64-macos" "--output" "P1.kseed"])
  (let [extracted (mac/native-run producer directory ["extract-native" "P1.kseed" "--symbol" "main" "--output" "P1.raw"])
        m (extract-match (.-stdout extracted))]
    (when (or (nil? m) (not= (python/int (.group m 2)) (.-st_size (.stat (.joinpath directory "P1.raw")))))
      (mac/fail "Mac packager main extraction did not match raw bytes"))
    (let [entry (python/int (.group m 1))
          p (fn [n] (.joinpath directory n))]
      (mac/native-run packager directory ["P1-unsigned.macho" "P1.raw" "fs2-cli-stdio-general" (str entry)])
      (mac/sign (p "P1-unsigned.macho") (p "P1-signed.macho"))
      (mac/native-run (p "P1-signed.macho") directory ["P2-unsigned.macho" "P1.raw" "fs2-cli-stdio-general" (str entry)])
      (when-not (u/deq (mac/pin (p "P1-unsigned.macho")) (mac/pin (p "P2-unsigned.macho")))
        (mac/fail "Mac packager did not repackage itself byte for byte"))
      (mac/native-run (p "P1-signed.macho") directory ["F3-unsigned.macho" (str "F" (u/geti compiler-row "number") ".raw")
                                                       "fs2-cli-stdio-general" (str (u/geti compiler-row "entry"))])
      (when-not (u/deq (mac/pin (p "F3-unsigned.macho")) (u/geti compiler-row "unsigned"))
        (mac/fail "rebuilt Mac packager changed the full compiler image"))
      (u/pydict "source" (mac/pin mac/packager-source) "container" (mac/pin (p "P1.kseed")) "raw" (mac/pin (p "P1.raw"))
                "entry" entry "unsigned" (mac/pin (p "P1-unsigned.macho")) "repackagedUnsigned" (mac/pin (p "P2-unsigned.macho"))
                "repackagedCompilerUnsigned" (mac/pin (p "F3-unsigned.macho"))))))

(defn main
  "args: {:compiler-image :compiler-sha256 :packager-image :packager-sha256 :output} (output a pathlib.Path)."
  [args]
  (when-not (mac/available?) (mac/fail "Mac native user-target gate requires Apple Silicon"))
  (let [[compiler compiler-sha packager packager-sha descriptor descriptor-pin] (bootstrap-inputs args)
        compiler-pin (mac/require-regular compiler compiler-sha)
        packager-pin (mac/require-regular packager packager-sha)
        manifest-pin (mac/require-regular mac/manifest)
        checker-pin (mac/require-regular user-check)
        fs2-product-pin (mac/require-regular fs2-product)
        packager-source-pin (mac/require-regular mac/packager-source)
        _ (mac/verify-macho compiler)
        _ (mac/verify-macho packager)
        output (.resolve (pathlib/Path (:output args)))
        _ (.mkdir output ** :parents false :mode 0700 :exist_ok false)
        [sources unity] (mac/stage-unity output)
        _ (when (and (some? descriptor) (not (u/deq unity (u/geti descriptor "fullSource"))))
            (mac/fail "Mac bootstrap source graph changed"))
        _ (do (println (str "staged " (count sources) " modules " (u/geti unity "sha256"))) (.flush sys/stdout))
        p (fn [n] (.joinpath output n))
        ;; three generations, stopping at the first whose outputs equal its predecessor's
        [producer rows] (loop [number 1 producer compiler rows []]
                          (if (> number 3)
                            (mac/fail "Mac full compiler did not reach a source fixed point")
                            (let [[signed row] (mac/generation number producer packager output)
                                  rows (conj rows row)]
                              (if (and (> number 1)
                                       (every? #(u/deq (u/geti row %) (u/geti (nth rows (- (count rows) 2)) %)) ["container" "raw" "unsigned"]))
                                [signed rows]
                                (recur (inc number) signed rows)))))
        _ (when (and (some? descriptor)
                     (not= (u/geti (u/geti (last rows) "container") "sha256")
                           (u/geti (u/geti descriptor "expectedFixedPoint") "compilerContainerSha256")))
            (mac/fail "Mac bootstrap compiler fixed-point digest changed"))
        packager-rebuild (rebuild-packager producer packager output (last rows))
        _ (when (and (some? descriptor)
                     (not= (u/geti (u/geti packager-rebuild "unsigned") "sha256")
                           (u/geti (u/geti descriptor "expectedFixedPoint") "packagerUnsignedSha256")))
            (mac/fail "Mac bootstrap packager fixed-point digest changed"))
        scalar (p "scalar.kotoba")
        _ (.write_text scalar elf/source)
        _ (mac/native-run producer output ["compile" "scalar.kotoba" "--target" elf/target "--output" "scalar.elf"])
        image (p "scalar.elf")
        _ (elf/verify (.read_bytes image))
        _ (mac/native-run producer output ["package-aiueos-user-payload" "scalar.elf" "--output" "scalar-slot.bin"])
        slot (p "scalar-slot.bin")
        packed (.read_bytes slot)
        n (.-st_size (.stat image))
        _ (u/chk (= (python/len packed) 524288))
        _ (u/chk (= (vec (struct/unpack_from "<QQQ" packed 0)) [0x0031444c50554941 1 n]))
        _ (u/chk (u/deq (u/bslice packed 64 (+ 64 n)) (.read_bytes image)))
        _ (u/chk (not (python/any (u/bslice packed (+ 64 n) (python/len packed)))))
        existing (mac/native-run producer output ["package-aiueos-user-payload" "scalar.elf" "--output" (.-name slot)] :expected 2)
        _ (when-not (u/has-bytes? (.encode "E7110") (.-stderr existing)) (mac/fail "user payload packager did not refuse existing output"))
        missing (mac/native-run producer output ["package-aiueos-user-payload" "missing.elf" "--output" "missing-slot.bin"] :expected 1)
        _ (when (or (not (u/has-bytes? (.encode "E3") (.-stderr missing))) (.exists (p "missing-slot.bin")))
            (mac/fail "user payload packager did not refuse missing input"))
        _ (.write_bytes (p "oversized.bin") (u/bytes-of-n 524225 0))
        oversized (mac/native-run producer output ["package-aiueos-user-payload" "oversized.bin" "--output" "oversized-slot.bin"] :expected 1)
        _ (when (or (not (u/has-bytes? (.encode "E7112") (.-stderr oversized))) (.exists (p "oversized-slot.bin")))
            (mac/fail "user payload packager did not refuse oversized input"))
        effect (p "effect.kotoba")
        _ (.write_text effect elf/effect)
        refused (mac/native-run producer output ["compile" "effect.kotoba" "--target" elf/target "--output" "effect.elf"] :expected 1)
        _ (when (or (not (u/has-bytes? (.encode "E7101") (.-stderr refused))) (.exists (p "effect.elf")))
            (mac/fail "undeclared effect was not refused without an artifact"))
        ;; The Mac wrapper must dispatch real bytes-concat/slice calls, not merely rebuild a compiler whose own source
        ;; happens not to exercise those slots.
        _ (shutil/copyfile fs2-product (p "fs2-product.kotoba"))
        _ (mac/native-run producer output ["compile" "fs2-product.kotoba" "--target" "aarch64-macos" "--output" "fs2-product.kseed"])
        extracted (mac/native-run producer output ["extract-native" "fs2-product.kseed" "--symbol" "main" "--output" "fs2-product.raw"])
        m (extract-match (.-stdout extracted))
        _ (when (or (nil? m) (not= (python/int (.group m 2)) (.-st_size (.stat (p "fs2-product.raw")))))
            (mac/fail "Mac FS2 product main extraction did not match raw bytes"))
        _ (mac/native-run (p "P1-signed.macho") output ["fs2-product-unsigned.macho" "fs2-product.raw" "fs2-cli-stdio-general" (.decode (.group m 1))])
        fs2-image-pin (mac/sign (p "fs2-product-unsigned.macho") (p "fs2-product-signed.macho"))
        _ (mac/native-run (p "fs2-product-signed.macho") output ["raw" "fs2-byte-roundtrip.bin"])
        fs2-written (p "fs2-byte-roundtrip.bin")
        _ (when-not (u/deq (.read_bytes fs2-written) (u/hex->bytes "00ff80")) (mac/fail "Mac FS2 B/C and A byte roundtrip changed"))
        parameter (p "parameter.kotoba")
        _ (.write_text parameter elf/parameter)
        refused-parameter (mac/native-run producer output ["compile" "parameter.kotoba" "--target" elf/target "--output" "parameter.elf"] :expected 1)
        _ (when (or (not (u/has-bytes? (.encode "E7102") (.-stderr refused-parameter))) (.exists (p "parameter.elf")))
            (mac/fail "v1 parameter was not refused without an artifact"))
        _ (when (or (not (u/deq (mac/pin compiler) compiler-pin)) (not (u/deq (mac/pin packager) packager-pin))
                    (not (u/deq (mac/pin mac/manifest) manifest-pin)) (not (u/deq (mac/pin user-check) checker-pin))
                    (not (u/deq (mac/pin fs2-product) fs2-product-pin))
                    (not (u/deq (mac/pin mac/packager-source) packager-source-pin))
                    (and (some? descriptor-pin) (not (u/deq (mac/pin mac/root-descriptor) descriptor-pin)))
                    (not (u/deq (mac/pin (p "full-unity.kotoba")) unity))
                    (some (fn [row] (not (u/deq (mac/pin (.joinpath u/root (u/geti row "name")))
                                                (u/pydict "bytes" (u/geti row "bytes") "sha256" (u/geti row "sha256")))))
                          sources))
            (mac/fail "input changed during Mac gate"))
        report (u/pydict "schema" "amu.mac-aiueos-user-target.v3" "status" "PASS_MAC_NATIVE_USER_TARGET_SELFHOST"
                         "compiler" compiler-pin "packager" packager-pin "manifest" manifest-pin "source" unity
                         "sources" (python/list sources) "generations" (python/list rows) "fixedPointGeneration" (count rows)
                         "packagerSelfRebuild" packager-rebuild "bootstrapDescriptor" descriptor-pin
                         "userSource" (mac/pin scalar) "userElf" (mac/pin image) "userPayloadSlot" (mac/pin slot)
                         "userPayloadExistingOutputRefused" true "userPayloadMissingInputRefused" true
                         "userPayloadOversizedInputRefused" true "effectSource" (mac/pin effect)
                         "undeclaredEffectRefused" true "parameterSource" (mac/pin parameter) "parameterRefused" true
                         "fs2ProductRaw" (u/pydict "status" "PASS_MAC_FS2_RAW_BYTES" "source" fs2-product-pin
                                                   "container" (mac/pin (p "fs2-product.kseed")) "raw" (mac/pin (p "fs2-product.raw"))
                                                   "image" fs2-image-pin "stored" (mac/pin fs2-written))
                         "guestExecution" false "ItonamiTurn" false "releaseAdmission" false "linuxProcessInThisGate" false
                         "userVerifier" checker-pin "observer" (mac/pin observer-path))]
    (.write_text (p "mac-aiueos-user-target.json") (u/json-dump report))
    (println (u/geti report "status") (u/geti (u/geti report "userElf") "sha256"))
    (.flush sys/stdout)))
