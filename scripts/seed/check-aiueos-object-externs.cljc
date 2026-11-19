;; The aiueos kernel object route can call declared functions of other objects (JUN-556 D1, ADR 0380).
;;
;; A private function named extern-<symbol> declares a function the linker supplies. The object route turns each call
;; of it into `call rel32` plus `mov r9,[rbp-8]` and an R_X86_64_PLT32 addend -4 relocation against an undefined
;; GLOBAL NOTYPE symbol <symbol>. Compiles sources with a native Amu compiler and reads the objects back with the same
;; independent ELF parser as check-aiueos-object-exports (this script stages and observes; it emits nothing):
;;
;; * one extern called twice and a second extern called once: three PLT32 relocations, two undefined symbols in
;;   declaration order, sh_info still naming the first global, every call site `e8 00000000 4c 8b 4d f8` (the
;;   displacement is the linker's);
;; * a source with no extern declaration compiles as before (its digest is the one-export gate's pinned one, checked
;;   there);
;; * seventeen declarations: refused (E7102), nothing written;
;; * an extern may take up to eight parameters in System V order (JUN-556 E, ADR 0383): the sixth in r9, the seventh
;;   and eighth pushed (an odd count padded by `sub rsp,8`) and removed by `add rsp,imm8` after the context restore; a
;;   nine-parameter extern is refused, nothing written;
;; * a declaration whose body is not the placeholder 0, whose symbol is not [a-z_][a-z0-9_]*, or that is named like an
;;   export: refused, nothing written (review of amu#1662);
;; * the same declaration on the image route (--artifact image): refused, no image.
;;
;; The byte sequence after each call was assembled independently with clang's integrated assembler (ADR 0380); no x86
;; machine ran it here. Ported from check-aiueos-object-externs.py (Basilisp, JUN-974).
;; Run: basilisp run -p scripts/seed scripts/seed/check-aiueos-object-externs.cljc -- --compiler C --output DIR
(ns check-aiueos-object-externs
  (:require [basilisp.string :as str]
            [aiueos-object-lib :as lib]
            [gate-util :as u]
            [macos-native-lib :as mac])
  (:import operator sys))

(def call-tail (u/hex->bytes "4c8b4df8"))        ; mov r9, [rbp-8]
(def source
  (str "(ns ext (:export [f]))\n"
       "(defn- extern-sink_a [a :i64 b :i64] :i64 0)\n"
       "(defn- extern-sink_b [a :i64] :i64 0)\n"
       "(defn f [x :i64] :i64\n"
       "  (+ (extern-sink_a x 7) (+ (extern-sink_b x) (extern-sink_a 1 2))))\n"))
(def too-many
  (str "(ns many (:export [f]))\n"
       (apply str (for [i (range 17)] (str "(defn- extern-e" i " [a :i64] :i64 0)\n")))
       "(defn f [x :i64] :i64 (extern-e0 x))\n"))
(def nine-params
  (str "(ns nine (:export [f]))\n"
       "(defn- extern-nine [a :i64 b :i64 c :i64 d :i64 e :i64 g :i64 h :i64 i :i64 j :i64] :i64 0)\n"
       "(defn f [x :i64] :i64 (extern-nine x x x x x x x x x))\n"))
(defn wide-source [n]
  (let [params (str/join " " (for [i (range n)] (str "p" i " :i64")))
        args (str/join " " (cons "x" (map str (range 2 (inc n)))))]
    (str "(ns w" n " (:export [f]))\n(defn- extern-wide" n " [" params "] :i64 0)\n"
         "(defn f [x :i64] :i64 (extern-wide" n " " args "))\n")))
(def body-not-zero
  (str "(ns b (:export [f]))\n(defn- extern-sink [x :i64] :i64 (+ x 99))\n" "(defn f [x :i64] :i64 (extern-sink x))\n"))
(def body-const
  (str "(ns c (:export [f]))\n(defn- extern-sink [x :i64] :i64 7)\n" "(defn f [x :i64] :i64 (extern-sink x))\n"))
(def bad-name
  (str "(ns n (:export [f]))\n(defn- extern-Bad [x :i64] :i64 0)\n" "(defn f [x :i64] :i64 (extern-Bad x))\n"))
(def clash
  (str "(ns k (:export [sink]))\n(defn- extern-sink [x :i64] :i64 0)\n" "(defn sink [x :i64] :i64 (extern-sink x))\n"))
(def image
  (str "(ns i (:export [main]))\n(defn- extern-sink [] :i64 0)\n" "(defn main [] :i64 (extern-sink))\n"))

(defn pc32 [sym] (bit-or (bit-shift-left sym 32) 2))
(defn plt32 [sym] (bit-or (bit-shift-left sym 32) 4))

(defn check-externs [obj]
  (let [syms (:symbols obj) relas (:relas obj) text (:text obj)]
    (when (not= (mapv first syms) ["" "context" "f" "sink_a" "sink_b"]) (mac/fail (str "symbols " (mapv first syms))))
    (doseq [sym (drop 3 syms)]
      (when (or (not= (nth sym 1) 0x10) (not= (nth sym 2) 0) (not= (nth sym 3) 0) (not= (nth sym 4) 0))
        (mac/fail (str "extern " (first sym) " is " (rest sym) ", want GLOBAL NOTYPE UNDEF"))))
    (when (not= (:sym-info obj) 2) (mac/fail "sh_info must name the first global (index 2)"))
    (when (not= (count relas) 4) (mac/fail (str (count relas) " relocations, want 1 context + 3 calls")))
    (when (not= (first relas) [3 (pc32 1) -4]) (mac/fail (str "context relocation " (first relas))))
    (doseq [[[offset info addend] sym] (map vector (sort-by first (rest relas)) [3 4 3])]   ; sink_a, sink_b, sink_a again
      (when (or (not= info (plt32 sym)) (not= addend -4))
        (mac/fail (str "call relocation " [offset info addend] ", want symbol " sym " PLT32 -4")))
      (when (or (not= (operator/getitem text (dec offset)) 0xE8) (not (u/deq (u/bslice text offset (+ offset 4)) (u/bytes-of-n 4 0))))
        (mac/fail (str "call at " (dec offset) " is not e8 00000000")))
      (when-not (u/deq (u/bslice text (+ offset 4) (+ offset 8)) call-tail)
        (mac/fail (str "call at " (dec offset) " is not followed by mov r9,[rbp-8]: " (.hex (u/bslice text (+ offset 4) (+ offset 8)))))))))

(defn check-wide
  "The call of a declared n-parameter extern (n = 6, 7, 8) is System V shaped."
  [obj n]
  (let [text (:text obj)
        sites (filterv (fn [r] (= (bit-and (second r) 0xFFFFFFFF) 4)) (:relas obj))
        _ (when (not= (count sites) 1) (mac/fail (str "wide" n ": " (count sites) " call relocations")))
        off (first (first sites))
        sl (fn [a b] (u/bslice text a b))]
    (when (or (not= (operator/getitem text (dec off)) 0xE8) (not (u/deq (sl off (+ off 4)) (u/bytes-of-n 4 0)))
              (not (u/deq (sl (+ off 4) (+ off 8)) call-tail)))
      (mac/fail (str "wide" n ": call tail is " (.hex (sl (+ off 4) (+ off 8))))))
    (when-not (u/deq (sl (- off 8) (- off 5)) (u/hex->bytes "4c8b8d"))
      (mac/fail (str "wide" n ": the sixth argument is not loaded into r9 before the call")))
    (let [stack (- n 6)
          after (sl (+ off 8) (+ off 12))]
      (if (zero? stack)
        (when (or (u/deq (u/bslice after 0 3) (u/hex->bytes "4883c4"))
                  (u/has-bytes? (u/hex->bytes "ffb5") (sl (- off 1 (* 6 7) 6) (- off 1 (* 6 7)))))
          (mac/fail "wide6: unexpected stack adjustment"))
        (let [pad (bit-and stack 1)]
          (when-not (u/deq after (operator/add (u/hex->bytes "4883c4") (u/bytes-of (* 8 (+ stack pad)))))
            (mac/fail (str "wide" n ": stack cleanup is " (.hex after))))
          ;; six register loads (7 bytes each) precede the call opcode; the pushes precede those
          (let [start (- off 1 (* 6 7))
                expect (if (= pad 1) (u/hex->bytes "4883ec08") (u/bytes-of))
                block (sl (- start (* 6 stack) (python/len expect)) start)]
            (when (or (not= (python/len block) (+ (* 6 stack) (python/len expect)))
                      (not (u/deq (u/bslice block 0 (python/len expect)) expect)))
              (mac/fail (str "wide" n ": alignment pad missing or wrong")))
            (doseq [k (range stack)]
              (let [a (+ (python/len expect) (* 6 k))
                    chunk (u/bslice block a (+ a 6))]
                (when-not (u/deq (u/bslice chunk 0 2) (u/hex->bytes "ffb5"))
                  (mac/fail (str "wide" n ": push " k " is " (.hex chunk))))))))))))

(defn main [compiler output]
  (lib/start! compiler output)
  (let [report (u/pydict)
        [_ path] (lib/compile-source compiler output "ext" source)]
    (check-externs (lib/read-elf path))
    (.__setitem__ report "externs" (u/pydict "sha256" (lib/sha-of path) "bytes" (.-st_size (.stat path))))
    (doseq [n [6 7 8]]
      (let [[_ wpath] (lib/compile-source compiler output (str "wide" n) (wide-source n))]
        (check-wide (lib/read-elf wpath) n)
        (.__setitem__ report (str "wide" n) (lib/sha-of wpath))))
    (doseq [[name src] [["many" too-many] ["nine" nine-params] ["body-not-zero" body-not-zero]
                        ["body-const" body-const] ["bad-name" bad-name] ["export-clash" clash]]]
      (let [[result bad] (lib/compile-source compiler output name src 1)]
        (when (.exists bad) (mac/fail (str name ": an object was written")))
        (let [m (.strip (lib/message-of result))]
          (.__setitem__ report name (str "refused: " (subs m 0 (min 120 (count m))))))))
    (.write_text (.joinpath output "image.kotoba") image)
    (let [result (mac/native-run compiler output ["compile" "image.kotoba" "--target" "x86_64-aiueos-kernel-v1" "--artifact" "image"
                                                  "--output" "image.elf" "--fuel" "1024"] :expected 1)]
      (when (or (.exists (.joinpath output "image.elf")) (not (.__contains__ (lib/message-of result) "E7102")))
        (mac/fail "an extern declaration on the image route was not refused with E7102"))
      (.__setitem__ report "image" "refused E7102"))
    (lib/emit! output report "PASS_AIUEOS_OBJECT_EXTERNS")))

(defn -main [& args] (lib/cli-main args main))

(when (some #(or (= % "check-aiueos-object-externs.cljc") (str/ends-with? % "/check-aiueos-object-externs.cljc")) sys/argv)
  (apply -main *command-line-args*))
