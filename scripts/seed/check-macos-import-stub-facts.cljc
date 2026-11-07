;; JUN-595: T2 must not derive whole-program facts from import stubs.
;;
;; A project compile gives each required module's export an import stub in the importer, a typing self call whose
;; first instruction the linker replaces with `b <export>`. T2's whole-program RET0 ("returns its parameter-0
;; vector"), may-change-descriptors and least-length facts used to read that SIR as if it were the export's code.
;; RET0 = 1 for a slice export made the result of a call alias its first argument, so a later vector-at read the
;; argument's element.
;;
;; The compiler under test builds a two-module program (an imported slice used through two private helpers,
;; exit = s[10] = 85) and an identity import (exit = 7). The negative control is a compiler built by the compiler
;; under test from the same unity with the four stub guards removed: it must read the wrong element. This script
;; stages bytes, launches native programs and signs copies.
;; Ported from check-macos-import-stub-facts.py (Basilisp, JUN-974). Apple Silicon macOS only.
;; Run: basilisp run -p scripts/seed scripts/seed/check-macos-import-stub-facts.cljc -- --compiler C --output DIR
(ns check-macos-import-stub-facts
  (:require [basilisp.string :as str]
            [gate-util :as u]
            [macos-image :as image]
            [macos-native-lib :as mac])
  (:import json operator pathlib re sys))

(def lib-source "(ns m.lib (:export [slice ident]))\n(defn slice [v :vector-i64 start :i64 count :i64] :vector-i64\n  (loop [i 0 out (vector-i64)]\n    (if (= i count) out (recur (+ i 1) (vector-conj out (vector-at v (+ start i)))))))\n(defn ident [v :vector-i64] :vector-i64 v)\n")
(def main-source "(ns m.main (:export [main]) (:require [m.lib :as c]))\n(defn- at [batch :vector-i64 offset :i64] :vector-i64\n  (c/slice batch offset (vector-at batch (- offset 1))))\n(defn- state [a :vector-i64] :vector-i64 (c/slice a 8 (vector-at a 6)))\n;; s = [1 0 1 0 0 0 0 0 0 0 85 0 0 0 0]; batch[10] = 1, s[10] = 85\n(defn- pick [batch :vector-i64 offset :i64 top :i64] :i64\n  (let [s (state (at batch offset))] (vector-at s 10)))\n(defn main [] :i64\n  (let [batch (c/slice (vector-i64 9 23 1 0 0 0 0 0 15 0 1 0 1 0 0 0 0 0 0 0 85 0 0 0 0) 0 25)]\n    (pick batch 2 1)))\n")
(def ident-source "(ns m.main (:export [main]) (:require [m.lib :as c]))\n(defn- middle [v :vector-i64] :i64 (let [w (c/ident v)] (vector-at w 1)))\n(defn main [] :i64 (middle (vector-i64 3 7 9)))\n")
(def guards [
 [" (not (gn-clamp-open M g)))\n                (t2-mcd-scan M (inc p)) 1)]"
  ")\n                (t2-mcd-scan M (inc p)) 1)]"]
 ["\n                                                             (not (gn-clamp-open m f)))"
  ")"]
 [" (lw-spec? M f) (lw-tmpl? M f) (gn-clamp-open M f))"
  " (lw-spec? M f) (lw-tmpl? M f))"]
 [" (= (t2-g M (+ t2-a-ret0 g)) 1) (not (gn-clamp-open M g)))))"
  " (= (t2-g M (+ t2-a-ret0 g)) 1))))"]
])

(defn project
  "Compile lib + main through the source-lock project route and run it."
  [compiler packager out main-src]
  (let [src (.joinpath out "src" "m")
        _ (.mkdir src ** :parents true)
        _ (.write_text (.joinpath src "lib.kotoba") lib-source)
        _ (.write_text (.joinpath src "main.kotoba") main-src)
        lock (.joinpath out "p.ksl")
        _ (.write_text lock (str "KSL1\nentry /src/m/main.kotoba\nroot /src\n"
                                 (apply str (for [n ["lib.kotoba" "main.kotoba"]]
                                              (str "file " (u/sha256-hex (.read_bytes (.joinpath src n))) " /src/m/" n "\n")))))
        flags ["--source-path" "/src" "--source-lock" (.-name lock) "--source-lock-sha256" (u/sha256-hex (.read_bytes lock))]
        _ (mac/native-run compiler out (concat ["compile" "/src/m/main.kotoba" "--target" "aarch64-macos" "--output" "p.kseed"] flags))
        r (mac/native-run compiler out ["extract-native" "p.kseed" "--symbol" "main" "--output" "p.raw"])
        m (re/search (.encode ":offset (\\d+), :length (\\d+), :arity 0}") (.-stdout r))]
    (u/chk (and m (= (python/int (.group m 2)) (.-st_size (.stat (.joinpath out "p.raw"))))) (.-stdout r))
    (mac/native-run packager out ["p-unsigned.macho" "p.raw" "fs2-cli-stdio-general" (.decode (.group m 1))])
    (mac/sign (.joinpath out "p-unsigned.macho") (.joinpath out "p.macho"))
    (.-returncode (image/run (.joinpath out "p.macho") out []))))

(defn mutant
  "A compiler built by the compiler under test from the unity without the guards."
  [compiler packager out]
  (.mkdir out)
  (mac/stage-unity out)
  (let [unity (.joinpath out "full-unity.kotoba")
        text (atom (.read_bytes unity))]
    (doseq [[fixed old] guards]
      (u/chk (= 1 (.count @text (.encode fixed))) (str "guard drifted " fixed))
      (reset! text (.replace @text (.encode fixed) (.encode old))))
    (.write_bytes unity @text)
    (first (mac/generation 1 compiler packager out))))

(defn main [compiler out]
  (u/chk (image/available?) "Apple Silicon host required")
  (.mkdir out ** :parents false :mode 0700 :exist_ok false)
  (let [[_ packager] (image/root-images)
        report (u/pydict "schema" "amu.macos-import-stub-facts.v1" "compiler" (mac/pin compiler) "packager" (mac/pin packager))
        slice (project compiler packager (.joinpath out "slice") main-source)
        _ (do (operator/setitem report "slice" slice)
              (u/chk (= 85 slice) (str "imported slice result aliased its argument " slice)))
        identity (project compiler packager (.joinpath out "identity") ident-source)
        _ (do (operator/setitem report "identity" identity)
              (u/chk (= 7 identity) (str "identity import " identity)))
        control (mutant compiler packager (.joinpath out "mutant"))
        _ (operator/setitem report "mutant" (mac/pin control))
        control-result (project control packager (.joinpath out "control") main-source)]
    (operator/setitem report "control" control-result)
    (u/chk (= 1 control-result) (str "the unguarded compiler must read the argument's element " control-result))
    (operator/setitem report "status" "PASS_MACOS_IMPORT_STUB_FACTS")
    (.write_text (.joinpath out "import-stub-facts.json") (u/json-dump report))
    (println (u/geti report "status"))
    (.flush sys/stdout)))

(defn -main [& args]
  (main (.resolve (pathlib/Path (or (u/opt args "--compiler") (sys/exit "--compiler is required"))))
        (.resolve (pathlib/Path (or (u/opt args "--output") (sys/exit "--output is required"))))))

(when (some #(or (= % "check-macos-import-stub-facts.cljc") (str/ends-with? % "/check-macos-import-stub-facts.cljc")) sys/argv)
  (apply -main *command-line-args*))
