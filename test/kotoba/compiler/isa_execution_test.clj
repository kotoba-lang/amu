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
            [clojure.string :as str]
            [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]
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

(def ^:private cases
  (vec (concat base-cases
               record-result-cases
               string-search-cases
               bool-parameter-cases
               boolean-literal-argument-cases)))

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
