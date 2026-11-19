;; The aiueos kernel object route emits one or several exports (JUN-556).
;;
;; Compiles sources with a native Amu compiler and reads the objects back with an independent ELF parser (this script
;; stages and observes; it emits nothing):
;;
;; * one export: the object is byte-identical to the one the single-export route has always produced (its SHA-256 is
;;   pinned below), so nothing that links it changes;
;; * two exports: an ET_REL object with the seven expected sections, one local .data `context` symbol, two public
;;   GLOBAL FUNC symbols, and one R_X86_64_PC32 addend -4 relocation per export at the context LEA of its shim
;;   (offset 3 into the shim), with the shims laid out back to back;
;; * nine exports: refused (E7102), nothing written;
;; * exports of six and eight parameters (R4B raised to 8, ADR 0384): a long shim that stores System V's sixth
;;   argument (r9) and its stack words where the internal convention expects them, then sets the context exactly as
;;   the short shim does. The bytes are compared with the expected encoding assembled here, the relocation sits at the
;;   LEA displacement, and a six-parameter export and a two-parameter export in one object are laid out back to back;
;; * a nine-parameter export (E2108) and a six-parameter private function (E7102): refused, nothing written.
;;
;; The aiueos verifier (kotoba.aiueos verify-kotoba-kernel-object.py) takes the export list; this gate does not
;; depend on it. Ported from check-aiueos-object-exports.py (Basilisp, JUN-974).
;; Run: basilisp run -p scripts/seed scripts/seed/check-aiueos-object-exports.cljc -- --compiler C --output DIR
(ns check-aiueos-object-exports
  (:require [basilisp.string :as str]
            [aiueos-object-lib :as lib]
            [gate-util :as u]
            [macos-native-lib :as mac])
  (:import operator struct sys))

(def one-sha256 lib/one-sha256)
(def one-source lib/one-source)
(def two-source (str "(ns two (:export [f g]))\n(defn f [x :i64] :i64 (+ x 1))\n"
                     "(defn g [x :i64 y :i64] :i64 (* x y))\n"))
(def nine-source (str "(ns nine (:export [" (str/join " " (for [i (range 9)] (str "f" i))) "]))\n"
                      (apply str (for [i (range 9)] (str "(defn f" i " [x :i64] :i64 (+ x " i "))\n")))))

(defn params-source
  ([name n] (params-source name n false))
  ([name n private]
   (let [ps (str/join " " (for [i (range n)] (str "a" i " :i64")))
         body (str "(+ " (str/join " " (for [i (range n)] (str "(* a" i " " (inc i) ")"))) ")")]
     (if private
       (str "(ns " name " (:export [f]))\n(defn- g [" ps "] :i64 " body ")\n"
            "(defn f [x :i64] :i64 (g " (str/join " " (repeat n "x")) "))\n")
       (str "(ns " name " (:export [f]))\n(defn f [" ps "] :i64 " body ")\n")))))

(def six-source (params-source "six" 6))
(def eight-source (params-source "eight" 8))
(def nine-params-source (params-source "ninep" 9))
(def private-six-source (params-source "privsix" 6 true))
(def mixed-source
  (str "(ns mixed (:export [f g]))\n" "(defn f [" (str/join " " (for [i (range 6)] (str "a" i " :i64")))
       "] :i64 (+ a0 a5))\n(defn g [x :i64 y :i64] :i64 (* x y))\n"))
(def shim 29)   ; the shim for a fuel that fits in 31 bits
(def fuel-int (python/int lib/fuel))

(defn fail [m] (throw (python/ValueError m)))
(defn bytes* [& xs] (python/bytes (python/list xs)))
(defn cat [& parts] (reduce operator/add parts))
(defn unpack [fmt b off] (vec (struct/unpack_from fmt b off)))

(defn check-two [obj]
  (let [syms (:symbols obj) relas (:relas obj)]
    (when (not= (mapv first syms) ["" "context" "f" "g"]) (fail (str "symbols " (mapv first syms))))
    (let [[_ context f g] syms]
      (when (or (not= [(nth context 1) (nth context 2)] [0x01 (:data-index obj)]) (not= (nth context 4) 80))
        (fail "context is not a local 80-byte .data object"))
      (when (not= (:sym-info obj) 2) (fail "sh_info must name the first global (index 2)"))
      (doseq [[sym start] [[f 0] [g shim]]]
        (when (or (not= (nth sym 1) 0x12) (not= (nth sym 2) (:text-index obj)) (not= (nth sym 3) start) (not= (nth sym 4) shim))
          (fail (str "export " (first sym) " is " (rest sym) ", want GLOBAL FUNC at " start " size " shim)))))
    (when (not= (count relas) 2) (fail (str (count relas) " relocations, want 2")))
    (doseq [[[offset info addend] start] (map vector relas [0 shim])]
      (when (or (not= offset (+ start 3)) (not= info (bit-or (bit-shift-left 1 32) 2)) (not= addend -4))
        (fail (str "relocation " [offset info addend] " at shim " start))))
    ;; each shim: lea r9,[rip+context]; mov qword [r9+8], fuel; sub rsp,8; call; add rsp,8; ret
    (doseq [start [0 shim]]
      (let [s (u/bslice (:text obj) start (+ start shim))]
        (when (or (not (u/deq (u/bslice s 0 3) (bytes* 0x4c 0x8d 0x0d))) (not (u/deq (u/bslice s 7 11) (bytes* 0x49 0xc7 0x41 0x08)))
                  (not= (operator/getitem s -1) 0xC3) (not= (operator/getitem s 19) 0xE8))
          (fail (str "shim at " start " is not the expected sequence: " (.hex s))))
        (when (not= (first (unpack "<i" s 11)) fuel-int)
          (fail (str "shim at " start " does not replenish fuel " lib/fuel)))))))

(defn long-shim
  "The expected long shim of an n-parameter export, assembled here from the encoding: [bytes lea-offset]."
  [n]
  (let [frame (bit-and (+ (* 8 (- n 5)) 15) -16)
        out (atom (bytes* 0x55 0x48 0x89 0xE5 0x48 0x83 0xEC frame))]            ; push rbp; mov rbp,rsp; sub rsp,F
    (swap! out cat (bytes* 0x4C 0x89 0x4C 0x24 0x00))                            ; mov [rsp+0],r9
    (doseq [j (range 6 n)]                                                      ; mov rax,[rbp+16+8(j-6)]; mov [rsp+8(j-5)],rax
      (swap! out cat (bytes* 0x48 0x8B 0x45 (+ 16 (* 8 (- j 6))) 0x48 0x89 0x44 0x24 (* 8 (- j 5)))))
    (let [lea (+ (python/len @out) 3)]
      (swap! out cat (bytes* 0x4C 0x8D 0x0D 0 0 0 0))                            ; lea r9,[rip+context]
      (swap! out cat (bytes* 0x49 0xC7 0x41 0x08) (struct/pack "<i" fuel-int))   ; mov qword [r9+8], fuel
      [@out lea])))

(defn check-long [obj n]
  (let [[sh lea] (long-shim n)
        size (+ (python/len sh) 5 2)
        text (:text obj)]
    (when (or (not (u/deq (u/bslice text 0 (python/len sh)) sh)) (not= (operator/getitem text (python/len sh)) 0xE8)
              (not (u/deq (u/bslice text (+ (python/len sh) 5) size) (bytes* 0xc9 0xc3))))
      (fail (str n "-parameter shim is not the expected sequence: " (.hex (u/bslice text 0 size)))))
    (when (not= (first (unpack "<i" text (inc (python/len sh)))) 2)   ; past leave; ret, to the code after the shim
      (fail (str n "-parameter shim does not call the code right after it")))
    (let [f (first (filter #(= (first %) "f") (:symbols obj)))]
      (when (or (not= (nth f 1) 0x12) (not= (nth f 3) 0) (not= (nth f 4) size))
        (fail (str "export f is " (rest f) ", want GLOBAL FUNC at 0 size " size))))
    (when (not= (mapv (fn [[o _ a]] [o a]) (:relas obj)) [[lea -4]])
      (fail (str "relocations " (:relas obj) ", want one at the LEA displacement " lea)))
    size))

(defn check-mixed [obj]
  (let [[six lea] (long-shim 6)
        size6 (+ (python/len six) 7)
        syms (into {} (map (fn [s] [(first s) s]) (:symbols obj)))]
    (when (not= [(nth (get syms "f") 3) (nth (get syms "f") 4) (nth (get syms "g") 3) (nth (get syms "g") 4)] [0 size6 size6 shim])
      (fail (str "mixed layout f=" (rest (get syms "f")) ", g=" (rest (get syms "g")))))
    (when (not= (mapv (fn [[o _ a]] [o a]) (:relas obj)) [[lea -4] [(+ size6 3) -4]])
      (fail (str "mixed relocations " (:relas obj))))))

(defn refused? [result obj code]
  (and (.__contains__ (lib/message-of result) code) (not (.exists obj))))

(defn main [compiler output]
  (lib/start! compiler output)
  (let [report (u/pydict)
        [_ one] (lib/compile-source compiler output "one" one-source)
        digest (lib/sha-of one)
        _ (when (not= digest one-sha256) (fail (str "one-export object changed: " digest)))
        _ (.__setitem__ report "oneExport" (u/pydict "sha256" digest "bytes" (.-st_size (.stat one))))
        [_ two] (lib/compile-source compiler output "two" two-source)
        _ (check-two (lib/read-elf two))
        _ (.__setitem__ report "twoExports" (u/pydict "sha256" (lib/sha-of two) "bytes" (.-st_size (.stat two))))
        [result nine] (lib/compile-source compiler output "nine" nine-source 1)
        _ (when-not (refused? result nine "E7102") (fail "nine exports were not refused with E7102 and no output"))
        _ (.__setitem__ report "nineExports" "refused E7102")]
    (doseq [[name src n] [["six" six-source 6] ["eight" eight-source 8]]]
      (let [[_ obj] (lib/compile-source compiler output name src)
            size (check-long (lib/read-elf obj) n)]
        (.__setitem__ report (str name "Params") (u/pydict "sha256" (lib/sha-of obj) "shimBytes" size))))
    (let [[_ mixed] (lib/compile-source compiler output "mixed" mixed-source)]
      (check-mixed (lib/read-elf mixed))
      (.__setitem__ report "mixedLayout" "six-parameter shim then the short shim"))
    (doseq [[name src code] [["ninep" nine-params-source "E2108"] ["privsix" private-six-source "E7102"]]]
      (let [[result obj] (lib/compile-source compiler output name src 1)]
        (when-not (refused? result obj code) (fail (str name " was not refused with " code " and no output")))
        (.__setitem__ report name (str "refused " code))))
    (lib/emit! output report "PASS_AIUEOS_OBJECT_EXPORTS")))

(defn -main [& args] (lib/cli-main args main))

(when (some #(or (= % "check-aiueos-object-exports.cljc") (str/ends-with? % "/check-aiueos-object-exports.cljc")) sys/argv)
  (apply -main *command-line-args*))
