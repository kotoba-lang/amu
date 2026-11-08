;; The aiueos kernel object route's 16 KiB tier for u8 / u16 / u64 window accesses (JUN-556 C).
;;
;; kernel-<load|store>-<u8|u16|u64>-16k are the accesses of check-aiueos-object-windows with the length bound 16384
;; instead of 512 (the tier kernel-load-u32-16k already has). Compiles with a native Amu compiler and decodes every
;; inlined window with a decoder written in aiueos_object_lib (this script stages and observes; it emits nothing):
;;
;;   cmp rcx,BOUND; ja TRAP; test rdx,rdx; jz TRAP; cmp INDEX,rcx; jae TRAP;
;;   [width > 1: mov rsi,rcx; sub rsi,INDEX; cmp rsi,WIDTH; jl TRAP; test INDEX,WIDTH-1; ja TRAP;]
;;   ACCESS; jmp +2; TRAP: ud2
;;
;; with every branch landing on that ud2.
;;
;; * six-16k: one object with the six 16 KiB accesses, in order, each with BOUND 16384;
;; * mixed: the 512-byte and the 16 KiB u8 load in one object keep their own bounds (the ids stay positional);
;; * unchanged: the object of check-aiueos-object-windows's source is byte-identical to the one the 512-byte tier has
;;   always produced (its SHA-256 is pinned in aiueos_object_lib), so no object that does not name a 16 KiB stub changes;
;; * refused (E7106, nothing written): a base that is not rooted, and a length that is not the region's own.
;;
;; Not shown here: execution. docs/evidence/windows16-20261030/ ran the six-16k object under QEMU by hand.
;; Ported from check-aiueos-object-windows16.py (Basilisp, JUN-974).
;; Run: basilisp run -p scripts/seed scripts/seed/check-aiueos-object-windows16.cljc -- --compiler C --output DIR
(ns check-aiueos-object-windows16
  (:require [basilisp.string :as str]
            [aiueos-object-lib :as lib]
            [gate-util :as u]
            [macos-native-lib :as mac])
  (:import json pathlib sys))

(def mixed
  (str "(ns mixed (:export [f g]))\n"
       "(defn f [b :i64 n :i64 i :i64] :i64 (kernel-load-u8 b n i))\n"
       "(defn g [b :i64 n :i64 i :i64] :i64 (kernel-load-u8-16k b n i))\n"))
(def expected [["load" 1] ["store" 1] ["load" 2] ["store" 2] ["load" 8] ["store" 8]])
(def refusals
  [["unrooted-base" "(ns refused (:export [f]))\n(defn f [b :i64 n :i64 i :i64] :i64 (kernel-load-u8-16k (+ b 1) n i))\n"]
   ["free-length" "(ns refused (:export [f]))\n(defn f [b :i64 n :i64 i :i64 v :i64] :i64 (kernel-store-u64-16k b 16 i v))\n"]])

(defn main [compiler output]
  (mac/verify-macho compiler)
  (.mkdir output ** :parents false :mode 0700 :exist_ok false)
  (let [report (u/pydict)
        [_ obj] (lib/compile-source compiler output "widths16" lib/source16)
        text (lib/text-section obj)
        found (mapv second (lib/windows text 16384))
        _ (when (or (not= found expected) (seq (lib/windows text 512)))
            (mac/fail (str "16 KiB windows " found ", 512-byte windows " (lib/windows text 512))))
        _ (.__setitem__ report "six16k" (u/pydict "windows" (count found) "sha256" (lib/sha-of obj)))
        [_ obj] (lib/compile-source compiler output "mixed" mixed)
        text (lib/text-section obj)
        small (lib/windows text 512)
        large (lib/windows text 16384)
        _ (when (or (not= (mapv second small) [["load" 1]]) (not= (mapv second large) [["load" 1]])
                    (> (first (first small)) (first (first large))))
            (mac/fail (str "mixed: 512-byte " small ", 16 KiB " large)))
        _ (.__setitem__ report "mixed" "f keeps 512, g has 16384")
        [_ obj] (lib/compile-source compiler output "widths" lib/widths-source)
        digest (lib/sha-of obj)
        _ (when (not= digest lib/widths-sha256) (mac/fail (str "the 512-byte width object changed: " digest)))
        _ (.__setitem__ report "widthsUnchanged" digest)]
    (doseq [[name source] refusals]
      (let [[result obj] (lib/compile-source compiler output name source 1)
            message (lib/message-of result)]
        (when (or (not (.__contains__ message "E7106")) (.exists obj))
          (mac/fail (str name " was not refused with E7106 and no output: " message)))
        (.__setitem__ report name "refused E7106")))
    (.write_text (.joinpath output "report.json") (u/json-dump report))
    (println (str "PASS_AIUEOS_OBJECT_WINDOWS16 " (json/dumps report ** :sort_keys true)))
    (.flush sys/stdout)))

(defn -main [& args]
  (main (.resolve (pathlib/Path (or (u/opt args "--compiler") (sys/exit "--compiler is required"))) ** :strict true)
        (.resolve (pathlib/Path (or (u/opt args "--output") (sys/exit "--output is required"))))))

(when (some #(or (= % "check-aiueos-object-windows16.cljc") (str/ends-with? % "/check-aiueos-object-windows16.cljc")) sys/argv)
  (apply -main *command-line-args*))
