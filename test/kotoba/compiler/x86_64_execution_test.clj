(ns kotoba.compiler.x86-64-execution-test
  "Executes x86-64 artifacts on a machine whose CPU is not x86-64.

  This exists because its absence let a real bug ship twice. `emit-heap-call`
  encoded every context offset as a signed disp8, so the callbacks at 136 and
  144 called the wrong address; AArch64 cannot express that mistake, and every
  execution test here runs on AArch64, so nothing failed. Compiling both
  artifacts with the pre-fix backend and running them through this harness
  segfaults -- which is what a test that had existed would have said.

  macOS on Apple silicon can both cross-compile to x86-64 (`cc -arch x86_64`)
  and run the result (Rosetta 2). Where either is missing the tests skip rather
  than fail: on an x86-64 host the ordinary native_executor_test already
  executes this ISA, and this file is only interesting on a host that does not."
  (:require [clojure.java.io :as io]
            [clojure.java.shell :as shell]
            [clojure.string :as str]
            [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]))

(defn- x86-64-execution-available? []
  (and (str/includes? (str/lower-case (System/getProperty "os.name")) "mac")
       (let [probe (io/file (System/getProperty "java.io.tmpdir")
                            "kotoba-x86-probe.c")
             out (io/file (System/getProperty "java.io.tmpdir")
                          "kotoba-x86-probe.bin")]
         (spit probe "int main(void){return 7;}")
         (and (zero? (:exit (shell/sh "cc" "-arch" "x86_64" (.getPath probe)
                                      "-o" (.getPath out))))
              (= 7 (:exit (shell/sh (.getPath out))))))))

(defonce ^:private harness
  (delay
    (when (x86-64-execution-available?)
      (let [loader (io/file (System/getProperty "java.io.tmpdir")
                            "kotoba-x86-loader.bin")
            build (shell/sh "cc" "-arch" "x86_64" "-std=c11" "-O2"
                            "-Wall" "-Wextra" "-Werror"
                            "tools/kexe_loader.c" "-o" (.getPath loader))]
        (when (zero? (:exit build)) (.getPath loader))))))

(defn- run-x86-64
  ([source] (run-x86-64 source "-" {:allow #{}}))
  ([source allow policy]
  (let [artifact (:artifact (compiler/compile-source source :x86_64-kotoba-v1
                                                     policy))
        code (io/file (System/getProperty "java.io.tmpdir") "kotoba-x86-code.bin")
        offset (get-in artifact [:exports 'main :offset])]
    (with-open [out (io/output-stream code)]
      (.write out (byte-array (map #(unchecked-byte (bit-and (int %) 0xff))
                                   (:code artifact)))))
    (:out (shell/sh @harness (.getPath code) (str offset) "0" "x86_64" allow
                    :env (assoc (into {} (System/getenv))
                                "KEXE_STRUCTURED_REPORT" "1"))))))

;; The two host calls whose context offsets exceed the disp8 range. A wrong
;; displacement here is not subtle: it calls into whatever precedes the
;; context, and both of these segfaulted before the encoding was fixed.
(deftest host-calls-past-disp8-execute-on-real-x86-64
  (if-not @harness
    (println "skipping: no x86-64 cross-compile + execution on this host")
    (doseq [[why source expected]
            [["a program with no host call" "(defn main [] 42)" 42]
             ["string-substring at offset 136"
              (str "(defn main [] (string-byte-length (string-substring"
                   " (string-concat \"ab\" \"cde\") 1 4)))") 3]
             ["string-code-point-at at offset 144"
              "(defn main [] (string-code-point-at \"日本語\" 3))" 26412]]]
      (testing why
        (let [report (run-x86-64 source)]
          (is (not (str/includes? report "KEXE_TRAP"))
              (str why " must not trap: " (str/trim report)))
          (is (str/includes? report (str ":result " expected))
              (str why " => " (str/trim report))))))))

;; Everything below is a shape native_executor_test already executes -- on
;; AArch64, which is the only CPU here. The disp8 bug showed that "it emits,
;; and the other ISA runs it" is not evidence that THIS ISA runs it, so the
;; verified surface is re-run through real x86-64 rather than sampled.
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
             ["u32 shift" "(defn main [] (u32-shift-right 256 4))" 16]
             ["pair" "(defn main [] (pair-first (pair 9 8)))" 9]
             ["string=?" "(defn main [] (if (string=? \"ab\" \"ab\") 1 0))" 1]
             ["string-concat" (str "(defn main [] (string-byte-length"
                                   " (string-concat \"ab\" \"cde\")))") 5]
             ["bool-not" "(defn main [] (if (bool-not true) 1 0))" 0]
             ["i32 wrapping" "(defn main [] (i32-wrapping-add 2147483647 1))"
              -2147483648]
             ["record projection"
              (str "(defn main [] (record-get [:record :t/r [[:a :i64] [:b :i64]]]"
                   " (record-new [:record :t/r [[:a :i64] [:b :i64]]] 4 9) :b))") 9]
             ["option" "(defn main [] (option-value (option-some 5) 0))" 5]
             ["result" "(defn main [] (if (result-ok? (result-ok 5)) 1 0))" 1]
             ["f64 arithmetic" (str "(defn main [] (f64-to-bits (f64-add"
                                    " (f64-from-bits " f64-one ")"
                                    " (f64-from-bits " f64-one "))))") f64-two]
             ["f64-lt" (f64c "f64-lt" f64-one f64-two) 1]
             ["f64-gt ordered" (f64c "f64-gt" f64-one f64-two) 0]
             ["f64-eq" (f64c "f64-eq" f64-one f64-one) 1]
             ;; The NaN rows: setb/setbe are TRUE on unordered, so a naive
             ;; encoding passes every ordered row above and fails only these.
             ["f64-eq NaN" (f64c "f64-eq" f64-nan f64-nan) 0]
             ["f64-lt NaN" (f64c "f64-lt" f64-nan f64-one) 0]
             ["f64-le NaN" (f64c "f64-le" f64-nan f64-one) 0]
             ["f64-ge NaN" (f64c "f64-ge" f64-nan f64-one) 0]
             ["f64-unordered NaN" (f64c "f64-unordered" f64-nan f64-one) 1]
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
    (let [report (run-x86-64 "(defn main [] (cap-call 1 5))" "1"
                             {:allow #{[:cap/call 1]}})]
      (is (not (str/includes? report "KEXE_TRAP")) (str/trim report))
      ;; The qualification host's cap-call provider adds one.
      (is (str/includes? report ":result 6") (str/trim report)))))
