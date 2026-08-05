(ns kotoba.compiler.isa-execution-test
  "Runs ONE table of programs through BOTH native ISAs, as real processes.

  This exists because its absence let a real bug ship twice. `emit-heap-call`
  encoded every context offset as a signed disp8, so the callbacks at 136 and
  144 called the wrong address. AArch64 cannot express that mistake, and every
  execution test ran on AArch64, so nothing failed -- compiling the same two
  programs with the pre-fix backend and running them here segfaults.

  The table is shared rather than duplicated per ISA on purpose: the property
  under test is that one program produces one value on both backends, so a
  divergence has to show up as the same row passing on one ISA and failing on
  the other. Two separate tables could drift apart and still both be green.

  An ISA runs if a loader can be built and executed for it. The host ISA always
  can; the other needs cross-compilation and emulation, which macOS on Apple
  silicon has (`cc -arch x86_64` plus Rosetta 2). Missing ones are skipped and
  named, so a run that covered only one ISA never looks like it covered both."
  (:require [clojure.java.io :as io]
            [clojure.java.shell :as shell]
            [clojure.string :as str]
            [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]))

;; loader argv name -> [cc -arch value, compiler target]
(def ^:private isas
  {"x86_64" ["x86_64" :x86_64-kotoba-v1]
   "aarch64" ["arm64" :aarch64-kotoba-v1]})

(defn- tmp [name] (io/file (System/getProperty "java.io.tmpdir") name))

(defn- macos? [] (= "Mac OS X" (System/getProperty "os.name")))

(defn- host-isa []
  (case (str/lower-case (System/getProperty "os.arch"))
    ("amd64" "x86_64") "x86_64"
    ("aarch64" "arm64") "aarch64"
    nil))

(defn- cc-command
  "Build COMMAND for ISA. Apple's `cc -arch` selects a native/Rosetta slice;
  GCC and Clang on Linux do not accept `-arch`, so the host ISA uses plain cc
  there and non-host ISAs remain explicitly unavailable."
  [isa arch & args]
  (cond
    (macos?) (into ["cc" "-arch" arch] args)
    (= isa (host-isa)) (into ["cc"] args)
    :else nil))

(defn- buildable-and-runnable? [isa arch]
  (let [probe (tmp (str "kotoba-isa-probe-" isa ".c"))
        out (tmp (str "kotoba-isa-probe-" isa ".bin"))
        command (cc-command isa arch (.getPath probe) "-o" (.getPath out))]
    (spit probe "int main(void){return 7;}")
    (and command
         (zero? (:exit (apply shell/sh command)))
         (= 7 (:exit (shell/sh (.getPath out)))))))

(defonce ^:private loaders
  (delay
    (into {}
          (for [[isa [arch _]] isas]
            [isa (when (buildable-and-runnable? isa arch)
                   (let [loader (tmp (str "kotoba-isa-loader-" isa ".bin"))
                         command (cc-command isa arch "-std=c11" "-O2"
                                             "-Wall" "-Wextra" "-Werror"
                                             "tools/kexe_loader.c"
                                             "-o" (.getPath loader))
                         build (when command (apply shell/sh command))]
                     (when (zero? (:exit build)) (.getPath loader))))]))))

(defn- run-native
  ([isa source] (run-native isa source "-" {:allow #{}}))
  ([isa source allow policy]
   (let [[_ target] (isas isa)
         artifact (:artifact (compiler/compile-source source target policy))
         code (tmp (str "kotoba-isa-code-" isa ".bin"))
         offset (get-in artifact [:exports 'main :offset])]
     (with-open [out (io/output-stream code)]
       (.write out (byte-array (map #(unchecked-byte (bit-and (int %) 0xff))
                                    (:code artifact)))))
     (:out (shell/sh (@loaders isa) (.getPath code) (str offset) "0" isa allow
                     :env (assoc (into {} (System/getenv))
                                 "KEXE_STRUCTURED_REPORT" "1"))))))

(def ^:private f64-one 4607182418800017408)
(def ^:private f64-two 4611686018427387904)
(def ^:private f64-nan 9221120237041090560)

(defn- f64c [op a b] (str "(defn main [] (if (" op " (f64-from-bits " a
                          ") (f64-from-bits " b ")) 1 0))"))

(def ^:private record-type "[:record :t/r [[:a :i64] [:b :i64]]]")
(def ^:private option-record-type
  "[:record :t/o [[:m [:option :i64]] [:x :i64]]]")

(def ^:private cases
  [["arithmetic" "(defn main [] (+ (* 3 4) (quot 10 2)))" 17]
   ["comparison" "(defn main [] (if (< 1 2) 7 8))" 7]
   ["recursion" (str "(defn f [n] (if (< n 1) 0 (+ n (f (- n 1)))))"
                     " (defn main [] (f 5))") 15]
   ["let" "(defn main [] (let [a 3 b 4] (* a b)))" 12]
   ["bit-not" "(defn main [] (bit-not 5))" -6]
   ["bit-or" "(defn main [] (bit-or 5 2))" 7]
   ["i64 shift" "(defn main [] (i64-shift-left 1 5))" 32]
   ["u32 shift" "(defn main [] (u32-shift-right 256 4))" 16]
   ["i32 wrapping" "(defn main [] (i32-wrapping-add 2147483647 1))" -2147483648]
   ["bool-not" "(defn main [] (if (bool-not true) 1 0))" 0]
   ["pair" "(defn main [] (pair-first (pair 9 8)))" 9]
   ["string=?" "(defn main [] (if (string=? \"ab\" \"ab\") 1 0))" 1]
   ["string-concat" (str "(defn main [] (string-byte-length"
                         " (string-concat \"ab\" \"cde\")))") 5]
   ;; The two host calls whose context offsets exceed the disp8 range.
   ["string-substring at offset 136"
    (str "(defn main [] (string-byte-length (string-substring"
         " (string-concat \"ab\" \"cde\") 1 4)))") 3]
   ["string-code-point-at at offset 144"
    "(defn main [] (string-code-point-at \"日本語\" 3))" 26412]
   ["record projection"
    (str "(defn main [] (record-get " record-type " (record-new "
         record-type " 4 9) :b))") 9]
   ;; A record crossing INTO a function. It is boxed into the same pair chain a
   ;; record result already crossed on, so these rows fail loudly if the caller
   ;; and the callee ever disagree about that shape.
   ;;
   ;; Each row picks a field whose value differs from every other field's, and
   ;; the two projections below select DIFFERENT fields, because a chain walked
   ;; to the wrong depth still returns a plausible i64 -- reading `:a` when `:b`
   ;; was asked for is exactly the bug this shape can have, and a row whose
   ;; fields shared a value could not see it.
   ["record parameter, first field"
    (str "(defn f [r " record-type "] (record-get " record-type " r :a))"
         " (defn main [] (f (record-new " record-type " 4 9)))") 4]
   ["record parameter, second field"
    (str "(defn f [r " record-type "] (record-get " record-type " r :b))"
         " (defn main [] (f (record-new " record-type " 4 9)))") 9]
   ;; A record parameter forwarded to a second function: the handle must stay a
   ;; handle across the hop rather than being re-boxed into a chain of a chain.
   ["record parameter forwarded"
    (str "(defn g [r " record-type "] (record-get " record-type " r :b))"
         " (defn f [r " record-type "] (g r))"
         " (defn main [] (f (record-new " record-type " 4 9)))") 9]
   ;; A `let`-bound record was flattened into one slot per field, so passing it
   ;; exercises the OTHER caller path: re-boxing from slots, in field order.
   ["let-bound record passed as an argument"
    (str "(defn f [r " record-type "] (record-get " record-type " r :b))"
         " (defn main [] (let [r (record-new " record-type " 4 9)] (f r)))") 9]
   ;; Both directions at once: a record built by one function, returned boxed,
   ;; then handed straight into another as a parameter.
   ["record result becomes a record parameter"
    (str "(defn mk [] " record-type " (record-new " record-type " 4 9))"
         " (defn f [r " record-type "] (record-get " record-type " r :a))"
         " (defn main [] (f (mk)))") 4]
   ;; The other boundary types admitted alongside records. Each was already a
   ;; single word INSIDE a function; these rows are what makes "and therefore it
   ;; can cross a boundary" a measured claim rather than an argument.
   ;; A bare `:bool` PARAMETER is absent on purpose: the interpreter validates a
   ;; `:bool` argument as an i64 word (`{:trap :value-type-mismatch :expected
   ;; :i64}`), so the boundary gates exclude it and there is nothing to execute
   ;; here. `:bool` results and `:bool` record fields both work and are covered.
   ;;
   ;; `(< n 3)` infers `:i64`, not `:bool` -- every comparison in this frontend
   ;; does -- so a genuine `:bool` result has to come from a literal.
   ["bool result"
    (str "(defn f [n] :bool (if (< n 3) true false))"
         " (defn main [] (if (f 1) 6 7))") 6]
   ["keyword parameter"
    (str "(defn f [k :keyword] (string-byte-length (keyword-name k)))"
         " (defn main [] (f :abc))") 3]
   ["option parameter"
    (str "(defn f [m [:option :i64]] (option-value-of [:option :i64] m 7))"
         " (defn main [] (f (option-some-of [:option :i64] 5)))") 5]
   ["option parameter, none"
    (str "(defn f [m [:option :i64]] (option-value-of [:option :i64] m 7))"
         " (defn main [] (f (option-none-of [:option :i64])))") 7]
   ["result parameter"
    (str "(defn f [r [:result :i64 :i64]] (result-value-of [:result :i64 :i64] r 7))"
         " (defn main [] (f (result-ok-of [:result :i64 :i64] 5)))") 5]
   ;; A record whose FIELD is an option -- murakumo's `:join/clamp` shape, and
   ;; the one that made a schema unrepresentable while each of its parts was
   ;; representable alone. Both field slots are read, so a flattening that lost
   ;; or reordered the option slot fails here.
   ["option-typed record field, some"
    (str "(defn f [r " option-record-type "] (option-value-of [:option :i64]"
         " (record-get " option-record-type " r :m)"
         " (record-get " option-record-type " r :x)))"
         " (defn main [] (f (record-new " option-record-type
         " (option-some-of [:option :i64] 5) 9)))") 5]
   ["option-typed record field, none falls back to the sibling field"
    (str "(defn f [r " option-record-type "] (option-value-of [:option :i64]"
         " (record-get " option-record-type " r :m)"
         " (record-get " option-record-type " r :x)))"
         " (defn main [] (f (record-new " option-record-type
         " (option-none-of [:option :i64]) 9)))") 9]
   ["option" "(defn main [] (option-value (option-some 5) 0))" 5]
   ["result" "(defn main [] (if (result-ok? (result-ok 5)) 1 0))" 1]
   ["f64 arithmetic" (str "(defn main [] (f64-to-bits (f64-add (f64-from-bits "
                          f64-one ") (f64-from-bits " f64-one "))))") f64-two]
   ["f64-lt" (f64c "f64-lt" f64-one f64-two) 1]
   ["f64-gt ordered" (f64c "f64-gt" f64-one f64-two) 0]
   ["f64-eq" (f64c "f64-eq" f64-one f64-one) 1]
   ;; The NaN rows. On x86-64 setb/setbe are TRUE when a compare is unordered
   ;; and on AArch64 so are LT/LE, so a naive encoding on either backend passes
   ;; every ordered row above and fails only here.
   ["f64-eq NaN" (f64c "f64-eq" f64-nan f64-nan) 0]
   ["f64-lt NaN" (f64c "f64-lt" f64-nan f64-one) 0]
   ["f64-le NaN" (f64c "f64-le" f64-nan f64-one) 0]
   ["f64-ge NaN" (f64c "f64-ge" f64-nan f64-one) 0]
   ["f64-unordered NaN" (f64c "f64-unordered" f64-nan f64-one) 1]
   ["f64-unordered ordered" (f64c "f64-unordered" f64-one f64-two) 0]
   ["kgraph" (str "(defn main [] (do (kgraph-assert! 1 2 3)"
                  " (kgraph-get 1 2)))") 3]
   ;; Keyword operations, which desugar into the general substring and the
   ;; concatenation rather than needing anything of their own. The content
   ;; comparisons are the point: a length-only check would pass even if the
   ;; colon were kept or an extra byte dropped.
   ["keyword-name length" "(defn main [] (string-byte-length (keyword-name :abc)))" 3]
   ["keyword-name content"
    "(defn main [] (if (string=? (keyword-name :abc) \"abc\") 1 0))" 1]
   ["keyword-from-string round trip"
    (str "(defn main [] (if (string=? (keyword-name"
         " (keyword-from-string \"xy\")) \"xy\") 1 0))") 1]
   ["keyword-name of a multi-byte name"
    "(defn main [] (string-byte-length (keyword-name :日本)))" 6]])

(deftest the-verified-surface-executes-identically-on-every-available-isa
  (let [available (into {} (remove (comp nil? val) @loaders))
        missing (remove available (keys isas))]
    (when (seq missing)
      (println "skipping ISAs with no buildable/runnable loader here:"
               (str/join ", " missing)))
    (is (seq available) "at least the host ISA must be runnable")
    (doseq [[isa _] available
            [why source expected] cases]
      (testing (str isa " / " why)
        (let [report (run-native isa source)]
          (is (not (str/includes? report "KEXE_TRAP"))
              (str isa " " why " must not trap: " (str/trim report)))
          (is (str/includes? report (str ":result " expected))
              (str isa " " why " => " (str/trim report))))))))

(deftest a-capability-call-executes-on-every-available-isa
  (doseq [[isa loader] @loaders :when loader]
    (testing isa
      (let [report (run-native isa "(defn main [] (cap-call 1 5))" "1"
                               {:allow #{[:cap/call 1]}})]
        (is (not (str/includes? report "KEXE_TRAP")) (str/trim report))
        ;; The qualification host's cap-call provider adds one.
        (is (str/includes? report ":result 6") (str/trim report))))))
