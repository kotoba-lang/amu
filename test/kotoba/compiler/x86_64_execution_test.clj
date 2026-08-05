
;; Everything below is a shape native_executor_test already executes -- on
;; AArch64, which is the only CPU here. The disp8 bug showed that "emits and
;; the other ISA runs it" is not evidence that THIS ISA runs it, so the whole
;; verified surface is re-run through real x86-64 rather than a sample of it.
(def ^:private f64-one 4607182418800017408)
(def ^:private f64-two 4611686018427387904)
(def ^:private f64-nan 9221120237041090560)

(defn- f64c [op a b] (str "(defn main [] (if (" op " (f64-from-bits " a
                          ") (f64-from-bits " b ")) 1 0))"))

(deftest the-aarch64-verified-surface-also-executes-on-real-x86-64
  (if-not @harness
    (println "skipping: no x86-64 cross-compile + execution on this host")
    (doseq [[why source expected]
            [["arithmetic" "(defn main [] (+ (* 3 4) (quot 10 2)))" 17]
             ["comparison" "(defn main [] (if (< 1 2) 7 8))" 7]
             ["recursion" (str "(defn f [n] (if (< n 1) 0 (+ n (f (- n 1)))))"
                               " (defn main [] (f 5))") 15]
             ["let" "(defn main [] (let [a 3 b 4] (* a b)))" 12]
             ["bit-not" "(defn main [] (bit-not 5))" -6]
             ["bit-or" "(defn main [] (bit-or 5 2))" 7]
             ["i64 shift" "(defn main [] (i64-shift-left 1 5))" 32]
             ["i32 wrapping" "(defn main [] (i32-wrapping-add 2147483647 1))" -2147483648]
             ["u32 shift" "(defn main [] (u32-shift-right 256 4))" 16]
             ["bool-not" "(defn main [] (if (bool-not true) 1 0))" 0]
             ["pair" "(defn main [] (pair-first (pair 9 8)))" 9]
             ["string=?" "(defn main [] (if (string=? \"ab\" \"ab\") 1 0))" 1]
             ["string-concat" (str "(defn main [] (string-byte-length"
                                   " (string-concat \"ab\" \"cde\")))") 5]
             ["keyword literal" "(defn main [] (string-byte-length :abc))" 4]
             ["record" (str "(defn main [] (record-get [:record :r [[:a :i64]"
                            " [:b :i64]]] (record-new [:record :r [[:a :i64]"
                            " [:b :i64]]] 4 9) :b))") 9]
             ["option" "(defn main [] (option-value (option-some 5) 0))" 5]
             ["result" "(defn main [] (if (result-ok? (result-ok 5)) 1 0))" 1]
             ["f64 arithmetic" (str "(defn main [] (f64-to-bits (f64-add"
                                    " (f64-from-bits " f64-one ")"
                                    " (f64-from-bits " f64-one "))))") f64-two]
             ["f64-lt" (f64c "f64-lt" f64-one f64-two) 1]
             ["f64-gt ordered" (f64c "f64-gt" f64-one f64-two) 0]
             ["f64-eq" (f64c "f64-eq" f64-one f64-one) 1]
             ;; The NaN rows: setb/setbe are TRUE on unordered, so a naive
             ;; encoding passes every ordered row above and fails these.
             ["f64-eq NaN" (f64c "f64-eq" f64-nan f64-nan) 0]
             ["f64-lt NaN" (f64c "f64-lt" f64-nan f64-one) 0]
             ["f64-le NaN" (f64c "f64-le" f64-nan f64-one) 0]
             ["f64-ge NaN" (f64c "f64-ge" f64-nan f64-one) 0]
             ["f64-unordered" (f64c "f64-unordered" f64-nan f64-one) 1]
             ["f64-unordered ordered" (f64c "f64-unordered" f64-one f64-two) 0]
             ["kgraph" (str "(defn main [] (do (kgraph-assert! 1 2 3)"
                            " (kgraph-get 1 2)))") 3]]]
      (testing why
        (let [report (run-x86-64 source)]
          (is (not (str/includes? report "KEXE_TRAP"))
              (str why " must not trap: " (str/trim report)))
          (is (str/includes? report (str ":result " expected))
              (str why " => " (str/trim report))))))))

(deftest a-capability-call-executes-on-real-x86-64
  (if-not @harness
    (println "skipping: no x86-64 cross-compile + execution on this host")
    (let [report (run-x86-64 "(defn main [] (cap-call 1 5))" "1")]
      (is (not (str/includes? report "KEXE_TRAP")) (str/trim report))
      (is (str/includes? report ":result 5") (str/trim report)))))
