;; Check the SHA-256 crypto-hardware compile option on the signed Mac Amu (JUN-578).
;;
;; An ordinary compile uses the ARMv8 SHA-256 instructions for the certified sha256 shape; `compile --no-crypto-hw`
;; selects the scalar paths. Both builds must give the exact digest, a changed expected byte must fail in both, the
;; flag must be refused by `check`, and the instruction counts must differ in the documented direction.
;; Ported from check-crypto-hw-option-macos-native.py (Basilisp, JUN-974). Apple Silicon macOS only.
;; Run: basilisp run -p scripts/seed scripts/seed/check-crypto-hw-option-macos-native.cljc -- --mac-build DIR --output DIR
(ns check-crypto-hw-option-macos-native
  (:require [basilisp.string :as str]
            [gate-util :as u]
            [macos-native-lib :as mac])
  (:import operator pathlib platform re struct sys))

(def port (.joinpath u/root "bench/embench/reproduce-20261015/ports/official-nettle-sha256.kotoba"))
(def first-byte "(if (= i 0) 36 (if (= i 1) 141")
(def masks [["sha256h" 0xFFE0FC00 0x5E004000] ["sha256h2" 0xFFE0FC00 0x5E005000]
            ["sha256su1" 0xFFE0FC00 0x5E006000] ["sha256su0" 0xFFFFFC00 0x5E282800]])

(defn instruction-counts [kseed]
  (let [native (u/geti (.split (.read_bytes kseed) (.encode "\n\n") 1) 1)
        n (quot (python/len native) 4)
        words (struct/unpack (str "<" n "I") (u/bslice native 0 (* n 4)))]
    (u/pydict-from (for [[name mask value] masks]
                     [name (count (filter #(= (bit-and % mask) value) words))]))))

(defn main [mac-build output]
  (when-not (mac/available?) (mac/fail "native Apple Silicon required"))
  (let [report (u/read-json (.joinpath mac-build "mac-aiueos-user-target.json"))
        final (last (u/geti report "generations"))
        compiler (.joinpath mac-build (str "F" (u/geti final "number") "-signed.macho"))
        _ (when-not (u/deq (mac/verify-macho compiler) (u/geti final "signed")) (mac/fail "Mac compiler changed"))
        descriptor (u/read-json mac/root-descriptor)
        packager (.joinpath u/root (u/geti (u/geti descriptor "packager") "path"))
        _ (.mkdir output ** :parents false :mode 0700 :exist_ok false)
        src (.read_text port)
        _ (when (or (not= 1 (.count src first-byte)) (not (.__contains__ src "(:export [bench observe")))
            (mac/fail "port shape changed"))
        src (.replace src "(:export [bench observe" "(:export [main bench observe" 1)
        good (str src "\n(defn main [] :i64 (+ (bench 5) (* 10 (bench 1))))\n")
        bad (.replace good first-byte (.replace first-byte "36" "37" 1) 1)
        expected {"good" 11 "bad" 0}
        counts (atom {})]
    (doseq [[label source] [["good" good] ["bad" bad]]]
      (.write_text (.joinpath output (str label ".kotoba")) source)
      (doseq [[mode flags] [["hw" []] ["scalar" ["--no-crypto-hw"]]]]
        (let [tag (str label "-" mode)]
          (mac/native-run compiler output (concat ["compile" (str label ".kotoba") "--target" "aarch64-macos"] flags
                                                  ["--output" (str tag ".kseed")]))
          (let [extracted (mac/native-run compiler output ["extract-native" (str tag ".kseed") "--symbol" "main" "--output" (str tag ".raw")])
                m (re/search (.encode ":offset (\\d+), :length (\\d+), :arity 0}") (.-stdout extracted))]
            (when (or (nil? m) (not= (python/int (.group m 2)) (.-st_size (.stat (.joinpath output (str tag ".raw"))))))
              (mac/fail (str "main extraction mismatch: " tag)))
            (mac/native-run packager output [(str tag "-unsigned") (str tag ".raw") "fs2-cli-stdio-general" (.decode (.group m 1))])
            (mac/sign (.joinpath output (str tag "-unsigned")) (.joinpath output tag))
            (mac/native-run (.joinpath output tag) output [] :expected (get expected label))
            (when (= label "good")
              (swap! counts assoc mode (instruction-counts (.joinpath output (str tag ".kseed")))))))))
    (let [hw (get @counts "hw") scalar (get @counts "scalar")]
      (when (or (some zero? (.values hw)) (some pos? (.values scalar)))
        (mac/fail (str "instruction counts not as documented: " @counts))))
    (mac/native-run compiler output ["check" "good.kotoba" "--no-crypto-hw"] :expected 2)
    (let [counts-py (u/pydict "hw" (get @counts "hw") "scalar" (get @counts "scalar"))
          receipt (u/pydict "schema" "amu.mac-crypto-hw-option.v1" "status" "PASS_MAC_CRYPTO_HW_OPTION"
                            "compiler" (u/geti final "signed") "sha256InstructionCounts" counts-py
                            "digestExactBothModes" true "negativeControlFailsBothModes" true
                            "checkWithFlagRefused" true "nativeLinuxQualified" false
                            "observer" (mac/pin (.joinpath u/root "scripts/seed/check-crypto-hw-option-macos-native.cljc")))]
      (.write_text (.joinpath output "mac-crypto-hw-option.json") (u/json-dump receipt))
      (println (u/geti receipt "status") (.dumps (python/__import__ "json") counts-py))
      (.flush sys/stdout))))

(defn -main [& args]
  (main (.resolve (pathlib/Path (or (u/opt args "--mac-build") (sys/exit "--mac-build is required"))))
        (.resolve (pathlib/Path (or (u/opt args "--output") (sys/exit "--output is required"))))))

(when (some #(or (= % "check-crypto-hw-option-macos-native.cljc") (str/ends-with? % "/check-crypto-hw-option-macos-native.cljc")) sys/argv)
  (apply -main *command-line-args*))
