(ns kotoba-bench.scalar)

(set! *warn-on-reflection* true)

(defn multiply [left right]
  (unchecked-multiply (long left) (long right)))

(defn checksum [iterations]
  (let [limit (long iterations)
        product (long (multiply 6 7))]
    (loop [index (long 0) total (long 0)]
      (if (< index limit)
        (recur (unchecked-inc index) (unchecked-add total product))
        total))))

(defn branch-checksum [iterations]
  (let [limit (long iterations)
        half (quot limit 2)]
    (loop [index (long 0) total (long 0)]
      (if (< index limit)
        (recur (unchecked-inc index)
               (unchecked-add total (if (< index half) (long 41) (long 43))))
        total))))

(defn xorshift32-checksum [iterations]
  (let [limit (long iterations)
        mask 0xffffffff]
    (loop [index (long 0) state (long 2463534242)]
      (if (< index limit)
        (let [x1 (bit-and mask (bit-xor state (bit-shift-left state 13)))
              x2 (bit-and mask (bit-xor x1 (unsigned-bit-shift-right x1 17)))
              x3 (bit-and mask (bit-xor x2 (bit-shift-left x2 5)))]
          (recur (unchecked-inc index) x3))
        state))))

(defn vector-allocation-checksum [iterations]
  (let [limit (long iterations)
        mask (long 0xffffffff)]
    (loop [index (long 0) state (long 2463534242) total (long 0)]
      (if (< index limit)
        (let [values (vector 3 5 8 13 21 34 55 89)
              x1 (bit-and mask (bit-xor state (bit-shift-left state 13)))
              x2 (bit-and mask (bit-xor x1 (unsigned-bit-shift-right x1 17)))
              next (bit-and mask (bit-xor x2 (bit-shift-left x2 5)))]
          (recur (unchecked-inc index) next
                 (unchecked-add total (long (nth values (bit-and next 7))))))
        total))))

(defn retain-vector [values]
  values)

(defn vector-materialization-checksum [iterations]
  (let [limit (long iterations)
        mask (long 0xffffffff)]
    (loop [index (long 0) state (long 2463534242) total (long 0)]
      (if (< index limit)
        (let [values (vector 3 5 8 13 21 34 55 89)
              x1 (bit-and mask (bit-xor state (bit-shift-left state 13)))
              x2 (bit-and mask (bit-xor x1 (unsigned-bit-shift-right x1 17)))
              next (bit-and mask (bit-xor x2 (bit-shift-left x2 5)))]
          (recur (unchecked-inc index) next
                 (unchecked-add total
                                (long (nth (if (zero? (bit-and index 511))
                                             (retain-vector values)
                                             values)
                                           (bit-and next 7))))))
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
