(ns kotoba-bench.scalar
  (:require [goog.object :as gobj]))

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
  (loop [index 0 state 2463534242]
    (if (< index iterations)
      (let [x1 (bit-xor state (bit-shift-left state 13))
            x2 (bit-xor x1 (unsigned-bit-shift-right x1 17))
            x3 (bit-xor x2 (bit-shift-left x2 5))]
        (recur (inc index) (unsigned-bit-shift-right x3 0)))
      state)))

(defn vector-allocation-checksum [iterations]
  (loop [index 0 state 2463534242 total 0]
    (if (< index iterations)
      (let [values (vector 3 5 8 13 21 34 55 89)
            x1 (bit-xor state (bit-shift-left state 13))
            x2 (bit-xor x1 (unsigned-bit-shift-right x1 17))
            next (unsigned-bit-shift-right (bit-xor x2 (bit-shift-left x2 5)) 0)]
        (recur (inc index) next (+ total (nth values (bit-and next 7)))))
      total)))

(defn retain-vector [values]
  values)

(defn vector-materialization-checksum [iterations]
  (loop [index 0 state 2463534242 total 0]
    (if (< index iterations)
      (let [values (vector 3 5 8 13 21 34 55 89)
            x1 (bit-xor state (bit-shift-left state 13))
            x2 (bit-xor x1 (unsigned-bit-shift-right x1 17))
            next (unsigned-bit-shift-right (bit-xor x2 (bit-shift-left x2 5)) 0)]
        (recur (inc index) next
               (+ total
                  (nth (if (zero? (bit-and index 511))
                         (retain-vector values)
                         values)
                       (bit-and next 7)))))
      total)))

(defn -main [& args]
  (let [workload (or (first args) "scalar")
        once? (= "--once" (second args))
        iterations (js/Number (or (nth args 2 nil) "1"))
        warmup-iterations (js/Number (or (nth args 3 nil)
                                         (str (min iterations 1000))))
        run-workload (case workload
                       "scalar" checksum
                       "branch" branch-checksum
                       "mix" xorshift32-checksum
                       "vector" vector-allocation-checksum
                       "vector-materialize" vector-materialization-checksum
                       (throw (js/Error. "unknown benchmark workload")))]
    (if once?
      (js/console.log (.stringify js/JSON #js {:checksum (run-workload iterations)}))
      (do
        (run-workload warmup-iterations)
        (let [hrtime (gobj/get js/process "hrtime")
              started (hrtime)
              result (run-workload iterations)
              delta (hrtime started)
              elapsed (+ (* (aget delta 0) 1000000000) (aget delta 1))]
          (js/console.log
           (.stringify js/JSON
                       #js {:iterations iterations
                            :warmupIterations warmup-iterations
                            :checksum result
                            :elapsedNanoseconds elapsed})))))))

(set! *main-cli-fn* -main)
