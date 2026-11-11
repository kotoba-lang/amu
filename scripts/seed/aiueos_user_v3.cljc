;; Check the bounded Amu user-v3 syscall ELF with a pinned Mac selfhost image: fixed sources, pins and the byte
;; verifier, plus compiler resolution from a Mac build receipt or an explicit pin (shared by check-aiueos-user-v3-macos-native
;; and the user-v5 layout gate). This checks compiler isolation and ELF bytes. Guest behavior has a separate AIUEOS
;; QEMU gate; this does not claim an Itonami turn. Ported from check-aiueos-user-v3-macos-native.py (Basilisp, JUN-974).
(ns aiueos-user-v3
  (:require [gate-util :as u]
            [macos-native-lib :as mac])
  (:import pathlib struct))

(def source-path (.joinpath u/root "seed/tests/aiueos-user-v3-local-model.kotoba"))
(def trampoline (u/hex->bytes "b8050000004883ec080f054883c408c3"))
(def elf-sha256 "108174e896008ac4b523450acd57d16b2b37ba3eb31f6b21d3ad3874344ca4ec")
(def llm-source
  (str "(ns aiueos-user-v3-llm (:export [main]))\n"
       "(defn main [request :i64 request-bytes :i64] :i64\n"
       "  (llm/generate request))\n"))
(def llm-declared-source
  (str "(ns aiueos-user-v3-llm\n"
       "  (:export [main])\n"
       "  (:capabilities #{:llm/generate}))\n"
       "(defn main [request :i64 request-bytes :i64] :i64\n"
       "  (llm/generate request))\n"))

(defn- q [fmt b off] (first (struct/unpack_from fmt b off)))

(defn verify
  "ValueError unless data is the user-v3 local-call image."
  [data]
  (when (or (not= (python/len data) 8280) (not (u/deq (u/bslice data 0 4) (u/hex->bytes "7f454c46"))))
    (mac/fail "wrong user-v3 ELF size or header"))
  (when (not= (q "<Q" data 24) 0x220000) (mac/fail "wrong user-v3 entry"))
  (when (not= (q "<Q" data (+ 64 32)) 478) (mac/fail "wrong user-v3 executable extent"))
  (when (not= (q "<Q" data (+ 120 40)) 320) (mac/fail "wrong user-v3 writable extent"))
  (when-not (u/deq (u/bslice data (+ 4096 48) (+ 4096 64)) trampoline)
    (mac/fail "syscall trampoline did not align the stack"))
  (when (or (not= (q "<Q" data (+ 8192 8)) 256) (not= (q "<Q" data (+ 8192 48)) 0x220030)
            (python/any (u/bslice data 8192 (+ 8192 8)))
            (python/any (u/bslice data (+ 8192 16) (+ 8192 48)))
            (python/any (u/bslice data (+ 8192 56) 8280)))
    (mac/fail "user-v3 ELF has unexpected initial context")))

(defn resolve-compiler
  "[compiler compiler-pin] from a Mac build receipt directory or an explicit image + SHA-256 pin."
  [{:keys [mac-build compiler-image compiler-sha256]}]
  (if mac-build
    (do
      (when (or compiler-image compiler-sha256) (mac/fail "choose the Mac build receipt or an explicit compiler pin"))
      (let [build (.resolve (pathlib/Path mac-build) ** :strict true)
            receipt (.joinpath build "mac-aiueos-user-target.json")
            _ (mac/require-regular receipt)
            root (u/read-json mac/root-descriptor)
            report (u/read-json receipt)
            generations (vec (.get report "generations" (python/list)))]
        (when (or (not= (.get report "status") "PASS_MAC_NATIVE_USER_TARGET_SELFHOST")
                  (not (u/deq (.get report "source") (u/geti root "fullSource")))
                  (< (count generations) 2)
                  (not (u/deq (u/geti (last generations) "container") (u/geti (nth generations (- (count generations) 2)) "container")))
                  (not= (u/geti (u/geti (last generations) "container") "sha256")
                        (u/geti (u/geti root "expectedFixedPoint") "compilerContainerSha256")))
          (mac/fail "Mac root receipt does not bind the current fixed point"))
        (let [compiler (.joinpath build (str "F" (u/geti (last generations) "number") "-signed.macho"))
              pin (mac/require-regular compiler (u/geti (u/geti (last generations) "signed") "sha256"))]
          (when-not (u/deq pin (u/geti (last generations) "signed")) (mac/fail "Mac root compiler size changed"))
          [compiler pin])))
    (do
      (when (or (not compiler-image) (not compiler-sha256)) (mac/fail "explicit compiler requires path and SHA-256 pin"))
      (let [compiler (.resolve (pathlib/Path compiler-image) ** :strict true)]
        [compiler (mac/require-regular compiler compiler-sha256)]))))
