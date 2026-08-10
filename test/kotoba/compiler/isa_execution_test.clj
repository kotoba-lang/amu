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
            [kotoba.compiler.core :as compiler]))

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

(defn- run-native
  ([isa source] (run-native isa source "-" {:allow #{}}))
  ([isa source allow policy]
   (run-native isa source allow policy 'main []))
  ([isa source allow policy entry args]
   (let [[_ target] (isas isa)
         artifact (:artifact (compiler/compile-source source target policy))
         code (tmp (str "kotoba-isa-code-" isa ".bin"))
         offset (get-in artifact [:exports entry :offset])]
     (with-open [out (io/output-stream code)]
       (.write out (byte-array (map #(unchecked-byte (bit-and (int %) 0xff))
                                    (:code artifact)))))
     (:out (apply shell/sh
                  (concat [(@loaders isa) (.getPath code) (str offset)
                           (str (count args)) isa allow]
                          (map str args)
                          [:env (assoc (into {} (System/getenv))
                                       "KEXE_STRUCTURED_REPORT" "1")]))))))

(def ^:private f64-one 4607182418800017408)
(def ^:private f64-two 4611686018427387904)
(def ^:private f64-nan 9221120237041090560)

(defn- f64c [op a b] (str "(defn main [] (if (" op " (f64-from-bits " a
                          ") (f64-from-bits " b ")) 1 0))"))

(def ^:private record-type "[:record :t/r [[:a :i64] [:b :i64]]]")
(def ^:private option-record-type
  "[:record :t/o [[:m [:option :i64]] [:x :i64]]]")

(def ^:private base-cases
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
