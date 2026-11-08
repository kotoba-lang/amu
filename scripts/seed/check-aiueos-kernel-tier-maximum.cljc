;; A kernel window access above its tier's maximum is refused at compile time (JUN-483).
;;
;; The kernel memory intrinsics trap at run time (ud2) when their size operand is above the tier maximum: 512 for the
;; plain forms, 4096 for -4k, 16384 for -16k, 65536 for -64k (seed/86 km-maximum). When that size is a literal,
;; km-check now refuses the call with E7108 naming the intrinsic, the size and the maximum, instead of compiling a
;; function that can only reach its ud2. Compiles with a native Amu compiler on the aiueos object route, over the
;; object's own .bss / .high_bss arrays (whose literal extent is known):
;;
;; * object route (seed/74): the plain and 16 KiB windows at exactly their maximum compile; at twice the maximum they
;;   are refused (E7108 with the intrinsic's name, the size and the maximum; nothing written), loads and stores, u8 to
;;   u64;
;; * not exercised here: the kernel-image route (seed/86 km-check, all four tiers including -4k and -64k), whose
;;   source-locked multi-module compile needs the Linux producers of check-aiueos-owned-page-native;
;; * unchanged: E7106 for a length that is not the region's own, and an object without arrays is byte-identical to
;;   check-aiueos-object-exports's pinned one-export object.
;;
;; A size tied to a parameter keeps the run-time check; this gate does not change that.
;; Ported from check-aiueos-kernel-tier-maximum.py (Basilisp, JUN-974).
;; Run: basilisp run -p scripts/seed scripts/seed/check-aiueos-kernel-tier-maximum.cljc -- --compiler C --output DIR
(ns check-aiueos-kernel-tier-maximum
  (:require [basilisp.string :as str]
            [aiueos-object-lib :as lib]
            [gate-util :as u]
            [macos-native-lib :as mac])
  (:import sys))

(defn source [array size call]
  (str "(ns t (:export [f]))\n(defn- " array "-addr-0-" size " [] :i64 0)\n(defn f [i :i64 v :i64] :i64 " call ")\n"))
;; object route (seed/74 xk-check): its windows have the plain and 16 KiB tiers; (intrinsic, maximum, array section)
(def tiers [["kernel-store-u8" 512 "bss"] ["kernel-load-u8" 512 "bss"] ["kernel-load-u32" 512 "bss"]
            ["kernel-store-u64" 512 "bss"]
            ["kernel-store-u16-16k" 16384 "highbss"] ["kernel-load-u8-16k" 16384 "highbss"]
            ["kernel-load-u32-16k" 16384 "highbss"]])
(defn call [intrinsic array size]
  (let [base (str "(" array "-addr-0-" size ")")]
    (if (.__contains__ intrinsic "store")
      (str "(" intrinsic " " base " " size " i v)")
      (str "(" intrinsic " " base " " size " i)"))))

(defn main [compiler output]
  (lib/start! compiler output)
  (let [report (u/pydict)]
    (doseq [[intrinsic maximum array] tiers]
      (let [slug (.replace intrinsic "kernel-" "")
            [_ ok] (lib/compile-source compiler output (str slug "-at-max") (source array maximum (call intrinsic array maximum)))
            _ (when-not (.exists ok) (mac/fail (str intrinsic " at its maximum " maximum ": no object")))
            over (* maximum 2)
            [result bad] (lib/compile-source compiler output (str slug "-over") (source array over (call intrinsic array over)) 1)
            text (lib/message-of result)
            want (str "E7108 " intrinsic " size " over " is above its tier maximum " maximum)]
        (when (or (.exists bad) (not (.__contains__ text want)))
          (mac/fail (str intrinsic " size " over ": want '" want "' and no output, got " (pr-str (subs text (max 0 (- (count text) 300)))))))
        (.__setitem__ report intrinsic (u/pydict "atMaximum" maximum "refused" over))))
    (let [[result bad] (lib/compile-source compiler output "wrong-literal"
                                           (source "bss" 64 "(kernel-load-u8 (bss-addr-0-64) 128 i)") 1)]
      (when (or (.exists bad) (not (.__contains__ (lib/message-of result) "E7106")))
        (mac/fail "a length other than the region's own is no longer E7106"))
      (.__setitem__ report "wrongLiteral" "refused E7106"))
    (let [[_ one] (lib/compile-source compiler output "one" lib/one-source)]
      (when (not= (lib/sha-of one) lib/one-sha256) (mac/fail "an object without arrays changed its bytes"))
      (.__setitem__ report "withoutArrays" "byte-identical"))
    (lib/emit! output report "PASS_AIUEOS_KERNEL_TIER_MAXIMUM")))

(defn -main [& args] (lib/cli-main args main))

(when (some #(or (= % "check-aiueos-kernel-tier-maximum.cljc") (str/ends-with? % "/check-aiueos-kernel-tier-maximum.cljc")) sys/argv)
  (apply -main *command-line-args*))
