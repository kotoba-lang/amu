;; Keyword map literals have structural identity; nil is an [:option T] field's none (JUN-733 slice 1).
;;
;; Owner decision 2026-11-01 (Linear JUN-733): native Amu follows the amu ladder's
;; row floors (docs/language-ladder.edn :absence, :absent-field-from-assoc,
;; :row-unification, :literal-typing; kotoba-lang lang/guest-grammar.edn
;; :map-literal :value-types :keyword-keys). In seed/21-check:
;;
;; * D1 structural identity -- a keyword map literal whose keys and value types fit
;;   exactly one declared record (defrecord, ns :schemas or an inline [:record ..]
;;   schema) is that record (ck-kwrec-decl); a literal checked where a record is
;;   expected -- a call argument, a record field, an assoc value, a typed slot --
;;   with exactly that record's keys is that record (ck-expr-to / ck-kwrec-in), so
;;   two declared records of one shape are each reached by their own slot. Such a
;;   literal builds the record in the record's field order;
;; * D4 nil -- nil at a keyword key of a map literal, an assoc pair or a
;;   record-new / constructor argument is the none of an [:option T] field; T is
;;   the declared field's, else the one type the module spells at that key
;;   (ck-kopt-scan: literals, constructors, calls of defns with a declared result,
;;   declared [:option T] fields of that key); a non-nil value T at such a key is
;;   its some (30-lower lw-some: pair(x, 0)). nil with no T is E2182, two Ts E2128.
;;
;; This gate, on Apple Silicon:
;;
;; * builds seed/tests/native-record-identity-option.kotoba with --compiler (the
;;   Mac fixed point of this tree) and the descriptor's packager and runs it:
;;   exit 0;
;; * checks that each refusal below is refused at check time with its named code;
;; * definition-cids: a literal and the hand-written constructor in a [:ref P]
;;   slot are refused identically (unbridged-source: the definition bridge carries
;;   no records), so CID equality is not observable for these forms;
;; * negative controls: one mutant full compiler per change, built from this
;;   tree's FULL-MANIFEST with that change removed; the checker mutants must refuse
;;   the corpus with the old code, the lowering mutant (no some) must build a
;;   corpus that does not exit 0;
;; * runs the corpus through the public CLI (bin/amu run), which must print 0.
;;
;; Python stages sources and observes processes; every compiler and program is a
;; native Amu-built Mach-O.
;; Ported from check-record-identity-option.py (Basilisp, JUN-974). Apple Silicon macOS only. The mutation, refusal and
;; CID literals below are generated from the Python original so whitespace-sensitive anchors stay byte-exact.
;; Run: basilisp run -p scripts/seed scripts/seed/check-record-identity-option.cljc -- --compiler C --output DIR
(ns check-record-identity-option
  (:require [basilisp.string :as str]
            [gate-util :as u]
            [macos-image :as image]
            [macos-native-lib :as mac]
            [macos-scope-build :as sb])
  (:import pathlib subprocess sys))

(def corpus (.joinpath u/root "seed/tests/native-record-identity-option.kotoba"))

;; (label, file, [[old new] ...], expected: a refusal code string, or "run" (the built corpus must not exit 0))
(def ns-prefix "(ns d (:export [main]))\n(defrecord P [x :i64 y :i64])\n(defn sum-p [p [:ref :d/P]] :i64 (+ (:x p) (:y p)))\n")
(def mutants [
 ["no-structural-identity" "seed/21-check.kotoba" [["  (let [d (ck-kwrec-decl M n)\n" "  (let [d 0\n"]] "E2121"]
 ["no-expected-record" "seed/21-check.kotoba" [["      (ck-kwrec-in M c fx b)\n      (ck-expr M c fx 0))))" "      (ck-expr M c fx 0)\n      (ck-expr M c fx 0))))"]] "E2104"]
 ["no-nil-option" "seed/21-check.kotoba" [["(defn- ck-nil? [M :vector-i64 v :i64] :bool (and (nm-r6b-nil? M v) (neg? (nm-local-slot M (nm-sym-of M v)))))" "(defn- ck-nil? [M :vector-i64 v :i64] :bool false)"]] "E2102 unknown symbol 'nil'"]
 ["no-module-option-key" "seed/21-check.kotoba" [["        M3 (ck-kopt-scan (ck-hints-apply (ck-sigs M2 1)))" "        M3 (ck-hints-apply (ck-sigs M2 1))"]] "E2182"]
 ["no-some-lowering" "seed/30-lower.kotoba" [["  (if (or (zero? vty) (= fty vty)) M (-> M" "  (if true M (-> M"]] "run"]
])
(def refusals [
 ["nil-no-type" "(defn main [] :i64 (let [a {:zz nil}] 0))" "E2182"]
 ["nil-two-types" "(defn main [] :i64 (let [a {:zz nil} b {:zz 1} c {:zz \"s\"}] 0))" "E2128"]
 ["value-not-the-key-type" "(defn main [] :i64 (let [a {:q nil} b {:q 1} s \"x\" c {:q s}] 0))" "E2104"]
 ["nil-into-plain-field" "(defn main [] :i64 (:x (assoc (->P 1 2) :x nil)))" "E2104"]
 ["nil-into-plain-constructor-field" "(defn main [] :i64 (:x (->P nil 2)))" "E2102"]
 ["nil-as-a-value" "(defn main [] :i64 (let [x nil] 0))" "E2102"]
 ["literal-extra-key" "(defn main [] :i64 (sum-p {:x 1 :z 2}))" "E2104"]
 ["literal-field-type" "(defn main [] :i64 (sum-p {:x 1 :y \"s\"}))" "E2104"]
 ["literal-missing-key" "(defn main [] :i64 (sum-p {:x 1}))" "E2104"]
 ["two-records-one-shape-let-bound" "(defrecord A [x :i64 y :i64])\n(defn main [] :i64 (let [m {:x 1 :y 2}] (sum-p m)))" "E2104"]
])
(def cids [
 ["literal" "(ns a (:export [main]))\n(defrecord P [x :i64 y :i64])\n(defn f [p [:ref :a/P]] :i64 (:x p))\n(defn main [] :i64 (f {:x 1 :y 2}))\n"]
 ["constructor" "(ns a (:export [main]))\n(defrecord P [x :i64 y :i64])\n(defn f [p [:ref :a/P]] :i64 (:x p))\n(defn main [] :i64 (f (->P 1 2)))\n"]
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
    (let [ids (.joinpath output "cids")
          _ (.mkdir ids ** :mode 0700)
          reports (into {} (for [[name src] cids]
                             ;; Since the checked-source bridge (JUN-358, #1788/#1789) a source that holds a form with no
                             ;; bridge, such as a record literal or constructor, refuses atomically (exit 66, stderr
                             ;; DSB:BRIDGE:3:<offset>) instead of reporting each definition REFUSED:unbridged-source.
                             (let [[status out err] (sb/run-source compiler ids "definition-cids" name src)]
                               (when (or (not= status 66) (seq out) (not (.startswith err "DSB:BRIDGE:3:")))
                                 (mac/fail (str "definition-cids " name ": expected the atomic DSB:BRIDGE:3 refusal, got exit " status ": " (tail300 (str out err)))))
                               [name err])))]
      (when (not= (take 3 (str/split (get reports "literal") #":")) (take 3 (str/split (get reports "constructor") #":")))
        (mac/fail "definition-cids: the literal and constructor refusals differ in kind"))
      (println "definition-cids: literal and constructor both refuse atomically (DSB:BRIDGE:3; records have no bridge)")
      (.flush sys/stdout))
    (doseq [[label path edits expected] mutants]
      (let [mutant (sb/mutant-compiler compiler packager output label path edits)
            mdir (.joinpath output label)
            [status out err] (sb/run-source mutant mdir "check" "corpus" (.read_text corpus))]
        (if (= expected "run")
          (do (when (not (zero? status))
                (mac/fail (str label " mutant: expected the corpus admitted, got exit " status ": " (tail300 (str out err)))))
              (let [built (sb/build mutant packager mdir "corpus-run" corpus)
                    run (subprocess/run (python/list [(str built)]) ** :cwd mdir :capture_output true :timeout 60
                                        :env (python/dict {"PATH" "/usr/bin:/bin" "LANG" "C"}))]
                (when (zero? (.-returncode run)) (mac/fail (str label " mutant: the corpus still exits 0")))
                (println (str label " (mutant compiler): corpus admitted, built and exits " (.-returncode run)))))
          (do (when (or (zero? status) (not (.__contains__ (str out err) expected)))
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
      (println "PASS_NATIVE_RECORD_IDENTITY_OPTION_WITH_NEGATIVE_CONTROLS")
      (.flush sys/stdout))))

(defn -main [& args]
  (main (.resolve (pathlib/Path (or (u/opt args "--compiler") (sys/exit "--compiler is required"))) ** :strict true)
        (.resolve (pathlib/Path (or (u/opt args "--output") (sys/exit "--output is required"))))))

(when (some #(or (= % "check-record-identity-option.cljc") (str/ends-with? % "/check-record-identity-option.cljc")) sys/argv)
  (apply -main *command-line-args*))
