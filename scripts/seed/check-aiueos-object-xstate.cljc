;; The aiueos kernel object route's extended-state setup (JUN-633 slice 2, ADR 0390).
;;
;; kernel-cr4-set-bits [mask], kernel-xcr0-set-bits [mask], kernel-read-cr4 [] and kernel-xgetbv [] are ids 24..27 of
;; seed/74-x86_64-aiueos-object.kotoba. The two writes OR a LITERAL mask into the register; the verifier admits only
;; CR4 OSFXSR / OSXMMEXCPT / OSXSAVE (0x40600) and XCR0 x87 / SSE / AVX (0x7). Compiles with a native Amu compiler and
;; checks (this script stages and observes; it emits nothing):
;;
;; * four: one object exporting the four, each body carrying exactly its sequence --
;;     cr4-set-bits:  mov rcx,[mask]; mov rax,cr4; or rax,rcx; mov cr4,rax
;;     xcr0-set-bits: mov rsi,[mask]; xor ecx,ecx; xgetbv; or rax,rsi; xsetbv; shl rdx,32; or rax,rdx
;;     read-cr4:      mov rax,cr4
;;     xgetbv:        xor ecx,ecx; xgetbv; shl rdx,32; or rax,rdx
;; * unchanged: the 512-byte width object keeps its pinned SHA-256;
;; * refused E7107, nothing written: a CR4 bit outside the set (PGE), an XCR0 bit outside it (bit 3), a mask that is a
;;   parameter rather than a literal, and a zero mask.
;;
;; Not shown here: execution. docs/evidence/xstate-intrinsics-20261030/ runs the four under QEMU against inline-asm C.
;; Ported from check-aiueos-object-xstate.py (Basilisp, JUN-974).
;; Run: basilisp run -p scripts/seed scripts/seed/check-aiueos-object-xstate.cljc -- --compiler C --output DIR
(ns check-aiueos-object-xstate
  (:require [basilisp.string :as str]
            [aiueos-object-lib :as lib]
            [gate-util :as u]
            [macos-native-lib :as mac])
  (:import json pathlib sys))

(def source
  (str "(ns xs (:export [cr4on xcr0on rc xg]))\n"
       "(defn cr4on [] :i64 (kernel-cr4-set-bits 263680))\n"
       "(defn xcr0on [] :i64 (kernel-xcr0-set-bits 7))\n"
       "(defn rc [] :i64 (kernel-read-cr4))\n"
       "(defn xg [] :i64 (kernel-xgetbv))\n"))
(def cr4-set (str "0f20e0" "4809c8" "0f22e0"))
(def xcr0-set (str "31c9" "0f01d0" "4809f0" "0f01d1" "48c1e220" "4809d0"))
(def xgetbv (str "31c9" "0f01d0" "48c1e220" "4809d0"))
(def refusals
  [["cr4-pge" "(ns r (:export [f]))\n(defn f [] :i64 (kernel-cr4-set-bits 128))\n"]
   ["xcr0-bit3" "(ns r (:export [f]))\n(defn f [] :i64 (kernel-xcr0-set-bits 8))\n"]
   ["mask-parameter" "(ns r (:export [f]))\n(defn f [m :i64] :i64 (kernel-cr4-set-bits m))\n"]
   ["mask-zero" "(ns r (:export [f]))\n(defn f [] :i64 (kernel-xcr0-set-bits 0))\n"]])

(defn main [compiler output]
  (mac/verify-macho compiler)
  (.mkdir output ** :parents false :mode 0700 :exist_ok false)
  (let [report (u/pydict)
        [_ obj] (lib/compile-source compiler output "xstate" source)
        text (.hex (lib/text-section obj))
        found (u/pydict "cr4-set-bits" (.count text cr4-set) "xcr0-set-bits" (.count text xcr0-set)
                        "xgetbv" (.count text xgetbv) "mov-from-cr4" (.count text "0f20e0")
                        "mov-to-cr4" (.count text "0f22e0") "xsetbv" (.count text "0f01d1"))
        _ (when-not (u/deq found (u/pydict "cr4-set-bits" 1 "xcr0-set-bits" 1 "xgetbv" 1 "mov-from-cr4" 2 "mov-to-cr4" 1 "xsetbv" 1))
            (mac/fail (str "extended-state sequences " (json/dumps found))))
        _ (.__setitem__ report "four" (u/pydict "sequences" found "sha256" (lib/sha-of obj)))
        [_ obj] (lib/compile-source compiler output "widths" lib/widths-source)
        digest (lib/sha-of obj)
        _ (when (not= digest lib/widths-sha256) (mac/fail (str "the 512-byte width object changed: " digest)))
        _ (.__setitem__ report "widthsUnchanged" digest)]
    (doseq [[name src] refusals]
      (let [[result obj] (lib/compile-source compiler output name src 1)
            message (lib/message-of result)]
        (when (or (not (.__contains__ message "E7107")) (.exists obj))
          (mac/fail (str name " was not refused with E7107 and no output: " message)))
        (.__setitem__ report name "refused E7107")))
    (.write_text (.joinpath output "report.json") (u/json-dump report))
    (println (str "PASS_AIUEOS_OBJECT_XSTATE " (json/dumps report ** :sort_keys true)))
    (.flush sys/stdout)))

(defn -main [& args]
  (main (.resolve (pathlib/Path (or (u/opt args "--compiler") (sys/exit "--compiler is required"))) ** :strict true)
        (.resolve (pathlib/Path (or (u/opt args "--output") (sys/exit "--output is required"))))))

(when (some #(or (= % "check-aiueos-object-xstate.cljc") (str/ends-with? % "/check-aiueos-object-xstate.cljc")) sys/argv)
  (apply -main *command-line-args*))
