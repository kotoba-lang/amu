;; Native f32 / f64 on the aiueos kernel object route (JUN-633 slice 3, ADR 0391).
;;
;; seed/70-x86_64-linux.kotoba emits scalar SSE for the float SIR codes and seed/74's xo-check-sir admits them on the
;; object artifact only. A float is its bit pattern in an i64 slot (an f32 sign-extended from 32 bits). Compiles with a
;; native Amu compiler and checks (this script stages and observes; it emits nothing):
;;
;; * fops: one object exporting every admitted operation behind an op selector (the source of
;;   docs/evidence/f32-sse-20261030/fops.kotoba), whose text carries each operation's instruction exactly once
;;   (addss subss mulss divss and the sd forms, sqrtss / sqrtsd, cvtsi2ss / cvtsi2sd, cvtsd2ss / cvtss2sd, six
;;   ucomiss and seven ucomisd (six comparisons plus the NaN test of the f64-to-bits prelude, JUN-846), two setnp for
;;   the two eq, btc / btr rax,63 for f64 neg / abs) and no minss / maxss / cvttss2si / cvttsd2si;
;; * trap: f32-from-bits is this route's definition, an out-of-range pattern reaching ud2 rather than a vector access;
;; * unchanged: the 512-byte width object keeps its pinned SHA-256 (an integer object's bytes do not move);
;; * refused, nothing written: f32-min / f64-max and f64 -> i64 truncation (E7101), and an export whose parameter or
;;   result is a float (System V would pass it in an xmm register): E7102, or the shared check stage's E2104 before it.
;;   f32 -> i64 truncation is admitted since slice 7 (ADR 0395); check-aiueos-object-f2i covers it.
;;
;; Not shown here: execution. docs/evidence/f32-sse-20261030/ runs fops under QEMU against the same operations in C.
;; Ported from check-aiueos-object-f32.py (Basilisp, JUN-974).
;; Run: basilisp run -p scripts/seed scripts/seed/check-aiueos-object-f32.cljc -- --compiler C --output DIR
(ns check-aiueos-object-f32
  (:require [basilisp.string :as str]
            [aiueos-object-lib :as lib]
            [gate-util :as u]
            [macos-native-lib :as mac])
  (:import sys))

(def fops (.joinpath u/root "docs/evidence/f32-sse-20261030/fops.kotoba"))
(def expected
  [["addss" "f30f5885" 1] ["subss" "f30f5c85" 1] ["mulss" "f30f5985" 1] ["divss" "f30f5e85" 1]
   ["addsd" "f20f5885" 1] ["subsd" "f20f5c85" 1] ["mulsd" "f20f5985" 1] ["divsd" "f20f5e85" 1]
   ["sqrtss" "f30f5185" 1] ["sqrtsd" "f20f5185" 1]
   ["cvtsi2ss" "f3480f2a85" 1] ["cvtsi2sd" "f2480f2a85" 1] ["cvtsd2ss" "f20f5a85" 1] ["cvtss2sd" "f30f5a85" 1]
   ["ucomisd" "660f2e85" 7] ["setnp-cl" "0f9bc1" 2]
   ["btc-rax-63" "480fbaf83f" 1] ["btr-rax-63" "480fbaf03f" 1]
   ["minss" "f30f5d" 0] ["maxss" "f30f5f" 0] ["minsd" "f20f5d" 0] ["maxsd" "f20f5f" 0]
   ["cvttss2si" "f3480f2c" 0] ["cvttsd2si" "f2480f2c" 0]])
(def trap
  (str "(ns t (:export [kotoba_aiueos_t]))\n"
       "(defn kotoba_aiueos_t [x :i64] :i64 (f32-to-bits (f32-from-bits x)))\n"))
(def refusals
  [["f32-min" "(ns r (:export [f]))\n(defn f [x :i64] :i64 (f32-to-bits (f32-min (f32-from-bits x) (f32-from-bits x))))\n" ["E7101"]]
   ["f64-max" "(ns r (:export [f]))\n(defn f [x :i64] :i64 (f64-to-bits (f64-max (f64-from-bits x) (f64-from-bits x))))\n" ["E7101"]]
   ["f64-to-i64" "(ns r (:export [f]))\n(defn f [x :i64] :i64 (f64-to-i64-truncating (f64-from-bits x)))\n" ["E7101"]]
   ["export-f32-param" "(ns r (:export [f]))\n(defn f [x :f32] :i64 (f32-to-bits x))\n" ["E7102" "E2104"]]
   ["export-f64-result" "(ns r (:export [f]))\n(defn f [x :i64] :f64 (f64-from-bits x))\n" ["E7102" "E2104"]]])

(defn main [compiler output]
  (lib/start! compiler output)
  (let [report (u/pydict)
        [_ obj] (lib/compile-source compiler output "fops" (.read_text fops))
        text (lib/text-section obj)
        found (u/pydict-from (for [[name seq _] expected] [name (.count text (u/hex->bytes seq))]))
        _ (.__setitem__ found "ucomiss" (- (.count text (u/hex->bytes "0f2e85")) (u/geti found "ucomisd")))
        want (u/pydict-from (concat (for [[name _ n] expected] [name n]) [["ucomiss" 6]]))
        _ (when-not (u/deq found want) (mac/fail (str "float sequences " (python/dict found))))
        _ (.__setitem__ report "fops" (u/pydict "sequences" found "sha256" (lib/sha-of obj)))
        [_ obj] (lib/compile-source compiler output "trap" trap)
        text (lib/text-section obj)
        ;; the range check: cmp against INT32_MIN / INT32_MAX feeding (assert ...)'s ud2, and no runtime vector call
        _ (when (or (< (.count text (u/hex->bytes "0f0b")) 2) (not (u/has-bytes? (u/hex->bytes "ffffff7f") text)))
            (mac/fail "f32-from-bits carries no range trap"))
        _ (.__setitem__ report "trap" (lib/sha-of obj))]
    (lib/check-widths-unchanged! compiler output report)
    (doseq [[name src codes] refusals]
      (let [[result obj] (lib/compile-source compiler output name src 1)
            message (lib/message-of result)
            hit (vec (filter #(.__contains__ message %) codes))]
        (when (or (empty? hit) (.exists obj))
          (mac/fail (str name " was not refused with " codes " and no output: " message)))
        (.__setitem__ report name (str "refused " (first hit)))))
    (lib/emit! output report "PASS_AIUEOS_OBJECT_F32")))

(defn -main [& args] (lib/cli-main args main))

(when (some #(or (= % "check-aiueos-object-f32.cljc") (str/ends-with? % "/check-aiueos-object-f32.cljc")) sys/argv)
  (apply -main *command-line-args*))
