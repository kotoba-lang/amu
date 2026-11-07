;; Build and execute the bounded Darwin probe using only the Mac native root.
;;
;; This script stages bytes and observes native Amu, the native Kotoba packager and platform signing/inspection
;; tools. No Linux, assembler or hosted compiler. This diagnostic does not qualify the complete Darwin runtime or a
;; release. Ported from check-macos-exec-smoke-native.py (Basilisp, JUN-974). Apple Silicon macOS only.
;; Run: basilisp run -p scripts/seed scripts/seed/check-macos-exec-smoke-native.cljc -- --mac-build DIR --output DIR
(ns check-macos-exec-smoke-native
  (:require [basilisp.string :as str]
            [gate-util :as u]
            [macos-exec-smoke :as smoke]
            [macos-native-lib :as mac])
  (:import json pathlib re shutil sys))

(defn main [mac-build out]
  (let [root u/root
        report-path (.joinpath mac-build "mac-aiueos-user-target.json")
        descriptor-path mac/root-descriptor
        report-pin (mac/pin report-path)
        descriptor-pin (mac/pin descriptor-path)
        report (u/read-json report-path)
        descriptor (u/read-json descriptor-path)
        _ (u/chk (= "PASS_MAC_NATIVE_USER_TARGET_SELFHOST" (u/geti report "status")))
        _ (u/chk (u/deq (u/geti report "bootstrapDescriptor") descriptor-pin))
        _ (u/chk (u/deq (u/geti report "source") (u/geti descriptor "fullSource")))
        row (last (u/geti report "generations"))
        producer (.joinpath mac-build (str "F" (u/geti row "number") "-signed.macho"))
        packager (.joinpath root (u/geti (u/geti descriptor "packager") "path"))
        packager-pin (fn [] (u/pydict-from (for [k ["bytes" "sha256"]] [k (u/geti (u/geti descriptor "packager") k)])))
        _ (u/chk (u/deq (mac/verify-macho producer) (u/geti row "signed")))
        _ (u/chk (u/deq (mac/verify-macho packager) (packager-pin)))
        _ (.mkdir out ** :parents false :mode 0700 :exist_ok false)
        source (.joinpath root "seed/macos-exec-smoke.kotoba")
        source-pin (mac/pin source)
        _ (shutil/copyfile source (.joinpath out "probe.kotoba"))
        _ (mac/native-run producer out ["compile" "probe.kotoba" "--target" "aarch64-macos" "--output" "probe.kseed"])
        extracted (mac/native-run producer out ["extract-native" "probe.kseed" "--symbol" "main" "--output" "probe.raw"])
        m (re/search (.encode ":offset (\\d+), :length (\\d+), :arity 0}") (.-stdout extracted))
        _ (u/chk (and m (= (python/int (.group m 2)) (.-st_size (.stat (.joinpath out "probe.raw"))))))
        _ (mac/native-run packager out ["probe-unsigned.macho" "probe.raw" "fs2-cli-stdio-general" (.decode (.group m 1))])
        emitter (.joinpath out "probe-signed.macho")
        _ (mac/sign (.joinpath out "probe-unsigned.macho") emitter)
        _ (mac/native-run emitter out ["smoke-unsigned.macho"])
        _ (mac/native-run emitter out ["smoke-repeat.macho"])
        _ (u/chk (u/deq (.read_bytes (.joinpath out "smoke-unsigned.macho")) (.read_bytes (.joinpath out "smoke-repeat.macho"))))
        _ (mac/native-run emitter out [""] :expected 2)
        _ (u/chk (u/deq (mac/pin source) source-pin))
        observed (smoke/check (.joinpath out "smoke-unsigned.macho") (.joinpath out "execution"))
        _ (u/chk (u/deq (mac/verify-macho producer) (u/geti row "signed")))
        _ (u/chk (u/deq (mac/pin packager) (packager-pin)))
        _ (u/chk (u/deq (mac/pin source) source-pin))
        _ (u/chk (and (u/deq (mac/pin report-path) report-pin) (u/deq (mac/pin descriptor-path) descriptor-pin)))
        result (u/pydict "schema" "amu.mac-native-exec-smoke.v1" "status" "PASS_MAC_NATIVE_EXEC_SMOKE"
                         "bootstrapReport" report-pin "bootstrapDescriptor" descriptor-pin
                         "observer" (mac/pin (.joinpath root "scripts/seed/check-macos-exec-smoke-native.cljc"))
                         "compiler" (mac/pin producer) "packager" (mac/pin packager)
                         "source" source-pin "emitter" (mac/pin emitter)
                         "image" (mac/pin (.joinpath out "smoke-unsigned.macho")) "observation" observed
                         "repeatByteIdentical" true "emptyOutputPathRefused" true
                         "linuxProcessInThisGate" false "fullRuntimeQualified" false)]
    (.write_text (.joinpath out "native-smoke.json") (u/json-dump result))
    (println (u/geti result "status") (u/geti (u/geti result "image") "sha256"))
    (.flush sys/stdout)))

(defn -main [& args]
  (main (.resolve (pathlib/Path (or (u/opt args "--mac-build") (sys/exit "--mac-build is required"))))
        (.resolve (pathlib/Path (or (u/opt args "--output") (sys/exit "--output is required"))))))

(when (some #(or (= % "check-macos-exec-smoke-native.cljc") (str/ends-with? % "/check-macos-exec-smoke-native.cljc")) sys/argv)
  (apply -main *command-line-args*))
