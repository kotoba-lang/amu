(ns bench.runtime-kernel)

(defn kernel [n]
  (let [v1 (+ (* n 48271) 1) x1 (- v1 (* (quot v1 2147483647) 2147483647))
        v2 (+ (* x1 48271) 1) x2 (- v2 (* (quot v2 2147483647) 2147483647))
        v3 (+ (* x2 48271) 1) x3 (- v3 (* (quot v3 2147483647) 2147483647))
        v4 (+ (* x3 48271) 1) x4 (- v4 (* (quot v4 2147483647) 2147483647))
        v5 (+ (* x4 48271) 1) x5 (- v5 (* (quot v5 2147483647) 2147483647))
        v6 (+ (* x5 48271) 1) x6 (- v6 (* (quot v6 2147483647) 2147483647))
        v7 (+ (* x6 48271) 1) x7 (- v7 (* (quot v7 2147483647) 2147483647))
        v8 (+ (* x7 48271) 1)]
    (- v8 (* (quot v8 2147483647) 2147483647))))

(defn positive-arg [index name]
  (let [value (js/Number (aget (aget js/process "argv") (+ index 2)))]
    (when-not (and (js/Number.isSafeInteger value) (pos? value))
      (.error js/console (str name " must be a positive integer"))
      (.call (aget js/process "exit") js/process 2))
    value))

(defn now-nanoseconds []
  (let [hrtime (aget js/process "hrtime")
        bigint (aget hrtime "bigint")]
    (.call bigint hrtime)))

(defn main []
  (let [n (positive-arg 0 "n")
        calls (positive-arg 1 "calls")
        warmup (positive-arg 2 "warmup")]
    (loop [remaining warmup]
      (when (pos? remaining)
        (kernel n)
        (recur (dec remaining))))
    (let [started (now-nanoseconds)
          result (loop [remaining calls result 0]
                   (if (zero? remaining)
                     result
                     (recur (dec remaining) (kernel n))))
          elapsed (- (now-nanoseconds) started)]
      (.log js/console
            (.stringify js/JSON
                        (clj->js {:format "kotoba.runtime-sample/v1"
                                  :calls calls
                                  :warmupCalls warmup
                                  :elapsedNanoseconds (js/Number elapsed)
                                  :result result}))))))

(set! *main-cli-fn* main)
