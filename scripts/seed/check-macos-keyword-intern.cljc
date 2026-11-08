;; The Mac diagnostic runtime implements the keyword tables (JUN-707, JUN-710).
;;
;; Context ABI slots 80/88 are the public keyword graph (__r6-kgput / __r6-kgget, seed/77 on Linux) and 96/104 the
;; private keyword intern rows behind keyword-from-string, keyword-name, document-keyword-value and every other
;; __r6-kwreg caller (seed/73-keyword-intern.kotoba on Linux). The Mac runtime keeps each table in its own anonymous
;; mapping made on first use, outside every arena (4096 graph datoms, 262144 intern rows, as on Linux), and refuses a
;; wrong context tag, a failed mapping or a full table with one line on stderr and exit 70. Before JUN-707/708 none of
;; the four slots was installed and these programs died of SIGSEGV (exit 139). This gate compiles the oracles with the
;; descriptor's compiler, packages them with its packager, signs and runs them natively:
;;
;; * native-keyword-intern.kotoba (the repository's Linux oracle) main, which interns 1,800 keywords, poisons the
;;   public graph with an interned name's entity and interns inside arena-scope (exit 0); graph-full-main, all 4096
;;   public datoms beside the intern rows (exit 0); graph-overflow-main, datom 4097 (exit 70, the refusal line);
;; * macos-keyword-intern.kotoba main: literal keywords, document-keyword-value and Unicode round trips (exit 0);
;;   exhaust-main: more names than 262144 intern rows hold (exit 70);
;; * raw mains calling slot 80 and slot 96 with a context whose tag is not 11 (exit 70 each);
;; * a positive control without keywords.
;;
;; This script stages and observes; compiler, packager and the programs are native.
;; Ported from check-macos-keyword-intern.py (Basilisp, JUN-974). Apple Silicon macOS only.
;; Run: basilisp run -p scripts/seed scripts/seed/check-macos-keyword-intern.cljc -- --output DIR
(ns check-macos-keyword-intern
  (:require [basilisp.string :as str]
            [gate-util :as u]
            [macos-image :as image]
            [macos-native-lib :as mac])
  (:import pathlib re struct sys))

(def message "seed: keyword table failed (Mac runtime)\n")
(def oracle (.joinpath u/root "seed/tests/macos-keyword-intern.kotoba"))
(def linux-oracle (.joinpath u/root "seed/tests/native-keyword-intern.kotoba"))
(def plain "(ns plain (:export [main]))\n(defn main [] :i64 (if true 0 1))\n")

(defn build [compiler packager output name source symbol]
  (.write_text (.joinpath output (str name ".kotoba")) (if (string? source) source (.read_text source)))
  (mac/native-run compiler output ["compile" (str name ".kotoba") "--target" "aarch64-macos" "--output" (str name ".kseed")])
  (let [extracted (mac/native-run compiler output ["extract-native" (str name ".kseed") "--symbol" symbol "--output" (str name ".raw")])
        m (re/search (.encode ":offset (\\d+), :length (\\d+), :arity 0}") (.-stdout extracted))]
    (when (or (nil? m) (not= (python/int (.group m 2)) (.-st_size (.stat (.joinpath output (str name ".raw"))))))
      (mac/fail (str "native extraction did not match raw bytes: " name)))
    (mac/native-run packager output [(str name "-unsigned.macho") (str name ".raw") "fs2-cli-stdio-general" (.decode (.group m 1))])
    (mac/sign (.joinpath output (str name "-unsigned.macho")) (.joinpath output (str name ".macho")))
    (.joinpath output (str name ".macho"))))

(defn main [output]
  (when-not (mac/available?) (mac/fail "Apple Silicon native host required"))
  (let [[compiler packager] (image/root-images)
        _ (mac/verify-macho compiler)
        _ (mac/verify-macho packager)
        _ (.mkdir output ** :parents false :mode 0700 :exist_ok false)
        runs (.joinpath output "runs")
        _ (.mkdir runs ** :mode 0700)
        stderr-of (fn [result] (.decode (.-stderr result) "utf-8" "replace"))]
    (doseq [[name source symbol expected refused] [["plain" plain "main" 0 false]
                                                   ["intern-main" linux-oracle "main" 0 false]
                                                   ["graph-full" linux-oracle "graph-full-main" 0 false]
                                                   ["graph-overflow" linux-oracle "graph-overflow-main" 70 true]
                                                   ["keywords" oracle "main" 0 false]
                                                   ["exhaust" oracle "exhaust-main" 70 true]]]
      (let [img (build compiler packager runs name source symbol)
            result (mac/native-run img runs [] :expected expected)
            stderr (stderr-of result)]
        (when (and refused (not= stderr message)) (mac/fail (str name ": failure text changed: " (pr-str stderr))))
        (when (and (not refused) (seq stderr)) (mac/fail (str name ": unexpected stderr " (pr-str stderr))))
        (println (str name ": exit " expected))
        (.flush sys/stdout)))
    ;; A wrong context tag: no source form passes one, so each fixture is a six-word main (stp x29,x30,[sp,#-16]!;
    ;; mov x0,sp; ldr x16,[x7,#slot]; blr x16; ldp; ret) whose "context" is the saved frame pointer on the stack.
    (doseq [[name load] [["badtag-graph" 0xf94028f0] ["badtag-intern" 0xf94030f0]]]
      (.write_bytes (.joinpath runs (str name ".raw"))
                    (.join (u/bytes-of) (python/list (for [word [0xa9bf7bfd 0x910003e0 load 0xd63f0200 0xa8c17bfd 0xd65f03c0]]
                                                       (struct/pack "<I" word)))))
      (mac/native-run packager runs [(str name "-unsigned.macho") (str name ".raw") "fs2-cli-stdio-general" "0"])
      (mac/sign (.joinpath runs (str name "-unsigned.macho")) (.joinpath runs (str name ".macho")))
      (let [result (mac/native-run (.joinpath runs (str name ".macho")) runs [] :expected 70)]
        (when (not= (stderr-of result) message)
          (mac/fail (str name ": a wrong context tag did not report the keyword table failure"))))
      (println (str name ": exit 70"))
      (.flush sys/stdout))
    (println "PASS_MAC_KEYWORD_TABLES oracles exit 0, graph datom 4097 -> 70, 262144 intern rows -> 70, wrong tag -> 70")
    (.flush sys/stdout)))

(defn -main [& args]
  (main (.resolve (pathlib/Path (or (u/opt args "--output") (sys/exit "--output is required"))))))

(when (some #(or (= % "check-macos-keyword-intern.cljc") (str/ends-with? % "/check-macos-keyword-intern.cljc")) sys/argv)
  (apply -main *command-line-args*))
