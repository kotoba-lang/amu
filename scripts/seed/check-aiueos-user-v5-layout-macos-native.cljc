;; Check the proposed user-v5 ELF and slot-v4 layout with signed Mac Amu.
;;
;; This checks artifact shape, the bounded diagnostic syscall lowering and old target isolation. It does not execute
;; the guest or qualify a typed kit call. Ported from check-aiueos-user-v5-layout-macos-native.py (Basilisp, JUN-974).
;; Run: basilisp run -p scripts/seed scripts/seed/check-aiueos-user-v5-layout-macos-native.cljc -- --output DIR
;;      (--mac-build DIR | --compiler-image F --compiler-sha256 H)
(ns check-aiueos-user-v5-layout-macos-native
  (:require [basilisp.string :as str]
            [aiueos-user-v2 :as v2]
            [aiueos-user-v3 :as v3]
            [gate-util :as u]
            [macos-native-lib :as mac])
  (:import operator pathlib struct sys))

(def observer-path (.joinpath u/root "scripts/seed/check-aiueos-user-v5-layout-macos-native.cljc"))
(def v5-source
  (str "(ns aiueos-user-v5-layout (:export [main]))\n"
       "(defn main [request :i64 request-bytes :i64] :i64 "
       "(kernel-load-u32 request request-bytes 0))\n"))
(def declared-llm
  (str "(ns aiueos-user-v5-llm (:export [main]) "
       "(:capabilities #{:llm/generate}))\n"
       "(defn main [request :i64 request-bytes :i64] :i64 "
       "(llm/generate request))\n"))
(def call-elf-sha256 "e19f3be978e23b66c7551905f1d829258622e8358e1b28528bc48adb6869e852")
(defn- q [fmt b off] (first (struct/unpack_from fmt b off)))
(defn- qs [fmt b off] (vec (struct/unpack_from fmt b off)))
(defn- stderr-has? [result code] (u/has-bytes? (.encode code) (.-stderr result)))

(defn reject [compiler output source name diagnostic & options]
  (let [result (mac/native-run compiler output (concat ["package-aiueos-user-payload" source "--output" name] options) :expected 1)]
    (when (or (not (stderr-has? result diagnostic)) (.exists (.joinpath output name)))
      (mac/fail (str "slot admission failed open: " name)))))

(defn resolve-compiler [{:keys [mac-build compiler-image compiler-sha256]}]
  (if mac-build
    (do
      (when compiler-sha256 (mac/fail "choose Mac build or explicit compiler pin"))
      (let [build (.resolve (pathlib/Path mac-build) ** :strict true)
            _ (when (or (.is_symlink build) (not (.is_dir build))) (mac/fail "regular Mac build directory required"))
            descriptor (u/read-json mac/root-descriptor)
            report (u/read-json (.joinpath build "mac-aiueos-user-target.json"))
            generations (vec (.get report "generations" (python/list)))
            prev (when (>= (count generations) 2) (nth generations (- (count generations) 2)))]
        (when (or (not= (.get report "status") "PASS_MAC_NATIVE_USER_TARGET_SELFHOST")
                  (not (u/deq (.get report "source") (u/geti descriptor "fullSource")))
                  (not (u/deq (.get report "bootstrapDescriptor") (mac/pin mac/root-descriptor)))
                  (< (count generations) 2)
                  (some (fn [k] (not (u/deq (u/geti (last generations) k) (u/geti prev k)))) ["container" "raw" "unsigned"])
                  (not= (u/geti (u/geti (last generations) "container") "sha256")
                        (u/geti (u/geti descriptor "expectedFixedPoint") "compilerContainerSha256")))
          (mac/fail "Mac build is not the current source fixed point"))
        (let [compiler (.joinpath build (str "F" (u/geti (last generations) "number") "-signed.macho"))
              original (mac/require-regular compiler (u/geti (u/geti (last generations) "signed") "sha256"))]
          (when-not (u/deq original (u/geti (last generations) "signed")) (mac/fail "Mac compiler image size changed"))
          [compiler original])))
    (do
      (when-not compiler-sha256 (mac/fail "explicit compiler requires a SHA-256 pin"))
      (let [compiler (.resolve (pathlib/Path compiler-image) ** :strict true)]
        [compiler (mac/require-regular compiler compiler-sha256)]))))

(defn main [args]
  (let [[compiler original] (resolve-compiler args)
        _ (mac/verify-macho compiler)
        output (.resolve (pathlib/Path (:output args)))
        _ (.mkdir output ** :parents false :exist_ok false)
        p (fn [n] (.joinpath output n))
        _ (.write_text (p "user-v5.kotoba") v5-source)
        _ (mac/native-run compiler output ["compile" "user-v5.kotoba" "--target" "x86_64-aiueos-user-v5" "--output" "user-v5.elf"])
        elf (.read_bytes (p "user-v5.elf"))
        _ (when (or (not= (python/len elf) 8280) (not= (q "<Q" elf 24) 0x420000) (not (u/deq (u/bslice elf 0 4) (u/hex->bytes "7f454c46"))))
            (mac/fail "user-v5 ELF identity changed"))
        [rx rw] (for [i (range 2)] (qs "<IIQQQQQQ" elf (+ 64 (* 56 i))))
        _ (when (or (not= (subvec rx 0 5) [1 5 4096 0x420000 0x420000])
                    (not (and (< 80 (nth rx 5)) (= (nth rx 5) (nth rx 6)) (<= (nth rx 6) 4096)))
                    (not= (nth rx 7) 4096)
                    (not= rw [1 6 8192 0x421000 0x421000 88 262144 4096])
                    (not= (q "<Q" elf (+ 8192 48)) 0x420030)
                    (python/any (u/bslice elf 176 4096)) (python/any (u/bslice elf (+ 4096 (nth rx 5)) 8192)))
            (mac/fail "user-v5 ELF layout changed"))
        _ (mac/native-run compiler output ["package-aiueos-user-payload" "user-v5.elf" "--output" "user-v5.slot" "--version" "v4"])
        slot (.read_bytes (p "user-v5.slot"))
        n (python/len elf)
        _ (when (or (not= (python/len slot) 524288) (not= (qs "<QQQ" slot 0) [0x0031444c50554941 4 n])
                    (not (u/deq (u/bslice slot 64 (+ 64 n)) elf)) (python/any (u/bslice slot (+ 64 n) (python/len slot))))
            (mac/fail "slot-v4 content or zero padding changed"))
        call-source v3/source-path
        _ (.write_bytes (p "user-v5-call.kotoba") (.read_bytes call-source))
        _ (mac/native-run compiler output ["compile" "user-v5-call.kotoba" "--target" "x86_64-aiueos-user-v5" "--output" "user-v5-call.elf"])
        call-elf (.read_bytes (p "user-v5-call.elf"))
        _ (when (or (not= (u/sha256-hex call-elf) call-elf-sha256) (not= (q "<Q" call-elf 96) 478)
                    (not= (.count call-elf (u/hex->bytes "48b80011420000000000")) 1)
                    (not= (.count call-elf (u/hex->bytes "b830004200ffd0")) 1))
            (mac/fail "user-v5 diagnostic syscall lowering changed"))
        _ (mac/native-run compiler output ["package-aiueos-user-payload" "user-v5-call.elf" "--output" "user-v5-call.slot" "--version" "v4"])
        negative (atom [])]
    (doseq [[name offset value] [["entry" 24 0x220000] ["rw-address" 136 0x321000] ["rw-extent" 160 320]]]
      (let [candidate (python/bytearray elf)]
        (struct/pack_into "<Q" candidate offset value)
        (.write_bytes (p (str name ".elf")) candidate)
        (reject compiler output (str name ".elf") (str name ".slot") "E7111" "--version" "v4")
        (swap! negative conj name)))
    (doseq [version ["v2" "v3"]]
      (reject compiler output "user-v5.elf" (str "wrong-" version ".slot") "E7111" "--version" version)
      (swap! negative conj (str "v5-as-" version)))
    (.write_text (p "declared-llm.kotoba") declared-llm)
    (let [refused (mac/native-run compiler output ["compile" "declared-llm.kotoba" "--target" "x86_64-aiueos-user-v5"
                                                   "--output" "declared-llm.elf"] :expected 1)]
      (when (or (not (stderr-has? refused "E2004")) (.exists (p "declared-llm.elf")))
        (mac/fail "v5 accepted an unimplemented typed LLM kit"))
      (swap! negative conj "typed-llm-kit"))
    (let [v3-text (.read_text call-source)
          legacy (atom [])]
      (doseq [[name target src version] [["v2" "x86_64-aiueos-user-v2" v2/source "v2"]
                                         ["v3" "x86_64-aiueos-user-v3" v3-text "v2"]
                                         ["v4" "x86_64-aiueos-user-v4" v3-text "v3"]]]
        (.write_text (p (str name ".kotoba")) src)
        (mac/native-run compiler output ["compile" (str name ".kotoba") "--target" target "--output" (str name ".elf")])
        (let [artifact (.read_bytes (p (str name ".elf")))]
          (case name
            "v2" (v2/verify artifact)
            "v3" (do (v3/verify artifact)
                     (when (not= (u/sha256-hex artifact) v3/elf-sha256) (mac/fail "pinned v3 ELF changed")))
            (when (or (not= (q "<Q" artifact 24) 0x320000) (not= (q "<Q" artifact 136) 0x321000) (not= (q "<Q" artifact 160) 320))
              (mac/fail "legacy v4 ELF layout changed"))))
        (mac/native-run compiler output ["package-aiueos-user-payload" (str name ".elf") "--output" (str name ".slot") "--version" version])
        (swap! legacy conj (u/pydict "target" target "elf" (mac/pin (p (str name ".elf"))) "slot" (mac/pin (p (str name ".slot"))))))
      (when-not (u/deq (mac/pin compiler) original) (mac/fail "compiler changed during observation"))
      (let [report (u/pydict "schema" "amu.mac-aiueos-user-v5-layout-candidate.v1" "status" "PASS_MAC_NATIVE_V5_LAYOUT_CANDIDATE"
                             "compiler" original "source" (mac/pin (p "user-v5.kotoba")) "elf" (mac/pin (p "user-v5.elf"))
                             "slot" (mac/pin (p "user-v5.slot")) "diagnosticCallElf" (mac/pin (p "user-v5-call.elf"))
                             "diagnosticCallSlot" (mac/pin (p "user-v5-call.slot"))
                             "legacy" (python/list @legacy) "negativeControls" (python/list @negative)
                             "observer" (mac/pin observer-path) "guestAdmission" false "typedKitCall" false
                             "agentLoop" false "releaseQualified" false "linuxProcessInThisGate" false)]
        (.write_text (p "mac-aiueos-user-v5-layout.json") (u/json-dump report))
        (println (u/geti report "status") (u/geti (u/geti report "elf") "sha256"))
        (.flush sys/stdout)))))

(defn -main [& args]
  (main {:mac-build (u/opt args "--mac-build") :compiler-image (u/opt args "--compiler-image")
         :compiler-sha256 (u/opt args "--compiler-sha256")
         :output (or (u/opt args "--output") (sys/exit "--output is required"))}))

(when (some #(or (= % "check-aiueos-user-v5-layout-macos-native.cljc") (str/ends-with? % "/check-aiueos-user-v5-layout-macos-native.cljc")) sys/argv)
  (apply -main *command-line-args*))
