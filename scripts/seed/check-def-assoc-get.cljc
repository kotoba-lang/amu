;; Small native admissions in seed/21-check and seed/30-lower (JUN-734).
;;
;; lang/guest-grammar.edn, against the native checker as measured at amu c2186d76:
;; * D5 :def :value :literal -- a def of a vector / map literal with f64 or boolean values, or of map-literal items,
;;   was E2124. It now takes R6F's computed-def route (a private nullary defn whose body is the literal, typed as in a
;;   body); R0's integer vectors and R6B's opaque constant maps are unchanged;
;; * D6 -- the variadic (assoc r k1 v1 k2 v2 ..) was E2103. It is now reader sugar for
;;   (assoc (assoc r k1 v1) k2 v2 ..) on records, typed maps and documents; an odd key/value count stays E2103;
;; * D10 -- (get m k) on a typed map was E2104; it is now [:option V] (:def :value :quoted-not-widened: lookup is get
;;   on the typed map, [:option V], or V with a default), lowered as typed-map-get. (:k m d) on a typed map was E2103;
;;   it is now (get m :k d). On a record a default is refused E2103 (a field is never absent). A defrecord's bare name
;;   as a parameter type ([s S]) silently read S as a second parameter; it is now refused E2105 (a type is a keyword
;;   or a type vector; the record type is [:ref :<ns>/S]).
;; This gate, on Apple Silicon:
;; * builds seed/tests/native-def-assoc-get.kotoba with --compiler (the Mac fixed point of this tree) and the
;;   descriptor's packager and runs it: exit 0;
;; * checks that each refusal below is refused at check time with its named code;
;; * negative controls: one mutant full compiler per change, built from this tree's FULL-MANIFEST with that change
;;   removed: the four checker mutants must refuse the corpus with the old code at the old place, the lowering mutant
;;   (21-check admits (get m k) but 30-lower reads it as a record field) must build a corpus that does not exit 0, and
;;   the mutant without the bare-record-name refusal must not refuse [s S] with E2105;
;; * runs the corpus through the public CLI (bin/amu run), which must print 0.
;; Definition CIDs are not observable for these forms: the definition bridge refuses computed defs (DSB:BRIDGE, as for
;; (def x (+ 1 2)) before this change) and unbridged record / typed-map sources, on both the sugar and the pure side.
;; This stages sources and observes processes; every compiler and program is a native Amu-built Mach-O.
;; Ported from check-def-assoc-get.py (Basilisp, JUN-974). Apple Silicon macOS only. The mutation and refusal literals
;; below are generated from the Python original so whitespace-sensitive anchors stay byte-exact.
;; Run: basilisp run -p scripts/seed scripts/seed/check-def-assoc-get.cljc -- --compiler C --output DIR
(ns check-def-assoc-get
  (:require [basilisp.string :as str]
            [gate-util :as u]
            [macos-image :as image]
            [macos-native-lib :as mac]
            [macos-scope-build :as sb])
  (:import pathlib subprocess sys))

(def corpus (.joinpath u/root "seed/tests/native-def-assoc-get.kotoba"))

;; (label, file, [[old new] ...], expected: a refusal code string, "run" (built corpus must not exit 0) or "bare")
(def ns-prefix "(ns d (:export [main]))\n(defrecord S [a :i64 b :i64])\n")
(def bare "(ns d (:export [main]))\n(defrecord S [a :i64 b :i64])\n(defn f [s S] :i64 (:a s))\n(defn main [] :i64 (f (->S 1 2)))\n")
(def mutants [
 ["no-def-literal" "seed/21-check.kotoba" [["             (and (= k ND-VEC) (zero? (ck-def-vec M v)))\n             (and (= k ND-MAP) (not (ck-r6b-const? M v)))))))" "             false))))"]] "E2124 def value must be an integer, string, keyword or vector literal: 'cfg'"]
 ["no-variadic-assoc" "seed/21-check.kotoba" [["          (ck-vassoc? M n) (ck-ds-walk (ck-vassoc M n) S n)   ; JUN-734: variadic assoc\n" ""]] "E2103 wrong number of arguments to 'assoc'"]
 ["no-get-option" "seed/21-check.kotoba" [["          (= (ck-tcon M1 (ck-ty M1)) TC-MAP) (ck-gget2 M1 n fx)   ; JUN-734\n" ""]] "E2104 type mismatch in 'get'"]
 ["no-kw-default" "seed/21-check.kotoba" [["          (= (nm-count M n) 3) (ck-kwget3 M n fx)   ; JUN-734\n" ""]] "E2103 wrong number of arguments to ':q'"]
 ["no-get-option-lowering" "seed/30-lower.kotoba" [["                   (= (lw-ct M (lw-nf M a NF-TYPE) CT-CTOR) TC-MAP)   ; JUN-734: (get m k) on a map -> [:option V]\n                   (lw-mget M a (lw-nf M h NF-TYPE) (lw-md M (lw-nf M a NF-TYPE)) t)\n" ""]] "run"]
 ["no-bare-record-refusal" "seed/21-check.kotoba" [["          (pos? (nm-sf M (nm-sym-of M c) SF-REC)) (ck-err M E-CHECK-TYPENAME c 0)\n" ""]] "bare"]
])
(def refusals [
 ["def-loop" "(def x [(loop [i 0] (if (> i 3) i (recur (+ i 1))))])\n(defn main [] :i64 0)" "E2124"]
 ["def-fn-literal" "(def x {:a (fn [y] y)})\n(defn main [] :i64 0)" "E2124"]
 ["def-mixed-vector" "(def x [1 :a])\n(defn main [] :i64 0)" "E2116"]
 ["def-unknown-symbol" "(def x {:a 0.5 :b nope})\n(defn main [] :i64 0)" "E2102"]
 ["assoc-odd" "(defn main [] :i64 (let [s (->S 1 2)] (:a (assoc s :a 1 :b))))" "E2103"]
 ["assoc-absent-field" "(defn main [] :i64 (let [s (->S 1 2)] (:z (assoc s :a 1 :b 2))))" "E2127"]
 ["assoc-field-type" "(defn main [] :i64 (let [s (->S 1 2)] (:a (assoc s :a 1 :b \"x\"))))" "E2104"]
 ["assoc-map-value-type" "(defn main [] :i64 (let [m (typed-map-new [:map :keyword :i64] :a 1)] (get (assoc m :a 1 :b true) :a 0)))" "E2104"]
 ["get-key-type" "(defn main [] :i64 (let [m (typed-map-new [:map :keyword :i64] :a 1)] (option-or (get m \"a\") 0)))" "E2104"]
 ["get-is-option" "(defn main [] :i64 (let [m (typed-map-new [:map :keyword :i64] :a 1)] (get m :a)))" "E2121"]
 ["kw-default-type" "(defn main [] :i64 (let [m (typed-map-new [:map :keyword :i64] :a 1)] (:a m \"d\")))" "E2104"]
 ["kw-default-record-type" "(defn main [] :i64 (let [s (->S 1 2)] (:a s \"x\")))" "E2104"]
 ["kw-default-vector" "(defn main [] :i64 (let [v [1 2]] (:a v 0)))" "E2103"]
 ["bare-record-type" "(defn f [s S] :i64 (:a s))\n(defn main [] :i64 (f (->S 1 2)))" "E2105 unsupported type 'S'"]
 ["bare-record-param" "(defn f [S] :i64 0)\n(defn main [] :i64 (f 1))" "E2105 unsupported type 'S'"]
])

(defn tail300 [s] (pr-str (subs s (max 0 (- (count s) 300)))))

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
      (let [[status out err] (sb/run-source compiler refusal-dir "check" name (str ns-prefix src "\n"))]
        (when (or (zero? status) (not (.__contains__ (str out err) code)))
          (mac/fail (str name ": expected a check-time " code ", got exit " status ": " (tail300 (str out err)))))
        (println (str "refused " name ": " code))
        (.flush sys/stdout)))
    (doseq [[label path edits expected] mutants]
      (let [mutant (sb/mutant-compiler compiler packager output label path edits)
            mdir (.joinpath output label)]
        (case expected
          "bare"
          (let [[status out err] (sb/run-source mutant mdir "check" "bare" bare)
                text (str out err)]
            (when (and (not (zero? status)) (.__contains__ text "E2105"))
              (mac/fail (str label " mutant: [s S] is still refused with E2105: " (tail300 text))))
            (println (str label " (mutant compiler): [s S] is not refused E2105 (exit " status ": "
                          (let [s (.strip text)] (subs s (max 0 (- (count s) 120)))) ")")))
          "run"
          (let [[status out err] (sb/run-source mutant mdir "check" "corpus" (.read_text corpus))]
            (when (not (zero? status))
              (mac/fail (str label " mutant: expected the corpus admitted, got exit " status ": " (tail300 (str out err)))))
            (let [built (sb/build mutant packager mdir "corpus-run" corpus)
                  run (subprocess/run (python/list [(str built)]) ** :cwd mdir :capture_output true :timeout 60
                                      :env (python/dict {"PATH" "/usr/bin:/bin" "LANG" "C"}))]
              (when (zero? (.-returncode run)) (mac/fail (str label " mutant: the corpus still exits 0")))
              (println (str label " (mutant compiler): corpus admitted, built and exits " (.-returncode run)))))
          (let [[status out err] (sb/run-source mutant mdir "check" "corpus" (.read_text corpus))]
            (when (or (zero? status) (not (.__contains__ (str out err) expected)))
              (mac/fail (str label " mutant: expected the corpus refused with " expected ", got exit " status ": " (tail300 (str out err)))))
            (println (str label " (mutant compiler): corpus refused with " expected))))
        (.flush sys/stdout)))
    (let [public (.joinpath output "public")
          _ (.mkdir public ** :mode 0700)
          _ (.write_bytes (.joinpath public "corpus.kotoba") (.read_bytes corpus))
          result (subprocess/run (python/list [(str (.joinpath u/root "bin/amu")) "run" "corpus.kotoba"]) ** :cwd public
                                 :env (python/dict {"PATH" "/usr/bin:/bin" "LANG" "C"}) :capture_output true :timeout 600)]
      (when (or (not (zero? (.-returncode result))) (not (u/deq (.-stdout result) (.encode "0\n"))) (u/nonempty? (.-stderr result)))
        (mac/fail (str "bin/amu run: exit " (.-returncode result) ", stdout " (.-stdout result) ", stderr " (.-stderr result))))
      (println "bin/amu run corpus: 0")
      (println "PASS_NATIVE_DEF_ASSOC_GET_WITH_NEGATIVE_CONTROLS")
      (.flush sys/stdout))))

(defn -main [& args]
  (main (.resolve (pathlib/Path (or (u/opt args "--compiler") (sys/exit "--compiler is required"))) ** :strict true)
        (.resolve (pathlib/Path (or (u/opt args "--output") (sys/exit "--output is required"))))))

(when (some #(or (= % "check-def-assoc-get.cljc") (str/ends-with? % "/check-def-assoc-get.cljc")) sys/argv)
  (apply -main *command-line-args*))
