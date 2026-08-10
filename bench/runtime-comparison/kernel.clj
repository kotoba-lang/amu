(set! *unchecked-math* :warn-on-boxed)

(defn kernel ^long [^long n]
  (let [v1 (+ (* n 48271) 1) x1 (- v1 (* (quot v1 2147483647) 2147483647))
        v2 (+ (* x1 48271) 1) x2 (- v2 (* (quot v2 2147483647) 2147483647))
        v3 (+ (* x2 48271) 1) x3 (- v3 (* (quot v3 2147483647) 2147483647))
        v4 (+ (* x3 48271) 1) x4 (- v4 (* (quot v4 2147483647) 2147483647))
        v5 (+ (* x4 48271) 1) x5 (- v5 (* (quot v5 2147483647) 2147483647))
        v6 (+ (* x5 48271) 1) x6 (- v6 (* (quot v6 2147483647) 2147483647))
        v7 (+ (* x6 48271) 1) x7 (- v7 (* (quot v7 2147483647) 2147483647))
        v8 (+ (* x7 48271) 1)]
    (- v8 (* (quot v8 2147483647) 2147483647))))

(defn positive-arg ^long [index name]
  (let [^long value (try (Long/parseLong (nth *command-line-args* index))
                         (catch Exception _ 0))]
    (when-not (< (long 0) value)
      (binding [*out* *err*] (println name "must be a positive integer"))
      (System/exit 2))
    value))

(let [n (positive-arg 0 "n")
      calls (positive-arg 1 "calls")
      warmup (positive-arg 2 "warmup")]
  (loop [remaining warmup result (long 0)]
    (when (pos? remaining)
      (kernel n)
      (recur (unchecked-dec remaining) result)))
  (let [started (System/nanoTime)
        result (loop [remaining calls result (long 0)]
                 (if (zero? remaining)
                   result
                   (recur (unchecked-dec remaining) (kernel n))))
        elapsed (- (System/nanoTime) started)]
    (println (str "{\"format\":\"kotoba.runtime-sample/v1\","
                  "\"calls\":" calls ",\"warmupCalls\":" warmup ","
                  "\"elapsedNanoseconds\":" elapsed ",\"result\":" result "}"))))
