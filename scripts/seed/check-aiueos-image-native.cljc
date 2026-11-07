;; Diagnostic for JUN-31's native image packaging step, not a boot/CDCI pass.
;;
;; The producers must be the fixed-point F images in an actual loaderless selfhost bootstrap receipt. Basilisp
;; starts them and independently inspects their bytes; it never compiles or packages guest code. No legacy host
;; oracle is invoked. Complete kernel/ISR/EFI/GPT and QEMU/GOP/input remain separate.
;; Ported from check-aiueos-image-native.py (Basilisp). Linux only; other gates load `verify` from here.
;; Run: basilisp run scripts/seed/check-aiueos-image-native.cljc -- (--build DIR | --complete DIR) --output OUT
(ns check-aiueos-image-native
  (:require [aiueos-gate :as g]
            [aiueos-native-proof :as proof]
            [basilisp.string :as str]
            [gate-util :as u])
  (:import operator os platform struct subprocess sys))

(def target "x86_64-aiueos-kernel-v1")
(def data-size 77824)

(defn- cat-bytes [& parts] (reduce operator/add (u/bytes-of) parts))
(defn- pack [fmt & vs] (apply struct/pack fmt vs))
(defn- up [fmt blob off] (vec (struct/unpack_from fmt blob off)))
(defn- any-set? [b] (boolean (python/any b)))

(defn verify
  "Independent image/entry/context ABI checks, including all zero slots."
  ([blob fuel] (verify blob fuel false))
  ([blob fuel project]
   (let [h (vec (struct/unpack_from "<16sHHIQQQIHHHHHH" blob))
         _ (u/chk (= [(cat-bytes (u/bytes-of 0x7f 0x45 0x4c 0x46 2 1 1) (u/bytes-of-n 9 0)) 2 62 1] (subvec h 0 4)))
         _ (u/chk (= [0x101000 64] (subvec h 4 6)))
         shoff (nth h 6)
         _ (u/chk (= [0 64 56 2 64 4 3] (subvec h 7)))
         rx (up "<IIQQQQQQ" blob 64)
         rw (up "<IIQQQQQQ" blob (+ 64 56))
         _ (u/chk (= [1 5 4096 0x101000 0x101000] (subvec rx 0 5)))
         _ (u/chk (and (< 77 (nth rx 5)) (= (nth rx 5) (nth rx 6)) (<= (nth rx 6) 1048576) (= 4096 (nth rx 7))))
         data (nth rw 2) context (nth rw 3)
         _ (u/chk (= [1 6 data context context data-size data-size 4096] rw))
         _ (u/chk (and (zero? (mod data 4096)) (>= data 32768) (= context (+ 0x100000 data))))
         _ (u/chk (and (<= (+ 4096 (nth rx 5)) data) (< (+ data data-size) (python/len blob))))
         sh (vec (for [i (range 4)] (up "<IIQQQQIIQQ" blob (+ shoff (* i 64)))))
         _ (u/chk (= (vec (repeat 10 0)) (nth sh 0)))
         _ (u/chk (= [1 1 6 0x101000 4096 (nth rx 5) 0 0 16 0] (nth sh 1)))
         _ (u/chk (= [7 1 3 context data data-size 0 0 4096 0] (nth sh 2)))
         names (+ data data-size)
         _ (u/chk (= [13 3 0 0 names 23 0 0 1 0] (nth sh 3)))
         _ (u/chk (= (.encode "\u0000.text\u0000.data\u0000.shstrtab\u0000" "latin-1") (u/bslice blob names (+ names 23))))
         _ (u/chk (and (= shoff (bit-and (+ names 30) -8)) (= (python/len blob) (+ shoff 256))))
         _ (u/chk (and (not (any-set? (u/bslice blob 176 4096))) (not (any-set? (u/bslice blob (+ 4096 (nth rx 5)) data)))))
         _ (u/chk (not (any-set? (u/bslice blob (+ names 23) shoff))))
         ;; The 77-byte entry shim from the owner ABI: CLI, private stack, GDT, far-return/reload segments, LTR,
         ;; saved boot-info, r9 context, call/park.
         stack (+ context data-size) tss (+ context 168)
         boot (cat-bytes (u/bytes-of 0xfa 0x48 0x8d 0x25) (pack "<i" (- stack 0x101008))
                         (u/bytes-of 0x48 0x83 0xe4 0xf0 0x0f 0x01 0x15) (pack "<i" (- (+ context 152) 0x101013))
                         (u/hex->bytes "6a08488d05030000005048cb66b810008ed88ec08ed031c08ee08ee866b828000f00d8")
                         (u/bytes-of 0x48 0x89 0x3d) (pack "<i" (- (+ context 80) 0x10103d))
                         (u/bytes-of 0x4c 0x8d 0x0d) (pack "<i" (- context 0x101044)))
         _ (u/chk (and (= 68 (python/len boot)) (= boot (u/bslice blob 4096 4164))))
         _ (u/chk (and (= 0xe8 (u/geti blob 4164)) (= (u/hex->bytes "faf4ebfd") (u/bslice blob 4169 4173))))
         entry (+ 73 (u/geti (struct/unpack_from "<i" blob 4165) 0))
         _ (u/chk (and (<= 77 entry) (< entry (nth rx 5))))]
     (if project
       ;; Locked projects check the prospective frame against the private stack floor before PUSH RBP. This is a
       ;; different entry ABI from the scalar/object image; do not relax that image's byte check.
       (let [body (u/bslice blob (+ 4096 entry) (+ 4096 (nth rx 5)))]
         (u/chk (= (u/hex->bytes "4989e24981ea") (u/bslice body 0 6)))
         (let [frame (u/geti (struct/unpack_from "<I" body 6) 0)]
           (u/chk (and (<= 8 frame 65536) (= 8 (mod frame 16))))
           (u/chk (= (u/hex->bytes "0f82150000004d8b99580100004d39da0f8205000000e904000000faf4ebfd554889e5") (u/bslice body 10 45)))))
       (u/chk (= (u/hex->bytes "554889e5") (u/bslice blob (+ 4096 entry) (+ 4100 entry)))))
     (let [expected (python/bytearray data-size)
           gdt [0 0x00af9a000000ffff 0x00cf92000000ffff 0x00cff2000000ffff 0x00affa000000ffff]]
       (struct/pack_into "<Q" expected 8 fuel)
       (apply struct/pack_into "<5Q" expected 96 gdt)
       (operator/setitem expected (python/slice 136 152)
                         (cat-bytes (pack "<H" 103) (u/bslice (.to_bytes tss 8 "little") 0 3) (u/bytes-of 0x89 0)
                                    (u/bslice (.to_bytes tss 8 "little") 3 nil) (u/bytes-of-n 4 0)))
       (struct/pack_into "<HQ" expected 152 55 (+ context 96))
       (struct/pack_into "<Q" expected 172 stack)
       (struct/pack_into "<H" expected 270 104)
       (when project (struct/pack_into "<Q" expected 344 (+ context 20480)))
       (u/chk (= (u/bslice blob data (+ data data-size)) expected))
       (u/pydict "entry" 0x101000 "textBytes" (nth rx 5) "context" context "stackTop" stack
                 "fuel" fuel "imports" (python/list) "interpreter" nil)))))

(defn- object-gate [sym]
  (g/load-source-var "check-x86_64-aiueos-object-cfree.cljc" sym))

(defn main [build output complete]
  (let [[source-graph producers baseline] (proof/load-native-producers :build build :complete complete)
        _ (.mkdir output ** :parents true :exist_ok false)
        cases (object-gate 'check-x86-64-aiueos-object-cfree/cases)
        shape-refusals (object-gate 'check-x86-64-aiueos-object-cfree/shape-refusals)
        verify-abi (object-gate 'check-x86-64-aiueos-object-cfree/verify-abi)
        results (python/list) parity (python/list)]
    (doseq [producer producers]
      (let [scope (.joinpath output (.-stem producer))
            _ (.mkdir scope)
            env (let [e (python/dict os/environ)]
                  (operator/setitem e "KEXE_CAP_RESOURCES_35" (str scope))
                  (operator/setitem e "KEXE_STACK_BYTES" "8388608")
                  e)
            commands (python/list) artifacts (python/dict) refusals (python/list)
            compile- (fn [name source & {:keys [kind fuel extra sentinel] :or {kind "image" fuel "1024" extra []}}]
                       (let [src (.joinpath scope (str name ".kotoba")) dst (.joinpath scope (str name ".elf"))]
                         (.write_text src source)
                         (when sentinel (.write_bytes dst sentinel))
                         (let [r (u/run-process (concat [producer "compile" src "--target" target "--artifact" kind "--output" dst "--fuel" fuel] extra) env 120)]
                           (.append commands (u/pydict "name" name "exit" (.-returncode r) "stdout" (.decode (.-stdout r)) "stderr" (.decode (.-stderr r))))
                           [dst r])))
            source "(ns probe (:export [main]))\n(defn main [] :i64 42)\n"
            loop-src (str "(ns loop-image (:export [main]))\n"
                          "(defn- sum [n :i64 acc :i64] :i64 (if (= n 0) acc (sum (dec n) (+ acc n))))\n"
                          "(defn main [] :i64 (sum 100 0))\n")]
        (doseq [[name text fuel] [["value" source 1024] ["calls" loop-src 1024] ["fuel64" source 3000000000]]]
          (let [[dst r] (compile- name text :fuel (str fuel))]
            (u/chk (and (zero? (.-returncode r)) (not (u/nonempty? (.-stderr r)))) [name (.-returncode r) (.-stderr r)])
            (verify (.read_bytes dst) fuel)
            (operator/setitem artifacts name (u/pin dst))
            ;; Structural validator must actually reject corrupted output.
            (doseq [offset [4 24 68 120 4096 4111 4164 (+ 32768 8) (+ 32768 96) (+ 32768 152) (+ 32768 172) (+ 32768 270)]]
              (let [bad (python/bytearray (.read_bytes dst))
                    _ (operator/setitem bad offset (bit-xor (operator/getitem bad offset) 0x80))
                    admitted (try (verify bad fuel) true
                                  (catch python/AssertionError _ false)
                                  (catch struct/error _ false)
                                  (catch python/OverflowError _ false))]
                (when admitted (throw (python/AssertionError (str ["validator admitted corruption" name offset]))))))))
        (let [bad-sources (python/dict shape-refusals)]
          (operator/setitem bad-sources "nonzero-entry-arity" "(ns arg (:export [entry]))\n(defn entry [x :i64] :i64 x)\n")
          (doseq [[name text] (.items bad-sources)]
            (let [[dst r] (compile- (str "refuse-" name) text)]
              (u/chk (and (not (zero? (.-returncode r))) (not (.exists dst))) [name (.-stdout r) (.-stderr r)])
              (.append refusals name))))
        (doseq [[name kind fuel extra] [["unknown-artifact" "disk" "1024" []] ["zero-fuel" "image" "0" []] ["bad-fuel" "image" "10x" []]
                                        ["module-lock" "image" "1024" ["--module-lock" "no.edn"]]
                                        ["source-path" "image" "1024" ["--source-path" "unknown"]]
                                        ["format" "image" "1024" ["--format" "static"]]
                                        ["duplicate-artifact" "image" "1024" ["--artifact" "object"]]]]
          (let [[dst r] (compile- (str "refuse-" name) source :kind kind :fuel fuel :extra extra)]
            (u/chk (and (not (zero? (.-returncode r))) (not (.exists dst))) [name (.-stdout r) (.-stderr r)])
            (.append refusals name)))
        (let [[dst r] (compile- "existing" source :sentinel (.encode "preserve original"))]
          (u/chk (and (not (zero? (.-returncode r))) (= (.encode "preserve original") (.read_bytes dst))))
          (.append refusals "existing-output"))
        ;; All object fixtures retain the original ABI with explicit object selection.
        (doseq [[name [text symbol]] (.items cases)]
          (let [[dst r] (compile- (str "object-" name) text :kind "object")]
            (u/chk (and (zero? (.-returncode r)) (not (u/nonempty? (.-stderr r)))) [name (.-stderr r)])
            (verify-abi (.read_bytes dst) symbol)
            (let [original (.joinpath scope (str "baseline-object-" name ".o"))
                  r2 (u/run-process [baseline "compile" (.joinpath scope (str "object-" name ".kotoba")) "--target" target
                                     "--output" original "--fuel" "1024"] env 120)]
              (u/chk (and (zero? (.-returncode r2)) (not (u/nonempty? (.-stderr r2)))) ["native baseline" name (.-stderr r2)])
              (u/chk (= (.read_bytes original) (.read_bytes dst)) ["object bytes changed" name]))))
        (.write_text (.joinpath scope "commands.json") (u/json-dump commands))
        (.append results (u/pydict "producer" (u/pin producer) "artifacts" artifacts "refusals" refusals
                                   "objectRegressionCases" (python/len cases) "nativeBaselineByteParity" true))
        (.append parity artifacts)))
    (u/chk (u/deq (u/geti parity 0) (u/geti parity 1)) "fixed-point generations disagree on image bytes")
    (let [report (u/pydict "status" "PASS_NATIVE_AIUEOS_IMAGE_PACKAGING" "host" (python/list [(platform/system) (platform/machine)])
                           "source" source-graph "baseline" (u/pin baseline) "routes" results
                           "cCompilerOrLoader" false "JVMNodeOrGraalFallback" false "emulation" false
                           "legacyOwnerOracle" "unavailable in permitted native closure; ABI inspected independently"
                           "wholeKernel" false "efi" false "gpt" false "qemuBoot" false "nativeCDCI" false)]
      (.write_text (.joinpath output "native-image.json") (u/json-dump report))
      (println (u/geti report "status") (reduce + (map #(python/len (u/geti % "artifacts")) results)) "images; complete kernel/EFI/boot open"))))

(defn -main [& args]
  (let [[build out complete] (u/parse-build-complete-output args)]
    (main build out complete)))

(when (some #(or (= % "check-aiueos-image-native.cljc") (str/ends-with? % "/check-aiueos-image-native.cljc")) sys/argv)
  (apply -main *command-line-args*))
