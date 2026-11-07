;; Rebuild and observe the actual public native Mac CLI and its aliases.
;;
;; This script stages/hashes bytes and observes processes. Amu performs checking, compilation, ABI checking,
;; emission, packaging, host operations and execution. Ported from check-public-macos-product.py (Basilisp,
;; JUN-974). Apple Silicon macOS only.
;; Run: basilisp run -p scripts/seed scripts/seed/check-public-macos-product.cljc -- --output DIR
(ns check-public-macos-product
  (:require [basilisp.string :as str]
            [gate-util :as u]
            [macos-cli-build :as builder]
            [macos-cli-product :as product]
            [macos-native-lib :as mac])
  (:import json operator pathlib platform shutil subprocess sys))

(defn- pin-of [d key] (u/pydict-from (for [k ["bytes" "sha256"]] [k (u/geti (u/geti d key) k)])))

(defn main [out]
  (u/chk (and (= "Darwin" (platform/system)) (= "arm64" (platform/machine))))
  (let [root u/root
        d (u/read-json (.joinpath root "seed/bootstrap/aarch64-macos/cli.json"))
        root-d (u/read-json mac/root-descriptor)
        _ (u/chk (= "amu.macos-native-cli.v1" (u/geti d "schema")))
        _ (u/chk (.__contains__ (.read_text (.joinpath root "examples/foundation-starter/MACOS-ARM64.md"))
                                (u/geti (u/geti d "image") "sha256"))
                 "first-run guide has a stale CLI digest")
        _ (u/chk (and (u/deq (u/geti d "compiler") (u/geti root-d "compiler")) (u/deq (u/geti d "packager") (u/geti root-d "packager"))))
        _ (doseq [role ["compiler" "packager" "image"]]
            (u/chk (u/deq (mac/verify-macho (.joinpath root (u/geti (u/geti d role) "path"))) (pin-of d role))))
        aliases (vec (for [name (cons (u/geti d "entry") (u/geti d "aliases"))] (.joinpath root name)))
        image (.joinpath root (u/geti (u/geti d "image") "path"))
        _ (doseq [alias aliases]
            (u/chk (and (.is_symlink alias) (u/deq (.resolve alias ** :strict true) (.resolve image ** :strict true)))))
        _ (doseq [[name identity] (.items (u/geti d "sources"))]
            (u/chk (u/deq (mac/pin (.joinpath root name)) identity) name))
        names (vec (filter #(and (seq %) (not (.startswith % "#"))) (.splitlines (.read_text mac/manifest))))
        unity (.join (u/bytes-of) (python/list (for [n names] (operator/add (.read_bytes (.joinpath root n)) (.encode "\n")))))
        _ (u/chk (u/deq (u/pydict "bytes" (python/len unity) "sha256" (u/sha256-hex unity)) (u/geti root-d "fullSource")))
        _ (.mkdir out ** :parents true :mode 0700 :exist_ok false)
        ;; The complete fresh native derivation must reproduce the source-bound unsigned image. Ad-hoc signature
        ;; encodings may differ between OS hosts.
        _ (builder/build (.joinpath out "rebuild"))
        rebuilt (u/read-json (.joinpath out "rebuild/cli-build.json"))
        _ (u/chk (and (u/deq (u/geti rebuilt "unity") (u/geti d "unity")) (u/deq (u/geti rebuilt "sources") (u/geti d "sources"))))
        unsigned (.joinpath out "rebuild/amu-cli-unsigned.macho")
        _ (u/chk (u/deq (mac/pin unsigned) (u/geti d "unsigned")))
        stripped (.joinpath out "stripped.macho")
        _ (shutil/copy2 image stripped)
        _ (subprocess/run (python/list ["/usr/bin/codesign" "--remove-signature" (str stripped)]) ** :check true :capture_output true)
        observed (python/bytearray (.read_bytes stripped))
        expected (.read_bytes unsigned)]
    ;; codesign leaves the rounded __LINKEDIT virtual size after removal. Compare every executable/data/header byte
    ;; other than that metadata word.
    (u/chk (= (python/len observed) (python/len expected)))
    (operator/setitem observed (python/slice 280 288) (u/bslice expected 280 288))
    (u/chk (u/deq observed expected) "public image does not contain the rebuilt native payload")
    (product/check (first aliases) (.joinpath out "commands"))
    (doseq [alias (rest aliases)]
      (let [p (subprocess/run (python/list [(str alias) "check" (str (.joinpath out "commands/hello.kotoba"))]) ** :cwd out
                              :env (python/dict {"PATH" "/nonexistent"}) :capture_output true :timeout 150)]
        (u/chk (and (zero? (.-returncode p)) (u/deq (.-stdout p) (.encode "ok\n")) (not (u/nonempty? (.-stderr p)))))))
    (u/chk (u/deq (mac/pin image) (pin-of d "image")))
    (let [result (u/pydict "schema" "amu.public-macos-product.v2" "status" "PASS_PUBLIC_MACOS_PRODUCT"
                           "descriptor" (mac/pin (.joinpath root "seed/bootstrap/aarch64-macos/cli.json")) "image" (mac/pin image)
                           "unsigned" (mac/pin unsigned) "aliases" (python/list (for [p aliases] (str (.relative_to p root))))
                           "normalCommands" (u/read-json (.joinpath out "commands/cli-product.json"))
                           "nativeRebuildMatchesPublicPayload" true "manualFD3" false "hostedFallback" false
                           "fullRuntimeQualified" false "independentUserQualified" false)]
      (.write_text (.joinpath out "public-macos-product.json") (u/json-dump result))
      (println (u/geti result "status") "native rebuild, three public aliases, ordinary check/compile/run")
      (.flush sys/stdout))))

(defn -main [& args]
  (main (.resolve (pathlib/Path (or (u/opt args "--output") (sys/exit "--output is required"))))))

(when (some #(or (= % "check-public-macos-product.cljc") (str/ends-with? % "/check-public-macos-product.cljc")) sys/argv)
  (apply -main *command-line-args*))
