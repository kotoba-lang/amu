;; Closed static dispatch in the native frontend (JUN-730).
;;
;; lang/guest-grammar.edn, against the native checker as measured at amu 05668c77
;; (every form below was E2003 `unsupported top-level form`, reify E2101):
;;
;; * :closed-multimethod -- (defmulti NAME DISPATCH) with every (defmethod NAME
;;   KEY [params] body ..) of the module is reader sugar, expanded by seed/20-names
;;   before any name is registered, into one module-local
;;   (defn NAME [params] (case (DISPATCH p ..) KEY body .. [:default body]));
;;   DISPATCH an unqualified symbol or a keyword, KEY an integer or keyword, all
;;   parameter vectors identical and plain, no hierarchy / prefer / extension;
;; * :protocol-dispatch / :protocol-extension -- an implementation of a
;;   defprotocol method for a record of the module (inline in defrecord, in
;;   extend-type or in extend-protocol) becomes a private defn whose receiver is
;;   typed [:ref R]; seed/21-check binds a call's receiver to a fresh local and calls
;;   the implementation for its static record type (ADR 0204: no runtime type
;;   test). Another receiver type is E2180;
;; * reify stays a permanent refusal (E2181). An extend-protocol `default`
;;   section is refused E2006 for now: its per-record specialization was cut to
;;   fit the static profile's 786432-entry token table; JUN-737 raised the table
;;   to 1048576, and admitting `default` is separate work.
;;
;; This gate, on Apple Silicon:
;;
;; * builds seed/tests/native-closed-dispatch.kotoba with --compiler (the Mac fixed
;;   point of this tree) and the descriptor's packager and runs it: exit 0; the
;;   surface-equivalence corpus pair (inline defrecord implementation vs
;;   extend-type) builds and answers 7 on both sides;
;; * checks every refusal below at check time with its named code;
;; * Definition CIDs (definition-cids, profile 6): the multimethod sugar prints the
;;   same CIDs as the hand-written case defn and the control differs; the protocol
;;   corpus pair is refused identically on both sides (REFUSED:unbridged-source:
;;   the definition bridge carries no records), so its CID equality is not
;;   observable;
;; * negative controls: one mutant full compiler per load-bearing change, built
;;   from this tree's FULL-MANIFEST with that change removed; each must refuse the
;;   corpus with the old code at the old place, or (`run`) build a corpus that
;;   does not exit 0, or (`reify`) not refuse reify with E2181;
;; * runs the corpus through the public CLI (bin/amu run), which must print 0.
;;
;; Python stages sources and observes processes; every compiler and program is a
;; native Amu-built Mach-O.
;; Ported from check-closed-dispatch.py (Basilisp, JUN-974). Apple Silicon macOS only. The refusal, pair and mutation
;; literals below are generated from the Python original so whitespace-sensitive anchors stay byte-exact.
;; Run: basilisp run -p scripts/seed scripts/seed/check-closed-dispatch.cljc -- --compiler C --output DIR
(ns check-closed-dispatch
  (:require [basilisp.string :as str]
            [gate-util :as u]
            [macos-image :as image]
            [macos-native-lib :as mac]
            [macos-scope-build :as sb])
  (:import pathlib subprocess sys))

(def corpus (.joinpath u/root "seed/tests/native-closed-dispatch.kotoba"))

(def ns-prefix "(ns d (:export [main]))\n")
(def reify-src "(ns d (:export [main]))\n(defprotocol Area (area [this]) (scale [this k]))\n(defrecord Sq [w :i64])\n(defrecord Rect [w :i64 h :i64])\n(extend-type Sq Area (area [this] (* (:w this) (:w this))) (scale [this k] (->Sq (* k (:w this)))))\n(defn main [] :i64 (area (reify Area (area [this] 1) (scale [this k] this))))\n")
(def pair [
 ["protocol-sugar" "(ns d (:export [main]))\n(defprotocol Value (value [this]))\n(defrecord Box [x] Value (value [this] (get this :x)))\n(defn main [] (value (->Box 7)))\n"]
 ["protocol-pure" "(ns d (:export [main]))\n(defprotocol Value (value [this]))\n(defrecord Box [x])\n(extend-type Box Value (value [this] (get this :x)))\n(defn main [] (value (->Box 7)))\n"]
 ["protocol-control" "(ns d (:export [main]))\n(defprotocol Value (value [this]))\n(defrecord Box [x] Value (value [this] (+ (get this :x) 1)))\n(defn main [] (value (->Box 7)))\n"]
])
(def cids [
 ["multimethod-sugar" "(ns d (:export [main]))\n(defn kind [x :i64] :i64 x)\n(defmulti render kind)\n(defmethod render 1 [x :i64] (+ x 10))\n(defmethod render 2 [x :i64] (+ x 20))\n(defmethod render :default [x :i64] 99)\n(defn main [] :i64 (+ (render 2) (render 7)))\n"]
 ["multimethod-pure" "(ns d (:export [main]))\n(defn kind [x :i64] :i64 x)\n(defn render [x :i64] (case (kind x) 1 (+ x 10) 2 (+ x 20) 99))\n(defn main [] :i64 (+ (render 2) (render 7)))\n"]
 ["multimethod-control" "(ns d (:export [main]))\n(defn kind [x :i64] :i64 x)\n(defn render [x :i64] (case (kind x) 1 (+ x 11) 2 (+ x 20) 99))\n(defn main [] :i64 (+ (render 2) (render 7)))\n"]
])
(def mutants [
 ["no-dispatch-expansion" "seed/20-names.kotoba" [["  (nm-run-defs (nm-dp-norm (nm-pure-norm (nm-r6b-norm (nm-intern-nodes M S 1))))))" "  (nm-run-defs (nm-pure-norm (nm-r6b-norm (nm-intern-nodes M S 1)))))"]] "E2003 unsupported top-level form 'defmethod'"]
 ["no-protocol-call" "seed/21-check.kotoba" [["          (ck-pr-head? M n) (ck-pr-call M n fx ctx)   ; JUN-730: a protocol method\n" ""]] "E2101 unknown or unsupported form 'area'"]
 ["no-receiver-local" "seed/21-check.kotoba" [["          (ck-pr-wrap? M n) (ck-ds-walk (ck-pr-wrap M n) S n)   ; JUN-730: a protocol call's receiver is a fresh local\n" ""]] "E2180 no static implementation of protocol method 'area'"]
 ["dispatch-ignores-record" "seed/21-check.kotoba" [["                   (or (zero? blk) (= (nm-sf M (nm-sym-of M (nm-nth M (nm-nth M (nm-nth M d 2) 1) 1)) SF-REC) blk)))" "                   true)"]] "E2104 type mismatch"]
 ["multimethod-drops-default" "seed/20-names.kotoba" [["    (let [M1 (if (zero? prev) M (nm-set-nf M prev NF-NEXT dflt))" "    (let [M1 (if (zero? prev) M (nm-set-nf M prev NF-NEXT 0))"]] "run"]
 ["no-reify-refusal" "seed/21-check.kotoba" [["          (= (nm-sf M s SF-HASH) -3568532113232994950) (ck-err M E-CHECK-REIFY h 0)   ; JUN-730: reify (FNV-1a)\n" ""]] "reify"]
])
(def refusals [
 ["defmethod-without-defmulti" "(defmethod f 1 [x] x)\n(defn main [] :i64 0)" "E2007 closed dispatch: 'f'"]
 ["string-key" "(defmulti f identity)\n(defmethod f \"x\" [x] x)\n(defn main [] :i64 0)" "E2006"]
 ["different-parameters" "(defn k [x] x)\n(defmulti f k)\n(defmethod f 1 [x] x)\n(defmethod f 2 [y] y)\n(defn main [] :i64 (f 1))" "E2006"]
 ["pattern-parameter" "(defn k [x] x)\n(defmulti f k)\n(defmethod f 1 [[a b]] a)\n(defn main [] :i64 0)" "E2006"]
 ["two-defaults" "(defn k [x] x)\n(defmulti f k)\n(defmethod f :default [x] x)\n(defmethod f :default [x] 1)\n(defn main [] :i64 0)" "E2006 malformed closed dispatch form ':default'"]
 ["duplicate-key" "(defn k [x] x)\n(defmulti f k)\n(defmethod f 1 [x] x)\n(defmethod f 1 [x] 2)\n(defn main [] :i64 (f 1))" "E2125"]
 ["fn-literal-dispatch" "(defmulti f (fn [x] x))\n(defmethod f 1 [x] x)\n(defn main [] :i64 0)" "E2006"]
 ["no-defmethod" "(defmulti f :k)\n(defn main [] :i64 0)" "E2006"]
 ["dispatch-options" "(defmulti f :k :default :other)\n(defmethod f 1 [x] x)\n(defn main [] :i64 0)" "E2006"]
 ["duplicate-defmulti" "(defmulti f :k)\n(defmulti f :k)\n(defmethod f 1 [x] x)\n(defn main [] :i64 0)" "E2001"]
 ["defmulti-and-defn" "(defn f [x] x)\n(defmulti f :k)\n(defmethod f 1 [x] x)\n(defn main [] :i64 0)" "E2001"]
 ["empty-method-body" "(defn k [x] x)\n(defmulti f k)\n(defmethod f 1 [x])\n(defn main [] :i64 0)" "E2006"]
 ["extend-undeclared-protocol" "(defprotocol Area (area [this]) (scale [this k]))\n(defrecord Sq [w :i64])\n(defrecord Rect [w :i64 h :i64])\n(extend-type Sq Perimeter (area [this] 1))\n(defn main [] :i64 0)" "E2007 closed dispatch: 'Perimeter'"]
 ["extend-foreign-type" "(defprotocol Area (area [this]) (scale [this k]))\n(defrecord Sq [w :i64])\n(defrecord Rect [w :i64 h :i64])\n(extend-type String Area (area [this] 1) (scale [this k] this))\n(defn main [] :i64 0)" "E2007 closed dispatch: 'String'"]
 ["extend-protocol-foreign-type" "(defprotocol Area (area [this]) (scale [this k]))\n(defrecord Sq [w :i64])\n(defrecord Rect [w :i64 h :i64])\n(extend-protocol Area String (area [this] 1) (scale [this k] this))\n(defn main [] :i64 0)" "E2007 closed dispatch: 'String'"]
 ["extend-protocol-undeclared" "(defprotocol Area (area [this]) (scale [this k]))\n(defrecord Sq [w :i64])\n(defrecord Rect [w :i64 h :i64])\n(extend-protocol Perimeter Sq (area [this] 1))\n(defn main [] :i64 0)" "E2007 closed dispatch: 'Perimeter'"]
 ["defrecord-undeclared-protocol" "(defrecord Sq [w] Area (area [this] 1))\n(defn main [] :i64 0)" "E2007 closed dispatch: 'Area'"]
 ["defrecord-object" "(defprotocol Area (area [this]))\n(defrecord Sq [w] Object (toString [this] 1))\n(defn main [] :i64 0)" "E2007 closed dispatch: 'Object'"]
 ["missing-method" "(defprotocol Area (area [this]) (scale [this k]))\n(defrecord Sq [w :i64])\n(defrecord Rect [w :i64 h :i64])\n(extend-type Sq Area (area [this] 1))\n(defn main [] :i64 0)" "E2006 malformed closed dispatch form 'Area'"]
 ["unknown-method" "(defprotocol Area (area [this]) (scale [this k]))\n(defrecord Sq [w :i64])\n(defrecord Rect [w :i64 h :i64])\n(extend-type Sq Area (area [this] 1) (scale [this k] this) (perim [this] 2))\n(defn main [] :i64 0)" "E2006 malformed closed dispatch form 'perim'"]
 ["wrong-arity" "(defprotocol Area (area [this]) (scale [this k]))\n(defrecord Sq [w :i64])\n(defrecord Rect [w :i64 h :i64])\n(extend-type Sq Area (area [this x] 1) (scale [this k] this))\n(defn main [] :i64 0)" "E2006 malformed closed dispatch form 'area'"]
 ["implemented-twice" "(defprotocol Area (area [this]) (scale [this k]))\n(defrecord Sq [w :i64])\n(defrecord Rect [w :i64 h :i64])\n(extend-type Sq Area (area [this] (* (:w this) (:w this))) (scale [this k] (->Sq (* k (:w this)))))\n(extend-type Sq Area (area [this] 1) (scale [this k] this))\n(defn main [] :i64 0)" "E2006 malformed closed dispatch form 'area'"]
 ["method-twice-in-section" "(defprotocol Area (area [this]) (scale [this k]))\n(defrecord Sq [w :i64])\n(defrecord Rect [w :i64 h :i64])\n(extend-type Sq Area (area [this] 1) (area [this] 2) (scale [this k] this))\n(defn main [] :i64 0)" "E2006 malformed closed dispatch form 'area'"]
 ["typed-receiver" "(defprotocol Area (area [this]) (scale [this k]))\n(defrecord Sq [w :i64])\n(defrecord Rect [w :i64 h :i64])\n(extend-type Sq Area (area [this [:ref :d/Sq]] 1) (scale [this k] this))\n(defn main [] :i64 0)" "E2006 malformed closed dispatch form 'area'"]
 ["method-also-defined" "(defprotocol Area (area [this]) (scale [this k]))\n(defrecord Sq [w :i64])\n(defrecord Rect [w :i64 h :i64])\n(defn area [x] x)\n(defn main [] :i64 0)" "E2001 duplicate definition 'area'"]
 ["method-named-like-a-head" "(defprotocol C (count [this]))\n(defn main [] :i64 0)" "E2006 malformed closed dispatch form 'count'"]
 ["multi-arity-signature" "(defprotocol C (m [this] [this x]))\n(defn main [] :i64 0)" "E2006"]
 ["signature-docstring" "(defprotocol C (m [this] \"doc\"))\n(defn main [] :i64 0)" "E2006 malformed closed dispatch form 'm'"]
 ["extend-protocol-default" "(defprotocol Area (area [this]) (scale [this k]))\n(defrecord Sq [w :i64])\n(defrecord Rect [w :i64 h :i64])\n(extend-protocol Area default (area [this] 1) (scale [this k] this))\n(defn main [] :i64 0)" "E2006 malformed closed dispatch form 'default'"]
 ["receiver-not-a-record" "(defprotocol Area (area [this]) (scale [this k]))\n(defrecord Sq [w :i64])\n(defrecord Rect [w :i64 h :i64])\n(extend-type Sq Area (area [this] (* (:w this) (:w this))) (scale [this k] (->Sq (* k (:w this)))))\n(defn main [] :i64 (area 5))" "E2180 no static implementation of protocol method 'area'"]
 ["record-without-implementation" "(defprotocol Area (area [this]) (scale [this k]))\n(defrecord Sq [w :i64])\n(defrecord Rect [w :i64 h :i64])\n(extend-type Sq Area (area [this] (* (:w this) (:w this))) (scale [this k] (->Sq (* k (:w this)))))\n(defn main [] :i64 (area (->Rect 1 2)))" "E2180 no static implementation of protocol method 'area'"]
 ["no-receiver" "(defprotocol Area (area [this]) (scale [this k]))\n(defrecord Sq [w :i64])\n(defrecord Rect [w :i64 h :i64])\n(extend-type Sq Area (area [this] (* (:w this) (:w this))) (scale [this k] (->Sq (* k (:w this)))))\n(defn main [] :i64 (area))" "E2180"]
 ["reify" "(defprotocol Area (area [this]) (scale [this k]))\n(defrecord Sq [w :i64])\n(defrecord Rect [w :i64 h :i64])\n(extend-type Sq Area (area [this] (* (:w this) (:w this))) (scale [this k] (->Sq (* k (:w this)))))\n(defn main [] :i64 (area (reify Area (area [this] 1) (scale [this k] this))))" "E2181 reify is not admitted"]
 ["reify-empty" "(defn main [] :i64 (let [o (reify)] 0))" "E2181"]
 ["definterface" "(definterface I (m []))\n(defn main [] :i64 0)" "E2003 unsupported top-level form 'definterface'"]
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
        _ (do (println "fixed compiler: corpus exit 0") (.flush sys/stdout))]
    (doseq [name ["protocol-sugar" "protocol-pure"]]
      (let [status (sb/build-run compiler packager fixed name (second (first (filter #(= name (first %)) pair))))]
        (when (not= status 7) (mac/fail (str name ": expected exit 7, got " status)))
        (println (str "fixed compiler: " name " exit 7"))
        (.flush sys/stdout)))
    (let [refusal-dir (.joinpath output "refusals")
          _ (.mkdir refusal-dir ** :mode 0700)]
      (doseq [[name src code] refusals]
        (let [[status out err] (sb/run-source compiler refusal-dir "check" name (str ns-prefix src "\n"))]
          (when (or (zero? status) (not (.__contains__ (str out err) code)))
            (mac/fail (str name ": expected a check-time " code ", got exit " status ": " (tail300 (str out err)))))
          (println (str "refused " name ": " code))
          (.flush sys/stdout))))
    (let [ids (.joinpath output "cids")
          _ (.mkdir ids ** :mode 0700)
          get-src (fn [k] (second (first (filter #(= k (first %)) cids))))
          [sugar pure control] (map (fn [k] (sb/cids compiler ids k (get-src k))) ["multimethod-sugar" "multimethod-pure" "multimethod-control"])]
      (when (or (not= sugar pure) (.__contains__ sugar "REFUSED") (not (.__contains__ sugar "SCANNED\t3/3")))
        (mac/fail (str "multimethod sugar and pure CIDs differ:\n" sugar "\n" pure)))
      (when (= control sugar) (mac/fail "multimethod control has the sugar's CIDs"))
      (println "definition-cids: multimethod sugar = hand-written case defn; control differs")
      (.flush sys/stdout)
      ;; Both protocol examples contain defrecord. Until its generated constructor has an identity, the whole module must
      ;; refuse rather than emit a partial per-definition report; no CID may be produced on stdout.
      (doseq [[name src] pair]
        (let [[status out err] (sb/run-source compiler ids "definition-cids" name src)]
          (when (or (not= status 66) (seq out) (not (.startswith err "DSB:BRIDGE:3:")))
            (mac/fail (str name ": expected atomic defrecord refusal, got exit " status ": " (tail300 (str out err)))))))
      (println "definition-cids: protocol pair refused atomically (record constructors unbridged)")
      (.flush sys/stdout))
    (doseq [[label path edits expected] mutants]
      (let [mutant (sb/mutant-compiler compiler packager output label path edits)
            mdir (.joinpath output label)]
        (case expected
          "reify"
          (let [[status out err] (sb/run-source mutant mdir "check" "reify" reify-src)
                text (str out err)]
            (when (or (zero? status) (.__contains__ text "E2181"))
              (mac/fail (str label " mutant: reify is still refused E2181 (or admitted): " (tail300 text))))
            (println (str label " (mutant compiler): reify is not refused E2181 (" (let [s (.strip text)] (subs s (max 0 (- (count s) 120)))) ")")))
          "run"
          (let [[status out err] (sb/run-source mutant mdir "check" "corpus" (.read_text corpus))]
            (when (not (zero? status))
              (mac/fail (str label " mutant: expected the corpus admitted, got exit " status ": " (tail300 (str out err)))))
            (let [run-status (sb/build-run mutant packager mdir "corpus-run" (.read_text corpus))]
              (when (zero? run-status) (mac/fail (str label " mutant: the corpus still exits 0")))
              (println (str label " (mutant compiler): corpus admitted, built and exits " run-status))))
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
      (println "PASS_NATIVE_CLOSED_DISPATCH_WITH_NEGATIVE_CONTROLS")
      (.flush sys/stdout))))

(defn -main [& args]
  (main (.resolve (pathlib/Path (or (u/opt args "--compiler") (sys/exit "--compiler is required"))) ** :strict true)
        (.resolve (pathlib/Path (or (u/opt args "--output") (sys/exit "--output is required"))))))

(when (some #(or (= % "check-closed-dispatch.cljc") (str/ends-with? % "/check-closed-dispatch.cljc")) sys/argv)
  (apply -main *command-line-args*))
