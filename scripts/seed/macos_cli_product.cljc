;; Observe ordinary native CLI commands and refusals, never compile in Python (library half of the Mac CLI product
;; gate). Ported from check-macos-cli-product.py (Basilisp, JUN-974). Apple Silicon macOS only.
(ns macos-cli-product
  (:require [basilisp.string :as str]
            [gate-util :as u]
            [macos-native-lib :as mac])
  (:import json operator os pathlib platform shutil subprocess time))

(defn- b [s] (.encode s))
(defn- tmp-amu [] (python/set (python/list (.glob (pathlib/Path "/private/tmp") "amu-*"))))

(defn check [cli out]
  (u/chk (and (= "Darwin" (platform/system)) (= "arm64" (platform/machine))))
  (let [root u/root
        cli (pathlib/Path cli)
        out (pathlib/Path out)
        _ (mac/verify-macho cli)
        _ (.mkdir out ** :parents true :mode 0700 :exist_ok false)
        before-tmp (tmp-amu)
        calls (python/list)
        run (fn run [name args & {:keys [expected stdout diagnostic image] :or {expected 0}}]
              (let [start (time/monotonic)
                    r (subprocess/run (python/list (map str (cons (or image cli) args))) ** :cwd out
                                      :env (python/dict {"PATH" "/nonexistent" "LANG" "C" "AMU_TARGET" "bad-target"})
                                      :capture_output true :timeout 150)]
                (doseq [stream ["stdout" "stderr"]]
                  (.write_bytes (.joinpath out (str name "." stream)) (python/getattr r stream)))
                (u/chk (= expected (.-returncode r)) (str name " " (.-returncode r) " " (.-stdout r) (.-stderr r)))
                (when-not (nil? stdout) (u/chk (u/deq (.-stdout r) stdout) (str name " " (.-stdout r))))
                (if-not (nil? diagnostic)
                  (u/chk (u/has-bytes? diagnostic (.-stderr r)) (str name " " (.-stderr r)))
                  (when (zero? expected) (u/chk (not (u/nonempty? (.-stderr r))) (str name " " (.-stderr r)))))
                (.append calls (u/pydict "name" name "exit" (.-returncode r) "seconds" (python/round (- (time/monotonic) start) 3)
                                         "stdout" (mac/pin (.joinpath out (str name ".stdout")))
                                         "stderr" (mac/pin (.joinpath out (str name ".stderr")))))
                r))
        source (fn [name body]
                 (let [p (.joinpath out (str name ".kotoba"))]
                   (.write_text p (str "(ns hello (:export [main]))\n" body "\n"))
                   p))
        run-ok (fn [name args out-bytes] (run name args :stdout out-bytes))
        hello (source "hello" "(defn main [] :i64 42)")]
    (run-ok "check" ["check" (.-name hello)] (b "ok\n"))
    ;; JUN-579: a lone `check` reads `.cljk` input sugar; compile and the retired extensions refuse.
    (let [sugar (.joinpath out "hello-sugar.cljk")]
      (.write_text sugar (.read_text hello))
      (run-ok "check-cljk" ["check" (.-name sugar)] (b "ok\n"))
      (run "compile-cljk" ["compile" (.-name sugar)] :expected 2 :diagnostic (b "usage")))
    (let [retired (.joinpath out "hello-retired.cljc")]
      (.write_text retired (.read_text hello))
      (run "check-cljc" ["check" (.-name retired)] :expected 2 :diagnostic (b "usage")))
    ;; KOTOBA-161: negative float comparisons catch the previously observed integer-condition lowering error; the
    ;; reversed operands are the control.
    (let [float-less (source "float-negative-less" "(defn main [] :i64 (if (f64-lt -2.0 -1.0) 42 7))")
          float-greater (source "float-negative-greater" "(defn main [] :i64 (if (f64-lt -1.0 -2.0) 42 7))")]
      (run-ok "float-negative-less" ["run" (.-name float-less)] (b "42\n"))
      (run-ok "float-negative-greater" ["run" (.-name float-greater)] (b "7\n")))
    ;; JUN-846: f64-to-bits answers one canonical quiet NaN (0x7FF8000000000000) for every NaN, as the reference
    ;; does, so an x86 default NaN, a negative NaN and a payload NaN cannot make bits/serialisation host-dependent.
    ;; Infinity and -0.0 keep their exact bits. Each term is a distinct decimal digit; the pre-fix compiler answers 111001.
    (let [nan-canonical (source "f64-nan-canonical"
                                (str "(defn main [] :i64\n"
                                     "  (let [nan (f64-div (i64-to-f64-rounded 0) (i64-to-f64-rounded 0))\n"
                                     "        neg-nan (f64-from-bits -2251799813685248)\n"
                                     "        payload (f64-from-bits 9218868437227405313)\n"
                                     "        neg-zero (f64-neg (i64-to-f64-rounded 0))\n"
                                     "        inf (f64-div (i64-to-f64-rounded 1) (i64-to-f64-rounded 0))]\n"
                                     "    (+ (if (= (f64-to-bits nan) 9221120237041090560) 1 0)\n"
                                     "       (if (= (f64-to-bits neg-nan) 9221120237041090560) 10 0)\n"
                                     "       (if (= (f64-to-bits payload) 9221120237041090560) 100 0)\n"
                                     "       (if (= (f64-to-bits neg-zero) -9223372036854775808) 1000 0)\n"
                                     "       (if (= (f64-to-bits 1.5) 4609434218613702656) 10000 0)\n"
                                     "       (if (= (f64-to-bits inf) 9218868437227405312) 100000 0))))"))]
      (run-ok "f64-nan-canonical" ["run" (.-name nan-canonical)] (b "111111\n")))
    ;; JUN-846: :vector-f64 (library defn-s over :vector-i64; a type of its own). 7221907 = 7 + 100*19 + 10000*2 +
    ;; 100000*2 + 1000000*7 over new/conj/assoc/take/drop/get/at/count; the two mixes with :vector-i64 are E2104.
    (let [vf64 (source "vector-f64"
                       (str "(defn sum [v :vector-f64] :f64\n"
                            "  (loop [i 0 acc 0.0]\n"
                            "    (if (>= i (vector-f64-count v)) acc (recur (+ i 1) (f64-add acc (vector-f64-at v i))))))\n"
                            "(defn main [] :i64\n"
                            "  (let [v (vector-f64-new 1.5 2.5 3.0)\n"
                            "        w (vector-f64-assoc (vector-f64-conj v 4.0) 0 10.0)\n"
                            "        t (vector-f64-take w 2)\n"
                            "        d (vector-f64-drop w 2)]\n"
                            "    (+ (f64-to-i64-truncating (sum v))\n"
                            "       (* 100 (f64-to-i64-truncating (sum w)))\n"
                            "       (* 10000 (vector-f64-count t))\n"
                            "       (* 100000 (vector-f64-count d))\n"
                            "       (* 1000000 (f64-to-i64-truncating (vector-f64-get v 9 7.0))))))"))]
      (run-ok "vector-f64" ["run" (.-name vf64)] (b "7221907\n")))
    (let [p (source "vector-f64-as-i64" "(defn f [v :vector-i64] :i64 (vector-count v))\n(defn main [] :i64 (f (vector-f64-new 1.5)))")]
      (run "vector-f64-as-i64" ["check" (.-name p)] :expected 1 :diagnostic (b "E2104 type mismatch in")))
    (let [p (source "vector-i64-as-f64" "(defn f [v :vector-f64] :i64 (vector-f64-count v))\n(defn main [] :i64 (f (vector-alloc 3)))")]
      (run "vector-i64-as-f64" ["check" (.-name p)] :expected 1 :diagnostic (b "E2104 type mismatch in")))
    (let [p (source "vector-f64-field" "(defrecord R [v :vector-f64])\n(defn main [] :i64 1)")]
      (run "vector-f64-field" ["check" (.-name p)] :expected 1 :diagnostic (b "E2128")))
    ;; KOTOBA-13: the public host stages a locked KSL2 namespace map, verifies every original source digest, then
    ;; asks the pinned Kotoba compiler to check the rewritten project lock in its private FS2 root.
    (let [project (.joinpath out "locked-project")
          _ (.mkdir project)
          app (.joinpath project "app.kotoba")
          util (.joinpath project "util.kotoba")
          _ (.write_text app "(ns app (:require [util :as u]) (:export [main]))\n(defn main [] :i64 (u/add 41))\n")
          _ (.write_text util "(ns util (:export [add]))\n(defn add [x :i64] :i64 (+ x 1))\n")
          project-lock (fn [entry modules files]
                         (str "KSL2\nentry " entry "\n"
                              (apply str (for [[name path] modules] (str "module " name " " path "\n")))
                              (apply str (for [path (python/sorted (python/list files))]
                                           (str "file " (u/sha256-hex (.read_bytes path)) " " path "\n")))))
          ;; The previous formatter exhausted the native string pool when formatting subnormals repeatedly. Exercise
          ;; the real formatter, parser and boundary anchors; a deliberately wrong anchor must fail the same observation.
          f64-project (.joinpath out "f64-resource-project")
          _ (.mkdir f64-project)
          f64-source0 (.read_text (.joinpath root "test/fixtures/selfhost/f64-text/native/f64_text_test.kotoba"))
          main-at (.index f64-source0 "(defn main [] :i64")
          f64-source (str (subs f64-source0 0 main-at)
                          "(defn main [] :i64\n  (if (and (anchors) (refusals)\n           (loop [i 0] (if (= i 40) true (if (roundtrip 1) (recur (+ i 1)) false)))) 42 7))\n")
          f64-entry (.joinpath f64-project "f64_text_test.kotoba")
          f64-text (.joinpath f64-project "f64_text.kotoba")
          f64-decimal (.joinpath f64-project "decimal_bits.kotoba")
          _ (shutil/copyfile (.joinpath root "src/kotoba/compiler/f64_text.kotoba") f64-text)
          _ (shutil/copyfile (.joinpath root "src/kotoba/compiler/decimal_bits.kotoba") f64-decimal)
          f64-modules [["kotoba.compiler.decimal-bits" f64-decimal] ["kotoba.compiler.f64-text" f64-text] ["native.f64-text-test" f64-entry]]
          f64-lock (.joinpath f64-project "project.ksl")]
      (doseq [[suffix body expected-output] [["positive" f64-source (b "42\n")]
                                             ["negative" (.replace f64-source "\"5e-324\"" "\"5e-323\"") (b "7\n")]]]
        (u/chk (= (.count body "\"5e-324\"") (if (= suffix "positive") 1 0)))
        (.write_text f64-entry body)
        (.write_text f64-lock (project-lock f64-entry f64-modules [f64-entry f64-text f64-decimal]))
        (let [f64-program (.joinpath out (str "f64-resource-" suffix))]
          (run (str "f64-resource-" suffix "-compile") ["compile" f64-entry "--source-lock" f64-lock "-o" (.-name f64-program)]
               :stdout (b (str "compiled " f64-program "\n")))
          (run (str "f64-resource-" suffix "-execute") [] :image f64-program :stdout expected-output)))
      ;; JUN-924: the clojure.test -> plain defn/main converter is a multi-module native program over the lossless
      ;; CST. Its self-gate answers the number of failed fixtures (0 = all hold); changing one expected text must turn
      ;; the same program red, so the observation cannot pass by building and printing 0.
      (let [tc-project (.joinpath out "test-conv-project")
            tc-dir (.joinpath tc-project "kotoba/compiler/refactor")
            _ (.mkdir tc-dir ** :parents true)
            _ (shutil/copyfile (.joinpath root "src/kotoba/compiler/refactor/cst.kotoba") (.joinpath tc-dir "cst.kotoba"))
            tc-source (.read_text (.joinpath root "src/kotoba/compiler/refactor/test_conv.kotoba"))
            tc-entry (.joinpath tc-dir "test_conv.kotoba")
            expected-tail "(not (two)) 2 :else 42))\\n\"))"
            _ (u/chk (= 1 (.count tc-source expected-tail)))]
        (doseq [[suffix body expected-output] [["positive" tc-source (b "0\n")]
                                               ["negative" (.replace tc-source expected-tail "(not (two)) 2 :else 43))\\n\"))") (b "1\n")]]]
          (.write_text tc-entry body)
          (let [tc-program (.joinpath out (str "test-conv-" suffix))]
            (run (str "test-conv-" suffix "-compile") ["compile" tc-entry "--source-path" tc-project "-o" (.-name tc-program)]
                 :stdout (b (str "compiled " tc-program "\n")))
            (run (str "test-conv-" suffix "-execute") [] :image tc-program :stdout expected-output))))
      ;; JUN-933: the cljk reader-syntax converter (#( ) / #_ / #?) is a multi-module native program over the same CST.
      ;; Same shape as test-conv: the self-gate answers the number of failed fixtures; one expected text turned wrong
      ;; must turn the same program red.
      (let [sc-project (.joinpath out "syntax-conv-project")
            sc-dir (.joinpath sc-project "kotoba/compiler/refactor")
            _ (.mkdir sc-dir ** :parents true)
            _ (shutil/copyfile (.joinpath root "src/kotoba/compiler/refactor/cst.kotoba") (.joinpath sc-dir "cst.kotoba"))
            sc-source (.read_text (.joinpath root "src/kotoba/compiler/refactor/syntax_conv.kotoba"))
            sc-entry (.joinpath sc-dir "syntax_conv.kotoba")
            sc-right "\"(map (fn [p1] (+ p1 1)) xs)\""
            _ (u/chk (= 1 (.count sc-source sc-right)))]
        (doseq [[suffix body expected-output] [["positive" sc-source (b "0\n")]
                                               ["negative" (.replace sc-source sc-right "\"(map (fn [p2] (+ p1 1)) xs)\"") (b "1\n")]]]
          (.write_text sc-entry body)
          (let [sc-program (.joinpath out (str "syntax-conv-" suffix))]
            (run (str "syntax-conv-" suffix "-compile") ["compile" sc-entry "--source-path" sc-project "-o" (.-name sc-program)]
                 :stdout (b (str "compiled " sc-program "\n")))
            (run (str "syntax-conv-" suffix "-execute") [] :image sc-program :stdout expected-output))))
      (let [lock (.joinpath project "project.ksl")]
        (.write_text lock (project-lock app [["app" app] ["util" util]] [app util]))
        (run-ok "locked-project-check" ["check" app "--source-lock" lock] (b "ok\n"))
        ;; JUN-838: `check ENTRY --source-path DIR...` derives the KSL2 module map from the declared roots; the pinned
        ;; root still verifies it. A module on no declared root keeps the root's E6002, two roots holding one module refuse.
        (let [sp (.joinpath out "source-path-project")]
          (doseq [d ["src/lib" "other/lib" "dup/lib"]] (.mkdir (.joinpath sp d) ** :parents true))
          (let [sp-app (.joinpath sp "src/app.kotoba")
                src-root (.joinpath sp "src") other-root (.joinpath sp "other") dup-root (.joinpath sp "dup")]
            (.write_text sp-app "(ns app (:require [lib.mid :as m]) (:export [main]))\n(defn main [] :i64 (m/two 40))\n")
            (.write_text (.joinpath sp "src/lib/mid.kotoba")
                         (str "(ns lib.mid (:require [lib.leaf :as l]) (:export [two]))\n"
                              "(defn two [x :i64] :i64 (l/inc1 (l/inc1 x)))\n"))
            (.write_text (.joinpath sp "other/lib/leaf.kotoba") "(ns lib.leaf (:export [inc1]))\n(defn inc1 [x :i64] :i64 (+ x 1))\n")
            (.write_bytes (.joinpath sp "dup/lib/leaf.kotoba") (.read_bytes (.joinpath sp "other/lib/leaf.kotoba")))
            (run-ok "source-path-check" ["check" sp-app "--source-path" src-root "--source-path" other-root] (b "ok\n"))
            (run "source-path-missing-module" ["check" sp-app "--source-path" src-root]
                 :expected 1 :diagnostic (b "E6002 required module lib.leaf is missing from the explicit source paths"))
            (run "source-path-unlisted-root" ["check" sp-app "--source-path" other-root]
                 :expected 1 :diagnostic (b "E6002 required module lib.mid is missing from the explicit source paths"))
            (run "source-path-ambiguous-module" ["check" sp-app "--source-path" src-root "--source-path" other-root "--source-path" dup-root]
                 :expected 1 :diagnostic (b "EPATH module lib.leaf is found under more than one"))
            (run "source-path-with-lock" ["check" sp-app "--source-path" src-root "--source-lock" (.joinpath sp "x.ksl")]
                 :expected 2 :diagnostic (b "usage"))
            (run "source-path-dangling-flag" ["check" sp-app "--source-path" src-root "--source-path"] :expected 2 :diagnostic (b "usage"))
            ;; compile takes the same roots (parity with --source-lock compile). run stays refused: mc-main-abi?
            ;; cannot validate a multi-file project.
            (let [sp-program (.joinpath sp "../source-path-program")
                  sp-program (.joinpath out "source-path-program")]
              (run "source-path-compile" ["compile" sp-app "--source-path" src-root "--source-path" other-root "-o" (.-name sp-program)]
                   :stdout (b (str "compiled " sp-program "\n")))
              (mac/verify-macho sp-program)
              (run "source-path-native-execute" [] :expected 0 :stdout (b "42\n") :image sp-program)
              (run-ok "source-path-run-artifact" ["run" sp-program] (b "42\n"))
              (let [sp-profile (.joinpath out "source-path-profile-program")]
                (run "source-path-compile-profile" ["compile" sp-app "--source-path" src-root "--source-path" other-root
                                                    "--runtime-profile" "amu-program" "-o" (.-name sp-profile)]
                     :stdout (b (str "compiled " sp-profile "\n")))
                (mac/verify-macho sp-profile))
              (let [sp-program-bytes (.read_bytes sp-program)]
                (run "source-path-compile-output-collision" ["compile" sp-app "--source-path" src-root "--source-path" other-root "-o" (.-name sp-program)]
                     :expected 1 :diagnostic (b "EOUTPUT"))
                (u/chk (u/deq (.read_bytes sp-program) sp-program-bytes))))
            (run "source-path-compile-output-is-entry" ["compile" sp-app "--source-path" src-root "--source-path" other-root "-o" sp-app]
                 :expected 1 :diagnostic (b "EOUTPUT cannot replace the project entry"))
            (run "source-path-compile-missing-module" ["compile" sp-app "--source-path" src-root "-o" "sp-missing"]
                 :expected 1 :diagnostic (b "E6002 required module lib.leaf is missing from the explicit source paths"))
            (run "source-path-compile-ambiguous-module" ["compile" sp-app "--source-path" src-root "--source-path" other-root "--source-path" dup-root "-o" "sp-ambiguous"]
                 :expected 1 :diagnostic (b "EPATH module lib.leaf is found under more than one"))
            (run "source-path-compile-with-lock" ["compile" sp-app "--source-path" src-root "--source-lock" (.joinpath sp "x.ksl") "-o" "sp-mixed"]
                 :expected 2 :diagnostic (b "usage"))
            (run "source-path-run-refused" ["run" sp-app "--source-path" src-root] :expected 2 :diagnostic (b "usage"))
            (run "source-path-run-args-refused" ["run" sp-app "--source-path" src-root "--" "x"] :expected 2 :diagnostic (b "usage"))
            (run "source-path-run-with-lock" ["run" sp-app "--source-path" src-root "--source-lock" (.joinpath sp "x.ksl")] :expected 2 :diagnostic (b "usage"))
            (run "source-path-compile-dangling-flag" ["compile" sp-app "--source-path" src-root "-o"] :expected 2 :diagnostic (b "usage"))
            (run "source-path-compile-no-root-value" ["compile" sp-app "--source-path"] :expected 2 :diagnostic (b "usage"))
            (run "source-path-run-no-separator" ["run" sp-app "--source-path" src-root "extra"] :expected 2 :diagnostic (b "usage"))
            (run "source-path-run-receipt-refused" ["run" sp-app "--source-path" src-root "--receipt" "r.json"] :expected 2 :diagnostic (b "usage"))
            (run "source-path-too-many-roots" (concat ["check" sp-app] (mapcat (fn [_] ["--source-path" src-root]) (range 17)))
                 :expected 2 :diagnostic (b "usage"))))
        (let [project-program (.joinpath out "locked-project-program")]
          (run "locked-project-compile" ["compile" app "--source-lock" lock "-o" (.-name project-program)]
               :stdout (b (str "compiled " project-program "\n")))
          (mac/verify-macho project-program)
          (run "locked-project-native-execute" [] :expected 0 :stdout (b "42\n") :image project-program)
          (run-ok "locked-project-run" ["run" app "--source-lock" lock] (b "42\n"))
          (run-ok "locked-project-run-artifact" ["run" project-program] (b "42\n"))
          (let [damaged (.joinpath out "damaged-locked-project-program")
                damaged-bytes (python/bytearray (.read_bytes project-program))
                n (dec (python/len damaged-bytes))]
            (operator/setitem damaged-bytes n (bit-xor (operator/getitem damaged-bytes n) 1))
            (.write_bytes damaged damaged-bytes)
            (run "locked-project-run-damaged-artifact" ["run" damaged] :expected 1 :diagnostic (b "EARTIFACT supplied project differs")))
          (let [kept (.read_bytes project-program)]
            (run "locked-project-output-collision" ["compile" app "--source-lock" lock "-o" (.-name project-program)]
                 :expected 1 :diagnostic (b "EOUTPUT"))
            (u/chk (u/deq (.read_bytes project-program) kept))))
        (run "locked-project-wrong-entry" ["check" util "--source-lock" lock] :expected 1 :diagnostic (b "ELOCK entry does not match"))
        (run "locked-project-compile-wrong-entry" ["compile" util "--source-lock" lock "-o" "wrong-entry-program"]
             :expected 1 :diagnostic (b "ELOCK entry does not match"))
        (let [bad-utf8-lock (.joinpath project "invalid-utf8.ksl")]
          (.write_bytes bad-utf8-lock (u/hex->bytes "4b534c320aff0a"))
          (run "locked-project-invalid-utf8-lock" ["check" app "--source-lock" bad-utf8-lock]
               :expected 1 :diagnostic (b "ELOCK source lock must be valid UTF-8")))
        (let [legacy (.joinpath project "legacy.cljk")
              legacy-lock (.joinpath project "legacy.ksl")]
          (.write_text legacy (.read_text app))
          (.write_text legacy-lock (project-lock legacy [["app" legacy] ["util" util]] [legacy util]))
          (run "locked-project-non-kotoba-path" ["check" legacy "--source-lock" legacy-lock]
               :expected 1 :diagnostic (b "ELOCK project files must use canonical .kotoba paths")))
        (.write_text util (str (.read_text util) "\n"))
        (run "locked-project-changed-source" ["check" app "--source-lock" lock] :expected 1 :diagnostic (b "EINPUT a locked project source"))
        (run "locked-project-compile-changed-source" ["compile" app "--source-lock" lock "-o" "changed-source-program"]
             :expected 1 :diagnostic (b "EINPUT a locked project source"))
        (run "locked-project-run-changed-source" ["run" app "--source-lock" lock] :expected 1 :diagnostic (b "EINPUT a locked project source"))
        (.write_text util "(ns util (:export [add]))\n(defn add [x :i64] :i64 (+ x 1))\n")
        (let [missing (.joinpath project "missing.kotoba")
              missing-lock (.joinpath project "missing.ksl")]
          (.write_text missing "(ns app (:require [absent :as a]) (:export [main]))\n(defn main [] :i64 (a/value))\n")
          (.write_text missing-lock (project-lock missing [["app" missing] ["util" util]] [missing util]))
          (run "locked-project-missing-import" ["check" missing "--source-lock" missing-lock] :expected 1 :diagnostic (b "E")))))
    (run "compile-default" ["compile" (.-name hello)])
    (mac/verify-macho (.joinpath out "hello"))
    (run "execute-default" [] :expected 0 :stdout (b "42\n") :image (.joinpath out "hello"))
    (run-ok "run-source" ["run" (.-name hello)] (b "42\n"))
    (run-ok "run-artifact" ["run" "./hello"] (b "42\n"))
    ;; JUN-282: an opt-in run receipt binds source, host images, program and stdout
    (run-ok "run-receipt" ["run" (.-name hello) "--receipt" "run-receipt.json"] (b "42\n"))
    (let [receipt (u/read-json (.joinpath out "run-receipt.json"))]
      (u/chk (and (= "amu.run-receipt.v1" (u/geti receipt "schema")) (= 0 (u/geti receipt "exit"))) receipt)
      (u/chk (= (u/sha256-hex (.read_bytes hello)) (u/geti receipt "source")) receipt)
      (u/chk (= (u/sha256-hex (b "42\n")) (u/geti receipt "stdout")) receipt)
      (u/chk (every? #(= 64 (count (u/geti receipt %))) ["compiler" "packager" "program"]) receipt))
    (let [kept (.read_bytes (.joinpath out "run-receipt.json"))]
      (run "run-receipt-exists" ["run" (.-name hello) "--receipt" "run-receipt.json"] :expected 1 :diagnostic (b "ERECEIPT"))
      (u/chk (u/deq (.read_bytes (.joinpath out "run-receipt.json")) kept)))
    (let [first-bytes (.read_bytes (.joinpath out "hello"))]
      (.write_text hello "(ns hello (:export [main]))\n(defn main [] :i64 43)\n")
      (run-ok "changed-source" ["run" (.-name hello)] (b "43\n"))
      (run-ok "old-artifact-independent" ["run" "./hello"] (b "42\n"))
      (run "compile-explicit" ["compile" (.-name hello) "-o" "hello43"])
      (run-ok "run-43-artifact" ["run" "hello43"] (b "43\n"))
      (u/chk (not (u/deq (.read_bytes (.joinpath out "hello43")) first-bytes)))
      (run "preserve-output" ["compile" (.-name hello) "-o" "hello"] :expected 1 :diagnostic (b "EOUTPUT"))
      (u/chk (u/deq (.read_bytes (.joinpath out "hello")) first-bytes))
      (let [nested (.joinpath out "space 日本語")
            _ (.mkdir nested)
            unicode-source (.joinpath nested "試験.kotoba")]
        (.write_bytes unicode-source (.read_bytes hello))
        (run-ok "unicode-check" ["check" unicode-source] (b "ok\n"))
        (run "unicode-compile" ["compile" unicode-source "--output" (.joinpath nested "native 実行")])
        (run-ok "unicode-run" ["run" (.joinpath nested "native 実行")] (b "43\n"))
        (doseq [[i value] (map-indexed vector [0 -1 256 9223372036854775807 -9223372036854775808])]
          (let [p (source (str "integer" i) (str "(defn main [] :i64 " value ")"))]
            (run-ok (str "integer" i) ["run" (.-name p)] (b (str value "\n")))))
        (let [scoped (source "scoped" "(defn main [] :i64 (arena-scope (+ (arena-scope 40) 2)))")]
          (run-ok "scoped-result" ["run" (.-name scoped)] (b "42\n")))
        (doseq [[name body] [["string" "(defn main [] :string \"hello\")"]
                             ["bool" "(defn main [] :bool true)"]
                             ["parameter" "(defn main [x :i64] :i64 x)"]
                             ["no-main" "(defn other [] :i64 42)"]
                             ["invalid" "(defn main [] :i64 \"bad\")"]
                             ["trailing-reader-discard" "(defn main [] :string \"bad\")\n#_"]]]
          (let [p (source name body)]
            (run (str "reject-" name) ["compile" (.-name p) "-o" (str name ".out")] :expected 1 :diagnostic (b "EABI"))
            (u/chk (not (.exists (.joinpath out (str name ".out")))))))
        (let [bad (source "bad" "(defn main [] :i64 \"bad\")")]
          (run "check-type-error" ["check" (.-name bad)] :expected 1 :diagnostic (b "E")))
        (doseq [[i args] (map-indexed vector [["compile" (.-name hello) "--target" "x86_64-linux"]
                                              ["check" (.-name hello) "--source-path"]
                                              ["check" (.-name hello) "--source-path" "." "--source-lock" "x.ksl"]
                                              ["compile" (.-name hello) "-o"] ["garbage" (.-name hello)]
                                              ["run" (.-name hello) "--receipt"]
                                              ["run" (.-name hello) "--receipt" "r.json" "extra"]])]
          (run (str "usage" i) args :expected 2 :diagnostic (b "usage:")))
        (run "project-run-missing-lock" ["run" (.-name hello) "--source-lock" "missing"]
             :expected 1 :diagnostic (b "EINPUT expected a bounded regular source lock"))
        ;; removed with the C loader (docs/c-loader-removal.md): refused by name, not as unknown (JUN-282)
        (doseq [name ["measure-runtime" "package-ios" "package-macos" "test"]]
          (run (str "removed-" name) [name (.-name hello)] :expected 2 :diagnostic (b (str "EREMOVED " name))))
        (doseq [[name path] [["missing" (.joinpath out "missing.kotoba")] ["directory" nested]]]
          (run name ["run" path] :expected 1 :diagnostic (b "EINPUT")))
        (let [link (.joinpath out "link.kotoba")]
          (.symlink_to link hello)
          (run "symlink" ["check" (.-name link)] :expected 1 :diagnostic (b "EINPUT")))
        (let [fifo (.joinpath out "fifo.kotoba")]
          (os/mkfifo fifo)
          (run "fifo" ["check" (.-name fifo)] :expected 1 :diagnostic (b "EINPUT")))
        (let [big (.joinpath out "big.kotoba")
              f (.open big "wb")]
          (try (.truncate f 1048577) (finally (.close f)))
          (run "oversize" ["check" (.-name big)] :expected 1 :diagnostic (b "EINPUT")))
        (doseq [[i at] (map-indexed vector [0 1024 (dec (python/len first-bytes))])]
          (let [changed (python/bytearray first-bytes)
                p (.joinpath out (str "tampered" i))]
            (operator/setitem changed at (bit-xor (operator/getitem changed at) 1))
            (.write_bytes p changed)
            (run (str "tampered" i) ["run" (.-name p)] :expected 1 :diagnostic (b "EARTIFACT"))))
        (let [p (source "args" "(defn main [] :i64 (let [w (typed-cap-call :io/write :string :string (typed-cap-call :cli/args :string :string \"0\"))] 42))")]
          (run "guest-argv" ["run" (.-name p) "--" "hello 日本語"] :stdout (b "hello 日本語42\n")))
        (doseq [[name cap kind payload] [["fs" ":fs/app-data-bytes" ":bytes" "(bytes-from-vector-i64 [0 70 83 50 0 65 120 0])"]
                                         ["process" ":process/spawn" ":string" "\"anything\""]]]
          (let [p (source (str "deny-" name) (str "(defn main [] :i64 (let [r (typed-cap-call " cap " " kind " " kind " " payload ")] 42))"))
                r (subprocess/run (python/list (map str [cli "run" p])) ** :cwd out :capture_output true :timeout 150)]
            (.write_bytes (.joinpath out (str "denied-" name ".stdout")) (.-stdout r))
            (.write_bytes (.joinpath out (str "denied-" name ".stderr")) (.-stderr r))
            (u/chk (and (not (zero? (.-returncode r))) (not (u/deq (.-stdout r) (b "42\n")))) name)
            (.append calls (u/pydict "name" (str "guest-grant-denied-" name) "exit" (.-returncode r)))))
        (let [lp (source "loop" "(defn main [] :i64 (loop [i 0] (recur (+ i 1))))")]
          (run "deadline" ["run" (.-name lp)] :expected 124 :diagnostic (b "ETIME")))
        ;; Caller-controlled program bytes are recompiled and compared, never exec'd.
        (let [marker (.joinpath out "must-not-execute")
              fake (.joinpath out "untrusted")]
          (.write_bytes fake (operator/add (operator/add (b "#!/bin/sh\ntouch ") (b (str marker))) (b "\n")))
          (.chmod fake 0700)
          (run "untrusted-executable" ["run" fake] :expected 1 :diagnostic (b "EINPUT"))
          (u/chk (not (.exists marker))))
        (let [isolated (.joinpath out "provenance")
              _ (.mkdir isolated)
              isolated-cli (.joinpath isolated "amu-cli.macho")
              cli-dir (.-parent (.resolve cli))]
          (shutil/copy2 (.resolve cli) isolated-cli)
          (run "missing-compiler" ["check" hello] :expected 70 :diagnostic (b "EPROVENANCE") :image isolated-cli)
          (doseq [name ["amu-full-root.macho" "kotoba-packager-root.macho"]]
            (shutil/copy2 (.joinpath cli-dir name) (.joinpath isolated name))
            (let [f (.open (.joinpath isolated name) "r+b")]
              (try
                (let [first-byte (.read f 1)]
                  (.seek f 0)
                  (.write f (python/bytes [(bit-xor (operator/getitem first-byte 0) 1)])))
                (finally (.close f))))
            (run (str "corrupted-" name) ["check" hello] :expected 70 :diagnostic (b "EPROVENANCE") :image isolated-cli)
            (shutil/copy2 (.joinpath cli-dir name) (.joinpath isolated name))))))
    (u/chk (u/deq (tmp-amu) before-tmp) "private CLI directories leaked")
    (let [result (u/pydict "schema" "amu.macos-cli-product-observation.v1" "status" "PASS_ORDINARY_MACOS_CLI"
                           "cli" (mac/pin cli) "calls" calls "manualFD3" false "hostedFallback" false
                           "nativeResults" (python/list [42 43]) "nativeBuildRequired" true "independentUserQualified" false)]
      (.write_text (.joinpath out "cli-product.json") (u/json-dump result))
      (println (u/geti result "status") (python/len calls) "native observations"))))
