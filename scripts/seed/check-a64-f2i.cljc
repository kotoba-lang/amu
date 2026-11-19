;; f32 -> i64 (JUN-633, ADR 0398) and f64 -> i64 (JUN-846) truncation on the aarch64 route (seed/41).
;;
;; seed/41's gn-fl-un emits `f32-to-i64-truncating` (SIR UOP 37) with ADR 0395's semantics, as the x86 object route
;; does: truncation toward zero; a NaN, +-Inf or any operand outside [-2^63, 2^63) reaches brk #0 instead of fcvtzs's
;; saturated answer. Compiles with a native Amu compiler for --target aarch64-macos, packages with the pinned Mac
;; packager and runs natively (this script stages and observes; it emits nothing):
;;
;; * guard: the payload exporting the conversion carries, exactly once,
;;     fmov s0,wX ; movz xD,#0xdf00,lsl #16 ; fmov s1,wD ; fcmp s0,s1 ; b.lt +4 ; fneg s1,s1 ; fcmp s1,s0 ; b.gt +2 ;
;;     brk #0 ; fcvtzs xD,s0
;;   with one D, and no single-precision fcvtzs anywhere else; a function with two conversions carries two guards;
;; * f64 -> i64 (UOP 32, JUN-846) is the same guard at double precision, once per use (the reference traps NaN, +-Inf
;;   and every |x| >= 2^63; fcvtzs would saturate):
;;     fmov d0,xX ; movz xD,#0xc3e0,lsl #48 ; fmov d1,xD ; fcmp d0,d1 ; b.lt +4 ; fneg d1,d1 ; fcmp d1,d0 ; b.gt +2 ;
;;     brk #0 ; fcvtzs xD,d0
;; * opt-in: payloads that do not name the conversion keep the SHA-256 they have under the main 26833b16 root;
;; * execution, packaged and signed on this Mac: in-range operands return the truncated integer (including -2^63 ->
;;   INT64_MIN, 2^63 - 2^39, +-0, denormals, +-0.99999994, +-2.5); NaNs (quiet, signalling, negative), +-Inf, 2^63,
;;   the f32 neighbour below -2^63 and the finite extremes each die by SIGTRAP with no output.
;;
;; Against the main root (saturating fcvtzs) the gate is red: no guard, and the trap programs exit with an answer.
;; docs/evidence/f32-to-i64-a64-20261031/ runs every 2^32 pattern natively on macOS and Linux arm64 against the x86
;; run's integer C reference. Ported from check-a64-f2i.py (Basilisp, JUN-974). Apple Silicon macOS only.
;; Run: basilisp run -p scripts/seed scripts/seed/check-a64-f2i.cljc -- --compiler C --output DIR [--measure-unchanged]
(ns check-a64-f2i
  (:require [basilisp.string :as str]
            [gate-util :as u]
            [macos-native-lib :as mac])
  (:import json operator pathlib re struct sys))

(def packager (.joinpath u/root "seed/bootstrap/aarch64-macos/kotoba-packager-root.macho"))
(def float-cases (.joinpath u/root "seed/float-cases.json"))
(def source
  (str "(ns f2i (:export [kotoba_aiueos_f32_to_i64]))\n"
       "(defn kotoba_aiueos_f32_to_i64 [bits :i64] :i64 (f32-to-i64-truncating (f32-from-bits bits)))\n"))
(def twice
  (str "(ns f2i2 (:export [f]))\n"
       "(defn f [a :i64 b :i64] :i64 (+ (f32-to-i64-truncating (f32-from-bits a)) (f32-to-i64-truncating (f32-from-bits b))))\n"))
(def f64-source
  (str "(ns d2i (:export [f]))\n"
       "(defn f [bits :i64] :i64 (f64-to-i64-truncating (f64-from-bits bits)))\n"))
(def sigtrap -5)
(def int64-min (- (bit-shift-left 1 63)))
;; float-cases.json entries that do not use f32-to-i64-truncating: their aarch64-macos payloads (extract-native main)
;; use the main 26833b16 pins except the three decimal-literal cases, whose source now lowers literals directly to f64
;; bits. Their native results are checked separately in this integration.
;; JUN-846: the cases that name f64-to-i64-truncating (basic, literal, div-trunc, neg-abs-sqrt, min-max, f32-conv) now
;; carry the double guard and moved; float-f64-cmp, float-f64-unordered and float-f32-cmp name no conversion and are
;; unchanged.
(def unchanged
  [["float-f64-basic" "a2c90acedf196f84213e55d3209be6cdcb62bb65a31a3b0c595e1c024d52eff5"]
   ["float-f64-literal" "efba8429890323d8aec4a405b6bc8f65f0c0ca773135c6341904e9021bb1a0ee"]
   ["float-f64-div-trunc" "abb54f6f44af7f68ed3d21f7727b12e9fc1555606ca63ba9c2d5736efa7038fc"]
   ["float-f64-neg-abs-sqrt" "3230bc36caee3e893faadb51b5f2274de38df1b279dcd428f982f428c806ddde"]
   ["float-f64-cmp" "9f1bc1bec464d34e3e307f7d425f91138fd539a099c07fe98072a6dd6eb6816c"]
   ["float-f64-min-max" "73a3bef116536c368de53a4675668befa5907e1a4f7bfb11a3563d1bf71847cf"]
   ["float-f32-conv" "0509db2448d7b2b695558b85d85ec521de1615c12fb3d70ebb362b774e5fac82"]
   ["float-f64-unordered" "96d77de223bed4e18a5768a5abdb55cc7e2df6c02944ebb082ad2b99b187cc54"]
   ["float-f32-cmp" "2629d0afcd6fb9520f037a8c40678e735bf00a6eb44912e86163d20422eb3264"]])
(def d64 "7d9f1baa1962dd3c4c3f03d0c090bd4707ed9605d6684991875b26d8327c1619")   ; the F64 payload under the same root
(def in-range [0x00000000 0x80000000 0x00000001 0x807fffff 0x3f7fffff 0xbf7fffff 0x3f800000 0xbfc00000
               0x40200000 0xc0200000 0x4b000001 0xcaffffff 0x4f000000 0xcf800001 0x5e800000 0x5effffff
               0xdeffffff 0xdf000000])
(def traps [0x7f800000 0xff800000 0x7fc00000 0xffc00000 0x7f800001 0xffa5a5a5 0x7fffffff 0x5f000000
            0x5f000001 0xdf000001 0xdf800000 0x7f7fffff 0xff7fffff])
;; f64 patterns: zeros, denormals, +-0.99999999999999989, +-1, +-2.5, 2^53+1 region, 2^63 - 1024 (the largest double
;; below 2^63), -2^63 (exact), the first double above -2^63
(def in-range64 [0x0000000000000000 0x8000000000000000 0x0000000000000001 0x800fffffffffffff 0x3fefffffffffffff
                 0xbfefffffffffffff 0x3ff0000000000000 0xbff0000000000000 0x4004000000000000 0xc004000000000000
                 0x4340000000000001 0xc340000000000001 0x43dfffffffffffff 0xc3e0000000000000 0xc3dfffffffffffff])
;; NaNs (quiet, signalling, negative, payload), +-Inf, 2^63, the double below -2^63, the finite extremes
(def traps64 [0x7ff0000000000000 0xfff0000000000000 0x7ff8000000000000 0xfff8000000000000 0x7ff0000000000001
              0xfff4a5a5a5a5a5a5 0x7fffffffffffffff 0x43e0000000000000 0xc3e0000000000001 0x7fefffffffffffff
              0xffefffffffffffff 0x43f0000000000000])

(defn ref32
  "ADR 0395 from the bit pattern alone (docs/evidence/f32-to-i64-20261031/ref.c): an integer, or nil (trap)."
  [bits]
  (let [s (bit-shift-right bits 31) e (bit-and (bit-shift-right bits 23) 0xFF) m (bit-and bits 0x7FFFFF)]
    (cond (= e 0xFF) nil
          (< e 127) 0
          :else (let [sh (- e 127)]
                  (if (>= sh 63)
                    (if (and (pos? s) (= sh 63) (zero? m)) int64-min nil)
                    (let [sig (bit-or m 0x800000)
                          mag (if (>= sh 23) (bit-shift-left sig (- sh 23)) (bit-shift-right sig (- 23 sh)))]
                      (if (pos? s) (- mag) mag)))))))

(defn ref64
  "The reference f64 -> i64 truncation from the bit pattern alone: an integer, or nil (trap)."
  [bits]
  (let [s (bit-shift-right bits 63) e (bit-and (bit-shift-right bits 52) 0x7FF) m (bit-and bits 0xFFFFFFFFFFFFF)]
    (cond (= e 0x7FF) nil
          (< e 1023) 0
          :else (let [sh (- e 1023)]
                  (if (>= sh 63)
                    (if (and (pos? s) (= sh 63) (zero? m)) int64-min nil)
                    (let [sig (bit-or m (bit-shift-left 1 52))
                          mag (if (>= sh 52) (bit-shift-left sig (- sh 52)) (bit-shift-right sig (- 52 sh)))]
                      (if (pos? s) (- mag) mag)))))))

(defn signed32 [bits] (if (pos? (bit-and bits 0x80000000)) (- bits (bit-shift-left 1 32)) bits))
(defn signed64 [bits] (if (pos? (bit-shift-right bits 63)) (- bits (bit-shift-left 1 64)) bits))

(defn words [raw]
  (let [n (quot (python/len raw) 4)]
    (vec (struct/unpack (str "<" n "I") (u/bslice raw 0 (* n 4))))))

(defn find-guards
  "Start indices of a guarded sequence of the given shape; the register fields must agree."
  [ws {:keys [w0 movz fmov1 tail fcvt]}]
  (vec (for [i (range (- (count ws) 9))
             :let [w (subvec ws i (+ i 10))
                   d (bit-and (nth w 1) 31)]
             :when (and (= (bit-and (nth w 0) 0xFFFFFC1F) w0)
                        (= (nth w 1) (bit-or movz d))
                        (= (nth w 2) (bit-or fmov1 (bit-shift-left d 5)))
                        (= (subvec w 3 9) tail)
                        (= (nth w 9) (bit-or fcvt d)))]
         i)))

(def shape32 {:w0 0x1E270000 :movz 0xD2BBE000 :fmov1 0x1E270001
              :tail [(bit-or 0x1E202000 (bit-shift-left 1 16)) 0x5400008B 0x1E214021 0x1E202020 0x5400004C 0xD4200000]
              :fcvt 0x9E380000})
(def shape64 {:w0 0x9E670000 :movz 0xD2F87C00 :fmov1 0x9E670001
              :tail [(bit-or 0x1E602000 (bit-shift-left 1 16)) 0x5400008B 0x1E614021 0x1E602020 0x5400004C 0xD4200000]
              :fcvt 0x9E780000})
(defn guards [ws] (find-guards ws shape32))
(defn guards64 [ws] (find-guards ws shape64))

(defn fcvtzs [ws single]
  (let [base (if single 0x9E380000 0x9E780000)]
    (vec (for [[i w] (map-indexed vector ws) :when (= (bit-and w 0xFFFFFC00) base)] i))))

(defn compile-raw [compiler out name src symbol]
  (.write_text (.joinpath out (str name ".kotoba")) src)
  (mac/native-run compiler out ["compile" (str name ".kotoba") "--target" "aarch64-macos" "--output" (str name ".kseed")])
  (let [extracted (mac/native-run compiler out ["extract-native" (str name ".kseed") "--symbol" symbol "--output" (str name ".raw")])
        m (re/search (.encode ":offset (\\d+), :length (\\d+), :arity \\d+}") (.-stdout extracted))
        raw (.read_bytes (.joinpath out (str name ".raw")))]
    (when (or (nil? m) (not= (python/int (.group m 2)) (python/len raw)))
      (mac/fail (str "native extraction did not match raw bytes: " name)))
    [raw (python/int (.group m 1))]))

(defn program [compiler out name src]
  (let [[_ entry] (compile-raw compiler out name src "main")]
    (mac/native-run packager out [(str name "-unsigned.macho") (str name ".raw") "fs2-cli-stdio-general" (str entry)])
    (mac/sign (.joinpath out (str name "-unsigned.macho")) (.joinpath out (str name ".macho")))
    (mac/process [(.joinpath out (str name ".macho"))] :cwd out :timeout 120)))

(defn hex-of [b width] (python/format b (str "0" width "x")))

(defn main [compiler output measure]
  (mac/verify-macho compiler)
  (mac/verify-macho packager)
  (.mkdir output ** :parents false :mode 0700 :exist_ok false)
  (let [report (u/pydict)
        cases (u/pydict-from (for [c (u/geti (u/read-json float-cases) "cases")] [(u/geti c "name") (u/geti c "source")]))
        digests (u/pydict)]
    (doseq [[name _] unchanged]
      (let [[raw _] (compile-raw compiler output name (u/geti cases name) "main")]
        (.__setitem__ digests name (u/sha256-hex raw))))
    (let [[raw _] (compile-raw compiler output "d2i" f64-source "f")]
      (.__setitem__ digests "d2i" (u/sha256-hex raw))
      (if measure
        (do (println (json/dumps digests ** :indent 2)) (.flush sys/stdout))
        (let [ws (words raw)
              at64 (guards64 ws)]
          (when (or (seq (guards ws)) (not= 1 (count at64)) (not= (sort (fcvtzs ws false)) (mapv #(+ % 9) at64)) (seq (fcvtzs ws true)))
            (mac/fail (str "f64 -> i64 is not exactly one guarded double fcvtzs: guards " at64)))
          (let [want (u/pydict-from (concat unchanged [["d2i" d64]]))]
            (when-not (u/deq digests want) (mac/fail (str "payloads without the conversion changed: " (python/dict digests)))))
          (.__setitem__ report "unchanged" digests)
          (.__setitem__ report "f64Guard" (python/list (map #(* 4 %) at64)))
          ;; The independent aarch64-linux emitter (seed/80 xa-un) carries the same guard, once per use. Compile only:
          ;; this gate runs on macOS, which cannot execute the ELF (docs/evidence/f64-to-i64-a64-linux-20261105 runs it
          ;; on arm64 Linux).
          (doseq [[name n] [["linux64" 1] ["linux64x2" 2]]]
            (let [body (if (= n 1)
                         "(f64-to-i64-truncating (f64-from-bits 4614256656552045848))"
                         "(+ (f64-to-i64-truncating (f64-from-bits 4614256656552045848)) (f64-to-i64-truncating (f64-from-bits 4611686018427387904)))")]
              (.write_text (.joinpath output (str name ".kotoba")) (str "(ns " name " (:export [main]))\n(defn main [] :i64 " body ")\n"))
              (mac/native-run compiler output ["compile" (str name ".kotoba") "--target" "aarch64-linux" "--output" (str name ".elf") "--format" "static"])
              (let [lws (words (.read_bytes (.joinpath output (str name ".elf"))))
                    lat (guards64 lws)]
                (when (or (not= (count lat) n) (seq (guards lws)))
                  (mac/fail (str name ": aarch64-linux f64 -> i64 guards " lat ", expected " n " double guards")))
                (.__setitem__ report name (u/pydict "guards" (count lat))))))
          ;; These literals intentionally lower to different bytes in the decimal frontend. Execute each result as well
          ;; as pinning its emitted payload.
          (let [literal-results (u/pydict)]
            (doseq [name ["float-f64-literal" "float-f32-conv" "float-f64-unordered"]]
              (let [expected (u/geti (first (filter #(= name (u/geti % "name")) (u/geti (u/read-json float-cases) "cases"))) "result")
                    result (program compiler output (str "execute-" name) (u/geti cases name))]
                (when (or (not= expected (.-returncode result)) (u/nonempty? (.-stdout result)) (u/nonempty? (.-stderr result)))
                  (mac/fail (str name ": exit " (.-returncode result) ", expected " expected "; " (.-stderr result))))
                (.__setitem__ literal-results name (.-returncode result))))
            (.__setitem__ report "decimalLiteralResults" literal-results))
          (doseq [[name src symbol n] [["f2i" source "kotoba_aiueos_f32_to_i64" 1] ["f2i2" twice "f" 2]]]
            (let [[raw _] (compile-raw compiler output name src symbol)
                  ws (words raw)
                  at (guards ws)]
              (when (or (not= (count at) n) (not= (sort (fcvtzs ws true)) (mapv #(+ % 9) at)) (seq (fcvtzs ws false)))
                (mac/fail (str name ": guard at " at ", f32 fcvtzs at " (fcvtzs ws true) ", expected " n " guards")))
              (.__setitem__ report name (u/pydict "guards" (python/list (map #(* 4 %) at)) "sha256" (u/sha256-hex raw)))))
          (let [checks (apply str (for [[k b] (map-indexed vector in-range)]
                                    (str "\n        (not= (f32-to-i64-truncating (f32-from-bits " (signed32 b) ")) " (ref32 b) ") " (inc k))))
                result (program compiler output "inrange"
                                (str "(ns inrange (:export [main]))\n(defn main [] :i64\n  (cond" checks "\n        :else 0))\n"))]
            (when (or (not (zero? (.-returncode result))) (u/nonempty? (.-stdout result)) (u/nonempty? (.-stderr result)))
              (mac/fail (str "in-range answers wrong: exit " (.-returncode result) " (case number), " (.-stderr result)))))
          (.__setitem__ report "inRange" (count in-range))
          (doseq [b traps]
            (u/chk (nil? (ref32 b)))
            (let [name (str "trap-" (hex-of b 8))
                  result (program compiler output name
                                  (str "(ns t (:export [main]))\n(defn main [] :i64 "
                                       "(bit-and (f32-to-i64-truncating (f32-from-bits " (signed32 b) ")) 255))\n"))]
              (when (or (not= sigtrap (.-returncode result)) (u/nonempty? (.-stdout result)) (u/nonempty? (.-stderr result)))
                (mac/fail (str name ": exit " (.-returncode result) ", expected SIGTRAP; " (.-stderr result))))))
          (.__setitem__ report "traps" (python/list (map #(hex-of % 8) traps)))
          (let [checks64 (apply str (for [[k b] (map-indexed vector in-range64)]
                                      (str "\n        (not= (f64-to-i64-truncating (f64-from-bits " (signed64 b) ")) " (ref64 b) ") " (inc k))))
                result (program compiler output "inrange64"
                                (str "(ns inrange64 (:export [main]))\n(defn main [] :i64\n  (cond" checks64 "\n        :else 0))\n"))]
            (when (or (not (zero? (.-returncode result))) (u/nonempty? (.-stdout result)) (u/nonempty? (.-stderr result)))
              (mac/fail (str "f64 in-range answers wrong: exit " (.-returncode result) " (case number), " (.-stderr result)))))
          (.__setitem__ report "inRange64" (count in-range64))
          (doseq [b traps64]
            (u/chk (nil? (ref64 b)))
            (let [name (str "trap64-" (hex-of b 16))
                  result (program compiler output name
                                  (str "(ns t (:export [main]))\n(defn main [] :i64 "
                                       "(bit-and (f64-to-i64-truncating (f64-from-bits " (signed64 b) ")) 255))\n"))]
              (when (or (not= sigtrap (.-returncode result)) (u/nonempty? (.-stdout result)) (u/nonempty? (.-stderr result)))
                (mac/fail (str name ": exit " (.-returncode result) ", expected SIGTRAP; " (.-stderr result))))))
          (.__setitem__ report "traps64" (python/list (map #(hex-of % 16) traps64)))
          (.write_text (.joinpath output "report.json") (u/json-dump report))
          (println (str "PASS_A64_F2I " (json/dumps report ** :sort_keys true)))
          (.flush sys/stdout))))))

(defn -main [& args]
  (main (.resolve (pathlib/Path (or (u/opt args "--compiler") (sys/exit "--compiler is required"))) ** :strict true)
        (.resolve (pathlib/Path (or (u/opt args "--output") (sys/exit "--output is required"))))
        (boolean (some #{"--measure-unchanged"} args))))

(when (some #(or (= % "check-a64-f2i.cljc") (str/ends-with? % "/check-a64-f2i.cljc")) sys/argv)
  (apply -main *command-line-args*))
