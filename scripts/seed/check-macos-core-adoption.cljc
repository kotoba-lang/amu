;; Rebuild the selected 19-module core from the signed Mac Amu fixed point.
;; Ported from check-macos-core-adoption.py (Basilisp, JUN-974). Apple Silicon macOS only.
;; Run: basilisp run -p scripts/seed scripts/seed/check-macos-core-adoption.cljc -- --mac-build DIR --output DIR
(ns check-macos-core-adoption
  (:require [basilisp.string :as str]
            [gate-util :as u]
            [macos-native-lib :as mac])
  (:import json operator pathlib re sys))

(defn- pin-of [d key] (u/pydict-from (for [k ["bytes" "sha256"]] [k (u/geti (u/geti d key) k)])))

(defn main [mac-build output]
  (when-not (mac/available?) (mac/fail "native Apple Silicon required"))
  (let [root u/root
        descriptor-path mac/root-descriptor
        descriptor (u/read-json descriptor-path)
        report-path (.joinpath mac-build "mac-aiueos-user-target.json")
        report (u/read-json report-path)
        _ (when (or (not= "PASS_MAC_NATIVE_USER_TARGET_SELFHOST" (.get report "status"))
                    (not (u/deq (.get report "bootstrapDescriptor") (mac/pin descriptor-path)))
                    (not (u/deq (.get report "source") (u/geti descriptor "fullSource"))))
            (mac/fail "Mac source fixed point is not bound to this descriptor"))
        final (last (u/geti report "generations"))
        producer (.joinpath mac-build (str "F" (u/geti final "number") "-signed.macho"))
        _ (when-not (u/deq (mac/verify-macho producer) (u/geti final "signed")) (mac/fail "Mac compiler changed"))
        packager (.joinpath root (u/geti (u/geti descriptor "packager") "path"))
        _ (when-not (u/deq (mac/verify-macho packager) (pin-of descriptor "packager")) (mac/fail "Mac packager changed"))
        core (u/read-json (.joinpath root "seed/compiler-core.json"))
        adoption-path (.joinpath root (u/geti core "adoptionReceipt"))
        adoption (u/read-json adoption-path)
        _ (when (not= "seed/MANIFEST" (u/geti adoption "sourceManifest")) (mac/fail "wrong core manifest"))
        names (vec (filter #(and (seq %) (not (.startswith % "#")))
                           (.splitlines (.read_text (.joinpath root (u/geti adoption "sourceManifest"))))))
        _ (when (or (not= 19 (count names)) (not= (count names) (count (set names))) (not (contains? (set names) "seed/19-decimal.kotoba")))
            (mac/fail "core manifest must contain 19 unique modules including decimal"))
        _ (.mkdir output ** :parents false :mode 0700 :exist_ok false)
        unity-path (.joinpath output "adopted-unity.kotoba")
        stream (.open unity-path "wb")
        sources (try
                  (python/list
                   (for [name names]
                     (let [path (pathlib/Path name)]
                       (when (or (.is_absolute path) (.__contains__ (.-parts path) "..") (not= "seed" (first (.-parts path))))
                         (mac/fail "invalid core source path"))
                       (let [source (.joinpath root path)
                             row (u/pydict-from (concat [["path" name]] (.items (mac/require-regular source))))]
                         (.write stream (operator/add (.read_bytes source) (.encode "\n")))
                         row))))
                  (finally (.close stream)))
        unity (mac/pin unity-path)
        _ (when (or (not (u/deq sources (u/geti adoption "sources"))) (not (u/deq sources (u/geti core "sources")))
                    (not (u/deq unity (u/pydict "bytes" (u/geti adoption "sourceUnityBytes") "sha256" (u/geti adoption "sourceUnitySHA256"))))
                    (not (u/deq unity (u/pydict "bytes" (u/geti core "sourceUnityBytes") "sha256" (u/geti core "sourceUnitySHA256")))))
            (mac/fail "selected core source drift"))
        generations (atom [])
        current (atom producer)]
    (doseq [number [1 2 3]]
      (let [container (.joinpath output (str "G" number ".kseed"))
            raw (.joinpath output (str "G" number ".bin"))
            unsigned (.joinpath output (str "G" number "-unsigned.macho"))
            signed (.joinpath output (str "G" number "-signed.macho"))
            _ (mac/native-run @current output ["compile" "adopted-unity.kotoba" "--target" "aarch64-macos" "--output" (.-name container)])
            extracted (mac/native-run @current output ["extract-native" (.-name container) "--symbol" "main" "--output" (.-name raw)])
            m (re/search (.encode ":offset (\\d+), :length (\\d+), :arity 0}") (.-stdout extracted))]
        (when (or (nil? m) (not= (python/int (.group m 2)) (.-st_size (.stat raw))))
          (mac/fail "core main extraction mismatch"))
        (mac/native-run packager output [(.-name unsigned) (.-name raw) "fs2-cli-stdio-general" (.decode (.group m 1))])
        (mac/sign unsigned signed)
        (let [row (u/pydict "name" (str "G" number) "native" (mac/pin raw) "container" (mac/pin container))]
          (when-not (u/deq row (nth (u/geti adoption "generations") (dec number)))
            (mac/fail "core generation differs from selected adoption"))
          (swap! generations conj row)
          (reset! current signed))))
    (let [gens @generations
          g0 (first gens)]
      (when-not (every? #(and (u/deq (u/geti % "native") (u/geti g0 "native")) (u/deq (u/geti % "container") (u/geti g0 "container"))) gens)
        (mac/fail "core source fixed point absent"))
      (when (or (not (u/deq (u/geti g0 "native") (u/pydict "bytes" (u/geti adoption "nativeImageBytes") "sha256" (u/geti adoption "nativeImageSHA256"))))
                (not (u/deq (u/geti g0 "container") (u/geti adoption "container")))
                (not (u/deq (mac/verify-macho producer) (u/geti final "signed")))
                (not (u/deq (mac/pin descriptor-path) (u/geti report "bootstrapDescriptor"))))
        (mac/fail "core output or producer changed"))
      (let [receipt (u/pydict "schema" "amu.mac-core-adoption.v1" "status" "PASS_MAC_CORE_ADOPTION_FIXED_POINT"
                              "bootstrapReport" (mac/pin report-path) "adoption" (mac/pin adoption-path)
                              "sourceUnity" unity "generations" (python/list gens)
                              "nativeLinuxQualified" false "coldC0Qualified" false
                              "observer" (mac/pin (.joinpath root "scripts/seed/check-macos-core-adoption.cljc")))]
        (.write_text (.joinpath output "mac-core-adoption.json") (u/json-dump receipt))
        (println (u/geti receipt "status") (u/geti unity "sha256") (u/geti (u/geti g0 "native") "sha256"))
        (.flush sys/stdout)))))

(defn -main [& args]
  (main (.resolve (pathlib/Path (or (u/opt args "--mac-build") (sys/exit "--mac-build is required"))))
        (.resolve (pathlib/Path (or (u/opt args "--output") (sys/exit "--output is required"))))))

(when (some #(or (= % "check-macos-core-adoption.cljc") (str/ends-with? % "/check-macos-core-adoption.cljc")) sys/argv)
  (apply -main *command-line-args*))
