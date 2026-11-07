;; Shared body of the "--selfbuild-output" control gates (check-sequential-scan, check-positive-quotient-proof).
;; Ported from the Python originals (JUN-974). --selfbuild-output is the output directory of
;; selfhost-bootstrap; everything runs through its C-free aarch64 runner (R-aarch64.elf) and the producer is its
;; adopted fixed-point image (G3.bin). Run on arm64 Linux.
(ns selfbuild-controls
  (:require [gate-util :as u])
  (:import json operator os pathlib shutil sys))

(defn run
  "opts: :dir :producer :fixture :calls :report :prefix :status :fields (vector of [k v] before the common tail)."
  [out {:keys [dir producer fixture calls report prefix status fields]}]
  (let [root u/root
        out (.resolve (pathlib/Path out))
        _ (.mkdir (.joinpath out "artifacts") ** :exist_ok true)
        _ (.mkdir (.joinpath out "host") ** :exist_ok true)
        host (.joinpath out "host")
        d (.joinpath out (str "artifacts/" dir))
        _ (.mkdir d ** :exist_ok false)
        receipt (u/read-json (.joinpath root "seed/adoption-20261022.json"))
        loader (.joinpath out "R-aarch64.elf")
        prod (.joinpath host producer)
        _ (shutil/copy2 (.joinpath out "G3.bin") prod)
        sha (fn [p] (u/sha256-hex (.read_bytes (pathlib/Path p))))
        _ (u/chk (= (sha prod) (u/geti receipt "nativeImageSHA256")))
        paths (u/manifest-paths (.joinpath root "seed/MANIFEST"))
        fix (.joinpath root fixture)
        source (.joinpath d "controls.kotoba")
        ;; internal generator controls omit the separately qualified CLI driver
        body (.join (u/bytes-of)
                    (python/list (for [p paths :when (not (contains? #{"seed/90-drv.kotoba" "seed/99-entry.kotoba"} p))]
                                   (operator/add (.read_bytes (.joinpath root p)) (.encode "\n")))))
        _ (.write_bytes source (operator/add (operator/add body (.read_bytes fix)) (.encode "\n")))
        pins [[loader (sha loader)] [prod (sha prod)] [source (sha source)] [fix (sha fix)]]
        env (python/dict (for [[k v] (.items os/environ) :when (not (.startswith k "KEXE_"))] (python/tuple [k v])))
        _ (.update env (python/dict {"KEXE_COMMAND" "1" "KEXE_STACK_BYTES" "8388608" "KEXE_CAP_RESOURCES_35" (str d)
                                    "KEXE_FUEL" "off" "KEXE_VECTORS" "4194304" "KEXE_VECTOR_ITEMS" "134217728"
                                    "KEXE_STRING_POOL" "268435456" "KEXE_PAIRS" "16777216" "KEXE_CPU_SECONDS" "1800"
                                    "KEXE_WALL_SECONDS" "1800" "TMPDIR" (str d)}))
        rows (python/list)
        call (fn [name p args]
               (let [z (u/run-process (concat [loader p "0" "0" "aarch64" "35,37,38,39" "--"] args) env 1800 :cwd d)]
                 (.write_bytes (.joinpath host (str name ".stdout")) (.-stdout z))
                 (.write_bytes (.joinpath host (str name ".stderr")) (.-stderr z))
                 (.append rows (u/pydict "name" name "exit" (.-returncode z)))
                 (.write_text (.joinpath host calls) (u/json-dump rows))
                 (u/chk (and (zero? (.-returncode z)) (not (u/nonempty? (.-stderr z))) (every? (fn [[p h]] (= (sha p) h)) pins)) name)
                 (.-stdout z)))
        kseed (.joinpath d "controls.kseed")
        bin (.joinpath d "controls.bin")]
    (call (str prefix "-compile") prod ["compile" source "--target" "aarch64-macos" "--output" kseed])
    (call (str prefix "-extract") prod ["extract-native" kseed "--symbol" "main" "--output" bin])
    (let [parts (.split (.read_bytes kseed) (.encode "\n\n") 1)
          h (first parts) payload (second parts)]
      (u/chk (and (u/deq payload (.read_bytes bin)) (= (vec (rest (.splitlines (.decode h)))) ["main 0 0"]))))
    (let [result (call (str prefix "-execute") bin [])]
      (u/chk (u/deq result (.encode (str status "\n")))))
    (let [r (u/pydict-from (concat [["status" status] ["compilerCalls" 2] ["controlInvocations" 1]] fields
                                   [["compilerImageSHA256" (sha prod)] ["fixtureSHA256" (sha fix)] ["performanceMeasured" false]]))]
      (.write_text (.joinpath host report) (u/json-dump r))
      (println status)
      (.flush sys/stdout))))
