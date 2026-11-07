;; Cheap source/image preflight; not compiler or controller qualification.
;; Ported from check-native-identities.py (Basilisp). Runs at the start of many jobs.
;; Run: basilisp run scripts/seed/check-native-identities.cljc -- [--source-candidate-sha256 SHA]
;;      (SOURCE_CANDIDATE_SHA256 in the environment is the default)
(ns check-native-identities
  (:require [basilisp.string :as str]
            [gate-util :as u])
  (:import hashlib operator os pathlib sys))

(defn- identity [data] (u/pydict "bytes" (python/len data) "sha256" (u/sha256-hex data)))
(defn- id-of [p] (identity (.read_bytes p)))
(defn- subset [m ks] (u/pydict-from (for [k ks] [k (u/geti m k)])))
(defn- cat-bytes [parts] (.join (u/bytes-of) (python/list parts)))
(defn- resolve-path [p] (.resolve p))

(defn main [source-candidate-sha256]
  (let [root u/root
        r (fn [rel] (.joinpath root rel))
        product (u/read-json (r "native-product.json"))
        root-json (u/read-json (r "seed/bootstrap/aarch64-linux-static-root.json"))
        paths (u/manifest-paths (r "seed/FULL-MANIFEST"))
        _ (u/chk (= (count paths) (u/geti product "sourceModuleCount")))
        unity (cat-bytes (for [p paths] (operator/add (.read_bytes (r p)) (.encode "\n"))))
        current-source-unity (identity unity)]
    (if (not (u/deq current-source-unity (u/geti product "sourceUnity")))
      (u/chk (= source-candidate-sha256 (u/geti current-source-unity "sha256")) "candidate source unity SHA mismatch")
      (u/chk (contains? #{nil (u/geti current-source-unity "sha256")} source-candidate-sha256) "candidate source unity SHA mismatch"))
    (u/chk (u/deq (u/geti product "sourceUnity") (u/geti root-json "sourceUnity")))
    (u/chk (u/deq (id-of (r "bin/amu-linux-x86_64")) (u/geti product "image")))
    (doseq [alias (u/geti product "aliases")]
      (u/chk (= (resolve-path (r alias)) (resolve-path (r "bin/amu-linux-x86_64")))))
    ;; KOTOBA-174 / ADR 0396: the public Linux x86_64 host entry names x86_64-linux
    (let [host (u/geti product "hostEntry")]
      (u/chk (and (= "x86_64-linux" (u/geti host "target")) (= "bin/x86_64-linux/amu" (u/geti host "entry"))))
      (let [host-image (r (u/geti host "entry"))]
        (u/chk (and (not (.is_symlink host-image)) (u/deq (id-of host-image) (u/geti host "image"))))
        (u/chk (not (u/deq (u/geti host "image") (u/geti product "image"))) "host entry must not be the engine-neutral compiler image")
        (doseq [alias (u/geti host "aliases")]
          (u/chk (and (.is_symlink (r alias)) (= (resolve-path (r alias)) (resolve-path host-image)))))))
    (let [root-image (id-of (r "seed/bootstrap/aarch64-linux-static-root.elf"))]
      (u/chk (and (u/deq root-image (u/geti root-json "image")) (u/deq (u/geti root-json "image") (u/geti product "rootImage")))))
    (let [mac (u/read-json (r "seed/bootstrap/aarch64-macos/root.json"))
          _ (u/chk (u/deq (u/geti mac "fullSource") (u/geti product "sourceUnity")))
          mac-image (r (u/geti (u/geti mac "compiler") "path"))
          bytes-sha ["bytes" "sha256"]
          _ (u/chk (u/deq (id-of mac-image) (subset (u/geti mac "compiler") bytes-sha)))
          macho (u/hex->bytes "cffaedfe0c000001")
          _ (u/chk (= macho (u/bslice (.read_bytes mac-image) 0 8)))
          cli (u/read-json (r "seed/bootstrap/aarch64-macos/cli.json"))
          _ (u/chk (= "amu.macos-native-cli.v1" (u/geti cli "schema")))
          _ (u/chk (and (u/deq (u/geti cli "compiler") (u/geti mac "compiler")) (u/deq (u/geti cli "packager") (u/geti mac "packager"))) "stale public Mac dependency pins")
          _ (u/chk (= "seed/bootstrap/aarch64-macos/amu-cli.macho" (u/geti (u/geti cli "image") "path")))
          public-image (r (u/geti (u/geti cli "image") "path"))
          _ (u/chk (u/deq (id-of public-image) (subset (u/geti cli "image") bytes-sha)) "public Mac image pin mismatch")
          _ (u/chk (= macho (u/bslice (.read_bytes public-image) 0 8)))]
      (doseq [role ["packager" "packagerSource"]]
        (u/chk (u/deq (id-of (r (u/geti (u/geti mac role) "path"))) (subset (u/geti mac role) bytes-sha))))
      (let [core (vec (take (inc (.index (python/list paths) "seed/90-drv.kotoba")) paths))
            _ (u/chk (and (= 18 (count core)) (= 18 (count (set core))) (contains? (set core) "seed/19-decimal.kotoba")))
            source-names (into core ["seed/macos-cli-api.kotoba" "seed/macos-cli.kotoba"])
            _ (u/chk (= (set (python/list (u/geti cli "sources"))) (set source-names)) "public Mac source recipe mismatch")]
        (doseq [name source-names]
          (u/chk (u/deq (id-of (r name)) (u/geti (u/geti cli "sources") name)) (str "public Mac source pin mismatch: " name)))
        (let [pins (.encode (str "(def MC-COMPILER-SHA256 \"" (u/geti (u/geti mac "compiler") "sha256") "\")\n"
                                 "(def MC-PACKAGER-SHA256 \"" (u/geti (u/geti mac "packager") "sha256") "\")\n"))
              cli-unity (cat-bytes (concat (for [name (conj core "seed/macos-cli-api.kotoba")] (operator/add (.read_bytes (r name)) (.encode "\n")))
                                           [pins (.encode "\n") (.read_bytes (r "seed/macos-cli.kotoba")) (.encode "\n")]))]
          (u/chk (u/deq (identity cli-unity) (u/geti cli "unity")) "public Mac unity pin mismatch"))
        (doseq [name ["amu" "kotoba" "kotoba-compiler"]]
          (let [alias (r (str "bin/" name))]
            (u/chk (and (.is_symlink alias) (= (.resolve alias ** :strict true) (.resolve public-image ** :strict true))) "public Mac alias mismatch")))
        (load-file (str (r "scripts/seed/check-native-cdci.cljc")))
        (let [checker-pin @(resolve 'check-native-cdci/controller-pin-metadata)
              policy (u/read-json (r "seed/cdci/policy.json"))]
          (checker-pin policy))
        (println "PASS_NATIVE_IDENTITIES_PREFLIGHT_ONLY" (count paths) "production modules"
                 "candidate-source" (if source-candidate-sha256 (u/geti current-source-unity "sha256") "none"))))))

(defn -main [& args]
  (main (or (u/opt args "--source-candidate-sha256")
            (not-empty (.get os/environ "SOURCE_CANDIDATE_SHA256")))))

(when (some #(or (= % "check-native-identities.cljc") (str/ends-with? % "/check-native-identities.cljc")) sys/argv)
  (apply -main *command-line-args*))
