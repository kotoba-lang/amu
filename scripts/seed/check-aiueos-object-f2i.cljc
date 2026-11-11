;; f32 -> i64 truncation on the aiueos kernel object route (JUN-633 slice 7, ADR 0395).
;;
;; seed/70's xg-fun emits `f32-to-i64-truncating` (SIR UOP 37) and seed/74's xo-check-sir admits it on the object
;; artifact only. The semantics: truncation toward zero; a NaN or an operand outside [-2^63, 2^63) reaches ud2, so the
;; route never answers cvttss2si's integer indefinite except for -2^63 itself. Compiles with a native Amu compiler and
;; checks (this script stages and observes; it emits nothing):
;;
;; * guard: the object exporting the conversion carries, exactly once, cvttss2si rax,[rbp+d]; mov rcx,rax; neg rcx;
;;   jno +14; cmp dword [rbp+d],0xdf000000 (the same slot); je +2; ud2 -- and no cvtss2si (rounding) or cvttsd2si;
;; * opt-in: objects that do not name the conversion keep their bytes -- slice 3's fops object, the pause object and
;;   the 512-byte width object keep the SHA-256 they have on main 3d160442;
;; * refused, nothing written, on the object route: one or two operands short or over (E2103), a non-f32 operand
;;   (E2104), and f64 -> i64 truncation (E7101, still not emitted);
;; * refused on every other x86 route: the kernel image artifact answers E7101 detail 37 for the same conversion, so
;;   only the object artifact (and the scalar Linux route, which carries the same guard) admits it.
;;
;; Not shown here: execution. docs/evidence/f32-to-i64-20261031/ runs the object under QEMU against a C reference.
;; Ported from check-aiueos-object-f2i.py (Basilisp, JUN-974).
;; Run: basilisp run -p scripts/seed scripts/seed/check-aiueos-object-f2i.cljc -- --compiler C --output DIR
(ns check-aiueos-object-f2i
  (:require [basilisp.string :as str]
            [aiueos-object-lib :as lib]
            [gate-util :as u]
            [macos-native-lib :as mac])
  (:import operator re sys))

(def fops (.joinpath u/root "docs/evidence/f32-sse-20261030/fops.kotoba"))
;; the objects' SHA-256 under amu main 3d160442 (slice 6), before the conversion existed
(def fops-sha256 "d079b9d45c526f4e36831610a02ead9f19c0e85c30b4f0ec7468911554e4fe56")
(def pause-sha256 "c24f9c962e000ead3c1672975f74f941960c169d9c22bfe824a89a3c7a909403")
(def source
  (str "(ns f2i (:export [kotoba_aiueos_f32_to_i64]))\n"
       "(defn kotoba_aiueos_f32_to_i64 [bits :i64] :i64 (f32-to-i64-truncating (f32-from-bits bits)))\n"))
(defn cat [& parts] (reduce operator/add parts))
(def guard
  (re/compile (cat (u/hex->bytes "f3480f2c85") (.encode "(....)")
                   (u/hex->bytes "4889c148f7d9710e81bd") (.encode "(....)")
                   (u/hex->bytes "000000df74020f0b"))
              re/DOTALL))
(def absent [["cvtss2si" "f3480f2d"] ["cvttsd2si" "f2480f2c"]])
(def object-refusals
  [["two-operands" (str "(ns r (:export [f]))\n(defn f [x :i64] :i64 "
                        "(f32-to-i64-truncating (f32-from-bits x) (f32-from-bits x)))\n") "E2103"]
   ["no-operand" "(ns r (:export [f]))\n(defn f [x :i64] :i64 (f32-to-i64-truncating))\n" "E2103"]
   ["i64-operand" "(ns r (:export [f]))\n(defn f [x :i64] :i64 (f32-to-i64-truncating x))\n" "E2104"]
   ["f64-to-i64" "(ns r (:export [f]))\n(defn f [x :i64] :i64 (f64-to-i64-truncating (f64-from-bits x)))\n" "E7101"]])
;; the conversion is the first float SIR in each source, so detail 37 names it
(def route-refusals
  [["kernel-image" (str "(ns g (:export [kotoba_aiueos_f]))\n"
                        "(defn kotoba_aiueos_f [x :i64] :i64 (f32-to-i64-truncating (__r6-as :f32 x)))\n")
    ["--target" "x86_64-aiueos-kernel-v1" "--artifact" "image"]]])

(defn main [compiler output]
  (lib/start! compiler output)
  (let [report (u/pydict)
        [_ obj] (lib/compile-source compiler output "f2i" source)
        text (lib/text-section obj)
        hits (vec (re/findall guard text))
        _ (when (or (not= 1 (count hits)) (not (u/deq (operator/getitem (first hits) 0) (operator/getitem (first hits) 1))))
            (mac/fail (str "guarded cvttss2si sequence found " (count hits) " times: " hits)))
        absent-counts (into {} (for [[name hex] absent] [name (.count text (u/hex->bytes hex))]))
        _ (when (or (some pos? (vals absent-counts)) (not= 1 (.count text (u/hex->bytes "f3480f2c"))))
            (mac/fail (str "unexpected conversions " absent-counts)))
        _ (.__setitem__ report "guard" (u/pydict "slot" (.from_bytes python/int (operator/getitem (first hits) 0) "little" ** :signed true)
                                                 "sha256" (lib/sha-of obj)))]
    (doseq [[name src want] [["fops" (.read_text fops) fops-sha256] ["pause" lib/pause-source pause-sha256]
                             ["widths" lib/widths-source lib/widths-sha256]]]
      (let [[_ o] (lib/compile-source compiler output name src)
            digest (lib/sha-of o)]
        (when (or (not= digest want) (.search guard (lib/text-section o)))
          (mac/fail (str "the " name " object changed: " digest)))
        (.__setitem__ report (str name "Unchanged") digest)))
    (doseq [[name src code] object-refusals]
      (lib/check-refusals! compiler output report [[name src]] code))
    ;; The scalar Linux route now admits f32 conversion. It must carry the same guarded conversion, while the object
    ;; and kernel contracts remain.
    (.write_text (.joinpath output "x86_64-linux.kotoba")
                 "(ns scalar (:export [main]))\n(defn main [] :i64 (f32-to-i64-truncating (__r6-as :f32 1065353216)))\n")
    (mac/native-run compiler output ["compile" "x86_64-linux.kotoba" "--target" "x86_64-linux" "--output" "x86_64-linux.elf"])
    (let [scalar-bytes (.read_bytes (.joinpath output "x86_64-linux.elf"))
          scalar-guards (vec (re/findall guard scalar-bytes))]
      (when (or (not (.startswith scalar-bytes (u/hex->bytes "7f454c4602010100")))
                (not= 1 (count scalar-guards))
                (not (u/deq (operator/getitem (first scalar-guards) 0) (operator/getitem (first scalar-guards) 1))))
        (mac/fail "Linux scalar f32 guard missing or malformed"))
      (.__setitem__ report "x86_64-linux" (u/pydict "admitted" true "sha256" (u/sha256-hex scalar-bytes))))
    (doseq [[name src target] route-refusals]
      (.write_text (.joinpath output (str name ".kotoba")) src)
      (let [dest (.joinpath output (str name ".out"))
            result (mac/native-run compiler output (concat ["compile" (str name ".kotoba")] target ["--output" (.-name dest) "--fuel" "1000000"]) :expected 1)
            message (lib/message-of result)]
        (when (or (not (.__contains__ message "E7101")) (not (.endswith (.rstrip message) "detail 37")) (.exists dest))
          (mac/fail (str name " did not refuse the conversion (E7101 detail 37): " message)))
        (.__setitem__ report name "refused E7101 detail 37")))
    (lib/emit! output report "PASS_AIUEOS_OBJECT_F2I")))

(defn -main [& args] (lib/cli-main args main))

(when (some #(or (= % "check-aiueos-object-f2i.cljc") (str/ends-with? % "/check-aiueos-object-f2i.cljc")) sys/argv)
  (apply -main *command-line-args*))
