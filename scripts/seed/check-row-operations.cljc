;; Row operations on native records (JUN-733 slice 2).
;;
;; Owner decision 2026-11-01 (Linear JUN-733): native Amu follows the amu ladder's
;; row floors (docs/language-ladder.edn :row-operations, :empty-map-literal,
;; :record-field-update, :merge-literal-reads-its-row). In seed/21-check every
;; result is a record type of the shape the operation gives, by structural
;; identity (ck-shape-type): the one declared record of exactly that shape, else
;; the anonymous record of that shape (its keys in printed-text order, ck-krank):
;;
;; * (assoc r :k v) with :k not a field of r extends the row (ck-assoc-ext; the
;;   value is typed as in a literal: nil / some at a key the module writes nil at);
;; * (assoc {} :k v) and (merge {} m): {} is the empty record there (ck-empty-rec);
;;   anywhere else it stays E2133;
;; * (dissoc r :k ..) and (select-keys r [:k ..]) shrink the row (ck-shrink; a key
;;   the record does not have is ignored, as clojure.core does);
;; * (merge a b ..) is the record with a's fields and b's, b's value and type
;;   winning (ck-merge), folded left;
;; * (update m :k f x ..) is reader sugar: (let [g m] (assoc g :k (f (:k g) x ..))),
;;   a fn literal f applied as a let (ck-rowop-ds).
;;
;; 30-lower builds each result field from the source record's field of the same key
;; (lw-assoc / lw-rebuild / lw-merge, lw-src).
;;
;; This gate, on Apple Silicon:
;;
;; * builds seed/tests/native-row-operations.kotoba with --compiler (the Mac fixed
;;   point of this tree) and the descriptor's packager and runs it: exit 0;
;; * checks that each refusal below is refused at check time with its named code;
;; * definition-cids: both update forms are refused atomically because generated
;;   record constructors are unbridged, so CID equality is not observable;
;; * negative controls: one mutant full compiler per change, built from this
;;   tree's FULL-MANIFEST with that change removed; the checker mutants must refuse
;;   the corpus with the old code, the lowering mutants must build a corpus that
;;   does not exit 0;
;; * runs the corpus through the public CLI (bin/amu run), which must print 0.
;;
;; Python stages sources and observes processes; every compiler and program is a
;; native Amu-built Mach-O.
;; Ported from check-row-operations.py (Basilisp, JUN-974). Apple Silicon macOS only. The mutation, refusal and CID
;; literals below are generated from the Python original so whitespace-sensitive anchors stay byte-exact.
;; Run: basilisp run -p scripts/seed scripts/seed/check-row-operations.cljc -- --compiler C --output DIR
(ns check-row-operations
  (:require [basilisp.string :as str]
            [gate-util :as u]
            [macos-image :as image]
            [macos-native-lib :as mac]
            [macos-scope-build :as sb])
  (:import pathlib subprocess sys))

(def corpus (.joinpath u/root "seed/tests/native-row-operations.kotoba"))

;; (label, file, [[old new] ...], expected: a refusal code string, or "run" (the built corpus must not exit 0))
;; (label, file, [[old new] ...], expected: a refusal code string, or "run" (the built corpus must not exit 0))
(def ns-prefix "(ns d (:export [main]))\n(defrecord P [x :i64 y :i64])\n")
(def mutants [
 ["no-row-extension" "seed/21-check.kotoba" [["          (ck-assoc-ext? M r kw) (ck-assoc-ext M n fx)   ; JUN-733: a key r does not have extends the row\n" ""]] "E2127"]
 ["no-empty-record" "seed/21-check.kotoba" [["  (if (and (= (nm-kind M r) ND-MAP) (zero? (nm-count M r))) (ck-kwrec M r fx) M))" "  M)"]] "E2133"]
 ["no-record-dissoc" "seed/21-check.kotoba" [["        (= hd HD-DISSOC) (ck-dissoc M n fx ctx)   ; JUN-733: a record's dissoc shrinks the row\n" ""]] "E2104"]
 ["no-select-keys" "seed/21-check.kotoba" [["          (= (nm-sf M s SF-HASH) 5227267513227667492) (ck-selkeys M n fx)   ; JUN-733: select-keys (FNV-1a)\n" ""]] "E2101 unknown or unsupported form 'select-keys'"]
 ["no-merge" "seed/21-check.kotoba" [["          (= (nm-sf M s SF-HASH) 5641795132494944871) (ck-merge M n fx)   ; JUN-733: merge (FNV-1a)\n" ""]] "E2101 unknown or unsupported form 'merge'"]
 ["no-variadic-merge" "seed/21-check.kotoba" [["(>= (nm-count M n) 4)) 1   ; merge" "(>= (nm-count M n) 4)) 0   ; merge"]] "E2103 wrong number of arguments to 'merge'"]
 ["no-update-sugar" "seed/21-check.kotoba" [["(ck-fn-form? M f)))) 2   ; update" "(ck-fn-form? M f)))) 0   ; update"]] "E2139"]
 ["assoc-copies-by-position" "seed/30-lower.kotoba" [["(lw-seconds (+ t i) (lw-src M (:a q) (:b q) i))" "(lw-seconds (+ t i) i)"]] "run"]
 ["rebuild-copies-by-position" "seed/30-lower.kotoba" [["(recur (-> M3 (lw-emit OP-LGET (+ t j) s) (lw-seconds (+ t j) (lw-src M3 a b j))) (inc j))" "(recur (-> M3 (lw-emit OP-LGET (+ t j) s) (lw-seconds (+ t j) j)) (inc j))"]] "run"]
 ["merge-ignores-b" "seed/30-lower.kotoba" [["                 (recur (if (neg? ic)\n" "                 (recur (if true\n"]] "run"]
])
(def refusals [
 ["empty-literal-alone" "(defn main [] :i64 (let [m {}] 0))" "E2133"]
 ["dissoc-then-read" "(defn main [] :i64 (:a (dissoc {:a 1 :b 2} :a)))" "E2127"]
 ["dissoc-computed-key" "(defn main [] :i64 (let [k :a m (dissoc {:a 1} k)] 0))" "E2127"]
 ["select-keys-not-a-vector" "(defn main [] :i64 (let [m (select-keys {:a 1} :a)] 0))" "E2103"]
 ["select-keys-of-a-number" "(defn main [] :i64 (let [m (select-keys 5 [:a])] 0))" "E2104"]
 ["merge-a-number" "(defn main [] :i64 (let [m (merge 1 {:a 1})] 0))" "E2104"]
 ["merge-a-typed-map" "(defn main [] :i64 (let [m (merge {:a 1} (typed-map-new [:map :keyword :i64] :b 2))] 0))" "E2104"]
 ["update-answers-another-type" "(defn main [] :i64 (:a (update {:a 1} :a (fn [x] \"s\"))))" "E2104"]
 ["update-absent-key" "(defn main [] :i64 (:z (update {:a 1} :z inc)))" "E2127"]
 ["update-fn-arity" "(defn main [] :i64 (let [m (update {:a 1} :a (fn [x y] x))] 0))" "E2103"]
 ["update-a-number" "(defn main [] :i64 (let [m (update 5 :a inc)] 0))" "E2104"]
 ["assoc-new-key-nil-without-type" "(defn main [] :i64 (let [m (assoc {:a 1} :b nil)] 0))" "E2182"]
 ["assoc-new-key-fn-value" "(defn main [] :i64 (let [m (assoc {:a 1} :b (fn [x] x))] 0))" "E2128"]
 ["assoc-past-32-fields" "(defn main [] :i64 (let [m (assoc {:k0 0 :k1 1 :k2 2 :k3 3 :k4 4 :k5 5 :k6 6 :k7 7 :k8 8 :k9 9 :k10 10 :k11 11 :k12 12 :k13 13 :k14 14 :k15 15 :k16 16 :k17 17 :k18 18 :k19 19 :k20 20 :k21 21 :k22 22 :k23 23 :k24 24 :k25 25 :k26 26 :k27 27 :k28 28 :k29 29 :k30 30 :k31 31} :z 1)] 0))" "E2128"]
])
(def cids [
 ["update-sugar" "(ns a (:export [main]))\n(defrecord P [x :i64 y :i64])\n(defn f [p [:ref :a/P]] [:ref :a/P] (update p :x inc))\n(defn main [] :i64 (:x (f (->P 1 2))))\n"]
 ["update-pure" "(ns a (:export [main]))\n(defrecord P [x :i64 y :i64])\n(defn f [p [:ref :a/P]] [:ref :a/P] (let [g p] (assoc g :x (inc (:x g)))))\n(defn main [] :i64 (:x (f (->P 1 2))))\n"]
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
          _ (.mkdir ids ** :mode 0700)]
      (doseq [[name src] cids]
        (let [[status out err] (sb/run-source compiler ids "definition-cids" name src)]
          (when (or (not= status 66) (seq out) (not (.startswith err "DSB:BRIDGE:3:")))
            (mac/fail (str "definition-cids " name ": expected atomic defrecord refusal, got exit " status ": " (tail300 (str out err)))))))
      (println "definition-cids: both update forms refused atomically (record constructors unbridged)")
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
      (println "PASS_NATIVE_ROW_OPERATIONS_WITH_NEGATIVE_CONTROLS")
      (.flush sys/stdout))))

(defn -main [& args]
  (main (.resolve (pathlib/Path (or (u/opt args "--compiler") (sys/exit "--compiler is required"))) ** :strict true)
        (.resolve (pathlib/Path (or (u/opt args "--output") (sys/exit "--output is required"))))))

(when (some #(or (= % "check-row-operations.cljc") (str/ends-with? % "/check-row-operations.cljc")) sys/argv)
  (apply -main *command-line-args*))
