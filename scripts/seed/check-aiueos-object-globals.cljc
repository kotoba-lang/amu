;; The aiueos kernel object route exports data cells as GLOBAL OBJECT symbols (JUN-556 D3b, ADR 0380).
;;
;; A private cell-name-<k>-<symbol> [] gives cell k (the 8-byte cell cell-load-<k> and cell-store-<k> address, .data
;; offset 80 + 8k) the symbol <symbol>: GLOBAL OBJECT, size 8, defined in .data. Other objects (entry.S, C) link to it
;; by name, the way kernel/entry.S links aiueos_apic_timer_ticks. Symbols come after the exports and the externs in
;; .symtab; sh_info still names the first global; the context stays the only LOCAL symbol. Reads objects back with the
;; independent ELF parser (aiueos_object_lib/read-elf). Positive: two symbols (cell 0 and cell 3) next to an export
;; and an extern, .data large enough for cell 3. Refused (E7102, nothing written): k = 64, a bad symbol, a symbol
;; equal to an export, to an extern or to another data symbol, a parameter on the declaration, a body other than the
;; placeholder 0, more than sixteen symbols, and the image route. No x86 machine ran these symbols; the linker does
;; the linking. Ported from check-aiueos-object-globals.py (Basilisp, JUN-974).
;; Run: basilisp run -p scripts/seed scripts/seed/check-aiueos-object-globals.cljc -- --compiler C --output DIR
(ns check-aiueos-object-globals
  (:require [basilisp.string :as str]
            [aiueos-object-lib :as lib]
            [gate-util :as u]
            [macos-native-lib :as mac])
  (:import sys))

(def source
  (str "(ns globals (:export [f]))\n"
       "(defn- extern-sink [a :i64] :i64 0)\n"
       "(defn- cell-load-0 [] :i64 0)\n(defn- cell-store-3 [v :i64] :i64 0)\n"
       "(defn- cell-name-0-aiueos_apic_timer_ticks [] :i64 0)\n"
       "(defn- cell-name-3-aiueos_apic_mmio_base [] :i64 0)\n"
       "(defn f [x :i64] :i64 (extern-sink (cell-store-3 (cell-load-0))))\n"))
(defn refused
  ([decl] (refused decl "x"))
  ([decl call] (str "(ns r (:export [f]))\n(defn- extern-sink [a :i64] :i64 0)\n" decl "\n(defn f [x :i64] :i64 " call ")\n")))
(def cases
  [["k64" (refused "(defn- cell-name-64-a [] :i64 0)")]
   ["bad-symbol" (refused "(defn- cell-name-1-Bad [] :i64 0)")]
   ["no-dash" (refused "(defn- cell-name-1 [] :i64 0)")]
   ["equals-export" (refused "(defn- cell-name-1-f [] :i64 0)")]
   ["equals-extern" (refused "(defn- cell-name-1-sink [] :i64 0)")]
   ["equals-other" "(ns r (:export [f]))\n(defn- cell-name-1-dup [] :i64 0)\n(defn- cell-name-2-dup [] :i64 0)\n(defn f [x :i64] :i64 x)\n"]
   ["with-param" (refused "(defn- cell-name-1-a [v :i64] :i64 0)")]
   ["body-not-zero" (refused "(defn- cell-name-1-a [] :i64 5)")]
   ["seventeen" (str "(ns r (:export [f]))\n" (apply str (for [i (range 17)] (str "(defn- cell-name-" i "-s" i " [] :i64 0)\n")))
                     "(defn f [x :i64] :i64 x)\n")]])

(defn check [path]
  (let [obj (lib/read-elf path)
        syms (:symbols obj)
        names (mapv first syms)]
    (when (not= names ["" "context" "f" "sink" "aiueos_apic_timer_ticks" "aiueos_apic_mmio_base"])
      (mac/fail (str "symbols " names)))
    (when (not= (:sym-info obj) 2) (mac/fail "sh_info must name the first global (index 2)"))
    (doseq [[sym value] [[(nth syms 4) 80] [(nth syms 5) (+ 80 24)]]]
      (when (or (not= (nth sym 1) 0x11) (not= (nth sym 2) (:data-index obj)) (not= (nth sym 3) value) (not= (nth sym 4) 8))
        (mac/fail (str "data symbol " sym ", want GLOBAL OBJECT in .data at " value " size 8"))))
    (when (not= (vec (rest (nth syms 3))) [0x10 0 0 0]) (mac/fail (str "extern " (nth syms 3))))
    (when (not= 1 (count (filter #(= % 0x01) (map #(nth % 1) syms))))
      (mac/fail "the context must stay the only LOCAL symbol"))))

(defn main [compiler output]
  (lib/start! compiler output)
  (let [report (u/pydict)
        [_ path] (lib/compile-source compiler output "globals" source)]
    (check path)
    (.__setitem__ report "globals" (u/pydict "bytes" (.-st_size (.stat path))))
    (doseq [[name src] cases]
      (lib/check-refusals! compiler output report [[name src]] "E7102"))
    (.write_text (.joinpath output "image.kotoba") "(ns i (:export [main]))\n(defn- cell-name-0-a [] :i64 0)\n(defn main [] :i64 0)\n")
    (let [result (mac/native-run compiler output ["compile" "image.kotoba" "--target" "x86_64-aiueos-kernel-v1" "--artifact" "image"
                                                  "--output" "image.elf" "--fuel" "1024"] :expected 1)]
      (when (or (.exists (.joinpath output "image.elf")) (not (.__contains__ (lib/message-of result) "E7102")))
        (mac/fail "a data symbol on the image route was not refused with E7102"))
      (.__setitem__ report "image" "refused E7102"))
    (lib/emit! output report "PASS_AIUEOS_OBJECT_GLOBALS")))

(defn -main [& args] (lib/cli-main args main))

(when (some #(or (= % "check-aiueos-object-globals.cljc") (str/ends-with? % "/check-aiueos-object-globals.cljc")) sys/argv)
  (apply -main *command-line-args*))
