;; Stage and observe the Amu-native Mac CLI build; no compiler/emitter here. Library half of build-macos-cli.cljc.
;; Ported from build-macos-cli.py (Basilisp, JUN-974). Apple Silicon macOS only.
(ns macos-cli-build
  (:require [basilisp.string :as str]
            [gate-util :as u]
            [macos-native-lib :as mac])
  (:import json operator pathlib platform re sys))

(def pin-keys ["bytes" "sha256"])

(defn pin-of [d key] (u/pydict-from (for [k pin-keys] [k (u/geti (u/geti d key) k)])))

(defn cli-input-paths [root names pins]
  (let [manifest-paths (vec (map #(.joinpath root %) names))
        api (.joinpath root "seed/macos-cli-api.kotoba")
        cli (.joinpath root "seed/macos-cli.kotoba")]
    {:declared (vec (concat manifest-paths [api cli]))
     :assembly (vec (concat manifest-paths [api pins cli]))}))

(defn source-report [root inputs]
  (u/pydict-from (for [p (:declared inputs)] [(str (.relative_to p root)) (mac/pin p)])))

(defn build [out]
  (u/chk (and (= "Darwin" (platform/system)) (= "arm64" (platform/machine))))
  (let [root u/root
        d (u/read-json mac/root-descriptor)
        compiler (.joinpath root (u/geti (u/geti d "compiler") "path"))
        bootstrap (.joinpath root (u/geti (u/geti d "packager") "path"))]
    (doseq [[key image] [["compiler" compiler] ["packager" bootstrap]]]
      (u/chk (u/deq (mac/verify-macho image) (pin-of d key))))
    (.mkdir out ** :parents true :mode 0700 :exist_ok false)
    (let [native (fn [paths stem packager mode]
                   (let [source (.joinpath out (str stem ".kotoba"))]
                     (.write_bytes source (.join (u/bytes-of) (python/list (for [p paths] (operator/add (.read_bytes p) (.encode "\n"))))))
                     (mac/native-run compiler out ["compile" (.-name source) "--target" "aarch64-macos" "--output" (str stem ".kseed")])
                     (let [r (mac/native-run compiler out ["extract-native" (str stem ".kseed") "--symbol" "main" "--output" (str stem ".raw")])
                           m (re/search (.encode ":offset (\\d+), :length (\\d+), :arity 0}") (.-stdout r))]
                       (u/chk (and m (= (python/int (.group m 2)) (.-st_size (.stat (.joinpath out (str stem ".raw")))))))
                       (mac/native-run packager out [(str stem "-unsigned.macho") (str stem ".raw") mode (.decode (.group m 1))]))
                     (let [image (.joinpath out (str stem ".macho"))]
                       (mac/sign (.joinpath out (str stem "-unsigned.macho")) image)
                       (mac/verify-macho image)
                       image)))
          packager (native [mac/packager-source] "packager" bootstrap "fs2-cli-stdio-general")
          _ (u/chk (u/deq (mac/pin mac/packager-source) (pin-of d "packagerSource")))
          _ (u/chk (= (u/geti (mac/pin (.joinpath out "packager-unsigned.macho")) "sha256")
                      (u/geti (u/geti d "expectedFixedPoint") "packagerUnsignedSha256")))
          pins (.joinpath out "macos-cli-pins.kotoba")
          _ (.write_text pins (str "(def MC-COMPILER-SHA256 \"" (u/geti (mac/pin compiler) "sha256") "\")\n"
                                   "(def MC-PACKAGER-SHA256 \"" (u/geti (mac/pin bootstrap) "sha256") "\")\n"))
          names (loop [lines (seq (.splitlines (.read_text mac/manifest))) acc []]
                  (if-let [name (first lines)]
                    (if (and (seq name) (not (.startswith name "#")))
                      (if (= name "seed/90-drv.kotoba") (conj acc name) (recur (rest lines) (conj acc name)))
                      (recur (rest lines) acc))
                    acc))
          _ (u/chk (and (= 18 (count names)) (= 18 (count (set names))) (contains? (set names) "seed/19-decimal.kotoba")))
          inputs (cli-input-paths root names pins)
          cli (native (:assembly inputs) "amu-cli" bootstrap "amu-cli-host")
          report (u/pydict "schema" "amu.macos-native-cli-build.v1" "status" "BUILT_NATIVE_MACOS_CLI"
                           "compiler" (mac/pin compiler) "packager" (mac/pin bootstrap) "rebuiltPackager" (mac/pin packager)
                           "cli" (mac/pin cli) "unity" (mac/pin (.joinpath out "amu-cli.kotoba"))
                           "sources" (source-report root inputs)
                           "nativeBuild" true "hostedFallback" false "publicEntrySelected" false)]
      (.write_text (.joinpath out "cli-build.json") (u/json-dump report))
      (println (u/geti report "status") (str cli))
      (.flush sys/stdout))))
