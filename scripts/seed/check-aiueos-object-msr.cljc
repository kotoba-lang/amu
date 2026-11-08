;; The aiueos kernel object route's bounded MSR and port-input accesses (JUN-600, ADR 0399).
;;
;; kernel-read-msr [index], kernel-write-msr [index value] and kernel-in-u32 [port] are ids 32, 33 and 34 of
;; seed/74-x86_64-aiueos-object.kotoba, each a block of its own. The index and the port must be integer LITERALS in
;; closed lists (E7107): MSRs 0x1b IA32_APIC_BASE, 0xc0000080 IA32_EFER, 0xc0000081 IA32_STAR, 0xc0000082 IA32_LSTAR and
;; 0xc0000084 IA32_FMASK; port 0xcfc. A write of APIC_BASE may only set bit 11 and a write of EFER only bits 0 and 11
;; of the current value (a run-time bound, ud2 otherwise). Compiles with a native Amu compiler and checks (this script
;; stages and observes; it emits nothing):
;;
;; * sequences: one object exporting an MSR read and an MSR write, each selecting one of the five literal indices by
;;   the run-time index (as the kernel's msr-read / msr-write objects do), and a PCI configuration read carries
;;     read-msr:  mov rcx,[index]; rdmsr; shl rdx,32; or rax,rdx                                   five times
;;     write-msr: mov rcx,[index]; mov rsi,[value]; the APIC_BASE / EFER bound (cmp ecx,0x1b ... ud2); wrmsr   five times
;;     in-u32:    mov rdx,[port]; in eax,dx                                                            once
;;   and no other rdmsr, wrmsr or in;
;; * opt-in: the fused-reduction gate's dot object, which names none of the three, keeps the bytes it had before the
;;   blocks existed, and the 512-byte width object keeps its pinned SHA-256;
;; * refused, nothing written: an index outside the list (IA32_CSTAR 0xc0000083, between two admitted ones; IA32_TSC
;;   0x10; IA32_PAT 0x277 for a write), an index that is a parameter or computed, a port outside the list (0xcf8,
;;   0xcfd) or a parameter port (E7107); each with the wrong number of arguments (E2103).
;;
;; Not shown here: execution. docs/evidence/msr-in-intrinsics-20261031/ runs the object under QEMU against inline-asm C.
;; Ported from check-aiueos-object-msr.py (Basilisp, JUN-974).
;; Run: basilisp run -p scripts/seed scripts/seed/check-aiueos-object-msr.cljc -- --compiler C --output DIR
(ns check-aiueos-object-msr
  (:require [basilisp.string :as str]
            [aiueos-object-lib :as lib]
            [gate-util :as u]
            [macos-native-lib :as mac])
  (:import operator re sys))

;; the fused-reduction gate's dot object under amu c2c9dfbe (main before these blocks): it must keep its bytes
(def dot-sha256 "30261e7d172802a0561c3c7053655a80faadbfc174cc5a121dcd75d5736f4706")
(def msrs [27 3221225600 3221225601 3221225602 3221225604])
;; kotoba_aiueos_msr_read / _write select one of the five literal indices by the run-time index, as the kernel's objects do
(def source
  (str "(ns msr (:export [kotoba_aiueos_msr_read kotoba_aiueos_msr_write pcr]))\n"
       "(defn kotoba_aiueos_msr_read [i :i64] :i64\n  (cond "
       (str/join " " (for [v msrs] (str "(= i " v ") (kernel-read-msr " v ")"))) " :else 0))\n"
       "(defn kotoba_aiueos_msr_write [i :i64 v :i64] :i64\n  (cond "
       (str/join " " (for [v msrs] (str "(= i " v ") (kernel-write-msr " v " v)"))) " :else 0))\n"
       "(defn pcr [a :i64] :i64 (let [x (kernel-out-u32 3320 a)] (kernel-in-u32 3324)))\n"))
(def read-seq (str "0f32" "48c1e220" "4809d0"))
(def write-seq (str "83f91b" "7410" "81f9800000c0" "7522" "41b801080000" "eb06" "41b800080000"
                    "0f32" "48c1e220" "4809d0" "4921f0" "4909c0" "4939f0" "750e"
                    "4889f0" "4889f2" "48c1ea20" "0f30" "eb02" "0f0b"))
(def refusals
  [["read-cstar" "(ns r (:export [f]))\n(defn f [] :i64 (kernel-read-msr 3221225603))\n" "E7107"]
   ["read-tsc" "(ns r (:export [f]))\n(defn f [] :i64 (kernel-read-msr 16))\n" "E7107"]
   ["read-parameter" "(ns r (:export [f]))\n(defn f [i :i64] :i64 (kernel-read-msr i))\n" "E7107"]
   ["read-computed" "(ns r (:export [f]))\n(defn f [i :i64] :i64 (kernel-read-msr (bit-or i 27)))\n" "E7107"]
   ["write-cstar" "(ns r (:export [f]))\n(defn f [v :i64] :i64 (kernel-write-msr 3221225603 v))\n" "E7107"]
   ["write-pat" "(ns r (:export [f]))\n(defn f [v :i64] :i64 (kernel-write-msr 631 v))\n" "E7107"]
   ["write-parameter" "(ns r (:export [f]))\n(defn f [i :i64 v :i64] :i64 (kernel-write-msr i v))\n" "E7107"]
   ["in-index-port" "(ns r (:export [f]))\n(defn f [] :i64 (kernel-in-u32 3320))\n" "E7107"]
   ["in-cfd" "(ns r (:export [f]))\n(defn f [] :i64 (kernel-in-u32 3325))\n" "E7107"]
   ["in-parameter" "(ns r (:export [f]))\n(defn f [p :i64] :i64 (kernel-in-u32 p))\n" "E7107"]
   ["read-two" "(ns r (:export [f]))\n(defn f [] :i64 (kernel-read-msr 27 0))\n" "E2103"]
   ["write-one" "(ns r (:export [f]))\n(defn f [] :i64 (kernel-write-msr 27))\n" "E2103"]
   ["in-none" "(ns r (:export [f]))\n(defn f [] :i64 (kernel-in-u32))\n" "E2103"]])

(defn cat [& parts] (reduce operator/add parts))
(defn rx [pattern] (re/compile pattern re/DOTALL))

(defn main [compiler output]
  (lib/start! compiler output)
  (let [report (u/pydict)
        [_ obj] (lib/compile-source compiler output "msr" source)
        text (lib/text-section obj)
        seq-count (fn [pattern] (python/len (re/findall (rx pattern) text)))]
    ;; byte-exact patterns, built from raw bytes (the Python original used b"\x48\x8b\x8d.{4}" + bytes.fromhex(...))
    (let [pat-read (cat (u/hex->bytes "488b8d") (.encode ".{4}") (u/hex->bytes read-seq))
          pat-write (cat (u/hex->bytes "488b8d") (.encode ".{4}") (u/hex->bytes "488bb5") (.encode ".{4}") (u/hex->bytes write-seq))
          pat-in (cat (u/hex->bytes "488b95") (.encode ".{4}") (u/hex->bytes "ed"))
          found (u/pydict "read-msr" (seq-count pat-read) "write-msr" (seq-count pat-write)
                          "in-u32" (seq-count pat-in) "rdmsr" (.count text (u/hex->bytes "0f32"))
                          "wrmsr" (.count text (u/hex->bytes "0f30")) "in" (.count text (u/hex->bytes "ed")))
          want (u/pydict "read-msr" 5 "write-msr" 5 "in-u32" 1 "rdmsr" 10 "wrmsr" 5 "in" 1)]
      (when-not (u/deq found want)
        (mac/fail (str "MSR / port-input sequences " (python/dict found) ", want " (python/dict want))))
      (.__setitem__ report "sequences" (u/pydict "found" found "sha256" (lib/sha-of obj))))
    (let [[_ obj] (lib/compile-source compiler output "dot" lib/dot-source)
          digest (lib/sha-of obj)]
      (when (not= digest dot-sha256) (mac/fail (str "the fused-reduction dot object changed: " digest)))
      (.__setitem__ report "optIn" digest))
    (lib/check-widths-unchanged! compiler output report)
    (doseq [[name src code] refusals]
      (lib/check-refusals! compiler output report [[name src]] code))
    (lib/emit! output report "PASS_AIUEOS_OBJECT_MSR")))

(defn -main [& args] (lib/cli-main args main))

(when (some #(or (= % "check-aiueos-object-msr.cljc") (str/ends-with? % "/check-aiueos-object-msr.cljc")) sys/argv)
  (apply -main *command-line-args*))
