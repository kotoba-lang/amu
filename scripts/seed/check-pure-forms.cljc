;; The pure heads lam, app and ref in the native frontend (JUN-950).
;;
;; kotoba-lang lang/pure-form.edn, against the native checker as measured at amu
;; 1754ff26f, where lam, app and ref were each E2101 and (def f (lam ..)) could not
;; be written. seed/20-names lowers them before any name is registered:
;;
;; * (def NAME (lam [x T ..] R BODY)) becomes (defn NAME [x T ..] R BODY);
;; * (lam [x ..] BODY) becomes (fn [x ..] BODY);
;; * (ref NAME) becomes NAME; (ref "bafy..") stays E2101 until a definition can be
;;   read by CID;
;; * (app NAME a ..) becomes (NAME a ..), and (app COMPUTED a ..) becomes
;;   (invoke COMPUTED a ..).
;;
;; This gate, on Apple Silicon:
;;
;; * builds seed/tests/native-pure-forms.kotoba with --compiler (the Mac fixed point
;;   of this tree) and runs it: exit 0;
;; * checks every refusal below at check time with its named code;
;; * checks that a module defining or binding one of the names keeps its own meaning;
;; * Definition CIDs (definition-cids): each pure spelling prints the CIDs of its
;;   surface spelling, and each control differs. (app (lam ..) a) has no CID: its
;;   invoke is unbridged, and that refusal is asserted so that a change is noticed;
;; * negative controls: one mutant full compiler per load-bearing change, built from
;;   this tree's FULL-MANIFEST with that change removed;
;; * runs the corpus through the public CLI (bin/amu run), which must print 0.
;;
;; Python stages sources and observes processes; every compiler and program is a
;; native Amu-built Mach-O.
;; Ported from check-pure-forms.py (Basilisp, JUN-974). Apple Silicon macOS only. The refusal, spelling and mutation
;; literals below are generated from the Python original so whitespace-sensitive anchors stay byte-exact.
;; Run: basilisp run -p scripts/seed scripts/seed/check-pure-forms.cljc -- --compiler C --output DIR
(ns check-pure-forms
  (:require [basilisp.string :as str]
            [gate-util :as u]
            [macos-image :as image]
            [macos-native-lib :as mac]
            [macos-scope-build :as sb])
  (:import pathlib subprocess sys))

(def corpus (.joinpath u/root "seed/tests/native-pure-forms.kotoba"))

(def norm-file "seed/20-names.kotoba")
(def ns-prefix "(ns d (:export [main]))\n")
(def main-def "(def main (lam [] :i64 1))\n")
(def shape "E2184 lam takes one body, and at the top level every parameter and its result are annotated")
(def d-def "(defn inc1 [n :i64] :i64 (+ n 1))\n")
(def p-def "(def inc1 (lam [n :i64] :i64 (+ n 1)))\n")
(def loop-src "(defn main [] :i64 (loop [i 0] (if (= i 3) i (recur (+ i 1)))))\n")
(def tail-src "(def lp (lam [i :i64] :i64 (if (= i 3) i (lp (+ i 1)))))\n(def main (lam [] :i64 (lp 0)))\n")
(def tail-control-src "(def lp (lam [i :i64] :i64 (if (= i 4) i (lp (+ i 1)))))\n(def main (lam [] :i64 (lp 0)))\n")
(def beta-src "(def inc1 (lam [n :i64] :i64 (+ n 1)))\n(def main (lam [] :i64 (app (ref inc1) (app (lam [x] (+ x 1)) 40))))\n")
(def user-app "(ns d (:export [main]))\n(defn app [x :i64] :i64 (+ x 1))\n(defn main [] :i64 (app 41))\n")
(def refusals [
 ["unannotated-parameter" "(def f (lam [x] :i64 x))\n(def main (lam [] :i64 1))\n" "E2184 lam takes one body, and at the top level every parameter and its result are annotated"]
 ["unannotated-second-parameter" "(def f (lam [x :i64 y] :i64 x))\n(def main (lam [] :i64 1))\n" "E2184 lam takes one body, and at the top level every parameter and its result are annotated"]
 ["no-result-type" "(def f (lam [x :i64] x))\n(def main (lam [] :i64 1))\n" "E2184 lam takes one body, and at the top level every parameter and its result are annotated"]
 ["two-bodies" "(def f (lam [x :i64] :i64 x x))\n(def main (lam [] :i64 1))\n" "E2184 lam takes one body, and at the top level every parameter and its result are annotated"]
 ["no-body" "(def f (lam [x :i64] :i64))\n(def main (lam [] :i64 1))\n" "E2184 lam takes one body, and at the top level every parameter and its result are annotated"]
 ["variadic" "(def f (lam [x :i64 & r] :i64 x))\n(def main (lam [] :i64 1))\n" "E2184 lam takes one body, and at the top level every parameter and its result are annotated"]
 ["destructuring" "(def f (lam [[a b] :i64] :i64 a))\n(def main (lam [] :i64 1))\n" "E2184 lam takes one body, and at the top level every parameter and its result are annotated"]
 ["no-parameter-vector" "(def f (lam x :i64 x))\n(def main (lam [] :i64 1))\n" "E2184 lam takes one body, and at the top level every parameter and its result are annotated"]
 ["inner-two-bodies" "(def main (lam [] :i64 (let [g (lam [x] x x)] (g 1))))\n" "E2184 lam takes one body, and at the top level every parameter and its result are annotated"]
 ["inner-no-vector" "(def main (lam [] :i64 (let [g (lam x x)] 1)))\n" "E2184 lam takes one body, and at the top level every parameter and its result are annotated"]
 ["inner-annotation" "(def main (lam [] :i64 (let [g (lam [x :i64] x)] (g 1))))\n" "E2139"]
 ["ref-by-cid" "(def main (lam [] :i64 (let [g (ref \"bafyreiblk\")] 1)))\n" "E2101 unknown or unsupported form 'ref'"]
 ["ref-two-names" "(def f (lam [] :i64 1))\n(def main (lam [] :i64 (let [g (ref f f)] 1)))\n" "E2101 unknown or unsupported form 'ref'"]
 ["app-no-operator" "(def main (lam [] :i64 (app)))\n" "E2101 unknown or unsupported form 'app'"]
 ["def-of-fn" "(def f (fn [x :i64] :i64 x))\n(def main (lam [] :i64 1))\n" "E2124"]
])
(def own-meaning [
 ["defines-app" "(defn app [x :i64] :i64 (+ x 1))\n(defn main [] :i64 (app 41))\n" 42]
 ["defines-lam" "(defn lam [x :i64] :i64 x)\n(defn main [] :i64 (lam 42))\n" 42]
 ["defines-ref" "(defn ref [x :i64] :i64 x)\n(defn main [] :i64 (ref 42))\n" 42]
 ["parameter-app" "(defn f [app :i64] :i64 app)\n(defn main [] :i64 (f 42))\n" 42]
 ["let-app" "(defn main [] :i64 (let [app (fn [x] (+ x 1))] (app 41)))\n" 42]
])
(def cid-groups [
 ["definition" ["(defn inc1 [n :i64] :i64 (+ n 1))\n(defn main [] :i64 (inc1 (inc1 40)))\n" "(def inc1 (lam [n :i64] :i64 (+ n 1)))\n(def main (lam [] :i64 (inc1 (inc1 40))))\n" "(def inc1 (lam [n :i64] :i64 (+ n 1)))\n(def main (lam [] :i64 (app (ref inc1) (app (ref inc1) 40))))\n" "(defn inc1 [n :i64] :i64 (+ n 1))\n(defn main [] :i64 (-> 40 inc1 inc1))\n"] "(def inc1 (lam [n :i64] :i64 (+ n 1)))\n(def main (lam [] :i64 (inc1 (inc1 41))))\n"]
 ["cond-is-if" ["(defn main [] :i64 (cond (< 1 2) 1 :else 0))\n" "(def main (lam [] :i64 (if (< 1 2) 1 0)))\n"] "(def main (lam [] :i64 (if (< 1 3) 1 0)))\n"]
])
(def mutants [
 ["no-pure-pass" [["(nm-run-defs (nm-dp-norm (nm-pure-norm (nm-r6b-norm (nm-intern-nodes M S 1)))))" "(nm-run-defs (nm-dp-norm (nm-r6b-norm (nm-intern-nodes M S 1))))"]] "@CORPUS@" "E2005 export of undefined function 'main'"]
 ["app-keeps-its-head" [["(= (nm-kind M op) ND-SYM) (nm-set-nf M n NF-FIRST op)" "(= (nm-kind M op) ND-SYM) (nm-touch M)"]] "@CORPUS@" "E2101 unknown or unsupported form 'app'"]
 ["ref-keeps-its-head" [["(nm-pf-head? M n nm-pf-ref) (nm-pf-refs (nm-pf-ref1 M n) (+ n 1))" "(nm-pf-head? M n nm-pf-ref) (nm-pf-refs M (+ n 1))"]] "@CORPUS@" "unknown or unsupported form 'ref'"]
 ["top-lam-unchecked" [["(and (= (nm-count M l) 4) (= (nm-kind M v) ND-VEC) (nm-pf-typed-params? M v) (nm-pf-type? M r))" "(and (= (nm-kind M v) ND-VEC) (nm-pf-type? M r))"]] "(ns d (:export [main]))\n(def f (lam [x] :i64 x))\n(def main (lam [] :i64 1))\n" nil]
 ["user-name-rewritten" [["(and (nm-pf-spelled? M hash) (not (nm-pf-user? M hash)))" "(nm-pf-spelled? M hash)"]] "(ns d (:export [main]))\n(defn app [x :i64] :i64 (+ x 1))\n(defn main [] :i64 (app 41))\n" "E2104 type mismatch in 'app'"]
])

(defn tail300 [s] (pr-str (subs s (max 0 (- (count s) 300)))))

(defn cid-rows
  "Sorted CIDs of a definition-cids report, ignoring names and order; refuses a report with a refusal."
  [compiler directory name source]
  (let [out (sb/cids compiler directory name (str ns-prefix source))]
    (when (.__contains__ out "REFUSED") (mac/fail (str name ": definition refused: " (pr-str out))))
    (let [rows (vec (for [line (.splitlines out) :when (and (.__contains__ line "\t") (not (.startswith line "SCANNED")))]
                      (second (.split line "\t"))))]
      (when (empty? rows) (mac/fail (str name ": no definitions reported: " (pr-str out))))
      (vec (sort rows)))))

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
      (let [[status out err] (sb/run-source compiler refusal-dir "check" name (str ns-prefix src))]
        (when (or (zero? status) (not (.__contains__ (str out err) code)))
          (mac/fail (str name ": expected a check-time " code ", got exit " status ": " (tail300 (str out err)))))
        (println (str "refused " name ": " code))
        (.flush sys/stdout)))
    (let [own (.joinpath output "own-meaning")
          _ (.mkdir own ** :mode 0700)]
      (doseq [[name src expected] own-meaning]
        (let [status (sb/build-run compiler packager own name (str ns-prefix src))]
          (when (not= status expected) (mac/fail (str name ": expected exit " expected ", got " status)))
          (println (str "own meaning kept: " name " exit " expected))
          (.flush sys/stdout))))
    (let [ids (.joinpath output "cids")
          _ (.mkdir ids ** :mode 0700)]
      (doseq [[label spellings control] cid-groups]
        (let [rows (vec (map-indexed (fn [i s] (cid-rows compiler ids (str label "-" i) s)) spellings))]
          (when (some #(not= % (first rows)) rows) (mac/fail (str label ": spellings print different CIDs: " rows)))
          (when (= (cid-rows compiler ids (str label "-control") control) (first rows))
            (mac/fail (str label ": the control has the spellings' CIDs")))
          (println (str "definition-cids: " label ": " (count spellings) " spellings agree; control differs"))
          (.flush sys/stdout)))
      (let [loop-rows (cid-rows compiler ids "loop" loop-src)
            tail-rows (cid-rows compiler ids "tail" tail-src)]
        (when (not= loop-rows tail-rows) (mac/fail (str "loop and the tail-recursive def print different CIDs: " loop-rows " " tail-rows)))
        (when (= (cid-rows compiler ids "tail-control" tail-control-src) tail-rows)
          (mac/fail "the tail-recursion control has the same CIDs"))
        (println "definition-cids: loop = tail-recursive def; control differs")
        (.flush sys/stdout))
      (let [[status out err] (sb/run-source compiler ids "definition-cids" "beta" (str ns-prefix beta-src))]
        (when-not (.__contains__ (str out err) "REFUSED:unbridged-source")
          (mac/fail (str "(app (lam ..) a): expected the unbridged refusal, got exit " status ": " (tail300 (str out err)))))
        (println "definition-cids: (app (lam ..) a) refused as unbridged, the recorded boundary")
        (.flush sys/stdout)))
    (doseq [[label edits source expected] mutants]
      (let [source (if (= source "@CORPUS@") (.read_text corpus) source)
            mutant (sb/mutant-compiler compiler packager output label norm-file edits)
            mdir (.joinpath output label)
            [status out err] (sb/run-source mutant mdir "check" "probe" source)]
        (if (nil? expected)
          (do (when (not (zero? status))
                (mac/fail (str label " mutant: expected the refused source admitted, got exit " status ": " (tail300 (str out err)))))
              (println (str label " (mutant compiler): the refused source is admitted")))
          (do (when (or (zero? status) (not (.__contains__ (str out err) expected)))
                (mac/fail (str label " mutant: expected a refusal with " expected ", got exit " status ": " (tail300 (str out err)))))
              (println (str label " (mutant compiler): refused with " expected))))
        (.flush sys/stdout)))
    (let [public (.joinpath output "public")
          _ (.mkdir public ** :mode 0700)
          _ (.write_bytes (.joinpath public "corpus.kotoba") (.read_bytes corpus))
          result (subprocess/run (python/list [(str (.joinpath u/root "bin/amu")) "run" "corpus.kotoba"]) ** :cwd public
                                 :env (python/dict {"PATH" "/usr/bin:/bin" "LANG" "C"}) :capture_output true :timeout 600)]
      (when (or (not (zero? (.-returncode result))) (not (u/deq (.-stdout result) (.encode "0\n"))) (u/nonempty? (.-stderr result)))
        (mac/fail (str "bin/amu run: exit " (.-returncode result) ", stdout " (.-stdout result) ", stderr " (.-stderr result))))
      (println "bin/amu run corpus: 0")
      (println "PASS_NATIVE_PURE_FORMS_WITH_NEGATIVE_CONTROLS")
      (.flush sys/stdout))))

(defn -main [& args]
  (main (.resolve (pathlib/Path (or (u/opt args "--compiler") (sys/exit "--compiler is required"))) ** :strict true)
        (.resolve (pathlib/Path (or (u/opt args "--output") (sys/exit "--output is required"))))))

(when (some #(or (= % "check-pure-forms.cljc") (str/ends-with? % "/check-pure-forms.cljc")) sys/argv)
  (apply -main *command-line-args*))
