;; Observe the bounded AIUEOS user-v2 Goal input ELF contract: fixed sources, refusal vectors and the byte verifier
;; (shared by check-aiueos-user-v2-native and the Mac user-v2 / user-v5 layout gates). Amu emits the ELF. This
;; observer checks its image and fixed source/refusal vectors; it does not implement guest behavior or establish CPL3
;; execution. Ported from check-aiueos-user-v2-native.py (Basilisp, JUN-974).
(ns aiueos-user-v2
  (:require [gate-util :as u])
  (:import operator struct))

(def target "x86_64-aiueos-user-v2")
(def source
  (str "(ns aiueos-user-goal-v2 (:export [main]))\n"
       "(defn main [request :i64 request-bytes :i64] :i64 "
       "(kernel-load-u32 request request-bytes 0))\n"))
(def constant
  (str "(ns aiueos-user-goal-v2 (:export [main]))\n"
       "(defn main [request :i64 request-bytes :i64] :i64 42)\n"))
(def refusals
  [["arity" (str "(ns aiueos-user-goal-v2 (:export [main]))\n" "(defn main [request :i64] :i64 request)\n") "E7102"]
   ["base" (str "(ns aiueos-user-goal-v2 (:export [main]))\n"
                "(defn main [request :i64 request-bytes :i64] :i64 "
                "(kernel-load-u32 (+ request 4) request-bytes 0))\n") "E7106"]
   ["length" (str "(ns aiueos-user-goal-v2 (:export [main]))\n"
                  "(defn main [request :i64 request-bytes :i64] :i64 "
                  "(kernel-load-u32 request 64 0))\n") "E7106"]
   ["effect" (str "(ns aiueos-user-goal-v2 (:export [main]))\n"
                  "(defn main [request :i64 request-bytes :i64] :i64 "
                  "(let [x (typed-cap-call :io/write :string :string \"denied\")] 42))\n") "E7101"]
   ["export" (str "(ns aiueos-user-goal-v2 (:export [other]))\n"
                  "(defn other [request :i64 request-bytes :i64] :i64 42)\n") "E7102"]
   ["parameter-type" (str "(ns aiueos-user-goal-v2 (:export [main]))\n"
                          "(defn main [request :bool request-bytes :i64] :i64 42)\n") "E7102"]
   ["return-type" (str "(ns aiueos-user-goal-v2 (:export [main]))\n"
                       "(defn main [request :i64 request-bytes :i64] :bool true)\n") "E7102"]])

(defn- unpack [fmt b off] (vec (struct/unpack_from fmt b off)))
(defn- need [condition message] (when-not condition (throw (python/ValueError message))))

(defn verify
  "ValueError unless blob is exactly the v2 Goal image."
  [blob]
  (need (= (python/len blob) 8280) "unexpected user-v2 image length")
  (let [header (unpack "<16sHHIQQQIHHHHHH" blob 0)]
    (need (and (u/deq (first header) (operator/add (u/hex->bytes "7f454c46020101") (u/bytes-of-n 9 0)))
                   (= (vec (rest header)) [2 62 1 0x220000 64 0 0 64 56 2 0 0 0]))
              "ELF identity"))
  (let [[rx rw] (for [i (range 2)] (unpack "<IIQQQQQQ" blob (+ 64 (* 56 i))))]
    (need (= (subvec rx 0 5) [1 5 4096 0x220000 0x220000]) "RX segment identity")
    (need (and (< 80 (nth rx 5)) (= (nth rx 5) (nth rx 6)) (<= (nth rx 6) 4096) (= (nth rx 7) 4096)) "RX segment bounds")
    (need (= rw [1 6 8192 0x221000 0x221000 88 320 4096]) "RW segment contract")
    (need (and (not (python/any (u/bslice blob 176 4096))) (not (python/any (u/bslice blob (+ 4096 (nth rx 5)) 8192))))
              "ELF padding")
    (let [prefix (u/hex->bytes (str "4c8d0df90f0000498db900010000be40000000e838000000" "488905e10f0000f390ebfc"))
          n (python/len prefix)]
      (need (u/deq (u/bslice blob 4096 (+ 4096 n)) prefix) "v2 entry and arguments")
      (need (u/deq (u/bslice blob (+ 4096 n) (+ 4096 48)) (u/bytes-of-n (- 48 n) 0x90)) "entry padding"))
    (need (u/deq (u/bslice blob (+ 4096 48) (+ 4096 60)) (u/hex->bytes "b805000000488b7f500f05c3")) "syscall trampoline")
    (need (u/deq (u/bslice blob (+ 4096 60) (+ 4096 80)) (u/bytes-of-n 20 0x90)) "trampoline padding")
    (let [context (python/bytearray 88)]
      (struct/pack_into "<Q" context 8 256)
      (struct/pack_into "<Q" context 48 0x220030)
      (need (u/deq (u/bslice blob 8192 (python/len blob)) context) "v2 image must not bake in Goal or authority"))))
