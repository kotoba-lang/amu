;; Check the bounded Amu user-v3 syscall ELF with a pinned Mac selfhost image.
;;
;; This checks compiler isolation and ELF bytes. Guest behavior has a separate AIUEOS QEMU gate; this script does not
;; claim an Itonami turn. Ported from check-aiueos-user-v3-macos-native.py (Basilisp, JUN-974).
;; Run: basilisp run -p scripts/seed scripts/seed/check-aiueos-user-v3-macos-native.cljc -- --output DIR
;;      (--mac-build DIR | --compiler-image F --compiler-sha256 H)
(ns check-aiueos-user-v3-macos-native
  (:require [basilisp.string :as str]
            [aiueos-user-v3 :as v3]
            [gate-util :as u]
            [macos-native-lib :as mac])
  (:import json pathlib sys))

(def observer-path (.joinpath u/root "scripts/seed/check-aiueos-user-v3-macos-native.cljc"))

(defn main [args]
  (let [[compiler compiler-pin] (v3/resolve-compiler args)
        _ (mac/verify-macho compiler)
        source-pin (mac/require-regular v3/source-path)
        output (.resolve (pathlib/Path (:output args)))
        _ (.mkdir output ** :parents false :exist_ok false)
        source (.joinpath output "user.kotoba")
        _ (.write_bytes source (.read_bytes v3/source-path))
        results (vec (for [name ["user.elf" "user.reproduced.elf"]]
                       (do (mac/native-run compiler output ["compile" (.-name source) "--target" "x86_64-aiueos-user-v3" "--output" name])
                           (let [result (.joinpath output name)]
                             (v3/verify (.read_bytes result))
                             (let [identity (mac/pin result)]
                               (when (not= (u/geti identity "sha256") v3/elf-sha256)
                                 (mac/fail "user-v3 ELF changed from the pinned guest image"))
                               identity)))))
        _ (when-not (u/deq (first results) (second results)) (mac/fail "user-v3 native build was not reproducible"))
        refused (mac/native-run compiler output ["compile" (.-name source) "--target" "x86_64-aiueos-user-v2" "--output" "forbidden-v2.elf"] :expected 1)
        _ (when (or (.exists (.joinpath output "forbidden-v2.elf")) (not (u/nonempty? (.-stderr refused))))
            (mac/fail "v2 target accepted the v3-only operation"))
        ;; Preserve the measured gap as a fail-closed baseline. This is not a kit qualification: the target still lacks
        ;; a typed request/result ABI and a declared-capability manifest. JUN-444 must replace both refusals with a
        ;; positive whole-kit gate when that path is implemented.
        llm-refusals (u/pydict)]
    (doseq [[name text diagnostic] [["llm-undeclared" v3/llm-source "E2115"] ["llm-declared" v3/llm-declared-source "E2004"]]]
      (let [candidate (.joinpath output (str name ".kotoba"))
            artifact (.joinpath output (str name ".elf"))]
        (.write_text candidate text)
        (let [result (mac/native-run compiler output ["compile" (.-name candidate) "--target" "x86_64-aiueos-user-v3" "--output" (.-name artifact)] :expected 1)]
          (when (or (not (u/has-bytes? (.encode diagnostic) (.-stderr result))) (.exists artifact))
            (mac/fail (str name " did not refuse without an ELF")))
          (.__setitem__ llm-refusals name (u/pydict "source" (mac/pin candidate) "diagnostic" diagnostic "artifactAbsent" true)))))
    (when (or (not (u/deq (mac/pin source) source-pin)) (not (u/deq (mac/pin compiler) compiler-pin)))
      (mac/fail "qualification inputs changed"))
    (let [report (u/pydict "schema" "amu.mac-aiueos-user-v3-local-call.v1" "status" "PASS_MAC_NATIVE_USER_V3_LOCAL_CALL_ELF"
                           "compiler" compiler-pin "source" source-pin "elf" (first results) "reproducedElf" (second results)
                           "v2Refusal" true "llmKitRefusals" llm-refusals "observer" (mac/pin observer-path)
                           "guestExecution" false "externalOperation" false "agentLoop" false "linuxProcessInThisGate" false)]
      (.write_text (.joinpath output "mac-aiueos-user-v3-local-call.json") (u/json-dump report))
      (println (u/geti report "status") v3/elf-sha256)
      (.flush sys/stdout))))

(defn -main [& args]
  (main {:mac-build (u/opt args "--mac-build") :compiler-image (u/opt args "--compiler-image")
         :compiler-sha256 (u/opt args "--compiler-sha256")
         :output (or (u/opt args "--output") (sys/exit "--output is required"))}))

(when (some #(or (= % "check-aiueos-user-v3-macos-native.cljc") (str/ends-with? % "/check-aiueos-user-v3-macos-native.cljc")) sys/argv)
  (apply -main *command-line-args*))
