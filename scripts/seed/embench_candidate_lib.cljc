;; Pure helpers of the native embench candidate observers (pins, ELF/arena/entry checks, provenance).
;; Split out of check-embench-native-candidate.cljc (Basilisp port of check-embench-native-candidate.py) so the other
;; benchmark observers and the tests can `require` it instead of loading a hyphenated script by path.
(ns embench-candidate-lib
  (:require [gate-util :as u])
  (:import operator pathlib platform re struct))

(def entry-sha "3572dfb834b5479d4694e9554e67ad6b7e02e517d19c480c4943955bb79c4849")
(def data-pins
  (u/pydict "round-sa-m104-20261015/expected/measured-images.json" "c0c9a31deba334a8c5402554719e1b012c02debe8c5963e9316fe322f3bf179a"
            "round-sa-m104-20261015/workloads.json" "c83550918d2125497d5ed75ca5d9a9ff83d509ce87f33dbc33f2ca95678d56c8"
            "round-sa-m104-20261015/records/round/expected-accounting-mw.json" "6368bd343086a6c88e0645e31dde82bcdf64742c7b4727cdd56103ef72e9b4cc"))
(def fields
  ["pairs" "string-pool-bytes" "vectors" "vector-items" "heap-bytes" "conj" "conj-tail" "conj-region" "conj-copy" "copied-words"
   "reserved-words" "regions" "scope-releases" "string-regions" "string-region-appends" "string-copied-bytes" "string-reserved-bytes"])

(defn pin [path] (u/pin path))

(defn elf [path machine]
  (let [raw (.read_bytes path)]
    (u/chk (and (= (u/bslice raw 0 8) (u/bytes-of 0x7f 0x45 0x4c 0x46 2 1 1 0))
                (= [2 machine] (vec (struct/unpack_from "<HH" raw 16)))))
    (let [offset (u/geti (struct/unpack_from "<Q" raw 32) 0)
          [size cnt] (vec (struct/unpack_from "<HH" raw 54))]
      (u/chk (and (= 56 size) (< 0 cnt 17) (<= (+ offset (* size cnt)) (python/len raw))))
      (u/chk (every? (fn [i] (not (contains? #{2 3} (u/geti (struct/unpack_from "<I" raw (+ offset (* size i))) 0)))) (range cnt)))
      (pin path))))

(defn arena
  "The 17 canonical KEXE_ARENA_USE counters in order, or nil."
  [raw]
  (when-let [m (re/fullmatch (.encode "KEXE_ARENA_USE \\{(.+)\\}\n") raw)]
    (let [pairs (vec (re/findall (.encode ":([a-z-]+) ([0-9]+)") (.group m 1)))]
      (when (and (= fields (mapv #(.decode (first %)) pairs))
                 (= (.group m 1) (.join (.encode " ") (python/list (for [[k v] pairs] (operator/add (operator/add (operator/add (.encode ":") k) (.encode " ")) v))))))
        (u/pydict-from (for [[k v] pairs] [(.decode k) (python/int v)]))))))

(defn entry-offset [extracted payload]
  (let [header (re/fullmatch (.encode "\\{:ok true, :output \"([^\"\\r\\n]+)\", :offset ([0-9]+), :length ([0-9]+), :arity 0\\}\n") extracted)]
    (u/chk (and header (= (.decode (.group header 1)) (str payload)) (= (python/int (.group header 3)) (.-st_size (.stat payload)))))
    (let [offset (python/int (.group header 2))]
      (u/chk (and (<= 0 offset) (< offset (.-st_size (.stat payload))) (zero? (mod offset 4))))
      offset)))

(defn verify-bundle-data [package entry]
  (u/chk (= entry-sha (u/geti (pin entry) "sha256")))
  (u/chk (every? (fn [[name digest]] (= digest (u/geti (pin (.joinpath package name)) "sha256"))) (.items data-pins))))

(defn provenance
  "Returns [compiler machine target receipt source]. Exactly one of one/complete is given."
  [one complete]
  (let [arch (platform/machine)
        root u/root
        _ (u/chk (and (= "Linux" (platform/system)) (contains? #{"aarch64" "x86_64"} arch)))
        paths (u/manifest-paths (.joinpath root "seed/FULL-MANIFEST"))
        source (u/pydict-from (for [p (cons "seed/FULL-MANIFEST" paths)] [p (pin (.joinpath root p))]))
        unity (.join (u/bytes-of) (python/list (for [p paths] (operator/add (.read_bytes (.joinpath root p)) (.encode "\n")))))]
    (if (= arch "aarch64")
      (do
        (u/chk (and one (not complete)))
        (let [receipt (.joinpath one "one-compiler.json")
              proof (u/read-json receipt)]
          (u/chk (and (= "PASS_COMBINED_COMPILER" (u/geti proof "status")) (= ["Linux" arch] (vec (take 2 (u/geti proof "host"))))))
          (u/chk (and (not (u/geti proof "cCompilerOrLoader")) (not (u/geti proof "emulation"))))
          (u/chk (u/deq source (u/geti (u/geti proof "sources") "seed/FULL-MANIFEST")))
          (let [f (u/geti proof "F") containers (u/geti f "containers")]
            (u/chk (and (= 3 (python/len containers)) (every? #(u/deq % (u/geti containers 0)) containers)))
            (u/chk (u/deq (u/geti f "image") (u/geti f "packedByF")))
            (doseq [i [1 2 3]]
              (u/chk (u/deq (pin (.joinpath one (str "F" i ".kseed"))) (u/geti containers (dec i)))))
            (doseq [i [1 2]]
              (u/chk (u/deq (elf (.joinpath one (str "F" i ".elf")) 183) (u/geti f "image")))))
          [(.joinpath one "F2.elf") 183 "aarch64-linux" receipt source]))
      (do
        (u/chk (and complete (not one)))
        (let [receipt (.joinpath complete "complete-x86.json")
              proof (u/read-json receipt)]
          (u/chk (and (= "PASS_COMPLETE_NATIVE_X86_COMPILER_BUILD" (u/geti proof "status")) (= ["Linux" arch] (vec (take 2 (u/geti proof "host"))))))
          (u/chk (and (not (u/geti proof "cCompilerOrLoader")) (not (u/geti proof "JVMNodeOrGraalFallback")) (not (u/geti proof "emulation"))))
          (u/chk (u/deq (u/geti proof "sourceUnity") (u/pydict "bytes" (python/len unity) "sha256" (u/sha256-hex unity))))
          (let [gens (u/geti proof "generations")]
            (u/chk (and (= 3 (python/len gens)) (u/deq (u/geti gens 0) (u/geti gens 1)) (u/deq (u/geti gens 1) (u/geti gens 2))))
            (doseq [i [1 2 3]]
              (u/chk (u/deq (elf (.joinpath complete (str "F" i ".elf")) 62)
                            (u/pydict-from (for [k ["bytes" "sha256"]] [k (u/geti (u/geti gens (dec i)) k)]))))))
          [(.joinpath complete "F3.elf") 62 "x86_64-linux" receipt source])))))

