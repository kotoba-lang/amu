;; The aiueos kernel object route has 8-byte data cells after the context (JUN-556 D3, ADR 0380).
;;
;; Private functions cell-load-<k> [] and cell-store-<k> [v] (k < 64, canonical decimal) name cell k at .data offset
;; 80 + 8k. A load is `mov rax,[rip+disp]`, a store `mov [rip+disp],rax`; each access has an R_X86_64_PC32 relocation
;; against the context symbol with addend 80 + 8k - 4 and a zero displacement. .data grows to 80 + 8 * (highest named
;; cell + 1) zero bytes; sections and symbols stay as they were. Compiles sources with a native Amu compiler and reads
;; the objects back with an independent ELF reader (aiueos_object_lib/elf-sections). Positive: cells 0 and 3 read and
;; written by one export; the .data size, the relocations and the access bytes are checked. A source without a cell
;; compiles to the bytes it always did (the one-export gate pins that). Refused (E7102, nothing written): k = 64, a
;; leading zero, a non-digit suffix, a load with a parameter, a store without one, a body other than the placeholder 0,
;; cells on the image route. The extern gate's cases are unaffected. No x86 machine ran these accesses here.
;; Ported from check-aiueos-object-cells.py (Basilisp, JUN-974).
;; Run: basilisp run -p scripts/seed scripts/seed/check-aiueos-object-cells.cljc -- --compiler C --output DIR
(ns check-aiueos-object-cells
  (:require [basilisp.string :as str]
            [aiueos-object-lib :as lib]
            [gate-util :as u]
            [macos-native-lib :as mac])
  (:import sys))

(def source
  (str "(ns cells (:export [f]))\n"
       "(defn- cell-load-0 [] :i64 0)\n(defn- cell-store-0 [v :i64] :i64 0)\n"
       "(defn- cell-load-3 [] :i64 0)\n(defn- cell-store-3 [v :i64] :i64 0)\n"
       "(defn f [x :i64] :i64\n"
       "  (+ (cell-store-3 (+ (cell-load-0) x)) (+ (cell-store-0 x) (cell-load-3))))\n"))
(def load-op "488b05")
(def store-op "488905")
(def context-pc32 (bit-or (bit-shift-left 1 32) 2))
(defn refused [decl call] (str "(ns r (:export [f]))\n" decl "\n(defn f [x :i64] :i64 " call ")\n"))
(def cases
  [["k64" (refused "(defn- cell-load-64 [] :i64 0)" "(cell-load-64)")]
   ["leading-zero" (refused "(defn- cell-load-07 [] :i64 0)" "(cell-load-07)")]
   ["non-digit" (refused "(defn- cell-load-x [] :i64 0)" "(cell-load-x)")]
   ["load-with-param" (refused "(defn- cell-load-1 [a :i64] :i64 0)" "(cell-load-1 x)")]
   ["store-without-param" (refused "(defn- cell-store-1 [] :i64 0)" "(cell-store-1)")]
   ["body-not-zero" (refused "(defn- cell-load-1 [] :i64 5)" "(cell-load-1)")]])

(defn check [path]
  (let [blob (.read_bytes path)
        by (lib/elf-sections blob)
        data (get by ".data")
        text-sec (get by ".text")
        rela (get by ".rela.text")]
    (when (not= (nth data 5) (+ 80 (* 8 4))) (mac/fail (str ".data is " (nth data 5) " bytes, want " (+ 80 (* 8 4)))))
    (when-not (u/deq (u/bslice blob (+ (nth data 4) 80) (+ (nth data 4) (nth data 5))) (u/bytes-of-n 32 0))
      (mac/fail "cells are not zero"))
    (let [text (u/bslice blob (nth text-sec 4) (+ (nth text-sec 4) (nth text-sec 5)))
          rels (vec (for [i (range (quot (nth rela 5) 24))] (lib/unpack-from "<QQq" blob (+ (nth rela 4) (* 24 i)))))]
      (when (not= (first rels) [3 context-pc32 -4]) (mac/fail (str "context relocation " (first rels))))
      (let [cells (sort-by first (rest rels))]
        (when (not= (count cells) 4) (mac/fail (str (count cells) " cell relocations, want 4")))
        (let [seen (atom {})]
          (doseq [[offset info addend] cells]
            (when (or (not= info context-pc32) (not (contains? #{76 100} addend)))
              (mac/fail (str "cell relocation " [offset info addend])))
            (when-not (u/deq (u/bslice text offset (+ offset 4)) (u/bytes-of-n 4 0))
              (mac/fail (str "displacement at " offset " is not zero")))
            (let [opcode (.hex (u/bslice text (- offset 3) offset))]
              (when-not (contains? #{load-op store-op} opcode)
                (mac/fail (str "access at " (- offset 3) " is " opcode)))
              (swap! seen update [opcode addend] (fnil inc 0))))
          (when (not= @seen {[load-op 76] 1 [store-op 76] 1 [load-op 100] 1 [store-op 100] 1})
            (mac/fail (str "accesses " @seen))))))))

(defn main [compiler output]
  (lib/start! compiler output)
  (let [report (u/pydict)
        [_ path] (lib/compile-source compiler output "cells" source)]
    (check path)
    (.__setitem__ report "cells" (u/pydict "bytes" (.-st_size (.stat path))))
    (doseq [[name src] cases] (lib/check-refusals! compiler output report [[name src]] "E7102"))
    (.write_text (.joinpath output "image.kotoba")
                 "(ns i (:export [main]))\n(defn- cell-load-0 [] :i64 0)\n(defn main [] :i64 (cell-load-0))\n")
    (let [result (mac/native-run compiler output ["compile" "image.kotoba" "--target" "x86_64-aiueos-kernel-v1" "--artifact" "image"
                                                  "--output" "image.elf" "--fuel" "1024"] :expected 1)]
      (when (or (.exists (.joinpath output "image.elf")) (not (.__contains__ (lib/message-of result) "E7102")))
        (mac/fail "a cell on the image route was not refused with E7102"))
      (.__setitem__ report "image" "refused E7102"))
    (lib/emit! output report "PASS_AIUEOS_OBJECT_CELLS")))

(defn -main [& args] (lib/cli-main args main))

(when (some #(or (= % "check-aiueos-object-cells.cljc") (str/ends-with? % "/check-aiueos-object-cells.cljc")) sys/argv)
  (apply -main *command-line-args*))
