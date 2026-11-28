;; Stage and observe the Amu-native Mac CLI build; no compiler/emitter here. Library half of build-macos-cli.cljc.
;; Ported from build-macos-cli.py (Basilisp, JUN-974). Apple Silicon macOS only.
(ns macos-cli-build
  (:require [basilisp.string :as str]
            [gate-util :as u]
            [macos-native-lib :as mac])
  (:import json operator pathlib platform re sys))

(def pin-keys ["bytes" "sha256"])
(def cli-sources ["seed/macos-cli-api.kotoba" "seed/runtime/llm-v1-wire.kotoba"
                  "seed/macos-cli-murakumo.kotoba" "seed/macos-cli-llm.kotoba" "seed/macos-cli.kotoba"])

(defn pin-of [d key] (u/pydict-from (for [k pin-keys] [k (u/geti (u/geti d key) k)])))

(defn cli-unity-bytes [root names pins]
  (let [[api codec murakumo broker cli] (mapv #(.joinpath root %) cli-sources)
        text (.read_text codec)
        mark (.index text "\n;; KLM1/KLR1")
        ns-head (.rstrip (subs text 0 mark))
        schema (subs ns-head (.index ns-head "\n  (:schemas") (dec (count ns-head)))
        seed-ns "(ns seed (:export [main]))"
        first-source (.read_text (.joinpath root (first names)))
        _ (u/chk (= (.count first-source seed-ns) 1) "public CLI lost its seed namespace")
        head (.replace first-source seed-ns (str "(ns seed (:export [main])" schema ")"))]
    (.join (u/bytes-of)
           (python/list (concat [(.encode (str head "\n"))]
             (for [name (rest names)] (operator/add (.read_bytes (.joinpath root name)) (.encode "\n")))
             [(operator/add (.read_bytes api) (.encode "\n"))
              (.encode (str pins "\n"))
              (.encode (str (subs text mark) "\n"))
              (operator/add (.read_bytes murakumo) (.encode "\n"))
              (operator/add (.read_bytes broker) (.encode "\n"))
              (operator/add (.read_bytes cli) (.encode "\n"))])))))

(defn source-report [root names]
  (u/pydict-from (for [name (into names cli-sources)] [name (mac/pin (.joinpath root name))])))

(defn native-image [compiler packager out stem mode data]
  (let [source (.joinpath out (str stem ".kotoba"))]
    (.write_bytes source data)
    (mac/native-run compiler out ["compile" (.-name source) "--target" "aarch64-macos" "--output" (str stem ".kseed")])
    (let [r (mac/native-run compiler out ["extract-native" (str stem ".kseed") "--symbol" "main" "--output" (str stem ".raw")])
          m (re/search (.encode ":offset (\\d+), :length (\\d+), :arity 0}") (.-stdout r))]
      (u/chk (and m (= (python/int (.group m 2)) (.-st_size (.stat (.joinpath out (str stem ".raw")))))))
      (mac/native-run packager out [(str stem "-unsigned.macho") (str stem ".raw") mode (.decode (.group m 1))]))
    (let [image (.joinpath out (str stem ".macho"))]
      (mac/sign (.joinpath out (str stem "-unsigned.macho")) image)
      (mac/verify-macho image)
      image)))

(defn cli-core-names []
  (let [names (u/manifest-paths mac/manifest)
        core (vec (take (inc (.index (python/list names) "seed/90-drv.kotoba")) names))]
    (u/chk (and (= 18 (count core)) (= 18 (count (set core))) (contains? (set core) "seed/19-decimal.kotoba")))
    core))

(defn cli-pins [compiler-digest packager-digest]
  (str "(def MC-COMPILER-SHA256 \"" compiler-digest "\")\n"
       "(def MC-PACKAGER-SHA256 \"" packager-digest "\")\n"))

(defn build [out]
  (u/chk (and (= "Darwin" (platform/system)) (= "arm64" (platform/machine))))
  (let [root u/root
        d (u/read-json mac/root-descriptor)
        compiler (.joinpath root (u/geti (u/geti d "compiler") "path"))
        bootstrap (.joinpath root (u/geti (u/geti d "packager") "path"))]
    (doseq [[key image] [["compiler" compiler] ["packager" bootstrap]]]
      (u/chk (u/deq (mac/verify-macho image) (pin-of d key))))
    (.mkdir out ** :parents true :mode 0700 :exist_ok false)
    (let [packager (native-image compiler bootstrap out "packager" "fs2-cli-stdio-general"
                      (operator/add (.read_bytes mac/packager-source) (.encode "\n")))
          _ (u/chk (u/deq (mac/pin mac/packager-source) (pin-of d "packagerSource")))
          _ (u/chk (= (u/geti (mac/pin (.joinpath out "packager-unsigned.macho")) "sha256")
                      (u/geti (u/geti d "expectedFixedPoint") "packagerUnsignedSha256")))
          pins (.joinpath out "macos-cli-pins.kotoba")
          _ (.write_text pins (cli-pins (u/geti (mac/pin compiler) "sha256") (u/geti (mac/pin bootstrap) "sha256")))
          names (cli-core-names)
          cli (native-image compiler bootstrap out "amu-cli" "amu-cli-host" (cli-unity-bytes root names (.read_text pins)))
          report (u/pydict "schema" "amu.macos-native-cli-build.v1" "status" "BUILT_NATIVE_MACOS_CLI"
                           "compiler" (mac/pin compiler) "packager" (mac/pin bootstrap) "rebuiltPackager" (mac/pin packager)
                           "cli" (mac/pin cli) "unity" (mac/pin (.joinpath out "amu-cli.kotoba"))
                           "sources" (source-report root names)
                           "nativeBuild" true "hostedFallback" false "publicEntrySelected" false)]
      (.write_text (.joinpath out "cli-build.json") (u/json-dump report))
      (println (u/geti report "status") (str cli))
      (.flush sys/stdout))))
