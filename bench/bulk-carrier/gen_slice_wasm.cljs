;; Emits a hand-written wasm32 module holding TWO arms with byte-identical loop
;; shape, so their difference is exactly one element access:
;;
;;   hand-noref : acc + i                      (control; must equal the Kotoba
;;                                              `run-noref` arm, which is how we
;;                                              know the hand-written loop is the
;;                                              same loop)
;;   hand-slice : acc + load(base + i*8)       with the unsigned bounds test that
;;                                              a real lowering must emit
;;
;; This is a stand-in for a lowering that does not exist yet. It is honest about
;; exactly one thing: what instruction sequence `slice-at` would compile to on
;; wasm32, and what that sequence costs in the same engine, in the same
;; call-based loop, as the Kotoba arms. It is NOT evidence that the compiler can
;; emit it; that is a separate claim requiring the compiler change.
;;
;; Base and length are folded to constants. A real lowering carries them in
;; locals, which is at least as cheap as an i32.const, so this does not flatter
;; the proposal.

(def N 64)

(defn uleb [n]
  (loop [n n out []]
    (let [b (bit-and n 0x7f) n' (unsigned-bit-shift-right n 7)]
      (if (zero? n') (conj out b) (recur n' (conj out (bit-or b 0x80)))))))

(defn sleb [n]
  (loop [n n out []]
    (let [b (bit-and n 0x7f) n' (bit-shift-right n 7)
          done? (or (and (zero? n') (zero? (bit-and b 0x40)))
                    (and (= n' -1) (pos? (bit-and b 0x40))))]
      (if done? (conj out b) (recur n' (conj out (bit-or b 0x80)))))))

(defn vec* [items] (into (uleb (count items)) (apply concat items)))
(defn section [id payload] (into [id] (concat (uleb (count payload)) payload)))
(defn name-bytes [s] (let [b (mapv #(.charCodeAt s %) (range (count s)))]
                       (into (uleb (count b)) b)))

(def i64t 0x7e)
;; (i64,i64,i64)->i64  and  (i64)->i64
(def types [(concat [0x60] (uleb 3) [i64t i64t i64t] (uleb 1) [i64t])
            (concat [0x60] (uleb 1) [i64t]           (uleb 1) [i64t])])

(defn lget [i] (into [0x20] (uleb i)))
(defn call [i] (into [0x10] (uleb i)))
(def i64-add [0x7c])
(def i64-lt-s [0x53])
(def i64-ge-u [0x5a])
(defn i64c [n] (into [0x42] (sleb n)))
(defn i32c [n] (into [0x41] (sleb n)))

;; bounds test + address + load, i.e. what `slice-at` must lower to
(def slice-at
  (concat (lget 0) (i64c N) i64-ge-u          ;; i >= len  (unsigned)
          [0x04 0x40] [0x00] [0x0b]           ;; if (void) { unreachable }
          (lget 0) [0xa7]                     ;; i32.wrap_i64
          (i32c 8) [0x6c]                     ;; * 8
          [0x29 0x03 0x00]))                  ;; i64.load align=8 offset=0

;; loop(i,n,acc) = if i<n then loop(i+1, n, acc+ELEM) else acc
(defn loop-body [self elem]
  (concat (lget 0) (lget 1) i64-lt-s
          [0x04 i64t]
          (lget 0) (i64c 1) i64-add
          (lget 1)
          (lget 2) elem i64-add
          (call self)
          [0x05]
          (lget 2)
          [0x0b 0x0b]))

;; nest(k,n,acc) = if k<n then nest(k+1, n, acc + callee(0,64,0)) else acc
(defn nest-body [self callee]
  (loop-body self (concat (i64c 0) (i64c N) (i64c 0) (call callee))))

(defn run-body [outer] (concat (i64c 0) (lget 0) (i64c 0) (call outer) [0x0b]))

(defn body [code] (let [b (into (uleb 0) code)] (into (uleb (count b)) b)))

;; f0..f3 noref, f4..f7 slice
(def codes
  [(body (loop-body 0 (lget 0)))          ;; f0 noref-loop : acc + i
   (body (nest-body 1 0))                 ;; f1 noref-inner
   (body (nest-body 2 1))                 ;; f2 noref-outer
   (body (run-body 2))                    ;; f3 run-noref
   (body (loop-body 4 slice-at))          ;; f4 slice-loop : acc + load
   (body (nest-body 5 4))                 ;; f5 slice-inner
   (body (nest-body 6 5))                 ;; f6 slice-outer
   (body (run-body 6))])                  ;; f7 run-slice

(def funcs [0 0 0 1 0 0 0 1])             ;; type index per function

;; Values 1..N, little-endian i64.  Written byte-wise WITHOUT a shift: in
;; ClojureScript `unsigned-bit-shift-right` is a 32-bit operation, so a shift of
;; 56 silently becomes a shift of 24 and the high four bytes come out wrong.
;; The correctness gate below caught exactly that; every value here is < 256,
;; so the low byte carries it and the other seven are zero.
(def data-bytes
  (vec (mapcat (fn [i] (into [(inc i)] (repeat 7 0))) (range N))))

(def module
  (vec (concat [0x00 0x61 0x73 0x6d 0x01 0x00 0x00 0x00]
               (section 1 (vec* types))
               (section 3 (into (uleb (count funcs)) (mapcat uleb funcs)))
               (section 5 (into (uleb 1) [0x00 0x01]))                 ;; 1 memory, min 1 page
               (section 7 (vec* [(concat (name-bytes "run-noref") [0x00] (uleb 3))
                                 (concat (name-bytes "run-slice") [0x00] (uleb 7))]))
               (section 10 (vec* codes))
               (section 11 (vec* [(concat (uleb 0) (i32c 0) [0x0b]
                                          (uleb (count data-bytes)) data-bytes)])))))

(def fs (js/require "fs"))
(.writeFileSync fs "/tmp/bulk/handslice.wasm" (js/Buffer.from (clj->js module)))
(println "wrote" (count module) "bytes")
