;; Native keyword-keyed map literals are closed records, and records hold :f64 fields (JUN-728).
;;
;; lang/guest-grammar.edn :map-literal :value-types :keyword-keys and the amu ladder floor :literal-typing
;; (docs/language-ladder.edn): a keyword map literal is a closed record wherever it is written. seed/21-check (ck-kwrec)
;; types it by its values; literals with the same keys and field types share one anonymous record type; 30-lower
;; (lw-kwrec) builds the pair chain in the printed-text order of the keys. A record field may be :f64 (an i64 word of
;; IEEE-754 bits). This gate, on Apple Silicon:
;; * builds seed/tests/native-keyword-map-record.kotoba with --compiler (the Mac fixed point of this tree) and the
;;   descriptor's packager and runs it: exit 0;
;; * checks that each refusal below is refused at check time with its named code;
;; * negative controls: two mutant full compilers built from this tree's FULL-MANIFEST -- one without the
;;   keyword-literal route (the typed-map literal only, as before JUN-728), one that refuses :f64 record fields
;;   again -- must refuse the corpus with E2105 and E2128;
;; * runs the corpus through the public CLI (bin/amu run), which must print 0.
;; This stages sources and observes processes; every compiler and program is a native Amu-built Mach-O.
;; Ported from check-keyword-map-record.py (Basilisp, JUN-974). Apple Silicon macOS only.
;; Run: basilisp run -p scripts/seed scripts/seed/check-keyword-map-record.cljc -- --compiler C --output DIR
(ns check-keyword-map-record
  (:require [basilisp.string :as str]
            [gate-util :as u]
            [macos-image :as image]
            [macos-native-lib :as mac]
            [macos-scope-build :as sb])
  (:import pathlib subprocess sys))

(def corpus (.joinpath u/root "seed/tests/native-keyword-map-record.kotoba"))
(def check "seed/21-check.kotoba")
;; Mutate the actual keyword branch, not the enclosing conditional: the latter also handles JUN-733 empty row literals
;; on newer main revisions.
(def literal "(ck-kwrec M n fx)")
(def f64 ["(= ty ck-ty-f32) (ck-err M1 E-CHECK-SCHEMA k 0)" "(= ty ck-ty-f32) (ck-err M1 E-CHECK-SCHEMA c 0)"])
(def mutants
  [["no-keyword-literal" [[literal "(ck-maplit2 M n fx)"]] "E2105"]
   ["no-f64-field" (vec (for [x f64] [x (.replace x "(= ty ck-ty-f32)" "(or (= ty TY-F64) (= ty ck-ty-f32))")])) "E2128"]])
(def refusals
  [;; JUN-733: (assoc {:a 1} :b 2) extends the row (check-row-operations); a field the record lacks is still refused
   ["assoc-new-key-read-absent" "(defn main [] :i64 (let [m (assoc {:a 1} :b 2)] (:c m)))" "E2127"]
   ["absent-key" "(defn main [] :i64 (let [m {:a 1}] (:z m)))" "E2127"]
   ["mixed-key-kinds" "(defn main [] :i64 (let [m {:a 1 \"b\" 2}] 0))" "E2105"]
   ["repeated-key" "(defn main [] :i64 (let [m {:a 1 :a 2}] 0))" "E2128"]
   ["fn-value" "(defn main [] :i64 (let [m {:f (fn [x] x)}] 0))" "E2128"]
   ["f32-field" "(defrecord W [x :f32])\n(defn main [] :i64 0)" "E2128"]
   ["33-fields" (str "(defn main [] :i64 (let [m {" (str/join " " (for [i (range 33)] (str ":k" i " " i))) "}] 0))") "E2128"]
   ["empty" "(defn main [] :i64 (let [m {}] 0))" "E2133"]
   ;; JUN-733: a literal of the declared record's shape is that record (check-record-identity-option); one of another
   ;; shape is still refused
   ["declared-record-parameter-other-shape"
    (str "(defn g [m [:record :kotoba.map-literal/a+b [[:a :i64] [:b :string]]]] :i64 (:a m))\n"
         "(defn main [] :i64 (g {:a 4 :b 5}))") "E2104"]])

(defn main [compiler output]
  (when-not (mac/available?) (mac/fail "Apple Silicon native host required"))
  (let [[_ packager] (image/root-images)
        _ (mac/verify-macho compiler)
        _ (mac/verify-macho packager)
        _ (.mkdir output ** :parents false :mode 0700 :exist_ok false)
        fixed (.joinpath output "fixed")
        _ (.mkdir fixed ** :mode 0700)
        img (sb/build compiler packager fixed "corpus" corpus)
        _ (mac/native-run img fixed [] :expected 0)
        _ (do (println "fixed compiler: corpus exit 0") (.flush sys/stdout))
        refusal-dir (.joinpath output "refusals")
        _ (.mkdir refusal-dir ** :mode 0700)]
    (doseq [[name src code] refusals]
      (let [[status text] (sb/check-source compiler refusal-dir name src)]
        (when (or (zero? status) (not (.__contains__ text code)))
          (mac/fail (str name ": expected a check-time " code ", got exit " status ": " (pr-str (subs text (max 0 (- (count text) 300)))))))
        (println (str "refused " name ": " code))
        (.flush sys/stdout)))
    (let [names (vec (filter #(and (seq %) (not (.startswith % "#"))) (.splitlines (.read_text mac/manifest))))
          _ (when-not (contains? (set names) check) (mac/fail (str "FULL-MANIFEST no longer lists " check)))
          original (.read_text (.joinpath u/root check))]
      (doseq [[label edits code] mutants]
        (let [text (reduce (fn [text [old new]]
                             (when (not= 1 (.count text old)) (mac/fail (str "cannot construct the " label " negative control")))
                             (.replace text old new))
                           original edits)
              mutant (.joinpath output label)
              _ (.mkdir mutant ** :mode 0700)
              _ (.write_text (.joinpath mutant "full-unity.kotoba")
                             (apply str (for [name names] (str (if (= name check) text (.read_text (.joinpath u/root name))) "\n"))))
              mutant-compiler (sb/build compiler packager mutant "full-unity" (.read_text (.joinpath mutant "full-unity.kotoba")))
              _ (when (u/deq (mac/pin mutant-compiler) (mac/pin compiler))
                  (mac/fail (str "mutant compiler is identical to the compiler under test: " label)))
              [status out] (sb/check-source mutant-compiler mutant "corpus" (.read_text corpus))]
          (when (or (zero? status) (not (.__contains__ out code)))
            (mac/fail (str label " mutant: expected the corpus refused with " code ", got exit " status ": " (pr-str (subs out (max 0 (- (count out) 300)))))))
          (println (str label " (mutant compiler): corpus refused with " code))
          (.flush sys/stdout))))
    (let [public (.joinpath output "public")
          _ (.mkdir public ** :mode 0700)
          _ (.write_bytes (.joinpath public "corpus.kotoba") (.read_bytes corpus))
          result (subprocess/run (python/list [(str (.joinpath u/root "bin/amu")) "run" "corpus.kotoba"]) ** :cwd public
                                 :env (python/dict {"PATH" "/usr/bin:/bin" "LANG" "C"}) :capture_output true :timeout 600)]
      (when (or (not (zero? (.-returncode result))) (not (u/deq (.-stdout result) (.encode "0\n"))) (u/nonempty? (.-stderr result)))
        (mac/fail (str "bin/amu run: exit " (.-returncode result) ", stdout " (.-stdout result) ", stderr " (.-stderr result))))
      (println "bin/amu run corpus: 0")
      (println "PASS_NATIVE_KEYWORD_MAP_RECORD_WITH_NEGATIVE_CONTROLS")
      (.flush sys/stdout))))

(defn -main [& args]
  (main (.resolve (pathlib/Path (or (u/opt args "--compiler") (sys/exit "--compiler is required"))) ** :strict true)
        (.resolve (pathlib/Path (or (u/opt args "--output") (sys/exit "--output is required"))))))

(when (some #(or (= % "check-keyword-map-record.cljc") (str/ends-with? % "/check-keyword-map-record.cljc")) sys/argv)
  (apply -main *command-line-args*))
