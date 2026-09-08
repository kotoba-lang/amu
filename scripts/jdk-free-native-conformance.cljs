#!/usr/bin/env nbb
(ns jdk-free-native-conformance
  (:require [clojure.string :as str]
            ;; The reader this suite's `i64-beyond-double` control measures
            ;; AGAINST -- it is not used to read anything the suite relies on.
            [cljs.reader]
            ["node:child_process" :as child]
            ["node:crypto" :as crypto]
            ["node:fs" :as fs]
            ["node:os" :as os]
            ["node:path" :as path]))

(def root (.resolve path (.dirname path *file*) ".."))
(def tmp (.mkdtempSync fs (.join path (.tmpdir os) "amu-jdk-free-native-")))
(def shadow (.join path tmp "shadow"))
(def marker (.join path tmp "jvm-invoked.log"))
(def amu (.join path root "bin" "amu"))
(defn file [name] (.join path tmp name))
(defn ensure! [condition message] (when-not condition (throw (js/Error. message))))

(defn- magic
  "The three header fields that say what container a file actually is."
  [p]
  (let [b (fs/readFileSync p)]
    {:head (.toString (.subarray b 1 4) "latin1")
     :type (.readUInt16LE b 16)
     :machine (.readUInt16LE b 18)}))

(defn- sha256-file [p]
  (-> (crypto/createHash "sha256") (.update (fs/readFileSync p)) (.digest "hex")))

;; ELF64 symbol table, read here rather than shelled out to `readelf`, which
;; this platform does not ship. The aiueos object contract is a property of
;; the SYMBOL TABLE -- exactly one GLOBAL FUNC -- and asserting it on the
;; compiler's own `:exports` map would be asserting that the packager agrees
;; with itself.
(def ^:private sht-symtab 2)
(def ^:private stb-global 1)
(def ^:private stt-func 2)
(def ^:private sym-entry-bytes 24)

(defn- elf-symbols [p]
  (let [b (fs/readFileSync p)
        section-offset (js/Number (.readBigUInt64LE b 0x28))
        section-bytes (.readUInt16LE b 0x3a)
        section-count (.readUInt16LE b 0x3c)
        section (fn [index] (+ section-offset (* index section-bytes)))
        symtab (first (filter #(= sht-symtab (.readUInt32LE b (+ (section %) 4)))
                              (range section-count)))]
    (ensure! symtab (str p " carries no .symtab, so its symbols cannot be checked"))
    (let [table (js/Number (.readBigUInt64LE b (+ (section symtab) 24)))
          table-bytes (js/Number (.readBigUInt64LE b (+ (section symtab) 32)))
          strings (js/Number (.readBigUInt64LE
                              b (+ (section (.readUInt32LE b (+ (section symtab) 40))) 24)))
          name-at (fn [offset]
                    (let [start (+ strings offset)]
                      (.toString (.subarray b start (.indexOf b 0 start)) "latin1")))]
      (ensure! (pos? table-bytes) (str p " has an empty .symtab"))
      (vec (for [index (range (quot table-bytes sym-entry-bytes))
                 :let [at (+ table (* index sym-entry-bytes))
                       info (.readUInt8 b (+ at 4))]]
             {:name (name-at (.readUInt32LE b at))
              :bind (bit-shift-right info 4)
              :type (bit-and info 0xf)})))))

(defn- elf-symbol-names [p] (mapv :name (elf-symbols p)))

(defn- elf-global-funcs [p]
  (->> (elf-symbols p)
       (filter #(and (= stb-global (:bind %)) (= stt-func (:type %))))
       (mapv :name)
       sort vec))


(defn run
  ([command args env] (run command args env false))
  ([command args env allow-failure?]
   (let [result (.spawnSync child command (clj->js args)
                            #js {:cwd root :encoding "utf8" :maxBuffer 16777216
                                 :env env})
         status (if (nil? (.-status result)) 70 (.-status result))]
     (when (.-error result) (throw (.-error result)))
     (when (and (not allow-failure?) (not= 0 status))
       (throw (js/Error. (str "command failed: " command " " (str/join " " args)
                              "\n" (or (.-stderr result) "")))))
     {:status status :stdout (or (.-stdout result) "")
      :stderr (or (.-stderr result) "")})))

(try
  (fs/mkdirSync shadow)
  (doseq [binary ["java" "javac" "clojure" "clj"]]
    (let [target (.join path shadow binary)]
      (fs/writeFileSync target
                        (str "#!/bin/sh\necho '" binary " $*' >> '" marker
                             "'\necho '" binary ": forbidden by JDK-free conformance' >&2\nexit 127\n"))
      (fs/chmodSync target (js/parseInt "755" 8))))
  (let [platform (.platform os)
        arch (.arch os)
        isa (cond
              (contains? #{"arm64" "aarch64"} arch) "aarch64"
              (= "x64" arch) "x86_64"
              :else (throw (js/Error. (str "unsupported native conformance architecture: " arch))))
        _ (ensure! (contains? #{"darwin" "linux"} platform)
                   (str "unsupported native conformance platform: " platform))
        env (js/Object.assign #js {} js/process.env
                              #js {"PATH" (str shadow (.-delimiter path) (.-PATH js/process.env))
                                   "JAVA_HOME" (.join path tmp "no-java-home")})
        invoke (fn [args] (run js/process.execPath (into [amu] args) env))
        loader (file "kexe-loader")]
    (run "cc" ["-std=c11" "-O2" "-Wall" "-Wextra" "-Werror"
                (.join path root "tools" "kexe_loader.c") "-o" loader] env)
    (doseq [{:keys [source symbol arguments expected]}
            [;; A zero i64 literal reaches MIR as a JavaScript BigInt under
             ;; nbb. Keep this first so register classification can never
             ;; regress into hashing that primitive as a physical register.
             {:source "i64-semantics.kotoba" :symbol "main"
              :arguments [] :expected "0"}
             {:source "structured.kotoba" :symbol "score"
              :arguments ["-7" "2"] :expected "12"}
             {:source "nested-record.kotoba" :symbol "nested-score"
              :arguments [] :expected "15"}
             {:source "held-operations.kotoba" :symbol "held-score"
              :arguments [] :expected "54"}
             ;; More than eight DISTINCT constants in one branchless leaf.
             ;; The case above guards a single i64 literal against being hashed
             ;; as a register; one literal cannot grow a map past the
             ;; PersistentArrayMap boundary, so it structurally could not see
             ;; the sibling failure: `a64-cache-leaf-constants` keyed its
             ;; occurrences map by the raw i64, and past eight entries the map
             ;; hashes a BigInt primitive and throws. `kernel_deep.kotoba` and
             ;; `kernel_wide.kotoba` -- the two fixtures this repository
             ;; benchmarks itself on -- could not be built through `bin/amu`
             ;; while the JVM front compiled both.
             ;;
             ;; Eight lanes is the measured threshold on the broken backend:
             ;; four compile clean, eight do not. Expected value measured by
             ;; executing the artifact, not computed and trusted.
             {:source "many-constants.kotoba" :symbol "many-constants"
              :arguments ["1"] :expected "1737764"}
             ;; All three i64 shifts. `kotoba-verifier` re-derives the "shift
             ;; count must be an integer LITERAL in [0,63]" rule, and until
             ;; 3d7a6f0 it re-derived it with bare `integer?` -- false for the
             ;; JavaScript bigint every guest literal is under nbb. The count
             ;; of every shift therefore failed the literal test and NO
             ;; artifact using one could be built HERE, while `clojure -M:run`
             ;; compiled the same source. Neither the JVM suite nor the JVM
             ;; route of `bin/amu` could see it; only this driver can.
             ;;
             ;; The `+1` at x = -8 is contributed only by the logical right
             ;; shift, so the three entries cannot be confused for each other.
             ;; Measured by executing the artifact, not computed and trusted.
             {:source "i64-shift.kotoba" :symbol "mixed"
              :arguments ["-8"] :expected "-67"}
             ;; An i64 literal past 2^53, carried end to end. Until 2026-09-08
             ;; `extract-native` read the artifact with `cljs.reader`, which
             ;; returns a `js/Number` for every integer token -- so it did not
             ;; corrupt the artifact so much as fail to read it, and since the
             ;; seal is over the exact values it then refused its own
             ;; compiler's output as "artifact integrity mismatch". Every
             ;; fixture that reached this command had constants under 2^53,
             ;; where a Number is exact, so nothing here could see it; the
             ;; first program in the tree whose constants do not fit --
             ;; SHA-512, whose first round constant this is -- was refused on
             ;; the first try. The expected value is the LITERAL: a rounded
             ;; read prints 4794697086780617000, which this distinguishes
             ;; from a bare "it verified".
             {:source "i64-beyond-double.kotoba" :symbol "main"
              :arguments [] :expected "4794697086780616226"}]]
      (let [artifact (file (str symbol ".kexe"))
            binary (file (str symbol ".bin"))]
        (invoke ["compile" (.join path root "examples" source)
                 "--target" isa "--output" artifact])
        (let [extracted (:stdout (invoke ["extract-native" artifact "--symbol" symbol
                                         "--output" binary]))
              [_ offset] (re-find #":offset ([0-9]+)" extracted)]
          (ensure! offset (str "extract-native returned no " symbol " offset"))
          (let [executed (run loader
                              (into [binary offset (str (count arguments)) isa "-"]
                                    arguments)
                              env)]
            (ensure! (= expected (str/trim (:stdout executed)))
                     (str "native " symbol " expected " expected ", got "
                          (str/trim (:stdout executed))))))))
    ;; The oracle's budget is the caller's. `kotoba.kir/lower` seals a pure
    ;; entry's value by EXECUTING it, and that execution used to run on a
    ;; private 100,000 that no flag could reach: `--fuel` went to the
    ;; artifact's `:limits` and the verifier's re-execution and stopped there.
    ;; So a program costing more than that was refused as `fuel-exhausted`
    ;; whatever its author declared -- measured on the X25519 Montgomery
    ;; ladder, identically at `--fuel 60000000` and at the largest budget KIR
    ;; admits.
    ;;
    ;; Both directions, because each alone proves nothing: without the flag it
    ;; must still refuse (a default that quietly became unbounded would
    ;; compile a runaway recursion for as long as the machine tolerated it),
    ;; and with the flag it must compile AND the binary must answer 160,000 --
    ;; the value distinguishes a budget that was really in force from a
    ;; refusal that merely stopped happening.
    (let [source (.join path root "examples" "oracle-fuel-budget.kotoba")
          artifact (file "oracle-fuel-budget.kexe")
          binary (file "oracle-fuel-budget.bin")
          refused (run js/process.execPath
                       [amu "compile" source "--target" isa "--output" artifact]
                       env true)]
      (ensure! (not= 0 (:status refused))
               "a program past the oracle's default budget compiled with no budget named")
      (ensure! (str/includes? (str (:stdout refused) (:stderr refused)) "fuel-exhausted")
               (str "the no-budget refusal named a different cause: " (:stderr refused)))
      (invoke ["compile" source "--target" isa "--fuel" "10000000" "--output" artifact])
      (let [extracted (:stdout (invoke ["extract-native" artifact "--symbol" "main"
                                        "--output" binary]))
            [_ offset] (re-find #":offset ([0-9]+)" extracted)]
        (ensure! offset "extract-native returned no oracle-fuel-budget offset")
        (let [executed (run loader [binary offset "0" isa "-"]
                            (js/Object.assign #js {} env #js {"KEXE_FUEL" "10000000"}))]
          (ensure! (= "160000" (str/trim (:stdout executed)))
                   (str "native oracle-fuel-budget expected 160000, got "
                        (str/trim (:stdout executed)))))))

    ;; The control for the case above. `i64-beyond-double` only discriminates
    ;; between an exact reader and a lossy one while the artifact it produces
    ;; actually contains a token `cljs.reader` cannot hold -- if the example
    ;; ever drifted under 2^53 the case would pass for either reader and
    ;; assert nothing. Rather than trust that, read the artifact the way the
    ;; command used to and require that it still loses the constant. Failing
    ;; here does not mean the compiler is wrong; it means this suite can no
    ;; longer tell the two readers apart.
    (let [artifact (file "i64-beyond-double-control.kexe")
          literal "4794697086780616226"]
      (invoke ["compile" (.join path root "examples" "i64-beyond-double.kotoba")
               "--target" isa "--output" artifact])
      (let [text (fs/readFileSync artifact "utf8")
            lossy (pr-str (cljs.reader/read-string text))]
        (ensure! (str/includes? text literal)
                 (str "examples/i64-beyond-double.kotoba no longer puts " literal
                      " in its artifact, so the case above asserts nothing"))
        (ensure! (not (str/includes? lossy literal))
                 (str "cljs.reader no longer loses " literal
                      " in this artifact, so this suite cannot tell the "
                      "i64-preserving reader from the lossy one. Fix the "
                      "example, do not relax this check"))))

    ;; ------------------------------------------------------------------
    ;; kbb host contract of the loader (owner rule kbb-first, 2026-09-07).
    ;; These run the loader JVM-free against guests compiled here, so they
    ;; hold without the artifact runtime identity the JVM suite needs.
    ;;
    ;; KEXE_FUEL: the loader takes its fuel budget from the environment.
    ;; examples/fuel.kotoba's `forever` is the recursion that must trap: under
    ;; the default it traps with `:initial 512 :remaining 0`; under
    ;; KEXE_FUEL=100000 the report says `:initial 100000 :remaining 0` -- the
    ;; budget was in force, and exhausted (a report that still said 512 would
    ;; mean the knob did nothing). A zero, negative or non-decimal budget is
    ;; refused before the guest starts (exit 2), never coerced.
    (let [artifact (file "fuel-budget.kexe")
          binary (file "fuel-budget.bin")
          with-env (fn [extra] (js/Object.assign #js {} env (clj->js extra)))]
      (invoke ["compile" (.join path root "examples" "fuel.kotoba")
               "--target" isa "--output" artifact])
      (let [extracted (:stdout (invoke ["extract-native" artifact "--symbol" "forever"
                                        "--output" binary]))
            [_ offset] (re-find #":offset ([0-9]+)" extracted)
            _ (ensure! offset "extract-native returned no forever offset")
            args [binary offset "1" isa "-" "0"]
            default (run loader args (with-env {"KEXE_STRUCTURED_REPORT" "1"}) true)
            budget (run loader args (with-env {"KEXE_STRUCTURED_REPORT" "1"
                                               "KEXE_FUEL" "100000"}) true)]
        (ensure! (and (= 120 (:status default))
                      (str/includes? (:stdout default) ":fuel {:initial 512 :remaining 0}"))
                 (str "default fuel: forever did not exhaust 512: "
                      (:status default) " " (str/trim (:stdout default))))
        (ensure! (and (= 120 (:status budget))
                      (str/includes? (:stdout budget) ":fuel {:initial 100000 :remaining 0}"))
                 (str "KEXE_FUEL=100000 was not the budget in force: "
                      (:status budget) " " (str/trim (:stdout budget))))
        (doseq [bad ["0" "abc" "-5" "12abc" "+7"]]
          (let [refused (run loader args (with-env {"KEXE_FUEL" bad}) true)]
            (ensure! (= 2 (:status refused))
                     (str "KEXE_FUEL=" bad " was not refused with exit 2: "
                          (:status refused) " " (:stderr refused)))))))

    ;; :fs/browse (wire id 34): the loader lists ONE directory inside
    ;; KEXE_CAP_RESOURCES_34 -- entry names sorted bytewise, "\n"-joined, "."
    ;; and ".." excluded, dotfiles included -- the shape kotoba's js host
    ;; answers for the same wire id. Byte-exact through KEXE_RESULT_TYPE=string.
    ;; With no scope, a scope elsewhere, or a regular file as the request the
    ;; call traps (SIGILL, exit 120) instead of answering. Guest sources are
    ;; written here because the directory under test only exists here.
    (let [dir (file "browse-dir")
          other (file "browse-other")
          hex (fn [s] (.toString (js/Buffer.from s "utf8") "hex"))
          string-env (fn [extra] (js/Object.assign #js {} env
                                                   (clj->js (merge {"KEXE_STRUCTURED_REPORT" "1"
                                                                    "KEXE_RESULT_TYPE" "string"}
                                                                   extra))))
          guest! (fn [name request]
                   (let [source (file (str name ".kotoba"))
                         policy (file (str name "-policy.edn"))
                         artifact (file (str name ".kexe"))
                         binary (file (str name ".bin"))]
                     (fs/writeFileSync source
                                       (str "(ns conformance." name " (:export [main]))\n"
                                            "(defn main [] :string "
                                            "(typed-cap-call :fs/browse :string :string \"" request "\"))\n"))
                     (fs/writeFileSync policy "{:allow #{[:cap/call 34]}}")
                     (invoke ["compile" source "--target" isa "--policy" policy "--output" artifact])
                     (let [[_ offset] (re-find #":offset ([0-9]+)"
                                               (:stdout (invoke ["extract-native" artifact
                                                                 "--symbol" "main" "--output" binary])))]
                       (ensure! offset (str "extract-native returned no offset for " name))
                       [binary offset "0" isa "34"])))]
      (fs/mkdirSync dir)
      (fs/mkdirSync other)
      (doseq [n ["b.txt" "a.txt" ".hidden" "z"]] (fs/writeFileSync (.join path dir n) n))
      (let [args (guest! "browse-listing" dir)
            listed (run loader args (string-env {"KEXE_CAP_RESOURCES_34" dir}) true)
            expected (str ":result-utf8-hex \"" (hex ".hidden\t0\na.txt\t0\nb.txt\t0\nz\t0") "\"")]
        (ensure! (and (= 0 (:status listed)) (str/includes? (:stdout listed) expected))
                 (str "browse listing mismatch: " (:status listed) " " (str/trim (:stdout listed)) " " (str/trim (:stderr listed))))
        (doseq [[label extra] [["no scope" {}]
                               ["a scope elsewhere" {"KEXE_CAP_RESOURCES_34" other}]]]
          (let [refused (run loader args (string-env extra) true)]
            (ensure! (and (= 120 (:status refused))
                          (str/includes? (:stderr refused) ":signal :SIGILL"))
                     (str "browse with " label " was not refused: "
                          (:status refused) " " (:stderr refused))))))
      (let [args (guest! "browse-file" (.join path dir "a.txt"))
            refused (run loader args (string-env {"KEXE_CAP_RESOURCES_34" dir}) true)]
        (ensure! (and (= 120 (:status refused)) (str/includes? (:stderr refused) ":signal :SIGILL"))
                 (str "browse of a regular file was not refused: " (:status refused) " " (:stderr refused))))
      (let [args (guest! "browse-empty" other)
            empty (run loader args (string-env {"KEXE_CAP_RESOURCES_34" other}) true)]
        (ensure! (and (= 0 (:status empty)) (str/includes? (:stdout empty) ":result-utf8-hex \"\""))
                 (str "empty directory did not answer the empty string: "
                      (:status empty) " " (str/trim (:stdout empty)) " " (str/trim (:stderr empty))))))

    ;; :fs/app-data RANGE form (wire id 35): "<path>RANGE_SEP<offset>:<length>"
    ;; answers exactly that window of a file -- here 70,000 bytes, larger than
    ;; one guest string and than the loader's string pool, with U+2500 (three
    ;; bytes) planted at byte 5000. Byte-exact against the fixture through
    ;; KEXE_RESULT_TYPE=string. A window past EOF, a window that cuts the
    ;; code point, and the whole-file read of the same file (pool overflow --
    ;; the reason the range form exists) all trap instead of answering short.
    (let [big (file "range-big.txt")
          ascii (fn [n] (let [pattern "0123456789abcdef\n"]
                          (.slice (.repeat pattern (inc (quot n (count pattern)))) 0 n)))
          text (str (ascii 5000) "─" (ascii (- 70000 5003)))
          bytes (js/Buffer.from text "utf8")
          _ (ensure! (= 70000 (.-length bytes)) (str "range fixture is " (.-length bytes) " bytes"))
          hex (fn [buf] (.toString buf "hex"))
          string-env (fn [extra] (js/Object.assign #js {} env
                                                   (clj->js (merge {"KEXE_STRUCTURED_REPORT" "1"
                                                                    "KEXE_RESULT_TYPE" "string"
                                                                    "KEXE_CAP_RESOURCES_35" tmp}
                                                                   extra))))
          guest! (fn [name request]
                   (let [source (file (str name ".kotoba"))
                         policy (file (str name "-policy.edn"))
                         artifact (file (str name ".kexe"))
                         binary (file (str name ".bin"))]
                     (fs/writeFileSync source
                                       (str "(ns conformance." name " (:export [main]))\n"
                                            "(defn main [] :string "
                                            "(typed-cap-call :fs/app-data :string :string \"" request "\"))\n"))
                     (fs/writeFileSync policy "{:allow #{[:cap/call 35]}}")
                     (invoke ["compile" source "--target" isa "--policy" policy "--output" artifact])
                     (let [[_ offset] (re-find #":offset ([0-9]+)"
                                               (:stdout (invoke ["extract-native" artifact
                                                                 "--symbol" "main" "--output" binary])))]
                       (ensure! offset (str "extract-native returned no offset for " name))
                       [binary offset "0" isa "35"])))
          window! (fn [name offset length]
                    (let [args (guest! name (str big "RANGE_SEP" offset ":" length))
                          answered (run loader args (string-env {}) true)
                          expected (str ":result-utf8-hex \"" (hex (.subarray bytes offset (+ offset length))) "\"")]
                      (ensure! (and (= 0 (:status answered)) (str/includes? (:stdout answered) expected))
                               (str name " [" offset ", " (+ offset length) ") mismatch: "
                                    (:status answered) " " (subs (str/trim (:stdout answered)) 0 200)
                                    " " (str/trim (:stderr answered))))))
          refused! (fn [name request why]
                     (let [args (guest! name request)
                           refused (run loader args (string-env {}) true)]
                       (ensure! (and (= 120 (:status refused)) (str/includes? (:stderr refused) ":signal :SIGILL"))
                                (str why " was not refused: " (:status refused) " " (:stderr refused)))))]
      (fs/writeFileSync big bytes)
      (window! "range-head" 0 4096)
      (window! "range-tail" 66000 4000)
      (window! "range-across-code-point" 4990 20)
      (refused! "range-past-eof" (str big "RANGE_SEP69500:1000") "a window past EOF")
      (refused! "range-cut-code-point" (str big "RANGE_SEP5001:4") "a window cutting U+2500")
      (refused! "range-twice" (str big "RANGE_SEP0:4RANGE_SEP") "a second RANGE_SEP")
      (refused! "range-whole-file" big "the whole-file read of a 70,000-byte file"))

    ;; The aiueos target profiles package the sealed artifact into an ELF64 or
    ;; PE32+ container. Until `kotoba.compiler.nbb.native-package` existed this
    ;; driver had no packaging step at all, so `os/aiueos` built all 67 of its
    ;; kernel objects through `clojure` -- not because code generation needed a
    ;; JVM (these targets reach the same two emitters exercised above) but
    ;; because only the JVM CLI ran the packager.
    ;;
    ;; Asserted on the container bytes rather than on the exit status, because
    ;; the failure this guards against is not a crash: admitting the target
    ;; without a packager would have written artifact EDN to a path named `.o`
    ;; and reported :ok true. A wrong answer, delivered quietly.
    (do
      (doseq [{:keys [target artifact-kind expect-type expect-machine label]}
              [{:target "x86_64-aiueos-kernel-v1" :artifact-kind nil
                :expect-type 1 :expect-machine 0x3e :label "kernel object (ET_REL, EM_X86_64)"}
               ;; The x86-64 kernel IMAGE is deliberately absent: the two
               ;; `kotoba.native.elf64` twins genuinely disagree about it
               ;; (kotoba-native ADR-0036 keeps the live-boot GDT/TSS shim in
               ;; the JVM file only), so this route refuses it rather than
               ;; serving a different one. Asserted below.
               {:target "aarch64-aiueos-kernel-v1" :artifact-kind "image"
                :expect-type 2 :expect-machine 0xb7 :label "kernel image (ET_EXEC, EM_AARCH64)"}]]
        (let [out (file (str "aiueos-" target "-" (or artifact-kind "default") ".o"))]
          (invoke (cond-> ["compile" (.join path root "examples" "i64-semantics.kotoba")
                           "--target" target "--output" out]
                    artifact-kind (into ["--artifact" artifact-kind])))
          (let [{:keys [head type machine]} (magic out)]
            (ensure! (= "ELF" head)
                     (str "aiueos " label " is not ELF64; got " (pr-str head)
                          " -- artifact EDN written where a container belongs"))
            (ensure! (= expect-type type)
                     (str "aiueos " label " has e_type " type))
            (ensure! (= expect-machine machine)
                     (str "aiueos " label " has e_machine " machine)))))
      (let [efi (file "aiueos-uefi.efi")]
        (invoke ["compile" (.join path root "examples" "i64-semantics.kotoba")
                 "--target" "x86_64-aiueos-uefi-v1" "--artifact" "image" "--output" efi])
        (ensure! (= "MZ" (.toString (.subarray (fs/readFileSync efi) 0 2) "latin1"))
                 "aiueos UEFI image is not a PE32+ application"))
      ;; Refused, not served differently. Asserted on the OUTPUT FILE as well
      ;; as the status, because the failure guarded against is producing a
      ;; materially different kernel image under a flag whose whole value is
      ;; that it refuses instead of falling back.
      (let [refused (run js/process.execPath
                         [amu "compile" (.join path root "examples" "i64-semantics.kotoba")
                          "--target" "x86_64-aiueos-kernel-v1" "--artifact" "image"
                          "--output" (file "divergent.elf") "--jvm-free"]
                         env true)]
        (ensure! (not= 0 (:status refused))
                 "the x86-64 kernel image was served on the JDK-free route despite the twins disagreeing")
        (ensure! (.includes (str (:stdout refused) (:stderr refused)) "live-boot")
                 "the kernel-image refusal did not name why the twins disagree")
        (ensure! (not (fs/existsSync (file "divergent.elf")))
                 "the refused kernel image still wrote an output file"))
      ;; An unknown --artifact must be refused BEFORE the work, not discovered
      ;; after it, and must not fall through to writing the artifact EDN.
      (let [rejected (run js/process.execPath
                          [amu "compile" (.join path root "examples" "i64-semantics.kotoba")
                           "--target" "x86_64-aiueos-kernel-v1" "--artifact" "sections"
                           "--output" (file "rejected.o")]
                          env true)]
        (ensure! (not= 0 (:status rejected))
                 "an unknown --artifact kind was accepted")
        (ensure! (not (fs/existsSync (file "rejected.o")))
                 "an unknown --artifact kind still wrote an output file")))

    ;; ---------------------------------------------------------------------
    ;; Project route on the NATIVE driver.
    ;;
    ;; `--source-path` and `--module-lock` reached only the Wasm driver,
    ;; because `resolve-source!` was written inside `wasm-cli` rather than
    ;; beside the thing it does. The native driver read the entry file and
    ;; nothing else, so both flags were accepted on the command line and
    ;; silently ignored: measured 2026-09-02 on b1fdaad2, a two-module
    ;; fixture on `x86_64-aiueos-kernel-v1` was refused with
    ;; `:kotoba.error/namespace-require-needs-project` -- the SAME answer,
    ;; byte for byte, whether the roots were named or not.
    ;;
    ;; The consequence outside this repository is aiueos: a kernel object
    ;; that cannot import anything has to inline every helper it uses, so
    ;; SHA-256 was copied into three sources and about to be copied into
    ;; three more.
    (let [project (file "project")
          modules (.join path project "kproj")
          ;; The non-entry module deliberately exports an `aiueos-`
          ;; prefixed name that `kernel-object-entries` does not list. If a
          ;; dependency's exports reached the packager, this is the export
          ;; that would refuse the whole object -- and if they reached the
          ;; ELF symbol table instead, the aiueos verifier's
          ;; exactly-one-GLOBAL-FUNC rule would fail on it.
          helper (str "(ns kproj.helper\n"
                      "  (:export [twice aiueos-not-a-symbol]))\n"
                      "(defn twice [x] (* x 2))\n"
                      "(defn aiueos-not-a-symbol [x] (+ x 1))\n")
          entry (str "(ns kproj.entry\n"
                     "  (:require [kproj.helper :as helper])\n"
                     "  (:export [main aiueos-fnv1a]))\n"
                     "(defn aiueos-fnv1a [base length]\n"
                     "  (helper/twice (+ base length)))\n"
                     "(defn main [] 0)\n")
          entry-path (.join path modules "entry.kotoba")
          blocks (file "blocks")
          lock (file "kotoba.modules.edn")]
      (fs/mkdirSync modules #js {:recursive true})
      (fs/mkdirSync blocks)
      (fs/writeFileSync (.join path modules "helper.kotoba") helper)
      (fs/writeFileSync entry-path entry)

      ;; 1. The refusal is gone and what comes back is a kernel object.
      (let [out (file "project-kernel.o")]
        (invoke ["compile" entry-path "--source-path" project "--unpinned"
                 "--target" "x86_64-aiueos-kernel-v1" "--output" out])
        (let [{:keys [head type machine]} (magic out)]
          (ensure! (= "ELF" head)
                   (str "project-route kernel object is not ELF64: " (pr-str head)))
          (ensure! (= 1 type) (str "project-route kernel object has e_type " type))
          (ensure! (= 0x3e machine)
                   (str "project-route kernel object has e_machine " machine)))

        ;; 2. Exactly ONE global function, and it is the ENTRY module's --
        ;; the aiueos verifier's own rule (`verify-kotoba-kernel-object.py`).
        (let [globals (elf-global-funcs out)
              names (elf-symbol-names out)]
          (println (str "SCANNED symtab=" (count names)
                        " global-funcs=" (count globals) " " (pr-str globals)))
          (ensure! (= ["kotoba_aiueos_fnv1a"] globals)
                   (str "project-route object's global functions were "
                        (pr-str globals) ", not exactly [kotoba_aiueos_fnv1a]")))

        ;; 3. And the reason it is only one: `link-source` emits every
        ;; non-root function as `defn-`, so a DEPENDENCY's exports are not
        ;; exports of the linked unit. Asserted on the export surface rather
        ;; than on the symbol table, because the symbol table cannot show
        ;; this either way -- a kernel object names one public symbol and
        ;; `kotoba_source_entry` whatever the Kotoba exports were, so a
        ;; symbol-table check for the dependency's name would pass by
        ;; construction and never fail. `kproj.helper` exports
        ;; `aiueos-not-a-symbol`, a name `kernel-object-entries` does not
        ;; carry: if it reached the linked unit's exports the packager would
        ;; refuse the object outright (asserted in the other direction
        ;; below), so this is the load-bearing half of why the fixture
        ;; compiles at all.
        (let [checked (:stdout (invoke ["check" entry-path "--source-path" project]))]
          (ensure! (str/includes? checked ":exports [aiueos-fnv1a main]")
                   (str "the linked unit's exports were not the entry module's: "
                        checked))
          (ensure! (not (str/includes? checked "aiueos-not-a-symbol"))
                   (str "a NON-ENTRY module's export became an export of the "
                        "linked unit: " checked)))

        ;; 4. The pinned route builds the same bytes as the searched one.
        ;; Same graph, one resolver verified by CID and one not; if they
        ;; disagreed, a lock would be pinning a different build than the
        ;; source paths it was derived from.
        (invoke ["module-lock" entry-path "--source-path" project
                 "--blocks" blocks "--output" lock])
        (let [locked (file "project-kernel-locked.o")]
          (invoke ["compile" "--module-lock" lock "--blocks" blocks
                   "--target" "x86_64-aiueos-kernel-v1" "--output" locked])
          (ensure! (= (sha256-file out) (sha256-file locked))
                   "the --module-lock and --source-path routes built different objects")))

      ;; 5. The AArch64 kernel profile reaches the same shared code, so it
      ;; is asserted rather than assumed: one driver, two ISA entrypoints.
      (let [out (file "project-kernel-aarch64.elf")]
        (invoke ["compile" entry-path "--source-path" project "--unpinned"
                 "--target" "aarch64-aiueos-kernel-v1" "--artifact" "image"
                 "--output" out])
        (let [{:keys [head type machine]} (magic out)]
          (ensure! (and (= "ELF" head) (= 2 type) (= 0xb7 machine))
                   (str "project-route AArch64 kernel image is "
                        (pr-str [head type machine])))))

      ;; 6. A module the roots do not contain stops the build, by the
      ;; resolver's own sentence. Asserted on the message because five
      ;; different things in this area all end with a module that did not
      ;; load, and on the absent output because a refusal that still writes
      ;; is not a refusal.
      (let [lonely (file "lonely")
            lonely-modules (.join path lonely "kproj")
            out (file "lonely.o")]
        (fs/mkdirSync lonely-modules #js {:recursive true})
        (fs/writeFileSync (.join path lonely-modules "entry.kotoba") entry)
        (let [refused (run js/process.execPath
                           [amu "compile" (.join path lonely-modules "entry.kotoba")
                            "--source-path" lonely "--unpinned"
                            "--target" "x86_64-aiueos-kernel-v1" "--output" out]
                           env true)]
          (ensure! (not= 0 (:status refused))
                   "a project missing one of its modules compiled anyway")
          (ensure! (str/includes? (str (:stdout refused) (:stderr refused))
                                  "required module is missing from the explicit source paths")
                   (str "the missing-module refusal named a different cause: "
                        (:stderr refused)))
          (ensure! (not (fs/existsSync out))
                   "the refused project still wrote an object")))

      ;; 7. The discriminating pair. The SAME unlisted `aiueos-` name is
      ;; harmless in a dependency (asserted above) and fatal in the entry
      ;; module, because only the entry module's exports are the object's
      ;; exports. And the refusal must arrive as a refusal: packagers raise
      ;; `ex-info` without a `:phase`, which this CLI's exit table read as
      ;; :internal -- so until now the answer was exit 70 and the words
      ;; `internal compiler error`, with the real sentence discarded.
      (let [leak (file "leak")
            leak-modules (.join path leak "kproj")
            out (file "leak.o")]
        (fs/mkdirSync leak-modules #js {:recursive true})
        (fs/writeFileSync (.join path leak-modules "helper.kotoba")
                          "(ns kproj.helper\n  (:export [twice]))\n(defn twice [x] (* x 2))\n")
        (fs/writeFileSync (.join path leak-modules "entry.kotoba")
                          (str "(ns kproj.entry\n"
                               "  (:require [kproj.helper :as helper])\n"
                               "  (:export [main aiueos-not-a-symbol]))\n"
                               "(defn aiueos-not-a-symbol [base length]\n"
                               "  (helper/twice (+ base length)))\n"
                               "(defn main [] 0)\n"))
        (let [refused (run js/process.execPath
                           [amu "compile" (.join path leak-modules "entry.kotoba")
                            "--source-path" leak "--unpinned"
                            "--target" "x86_64-aiueos-kernel-v1" "--output" out]
                           env true)
              said (str (:stdout refused) (:stderr refused))]
          (ensure! (not= 0 (:status refused))
                   "an unlisted aiueos-* export in the entry module was packaged")
          (ensure! (str/includes?
                    said "Kotoba kernel object declares an aiueos export with no admitted symbol")
                   (str "the unlisted-export refusal named a different cause: " said))
          (ensure! (str/includes? said ":error :artifact-target")
                   (str "a packager's deliberate refusal was still reported as an "
                        "internal compiler error: " said))
          (ensure! (not (fs/existsSync out))
                   "the refused object was written anyway")))

      ;; 8. The single-file route is untouched: still one global function,
      ;; still the probe contract for a source that claims no aiueos name.
      (let [out (file "single-file-kernel.o")]
        (invoke ["compile" (.join path root "examples" "i64-semantics.kotoba")
                 "--target" "x86_64-aiueos-kernel-v1" "--output" out])
        (let [globals (elf-global-funcs out)]
          (ensure! (= ["kotoba_aiueos_probe"] globals)
                   (str "single-file kernel object's global functions were "
                        (pr-str globals))))))

    (when (fs/existsSync marker)
      (throw (js/Error. (str "JVM tool was invoked: " (fs/readFileSync marker "utf8")))))
    (println (str "jdk-free-native: sealed " isa
                  " scalar, aggregate-variant, callable, bounded-apply artifacts independently extracted"
                  " and executed under W^X loader; aiueos ELF64 object/user/aarch64 images and PE32+ image packaged; divergent x86-64 kernel image refused")))
  (finally
    (fs/rmSync tmp #js {:recursive true :force true})))
