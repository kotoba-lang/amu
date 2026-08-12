(ns kotoba-bench.scalar-boxed)

(defn multiply [left right]
  (* left right))

(defn checksum [iterations]
  (loop [index 0 total 0]
    (if (< index iterations)
      (recur (inc index) (+ total (multiply 6 7)))
      total)))

(defn branch-checksum [iterations]
  (let [half (quot iterations 2)]
    (loop [index 0 total 0]
      (if (< index iterations)
        (recur (inc index) (+ total (if (< index half) 41 43)))
        total))))

(defn xorshift32-checksum [iterations]
  (let [mask 0xffffffff]
    (loop [index 0 state 2463534242]
      (if (< index iterations)
        (let [x1 (bit-and mask (bit-xor state (bit-shift-left state 13)))
              x2 (bit-and mask (bit-xor x1 (unsigned-bit-shift-right x1 17)))
              x3 (bit-and mask (bit-xor x2 (bit-shift-left x2 5)))]
          (recur (inc index) x3))
        state))))

(defn vector-allocation-checksum [iterations]
  (let [mask 0xffffffff]
    (loop [index 0 state 2463534242 total 0]
      (if (< index iterations)
        (let [values (vector 3 5 8 13 21 34 55 89)
              x1 (bit-and mask (bit-xor state (bit-shift-left state 13)))
              x2 (bit-and mask (bit-xor x1 (unsigned-bit-shift-right x1 17)))
              next (bit-and mask (bit-xor x2 (bit-shift-left x2 5)))]
          (recur (inc index) next (+ total (nth values (bit-and next 7)))))
        total))))

(defn retain-vector [values]
  values)

(defn vector-materialization-checksum [iterations]
  (let [mask 0xffffffff]
    (loop [index 0 state 2463534242 total 0]
      (if (< index iterations)
        (let [values (vector 3 5 8 13 21 34 55 89)
              x1 (bit-and mask (bit-xor state (bit-shift-left state 13)))
              x2 (bit-and mask (bit-xor x1 (unsigned-bit-shift-right x1 17)))
              next (bit-and mask (bit-xor x2 (bit-shift-left x2 5)))]
          (recur (inc index) next
                 (+ total
                    (nth (if (zero? (bit-and index 511))
                           (retain-vector values)
                           values)
                         (bit-and next 7)))))
        total))))

(defn -main [& args]
  (let [workload (or (first args) "scalar")
        once? (= "--once" (second args))
        iterations (Long/parseLong (or (nth args 2 nil) "1"))
        warmup-iterations (Long/parseLong
                           (or (nth args 3 nil) (str (min iterations 1000))))
        run-workload (case workload
                       "scalar" checksum
                       "branch" branch-checksum
                       "mix" xorshift32-checksum
                       "vector" vector-allocation-checksum
                       "vector-materialize" vector-materialization-checksum
                       (throw (ex-info "unknown benchmark workload" {:workload workload})))]
    (if once?
      (println (str "{\"checksum\":" (run-workload iterations) "}"))
      (do
        (run-workload warmup-iterations)
        (let [started (System/nanoTime)
              result (run-workload iterations)
              elapsed (- (System/nanoTime) started)]
          (println (str "{\"iterations\":" iterations
                        ",\"warmupIterations\":" warmup-iterations
                        ",\"checksum\":" result
                        ",\"elapsedNanoseconds\":" elapsed "}")))))))
