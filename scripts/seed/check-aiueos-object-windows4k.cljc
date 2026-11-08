;; The aiueos kernel object route's 4 KiB window tier (JUN-708, ADR 0401).
;;
;; kernel-<load|store>-<u8|u16|u32|u64>-4k are ids 35..42 of seed/74-x86_64-aiueos-object.kotoba: kotoba-native
;; machine-ir's [:gmir/kernel-<op>-<w> 4096] memwidth windows, which kotoba-compiler/1 emitted into the AIUEOS crypto
;; and rtl8125 objects. Compiles with a native Amu compiler and decodes every inlined window with the decoder in
;; aiueos_object_lib (this script stages and observes; it emits nothing):
;;   cmp rcx,4096; ja T; test rdx,rdx; jz T; cmp INDEX,rcx; jae T;
;;   [width > 1: mov rsi,rcx; sub rsi,INDEX; cmp rsi,WIDTH; jl T; test INDEX,WIDTH-1; ja T;]
;;   ACCESS; jmp +2; T: ud2
;; with every branch landing on that ud2 (the u32 forms are aligned, as the reference's are; only the 512-byte u32 pair
;; is exempt there).
;;
;; * eight-4k: one object with the eight 4 KiB accesses, in order, each with bound 4096, and no 512-byte or 16 KiB window;
;; * mixed: a 512-byte, a 4 KiB and a 16 KiB u8 load in one object keep their own bounds (the ids stay positional);
;; * opt-in: objects that name no 4 KiB stub are byte-identical to main's root: the 512-byte width object (also with the
;;   new names in a comment only: the blocks are detected in call position), the 16 KiB width object and the out-port
;;   object of check-aiueos-object-outport (which carries every earlier block, ids 0..34);
;; * tier maximum: over the object's own .bss / .high_bss array, a literal length of exactly 4096 compiles; 8192 is
;;   refused (E7108 naming the intrinsic, the size and the maximum 4096; nothing written), loads and stores, u8 to u64;
;; * refused, nothing written: an unrooted base and a computed (or free literal) length (E7106); each form with one
;;   argument too few and one too many (E2103).
;;
;; A length tied to a parameter keeps the run-time check (length > 4096 reaches ud2): not shown here, see
;; docs/evidence/windows4k-fence-20261031/, which runs the eight accesses under QEMU against the reference model.
;; Ported from check-aiueos-object-windows4k.py (Basilisp, JUN-974).
;; Run: basilisp run -p scripts/seed scripts/seed/check-aiueos-object-windows4k.cljc -- --compiler C --output DIR
(ns check-aiueos-object-windows4k
  (:require [basilisp.string :as str]
            [aiueos-object-lib :as lib]
            [gate-util :as u]
            [macos-native-lib :as mac])
  (:import sys))

(def mixed
  (str "(ns mixed (:export [f g h]))\n"
       "(defn f [b :i64 n :i64 i :i64] :i64 (kernel-load-u8 b n i))\n"
       "(defn g [b :i64 n :i64 i :i64] :i64 (kernel-load-u8-4k b n i))\n"
       "(defn h [b :i64 n :i64 i :i64] :i64 (kernel-load-u8-16k b n i))\n"))
;; a source that names the new forms only in prose (as kotoba's acpi-checksum-ok does) is not opted in
(def mention ";; widths: `kernel-load-u8` (512), `kernel-load-u8-4k` (4096); a fence would be `kernel-fence-store`\n")
(def widths4 #{2 4 8})
(def width-of (into {} (for [[_ w name] lib/w4k-forms] [name w])))

(defn one
  ([form] (one form "b :i64 n :i64 i :i64 v :i64"))
  ([form params] (str "(ns r (:export [f]))\n(defn f [" params "] :i64 " form ")\n")))

(defn refusals []
  (vec (concat
        [["unrooted-base" (one "(kernel-load-u8-4k (+ b 1) n i)") "E7106"]
         ["computed-length" (one "(kernel-load-u32-4k b (+ n 4) i)") "E7106"]
         ["halved-length" (one "(kernel-store-u16-4k b (quot n 2) i v)") "E7106"]
         ["free-literal-length" (one "(kernel-store-u64-4k b 16 i v)") "E7106"]
         ["memory-base" (one "(kernel-load-u8-4k (kernel-load-u64-4k b n 0) n i)") "E7106"]]
        (mapcat (fn [[kind _ name]]
                  (let [args (vec (concat ["b" "n" "i"] (when (= kind "store") ["v"])))]
                    [[(str kind "-" name "-few") (one (str "(kernel-" kind "-" name "-4k " (str/join " " (butlast args)) ")")) "E2103"]
                     [(str kind "-" name "-many") (one (str "(kernel-" kind "-" name "-4k " (str/join " " args) " 0)")) "E2103"]]))
                lib/w4k-forms))))

(defn main [compiler output]
  (lib/start! compiler output)
  (let [report (u/pydict)
        [_ obj] (lib/compile-source compiler output "w4k" lib/w4k-source)
        text (lib/text-section obj)
        found (mapv second (lib/windows text 4096 widths4))
        want (mapv (fn [[k w _]] [k w]) lib/w4k-forms)
        _ (when (or (not= found want) (seq (lib/windows text 512)) (seq (lib/windows text 16384)))
            (mac/fail (str "4 KiB windows " found "; want " want " and no 512-byte or 16 KiB window")))
        digest (lib/sha-of obj)
        _ (when (not= digest lib/w4k-sha256) (mac/fail (str "the 4 KiB width object is not the pinned one: " digest)))
        _ (.__setitem__ report "eight4k" (u/pydict "windows" (count found) "sha256" digest))
        [_ obj] (lib/compile-source compiler output "mixed" mixed)
        text (lib/text-section obj)
        small (lib/windows text 512)
        mid (lib/windows text 4096 widths4)
        large (lib/windows text 16384)
        _ (when (or (not= (mapv second small) [["load" 1]]) (not= (mapv second mid) [["load" 1]])
                    (not= (mapv second large) [["load" 1]])
                    (not (< (first (first small)) (first (first mid)) (first (first large)))))
            (mac/fail (str "mixed: 512-byte " small ", 4 KiB " mid ", 16 KiB " large)))
        _ (.__setitem__ report "mixed" "f keeps 512, g has 4096, h has 16384")]
    (doseq [[name src want] [["widths" lib/widths-source lib/widths-sha256]
                             ["mention" (str mention lib/widths-source) lib/widths-sha256]
                             ["widths16" lib/source16 lib/widths16-sha256]
                             ["outport" lib/outport-source lib/outport-sha256]]]
      (let [[_ o] (lib/compile-source compiler output name src)
            have (lib/sha-of o)]
        (when (or (not= have want) (seq (lib/windows (lib/text-section o) 4096 widths4)))
          (mac/fail (str name ": an object naming no 4 KiB stub changed (" have ") or carries a 4 KiB window")))
        (.__setitem__ report (str name "Unchanged") have)))
    (let [tiers (u/pydict)]
      (doseq [[kind _ name] lib/w4k-forms]
        (let [intrinsic (str "kernel-" kind "-" name "-4k")]
          (doseq [[size array] [[4096 "bss"] [8192 "highbss"]]]
            (let [base (str "(" array "-addr-0-" size ")")
                  call (if (= kind "store")
                         (str "(" intrinsic " " base " " size " i v)")
                         (str "(" intrinsic " " base " " size " i)"))
                  src (str "(ns t (:export [f]))\n(defn- " array "-addr-0-" size " [] :i64 0)\n(defn f [i :i64 v :i64] :i64 " call ")\n")
                  expected (if (= size 4096) 0 1)
                  [result obj] (lib/compile-source compiler output (str kind "-" name "-" size) src expected)
                  message (lib/message-of result)]
              (if (= size 4096)
                (when (not= (mapv second (lib/windows (lib/text-section obj) 4096 widths4)) [[kind (get width-of name)]])
                  (mac/fail (str intrinsic " at 4096: no single 4 KiB window")))
                (let [need (str "E7108 " intrinsic " size 8192 is above its tier maximum 4096")]
                  (when (or (.exists obj) (not (.__contains__ message need)))
                    (mac/fail (str intrinsic " size 8192: want '" need "' and no output, got " (pr-str (subs message (max 0 (- (count message) 300)))))))))))
          (.__setitem__ tiers intrinsic (u/pydict "atMaximum" 4096 "refused" 8192))))
      (.__setitem__ report "tierMaximum" tiers))
    (doseq [[name src code] (refusals)]
      (lib/check-refusals! compiler output report [[name src]] code))
    (lib/emit! output report "PASS_AIUEOS_OBJECT_WINDOWS4K")))

(defn -main [& args] (lib/cli-main args main))

(when (some #(or (= % "check-aiueos-object-windows4k.cljc") (str/ends-with? % "/check-aiueos-object-windows4k.cljc")) sys/argv)
  (apply -main *command-line-args*))
