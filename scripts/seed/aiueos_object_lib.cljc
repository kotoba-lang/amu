;; Shared helpers of the aiueos kernel object route gates (check-aiueos-object-*): compile a source with a native
;; Amu compiler for x86_64-aiueos-kernel-v1, read the object's .text, decode inlined window accesses.
;; Ported from the helper half of check-aiueos-object-windows16.py (Basilisp, JUN-974). The compiler is a native
;; Mac (or Linux) Amu image; this library stages and observes, it emits nothing.
(ns aiueos-object-lib
  (:require [gate-util :as u]
            [macos-native-lib :as mac])
  (:import json operator pathlib struct sys))

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
(def access {["load" 1] "0fb60402" ["load" 2] "0fb70402" ["load" 4] "8b0402" ["load" 8] "488b0402"
             ["store" 1] "88043a" ["store" 2] "6689043a" ["store" 4] "89043a" ["store" 8] "4889043a"})

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
  "Decode one window access starting at its `cmp rcx,BOUND`; return [kind width]. `widths` are the admitted widths
  above one byte (2 and 8 for the 512-byte and 16 KiB tiers; 4 as well for the 4 KiB tier)."
  ([text at bound] (decode-window text at bound #{2 8}))
  ([text at bound widths]
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
          (when (or (not= mask (dec @width)) (not (contains? widths @width)))
            (throw (python/ValueError (str "width " @width " mask " mask)))))
        (jcc "0f87"))
      (let [kind (if store "store" "load")]
        (take (get access [kind @width]))
        (take "eb02")
        (let [trap @pos]
          (take "0f0b")
          (when (some #(not= % trap) @jumps)
            (throw (python/ValueError (str "a branch misses the ud2 at " trap ": " @jumps))))
          [kind @width]))))))

(defn windows
  "[[offset [kind width]] ...] for every window of BOUND in text."
  ([text bound] (windows text bound #{2 8}))
  ([text bound widths]
   (loop [i (.find text (head bound)) found []]
     (if (>= i 0)
       (recur (.find text (head bound) (inc i)) (conj found [i (decode-window text i bound widths)]))
       found))))

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

;; Sources shared across gates (a hyphenated gate namespace cannot be required).
(def xstate-source
  (str "(ns xs (:export [cr4on xcr0on rc xg]))\n"
       "(defn cr4on [] :i64 (kernel-cr4-set-bits 263680))\n"
       "(defn xcr0on [] :i64 (kernel-xcr0-set-bits 7))\n"
       "(defn rc [] :i64 (kernel-read-cr4))\n"
       "(defn xg [] :i64 (kernel-xgetbv))\n"))
(def halt-source
  (str "(ns hw (:export [kotoba_aiueos_wait]))\n"
       "(defn kotoba_aiueos_wait [] :i64 (kernel-wait-interrupt))\n"))

;; Steps every gate of the family repeats.
(defn check-widths-unchanged!
  "The 512-byte width object keeps its pinned SHA-256; records it in report."
  [compiler output report]
  (let [[_ obj] (compile-source compiler output "widths" widths-source)
        digest (sha-of obj)]
    (when (not= digest widths-sha256) (mac/fail (str "the 512-byte width object changed: " digest)))
    (.__setitem__ report "widthsUnchanged" digest)))

(defn check-refusals!
  "Each [name source] must be refused with `code` and write no object; records \"refused CODE\" in report."
  [compiler output report pairs code]
  (doseq [[name src] pairs]
    (let [[result obj] (compile-source compiler output name src 1)
          message (message-of result)]
      (when (or (not (.__contains__ message code)) (.exists obj))
        (mac/fail (str name " was not refused with " code " and no output: " message)))
      (.__setitem__ report name (str "refused " code)))))

(defn emit!
  "Write report.json and print TAG followed by the sorted-key report."
  [output report tag]
  (.write_text (.joinpath output "report.json") (u/json-dump report))
  (println (str tag " " (json/dumps report ** :sort_keys true)))
  (.flush sys/stdout))

(defn start!
  "Verify the compiler and create the output directory."
  [compiler output]
  (mac/verify-macho compiler)
  (.mkdir output ** :parents false :mode 0700 :exist_ok false))

(defn cli-main
  "Parse --compiler/--output (resolved) and call (f compiler output)."
  [args f]
  (f (.resolve (pathlib/Path (or (u/opt args "--compiler") (sys/exit "--compiler is required"))) ** :strict true)
     (.resolve (pathlib/Path (or (u/opt args "--output") (sys/exit "--output is required"))))))

(def pause-source
  (str "(ns ps (:export [kotoba_aiueos_spin]))\n"
       "(defn kotoba_aiueos_spin [] :i64 (kernel-pause))\n"))

(def dot-source
  (str "(ns fdot (:export [kotoba_aiueos_dot_f32]))\n"
       "(defn kotoba_aiueos_dot_f32 [a :i64 an :i64 b :i64 bn :i64 c :i64] :i64 (kernel-dot-f32 a an b bn c))\n"))

;; Independent ELF64 relocatable reader shared by the object-route gates.
(defn unpack-from [fmt b off] (vec (struct/unpack_from fmt b off)))

(defn read-elf
  "Symbols [name info shndx value size], relocations [offset info addend], .text and section indices of an ET_REL object."
  [path]
  (let [blob (.read_bytes path)]
    (when-not (u/deq (u/bslice blob 0 16) (u/hex->bytes "7f454c46020101000000000000000000"))
      (mac/fail "not ELF64 little-endian System V"))
    (let [[etype machine] (unpack-from "<HH" blob 16)
          shoff (first (unpack-from "<Q" blob 40))
          [shnum shstrndx] (unpack-from "<HH" blob 60)
          _ (when (not= [etype machine] [1 62]) (mac/fail "not ET_REL / EM_X86_64"))
          secs (vec (for [i (range shnum)] (unpack-from "<IIQQQQIIQQ" blob (+ shoff (* 64 i)))))
          sstr (nth secs shstrndx)
          shstr (u/bslice blob (nth sstr 4) (+ (nth sstr 4) (nth sstr 5)))
          name-at (fn [table offset] (.decode (u/bslice table offset (.index table (u/bytes-of 0) offset))))
          by-name (into {} (map-indexed (fn [i s] [(name-at shstr (first s)) i]) secs))
          _ (when (not= (set (keys by-name)) #{"" ".text" ".data" ".rela.text" ".symtab" ".strtab" ".shstrtab"})
              (mac/fail (str "unexpected sections " (sort (keys by-name)))))
          body (fn [name] (let [s (nth secs (get by-name name))]
                            [(u/bslice blob (nth s 4) (+ (nth s 4) (nth s 5))) s]))
          [strtab _] (body ".strtab")
          [symdata symsec] (body ".symtab")
          symbols (vec (for [off (range 0 (python/len symdata) 24)]
                         (let [[n info other shndx value size] (unpack-from "<IBBHQQ" symdata off)]
                           [(name-at strtab n) info shndx value size])))
          [reladata _] (body ".rela.text")
          relas (vec (for [off (range 0 (python/len reladata) 24)] (unpack-from "<QQq" reladata off)))
          [text _] (body ".text")]
      {:symbols symbols :relas relas :text text :sym-info (nth symsec 7)
       :data-index (get by-name ".data") :text-index (get by-name ".text")})))


;; check-aiueos-object-windows4k / -fence shared pins and sources.
(def widths16-sha256 "63c0486c9378502b71c33ea108949743e9557d5d467509e3949b60e825dcce6c")   ; SOURCE16 under main's root (amu 2d5ff706)
(def w4k-forms [["load" 1 "u8"] ["store" 1 "u8"] ["load" 2 "u16"] ["store" 2 "u16"]
                ["load" 4 "u32"] ["store" 4 "u32"] ["load" 8 "u64"] ["store" 8 "u64"]])
(def w4k-source
  (str "(ns w4k (:export [ld8 st8 ld16 st16 ld32 st32 ld64 st64]))\n"
       (apply str (for [[kind _ name] w4k-forms]
                    (str "(defn " (if (= kind "load") "ld" "st") (subs name 1) " [b :i64 n :i64 i :i64"
                         (when (= kind "store") " v :i64") "] :i64 (kernel-" kind "-" name "-4k b n i"
                         (when (= kind "store") " v") "))\n")))))
;; SOURCE compiled by the windows4k change's root: the fence block (ids 43..45) must leave it as it is
(def w4k-sha256 "1813e4fe08f8a99a5f06dd91748da6a16e146c6739ffd4477f1a64d2a39aa36f")
(def outport-source
  (str "(ns outport (:export [pic pcw pcr]))\n"
       "(defn pic [m :i64 s :i64] :i64\n"
       "  (if (and (>= m 32) (>= s 32))\n"
       "    (let [c1 (kernel-out-u8 32 17) d1 (kernel-out-u8 128 0) c2 (kernel-out-u8 160 17)\n"
       "          c3 (kernel-out-u8 33 m) c4 (kernel-out-u8 161 s) c9 (kernel-out-u8 33 255) c10 (kernel-out-u8 161 255)]\n"
       "      1)\n"
       "    0))\n"
       "(defn pcw [a :i64 v :i64] :i64\n"
       "  (let [x (kernel-out-u32 3320 (bit-or 2147483648 (bit-and a 252))) y (kernel-out-u32 3324 v)] 1))\n"
       "(defn pcr [a :i64] :i64 (let [x (kernel-out-u32 3320 (bit-or 2147483648 a))] (kernel-in-u32 3324)))\n"))
(def outport-sha256 "6377fce8f681ff0c760798f8fb41281e247f5b8627000ba5348c24464b1fd0d7")
