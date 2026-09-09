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
  silicon has (`cc -arch x86_64` plus Rosetta 2) but Ubuntu ARM does not.
  macOS therefore requires the full table, while other hosts require their host
  ISA. The availability set is always printed so the evidence cannot silently
  imply a cross-ISA run that did not occur."
  (:require [clojure.java.io :as io]
            [clojure.java.shell :as shell]
            [kotoba.lang.text :as str]
            [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]
            [kotoba.kir]
            [kotoba.kir.iq-codebook :as iq]
            [kotoba.gmir :as gmir]
            [kotoba.mir :as mir]
            [kotoba.native.machine-ir :as machine-ir]))

;; loader argv name -> [cc -arch value, compiler target]
(def ^:private isas
  {"x86_64" ["x86_64" :x86_64-kotoba-v1]
   "aarch64" ["arm64" :aarch64-kotoba-v1]})

;; Every scratch path this namespace writes is namespaced by process, because
;; they used to be fixed names in the shared temp directory and that is a race
;; against any other run of this table on the same machine. `run-native` writes
;; the program to `kotoba-isa-code-<isa>.bin` and then execs the loader on it,
;; so a neighbouring process writing the same path in that window makes the
;; loader run SOMEBODY ELSE'S program and report its result.
;;
;; It reads as a wrong answer, not as an error. Observed 2026-08-06 while a
;; second agent ran this table concurrently: `replace-all: two occurrences`
;; came back `:result -6`, which is the expected value of the `bit-not` row --
;; a different row's program, executed under this row's name. With two rows in
;; the table the window was small enough never to be hit; at 119 it is hit
;; readily, which is why this had not been noticed before.
(def ^:private run-token
  (str (.pid (java.lang.ProcessHandle/current)) "-"
       (Long/toHexString (System/nanoTime))))

(defn- tmp [name]
  (doto (io/file (System/getProperty "java.io.tmpdir") (str run-token "-" name))
    (.deleteOnExit)))

(defn- macos? [] (= "Mac OS X" (System/getProperty "os.name")))

(defn- host-isa []
  (case (str/lower (System/getProperty "os.arch"))
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

(defonce ^:private fuel-loaders
  ;; Boundary-only adversarial harness.  The production loader deliberately
  ;; fixes fuel at 512; compile an otherwise byte-identical temporary loader
  ;; whose initial word comes from KEXE_TEST_FUEL so 1/2-unit trap boundaries
  ;; can be executed without changing the sealed production-loader identity.
  (delay
    (into {}
          (for [[isa [arch _]] isas]
            [isa (when (buildable-and-runnable? isa arch)
                   (let [source (tmp (str "kotoba-fuel-loader-" isa ".c"))
                         loader (tmp (str "kotoba-fuel-loader-" isa ".bin"))
                         original (slurp "tools/kexe_loader.c")
                         patched (str/replace
                                  original
                                  "shared->context.fuel = 512;"
                                  (str "const char *test_fuel = getenv(\"KEXE_TEST_FUEL\");\n"
                                       "  shared->context.fuel = test_fuel == NULL ? 512 : "
                                       "(uint64_t)strtoull(test_fuel, NULL, 10);"))
                         _ (spit source patched)
                         command (cc-command isa arch "-std=c11" "-O2"
                                             "-Wall" "-Wextra" "-Werror"
                                             (.getPath source)
                                             "-o" (.getPath loader))
                         build (when command (apply shell/sh command))]
                     (when (zero? (:exit build)) (.getPath loader))))]))))

(defn- run-code
  ([isa bytes offset allow args] (run-code isa bytes offset allow args nil))
  ([isa bytes offset allow args fuel]
  (let [code (tmp (str "kotoba-isa-code-" isa ".bin"))]
     (with-open [out (io/output-stream code)]
       (.write out (byte-array (map #(unchecked-byte (bit-and (int %) 0xff))
                                    bytes))))
     (:out (apply shell/sh
                  (concat [((if fuel @fuel-loaders @loaders) isa)
                           (.getPath code) (str offset)
                           (str (count args)) isa allow]
                          (map str args)
                          [:env (assoc (into {} (System/getenv))
                                       "KEXE_STRUCTURED_REPORT" "1"
                                       "KEXE_TEST_FUEL" (str (or fuel 512)))]))))))

(defn- run-native
  ([isa source] (run-native isa source "-" {:allow #{}}))
  ([isa source allow policy]
   (run-native isa source allow policy 'main []))
  ([isa source allow policy entry args]
   (let [[_ target] (isas isa)
         artifact (:artifact (compiler/compile-source source target policy))]
     (run-code isa (:code artifact) (get-in artifact [:exports entry :offset])
               allow args)))
  ([isa source allow policy entry args fuel]
   (let [[_ target] (isas isa)
         artifact (:artifact (compiler/compile-source source target policy))]
     (run-code isa (:code artifact) (get-in artifact [:exports entry :offset])
               allow args fuel))))

(defn- a64-le-words [bytes]
  (mapv (fn [word]
          (reduce-kv (fn [value index byte]
                       (bit-or value (bit-shift-left byte (* 8 index))))
                     0 (vec word)))
        (partition 4 bytes)))

(def ^:private f64-one 4607182418800017408)
(def ^:private f64-two 4611686018427387904)
(def ^:private f64-nan 9221120237041090560)
(def ^:private f64-negative-zero -9223372036854775808)

(defn- f64b
  "A program returning the BIT PATTERN of `(op a b)`, so a NaN and a signed
  zero are distinguishable from every other answer. `(f64-to-bits x)` prints
  0x7ff8000000000000 for NaN and 0x8000000000000000 for -0.0; a printed float
  would show `NaN` and `0.0` and hide exactly what these rows are about."
  [op a b]
  (str "(defn main [] (f64-to-bits (" op " (f64-from-bits " a
       ") (f64-from-bits " b "))))"))

(defn- f64c [op a b] (str "(defn main [] (if (" op " (f64-from-bits " a
                          ") (f64-from-bits " b ")) 1 0))"))

(def ^:private record-type "[:record :t/r [[:a :i64] [:b :i64]]]")
(def ^:private option-record-type
  "[:record :t/o [[:m [:option :i64]] [:x :i64]]]")

(def ^:private scalar-pair-type
  "[:record :t/scalar-pair [[:x :i64] [:y :i64]]]")

(defn- scalar-pair-source [tail]
  (str "(defn select-pair [a :i64] :i64 "
       "(let [r (if a "
       "(record-new " scalar-pair-type " 1 2) "
       "(record-new " scalar-pair-type " 3 4))] "
       tail ")) "
       "(defn main [] :i64 0)"))

(def ^:private scalar-variant-type
  "[:variant :t/scalar-value [[:number :i64] [:flag :bool]]]")

(defn- scalar-variant-source [number-body flag-body]
  (str "(defn select-variant [a :i64] :i64 "
       "(let [v (if a "
       "(variant-new " scalar-variant-type " :number 41) "
       "(variant-new " scalar-variant-type " :flag false))] "
       "(variant-match " scalar-variant-type " v "
       "[[:number payload " number-body "] "
       "[:flag payload " flag-body "]]))) "
       "(defn main [] :i64 0)"))

(def ^:private base-cases
  [["arithmetic" "(defn main [] (+ (* 3 4) (quot 10 2)))" 17]
   ["comparison" "(defn main [] (if (< 1 2) 7 8))" 7]
   ["recursion" (str "(defn f [n] (if (< n 1) 0 (+ n (f (- n 1)))))"
                     " (defn main [] (f 5))") 15]
   ["tail recursion releases its frame"
    (str "(defn count-down [n acc] "
         "(if (= n 0) acc (count-down (- n 1) (+ acc 1)))) "
         "(defn main [] (count-down 400 0))") 400]
   ["mutual tail calls release both frames"
    (str "(defn even-tail [n] (if (= n 0) 1 (odd-tail (- n 1)))) "
         "(defn odd-tail [n] (if (= n 0) 0 (even-tail (- n 1)))) "
         "(defn main [] (even-tail 400))") 1]
   ["let" "(defn main [] (let [a 3 b 4] (* a b)))" 12]
   ["ordered scalar do"
    "(defn main [] :i64 (do (+ 1 2) (quot 8 2) (* 3 4)))" 12]
   ["ordered tail do"
    "(defn main [] :i64 (do (+ 1 2) (quot 8 2) (if (< 1 2) 13 14)))" 13]
   ["value-position if, then"
    "(defn main [] :i64 (+ 5 (if (< 1 2) 3 4)))" 8]
   ["value-position if, else"
    "(defn main [] :i64 (+ 5 (if (> 1 2) 3 4)))" 9]
   ["value-position if skips trapping else"
    "(defn main [] :i64 (+ 1 (if true 7 (quot 1 0))))" 8]
   ["value-position if skips trapping then"
    "(defn main [] :i64 (+ 1 (if false (quot 1 0) 7)))" 8]
   ["nested value-position if"
    "(defn main [] :i64 (let [x (if true (if false 2 3) 4)] (* x 5)))" 15]
   ["bit-not" "(defn main [] (bit-not 5))" -6]
   ["bit-or" "(defn main [] (bit-or 5 2))" 7]
   ["i64 shift" "(defn main [] (i64-shift-left 1 5))" 32]
   ["u32 shift" "(defn main [] (u32-shift-right 256 4))" 16]
   ["i32 wrapping" "(defn main [] (i32-wrapping-add 2147483647 1))" -2147483648]
   ["bool-not" "(defn main [] (if (bool-not true) 1 0))" 0]
   ["pair" "(defn main [] (pair-first (pair 9 8)))" 9]
   ["aggregate-payload variant"
    (str "(defn main [] "
         "(variant-match [:variant :t/record-or-count "
         "[[:record [:record :t/pair [[:a :i64] [:b :i64]]]] [:count :i64]]] "
         "(variant-new [:variant :t/record-or-count "
         "[[:record [:record :t/pair [[:a :i64] [:b :i64]]]] [:count :i64]]] "
         ":record (record-new [:record :t/pair [[:a :i64] [:b :i64]]] 20 22)) "
         "[[:record payload (+ (record-get [:record :t/pair [[:a :i64] [:b :i64]]] payload :a) "
         "(record-get [:record :t/pair [[:a :i64] [:b :i64]]] payload :b))] "
         "[:count payload payload]]))") 42]
   ["sealed indirect callable"
    "(defn add [a b] (+ a b)) (defn main [] (invoke (fn-ref add) 20 22))" 42]
   ["bounded apply"
    "(defn add [a b] (+ a b)) (defn main [] (apply (fn-ref add) (list 20 22)))" 42]
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
   ;;
   ;; A bare `:bool` PARAMETER used to be absent here, because the boundary
   ;; gates excluded it. kotoba-verifier `6433a81` (its ADR 0003) admits it, so
   ;; it is no longer absent -- see `bool-parameter-cases` below.
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
   ;; f64-min / f64-max, which are NOT the instructions of the same name.
   ;;
   ;; `minsd xmm0, xmm1` computes `(a < b) ? a : b`, so it returns the SECOND
   ;; operand on every false comparison -- and the two cases where the first
   ;; must win are exactly the ones where the comparison is false: either
   ;; input NaN, and (-0.0, +0.0). AArch64's FMIN/FMAX have neither hole.
   ;;
   ;; The definition is the KIR interpreter (`Math/min`/`Math/max` on the JVM,
   ;; `js/Math.min`/`js/Math.max` on cljs; both arms read on 2026-09-02 and in
   ;; agreement on every row here). Run against kotoba-native before the repair,
   ;; over twelve operand pairs times two operations times two ISAs = 48
   ;; observations, six were wrong: six of the eighteen NaN/signed-zero rows on
   ;; x86-64, and none of AArch64's twenty-four. That is the whole reason the
   ;; table is shared between the two ISAs.
   ;;
   ;; The two ordered rows are not filler: a sequence that unconditionally
   ;; returned the first operand would satisfy every NaN row above.
   ["f64-min NaN first" (f64b "f64-min" f64-nan f64-one) f64-nan]
   ["f64-min NaN second" (f64b "f64-min" f64-one f64-nan) f64-nan]
   ["f64-min -0.0 first" (f64b "f64-min" f64-negative-zero 0) f64-negative-zero]
   ["f64-min -0.0 second" (f64b "f64-min" 0 f64-negative-zero) f64-negative-zero]
   ["f64-min ordered, larger first" (f64b "f64-min" f64-two f64-one) f64-one]
   ["f64-max NaN first" (f64b "f64-max" f64-nan f64-one) f64-nan]
   ["f64-max NaN second" (f64b "f64-max" f64-one f64-nan) f64-nan]
   ["f64-max -0.0 first" (f64b "f64-max" f64-negative-zero 0) 0]
   ["f64-max -0.0 second" (f64b "f64-max" 0 f64-negative-zero) 0]
   ["f64-max ordered, smaller first" (f64b "f64-max" f64-one f64-two) f64-two]
   ["kgraph" (str "(defn main [] (do (kgraph-assert! 1 2 3)"
                  " (kgraph-get 1 2)))") 3]
   ["private string-index traversal state"
    (str "(ns native.string-index (:export [main]))"
         " (defn build [] :string-index"
         " (string-index-assoc"
         "  (string-index-assoc (string-index-new) \"bafy-b\" 2)"
         "  \"bafy-a\" 1))"
         " (defn replace [index :string-index] :string-index"
         "  (string-index-assoc index \"bafy-b\" 9))"
         " (defn main [] :i64"
         "  (+ (string-index-count (replace (build)))"
         "     (option-value-of [:option :i64]"
         "       (string-index-get (replace (build)) \"bafy-b\") 99)"
         "     (option-value-of [:option :i64]"
         "       (string-index-get (build) \"missing\") 7)"
         "     (if (string-index-contains (build) \"bafy-a\") 1 0)))")
    19]
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

;; ---------------------------------------------------------------------------
;; Rows that four separate agents wrote, ran green, and left uncommitted here
;; because this repository was outside each of their scopes. Each reproduced
;; its rows in an ADR of the repository it was allowed to touch; the ADR is
;; cited above each group. They are brought in unchanged rather than
;; re-derived, so that what runs here is what those ADRs claim ran.
;; ---------------------------------------------------------------------------

;; kotoba-native ADR 0001 -- a record result is boxed from ANY tail position,
;; not only when `record-new` is the outermost form of the body. Each row
;; builds the record where a real module builds one (under a `let`, in either
;; branch of an `if`) and hands the boxed result straight into a parameter.
;;
;; Handing it into a parameter rather than projecting the call's result
;; directly is not a simplification: a row that ALSO projects the call's result
;; is still refused by the verifier, which that ADR names as a residual gap and
;; proves around via the murakumo sweep instead.
;;
;; The two projections select DIFFERENT fields for the same reason the
;; record-parameter rows above do -- a chain walked to the wrong depth still
;; returns a plausible i64.
(def ^:private record-result-cases
  (let [proj (fn [field]
               (str " (defn f [r " record-type "] (record-get " record-type
                    " r " field ")) (defn main [] (f (mk)))"))
        under-let (str "(defn mk [] " record-type " (let [z 1] (record-new "
                       record-type " 4 9)))")
        then-branch (str "(defn mk [] " record-type " (if (< 1 2) (record-new "
                         record-type " 4 9) (record-new " record-type " 0 0)))")
        else-nested (str "(defn mk [] " record-type " (if (< 2 1) (record-new "
                         record-type " 0 0) (let [z 1] (record-new "
                         record-type " 4 9))))")]
    [["record result built under a let, first field"
      (str under-let (proj ":a")) 4]
     ["record result built under a let, second field"
      (str under-let (proj ":b")) 9]
     ["record result built in the then branch, second field"
      (str then-branch (proj ":b")) 9]
     ["record result built in the else branch under a nested let, first field"
      (str else-nested (proj ":a")) 4]
     ["record result built in the else branch under a nested let, second field"
      (str else-nested (proj ":b")) 9]]))

;; kotoba-native ADR 0002 -- `string-contains?` / `string-replace-all` lower
;; from the existing string callbacks. Admitted onto the native targets by
;; kotoba-kir ADR 0222 and kotoba-verifier ADR 0002, so these need nothing
;; relaxed any more; the ADR ran them under two in-process relaxations because
;; neither had landed yet.
;;
;; Source text is built with `pr-str` rather than hand-escaped, so a row's
;; multi-byte literals are exactly the characters written here.
(def ^:private contains-rows
  ;; why, haystack, needle, expected
  [["needle at the very start" "abcdef" "abc" 1]
   ["needle at the very end" "abcdef" "def" 1]
   ["needle in the middle" "abcdef" "cd" 1]
   ["needle is the whole haystack" "abc" "abc" 1]
   ["absent" "abcdef" "xyz" 0]
   ["absent, but every window shares a prefix with it" "abcde" "cdf" 0]
   ["needle longer than the haystack" "ab" "abcd" 0]
   ["empty haystack" "" "a" 0]
   ["two occurrences, first at offset 0" "abab" "ab" 1]
   ["overlapping occurrences" "aaa" "aa" 1]
   ["multi-byte needle inside a multi-byte haystack" "日本語" "本語" 1]
   ["multi-byte needle absent" "日本語" "日語" 0]
   ["2-byte needle against a 3-byte-per-code-point haystack" "日本語" "ab" 0]
   ["mixed-width haystack" "aé日b" "é日" 1]])

(def ^:private replace-rows
  ;; why, haystack, needle, replacement, expected text
  [["single occurrence in the middle" "a-b" "-" "+" "a+b"]
   ["at the very start" "-ab" "-" "+" "+ab"]
   ["at the very end" "ab-" "-" "+" "ab+"]
   ["two occurrences" "a,b,c" "," ";" "a;b;c"]
   ["adjacent occurrences" "--" "-" "+" "++"]
   ["absent" "abc" "x" "y" "abc"]
   ["needle longer than the haystack" "ab" "abc" "z" "ab"]
   ["empty haystack" "" "a" "b" ""]
   ["needle is the whole haystack" "abc" "abc" "z" "z"]
   ;; The row that separates a correct scan from one that re-scans what it just
   ;; wrote: a replacement CONTAINING the needle loops forever if the cursor
   ;; does not advance past the text it emitted.
   ["replacement contains the needle" "xax" "a" "aa" "xaax"]
   ["replacement is the needle doubled" "a.b" "." ".." "a..b"]
   ["replacement shorter than the needle" "a--b--c" "--" "-" "a-b-c"]
   ["replacement longer than the needle" "a-b" "-" "===" "a===b"]
   ["empty replacement" "a-b" "-" "" "ab"]
   ["overlapping candidates, left to right" "aaa" "aa" "b" "ba"]
   ["multi-byte needle" "日本語" "本" "X" "日X語"]
   ["multi-byte replacement" "a-b" "-" "日" "a日b"]])

(defn- utf8-length [^String s] (alength (.getBytes s "UTF-8")))

(def ^:private string-search-cases
  (vec
   (concat
    (for [[why h n expected] contains-rows]
      [(str "contains?: " why)
       (str "(defn main [] (if (string-contains? " (pr-str h) " " (pr-str n)
            ") 1 0))")
       expected])
    ;; Each replace-all row runs twice: once comparing the produced text with
    ;; `string=?`, once measuring its byte length. The content check alone
    ;; cannot see a result that is right up to a truncation; the length check
    ;; alone cannot see right-length wrong-bytes.
    (mapcat
     (fn [[why h n r expected]]
       [[(str "replace-all: " why " (content)")
         (str "(defn main [] (if (string=? (string-replace-all " (pr-str h) " "
              (pr-str n) " " (pr-str r) ") " (pr-str expected) ") 1 0))")
         1]
        [(str "replace-all: " why " (byte length)")
         (str "(defn main [] (string-byte-length (string-replace-all "
              (pr-str h) " " (pr-str n) " " (pr-str r) ")))")
         (utf8-length expected)]])
     replace-rows))))

;; kotoba-verifier ADR 0003 -- a bare `:bool` PARAMETER is admitted at a
;; function boundary. Reproduced verbatim from that ADR, which is where they
;; lived because this repository was out of scope for the agent that ran them.
;;
;; Every row carries a `:string` parameter alongside its boolean. That is
;; LOAD-BEARING, not decoration: kotoba-kir carries `:param-types` into KIR
;; only when the HIR is typed, so a function whose ONLY typed feature is a
;; `:bool` parameter loses its table and traps at `:phase :ir` as `:i64`. That
;; is an open kotoba-kir gap (its ADR 0221) and is deliberately not worked
;; around here -- do not "simplify" the `:string` away.
;;
;; Every row is one half of a `true`/`false` pair returning DIFFERENT values, so
;; a backend that dropped the argument, passed a constant, or read the wrong
;; register cannot pass by luck. Ten of them are exactly the rows that trap on
;; x86-64 against kotoba-native `8e7c053` -- the pin this repository carried
;; until the change that committed them.
(def ^:private bool-parameter-cases
  [["bool parameter as an `if` test, `true`"
    "(defn f [s :string b :bool] (if b (string-byte-length s) 0))
     (defn main [] (f \"abcd\" true))" 4]
   ["bool parameter as an `if` test, `false`"
    "(defn f [s :string b :bool] (if b (string-byte-length s) 0))
     (defn main [] (f \"abcd\" false))" 0]
   ["bool parameter before a string parameter, `true`"
    "(defn f [b :bool s :string] (if b (string-byte-length s) 99))
     (defn main [] (f true \"abcd\"))" 4]
   ["bool parameter before a string parameter, `false`"
    "(defn f [b :bool s :string] (if b (string-byte-length s) 99))
     (defn main [] (f false \"abcd\"))" 99]
   ["bool parameter through `bool-not`, `true`"
    "(defn f [s :string b :bool] (if (bool-not b) (string-byte-length s) 99))
     (defn main [] (f \"abcd\" true))" 99]
   ["bool parameter through `bool-not`, `false`"
    "(defn f [s :string b :bool] (if (bool-not b) (string-byte-length s) 99))
     (defn main [] (f \"abcd\" false))" 4]
   ["bool parameter through `=`, `true`"
    "(defn f [s :string b :bool] (if (= b true) (string-byte-length s) 99))
     (defn main [] (f \"abcd\" true))" 4]
   ["bool parameter through `=`, `false`"
    "(defn f [s :string b :bool] (if (= b true) (string-byte-length s) 99))
     (defn main [] (f \"abcd\" false))" 99]
   ["bool parameter forwarded into another bool parameter, `true`"
    "(defn g [s :string b :bool] (if b 10 11))
     (defn f [s :string b :bool] (g s b))
     (defn main [] (f \"abcd\" true))" 10]
   ["bool parameter forwarded into another bool parameter, `false`"
    "(defn g [s :string b :bool] (if b 10 11))
     (defn f [s :string b :bool] (g s b))
     (defn main [] (f \"abcd\" false))" 11]
   ["two bool parameters, `true false`"
    "(defn f [s :string a :bool b :bool] (if a (if b 3 4) (if b 5 6)))
     (defn main [] (f \"abcd\" true false))" 4]
   ["two bool parameters, `false true`"
    "(defn f [s :string a :bool b :bool] (if a (if b 3 4) (if b 5 6)))
     (defn main [] (f \"abcd\" false true))" 5]
   ["bool parameter with a string result, `true`"
    "(defn f [s :string b :bool] :string (if b \"abc\" \"ab\"))
     (defn main [] (string-byte-length (f \"x\" true)))" 3]
   ["bool parameter with a string result, `false`"
    "(defn f [s :string b :bool] :string (if b \"abc\" \"ab\"))
     (defn main [] (string-byte-length (f \"x\" false)))" 2]
   ;; The two rows below and the record-field rows above are DOCUMENTATION, not
   ;; gates, and the verifier's own tests say so: a `:bool` RESULT and a `:bool`
   ;; inside a wrapper reach admission by recursion and passed before the
   ;; widening too. They are here because a reader should not have to infer
   ;; which of the boundary positions were already open.
   ["bool parameter returned as a bool result, `true`"
    "(defn f [s :string b :bool] :bool b)
     (defn main [] (if (f \"x\" true) 7 6))" 7]
   ["bool parameter returned as a bool result, `false`"
    "(defn f [s :string b :bool] :bool b)
     (defn main [] (if (f \"x\" false) 7 6))" 6]
   ["tail self-call passing a literal `false`"
    "(defn f [s :string b :bool] (if b (f s false) 6))
     (defn main [] (f \"abcd\" true))" 6]])

;; kotoba-native ADR 0003 -- a call argument that is the literal `false` is
;; emitted like any other argument. `emit-heap-call` walked its arguments with
;; `if-let`, which tests the BOUND VALUE, so a `false` ended the walk and every
;; argument after it was never pushed while the pop sequence still popped the
;; full arity.
;;
;; These two rows are the ones that ADR calls reachable on unmodified `main`
;; with NOTHING relaxed: `option-some-of` / `result-ok-of` lower to
;; `(pair 1 payload)`, so a `:bool` payload is a boolean literal in a host-call
;; argument slot and never crosses a function boundary at all. Before the fix
;; they are 159 bytes where the `true` form is 170 -- one dropped push -- and a
;; SIGBUS on x86-64 while AArch64 answers correctly.
;;
;; The ADR's other rows (a `:bool` in ordinary call and tail-self-call argument
;; positions) are covered by `bool-parameter-cases` above, which exercises the
;; same two emit sites through the now-open boundary.
(def ^:private boolean-literal-argument-cases
  [["`[:option :bool]` payload in a host-call argument slot, false"
    (str "(defn main [] (if (option-value-of [:option :bool]"
         " (option-some-of [:option :bool] false) true) 6 7))") 7]
   ["`[:option :bool]` payload in a host-call argument slot, true"
    (str "(defn main [] (if (option-value-of [:option :bool]"
         " (option-some-of [:option :bool] true) true) 6 7))") 6]
   ["`[:result :bool :i64]` payload in a host-call argument slot, false"
    (str "(defn main [] (if (result-value-of [:result :bool :i64]"
         " (result-ok-of [:result :bool :i64] false) true) 6 7))") 7]
   ["`[:result :bool :i64]` payload in a host-call argument slot, true"
    (str "(defn main [] (if (result-value-of [:result :bool :i64]"
         " (result-ok-of [:result :bool :i64] true) true) 6 7))") 6]])

;; Context ABI v4: `vector-alloc` at slot 200 and `vector-assoc!` at 208
;; (superproject ADR-2609010200). Here rather than only in
;; `native-executor-test` because that file runs on the HOST ISA only, and
;; this table is the one place a program is executed as a real process on
;; both -- the exact gap that let the signed-disp8 bug ship twice. Both new
;; offsets are past 127, so they take the same disp32 form that bug was about.
;;
;; The second row is the one that separates the store from the copy. The
;; element arena is bump-only and never reclaimed (65536 words), so a copying
;; update caps a 256-slot vector's whole-program write count at
;; `(65536 - 256) / 256` = 255. 300 writes is past that on purpose: it
;; returns 299 through `vector-assoc!` and traps through `vector-assoc`, so a
;; lowering that sent the bang to the copying slot fails this row on both
;; ISAs. The first row would not notice -- a copy and an in-place write are
;; indistinguishable on a handle that is dead afterwards, which is the whole
;; argument for admitting the bang.
(def ^:private abi-v4-vector-cases
  [["vector-alloc zeroes, and an in-place write lands in the named slot"
    (str "(defn main [] :i64 "
         "(let [v (vector-alloc 8) w (vector-assoc! v 5 41)] "
         "(+ (vector-at w 5) (vector-count w))))") 49]
   ["300 in-place writes over 256 slots outlive the copying arena budget"
    ;; `go` must NOT be exported: a vector handle is one machine word at an
    ;; internal call boundary and is deliberately not a host ABI
    ;; (`native-private-handle-type?`). Without the `:export` list every
    ;; function is exported and target selection refuses the whole module.
    (str "(ns fixtures.isa-slab (:export [main])) "
         "(defn go [items :vector-i64 i :i64 n :i64] :i64 "
         "(if (>= i n) (vector-at items 0) "
         "(go (vector-assoc! items 0 i) (+ i 1) n))) "
         "(defn main [] :i64 (go (vector-alloc 256) 0 300))") 299]])

(def ^:private cases
  (vec (concat base-cases
               record-result-cases
               string-search-cases
               bool-parameter-cases
               boolean-literal-argument-cases
               abi-v4-vector-cases)))

(deftest every-admitted-word-operation-uses-production-machine-ir
  (doseq [form ['(bool-not a) '(bit-not a)
                '(i64-shift-left a 3) '(i64-shift-right a 3)
                '(u64-shift-right a 3) '(i32-wrap a) '(u32-wrap a)
                '(i32-wrapping-add a b) '(i32-wrapping-mul a b)
                '(i32-xor a b) '(i32-shift-left a 3)
                '(i32-shift-right a 3) '(u32-shift-right a 3)]]
    (is (machine-ir/pilot-expression? ['a 'b] form) form)))

(def ^:private dual-phi-program
  (let [[test then-a then-b else-a else-b join-a join-b result]
        (mapv gmir/vreg (range 8))]
    {:gmir/version 2
     :gmir/instructions
     [{:gmir/op :gmir/argument :gmir/dst test :gmir/index 0}
      {:gmir/op :gmir/branch-zero :gmir/test test :gmir/target :test.label/else}
      {:gmir/op :gmir/label :gmir/id :test.label/then}
      {:gmir/op :gmir/constant :gmir/dst then-a :gmir/value 1}
      {:gmir/op :gmir/constant :gmir/dst then-b :gmir/value 2}
      {:gmir/op :gmir/label :gmir/id :test.label/then-exit}
      {:gmir/op :gmir/jump :gmir/target :test.label/join}
      {:gmir/op :gmir/label :gmir/id :test.label/else}
      {:gmir/op :gmir/constant :gmir/dst else-a :gmir/value 3}
      {:gmir/op :gmir/constant :gmir/dst else-b :gmir/value 4}
      {:gmir/op :gmir/label :gmir/id :test.label/else-exit}
      {:gmir/op :gmir/jump :gmir/target :test.label/join}
      {:gmir/op :gmir/label :gmir/id :test.label/join}
      {:gmir/op :gmir/phi :gmir/dst join-a
       :gmir/incomings [{:gmir/predecessor :test.label/then-exit
                         :gmir/value then-a}
                        {:gmir/predecessor :test.label/else-exit
                         :gmir/value else-a}]}
      {:gmir/op :gmir/phi :gmir/dst join-b
       :gmir/incomings [{:gmir/predecessor :test.label/then-exit
                         :gmir/value then-b}
                        {:gmir/predecessor :test.label/else-exit
                         :gmir/value else-b}]}
      {:gmir/op :gmir/add :gmir/dst result :gmir/left join-a :gmir/right join-b}
      {:gmir/op :gmir/return :gmir/value result}]}))

(deftest value-position-if-consumer-plan-has-zero-phi-frame-traffic
  (let [gmir (machine-ir/lower-kir-expression ['a] '(+ 1 (if a 2 3)))]
    (doseq [target [:x86-64 :aarch64]]
      (let [mc (machine-ir/compile-gmir target gmir)
            encodings (keep :mc/encoding (:mc/instructions mc))]
        (is (zero? (:mc/frame-slots mc)) target)
        ;; None on AArch64: its leaf tier is wide enough that both edges of the
        ;; join already reach the register the phi wants, so the transports
        ;; disappear rather than being scheduled. x86-64 offers two leaf
        ;; registers and still needs its three.
        (is (= (if (= :x86-64 target) 3 0)
               (count (filter #(= (keyword (name target) "move") %) encodings)))
            target)
        (is (not-any? #(contains? #{(keyword (name target) "spill-load")
                                    (keyword (name target) "spill-store")} %)
                      encodings)
            target)
        (is (seq (machine-ir/encode-mc mc)) target)))))

(deftest multi-phi-consumer-plan-and-real-process-have-zero-frame-traffic
  (doseq [[isa loader] @loaders :when loader
          :let [target (case isa "x86_64" :x86-64 "aarch64" :aarch64)
                mc (machine-ir/compile-gmir target dual-phi-program)
                encodings (keep :mc/encoding (:mc/instructions mc))
                bytes (machine-ir/encode-mc mc)]]
    (is (zero? (:mc/frame-slots mc)) target)
    (is (= (if (= :x86-64 target) 3 2)
           (count (filter #(= (keyword (name target) "move") %) encodings)))
        target)
    (is (not-any? #(contains? #{(keyword (name target) "spill-load")
                                (keyword (name target) "spill-store")} %)
                  encodings)
        target)
    (doseq [[argument expected] [[1 3] [0 7]]]
      (let [report (run-code isa bytes 0 "-" [argument])]
        (is (not (str/includes? report "KEXE_TRAP")) (str/trim report))
        (is (str/includes? report (str ":result " expected))
            (str isa " argument=" argument " => " (str/trim report)))))))

(deftest scalar-direct-call-preserves-a-live-caller-value
  (let [source (str "(defn inc-one [x :i64] :i64 (+ x 1)) "
                    "(defn main [] :i64 "
                    "(let [live 40] (+ live (inc-one 1))))")]
    (doseq [[isa loader] @loaders :when loader]
      (testing isa
        (let [report (run-native isa source)]
          (is (not (str/includes? report "KEXE_TRAP")) (str/trim report))
          (is (str/includes? report ":result 42") (str/trim report)))))))

(deftest four-argument-entry-and-five-argument-lazy-spill-run-as-real-processes
  (let [programs
        [[(str "(defn sum-four [a :i64 b :i64 c :i64 d :i64] :i64 "
               "(+ (+ a b) (+ c d))) "
               "(defn main [] :i64 (sum-four 1 2 4 8))")
          15]
         [(str "(defn sum-five [a :i64 b :i64 c :i64 d :i64 e :i64] :i64 "
               "(+ (+ (+ a b) (+ c d)) e)) "
               "(defn main [] :i64 (sum-five 1 2 4 8 16))")
          31]]]
    (doseq [[isa loader] @loaders :when loader
            [source expected] programs]
      (testing (str isa " result=" expected)
        (let [report (run-native isa source)]
          (is (not (str/includes? report "KEXE_TRAP")) (str/trim report))
          (is (str/includes? report (str ":result " expected))
              (str/trim report)))))))

(deftest source-record-sroa-has-zero-frame-traffic-and-runs-both-edges
  (let [body (list '+
                   (list 'record-get (read-string scalar-pair-type) 'r :x)
                   (list 'record-get (read-string scalar-pair-type) 'r :y))
        expression (list 'let
                         ['r (list 'if 'a
                                   (list 'record-new (read-string scalar-pair-type) 1 2)
                                   (list 'record-new (read-string scalar-pair-type) 3 4))]
                         body)
        gmir (machine-ir/lower-kir-expression ['a] expression)]
    (is (= 2 (count (filter #(= :gmir/phi (:gmir/op %))
                            (:gmir/instructions gmir)))))
    (doseq [target [:x86-64 :aarch64]]
      (let [mc (machine-ir/compile-gmir target gmir)
            encodings (keep :mc/encoding (:mc/instructions mc))]
        (is (zero? (:mc/frame-slots mc)) target)
        (is (= (if (= :x86-64 target) 3 2)
               (count (filter #(= (keyword (name target) "move") %)
                                encodings)))
            target)
        (is (not-any? #(contains? #{(keyword (name target) "spill-load")
                                    (keyword (name target) "spill-store")} %)
                      encodings)
            target)))
    (doseq [[isa loader] @loaders :when loader
            [argument expected] [[1 3] [0 7]]]
      (let [report (run-native isa (scalar-pair-source
                                    (str "(+ (record-get " scalar-pair-type
                                         " r :x) (record-get " scalar-pair-type
                                         " r :y))"))
                               "-" {:allow #{}} 'select-pair [argument])]
        (is (not (str/includes? report "KEXE_TRAP")) (str/trim report))
        (is (str/includes? report (str ":result " expected))
            (str isa " argument=" argument " => " (str/trim report)))))))

(deftest record-sroa-preserves-constructor-field-evaluation-order
  (let [source (str "(defn project-second [d :i64] :i64 "
                    "(let [r (record-new " scalar-pair-type
                    " (quot 1 d) 9)] "
                    "(record-get " scalar-pair-type " r :y))) "
                    "(defn main [] :i64 0)")]
    (doseq [[isa loader] @loaders :when loader]
      (testing isa
        (let [report (run-native isa source "-" {:allow #{}}
                                 'project-second [0])]
          (is (str/includes? report ":status :trap") (str/trim report)))))))

(deftest source-variant-sroa-has-zero-frame-traffic-and-runs-both-cases
  (let [type (read-string scalar-variant-type)
        expression (list 'let
                         ['v (list 'if 'a
                                   (list 'variant-new type :number 41)
                                   (list 'variant-new type :flag false))]
                         (list 'variant-match type 'v
                               [[:number 'payload (list '+ 'payload 1)]
                                [:flag 'payload (list 'if 'payload 1 7)]]))
        gmir (machine-ir/lower-kir-expression ['a] expression)]
    (is (= 4 (count (filter #(= :gmir/phi (:gmir/op %))
                            (:gmir/instructions gmir)))))
    (doseq [target [:x86-64 :aarch64]]
      (let [mc (machine-ir/compile-gmir target gmir)
            encodings (keep :mc/encoding (:mc/instructions mc))]
        (is (zero? (:mc/frame-slots mc)) target)
        (is (not-any? #(contains? #{(keyword (name target) "spill-load")
                                    (keyword (name target) "spill-store")} %)
                      encodings)
            target)))
    (doseq [[isa loader] @loaders :when loader
            [argument expected] [[1 42] [0 7]]]
      (let [report (run-native isa
                               (scalar-variant-source "(+ payload 1)"
                                                      "(if payload 1 7)")
                               "-" {:allow #{}} 'select-variant [argument])]
        (is (not (str/includes? report "KEXE_TRAP")) (str/trim report))
        (is (str/includes? report (str ":result " expected))
            (str isa " argument=" argument " => " (str/trim report)))))))

(deftest variant-sroa-executes-only-the-selected-branch
  (let [source (str "(defn select [a :i64 d :i64] :i64 "
                    "(let [v (if a "
                    "(variant-new " scalar-variant-type " :number 41) "
                    "(variant-new " scalar-variant-type " :flag false))] "
                    "(variant-match " scalar-variant-type " v "
                    "[[:number payload (quot payload d)] "
                    "[:flag payload 7]]))) "
                    "(defn main [] :i64 0)")]
    (doseq [[isa loader] @loaders :when loader]
      (let [unselected (run-native isa source "-" {:allow #{}} 'select [0 0])
            selected (run-native isa source "-" {:allow #{}} 'select [1 0])]
        (is (str/includes? unselected ":result 7") (str/trim unselected))
        (is (not (str/includes? unselected "KEXE_TRAP")) (str/trim unselected))
        (is (str/includes? selected ":status :trap") (str/trim selected))))))

(deftest variant-sroa-preserves-constructor-payload-evaluation
  (let [source (str "(defn project [d :i64] :i64 "
                    "(let [v (variant-new " scalar-variant-type
                    " :number (quot 1 d))] "
                    "(variant-match " scalar-variant-type " v "
                    "[[:number payload 9] [:flag payload 8]]))) "
                    "(defn main [] :i64 0)")]
    (doseq [[isa loader] @loaders :when loader]
      (let [report (run-native isa source "-" {:allow #{}} 'project [0])]
        (is (str/includes? report ":status :trap") (str/trim report))))))

(deftest the-verified-surface-executes-identically-on-every-available-isa
  (let [available (into {} (remove (comp nil? val) @loaders))
        missing (remove available (keys isas))
        required (if (macos?) (set (keys isas)) #{(host-isa)})]
    ;; Printed AND asserted. A skipped ISA reads exactly like a passing one in
    ;; the summary line, so "2 tests, N assertions, 0 failures" is not evidence
    ;; that both backends ran -- this assertion is.
    (println "available:" (vec (sort (keys available)))
             "/ missing (SKIPPED):" (vec (sort missing)))
    (is (every? available required)
        (str "required ISA loaders are unavailable on this host. required: "
             (vec (sort required)) ", missing: " (vec (sort missing))))
    (doseq [[isa _] available
            [why source expected] cases]
      (testing (str isa " / " why)
        (let [report (run-native isa source)]
          (is (not (str/includes? report "KEXE_TRAP"))
              (str isa " " why " must not trap: " (str/trim report)))
          (is (str/includes? report (str ":result " expected))
              (str isa " " why " => " (str/trim report))))))))

(deftest loop-call-zero-positive-and-fuel-boundary-run-on-every-available-isa
  (let [source (slurp "bench/runtime-comparison/kernel_loop_call.kotoba")]
    (doseq [[isa loader] @loaders :when loader]
      (testing isa
        (doseq [[n expected] [[0 0] [200 200] [510 510]]]
          (let [report (run-native isa source "-" {:allow #{}} 'kernel [n])]
            (is (not (str/includes? report ":status :trap")) (str/trim report))
            (is (str/includes? report (str ":result " expected))
                (str "n=" n " => " (str/trim report)))
            (is (str/includes? report (str ":remaining " (- 510 n)))
                (str "wrapper + exact n+1 kernel charge for n=" n ": "
                     (str/trim report)))))
        (let [exhausted (run-native isa source "-" {:allow #{}} 'kernel [511])]
          (is (str/includes? exhausted ":status :trap")
              (str "kernel wrapper + loop entry + 511 iterations exceed sealed fuel: "
                   (str/trim exhausted)))
          (is (str/includes? exhausted ":remaining 0")
              (str "exhaustion must not wrap and store UINT64_MAX: "
                   (str/trim exhausted))))
        (when (= isa :aarch64)
          (doseq [counter [-1 Long/MIN_VALUE]
                  fuel [1 2]]
            (let [report (run-native isa source "-" {:allow #{}}
                                     'kernel [counter] fuel)]
              (is (str/includes? report ":status :trap")
                  [counter fuel (str/trim report)])
              (is (str/includes? report ":remaining 0")
                  [counter fuel "cold charged loop-call copy must not wrap"]))))))))

(deftest aarch64-proven-countdown-bulk-fuel-preserves-exact-boundaries
  (when (@loaders :aarch64)
    (let [source (slurp "bench/runtime-comparison/kernel_batch.kotoba")
          zero (run-native :aarch64 source "-" {:allow #{}} 'kernel [7 0])
          one (run-native :aarch64 source "-" {:allow #{}} 'kernel [7 1])
          exact (run-native :aarch64 source "-" {:allow #{}} 'kernel [7 510])
          insufficient (run-native :aarch64 source "-" {:allow #{}}
                                   'kernel [7 511])]
      (is (str/includes? zero ":status :ok") (str/trim zero))
      (is (str/includes? zero ":remaining 510")
          "wrapper plus zero-iteration helper consume exactly two fuel")
      (is (str/includes? one ":status :ok") (str/trim one))
      (is (str/includes? one ":remaining 509")
          "counter=1 precharges helper entry plus its one recur exactly")
      (is (str/includes? exact ":status :ok") (str/trim exact))
      (is (str/includes? exact ":remaining 0")
          "entry precharge consumes the same exact 512 units as edge charging")
      (is (str/includes? insufficient ":status :trap")
          "an N+2=513 call traps before its pure body executes")
      (is (str/includes? insufficient ":remaining 0")
          "insufficient bulk charge saturates remaining fuel at zero"))))

(deftest aarch64-countdown-negative-and-large-inputs-fail-closed
  (when (and (@loaders :aarch64) (@fuel-loaders :aarch64))
    (let [source (str "(ns bulk-fallback (:export [down])) "
                      "(defn down [remaining :i64 acc :i64] :i64 "
                      "(if (= remaining 0) acc "
                      "(down (- remaining 1) (+ acc 1))))")]
      (doseq [[why counter] [["negative uses per-edge fallback" -1]
                             ["minimum i64 cannot wrap into a bulk amount" Long/MIN_VALUE]
                             ["maximum i64 bulk amount cannot fit available fuel" Long/MAX_VALUE]]]
        (let [report (run-native :aarch64 source "-" {:allow #{}}
                                 'down [counter 0])]
          (is (str/includes? report ":status :trap") [why (str/trim report)])
          (is (str/includes? report ":remaining 0")
              [why "fuel exhaustion must saturate at zero"])))
      (doseq [fuel [1 2]]
        (let [report (run-native :aarch64 source "-" {:allow #{}}
                                 'down [Long/MIN_VALUE 0] fuel)]
          (is (str/includes? report ":status :trap")
              ["MIN remains on the charged fallback" fuel (str/trim report)])
          (is (str/includes? report ":remaining 0")
              ["no wrap can escape the charged fallback" fuel
               (str/trim report)]))))))

(deftest aarch64-fifth-counter-and-high-pressure-allocation-preserve-fuel
  (when (@fuel-loaders :aarch64)
    (let [fifth-source
          (str "(ns fifth-counter (:export [down])) "
               "(defn down [a :i64 b :i64 c :i64 d :i64 counter :i64] :i64 "
               "(if (= counter 0) a "
               "(down (+ a 1) b c d (- counter 1))))")
          fifth (run-native :aarch64 fifth-source "-" {:allow #{}}
                            'down [7 0 0 0 1] 2)
          names (mapv #(str "v" %) (range 30))
          bindings (str/join " "
                             (map-indexed #(str %2 " (+ acc " %1 ")") names))
          sum (reduce #(str "(+ " %1 " " %2 ")") "acc" names)
          pressure-source
          (str "(ns pressure-count (:export [kernel])) "
               "(defn kernel [i :i64 b :i64 c :i64 d :i64 acc :i64] :i64 "
               "(if (= i 0) acc (let [" bindings "] "
               "(kernel (- i 1) b c d " sum "))))")
          pressure (run-native :aarch64 pressure-source "-" {:allow #{}}
                               'kernel [2 0 0 0 1] 3)]
      (is (str/includes? fifth ":status :ok") (str/trim fifth))
      (is (str/includes? fifth ":initial 2 :remaining 0")
          "the fifth ABI argument x4 supplies the exact one-iteration charge")
      (is (str/includes? pressure ":status :ok") (str/trim pressure))
      (is (str/includes? pressure ":initial 3 :remaining 0")
          "a public-tail allocation falls back: n+1 ordinary charges succeed"))))

(deftest full-compile-source-loop-call-is-one-direct-aarch64-cbnz
  (let [source (slurp "bench/runtime-comparison/kernel_loop_call.kotoba")
        compiled (compiler/compile-source source :aarch64-kotoba-v1)
        artifact (:artifact compiled)
        words (a64-le-words (:code artifact))
        module (->> (:kir compiled)
                    machine-ir/lower-kir-module
                    (machine-ir/compile-gmir :aarch64))
        loop-function (->> (:mc/functions module)
                           (filter #(some (fn [instruction]
                                            (= :mc/branch-nonzero
                                               (:mc/op instruction)))
                                          (:mc/instructions %)))
                           first)
        loop-instructions (:mc/instructions loop-function)
        cbz-x19? #(= 0xb4000013 (bit-and % 0xff00001f))
        cbnz-x19? #(= 0xb5000013 (bit-and % 0xff00001f))
        backward-b-indexes
        (keep-indexed
         (fn [index word]
           (when (and (= 0x14000000 (bit-and word 0xfc000000))
                      (let [imm26 (bit-and word 0x03ffffff)
                            signed (if (>= imm26 0x02000000)
                                     (- imm26 0x04000000)
                                     imm26)]
                        (neg? signed)))
             index))
         words)
        {:keys [offset length]} (get-in artifact [:exports 'main])]
    (is (= 284 (count (:code artifact)))
        "bulk fuel adds a complete cold negative fallback to the primary path")
    (is (= 2 (count (filter cbz-x19? words)))
        "primary and cold fallback enter their bodies through CBZ x19")
    (is (= 2 (count (filter cbnz-x19? words)))
        "primary and cold fallback rotate their latches to bottom CBNZ x19")
    (is (= 1 (count backward-b-indexes)))
    (is (every? #(< offset (* 4 %) (+ offset length)) backward-b-indexes)
        "the only backward B is main's public tail-call; no loop latch B remains")
    (is (not-any? #{0xeb01001f 0x9a9f17e2} words)
        "the former CMP x0,x1 and CSET x2,eq are absent")
    (is loop-function "the compiled module carries an explicit branch-nonzero")
    (is (= 1 (count (filter #(= :mc/branch-nonzero (:mc/op %))
                            loop-instructions))))
    (let [reentry-index (first (keep-indexed
                                #(when (= :mc/reentry (:mc/op %2)) %1)
                                loop-instructions))
          recur-index (first (keep-indexed
                              #(when (= :mc/recur (:mc/op %2)) %1)
                              loop-instructions))]
      (is (not-any? #(= :aarch64/move (:mc/encoding %))
                    (subvec loop-instructions (inc reentry-index) recur-index))
          "both unique-use producers write x19/x20 directly on the real edge"))
    (is (not-any? #(and (= :aarch64/constant (:mc/encoding %))
                        (zero? (:mir/value %)))
                  loop-instructions))
    (is (not-any? #(contains? #{:aarch64/equal :mc/branch-zero}
                              (or (:mc/encoding %) (:mc/op %)))
                  loop-instructions))))

(deftest a-capability-call-executes-on-every-available-isa
  (doseq [[isa loader] @loaders :when loader]
    (testing isa
      (let [report (run-native isa "(defn main [] (cap-call 1 5))" "1"
                               {:allow #{[:cap/call 1]}})]
        (is (not (str/includes? report "KEXE_TRAP")) (str/trim report))
        ;; The qualification host's cap-call provider adds one.
        (is (str/includes? report ":result 6") (str/trim report))))))

(deftest integer-division-errors-trap-on-every-available-isa
  ;; x86-64 IDIV traps for both cases in hardware. AArch64 SDIV does not, so
  ;; its lowering must preserve the language contract with explicit guards.
  ;; Running the real loader is essential: byte-shape tests cannot prove that
  ;; the branch targets reach the trap instruction.
  (let [source (str "(defn divide [x y] (quot x y)) "
                    "(defn main [] 0)")]
    (doseq [[isa loader] @loaders :when loader
            [why args] [["division by zero" [1 0]]
                        ["signed division overflow"
                         [Long/MIN_VALUE -1]]]]
      (testing (str isa " / " why)
        (let [report (run-native isa source "-" {:allow #{}} 'divide args)]
          (is (str/includes? report ":status :trap") (str/trim report)))))))

(deftest every-admitted-f64-form-uses-the-production-machine-ir-route
  (doseq [form ['(f64-from-bits 1) '(f64-to-bits 1)
                '(f64-abs 1) '(f64-neg 1) '(f64-sqrt 1)
                '(f64-add 1 2) '(f64-sub 1 2) '(f64-mul 1 2)
                '(f64-div 1 2) '(f64-min 1 2) '(f64-max 1 2)
                '(f64-eq 1 2) '(f64-lt 1 2) '(f64-le 1 2)
                '(f64-gt 1 2) '(f64-ge 1 2)
                '(f64-unordered 1 2)]]
    (is (machine-ir/pilot-expression? [] form) form)))

(deftest a-value-spilled-in-one-branch-arm-survives-into-the-other
  ;; Twelve values defined before an `if`, read only in the arm that runs, with
  ;; enough pressure in the arm that does not run to make the allocator evict
  ;; them there. A spill store left where the register ran out is inside the arm
  ;; that never executes; the reload is in the arm that does, and reads a slot
  ;; nothing wrote.
  ;;
  ;; This ran as a real process and printed 6171913639 instead of 282, on a
  ;; compiler whose whole test suite was green -- every check of the allocator
  ;; was structural, and the arithmetic of a taken branch is not structural.
  (let [source (str "(defn main [] :i64 "
                    "(let [n 7 "
                    "      b1 (+ n 11) b2 (+ n 12) b3 (+ n 13) b4 (+ n 14) "
                    "      b5 (+ n 15) b6 (+ n 16) b7 (+ n 17) b8 (+ n 18) "
                    "      b9 (+ n 19) b10 (+ n 20) b11 (+ n 21) b12 (+ n 22)] "
                    "  (if (= n 0) "
                    "    (let [x1 (* n 3) x2 (* n 5) x3 (* n 7) x4 (* n 11) "
                    "          x5 (* n 13) x6 (* n 17) x7 (* n 19) x8 (* n 23) "
                    "          x9 (* n 29) x10 (* n 31) x11 (* n 37) x12 (* n 41)] "
                    "      (+ (+ (+ x1 x2) (+ x3 x4)) "
                    "         (+ (+ x5 x6) (+ (+ x7 x8) (+ (+ x9 x10) (+ x11 x12)))))) "
                    "    (+ (+ (+ b1 b2) (+ b3 b4)) "
                    "       (+ (+ b5 b6) (+ (+ b7 b8) (+ (+ b9 b10) (+ b11 b12))))))))")]
    (doseq [[isa loader] @loaders :when loader]
      (testing isa
        (let [report (run-native isa source)]
          (is (not (str/includes? report "KEXE_TRAP")) (str/trim report))
          (is (str/includes? report ":result 282") (str/trim report)))))))

(deftest a-value-live-across-a-call-survives-into-a-branch-arm
  ;; Ten values defined before a call and read only after it, inside an arm of
  ;; an `if`. `clobber` exists to occupy the caller-saved tier, so a value left
  ;; there does not survive the call by luck.
  ;;
  ;; At the pin in deps.edn this function takes the conservative all-vreg path
  ;; and every value gets a slot, so today this passes for an uninteresting
  ;; reason. It is here for the pin that does not do that: kotoba-mir ADR 0012
  ;; routes calls-plus-control-flow to the linear scanner, where live-across
  ;; values prefer a preserved register and the rest are stored at their
  ;; DEFINITION -- which dominates every reload, including an arm that does not
  ;; contain the call.
  ;;
  ;; It discriminates against that implementation, which is why it is worth
  ;; landing before the pin moves: built against ADR 0012 with the
  ;; store-at-definition deleted, this returns 1861461900 on AArch64 and
  ;; -3652320519930723447 on x86-64 in place of 811.
  ;;
  ;; ADR 0012 is currently :accepted-defective for an unrelated reason -- it
  ;; miscompiles string search -- and this test does NOT catch that one.
  (let [source (str "(defn clobber [x :i64] :i64 "
                    "  (let [a (* x 3) b (* x 5) c (* x 7) d (* x 11) "
                    "        e (* x 13) f (* x 17) g (* x 19) h (* x 23)] "
                    "    (+ (+ (+ a b) (+ c d)) (+ (+ e f) (+ g h))))) "
                    "(defn main [] :i64 "
                    "  (let [n 7 "
                    "        v1 (+ n 1) v2 (+ n 2) v3 (+ n 3) v4 (+ n 4) v5 (+ n 5) "
                    "        v6 (+ n 6) v7 (+ n 7) v8 (+ n 8) v9 (+ n 9) v10 (+ n 10) "
                    "        r (clobber n)] "
                    "    (if (= n 0) "
                    "      0 "
                    "      (+ r (+ (+ (+ v1 v2) (+ v3 v4)) "
                    "              (+ (+ v5 v6) (+ (+ v7 v8) (+ v9 v10))))))))")]
    (doseq [[isa loader] @loaders :when loader]
      (testing isa
        (let [report (run-native isa source)]
          (is (not (str/includes? report "KEXE_TRAP")) (str/trim report))
          (is (str/includes? report ":result 811") (str/trim report)))))))

(deftest a-call-result-live-across-a-second-call-survives
  ;; Two calls, with the first call's result and one earlier value both live
  ;; across the second, then read in a branch arm.
  ;;
  ;; Recorded honestly: this one does NOT discriminate the store. Under ADR
  ;; 0012 two live values fit the preserved tier, so no slot is involved and
  ;; deleting the store leaves it at 1577. It covers the tier-preference path
  ;; -- a result that is itself live across a later call -- and is not a guard
  ;; for spill placement. `a-value-live-across-a-call-survives-into-a-branch-arm`
  ;; is that guard. Both are kept because they cover different shapes, not
  ;; because both are guards.
  (let [source (str "(defn clobber [x :i64] :i64 "
                    "  (let [a (* x 3) b (* x 5) c (* x 7) d (* x 11) "
                    "        e (* x 13) f (* x 17) g (* x 19) h (* x 23)] "
                    "    (+ (+ (+ a b) (+ c d)) (+ (+ e f) (+ g h))))) "
                    "(defn main [] :i64 "
                    "  (let [n 7 keep (+ n 100) r1 (clobber n) r2 (clobber (+ n 1))] "
                    "    (if (= n 0) 0 (+ keep (+ r1 r2)))))")]
    (doseq [[isa loader] @loaders :when loader]
      (testing isa
        (let [report (run-native isa source)]
          (is (not (str/includes? report "KEXE_TRAP")) (str/trim report))
          (is (str/includes? report ":result 1577") (str/trim report)))))))

(def ^:private call-and-back-edge-module
  "Same shape as kotoba-mir/test `call-and-back-edge-module`: a compiled
  function with a call and a backward jump, `acc` live across both.
  Kotoba `loop/recur` is a recursive helper, so source tests do not span this."
  (let [n0 (gmir/vreg 0)
        acc0 (gmir/vreg 1)
        n (gmir/vreg 2)
        acc (gmir/vreg 3)
        one (gmir/vreg 4)
        stepped (gmir/vreg 5)
        acc1 (gmir/vreg 6)
        n1 (gmir/vreg 7)]
    {:gmir/version 3
     :gmir/entry 'count-loop
     :gmir/functions
     [{:gmir/name 'id :gmir/arity 1
       :gmir/instructions
       [{:gmir/op :gmir/argument :gmir/dst (gmir/vreg 0) :gmir/index 0}
        {:gmir/op :gmir/return :gmir/value (gmir/vreg 0)}]}
      {:gmir/name 'count-loop :gmir/arity 1
       :gmir/instructions
       ;; Iteration 24: argument + acc0 are a prefix so entry-argument-plan
       ;; can start. Phi predecessors stay :test.label/preheader. The jump
       ;; still sits in the preheader block (label then jump).
       [{:gmir/op :gmir/argument :gmir/dst n0 :gmir/index 0}
        {:gmir/op :gmir/constant :gmir/dst acc0 :gmir/value 0}
        {:gmir/op :gmir/label :gmir/id :test.label/preheader}
        {:gmir/op :gmir/jump :gmir/target :test.label/header}
        {:gmir/op :gmir/label :gmir/id :test.label/header}
        {:gmir/op :gmir/phi :gmir/dst n
         :gmir/incomings [{:gmir/predecessor :test.label/preheader :gmir/value n0}
                          {:gmir/predecessor :test.label/latch :gmir/value n1}]}
        {:gmir/op :gmir/phi :gmir/dst acc
         :gmir/incomings [{:gmir/predecessor :test.label/preheader :gmir/value acc0}
                          {:gmir/predecessor :test.label/latch :gmir/value acc1}]}
        {:gmir/op :gmir/branch-zero :gmir/test n :gmir/target :test.label/done}
        {:gmir/op :gmir/label :gmir/id :test.label/body}
        {:gmir/op :gmir/constant :gmir/dst one :gmir/value 1}
        {:gmir/op :gmir/call :gmir/dst stepped :gmir/callee 'id
         :gmir/arguments [one]}
        {:gmir/op :gmir/add :gmir/dst acc1 :gmir/left acc :gmir/right stepped}
        {:gmir/op :gmir/subtract :gmir/dst n1 :gmir/left n :gmir/right one}
        {:gmir/op :gmir/label :gmir/id :test.label/latch}
        {:gmir/op :gmir/jump :gmir/target :test.label/header}
        {:gmir/op :gmir/label :gmir/id :test.label/done}
        {:gmir/op :gmir/return :gmir/value acc}]}]}))

(defn- run-call-and-back-edge [isa n]
  (let [target (case isa "x86_64" :x86-64 "aarch64" :aarch64)
        encoded (machine-ir/encode-mc-module
                 (machine-ir/compile-gmir target call-and-back-edge-module))
        offset (get-in encoded [:exports 'count-loop :offset])]
    (run-code isa (:code encoded) offset "-" [n])))

(defn- with-all-vreg-fallback
  "Execute THUNK with the conservative MIR fallback selected explicitly.
  This is execution evidence for the fallback's frame layout, not a production
  routing change: production still prefers the call-live scanner."
  [thunk]
  (let [lower-phis @#'kotoba.mir/lower-phis
        allocate-with-spills @#'kotoba.mir/allocate-with-spills
        force-fallback
        (fn [program]
          (let [{:keys [program merge-dst-by-slot]} (lower-phis program)
                calls? (boolean
                        (some #(contains? #{:mir/call :mir/runtime-call
                                            :mir/capability-call :mir/tail-call}
                                          (:mir/op %))
                              (:mir/instructions program)))]
            [(allocate-with-spills program merge-dst-by-slot)
             (if calls? :all-vregs :allocator)]))]
    (with-redefs-fn {#'kotoba.mir/allocate-with-policy force-fallback} thunk)))

(deftest a-call-and-a-back-edge-in-one-function-execute
  ;; Iteration 24 located :non-prefix-argument on this loop. Iteration 27
  ;; showed the production all-vreg asserts were the only suite delta with
  ;; back-edge? false. Production is the scanner path.
  (let [target-mc (fn [target]
                    (let [looper (->> (machine-ir/compile-gmir target call-and-back-edge-module)
                                      :mc/functions
                                      (filter #(= 'count-loop (:mc/name %)))
                                      first)]
                      ((juxt :mc/frame-policy :mc/frame-slots) looper)))]
    (is (= [:call-live 0] (target-mc :aarch64)))
    (is (= [:call-live 0] (target-mc :x86-64))))
  (doseq [[isa loader] @loaders :when loader
          n [0 1 5 50]]
    (testing (str isa " n=" n)
      (let [report (run-call-and-back-edge isa n)]
        (is (not (str/includes? report "KEXE_TRAP")) (str/trim report))
        (is (str/includes? report (str ":result " n))
            (str/trim report))))))

(deftest cfg-colored-all-vreg-call-loop-executes
  (let [target-mc
        (fn [target]
          (with-all-vreg-fallback
            #(let [looper (->> (machine-ir/compile-gmir target
                                                        call-and-back-edge-module)
                               :mc/functions
                               (filter (fn [function]
                                         (= 'count-loop (:mc/name function))))
                               first)]
               ((juxt :mc/frame-policy :mc/frame-slots) looper))))]
    (is (= [:all-vregs 4] (target-mc :aarch64)))
    (is (= [:all-vregs 4] (target-mc :x86-64))))
  (with-all-vreg-fallback
    #(doseq [[isa loader] @loaders :when loader
             n [0 1 5 50]]
       (testing (str isa " cfg-colored-all-vregs n=" n)
         (let [report (run-call-and-back-edge isa n)]
           (is (not (str/includes? report "KEXE_TRAP")) (str/trim report))
           (is (str/includes? report (str ":result " n))
               (str/trim report)))))))

(defmacro ^:private with-scratch-tier-only
  "Run BODY with only the always-available scratch tier. Same contract as
  kotoba-mir-test/with-scratch-tier-only: pressure tests have to be able to
  exhaust the profile."
  [& body]
  `(with-redefs [mir/leaf-registers {:x86-64 [] :aarch64 []}
                 mir/preserved-registers {:x86-64 [] :aarch64 []}]
     ~@body))

(def ^:private pressure-loop-module
  "count-loop plus five loop-invariant constants used after the latch, so
  their textual last-use covers the back-edge. Sum is 31; return is n+31.
  Under the scratch tier those five plus n/acc do not fit, so the scanner
  must spill. Iteration 25 executed the no-spill scanner path; this module
  is the spill-across-back-edge hole."
  (let [n0 (gmir/vreg 0)
        acc0 (gmir/vreg 1)
        k0 (gmir/vreg 2)
        k1 (gmir/vreg 3)
        k2 (gmir/vreg 4)
        k3 (gmir/vreg 5)
        k4 (gmir/vreg 6)
        n (gmir/vreg 7)
        acc (gmir/vreg 8)
        one (gmir/vreg 9)
        stepped (gmir/vreg 10)
        acc1 (gmir/vreg 11)
        n1 (gmir/vreg 12)
        t0 (gmir/vreg 13)
        t1 (gmir/vreg 14)
        t2 (gmir/vreg 15)
        t3 (gmir/vreg 16)
        ret (gmir/vreg 17)]
    {:gmir/version 3
     :gmir/entry 'count-loop
     :gmir/functions
     [{:gmir/name 'id :gmir/arity 1
       :gmir/instructions
       [{:gmir/op :gmir/argument :gmir/dst (gmir/vreg 0) :gmir/index 0}
        {:gmir/op :gmir/return :gmir/value (gmir/vreg 0)}]}
      {:gmir/name 'count-loop :gmir/arity 1
       :gmir/instructions
       [{:gmir/op :gmir/argument :gmir/dst n0 :gmir/index 0}
        {:gmir/op :gmir/constant :gmir/dst acc0 :gmir/value 0}
        {:gmir/op :gmir/constant :gmir/dst k0 :gmir/value 1}
        {:gmir/op :gmir/constant :gmir/dst k1 :gmir/value 2}
        {:gmir/op :gmir/constant :gmir/dst k2 :gmir/value 4}
        {:gmir/op :gmir/constant :gmir/dst k3 :gmir/value 8}
        {:gmir/op :gmir/constant :gmir/dst k4 :gmir/value 16}
        {:gmir/op :gmir/label :gmir/id :test.label/preheader}
        {:gmir/op :gmir/jump :gmir/target :test.label/header}
        {:gmir/op :gmir/label :gmir/id :test.label/header}
        {:gmir/op :gmir/phi :gmir/dst n
         :gmir/incomings [{:gmir/predecessor :test.label/preheader :gmir/value n0}
                          {:gmir/predecessor :test.label/latch :gmir/value n1}]}
        {:gmir/op :gmir/phi :gmir/dst acc
         :gmir/incomings [{:gmir/predecessor :test.label/preheader :gmir/value acc0}
                          {:gmir/predecessor :test.label/latch :gmir/value acc1}]}
        {:gmir/op :gmir/branch-zero :gmir/test n :gmir/target :test.label/done}
        {:gmir/op :gmir/label :gmir/id :test.label/body}
        {:gmir/op :gmir/constant :gmir/dst one :gmir/value 1}
        {:gmir/op :gmir/call :gmir/dst stepped :gmir/callee 'id
         :gmir/arguments [one]}
        {:gmir/op :gmir/add :gmir/dst acc1 :gmir/left acc :gmir/right stepped}
        {:gmir/op :gmir/subtract :gmir/dst n1 :gmir/left n :gmir/right one}
        {:gmir/op :gmir/label :gmir/id :test.label/latch}
        {:gmir/op :gmir/jump :gmir/target :test.label/header}
        {:gmir/op :gmir/label :gmir/id :test.label/done}
        {:gmir/op :gmir/add :gmir/dst t0 :gmir/left k0 :gmir/right k1}
        {:gmir/op :gmir/add :gmir/dst t1 :gmir/left k2 :gmir/right k3}
        {:gmir/op :gmir/add :gmir/dst t2 :gmir/left t0 :gmir/right t1}
        {:gmir/op :gmir/add :gmir/dst t3 :gmir/left t2 :gmir/right k4}
        {:gmir/op :gmir/add :gmir/dst ret :gmir/left acc :gmir/right t3}
        {:gmir/op :gmir/return :gmir/value ret}]}]}))

(defn- pressure-looper [target]
  (->> (machine-ir/compile-gmir target pressure-loop-module)
       :mc/functions
       (filter #(= 'count-loop (:mc/name %)))
       first))

(defn- spill-op-counts [target looper]
  (let [store (keyword (name target) "spill-store")
        load (keyword (name target) "spill-load")
        ins (:mc/instructions looper)]
    [(count (filter #(= store (:mc/encoding %)) ins))
     (count (filter #(= load (:mc/encoding %)) ins))]))

(defn- run-pressure-loop [isa n]
  (let [target (case isa "x86_64" :x86-64 "aarch64" :aarch64)
        encoded (machine-ir/encode-mc-module
                 (machine-ir/compile-gmir target pressure-loop-module))
        offset (get-in encoded [:exports 'count-loop :offset])]
    (run-code isa (:code encoded) offset "-" [n])))

(deftest a-call-and-a-back-edge-across-a-spill-execute
  ;; Iteration 25 executed the scanner path with no pressure spill.
  ;; This file puts five loop-invariants whose last-use is after the latch
  ;; so the interval covers the back-edge, then exhausts the scratch tier.
  ;; Production is :call-live. Slot count is not the claim; presence of
  ;; spill-store/load under the scratch-only pool is.
  (is (= :call-live (:mc/frame-policy (pressure-looper :aarch64))))
  (is (= :call-live (:mc/frame-policy (pressure-looper :x86-64))))
  (with-scratch-tier-only
    (doseq [target [:aarch64 :x86-64]]
      (let [looper (pressure-looper target)
            [stores loads] (spill-op-counts target looper)]
        (is (= :call-live (:mc/frame-policy looper)) target)
        (is (pos? stores) (str target " must store; otherwise this is not a spill"))
        (is (pos? loads) (str target " must load; otherwise this is not a spill"))))
    (doseq [[isa loader] @loaders :when loader
            n [0 1 5 50]]
      (testing (str isa " scanner-spill n=" n)
        (let [report (run-pressure-loop isa n)
              expected (+ n 31)]
          (is (not (str/includes? report "KEXE_TRAP")) (str/trim report))
          (is (str/includes? report (str ":result " expected))
              (str/trim report))))))
  (doseq [[isa loader] @loaders :when loader
          n [0 1 5 50]]
    (testing (str isa " production n=" n)
      (let [report (run-pressure-loop isa n)
            expected (+ n 31)]
        (is (not (str/includes? report "KEXE_TRAP")) (str/trim report))
        (is (str/includes? report (str ":result " expected))
            (str/trim report))))))

;; ---------------------------------------------------------------------------
;; granted regions: bytes the CALLER handed in, on both ISAs, as real processes
;; ---------------------------------------------------------------------------

(def ^:private granted-region-source
  (slurp "test/fixtures/granted-region-sum.kotoba"))

;; ---------------------------------------------------------------------------
;; rodata: a codebook the PROGRAM carries, on both ISAs, as real processes
;; ---------------------------------------------------------------------------

(def ^:private codebook-source
  (slurp "test/fixtures/rodata-codebook-iq4.kotoba"))

(def ^:private kvalues-iq4nl
  "The reference table, written here as sixteen decimal numbers rather than
  read out of the fixture. A test that derived the expectation from the same
  hex string the program carries would agree with itself no matter what the
  program did with it."
  [-127 -104 -83 -65 -49 -35 -22 -10 1 13 25 38 53 69 89 113])

(defn- nibble-sum-reference [bytes]
  (reduce + 0 (map (fn [b] (+ (nth kvalues-iq4nl (bit-and b 15))
                              (nth kvalues-iq4nl (bit-and (quot b 16) 15))))
                   bytes)))

(defn- region-hex [bytes]
  (apply str (map #(format "%02x" (bit-and (int %) 0xff)) bytes)))

(deftest a-granted-region-is-read-on-every-available-isa
  ;; `kotoba.verifier` 33b3d067 admits the slice memory subfamily on general
  ;; native targets when every base is provably a PARAMETER. This is the other
  ;; half: the loader's `g:<hex>`/`gl:<n>` pair, which is what a caller uses to
  ;; BE that parameter. Before it there was no caller that could grant a
  ;; region -- a string argument arrives as a pair handle and a vector as an
  ;; arena handle, and neither is an address.
  ;;
  ;; Both numbers are the loader's. `gl:0` is a REFERENCE to the zeroth region
  ;; minted, answered with the length recorded when the bytes were copied, so a
  ;; caller cannot grant a base together with a length that does not belong to
  ;; it. That is the property, and it is why the pair is a pair.
  (let [available (into {} (remove (comp nil? val) @loaders))
        missing (remove available (keys isas))
        required (if (macos?) (set (keys isas)) #{(host-isa)})]
    (println "granted-region available:" (vec (sort (keys available)))
             "/ missing (SKIPPED):" (vec (sort missing)))
    (is (every? available required)
        (str "required ISA loaders are unavailable on this host. required: "
             (vec (sort required)) ", missing: " (vec (sort missing))))
    (doseq [[isa _] available]
      (testing isa
        (testing "sixty-four granted bytes"
          ;; 1 + 2 + ... + 64
          (let [report (run-native isa granted-region-source "-" {:allow #{}}
                                   'sum-bytes
                                   [(str "g:" (region-hex (range 1 65))) "gl:0"])]
            (is (not (str/includes? report "KEXE_TRAP")) (str/trim report))
            (is (str/includes? report ":result 2080") (str/trim report))))
        (testing "the LENGTH is the grant's, not the traversal's"
          ;; The same program over a ten-byte grant walks ten bytes, because
          ;; `slice-length` answers what was granted. A traversal that assumed
          ;; its own bound would read the other fifty-four.
          (let [report (run-native isa granted-region-source "-" {:allow #{}}
                                   'sum-bytes
                                   [(str "g:" (region-hex (range 1 11))) "gl:0"])]
            (is (str/includes? report ":result 55") (str/trim report))))
        (testing "an empty grant is a grant"
          (let [report (run-native isa granted-region-source "-" {:allow #{}}
                                   'sum-bytes ["g:" "gl:0"])]
            (is (str/includes? report ":result 0") (str/trim report))))
        (testing "a byte is read UNSIGNED"
          ;; Four 0xFF bytes are 1020, not -4. The slice's element type is
          ;; :u8, and a sign-extended load would answer a negative here.
          (let [report (run-native isa granted-region-source "-" {:allow #{}}
                                   'sum-bytes
                                   [(str "g:" (region-hex [255 255 255 255])) "gl:0"])]
            (is (str/includes? report ":result 1020") (str/trim report))))
        (testing "a length naming a region the loader never minted is refused"
          ;; Fail closed rather than answered with zero: `gl:1` when one region
          ;; exists is a forward reference, and a zero there would be a silent
          ;; empty walk over a region that IS there.
          (let [report (run-native isa granted-region-source "-" {:allow #{}}
                                   'sum-bytes
                                   [(str "g:" (region-hex [1 2 3])) "gl:1"])]
            (is (not (str/includes? report ":result"))
                (str "a forward reference must not produce a result: "
                     (str/trim report)))))))))


(def ^:private iq3xxs-source
  (slurp "test/fixtures/rodata-codebook-iq3xxs.kotoba"))

(def ^:private iq3s-source
  (slurp "test/fixtures/rodata-codebook-iq3s.kotoba"))

(def ^:private iq2s-source
  (slurp "test/fixtures/rodata-codebook-iq2s.kotoba"))

(defn- pool-literals
  "Every `(bytes-literal \"…\")` hex string in SOURCE, in the order it appears."
  [source]
  (mapv second (re-seq #"\(bytes-literal \"([0-9a-f]*)\"\)" source)))

(def ^:private iq4xs-source
  (slurp "test/fixtures/rodata-codebook-iq4xs.kotoba"))

(deftest the-pool-carries-the-vendored-codebook-byte-for-byte
  ;; ⚠ THIS IS THE COMPARISON osaho ADR 0264 BUILT THE DIGESTS FOR, and it
  ;; says so in as many words: each image is pinned by an FNV-1a/32
  ;; positional digest so that "a SECOND transcription of the same table -- a
  ;; backend's read-only pool, say -- can be compared with this one BY A TEST
  ;; rather than only by an execution".
  ;;
  ;; These fixtures are that second transcription. Without this, a wrong
  ;; codebook is caught only where an execution test happens to index the
  ;; byte that differs -- and a 1024-entry grid probed at thirteen elements
  ;; leaves most of it unread. FNV rather than a sum because a sum cannot see
  ;; a permutation.
  ;;
  ;; The digest is recomputed HERE from the fixture's own hex rather than
  ;; taken from `iq/digests`, so the two sides arrive at the number by
  ;; different routes; `iq/digests` is what it is compared against.
  (letfn [(fnv [bytes]
            (reduce (fn [h b]
                      (let [x (bit-xor h (bit-and b 0xff))]
                        (bit-and (+ (* x 16777216) (* x 403)) 0xffffffff)))
                    0x811c9dc5
                    bytes))]
    (testing "IQ4_XS carries kvalues_iq4nl and nothing else"
      (let [literals (pool-literals iq4xs-source)]
        (is (= 1 (count literals)) "one table, so one pool entry")
        (is (= iq/kvalues-iq4nl-hex (first literals)))
        (is (= (get-in iq/digests [:kvalues-iq4nl :fnv1a32])
               (fnv (iq/hex->bytes (first literals)))))
        (is (= (get-in iq/digests [:kvalues-iq4nl :bytes])
               (count (iq/hex->bytes (first literals)))))))
    (testing "IQ2_S carries the ten-bit grid and kmask"
      (let [literals (pool-literals iq2s-source)]
        (is (= 2 (count literals)))
        (is (= iq/iq2s-grid-hex (first literals)))
        (is (= iq/kmask-iq2xs-hex (second literals)))
        (is (= (get-in iq/digests [:iq2s-grid :fnv1a32])
               (fnv (iq/hex->bytes (first literals)))))
        (is (= 8192 (count (iq/hex->bytes (first literals))))
            "1024 entries of EIGHT bytes -- four times IQ3_S's, which is what
             a ten-bit index and eight elements per entry come to")))
    (testing "IQ3_S carries the nine-bit grid and kmask"
      (let [literals (pool-literals iq3s-source)]
        (is (= 2 (count literals)) "two tables, so two pool entries")
        (is (= iq/iq3s-grid-hex (first literals)))
        (is (= iq/kmask-iq2xs-hex (second literals)))
        (is (= (get-in iq/digests [:iq3s-grid :fnv1a32])
               (fnv (iq/hex->bytes (first literals)))))
        (is (= 2048 (count (iq/hex->bytes (first literals))))
            "512 entries of four bytes -- twice IQ3_XXS's, which is the whole
             point of the ninth bit")))
    (testing "IQ3_XXS carries ksigns, the grid and kmask"
      ;; In the order the source names them, which is the order the decode
      ;; needs them: the sign selector, the grid entry, the element mask.
      (let [literals (pool-literals iq3xxs-source)
            expected [[iq/ksigns-iq2xs-hex :ksigns-iq2xs]
                      [iq/iq3xxs-grid-hex :iq3xxs-grid]
                      [iq/kmask-iq2xs-hex :kmask-iq2xs]]]
        (is (= 3 (count literals)) "three tables, so three pool entries")
        (doseq [[[hex k] got] (map vector expected literals)]
          (testing (str k)
            (is (= hex got))
            (is (= (get-in iq/digests [k :fnv1a32]) (fnv (iq/hex->bytes got))))
            (is (= (get-in iq/digests [k :bytes]) (count (iq/hex->bytes got))))))))
    (testing "and the digest sees a permutation, which is why it is not a sum"
      ;; The control. Swapping two bytes leaves the sum identical; if this
      ;; assertion ever passed, every assertion above would be vacuous.
      (let [bytes (iq/hex->bytes iq/kvalues-iq4nl-hex)
            swapped (assoc bytes 0 (peek bytes) 15 (first bytes))]
        (is (= (reduce + bytes) (reduce + swapped)) "the sum cannot tell")
        (is (not= (fnv bytes) (fnv swapped)) "the digest can")))))

(defn- half->f32-bits
  "fp16 -> the binary32 bit pattern, BY THE IEEE-754 DEFINITION rather than by
  the magic-multiply equation the program under test uses.

  ⚠ THIS IS THE POINT OF THE HELPER. Reimplementing the same equation would
  make the test agree with itself: both sides would carry `0x77800000` and
  both would be wrong together. Here the exponent and mantissa are read out
  and the value assembled arithmetically, which is a different route to the
  same number -- and the two disagree loudly if either is wrong."
  [half]
  (let [sign (if (zero? (bit-and half 0x8000)) 1.0 -1.0)
        e (bit-and (bit-shift-right half 10) 0x1f)
        m (bit-and half 0x3ff)]
    (if (= e 31)
      ;; ⚠ THE INFINITY/NAN ARM IS A BIT-LEVEL CONVENTION, NOT A VALUE, so it
      ;; is stated rather than derived -- and this arm therefore does NOT
      ;; discriminate, because it is the same equation the program uses. A NaN
      ;; has no numeric value to arrive at independently, and its PAYLOAD is
      ;; exactly what a derivation through a float would destroy: `(float
      ;; Double/NaN)` gives a canonical NaN, so a reference built that way
      ;; would report every payload as wrong. It is written out so a reader
      ;; is not misled into counting these three cases as evidence.
      ;; `unchecked-int` for the same reason the program narrows: both
      ;; exports answer a pattern SIGN-EXTENDED from bit 31, so a negative
      ;; infinity is -8388608 and not 4286578688.
      (unchecked-int (bit-or (bit-shift-left (bit-and half 0x8000) 16)
                             0x7f800000
                             (bit-shift-left m 13)))
      ;; The finite cases DO discriminate: the exponent and mantissa are read
      ;; out and the value assembled arithmetically, which never mentions the
      ;; `0x77800000` the program multiplies by.
      (Float/floatToRawIntBits
       (float
        (if (zero? e)
          (* sign (Math/pow 2 -14) (/ (double m) 1024.0))
          (* sign (Math/pow 2 (- e 15)) (+ 1.0 (/ (double m) 1024.0)))))))))

(defn- iq4xs-weight-bits
  "ggml's `dequantize_row_iq4_xs`, one element, as an f32 bit pattern.
  Transcribed from the C rather than from the fixture."
  [block element]
  (let [b (fn [i] (bit-and (int (nth block i)) 0xff))
        d-half (bit-or (b 0) (bit-shift-left (b 1) 8))
        scales-h (bit-or (b 2) (bit-shift-left (b 3) 8))
        ib (quot element 32)
        j (- element (* ib 32))
        low (< j 16)
        jj (if low j (- j 16))
        packed (b (+ 8 (* ib 16) jj))
        nibble (if low (bit-and packed 15) (bit-shift-right packed 4))
        sl (b (+ 4 (quot ib 2)))
        sl4 (if (even? ib) (bit-and sl 15) (bit-and (bit-shift-right sl 4) 15))
        sh2 (bit-and (bit-shift-right scales-h (* 2 ib)) 3)
        ls (bit-or sl4 (bit-shift-left sh2 4))
        d (Float/intBitsToFloat (unchecked-int (half->f32-bits d-half)))
        dl (float (* d (float (- ls 32))))]
    (Float/floatToRawIntBits (float (* dl (float (nth kvalues-iq4nl nibble)))))))

(def ^:private iq3xxs-block
  "One `block_iq3_xxs`, 98 bytes: `d`, 64 grid codes, and eight 32-bit words
  whose top nibble is a scale and whose low 28 bits are four seven-bit sign
  selectors. The words are chosen so all four selectors differ within a word
  and the scale nibble varies across the eight."
  (vec (concat [0x55 0x35]
               (map #(mod (* 37 (inc %)) 256) (range 64))
               (mapcat (fn [w] [(bit-and w 0xff)
                                (bit-and (bit-shift-right w 8) 0xff)
                                (bit-and (bit-shift-right w 16) 0xff)
                                (bit-and (bit-shift-right w 24) 0xff)])
                       [0x1234567 0x89abcde 0x2468ace 0x13579bd
                        0xfedcba9 0x7654321 0xa5a5a5a 0x5c5c5c5]))))

(def ^:private iq3s-block
  "One `block_iq3_s`, 110 bytes: `d`, 64 eight-bit codes, eight bytes of
  NINTH bits, 32 sign bytes, and four bytes holding two four-bit scales each.
  The `qh` bytes are chosen so the ninth bit is set for some codes in every
  one of the four `l` positions -- a block where it never fired would agree
  with a decode that ignored `qh` entirely."
  (vec (concat [0x55 0x35]
               (map #(mod (* 37 (inc %)) 256) (range 64))
               [0x9a 0x3c 0xf1 0x05 0xc7 0x2e 0x68 0xb3]
               (map #(mod (* 53 (inc %)) 256) (range 32))
               [0x41 0x7c 0x2b 0xd6])))

(def ^:private iq2s-block
  "One `block_iq2_s`, 82 bytes: `d`, 32 eight-bit codes, 32 sign bytes, eight
  bytes carrying the ninth and TENTH bits, and eight bytes of packed scales."
  (vec (concat [0x55 0x35]
               (map #(mod (* 37 (inc %)) 256) (range 32))
               (map #(mod (* 53 (inc %)) 256) (range 32))
               [0x9a 0x3c 0xf1 0x05 0xc7 0x2e 0x68 0xb3]
               [0x41 0x7c 0x2b 0xd6 0x8e 0x15 0xa9 0x63])))

(deftest iq2-s-dequantises-on-every-available-isa
  ;; THE FOURTH AND LAST of the formats kotoba-native's `elf64` docstring
  ;; named as staying in the C. 62 more of the model's 866 tensors, and with
  ;; IQ4_XS, IQ3_XXS and IQ3_S that is 222 of the 306 that sentence covered.
  ;;
  ;; The grid index is TEN bits -- two lifted out of `qh`, mask 0x300 -- so
  ;; the grid is 1024 entries of eight bytes. 8192 bytes is the largest of the
  ;; six vendored tables, and the size the pool was separately measured
  ;; against before any of this was written.
  ;;
  ;; Reference is osaho's oracle, for the reason given on the IQ3_XXS test.
  (let [available (into {} (remove (comp nil? val) @loaders))
        missing (remove available (keys isas))
        required (if (macos?) (set (keys isas)) #{(host-isa)})
        expected (mapv (fn [v] (Float/floatToRawIntBits (float v)))
                       (@#'kotoba.kir/dequantize-block
                        'kernel-dequant-dot-iq2-s iq2s-block 0))]
    (println "iq2-s available:" (vec (sort (keys available)))
             "/ missing (SKIPPED):" (vec (sort missing)))
    (is (every? available required)
        (str "required ISA loaders are unavailable on this host. required: "
             (vec (sort required)) ", missing: " (vec (sort missing))))
    (is (= 256 (count expected)))
    ;; Measured: 77 distinct, 127 negative, 129 positive, 0 zero. Floors
    ;; rather than the numbers, for the reason the IQ3_S test gives.
    (is (< 32 (count (distinct expected))) "SCANNED distinct values")
    (is (< 32 (count (filter neg? expected))) "SCANNED negative values")
    (is (< 32 (count (filter pos? expected))) "SCANNED positive values")
    (doseq [[isa _] available]
      (testing isa
        ;; Both scale nibbles (l < 2 takes the low one), every quarter of a
        ;; group, both 32-element boundaries, and the last element.
        (doseq [element [0 1 7 8 15 16 23 24 31 32 63 64 128 160 200 255]]
          (let [report (run-native isa iq2s-source "-" {:allow #{}}
                                   'weight-bits
                                   [(str "g:" (region-hex iq2s-block)) "gl:0"
                                    (str element)])]
            (is (not (str/includes? report "KEXE_TRAP")) (str/trim report))
            (is (str/includes? report (str ":result " (nth expected element)))
                (str "element " element ": " (str/trim report)))))))))

(deftest iq3-s-dequantises-on-every-available-isa
  ;; 64 more of the model's 866 tensors, and the format where the grid index
  ;; is NINE bits: eight from `qs` and one lifted out of `qh` by a shift whose
  ;; amount depends on which code pair is being read. The fixture writes that
  ;; shift as a multiply by `256 / 4^l`, because shift counts in this dialect
  ;; are literals -- a frontend admission rule, not a machine limit.
  ;;
  ;; Reference is osaho's oracle, for the reason given on the IQ3_XXS test.
  (let [available (into {} (remove (comp nil? val) @loaders))
        missing (remove available (keys isas))
        required (if (macos?) (set (keys isas)) #{(host-isa)})
        expected (mapv (fn [v] (Float/floatToRawIntBits (float v)))
                       (@#'kotoba.kir/dequantize-block
                        'kernel-dequant-dot-iq3-s iq3s-block 0))]
    (println "iq3-s available:" (vec (sort (keys available)))
             "/ missing (SKIPPED):" (vec (sort missing)))
    (is (every? available required)
        (str "required ISA loaders are unavailable on this host. required: "
             (vec (sort required)) ", missing: " (vec (sort missing))))
    (is (= 256 (count expected)))
    ;; This block decodes to 76 distinct values with 127 negative and 129
    ;; positive. Asserted rather than remembered: a fixture that drifted into
    ;; a single repeated value, or into one sign, would pass every element
    ;; comparison below while testing almost nothing.
    (is (< 32 (count (distinct expected))) "SCANNED distinct values")
    (is (< 32 (count (filter neg? expected))) "SCANNED negative values")
    (is (< 32 (count (filter pos? expected))) "SCANNED positive values")
    (doseq [[isa _] available]
      (testing isa
        ;; Both scale nibbles, both halves of a pair, all four `l` positions,
        ;; every 64-element pair boundary, and the last element.
        (doseq [element [0 1 3 4 7 8 15 16 31 32 33 63 64 96 128 191 200 255]]
          (let [report (run-native isa iq3s-source "-" {:allow #{}}
                                   'weight-bits
                                   [(str "g:" (region-hex iq3s-block)) "gl:0"
                                    (str element)])]
            (is (not (str/includes? report "KEXE_TRAP")) (str/trim report))
            (is (str/includes? report (str ":result " (nth expected element)))
                (str "element " element ": " (str/trim report)))))))))

(deftest iq3-xxs-dequantises-on-every-available-isa
  ;; THE LARGEST UNSUPPORTED TYPE IN THE SHIPPING MODEL -- 82 of 866 tensors,
  ;; more than any other single format. Three tables rather than one, and a
  ;; per-element sign the table does not carry.
  ;;
  ;; ⚠ THE REFERENCE IS osaho's ORACLE, NOT A SECOND TRANSCRIPTION HERE, and
  ;; that is a deliberate difference from the IQ4_XS test above. Writing the
  ;; equation out again in this file would test my reading of the C twice and
  ;; the backend once. osaho's oracle is already compared, element by element,
  ;; against a pointer-walk transcription of `dequantize_row_iq3_xxs` in
  ;; `kotoba.kir-dequant-iq-test` (osaho ADR 0264: SCANNED 256, DISAGREEMENTS
  ;; 0), so leaning on it makes THIS test about the backend -- which is the
  ;; part that is new.
  ;;
  ;; What the pool carries is checked separately and without executing
  ;; anything, by `the-pool-carries-the-vendored-codebook-byte-for-byte`. The
  ;; two are needed together: thirteen probes cannot read a 1024-entry grid,
  ;; and a digest cannot tell you the decode indexes it correctly.
  (let [available (into {} (remove (comp nil? val) @loaders))
        missing (remove available (keys isas))
        required (if (macos?) (set (keys isas)) #{(host-isa)})
        expected (mapv (fn [v] (Float/floatToRawIntBits (float v)))
                       (@#'kotoba.kir/dequantize-block
                        'kernel-dequant-dot-iq3-xxs iq3xxs-block 0))]
    (println "iq3-xxs available:" (vec (sort (keys available)))
             "/ missing (SKIPPED):" (vec (sort missing)))
    (is (every? available required)
        (str "required ISA loaders are unavailable on this host. required: "
             (vec (sort required)) ", missing: " (vec (sort missing))))
    (is (= 256 (count expected)))
    (is (< 1 (count (distinct expected)))
        "a block that decoded to one repeated value would pass vacuously")
    (doseq [[isa _] available]
      (testing isa
        ;; Every sub-block boundary, both halves of a sign group, both bytes
        ;; of a code pair, and the last element.
        (doseq [element [0 1 3 4 7 8 15 16 31 32 63 100 128 200 255]]
          (let [report (run-native isa iq3xxs-source "-" {:allow #{}}
                                   'weight-bits
                                   [(str "g:" (region-hex iq3xxs-block)) "gl:0"
                                    (str element)])]
            (is (not (str/includes? report "KEXE_TRAP")) (str/trim report))
            (is (str/includes? report (str ":result " (nth expected element)))
                (str "element " element ": " (str/trim report)))))
        (testing "a sign selector actually flips a sign"
          ;; The control for the third table. `ksigns_iq2xs` is the only one
          ;; of the three whose effect is invisible in magnitude, so a decode
          ;; that ignored it would still agree on |value| everywhere. This
          ;; asserts the block produces BOTH signs.
          (let [answers (map (fn [e]
                               (let [r (run-native isa iq3xxs-source "-" {:allow #{}}
                                                   'weight-bits
                                                   [(str "g:" (region-hex iq3xxs-block))
                                                    "gl:0" (str e)])]
                                 (Long/parseLong (second (re-find #":result (-?\d+)" r)))))
                             [0 3])]
            (is (some neg? answers))
            (is (some pos? answers))))))))

(deftest iq4-xs-dequantises-on-every-available-isa
  ;; ⚠ THE FORMAT THAT KEPT THE IQ TYPES IN THE C, decoded in Kotoba and run
  ;; as a real process. It needs everything the day's work added at once: a
  ;; codebook in the program's own pool, a region the caller granted, a base
  ;; that survives the frontend's rename through a `let`, and f32 arithmetic.
  ;;
  ;; The fp16 super-block scale is decoded BY THE X86 EQUATION -- mask, shift,
  ;; multiply by 2^112 -- and the reference above decodes it by the IEEE-754
  ;; definition instead, so the two agree by arriving at the same number
  ;; rather than by carrying the same constant.
  (let [available (into {} (remove (comp nil? val) @loaders))
        missing (remove available (keys isas))
        required (if (macos?) (set (keys isas)) #{(host-isa)})
        ;; A block whose fields are all non-trivial: a scale that is neither
        ;; a power of two nor 1, both nibble positions of every `scales_l`
        ;; byte, and a `scales_h` with all four two-bit patterns present.
        block (vec (concat [0x55 0x35 0xe7 0xb1 0x5a 0x3c 0x91 0x2d]
                           (map #(mod (* 37 (inc %)) 256) (range 128))))]
    (println "iq4-xs available:" (vec (sort (keys available)))
             "/ missing (SKIPPED):" (vec (sort missing)))
    (is (every? available required)
        (str "required ISA loaders are unavailable on this host. required: "
             (vec (sort required)) ", missing: " (vec (sort missing))))
    (doseq [[isa _] available]
      (testing isa
        (testing "the fp16 decode, against the IEEE-754 definition"
          ;; Zero, a subnormal, one, the scale this block uses, the largest
          ;; finite half, a negative, an infinity and a NaN with a payload.
          (doseq [half [0x0000 0x0001 0x03ff 0x3c00 0x3555 0x7bff
                        0xc000 0x7c00 0x7e01]]
            (let [report (run-native isa iq4xs-source "-" {:allow #{}}
                                     'half-bits [(str half)])
                  expected (half->f32-bits half)]
              (is (not (str/includes? report "KEXE_TRAP")) (str/trim report))
              (is (str/includes? report (str ":result " expected))
                  (str (format "half 0x%04x" half) ": " (str/trim report))))))
        (testing "the dequantised weight, over a whole block"
          ;; Every sub-block boundary, both halves of a sub-block, both
          ;; nibble positions, and the last element.
          (doseq [element [0 1 15 16 17 31 32 63 64 100 128 200 255]]
            (let [expected (iq4xs-weight-bits block element)
                  report (run-native isa iq4xs-source "-" {:allow #{}}
                                     'weight-bits
                                     [(str "g:" (region-hex block)) "gl:0"
                                      (str element)])]
              (is (not (str/includes? report "KEXE_TRAP")) (str/trim report))
              (is (str/includes? report (str ":result " expected))
                  (str "element " element ": " (str/trim report))))))
        (testing "changing one nibble of qs changes exactly that element"
          ;; The control. Two blocks differing in the low nibble of qs[0]
          ;; must differ at element 0 and agree at element 16, which reads
          ;; the HIGH nibble of the same byte.
          (let [bumped (assoc block 8 (bit-or (bit-and (nth block 8) 0xf0) 15))
                answer (fn [blk e]
                         (let [r (run-native isa iq4xs-source "-" {:allow #{}}
                                             'weight-bits
                                             [(str "g:" (region-hex blk)) "gl:0"
                                              (str e)])]
                           (Long/parseLong
                            (second (re-find #":result (-?\d+)" r)))))]
            (is (not= (answer block 0) (answer bumped 0)))
            (is (= (answer block 16) (answer bumped 16)))
            (is (= (iq4xs-weight-bits bumped 0) (answer bumped 0)))))))))

(deftest a-carried-codebook-is-decoded-on-every-available-isa
  ;; THE LAST PIECE THE IQ QUANTIZATION FORMATS WERE MISSING, executed rather
  ;; than argued. kotoba-native's `elf64` docstring says of IQ3_XXS, IQ3_S,
  ;; IQ4_XS and IQ2_S -- 306 of the shipping model's 866 tensors -- that they
  ;; "decode through codebook grids that `qwen35_quant_tables.inc` holds as
  ;; static const data, and this dialect has no rodata and no bytes literal to
  ;; put one in. Those types stay in the C."
  ;;
  ;; The fixture is `kvalues_iq4nl`, the sixteen-entry table IQ4_NL and IQ4_XS
  ;; decode through, carried as the program's own bytes. Three things had to
  ;; be true at once and none of them was until 2026-09-09: the four literal
  ;; heads had to leave the verifier's aiueos-only set, a literal had to be
  ;; admitted as a REGION BASE beside a parameter (a pool that is addressable
  ;; and unreadable is not a pool), and AArch64 had to have an instruction
  ;; that reaches the pool -- `adr`, one instruction, not ADRP+ADD.
  ;;
  ;; ⚠ THE EXPECTATION IS COMPUTED FROM A SEPARATE COPY OF THE TABLE, above.
  ;; Deriving it from the fixture's hex would make the test agree with itself.
  (let [available (into {} (remove (comp nil? val) @loaders))
        missing (remove available (keys isas))
        required (if (macos?) (set (keys isas)) #{(host-isa)})]
    (println "rodata-codebook available:" (vec (sort (keys available)))
             "/ missing (SKIPPED):" (vec (sort missing)))
    (is (every? available required)
        (str "required ISA loaders are unavailable on this host. required: "
             (vec (sort required)) ", missing: " (vec (sort missing))))
    (doseq [[isa _] available]
      (testing isa
        (testing "every entry of the table, read out of the program's own pool"
          (doseq [[index expected] (map-indexed vector kvalues-iq4nl)]
            (let [report (run-native isa codebook-source "-" {:allow #{}}
                                     'kvalue [(str index)])]
              (is (not (str/includes? report "KEXE_TRAP")) (str/trim report))
              (is (str/includes? report (str ":result " expected))
                  (str index " -> " expected ": " (str/trim report))))))
        (testing "a whole block's nibbles, against an independent reference"
          ;; 128 bytes is one IQ4_XS block's `qs`: 256 packed nibbles, low
          ;; first, which is ggml's own unpack order.
          (let [qs (mapv #(mod (* 37 (inc %)) 256) (range 128))
                expected (nibble-sum-reference qs)
                report (run-native isa codebook-source "-" {:allow #{}}
                                   'nibble-sum
                                   [(str "g:" (region-hex qs)) "gl:0"])]
            (is (not (str/includes? report "KEXE_TRAP")) (str/trim report))
            (is (str/includes? report (str ":result " expected))
                (str/trim report))))
        (testing "changing ONE nibble moves the answer by exactly one table step"
          ;; The control that separates "reads the codebook" from "computes
          ;; some constant". Both runs walk the same 128 bytes; they differ in
          ;; the low nibble of byte 0, so the answer must differ by exactly
          ;; kvalues[15] - kvalues[0] and by nothing else.
          (let [base (vec (repeat 128 0))
                bumped (assoc base 0 15)
                answer (fn [qs]
                         (let [r (run-native isa codebook-source "-" {:allow #{}}
                                             'nibble-sum
                                             [(str "g:" (region-hex qs)) "gl:0"])]
                           (Long/parseLong
                            (second (re-find #":result (-?\d+)" r)))))]
            (is (= (- (nth kvalues-iq4nl 15) (nth kvalues-iq4nl 0))
                   (- (answer bumped) (answer base))))))
        (testing "the grant's LENGTH bounds the walk, not the program's idea of it"
          (let [qs (mapv #(mod (* 37 (inc %)) 256) (range 128))]
            (doseq [n [0 1 64 128]]
              (let [taken (subvec qs 0 n)
                    report (run-native isa codebook-source "-" {:allow #{}}
                                       'nibble-sum
                                       [(str "g:" (region-hex taken)) "gl:0"])]
                (is (str/includes? report
                                   (str ":result " (nibble-sum-reference taken)))
                    (str n " bytes: " (str/trim report)))))))))))

;; ---------------------------------------------------------------------------
;; granted regions x dequant: the fused kernel over two granted regions
;; ---------------------------------------------------------------------------

(def ^:private granted-dequant-source
  (slurp "test/fixtures/granted-region-dequant.kotoba"))

(defn- f32-bytes [xs]
  (mapcat (fn [x]
            (let [bits (Float/floatToRawIntBits (float x))]
              [(bit-and bits 0xff)
               (bit-and (bit-shift-right bits 8) 0xff)
               (bit-and (bit-shift-right bits 16) 0xff)
               (bit-and (bit-shift-right bits 24) 0xff)]))
          xs))

(defn- q8-0-block
  "One Q8_0 block: a binary16 scale then thirty-two signed codes."
  [half codes]
  (into [(bit-and half 0xff) (bit-and (bit-shift-right half 8) 0xff)]
        (map #(bit-and % 0xff)) codes))

(defn- report-result [report]
  (when-let [m (re-find #":result (-?\d+)" report)] (Long/parseLong (second m))))

(deftest the-fused-dequant-answers-the-same-bits-on-every-available-isa
  ;; `kernel-dequant-dot-q8-0`'s contract is an ACCUMULATION TREE. Floating-
  ;; point addition is not associative, so one specific order of summation is
  ;; the operation, and the AArch64 arm exists only because it reproduces the
  ;; x86 one instruction for instruction. Cross-ISA bit-identity is therefore
  ;; not a nice property of this kernel -- it is the kernel.
  ;;
  ;; It is load-bearing beyond this repository too: `local-murakumo` qualifies
  ;; a node by comparing GREEDY tokens exactly, and the community-provider lane
  ;; verifies a claimed result by re-running a sampled job on another node. A
  ;; Mac mini and a K16 that disagree in the last bit of a logit are two fleets.
  ;;
  ;; The regions are GRANTED, which is what makes this runnable at all: the
  ;; weight row and the activations are host bytes the loader minted, and the
  ;; program's two bases are parameters it could not have chosen.
  (let [available (into {} (remove (comp nil? val) @loaders))
        missing (remove available (keys isas))
        required (if (macos?) (set (keys isas)) #{(host-isa)})
        run (fn [isa block activations]
              (report-result
               (run-native isa granted-dequant-source "-" {:allow #{}} 'dot-q8-0
                           [(str "g:" (region-hex block)) "gl:0"
                            (str "g:" (region-hex (f32-bytes activations))) "gl:1"
                            1])))]
    ;; Printed AND asserted, and the count is printed too, because the
    ;; cross-ISA claim below is VACUOUS when only one ISA is available: a set
    ;; of one answer has one distinct element no matter what that answer is.
    ;; On macOS both are required and the claim is real; on a Linux runner only
    ;; the host ISA exists and this degrades to the per-ISA constants above,
    ;; which is honest but is a smaller test than it looks.
    (println "granted-dequant available:" (vec (sort (keys available)))
             "/ missing (SKIPPED):" (vec (sort missing))
             "/ cross-isa claim is"
             (if (< (count available) 2) "VACUOUS here" "live"))
    (is (every? available required)
        (str "required ISA loaders are unavailable on this host. required: "
             (vec (sort required)) ", missing: " (vec (sort missing))))
    (testing "d = 1.0, codes 1..32, activations 1.0 -> 528.0f"
      (let [block (q8-0-block 0x3C00 (range 1 33))
            answers (into {} (map (fn [isa] [isa (run isa block (repeat 32 1.0))]))
                          (keys available))]
        (doseq [[isa answer] answers]
          (is (= (Float/floatToRawIntBits (float 528.0)) answer)
              (str isa " answered " answer)))
        ;; Equal TO EACH OTHER, asserted separately: a constant both arms had
        ;; drifted from together would pass the check above and fail here.
        (is (= 1 (count (set (vals answers))))
            (str "the ISAs disagree: " (pr-str answers)))))
    (testing "a fixture whose answer names the accumulation tree"
      ;; The first activation is 2^24 and the rest are 1.0, so each 1 added in
      ;; isolation rounds away and each pair does not. Four lanes, element e
      ;; into lane e mod 4, then (s0+s1)+(s2+s3): 2^24 + 24. A single
      ;; left-to-right accumulator answers 2^24 exactly, so the digits name the
      ;; tree rather than merely being a plausible dot product.
      (let [block (q8-0-block 0x3C00 (repeat 32 1))
            activations (cons (Float/intBitsToFloat 0x4B800000) (repeat 31 1.0))
            answers (into {} (map (fn [isa] [isa (run isa block activations)]))
                          (keys available))]
        (doseq [[isa answer] answers]
          (is (= 0x4B80000C answer)
              (str isa " answered " (format "0x%08X" answer)
                   " -- 0x4B800000 is a left-to-right sum")))
        (is (= 1 (count (set (vals answers))))
            (str "the ISAs disagree: " (pr-str answers)))))))

(deftest the-two-K-quants-are-still-refused-on-aarch64
  ;; Asserted rather than merely true, so writing either arm is a red test that
  ;; has to be looked at. The reason is a gap and is named as one: a Q4_K
  ;; block's (scale, min) pair and its nibble half change on different periods
  ;; and a Q6_K block's scale index every sixteen elements, so their thirty-two
  ;; groups are unrolled with per-group geometry rather than looped -- and none
  ;; of that is written for AArch64.
  (doseq [op '[kernel-dequant-dot-q4-k kernel-dequant-dot-q6-k]]
    (testing (str op)
      (let [source (str "(ns k (:export [go]))\n"
                        "(defn go [a :i64 b :i64 c :i64 d :i64 n :i64]\n"
                        "  (" op " a b c d n))")]
        (is (some? (:artifact (compiler/compile-source source :x86_64-kotoba-v1 {})))
            "x86-64 emits it")
        (is (thrown? clojure.lang.ExceptionInfo
                     (compiler/compile-source source :aarch64-kotoba-v1 {}))
            (str op " reached the AArch64 backend"))))))
