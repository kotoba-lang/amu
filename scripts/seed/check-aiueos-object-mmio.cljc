;; The aiueos kernel object route has fixed-address MMIO accesses (JUN-556 D4, ADR 0380).
;;
;; Private functions mmio-load32-<addr> [] and mmio-store32-<addr> [v] name one of five local-APIC registers (addr:
;; eight lowercase hex digits, fee00020 fee000f0 fee00320 fee00380 fee003e0; no other address is admitted). A load is
;; `movabs rax,addr; mov eax,[rax]`, a store `movabs rcx,addr; mov [rcx],eax`. The address is an immediate: the object
;; gets no new relocation, symbol or data, only the bytes below in .text. Compiles sources with a native Amu compiler
;; and reads the objects back with the independent ELF parser (aiueos_object_lib/read-elf). Positive: reads of
;; fee00320 and fee000f0 and writes of fee00380 and fee00320 by one export; the .text bytes and the single context
;; relocation are checked. Refused (E7102, nothing written): an address outside the list, uppercase hex, a short or
;; long address, a load with a parameter, a store without one, a body other than the placeholder 0, and the image
;; route. No x86 machine ran these accesses here, and the registers are only addressed, never touched.
;; Ported from check-aiueos-object-mmio.py (Basilisp, JUN-974).
;; Run: basilisp run -p scripts/seed scripts/seed/check-aiueos-object-mmio.cljc -- --compiler C --output DIR
(ns check-aiueos-object-mmio
  (:require [basilisp.string :as str]
            [aiueos-object-lib :as lib]
            [gate-util :as u]
            [macos-native-lib :as mac])
  (:import operator struct sys))

(def source
  (str "(ns mmio (:export [f]))\n"
       "(defn- mmio-load32-fee00320 [] :i64 0)\n(defn- mmio-store32-fee00320 [v :i64] :i64 0)\n"
       "(defn- mmio-load32-fee000f0 [] :i64 0)\n(defn- mmio-store32-fee00380 [v :i64] :i64 0)\n"
       "(defn f [x :i64] :i64\n"
       "  (+ (mmio-store32-fee00380 (+ (mmio-load32-fee00320) x)) (+ (mmio-store32-fee00320 x) (mmio-load32-fee000f0))))\n"))
(defn cat [& parts] (reduce operator/add parts))
(defn load-seq [addr] (cat (u/hex->bytes "48b8") (struct/pack "<Q" addr) (u/hex->bytes "8b00")))
(defn store-seq [addr] (cat (u/hex->bytes "48b9") (struct/pack "<Q" addr) (u/hex->bytes "8901")))
(defn refused [decl call] (str "(ns r (:export [f]))\n" decl "\n(defn f [x :i64] :i64 " call ")\n"))
(def cases
  [["address-not-listed" (refused "(defn- mmio-load32-fee00330 [] :i64 0)" "(mmio-load32-fee00330)")]
   ["uppercase-hex" (refused "(defn- mmio-load32-FEE00320 [] :i64 0)" "(mmio-load32-FEE00320)")]
   ["short-address" (refused "(defn- mmio-load32-ee00320 [] :i64 0)" "(mmio-load32-ee00320)")]
   ["long-address" (refused "(defn- mmio-load32-0fee00320 [] :i64 0)" "(mmio-load32-0fee00320)")]
   ["load-with-param" (refused "(defn- mmio-load32-fee00320 [a :i64] :i64 0)" "(mmio-load32-fee00320 x)")]
   ["store-without-param" (refused "(defn- mmio-store32-fee00320 [] :i64 0)" "(mmio-store32-fee00320)")]
   ["body-not-zero" (refused "(defn- mmio-load32-fee00320 [] :i64 5)" "(mmio-load32-fee00320)")]])

(defn check [path]
  (let [obj (lib/read-elf path)
        relas (:relas obj)
        text (:text obj)]
    (when (or (not= 1 (count relas)) (not= (first relas) [3 (bit-or (bit-shift-left 1 32) 2) -4]))
      (mac/fail (str "relocations " relas ": only the context relocation is expected")))
    (doseq [seq [(load-seq 0xfee00320) (load-seq 0xfee000f0) (store-seq 0xfee00380) (store-seq 0xfee00320)]]
      (when (not= (.count text seq) 1)
        (mac/fail (str "expected exactly one " (.hex seq) ", found " (.count text seq)))))))

(defn main [compiler output]
  (lib/start! compiler output)
  (let [report (u/pydict)
        [_ path] (lib/compile-source compiler output "mmio" source)]
    (check path)
    (.__setitem__ report "mmio" (u/pydict "bytes" (.-st_size (.stat path))))
    (doseq [[name src] cases]
      (lib/check-refusals! compiler output report [[name src]] "E7102"))
    (.write_text (.joinpath output "image.kotoba")
                 "(ns i (:export [main]))\n(defn- mmio-load32-fee00320 [] :i64 0)\n(defn main [] :i64 (mmio-load32-fee00320))\n")
    (let [result (mac/native-run compiler output ["compile" "image.kotoba" "--target" "x86_64-aiueos-kernel-v1" "--artifact" "image"
                                                  "--output" "image.elf" "--fuel" "1024"] :expected 1)]
      (when (or (.exists (.joinpath output "image.elf")) (not (.__contains__ (lib/message-of result) "E7102")))
        (mac/fail "an MMIO access on the image route was not refused with E7102"))
      (.__setitem__ report "image" "refused E7102"))
    (lib/emit! output report "PASS_AIUEOS_OBJECT_MMIO")))

(defn -main [& args] (lib/cli-main args main))

(when (some #(or (= % "check-aiueos-object-mmio.cljc") (str/ends-with? % "/check-aiueos-object-mmio.cljc")) sys/argv)
  (apply -main *command-line-args*))
