;; Native document-edn-read treats EDN delimiters as the spec does (JUN-650).
;;
;; The document library that seed/21-check appends to a program keeps a document as its EDN text, and every reader in
;; it (count, get, nth, kind, ...) assumes exactly one space between items. document-edn-read now canonicalizes its
;; input (comma, tab, LF, VT, FF, CR and runs of spaces are delimiters, ; starts a comment, no space at either end,
;; after an opener or before a closer). This gate, on Apple Silicon:
;; * builds seed/tests/native-document-edn-read.kotoba with --compiler (the Mac fixed point of this tree) and the
;;   descriptor's packager, and runs it: exit 0;
;; * negative control: builds a mutant full compiler from this tree's FULL-MANIFEST with document-edn-read put back to
;;   the identity it was before JUN-650, builds the same corpus with it and runs it: it must fail at case 1 (exit 1);
;; * runs the corpus through the public CLI (bin/amu run), which must print 0.
;; This stages sources and observes processes; every compiler and program is a native Amu-built Mach-O.
;; Ported from check-document-edn-read.py (Basilisp, JUN-974). Apple Silicon macOS only.
;; Run: basilisp run -p scripts/seed scripts/seed/check-document-edn-read.cljc -- --compiler C --output DIR
(ns check-document-edn-read
  (:require [basilisp.string :as str]
            [gate-util :as u]
            [macos-image :as image]
            [macos-native-lib :as mac]
            [macos-scope-build :as sb])
  (:import pathlib subprocess sys))

(def corpus (.joinpath u/root "seed/tests/native-document-edn-read.kotoba"))
(def check "seed/21-check.kotoba")
(def fixed "(defn- document-edn-read [s :string] :document (__r6-dd (__kr_dnorm s)))")
(def unfixed "(defn- document-edn-read [s :string] :document (__r6-dd s))")

(defn main [compiler output]
  (when-not (mac/available?) (mac/fail "Apple Silicon native host required"))
  (let [[_ packager] (image/root-images)
        _ (mac/verify-macho compiler)
        _ (mac/verify-macho packager)
        _ (.mkdir output ** :parents false :mode 0700 :exist_ok false)
        fixed-dir (.joinpath output "fixed")
        _ (.mkdir fixed-dir ** :mode 0700)
        img (sb/build compiler packager fixed-dir "corpus" corpus)
        _ (mac/native-run img fixed-dir [] :expected 0)
        _ (do (println "fixed compiler: corpus exit 0") (.flush sys/stdout))
        ;; Negative control: the same tree with document-edn-read as the identity.
        mutant (.joinpath output "mutant")
        _ (.mkdir mutant ** :mode 0700)
        names (vec (filter #(and (seq %) (not (.startswith % "#"))) (.splitlines (.read_text mac/manifest))))
        _ (when-not (contains? (set names) check) (mac/fail (str "FULL-MANIFEST no longer lists " check)))
        check-text (.read_text (.joinpath u/root check))
        _ (when (or (not= 1 (.count check-text fixed)) (not= 0 (.count check-text unfixed)))
            (mac/fail "cannot construct the identity document-edn-read negative control"))
        unity (apply str (for [name names]
                           (let [text (.read_text (.joinpath u/root name))]
                             (str (if (= name check) (.replace text fixed unfixed) text) "\n"))))
        _ (.write_text (.joinpath mutant "full-unity.kotoba") unity)
        mutant-compiler (sb/build compiler packager mutant "full-unity" (.read_text (.joinpath mutant "full-unity.kotoba")))
        _ (when (u/deq (mac/pin mutant-compiler) (mac/pin compiler)) (mac/fail "mutant compiler is identical to the compiler under test"))
        img (sb/build mutant-compiler packager mutant "corpus" corpus)
        _ (mac/native-run img mutant [] :expected 1)
        _ (do (println "identity document-edn-read (mutant compiler): corpus exit 1") (.flush sys/stdout))
        ;; The public CLI built from this tree runs the same corpus.
        public (.joinpath output "public")
        _ (.mkdir public ** :mode 0700)
        _ (.write_bytes (.joinpath public "corpus.kotoba") (.read_bytes corpus))
        result (subprocess/run (python/list [(str (.joinpath u/root "bin/amu")) "run" "corpus.kotoba"]) ** :cwd public
                               :env (python/dict {"PATH" "/usr/bin:/bin" "LANG" "C"}) :capture_output true :timeout 600)]
    (when (or (not (zero? (.-returncode result))) (not (u/deq (.-stdout result) (.encode "0\n"))) (u/nonempty? (.-stderr result)))
      (mac/fail (str "bin/amu run: exit " (.-returncode result) ", stdout " (.-stdout result) ", stderr " (.-stderr result))))
    (println "bin/amu run corpus: 0")
    (println "PASS_NATIVE_DOCUMENT_EDN_READ_WITH_NEGATIVE_CONTROL")
    (.flush sys/stdout)))

(defn -main [& args]
  (main (.resolve (pathlib/Path (or (u/opt args "--compiler") (sys/exit "--compiler is required"))) ** :strict true)
        (.resolve (pathlib/Path (or (u/opt args "--output") (sys/exit "--output is required"))))))

(when (some #(or (= % "check-document-edn-read.cljc") (str/ends-with? % "/check-document-edn-read.cljc")) sys/argv)
  (apply -main *command-line-args*))
