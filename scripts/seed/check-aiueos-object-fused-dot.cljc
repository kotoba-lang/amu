;; The aiueos kernel object route's fused f32 reductions (JUN-633 slice 6, ADR 0394).
;;
;; kernel-dot-f32 [a a-len b b-len count] and kernel-dequant-dot-ptq1-0 [weights w-len input i-len blocks] are ids 30
;; and 31 of seed/74-x86_64-aiueos-object.kotoba. Compiles with a native Amu compiler and checks (this script stages
;; and observes; it emits nothing):
;;
;; * each object carries its guards (both lengths against 0x10000, the count against 0x4000 / the blocks against
;;   0x80), the cpuid / xgetbv arm choice once, both arms (AVX2: vhaddps x2 and vzeroupper; scalar: the
;;   (l0+l1)+(l2+l3) reduction once) and, for PTQ1_0, sixteen eight-lane groups in the AVX2 arm;
;; * opt-in: the pause gate's object, which does not name the block, keeps the bytes it had before the block existed,
;;   and the 512-byte width object keeps its pinned SHA-256;
;; * refused, nothing written: either builtin called with four or six arguments (E2103), and a window whose length is
;;   computed rather than its owner's length parameter (E7106) -- the rooted-base rule holds for both windows.
;;
;; Not shown here: execution. docs/evidence/fused-dot-20261031/ runs both objects under QEMU against the
;; kotoba-compiler/1 object they replace.
;; Ported from check-aiueos-object-fused-dot.py (Basilisp, JUN-974).
;; Run: basilisp run -p scripts/seed scripts/seed/check-aiueos-object-fused-dot.cljc -- --compiler C --output DIR
(ns check-aiueos-object-fused-dot
  (:require [basilisp.string :as str]
            [aiueos-object-lib :as lib]
            [gate-util :as u]
            [macos-native-lib :as mac])
  (:import sys))

;; the pause object's SHA-256 under slice 5 (amu fd84f7e9, unchanged on main 4ece027c): the new block must leave it
(def pause-sha256 "c24f9c962e000ead3c1672975f74f941960c169d9c22bfe824a89a3c7a909403")
(def dot
  (str "(ns fdot (:export [kotoba_aiueos_dot_f32]))\n"
       "(defn kotoba_aiueos_dot_f32 [a :i64 an :i64 b :i64 bn :i64 c :i64] :i64 (kernel-dot-f32 a an b bn c))\n"))
(def ptq1
  (str "(ns fptq1 (:export [kotoba_aiueos_dequant_dot_ptq1_0]))\n"
       "(defn kotoba_aiueos_dequant_dot_ptq1_0 [w :i64 wn :i64 x :i64 xn :i64 c :i64] :i64 (kernel-dequant-dot-ptq1-0 w wn x xn c))\n"))
(def guard (u/hex->bytes "31c031c90fa283f807"))   ; xor eax,eax; xor ecx,ecx; cpuid; cmp eax,7
(def xgetbv (u/hex->bytes "31c90f01d0"))
(def common [["span-a" "4881f900000100"] ["span-b" "4881fa00000100"] ["vhaddps" "c5fb7cc0c5fb7cc0"]
             ["vzeroupper" "c5f877"] ["scalar-tree" "f30f58c1f30f58d3f30f58c2"]])
(def limit {"dot" "483d00400000" "ptq1" "483d80000000"})
(def lanes-seq (u/hex->bytes "c5f858c1c5f858c2"))   ; vaddps xmm0 += lower half, then upper half
(def refusals
  [["dot-four" "(ns r (:export [f]))\n(defn f [a :i64 b :i64] :i64 (kernel-dot-f32 a 64 b 64))\n" "E2103"]
   ["dot-six" "(ns r (:export [f]))\n(defn f [a :i64 an :i64 b :i64 bn :i64] :i64 (kernel-dot-f32 a an b bn 8 0))\n" "E2103"]
   ["ptq1-four" "(ns r (:export [f]))\n(defn f [a :i64 b :i64] :i64 (kernel-dequant-dot-ptq1-0 a 28 b 512))\n" "E2103"]
   ["ptq1-six" (str "(ns r (:export [f]))\n(defn f [a :i64 an :i64 b :i64 bn :i64] :i64 "
                    "(kernel-dequant-dot-ptq1-0 a an b bn 1 0))\n") "E2103"]
   ["dot-computed-length" (str "(ns r (:export [f]))\n(defn f [a :i64 an :i64 b :i64 bn :i64 c :i64] :i64 "
                               "(kernel-dot-f32 a (* c 4) b (* c 4) c))\n") "E7106"]
   ["ptq1-computed-length" (str "(ns r (:export [f]))\n(defn f [a :i64 an :i64 b :i64 bn :i64 c :i64] :i64 "
                                "(kernel-dequant-dot-ptq1-0 a an b (* c 512) c))\n") "E7106"]])

(defn main [compiler output]
  (lib/start! compiler output)
  (let [report (u/pydict)]
    (doseq [[name src lanes] [["dot" dot 1] ["ptq1" ptq1 16]]]
      (let [[_ obj] (lib/compile-source compiler output name src)
            text (lib/text-section obj)
            found (u/pydict-from (for [[k hex] common] [k (.count text (u/hex->bytes hex))]))
            _ (doseq [[k v] [["guard" (.count text guard)] ["xgetbv" (.count text xgetbv)]
                             ["limit" (.count text (u/hex->bytes (get limit name)))] ["lanes" (.count text lanes-seq)]]]
                (.__setitem__ found k v))
            want (u/pydict-from (concat (for [[k _] common] [k 1]) [["guard" 1] ["xgetbv" 1] ["limit" 1] ["lanes" lanes]]))]
        (when-not (u/deq found want)
          (mac/fail (str name " sequence " (python/dict found) ", expected " (python/dict want))))
        (.__setitem__ report name (u/pydict "sequence" found "textBytes" (python/len text) "sha256" (lib/sha-of obj)))))
    (let [[_ obj] (lib/compile-source compiler output "pause" lib/pause-source)
          digest (lib/sha-of obj)]
      (when (or (u/has-bytes? guard (lib/text-section obj)) (not= digest pause-sha256))
        (mac/fail (str "the pause object changed or carries the block: " digest)))
      (.__setitem__ report "optIn" digest))
    (lib/check-widths-unchanged! compiler output report)
    (doseq [[name src code] refusals]
      (lib/check-refusals! compiler output report [[name src]] code))
    (lib/emit! output report "PASS_AIUEOS_OBJECT_FUSED_DOT")))

(defn -main [& args] (lib/cli-main args main))

(when (some #(or (= % "check-aiueos-object-fused-dot.cljc") (str/ends-with? % "/check-aiueos-object-fused-dot.cljc")) sys/argv)
  (apply -main *command-line-args*))
