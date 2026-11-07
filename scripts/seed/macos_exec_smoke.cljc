;; Observe a Kotoba-emitted arm64 Mach-O in the macOS loader.
;;
;; The external codesign step signs diagnostic copies only. This does not build or qualify an Amu macOS
;; compiler, a self-rebuild, or a release artifact. Ported from check-macos-exec-smoke.py (Basilisp, JUN-974).
(ns macos-exec-smoke
  (:require [gate-util :as u])
  (:import os pathlib platform shutil struct subprocess))

(def expected-unsigned-sha256 "b4f151d148cdb76b9c22b94f1278c57a14ddde0a7c6174ab68facc5bd50b93a7")
(def expected-code
  [0xd10043ff 0xd2800000 0x910003e1 0xd2800202 0xd2800070 0xf2a04010 0xd4001001 0x54000202
   0xf100001f 0x5400018d 0xaa0003e2 0xd2800020 0x910003e1 0xd2800090 0xf2a04010 0xd4001001
   0x540000e2 0xeb02001f 0x540000a1 0xd2800540 0x14000004 0xd2800560 0x14000002 0xd2800580
   0xd2800030 0xf2a04010 0xd4001001 0xd65f03c0])

(defn run [argv & {:keys [input close-fd] :or {input nil close-fd nil}}]
  (let [args (python/list (map str argv))
        pipe subprocess/PIPE]
    (cond
      (and (nil? input) (nil? close-fd))
      (subprocess/run args ** :stdout pipe :stderr pipe :timeout 10 :check false :stdin subprocess/DEVNULL)
      (nil? close-fd)
      (subprocess/run args ** :stdout pipe :stderr pipe :timeout 10 :check false :input input)
      (nil? input)
      (subprocess/run args ** :stdout pipe :stderr pipe :timeout 10 :check false :stdin subprocess/DEVNULL
                      :preexec_fn (fn [] (os/close close-fd)))
      :else
      (subprocess/run args ** :stdout pipe :stderr pipe :timeout 10 :check false :input input
                      :preexec_fn (fn [] (os/close close-fd))))))

(defn- sha [path] (u/sha256-hex (.read_bytes (pathlib/Path path))))
(defn- fail [m] (throw (python/RuntimeError m)))
(defn- u32 [data off] (first (struct/unpack_from "<I" data off)))
(defn- u32x2 [data off] (vec (struct/unpack_from "<II" data off)))

(defn check [unsigned output]
  (when (or (not= "Darwin" (platform/system)) (not= "arm64" (platform/machine)))
    (fail "this loader smoke requires an Apple Silicon Mac"))
  (let [unsigned (pathlib/Path unsigned)
        output (pathlib/Path output)
        data (.read_bytes unsigned)]
    (when (or (not= 16384 (python/len data))
              (not (u/deq (u/bslice data 0 4) (u/hex->bytes "cffaedfe")))
              (not= (u32x2 data 4) [0x0100000c 0])
              (not= (u32 data 12) 2)
              (not= (u32x2 data 16) [8 400])
              (not= (u32 data 24) 0x00200085)
              (not= (vec (struct/unpack_from "<28I" data 1024)) expected-code))
      (throw (python/ValueError "unexpected unsigned Kotoba Mach-O smoke image")))
    (let [source-digest (sha unsigned)
          _ (when (not= source-digest expected-unsigned-sha256)
              (throw (python/ValueError "unsigned Kotoba Mach-O does not match the reviewed fixture")))
          _ (.mkdir output ** :exist_ok false)
          signed (.joinpath output "kotoba-macos-smoke-signed.macho")
          refused (.joinpath output "kotoba-macos-smoke-no-dyld-flags.macho")
          _ (shutil/copyfile unsigned signed)
          _ (.chmod signed 0755)
          sign (run ["/usr/bin/codesign" "--force" "--sign" "-" signed])
          verify (run ["/usr/bin/codesign" "--verify" "--strict" signed])
          _ (when (or (not (zero? (.-returncode sign))) (not (zero? (.-returncode verify))))
              (fail "diagnostic Mac code signing failed"))
          launched (run [signed] :input (.encode "abc\n"))
          eof (run [signed] :input (u/bytes-of))
          bounded (run [signed] :input (.encode "0123456789abcdefZ"))
          read-error (run [signed] :close-fd 0)
          write-error (run [signed] :input (.encode "abc\n") :close-fd 1)
          empty? (fn [b] (not (u/nonempty? b)))
          out? (fn [r code stdout] (and (= code (.-returncode r)) (u/deq (.-stdout r) (.encode stdout)) (empty? (.-stderr r))))
          _ (when-not (and (out? launched 42 "abc\n") (out? eof 43 "") (out? bounded 42 "0123456789abcdef"))
              (fail "Kotoba-emitted Mach-O failed bounded Darwin read/write/exit"))
          _ (when-not (every? #(and (= 44 (.-returncode %)) (empty? (.-stdout %)) (empty? (.-stderr %))) [read-error write-error])
              (fail "Darwin read/write errors were not refused without output"))
          broken (python/bytearray data)
          _ (struct/pack_into "<I" broken 24 0x00200000)
          _ (.write_bytes refused broken)
          _ (.chmod refused 0755)
          negative-sign (run ["/usr/bin/codesign" "--force" "--sign" "-" refused])
          negative-verify (run ["/usr/bin/codesign" "--verify" "--strict" refused])
          _ (when (or (not (zero? (.-returncode negative-sign))) (not (zero? (.-returncode negative-verify))))
              (fail "negative image did not pass independent signing"))
          negative (run [refused] :input (.encode "abc\n"))
          _ (when-not (and (= -9 (.-returncode negative)) (empty? (.-stdout negative)) (empty? (.-stderr negative)))
              (fail "missing dynamic-link flags did not give the observed pre-entry kill"))
          _ (when (not= (sha unsigned) source-digest) (fail "unsigned Kotoba image changed during observation"))
          receipt (u/pydict "schema" "amu.macos-exec-smoke.v3" "compilerQualification" false
                            "externalSignerDiagnostic" true "unsignedSha256" source-digest "signedSha256" (sha signed)
                            "host" (python/list [(platform/system) (platform/machine)])
                            "positiveExit" (.-returncode launched) "positiveStdout" (.decode (.-stdout launched) "ascii")
                            "eofExit" (.-returncode eof) "boundedExit" (.-returncode bounded)
                            "boundedStdout" (.decode (.-stdout bounded) "ascii")
                            "closedStdinExit" (.-returncode read-error) "closedStdoutExit" (.-returncode write-error)
                            "missingDyldFlagsExit" (.-returncode negative))]
      (.write_text (.joinpath output "receipt.json") (u/json-dump receipt))
      receipt)))
