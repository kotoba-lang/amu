;; Window accesses on the aiueos object route's own .bss / .high_bss arrays (JUN-553, ADR 0387).
;;
;; The address an array stub bss-addr-<k>-<N> / highbss-addr-<k>-<N> returns (ADR 0385) is a rooted base whose region
;; is the array: the ordinary window accesses (kernel-load-* / kernel-store-*, their 16 KiB tier, kernel-subregion)
;; accept it when the length operand is the literal N. Compiles with a native Amu compiler:
;;
;; * positive: one object whose five exports store, load and sum u8 / u64 windows over a 64-byte .bss array, use the
;;   16 KiB tier on a 4096-byte .high_bss array and read through a subregion. Each window's inlined check starts with
;;   `cmp rcx,BOUND` (512 or 16384) and every one sits after the array's `lea rax,[rip+disp]` (an R_X86_64_PC32
;;   against the section symbol);
;; * refused (E7106, nothing written): a length that is a parameter, a literal other than N, the address as a record
;;   base, and arithmetic on the address;
;; * unchanged: an object that names no array is byte-identical to check-aiueos-object-exports's pinned one-export
;;   object.
;;
;; docs/evidence/array-windows-20261030/ ran the positive object under QEMU by hand.
;; Ported from check-aiueos-object-array-windows.py (Basilisp, JUN-974).
;; Run: basilisp run -p scripts/seed scripts/seed/check-aiueos-object-array-windows.cljc -- --compiler C --output DIR
(ns check-aiueos-object-array-windows
  (:require [basilisp.string :as str]
            [aiueos-object-lib :as lib]
            [gate-util :as u]
            [macos-native-lib :as mac])
  (:import sys))

(def positive
  (str "(ns pos (:export [put get sum big part]))\n"
       "(defn- bss-addr-0-64 [] :i64 0)\n"
       "(defn- highbss-addr-0-4096 [] :i64 0)\n"
       "(defn put [i :i64 v :i64] :i64 (kernel-store-u8 (bss-addr-0-64) 64 i v))\n"
       "(defn get [i :i64] :i64 (kernel-load-u8 (bss-addr-0-64) 64 i))\n"
       "(defn sum [] :i64 (+ (kernel-load-u64 (bss-addr-0-64) 64 0) (kernel-load-u64 (bss-addr-0-64) 64 56)))\n"
       "(defn big [i :i64 v :i64] :i64 (let [w (kernel-store-u16-16k (highbss-addr-0-4096) 4096 i v)] (kernel-load-u16-16k (highbss-addr-0-4096) 4096 i)))\n"
       "(defn part [i :i64] :i64 (let [s (kernel-subregion (bss-addr-0-64) 64 32 16)] (kernel-load-u8 s 16 i)))\n"))
(defn refused [decl body]
  (str "(ns r (:export [f]))\n(defn- bss-addr-0-64 [] :i64 0)\n" decl "\n(defn f [i :i64 n :i64] :i64 " body ")\n"))
(def refusals
  [["param-length" (refused "" "(kernel-load-u8 (bss-addr-0-64) n i)")]
   ["wrong-literal" (refused "" "(kernel-load-u8 (bss-addr-0-64) 128 i)")]
   ["record-base" (refused "(defn- record-load-u32-0-64 [b :i64] :i64 0)" "(record-load-u32-0-64 (bss-addr-0-64))")]
   ["arithmetic" (refused "" "(kernel-load-u8 (+ (bss-addr-0-64) 1) 64 i)")]])
(def lea (u/hex->bytes "488d0500000000"))

(defn main [compiler output]
  (lib/start! compiler output)
  (let [report (u/pydict)
        [_ path] (lib/compile-source compiler output "pos" positive)
        obj (lib/read-elf-all path)
        _ (when (or (not= (subvec (:names obj) 7) [".bss" ".high_bss"])
                    (not= (nth (nth (:secs obj) 7) 5) 64) (not= (nth (nth (:secs obj) 8) 5) 4096))
            (mac/fail (str "sections " (:names obj) " sizes " (mapv #(nth % 5) (subvec (:secs obj) 7)))))
        text (:text obj)
        small (.count text (u/hex->bytes "4881f900020000"))
        large (.count text (u/hex->bytes "4881f900400000"))
        _ (when (not= [small large] [5 2]) (mac/fail (str "windows: " small " at 512 and " large " at 16384, want 5 and 2")))
        leas (vec (for [[off info _] (:relas obj)
                        :when (and (u/deq (u/bslice text (- off 3) (+ off 4)) lea)
                                   (= (bit-and info 0xFFFFFFFF) 2)
                                   (contains? #{2 3} (bit-shift-right info 32)))]
                    off))
        _ (when (not= (count leas) 7) (mac/fail (str (count leas) " array lea relocations, want 7")))
        _ (.__setitem__ report "positive" (u/pydict "bytes" (.-st_size (.stat path)) "windows512" small "windows16k" large
                                                    "arrayLeas" (count leas)))]
    (doseq [[name src] refusals] (lib/check-refusals! compiler output report [[name src]] "E7106"))
    (let [[_ one] (lib/compile-source compiler output "one" lib/one-source)]
      (when (not= (lib/sha-of one) lib/one-sha256) (mac/fail "an object without arrays changed its bytes"))
      (.__setitem__ report "withoutArrays" "byte-identical"))
    (lib/emit! output report "PASS_AIUEOS_OBJECT_ARRAY_WINDOWS")))

(defn -main [& args] (lib/cli-main args main))

(when (some #(or (= % "check-aiueos-object-array-windows.cljc") (str/ends-with? % "/check-aiueos-object-array-windows.cljc")) sys/argv)
  (apply -main *command-line-args*))
