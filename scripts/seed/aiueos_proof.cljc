;; Bind AIUEOS diagnostics to actual native compiler generations and source.
;;
;; Process orchestration only. This does not own the native CDCI verdict.
;; Ported from aiueos_native_proof.py (Basilisp). Linux only. Named aiueos_proof while the Python original is still imported by unported gates.
(ns aiueos-proof
  (:require [gate-util :as u])
  (:import hashlib platform))

(defn load-native-producers
  "Returns [source producers baseline]. Exactly one of build/complete must be given (a directory path)."
  [& {:keys [build complete]}]
  (u/chk (= "Linux" (platform/system)))
  (u/chk (not= (nil? build) (nil? complete)) "select one native proof")
  (let [paths (u/manifest-paths (.joinpath u/root "seed/FULL-MANIFEST"))
        source (u/pydict-from (for [p (cons "seed/FULL-MANIFEST" paths)] [p (u/pin (.joinpath u/root p))]))]
    (if complete
      (do
        (u/chk (contains? #{"x86_64" "AMD64"} (platform/machine)) "actual native Linux x86_64 required")
        (let [receipt (u/read-json (.joinpath complete "complete-x86.json"))]
          (u/chk (= "PASS_COMPLETE_NATIVE_X86_COMPILER_BUILD" (u/geti receipt "status")))
          (u/chk (and (not (u/geti receipt "cCompilerOrLoader")) (not (u/geti receipt "JVMNodeOrGraalFallback"))
                      (not (u/geti receipt "emulation"))))
          (let [unity (.join (u/bytes-of) (python/list (for [p paths] (u/concat-bytes (.read_bytes (.joinpath u/root p)) (u/bytes-of 10)))))]
            (u/chk (u/deq (u/pydict "bytes" (python/len unity) "sha256" (u/sha256-hex unity)) (u/geti receipt "sourceUnity"))))
          (let [gens (u/geti receipt "generations")]
            (u/chk (and (= 3 (python/len gens)) (u/deq (u/geti gens 0) (u/geti gens 1)) (u/deq (u/geti gens 1) (u/geti gens 2))))
            (let [producers (vec (for [i [2 3]]
                                   [(.joinpath complete (str "F" i ".elf"))
                                    (u/pydict "bytes" (u/geti (u/geti gens (dec i)) "bytes") "sha256" (u/geti (u/geti gens (dec i)) "sha256"))]))
                  baseline (.joinpath u/root "bin/amu-linux-x86_64")
                  expected (u/geti (u/read-json (.joinpath u/root "native-product.json")) "image")]
              (doseq [[p identity] producers]
                (u/chk (u/deq (u/pin p) identity) ["producer pin drift" p]))
              (u/chk (u/deq (u/pin baseline) expected) "baseline native compiler pin drift")
              [source (mapv first producers) baseline]))))
      (do
        (u/chk (contains? #{"aarch64" "arm64"} (platform/machine)) "actual native Linux ARM64 required")
        (let [receipt (u/read-json (.joinpath build "selfhost-bootstrap.json"))]
          (u/chk (= "PASS_LOADERLESS_SELFHOST_BOOTSTRAP" (u/geti receipt "status")))
          (u/chk (and (not (u/geti receipt "cCompilerOrLoader")) (not (u/geti receipt "JVMNodeOrGraalFallback"))
                      (not (u/geti receipt "emulation"))))
          (u/chk (u/deq source (u/geti (u/geti receipt "sourceGraph") "full")) "current full source differs")
          (let [gens (u/geti receipt "generations")
                root-image (u/geti (u/geti receipt "root") "image")
                producers (if (= 1 (python/len gens))
                            ;; After adoption the root is already the fixed point. This is valid only when the
                            ;; measured rebuild reproduces those bytes.
                            (do (u/chk (and (u/geti receipt "rootReproduces") (u/deq (u/geti (u/geti gens 0) "image") root-image)))
                                [[(.joinpath build "root.elf") root-image]
                                 [(.joinpath build (str (u/geti (u/geti gens 0) "name") ".elf")) (u/geti (u/geti gens 0) "image")]])
                            (do (u/chk (and (>= (python/len gens) 2)
                                            (u/deq (u/geti (u/geti gens -1) "image") (u/geti (u/geti gens -2) "image"))))
                                (vec (for [g [(u/geti gens -2) (u/geti gens -1)]]
                                       [(.joinpath build (str (u/geti g "name") ".elf")) (u/geti g "image")]))))
                baseline (.joinpath build "root.elf")]
            (doseq [[p identity] producers]
              (u/chk (u/deq (u/pin p) identity) ["producer pin drift" p]))
            (u/chk (u/deq (u/pin baseline) root-image) "baseline native compiler pin drift")
            [source (mapv first producers) baseline]))))))
