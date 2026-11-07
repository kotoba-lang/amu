;; Shared helpers of the aiueos kernel object route gates (check-aiueos-object-*): compile a source with a native
;; Amu compiler for x86_64-aiueos-kernel-v1, read the object's .text, decode inlined window accesses.
;; Ported from the helper half of check-aiueos-object-windows16.py (Basilisp, JUN-974). The compiler is a native
;; Mac (or Linux) Amu image; this library stages and observes, it emits nothing.
(ns aiueos-object-lib
  (:require [gate-util :as u]
            [macos-native-lib :as mac])
  (:import json operator pathlib struct))

(def fuel "1024")
(def widths-sha256 "a8ac4f073c599331986dbf50e9fd59dccbca14dc6bc89ef053918e47f1991738")
(def widths-source
  (str "(ns widths (:export [ld8 st8 ld16 st16 ld64 st64]))\n"
       "(defn ld8 [b :i64 n :i64 i :i64] :i64 (kernel-load-u8 b n i))\n"
       "(defn st8 [b :i64 n :i64 i :i64 v :i64] :i64 (kernel-store-u8 b n i v))\n"
       "(defn ld16 [b :i64 n :i64 i :i64] :i64 (kernel-load-u16 b n i))\n"
       "(defn st16 [b :i64 n :i64 i :i64 v :i64] :i64 (kernel-store-u16 b n i v))\n"
       "(defn ld64 [b :i64 n :i64 i :i64] :i64 (kernel-load-u64 b n i))\n"
       "(defn st64 [b :i64 n :i64 i :i64 v :i64] :i64 (kernel-store-u64 b n i v))\n"))
(def source16
  (-> widths-source (.replace "(ns widths" "(ns widths16") (.replace " b n i)" "-16k b n i)") (.replace " b n i v)" "-16k b n i v)")))
(def access {["load" 1] "0fb60402" ["load" 2] "0fb70402" ["load" 8] "488b0402"
             ["store" 1] "88043a" ["store" 2] "6689043a" ["store" 8] "4889043a"})

(defn hexb [s] (u/hex->bytes s))

(defn text-section
  "The .text bytes of an ELF64 relocatable object."
  [path]
  (let [blob (.read_bytes (pathlib/Path path))
        shoff (first (struct/unpack_from "<Q" blob 40))
        [shnum shstrndx] (vec (struct/unpack_from "<HH" blob 60))
        secs (vec (for [i (range shnum)] (vec (struct/unpack_from "<IIQQQQIIQQ" blob (+ shoff (* 64 i))))))
        sstr (nth secs shstrndx)
        shstr (u/bslice blob (nth sstr 4) (+ (nth sstr 4) (nth sstr 5)))]
    (or (first (for [s secs
                     :when (u/deq (u/bslice shstr (first s) (.index shstr (u/bytes-of 0) (first s))) (.encode ".text"))]
                 (u/bslice blob (nth s 4) (+ (nth s 4) (nth s 5)))))
        (throw (python/ValueError "no .text")))))

(defn head [bound] (operator/add (hexb "4881f9") (struct/pack "<I" bound)))

(defn decode-window
  "Decode one window access starting at its `cmp rcx,BOUND`; return [kind width]."
  [text at bound]
  (let [pos (atom at)
        jumps (atom [])
        take (fn [want]
               (let [want (if (string? want) (hexb want) want)
                     have (u/bslice text @pos (+ @pos (python/len want)))]
                 (when-not (u/deq have want)
                   (throw (python/ValueError (str "at " @pos ": want " (.hex want) ", have " (.hex have)))))
                 (swap! pos + (python/len want))))
        jcc (fn [opcode]
              (take opcode)
              (let [rel (first (struct/unpack_from "<i" text @pos))]
                (swap! pos + 4)
                (swap! jumps conj (+ @pos rel))))]
    (take (head bound))
    (jcc "0f87")
    (take "4885d2")
    (jcc "0f84")
    (let [store (u/deq (u/bslice text @pos (+ @pos 3)) (hexb "4839cf"))
          _ (take (if store "4839cf" "4839c8"))
          _ (jcc "0f83")
          width (atom 1)]
      (when (u/deq (u/bslice text @pos (+ @pos 3)) (hexb "4889ce"))
        (take "4889ce")
        (take (if store "4829fe" "4829c6"))
        (take "4881fe")
        (reset! width (first (struct/unpack_from "<i" text @pos)))
        (swap! pos + 4)
        (jcc "0f8c")
        (take (if store "48f7c7" "48f7c0"))
        (let [mask (first (struct/unpack_from "<i" text @pos))]
          (swap! pos + 4)
          (when (or (not= mask (dec @width)) (not (contains? #{2 8} @width)))
            (throw (python/ValueError (str "width " @width " mask " mask)))))
        (jcc "0f87"))
      (let [kind (if store "store" "load")]
        (take (get access [kind @width]))
        (take "eb02")
        (let [trap @pos]
          (take "0f0b")
          (when (some #(not= % trap) @jumps)
            (throw (python/ValueError (str "a branch misses the ud2 at " trap ": " @jumps))))
          [kind @width])))))

(defn windows
  "[[offset [kind width]] ...] for every window of BOUND in text."
  [text bound]
  (loop [i (.find text (head bound)) found []]
    (if (>= i 0)
      (recur (.find text (head bound) (inc i)) (conj found [i (decode-window text i bound)]))
      found)))

(defn compile-source
  "Compile output/name.kotoba for the kernel object target. Returns [result object-path]."
  ([compiler output name source] (compile-source compiler output name source 0))
  ([compiler output name source expected]
   (let [output (pathlib/Path output)]
     (.write_text (.joinpath output (str name ".kotoba")) source)
     [(mac/native-run compiler output ["compile" (str name ".kotoba") "--target" "x86_64-aiueos-kernel-v1"
                                       "--output" (str name ".o") "--fuel" fuel] :expected expected)
      (.joinpath output (str name ".o"))])))

(defn message-of [result]
  (.decode (operator/add (.-stdout result) (.-stderr result)) "utf-8" "replace"))

(defn sha-of [path] (u/sha256-hex (.read_bytes (pathlib/Path path))))
