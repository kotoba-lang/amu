;; Fixed sources and the byte verifier of the AIUEOS user ELF v1 scalar ABI (shared by check-aiueos-user-elf-native
;; and the Mac user-target gate). Ported from check-aiueos-user-elf-native.py (Basilisp, JUN-974).
(ns aiueos-user-elf
  (:require [gate-util :as u])
  (:import operator struct))

(def source "(ns aiueos-user-scalar (:export [main]))\n(defn main [] :i64 42)\n")
(def effect
  (str "(ns aiueos-user-effect (:export [main]))\n"
       "(defn main [] :i64 (let [x (typed-cap-call :io/write :string :string \"denied\")] 42))\n"))
(def parameter
  (str "(ns aiueos-user-parameter (:export [main]))\n"
       "(defn main [goal :i64] :i64 goal)\n"))
(def target "x86_64-aiueos-user-v1")

(defn- unpack [fmt b off] (vec (struct/unpack_from fmt b off)))

(defn verify
  "AssertionError unless blob is exactly the v1 scalar user image."
  [blob]
  (u/chk (= (python/len blob) 8280) "unexpected image length")
  (let [header (unpack "<16sHHIQQQIHHHHHH" blob 0)]
    (u/chk (and (u/deq (first header) (operator/add (u/hex->bytes "7f454c46020101") (u/bytes-of-n 9 0)))
                (= (vec (rest header)) [2 62 1 0x220000 64 0 0 64 56 2 0 0 0]))
           "ELF identity"))
  (let [[rx rw] (for [i (range 2)] (unpack "<IIQQQQQQ" blob (+ 64 (* 56 i))))]
    (u/chk (= (subvec rx 0 5) [1 5 4096 0x220000 0x220000]))
    (u/chk (and (< 64 (nth rx 5)) (= (nth rx 5) (nth rx 6)) (<= (nth rx 6) 4096) (= (nth rx 7) 4096)))
    (u/chk (= rw [1 6 8192 0x221000 0x221000 88 88 4096]))
    (u/chk (and (not (python/any (u/bslice blob 176 4096)))
                (not (python/any (u/bslice blob (+ 4096 (nth rx 5)) 8192)))))
    (u/chk (u/deq (u/bslice blob 4096 4103) (u/hex->bytes "4c8d0df90f0000")))
    (u/chk (u/deq (u/bslice blob 0x1020 0x102c) (u/hex->bytes "b805000000488b7f500f05c3")))
    (let [context (python/bytearray 88)]
      (struct/pack_into "<Q" context 8 256)
      (struct/pack_into "<Q" context 48 0x220020)
      (u/chk (u/deq (u/bslice blob 8192 (python/len blob)) context) "capabilities or runtime handle are nonzero"))))
