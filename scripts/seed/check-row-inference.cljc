;; Row inference for unannotated parameters; get with a default on a record (JUN-733 slice 3).
;;
;; Owner decision 2026-11-01 (Linear JUN-733): native Amu follows the amu ladder's row floors (docs/language-ladder.edn
;; :row-records, :row-get-and-match, :options-map-argument). In seed/21-check:
;; * an unannotated parameter used as a record -- (:k p), get, an assoc / dissoc / merge / select-keys operand, a :keys
;;   destructuring, or a record passed by a caller -- asks the R6C refinement for a ROW (the pseudo type TY-REC-BASE,
;;   ck-refine-note / ck-row-note); the re-run makes its function a ROW GENERIC (FN2-FLAGS bits 0 and 5): never checked
;;   or lowered itself, it exists only as its specializations, one per tuple of record types a call passes
;;   (ck-row-call / ck-row-spec: a clone of the defn form typed at them, FN2-FLAGS bit 6);
;; * (get m :k d) and (:k m d) on a record read a field it has as (:k m) (d of the field's type), an [:option T] field
;;   as (option-or (:k m) d), and a key the record does not have as d (ck-rget-d).
;; Refused by name: a non-record argument to a row parameter (E2104), a field the record lacks read without a default
;; (E2127), an explicitly exported row function (E2183), a row function as a value (E2134), a self-recursive row
;; function without a declared result (E2126), a computed key on a row (E2104).
;; This gate, on Apple Silicon:
;; * builds seed/tests/native-row-inference.kotoba with --compiler (the Mac fixed point of this tree) and the
;;   descriptor's packager and runs it: exit 0;
;; * checks that each refusal below is refused at check time with its named code;
;; * definition-cids: both the annotated and row modules are refused atomically (exit 66) because their generated
;;   record constructor is not bridged; no CID equivalence is observable for these forms;
;; * negative controls: one mutant full compiler per change, built from this tree's FULL-MANIFEST with that change
;;   removed, must refuse the corpus with the old code;
;; * runs the corpus through the public CLI (bin/amu run), which must print 0.
;; This stages sources and observes processes; every compiler and program is a native Amu-built Mach-O.
;; Ported from check-row-inference.py (Basilisp, JUN-974). Apple Silicon macOS only. The mutation and refusal literals
;; below are generated from the Python original so whitespace-sensitive anchors stay byte-exact.
;; Run: basilisp run -p scripts/seed scripts/seed/check-row-inference.cljc -- --compiler C --output DIR
(ns check-row-inference
  (:require [basilisp.string :as str]
            [gate-util :as u]
            [macos-image :as image]
            [macos-native-lib :as mac]
            [macos-scope-build :as sb])
  (:import pathlib subprocess sys))

(def corpus (.joinpath u/root "seed/tests/native-row-inference.kotoba"))

;; (label, file, [[old new] ...], expected: a refusal code string, or "run" (the built corpus must not exit 0))
(def ns-prefix "(ns d (:export [main]))\n(defrecord P [x :i64 y :i64])\n")
(def mutants [
 ["no-row-refinement" "seed/21-check.kotoba" [["        (= t TY-REC-BASE) true   ; JUN-733: a row (ck-row-gen?)\n" ""] ["                        (= t TY-REC-BASE) (ck-f2-set (ck-hint-set M f k t tn) f FN2-FLAGS (bit-or (ck-f2 M f FN2-FLAGS) 33))   ; JUN-733\n" ""]] "E2104"]
 ["no-row-specialization" "seed/21-check.kotoba" [["          (and (= (ck-callable M fi) 1) (ck-row-gen? M (ck-pick M fi (dec (nm-count M n))))) (ck-row-call M n (ck-pick M fi (dec (nm-count M n))) fx)   ; JUN-733\n" ""]] "E2126"]
 ["no-caller-row" "seed/21-check.kotoba" [["(ck-r6m-refine (ck-row-note M1 fi k ty) fi k (ck-r6m-fnsig-np M1 ty))" "(ck-r6m-refine M1 fi k (ck-r6m-fnsig-np M1 ty))"]] "E2104"]
 ["no-get-default-on-record" "seed/21-check.kotoba" [["          (and (ck-rec-ty? M1 (ck-ty M1)) (= (nm-kind M1 (nm-nth M1 n 2)) ND-KW))   ; JUN-733: a default on a record\n          (ck-rget-d M1 n (nm-nth M1 n 1) (nm-nth M1 n 2) (nm-nth M1 n 3) fx)\n" ""]] "E2104"]
 ["no-keyword-default-on-record" "seed/21-check.kotoba" [["          (ck-rec-ty? M1 (ck-ty M1)) (ck-rget-d M1 n r kw d fx)   ; JUN-733: a default on a record\n" ""]] "E2103"]
])
(def refusals [
 ["non-record-argument" "(defn- f [m] (:a m))\n(defn main [] :i64 (f 5))" "E2104"]
 ["absent-field-without-default" "(defn- f [m] (:z m))\n(defn main [] :i64 (f {:a 1}))" "E2127"]
 ["exported-row-function" "(ns d (:export [main f]))\n(defn f [m] (:a m))\n(defn main [] :i64 (f {:a 1}))" "E2183"]
 ["row-function-as-a-value" "(defn- f [m] (:a m))\n(defn main [] :i64 (let [g f] 0))" "E2134"]
 ["computed-key-on-a-row" "(defn- f [m] (get m (if true :a :b) 0))\n(defn main [] :i64 (f {:a 1}))" "E2104"]
 ["recursive-row-without-result" "(defn- len [m] (if (> (:n m) 0) (+ 1 (len (assoc m :n (- (:n m) 1)))) 0))\n(defn main [] :i64 (len {:n 3}))" "E2126"]
 ["default-of-another-type" "(defn main [] :i64 (get {:a 1} :a \"s\"))" "E2104"]
 ["row-read-as-a-number" "(defn- f [m] (+ (:a m) m))\n(defn main [] :i64 (f {:a 1}))" "E2104"]
])
(def cids {"row" "(ns a (:export [main]))\n(defrecord P [x :i64 y :i64])\n(defn- f [p] (:x p))\n(defn main [] :i64 (f (->P 1 2)))\n" "annotated" "(ns a (:export [main]))\n(defrecord P [x :i64 y :i64])\n(defn- f [p [:ref :a/P]] :i64 (:x p))\n(defn main [] :i64 (f (->P 1 2)))\n"})

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
      (let [[status out err] (sb/run-source compiler refusal-dir "check" name
                                            (str (if (.startswith src "(ns") src (str ns-prefix src)) "\n"))]
        (when (or (zero? status) (not (.__contains__ (str out err) code)))
          (mac/fail (str name ": expected a check-time " code ", got exit " status ": " (tail300 (str out err)))))
        (println (str "refused " name ": " code))
        (.flush sys/stdout)))
    (let [ids (.joinpath output "cids")
          _ (.mkdir ids ** :mode 0700)]
      (let [[status out err] (sb/run-source compiler ids "definition-cids" "annotated" (get cids "annotated"))]
        (when (or (not= status 66) (seq out) (not (.startswith err "DSB:BRIDGE:3:")))
          (mac/fail (str "definition-cids annotated: expected atomic defrecord refusal, got exit " status ": " (tail300 (str out err))))))
      ;; Both modules contain a defrecord whose generated constructor must be refused atomically before any
      ;; per-definition identities are emitted.
      (let [[status out err] (sb/run-source compiler ids "definition-cids" "row" (get cids "row"))]
        (when (or (not= status 66) (seq out) (not (.startswith err "DSB:BRIDGE:3:")))
          (mac/fail (str "definition-cids row: expected atomic defrecord refusal, got exit " status ": " (tail300 (str out err))))))
      (println "definition-cids: both record modules refused atomically")
      (.flush sys/stdout))
    (let [names (vec (filter #(and (seq %) (not (.startswith % "#"))) (.splitlines (.read_text mac/manifest))))]
      (doseq [[label path edits expected] mutants]
        (when-not (contains? (set names) path) (mac/fail (str "FULL-MANIFEST no longer lists " path)))
        (let [text (reduce (fn [text [old new]]
                             (when (not= 1 (.count text old)) (mac/fail (str "cannot construct the " label " negative control")))
                             (.replace text old new))
                           (.read_text (.joinpath u/root path)) edits)
              mutant (.joinpath output label)
              _ (.mkdir mutant ** :mode 0700)
              _ (.write_text (.joinpath mutant "full-unity.kotoba")
                             (apply str (for [name names] (str (if (= name path) text (.read_text (.joinpath u/root name))) "\n"))))
              mutant-compiler (sb/build compiler packager mutant "full-unity" (.read_text (.joinpath mutant "full-unity.kotoba")))
              _ (when (u/deq (mac/pin mutant-compiler) (mac/pin compiler))
                  (mac/fail (str "mutant compiler is identical to the compiler under test: " label)))
              [status out err] (sb/run-source mutant-compiler mutant "check" "corpus" (.read_text corpus))]
          (if (= expected "run")
            (do (when (not (zero? status))
                  (mac/fail (str label " mutant: expected the corpus admitted, got exit " status ": " (tail300 (str out err)))))
                (let [built (sb/build mutant-compiler packager mutant "corpus-run" corpus)
                      run (subprocess/run (python/list [(str built)]) ** :cwd mutant :capture_output true :timeout 60
                                          :env (python/dict {"PATH" "/usr/bin:/bin" "LANG" "C"}))]
                  (when (zero? (.-returncode run)) (mac/fail (str label " mutant: the corpus still exits 0")))
                  (println (str label " (mutant compiler): corpus admitted, built and exits " (.-returncode run)))))
            (do (when (or (zero? status) (not (.__contains__ (str out err) expected)))
                  (mac/fail (str label " mutant: expected the corpus refused with " expected ", got exit " status ": " (tail300 (str out err)))))
                (println (str label " (mutant compiler): corpus refused with " expected))))
          (.flush sys/stdout))))
    (let [public (.joinpath output "public")
          _ (.mkdir public ** :mode 0700)
          _ (.write_bytes (.joinpath public "corpus.kotoba") (.read_bytes corpus))
          result (subprocess/run (python/list [(str (.joinpath u/root "bin/amu")) "run" "corpus.kotoba"]) ** :cwd public
                                 :env (python/dict {"PATH" "/usr/bin:/bin" "LANG" "C"}) :capture_output true :timeout 600)]
      (when (or (not (zero? (.-returncode result))) (not (u/deq (.-stdout result) (.encode "0\n"))) (u/nonempty? (.-stderr result)))
        (mac/fail (str "bin/amu run: exit " (.-returncode result) ", stdout " (.-stdout result) ", stderr " (.-stderr result))))
      (println "bin/amu run corpus: 0")
      (println "PASS_NATIVE_ROW_INFERENCE_WITH_NEGATIVE_CONTROLS")
      (.flush sys/stdout))))

(defn -main [& args]
  (main (.resolve (pathlib/Path (or (u/opt args "--compiler") (sys/exit "--compiler is required"))) ** :strict true)
        (.resolve (pathlib/Path (or (u/opt args "--output") (sys/exit "--output is required"))))))

(when (some #(or (= % "check-row-inference.cljc") (str/ends-with? % "/check-row-inference.cljc")) sys/argv)
  (apply -main *command-line-args*))
