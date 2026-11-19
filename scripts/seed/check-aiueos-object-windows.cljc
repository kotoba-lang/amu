;; The aiueos kernel object route's u8 / u16 / u64 window accesses (JUN-556 B).
;;
;; Compiles one object whose six exports use kernel-load-u8, kernel-store-u8, kernel-load-u16, kernel-store-u16,
;; kernel-load-u64 and kernel-store-u64, and reads each inlined window back with the decoder in aiueos_object_lib
;; (this script stages and observes; it emits nothing). For each access the decoder requires, in order:
;;   cmp rcx,512; ja TRAP; test rdx,rdx; jz TRAP; cmp INDEX,rcx; jae TRAP;
;;   [width > 1: mov rsi,rcx; sub rsi,INDEX; cmp rsi,WIDTH; jl TRAP;
;;               test INDEX,WIDTH-1; ja TRAP;]
;;   ACCESS; jmp +2; TRAP: ud2
;; and that every branch lands exactly on that ud2, so no path reaches the access unless the base is non-null, the
;; length is at most 512, the index is below the length, the access fits (index + width <= length without wrapping)
;; and, above one byte, the index is aligned. These are the sequences of kotoba-native's x86_64.cljk
;; (`emit-kernel-load-u8`, `emit-kernel-store-u8`, `emit-memwidth-window`), with the operands read from their frame
;; slots as the plain u32 pair does.
;;
;; Refusals: a base that is not a rooted parameter, and a length that is not the region's own length, are refused
;; (E7106) for the new accesses as for the old.
;; Not shown: the machine code was decoded, not executed; no emitted object has run in a kernel.
;; Ported from check-aiueos-object-windows.py (Basilisp, JUN-974).
;; Run: basilisp run -p scripts/seed scripts/seed/check-aiueos-object-windows.cljc -- --compiler C --output DIR
(ns check-aiueos-object-windows
  (:require [basilisp.string :as str]
            [aiueos-object-lib :as lib]
            [gate-util :as u]
            [macos-native-lib :as mac])
  (:import sys))

(def expected [["load" 1] ["store" 1] ["load" 2] ["store" 2] ["load" 8] ["store" 8]])
(def refusals
  [["unrooted-base" "(ns refused (:export [f]))\n(defn f [b :i64 n :i64 i :i64] :i64 (kernel-load-u8 (+ b 1) n i))\n"]
   ["free-length" "(ns refused (:export [f]))\n(defn f [b :i64 n :i64 i :i64 v :i64] :i64 (kernel-store-u64 b 16 i v))\n"]
   ["unrooted-base-store16" "(ns refused (:export [f]))\n(defn f [b :i64 n :i64 i :i64 v :i64] :i64 (kernel-store-u16 (+ b 2) n i v))\n"]])

(defn main [compiler output]
  (lib/start! compiler output)
  (let [[_ obj] (lib/compile-source compiler output "w" lib/widths-source)
        text (lib/text-section obj)
        found (mapv second (lib/windows text 512))
        _ (when (not= found expected) (mac/fail (str "windows " found ", want " expected)))
        report (u/pydict "windows" (python/list (for [[k w] found] (u/pydict "kind" k "width" w)))
                         "object" (lib/sha-of obj))]
    (lib/check-refusals! compiler output (u/pydict) refusals "E7106")
    (.__setitem__ report "refused" (python/list (map first refusals)))
    (lib/emit! output report "PASS_AIUEOS_OBJECT_WINDOWS")))

(defn -main [& args] (lib/cli-main args main))

(when (some #(or (= % "check-aiueos-object-windows.cljc") (str/ends-with? % "/check-aiueos-object-windows.cljc")) sys/argv)
  (apply -main *command-line-args*))
