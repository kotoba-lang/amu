;; Native destructuring is reader sugar for the plain temp-bound form (JUN-729).
;;
;; lang/guest-grammar.edn :nested-destructuring (L2) and
;; lang/surface-equivalence-corpus.edn :destructuring: a vector / map pattern in a
;; let or loop binding or a defn parameter desugars to sequential temp-bound
;; nth / vector-drop / get bindings, and the sugar and the pure spelling must mint
;; the same Definition CID. seed/21-check (ck-dx-*) expands the patterns before
;; typing; seed/20-names counts a pattern parameter as one parameter.
;;
;; This gate, on Apple Silicon:
;;
;; * builds seed/tests/native-destructuring.kotoba with --compiler (the Mac fixed
;;   point of this tree) and the descriptor's packager and runs it: exit 0;
;; * checks that each refusal below is refused at check time with its named code;
;; * Definition CIDs (`definition-cids`, profile 6 / desugar 2): every sugar/pure
;;   pair prints the same report; for the MEASURED pairs that report holds CIDs
;;   (no refusal) and each control prints a different one. The UNMEASURED pairs are
;;   refused identically on both sides by the definition bridge (`get`, and the
;;   vector-drop library group), so equality is not observable there;
;; * negative controls: two mutant full compilers built from this tree's
;;   FULL-MANIFEST -- one without the let/loop expansion, one without the
;;   parameter expansion -- must refuse the corpus (E2111 at a let pattern, E2111
;;   at the `&` of a pattern rest parameter), and the
;;   first one must not reproduce the pure CID of the corpus vector pair;
;; * runs the corpus through the public CLI (bin/amu run), which must print 0.
;;
;; Python stages sources and observes processes; every compiler and program is a
;; native Amu-built Mach-O.
;; Ported from check-destructuring.py (Basilisp, JUN-974). Apple Silicon macOS only. The refusal, pair and mutation
;; literals below are generated from the Python original so whitespace-sensitive anchors stay byte-exact.
;; Run: basilisp run -p scripts/seed scripts/seed/check-destructuring.cljc -- --compiler C --output DIR
(ns check-destructuring
  (:require [basilisp.string :as str]
            [gate-util :as u]
            [macos-image :as image]
            [macos-native-lib :as mac]
            [macos-scope-build :as sb])
  (:import pathlib subprocess sys))

(def corpus (.joinpath u/root "seed/tests/native-destructuring.kotoba"))

(def check-file "seed/21-check.kotoba")
(def ns-prefix "(ns d (:export [main]))\n")
(def mutants [
 ["no-let-loop-expansion" [["          (and (= k ND-LIST) (ck-dx-let? M n)) (ck-ds-walk (ck-dx M S n) S n)   ; JUN-729: destructuring\n" ""]] "E2111"]
 ["no-parameter-expansion" [["(if (= (nm-kind M p) ND-VEC) (ck-dx-params M p) (nm-put M MM-R0 0))" "(nm-put M MM-R0 0)"]] "E2111 malformed binding vector in '&'"]
])
(def refusals [
 ["strs-keys" "(defn main [] :i64 (let [{:strs [a]} {:a 1}] a))" "E2111"]
 ["syms-keys" "(defn main [] :i64 (let [{:syms [a]} {:a 1}] a))" "E2111"]
 ["keyword-in-vector" "(defn main [] :i64 (let [[a :b] [1 2]] a))" "E2111"]
 ["after-rest" "(defn main [] :i64 (let [[a & r b] [1 2 3]] a))" "E2111"]
 ["dangling-amp" "(defn main [] :i64 (let [[a &] [1 2 3]] a))" "E2111"]
 ["as-not-symbol" "(defn main [] :i64 (let [[a :as [b]] [1 2]] a))" "E2111"]
 ["or-not-map" "(defn main [] :i64 (let [{:keys [a] :or [a 1]} {:a 1}] a))" "E2111"]
 ["unspelled-key" "(defn main [] :i64 (let [{:keys [nope] :or {nope 1}} (typed-map-new [:map :keyword :i64] :a 1)] nope))" "E2111"]
 ["unspelled-record-key" "(defn main [] :i64 (let [{:keys [nope] :or {nope 1}} {:other 2}] nope))" "E2111"]
 ["string-key" "(defn main [] :i64 (let [{a \"a\"} {:a 1}] a))" "E2111"]
 ["rest-of-list" "(defn main [] :i64 (let [[a & r] (typed-list-new [:list :i64] 1 2)] a))" "E2104"]
 ["typed-map-no-default" "(defn main [] :i64 (let [{:keys [a]} (typed-map-new [:map :keyword :i64] :a 2)] a))" "E2121"]
 ["untyped-pattern-param" "(defn f [[a b]] :i64 (+ a b))\n(defn main [] :i64 (f 1))" "E2104"]
 ["fn-literal-pattern" "(defn main [] :i64 ((fn [[a b]] (+ a b)) [1 2]))" "E2139"]
 ["duplicate-name" "(defn main [] :i64 (let [[a a] [1 2]] a))" "E2112"]
])
(def pairs [
 ["vector (surface-equivalence-corpus :destructuring :vector)" "(ns d (:export [main]))\n(defn run [] (let [[a b] [1 2]] (+ a b)))\n(defn main [] (run))\n" "(ns d (:export [main]))\n(defn run [] (let [t [1 2] a (nth t 0) b (nth t 1)] (+ a b)))\n(defn main [] (run))\n" "(ns d (:export [main]))\n(defn run [] (let [[a b] [2 2]] (+ a b)))\n(defn main [] (run))\n" true]
 ["vector :as and _" "(ns d (:export [main]))\n(defn run [] (let [[a _ c :as v] [1 2 3]] (+ a (+ c (count v)))))\n(defn main [] (run))\n" "(ns d (:export [main]))\n(defn run [] (let [t [1 2 3] a (nth t 0) c (nth t 2) v t] (+ a (+ c (count v)))))\n(defn main [] (run))\n" "(ns d (:export [main]))\n(defn run [] (let [[a _ c :as v] [1 2 3]] (+ a (- c (count v)))))\n(defn main [] (run))\n" true]
 ["nested vector" "(ns d (:export [main]))\n(defn run [] (let [[[a b] [c]] (typed-list-new [:list :vector-i64] [1 2] [3])] (+ a (+ b c))))\n(defn main [] (run))\n" "(ns d (:export [main]))\n(defn run [] (let [t (typed-list-new [:list :vector-i64] [1 2] [3]) u (nth t 0) a (nth u 0) b (nth u 1) w (nth t 1) c (nth w 0)] (+ a (+ b c))))\n(defn main [] (run))\n" "(ns d (:export [main]))\n(defn run [] (let [[[a b] [c]] (typed-list-new [:list :vector-i64] [1 2] [4])] (+ a (+ b c))))\n(defn main [] (run))\n" true]
 ["defn parameter" "(ns d (:export [main]))\n(defn f [[a b] :vector-i64] :i64 (+ a b))\n(defn main [] (f [1 2]))\n" "(ns d (:export [main]))\n(defn f [t :vector-i64] :i64 (let [a (nth t 0) b (nth t 1)] (+ a b)))\n(defn main [] (f [1 2]))\n" "(ns d (:export [main]))\n(defn f [[a b] :vector-i64] :i64 (- a b))\n(defn main [] (f [1 2]))\n" true]
 ["loop (clojure.core/loop expansion)" "(ns d (:export [main]))\n(defn run [] :i64 (loop [[a b] [1 2] n 0] (if (> n 3) (+ a b) (recur [b a] (+ n 1)))))\n(defn main [] (run))\n" "(ns d (:export [main]))\n(defn run [] :i64 (let [g [1 2] a (nth g 0) b (nth g 1) n 0] (loop [g g n n] (let [a (nth g 0) b (nth g 1) n n] (if (> n 3) (+ a b) (recur [b a] (+ n 1)))))))\n(defn main [] (run))\n" "(ns d (:export [main]))\n(defn run [] :i64 (loop [[a b] [1 2] n 0] (if (> n 4) (+ a b) (recur [b a] (+ n 1)))))\n(defn main [] (run))\n" true]
 ["map :keys/:or (surface-equivalence-corpus :destructuring :map-keys-or)" "(ns d (:export [main]))\n(defn run [] (let [{:keys [x y] :or {x 0 y 0}} (typed-map-new [:map :keyword :i64] :x 2 :y 3)] (+ x y)))\n(defn main [] (run))\n" "(ns d (:export [main]))\n(defn run [] (let [m (typed-map-new [:map :keyword :i64] :x 2 :y 3) x (get m :x 0) y (get m :y 0)] (+ x y)))\n(defn main [] (run))\n" nil false]
 ["record :keys/:as" "(ns d (:export [main]))\n(defn run [] (let [{:keys [x y] :as m} {:x 2 :y 3}] (+ x (+ y (:x m)))))\n(defn main [] (run))\n" "(ns d (:export [main]))\n(defn run [] (let [t {:x 2 :y 3} x (get t :x) y (get t :y) m t] (+ x (+ y (:x m)))))\n(defn main [] (run))\n" nil false]
 ["vector & rest" "(ns d (:export [main]))\n(defn run [] (let [[a & r] [1 2 3]] (+ a (count r))))\n(defn main [] (run))\n" "(ns d (:export [main]))\n(defn run [] (let [t [1 2 3] a (nth t 0) r (vector-drop t 1)] (+ a (count r))))\n(defn main [] (run))\n" nil false]
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
    (let [identity (.joinpath output "cids")
          _ (.mkdir identity ** :mode 0700)
          vector-pure (atom nil)]
      (doseq [[index [label sugar pure control measured]] (map-indexed vector pairs)]
        (let [a (sb/cids-report compiler identity (str "s" index) sugar)
              b (sb/cids-report compiler identity (str "p" index) pure)]
          (when (not= a b) (mac/fail (str label ": sugar and pure reports differ:\n" a "\n--\n" b)))
          (when (zero? index) (reset! vector-pure b))
          (if measured
            (do (when (or (not (.startswith a "exit 0\n")) (.__contains__ a "REFUSED") (not (.__contains__ a "SCANNED")))
                  (mac/fail (str label ": expected identified definitions, got " (pr-str a))))
                (let [c (sb/cids-report compiler identity (str "c" index) control)]
                  (when (or (not (.startswith c "exit 0\n")) (= c a))
                    (mac/fail (str label ": the control does not change the CID: " (pr-str c))))
                  (let [run (vec (filter #(or (.startswith % "run\t") (.startswith % "f\t")) (.splitlines a)))]
                    (println (str "CID sugar == pure, control differs: " label ": " (if (seq run) (first run) (pr-str a)))))))
            (println (str "CID not observable (both sides print the same refusal): " label ": " (vec (take 1 (drop 1 (.splitlines a)))))))
          (.flush sys/stdout)))
      (doseq [[label edits code] mutants]
        (let [mutant (sb/mutant-compiler compiler packager output label check-file edits)
              mdir (.joinpath output label)
              [status out err] (sb/run-source mutant mdir "check" "corpus" (.read_text corpus))]
          (when (or (zero? status) (not (.__contains__ (str out err) code)))
            (mac/fail (str label " mutant: expected the corpus refused with " code ", got exit " status ": " (tail300 (str out err)))))
          (println (str label " (mutant compiler): corpus refused with " code))
          (when (= label "no-let-loop-expansion")
            (let [a (sb/cids-report mutant mdir "s0" (second (first pairs)))]
              (when (or (= a @vector-pure) (not (.__contains__ a "2111")))
                (mac/fail (str label " mutant: the vector sugar still reproduces the pure CID: " (pr-str a))))
              (println (str label " (mutant compiler): vector sugar has no CID: " (vec (take 1 (drop 1 (.splitlines a))))))))
          (.flush sys/stdout))))
    (let [public (.joinpath output "public")
          _ (.mkdir public ** :mode 0700)
          _ (.write_bytes (.joinpath public "corpus.kotoba") (.read_bytes corpus))
          result (subprocess/run (python/list [(str (.joinpath u/root "bin/amu")) "run" "corpus.kotoba"]) ** :cwd public
                                 :env (python/dict {"PATH" "/usr/bin:/bin" "LANG" "C"}) :capture_output true :timeout 600)]
      (when (or (not (zero? (.-returncode result))) (not (u/deq (.-stdout result) (.encode "0\n"))) (u/nonempty? (.-stderr result)))
        (mac/fail (str "bin/amu run: exit " (.-returncode result) ", stdout " (.-stdout result) ", stderr " (.-stderr result))))
      (println "bin/amu run corpus: 0")
      (println "PASS_NATIVE_DESTRUCTURING_WITH_NEGATIVE_CONTROLS")
      (.flush sys/stdout))))

(defn -main [& args]
  (main (.resolve (pathlib/Path (or (u/opt args "--compiler") (sys/exit "--compiler is required"))) ** :strict true)
        (.resolve (pathlib/Path (or (u/opt args "--output") (sys/exit "--output is required"))))))

(when (some #(or (= % "check-destructuring.cljc") (str/ends-with? % "/check-destructuring.cljc")) sys/argv)
  (apply -main *command-line-args*))
