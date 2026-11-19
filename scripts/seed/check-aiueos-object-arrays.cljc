;; The aiueos kernel object route hands out the address of a fixed-size .bss / .high_bss array (JUN-556 C, ADR 0385).
;;
;; A private function bss-addr-<k>-<N> [] or highbss-addr-<k>-<N> [] (k a single digit 0..7, N a canonical decimal and
;; a multiple of 8 in 8..65536, body the placeholder 0) returns the address of zero-initialised LOCAL array k of N
;; bytes: `lea rax,[rip+disp32]` with an R_X86_64_PC32 relocation against the section's STT_SECTION symbol, addend
;; offset - 4. Arrays of one section lie in k order at 16-byte aligned offsets. The address is an ordinary value, not
;; a rooted base: it can only be handed to an extern. An object that names no such stub keeps its bytes (seven
;; sections). Compiles sources with a native Amu compiler and reads the objects back with an independent ELF parser
;; (aiueos_object_lib/read-elf-all). Positive: three arrays (.bss 0 of 1280 and 1 of 24, .high_bss 0 of 1536) passed
;; to a declared extern: two NOBITS sections of sizes 1312 and 1536, two LOCAL section symbols after the context, the
;; globals shifted by two, and one PC32 per lea site with addends -4, 1276 and -4. The one-export object of
;; check-aiueos-object-exports is still byte-identical. Refused: malformed names, a parameter, a non-zero body, two
;; sizes for one array (E7102), the address as a window or record base (E7106), the image route (E7102). In every
;; refusal nothing is written.
;; The QEMU run of this object (addresses and memset contents) was done by hand for the ADR; the consumer's
;; differential check in the kotoba repository runs the linked kernel.
;; Ported from check-aiueos-object-arrays.py (Basilisp, JUN-974).
;; Run: basilisp run -p scripts/seed scripts/seed/check-aiueos-object-arrays.cljc -- --compiler C --output DIR
(ns check-aiueos-object-arrays
  (:require [basilisp.string :as str]
            [aiueos-object-lib :as lib]
            [gate-util :as u]
            [macos-native-lib :as mac])
  (:import sys))

(def positive
  (str "(ns arrays (:export [f g]))\n"
       "(defn- extern-memset [p :i64 v :i64 n :i64] :i64 0)\n"
       "(defn- bss-addr-0-1280 [] :i64 0)\n(defn- bss-addr-1-24 [] :i64 0)\n(defn- highbss-addr-0-1536 [] :i64 0)\n"
       "(defn f [x :i64] :i64 (+ (extern-memset (bss-addr-0-1280) x 1280) (extern-memset (bss-addr-1-24) 0 24)))\n"
       "(defn g [] :i64 (extern-memset (highbss-addr-0-1536) 0 1536))\n"))
(def lea (u/hex->bytes "488d0500000000"))
(defn pc32 [sym] (bit-or (bit-shift-left sym 32) 2))
(defn refused-source
  ([decl call] (refused-source decl call "x :i64"))
  ([decl call params]
   (str "(ns r (:export [f]))\n(defn- extern-sink [a :i64] :i64 0)\n" decl "\n(defn f [" params "] :i64 " call ")\n")))
(defn one-stub
  ([name] (one-stub name "0" ""))
  ([name body params]
   (refused-source (str "(defn- " name " [" params "] :i64 " body ")") (str "(extern-sink (" name (when (seq params) " x") "))"))))
(def cases-7102
  [["k-8" (one-stub "bss-addr-8-16")]
   ["n-not-multiple-of-8" (one-stub "bss-addr-0-12")]
   ["n-too-large" (one-stub "bss-addr-0-65544")]
   ["n-leading-zero" (one-stub "bss-addr-0-016")]
   ["n-missing" (one-stub "bss-addr-0-")]
   ["high-k-two-digits" (one-stub "highbss-addr-10-16")]
   ["with-param" (one-stub "bss-addr-0-16" "0" "v :i64")]
   ["body-not-zero" (one-stub "bss-addr-0-16" "7" "")]
   ["two-sizes" (refused-source "(defn- bss-addr-0-16 [] :i64 0)\n(defn- bss-addr-0-32 [] :i64 0)"
                                "(+ (extern-sink (bss-addr-0-16)) (extern-sink (bss-addr-0-32)))")]])
(def cases-7106
  [["address-as-window-base" (refused-source "(defn- bss-addr-0-64 [] :i64 0)" "(kernel-load-u32 (bss-addr-0-64) n 0)" "n :i64")]
   ["address-as-record-base" (refused-source "(defn- bss-addr-0-64 [] :i64 0)\n(defn- record-load-u32-0-40 [b :i64] :i64 0)"
                                              "(record-load-u32-0-40 (bss-addr-0-64))")]])

(defn check [obj]
  (when (not= (:names obj) ["" ".text" ".data" ".rela.text" ".symtab" ".strtab" ".shstrtab" ".bss" ".high_bss"])
    (mac/fail (str "sections " (:names obj))))
  (doseq [[i size] [[7 1312] [8 1536]]]
    (let [[_ typ flags addr off sz _ _ align entsize] (nth (:secs obj) i)]
      (when (not= [typ flags addr sz align entsize] [8 3 0 size 16 0])
        (mac/fail (str (nth (:names obj) i) " header " (nth (:secs obj) i) ", want NOBITS WA size " size " align 16")))
      (when (> off (:size obj)) (mac/fail (str (nth (:names obj) i) " offset " off " past the file")))))
  (let [syms (:symbols obj)]
    (when (not= (mapv (fn [s] [(nth s 0) (nth s 1) (nth s 2) (nth s 3)]) (subvec syms 2 4)) [["" 0x03 7 0] ["" 0x03 8 0]])
      (mac/fail (str "symbols 2 and 3 are " (subvec syms 2 4) ", want LOCAL SECTION symbols of .bss and .high_bss")))
    (when (not= (:sym-info obj) 4)
      (mac/fail (str "sh_info " (:sym-info obj) ", want 4 (the first global after the section symbols)")))
    (when (not= (mapv first (subvec syms 4)) ["f" "g" "memset"]) (mac/fail (str "globals " (mapv first (subvec syms 4))))))
  (let [text (:text obj)
        sites (loop [at (.find text lea) acc []]
                (if (>= at 0) (recur (.find text lea (+ at (python/len lea))) (conj acc (+ at 3))) acc))
        found (vec (for [site sites [off info a] (:relas obj) :when (= off site)] [info a]))
        want [[(pc32 2) -4] [(pc32 2) (- 1280 4)] [(pc32 3) -4]]]
    (when (not= found want) (mac/fail (str "lea relocations " found ", want " want)))
    (let [memset (vec (for [[off info a] (:relas obj) :when (= info (bit-or (bit-shift-left 6 32) 4))] [off a]))]
      (when (or (not= 3 (count memset)) (some #(not= (second %) -4) memset))
        (mac/fail (str "memset relocations " memset ", want three PLT32 against symbol 6"))))))

(defn main [compiler output]
  (lib/start! compiler output)
  (let [report (u/pydict)
        [_ path] (lib/compile-source compiler output "arrays" positive)]
    (check (lib/read-elf-all path))
    (.__setitem__ report "arrays" (u/pydict "bytes" (.-st_size (.stat path))))
    (let [[_ one] (lib/compile-source compiler output "one" lib/one-source)]
      (when (not= (lib/sha-of one) lib/one-sha256) (mac/fail "an object without arrays changed its bytes"))
      (.__setitem__ report "withoutArrays" "byte-identical"))
    (doseq [[name src] cases-7102] (lib/check-refusals! compiler output report [[name src]] "E7102"))
    (doseq [[name src] cases-7106] (lib/check-refusals! compiler output report [[name src]] "E7106"))
    (.write_text (.joinpath output "image.kotoba")
                 "(ns i (:export [main]))\n(defn- bss-addr-0-16 [] :i64 0)\n(defn main [] :i64 (bss-addr-0-16))\n")
    (let [result (mac/native-run compiler output ["compile" "image.kotoba" "--target" "x86_64-aiueos-kernel-v1" "--artifact" "image"
                                                  "--output" "image.elf" "--fuel" "1024"] :expected 1)]
      (when (or (.exists (.joinpath output "image.elf")) (not (.__contains__ (lib/message-of result) "E7102")))
        (mac/fail "an array declaration on the image route was not refused with E7102"))
      (.__setitem__ report "image" "refused E7102"))
    (lib/emit! output report "PASS_AIUEOS_OBJECT_ARRAYS")))

(defn -main [& args] (lib/cli-main args main))

(when (some #(or (= % "check-aiueos-object-arrays.cljc") (str/ends-with? % "/check-aiueos-object-arrays.cljc")) sys/argv)
  (apply -main *command-line-args*))
