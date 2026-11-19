;; The aiueos kernel object route has fixed-size record accesses (JUN-556 D5, ADR 0381).
;;
;; Private functions record-load-<w>-<off>-<N> [b] and record-store-<w>-<off>-<N> [b v] (w one of u8 u16 u32 u64, off
;; and N canonical decimals, N a multiple of 4 in 8..256, off a multiple of the width, off + width <= N) read or write
;; the N-byte record that an exported function's parameter b points at, at the literal offset off. An access is
;; `mov rdx,[b]; (mov rax,[v];) test rdx,rdx; jz ud2; <access [rdx+off32]>; jmp +2; ud2`. The object gets no new
;; relocation, symbol or data, only the bytes below in .text.
;; The base must be an unassigned parameter of an exported function, every access to one parameter names the same N,
;; and that parameter is not also a window base.
;; Compiles sources with a native Amu compiler and reads the objects back with the independent ELF parser
;; (aiueos_object_lib/read-elf). Positive: a 40-byte record written at the offsets of struct
;; aiueos_device_worker_poll (u64 at 0 and 8, u32 at 16, u8 at 20..23) and read back at 16 and 20, plus the other
;; widths at their own offsets; the instruction bytes are checked one by one. Refused: malformed names and sizes
;; (E7102); a base that is a literal, arithmetic, a non-export parameter, a second N for one parameter, a parameter
;; used as a record and as a window base (E7106); the image route (E7102). In every refusal nothing is written.
;; No x86 machine ran these accesses in this gate; the QEMU differential check is scripts/apic-x86-smoke in the kotoba
;; repository for the same shape of object. Ported from check-aiueos-object-records.py (Basilisp, JUN-974).
;; Run: basilisp run -p scripts/seed scripts/seed/check-aiueos-object-records.cljc -- --compiler C --output DIR
(ns check-aiueos-object-records
  (:require [basilisp.string :as str]
            [aiueos-object-lib :as lib]
            [gate-util :as u]
            [macos-native-lib :as mac])
  (:import operator struct sys))

;; (access bytes before the 32-bit offset, jz distance)
(def access
  {["load" "u8"] ["0fb682" 9] ["load" "u16"] ["0fb782" 9] ["load" "u32"] ["8b82" 8] ["load" "u64"] ["488b82" 9]
   ["store" "u8"] ["8882" 8] ["store" "u16"] ["668982" 9] ["store" "u32"] ["8982" 8] ["store" "u64"] ["488982" 9]})
(def positive
  [["store" "u64" 0] ["store" "u64" 8] ["store" "u32" 16] ["store" "u8" 20] ["store" "u8" 21]
   ["store" "u16" 22] ["load" "u32" 16] ["load" "u8" 20] ["load" "u16" 22] ["load" "u64" 8]])

(defn declaration
  ([direction width off] (declaration direction width off 40))
  ([direction width off n]
   (str "(defn- record-" direction "-" width "-" off "-" n " " (if (= direction "load") "[b :i64]" "[b :i64 v :i64]") " :i64 0)\n")))

(defn positive-source []
  (let [decls (apply str (for [[d w o] positive] (declaration d w o)))
        calls (for [[d w o] positive]
                (str "(record-" d "-" w "-" o "-40 poll" (when (= d "store") " x") ")"))
        body (reduce (fn [acc call] (str "(+ " acc " " call ")")) calls)]
    (str "(ns records (:export [f]))\n" decls "(defn f [http :i64 len :i64 poll :i64 x :i64] :i64 " body ")\n")))

(defn cat [& parts] (reduce operator/add parts))
(defn sequence* [direction width off]
  (let [[prefix distance] (get access [direction width])]
    ;; test rdx,rdx; jz rel32 (over the access and the two-byte jmp); the access; jmp +2; ud2
    (cat (u/hex->bytes "4885d20f84") (struct/pack "<i" distance) (u/hex->bytes prefix) (struct/pack "<I" off) (u/hex->bytes "eb020f0b"))))

(defn refused-name
  ([decl call] (refused-name decl call "poll :i64"))
  ([decl call params] (str "(ns r (:export [f]))\n" decl "\n(defn f [" params "] :i64 " call ")\n")))
(def cases-7102   ; malformed declarations
  [["past-the-end" (refused-name "(defn- record-load-u64-36-40 [b :i64] :i64 0)" "(record-load-u64-36-40 poll)")]
   ["misaligned" (refused-name "(defn- record-load-u32-2-40 [b :i64] :i64 0)" "(record-load-u32-2-40 poll)")]
   ["size-not-multiple-of-4" (refused-name "(defn- record-load-u8-0-42 [b :i64] :i64 0)" "(record-load-u8-0-42 poll)")]
   ["size-below-8" (refused-name "(defn- record-load-u32-0-4 [b :i64] :i64 0)" "(record-load-u32-0-4 poll)")]
   ["size-above-256" (refused-name "(defn- record-load-u8-0-260 [b :i64] :i64 0)" "(record-load-u8-0-260 poll)")]
   ["leading-zero" (refused-name "(defn- record-load-u32-08-40 [b :i64] :i64 0)" "(record-load-u32-08-40 poll)")]
   ["unknown-width" (refused-name "(defn- record-load-u24-0-40 [b :i64] :i64 0)" "(record-load-u24-0-40 poll)")]
   ["no-offset" (refused-name "(defn- record-load-u32-40 [b :i64] :i64 0)" "(record-load-u32-40 poll)")]
   ["load-with-two-params" (refused-name "(defn- record-load-u32-0-40 [b :i64 v :i64] :i64 0)" "(record-load-u32-0-40 poll 1)")]
   ["store-with-one-param" (refused-name "(defn- record-store-u32-0-40 [b :i64] :i64 0)" "(record-store-u32-0-40 poll)")]
   ["body-not-zero" (refused-name "(defn- record-load-u32-0-40 [b :i64] :i64 5)" "(record-load-u32-0-40 poll)")]])
(def cases-7106   ; well-formed declarations used badly
  [["literal-base" (refused-name "(defn- record-load-u32-0-40 [b :i64] :i64 0)" "(record-load-u32-0-40 0)")]
   ["arithmetic-base" (refused-name "(defn- record-load-u32-0-40 [b :i64] :i64 0)" "(record-load-u32-0-40 (+ poll 8))")]
   ["two-sizes-one-parameter"
    (refused-name "(defn- record-load-u32-0-40 [b :i64] :i64 0)\n(defn- record-load-u32-4-48 [b :i64] :i64 0)"
                  "(+ (record-load-u32-0-40 poll) (record-load-u32-4-48 poll))")]
   ["record-and-window-base"
    (str "(ns r (:export [f]))\n(defn- record-load-u32-0-40 [b :i64] :i64 0)\n"
         "(defn f [b :i64 n :i64] :i64 (+ (record-load-u32-0-40 b) (kernel-load-u32 b n 0)))\n")]
   ["private-helper-base"
    (str "(ns r (:export [f]))\n(defn- record-load-u32-0-40 [b :i64] :i64 0)\n"
         "(defn- helper [p :i64] :i64 (record-load-u32-0-40 p))\n"
         "(defn f [poll :i64] :i64 (helper poll))\n")]])

(defn check [path]
  (let [obj (lib/read-elf path)]
    (when (or (not= 1 (count (:relas obj))) (not= (first (:relas obj)) [3 (bit-or (bit-shift-left 1 32) 2) -4]))
      (mac/fail (str "relocations " (:relas obj) ": only the context relocation is expected")))
    (when (not= (mapv first (:symbols obj)) ["" "context" "f"])
      (mac/fail (str "symbols " (mapv first (:symbols obj)) ": a record access adds none")))
    (doseq [[direction width off] positive]
      (let [seq (sequence* direction width off)]
        (when (not= 1 (.count (:text obj) seq))
          (mac/fail (str "expected exactly one " direction " " width " at " off " (" (.hex seq) "), found " (.count (:text obj) seq))))))))

(defn main [compiler output]
  (lib/start! compiler output)
  (let [report (u/pydict)
        [_ path] (lib/compile-source compiler output "records" (positive-source))]
    (check path)
    (.__setitem__ report "records" (u/pydict "bytes" (.-st_size (.stat path))))
    (doseq [[name src] cases-7102] (lib/check-refusals! compiler output report [[name src]] "E7102"))
    (doseq [[name src] cases-7106] (lib/check-refusals! compiler output report [[name src]] "E7106"))
    (.write_text (.joinpath output "image.kotoba")
                 (str "(ns i (:export [main]))\n(defn- record-load-u32-0-40 [b :i64] :i64 0)\n" "(defn main [] :i64 0)\n"))
    (let [result (mac/native-run compiler output ["compile" "image.kotoba" "--target" "x86_64-aiueos-kernel-v1" "--artifact" "image"
                                                  "--output" "image.elf" "--fuel" "1024"] :expected 1)]
      (when (or (.exists (.joinpath output "image.elf")) (not (.__contains__ (lib/message-of result) "E7102")))
        (mac/fail "a record declaration on the image route was not refused with E7102"))
      (.__setitem__ report "image" "refused E7102"))
    (lib/emit! output report "PASS_AIUEOS_OBJECT_RECORDS")))

(defn -main [& args] (lib/cli-main args main))

(when (some #(or (= % "check-aiueos-object-records.cljc") (str/ends-with? % "/check-aiueos-object-records.cljc")) sys/argv)
  (apply -main *command-line-args*))
