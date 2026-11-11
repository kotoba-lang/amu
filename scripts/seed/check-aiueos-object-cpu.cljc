;; The aiueos kernel object route's CPU feature reads (JUN-633).
;;
;; kernel-cpuid-<eax|ebx|ecx|edx> [leaf subleaf], kernel-rdtsc [] and kernel-rdrand [] are ids 18..23 of
;; seed/74-x86_64-aiueos-object.kotoba, named and encoded as seed/86's kernel runtime has them (km-cpu, km-entropy),
;; with lfence before rdtsc. Compiles with a native Amu compiler and checks the emitted bytes (this script stages and
;; observes; it emits nothing):
;;
;; * six: one object exporting the six, each body carrying exactly its sequence --
;;     cpuid:  mov rax,[leaf]; mov rcx,[subleaf]; push rbx; cpuid; [mov eax,ebx|ecx|edx]; pop rbx
;;     rdtsc:  lfence; rdtsc; shl rdx,32; or rax,rdx
;;     rdrand: mov ecx,10; L: rdrand rax; jc +6; dec ecx; jnz L; xor eax,eax
;; * unchanged: the 512-byte width object of check-aiueos-object-windows's source keeps its pinned SHA-256, so no
;;   object that does not name a CPU stub changes;
;; * refused, nothing written: a CPU read used as a window base (E7106, it is not a rooted region), and a call with the
;;   wrong arity.
;;
;; Not shown here: execution. docs/evidence/cpu-intrinsics-20261030/ runs the six-object under QEMU against inline-asm C.
;; Ported from check-aiueos-object-cpu.py (Basilisp, JUN-974).
;; Run: basilisp run -p scripts/seed scripts/seed/check-aiueos-object-cpu.cljc -- --compiler C --output DIR
(ns check-aiueos-object-cpu
  (:require [basilisp.string :as str]
            [aiueos-object-lib :as lib]
            [gate-util :as u]
            [macos-native-lib :as mac])
  (:import json sys))

(def source
  (str "(ns cpu (:export [ca cb cc cd ts rr]))\n"
       "(defn ca [l :i64 s :i64] :i64 (kernel-cpuid-eax l s))\n"
       "(defn cb [l :i64 s :i64] :i64 (kernel-cpuid-ebx l s))\n"
       "(defn cc [l :i64 s :i64] :i64 (kernel-cpuid-ecx l s))\n"
       "(defn cd [l :i64 s :i64] :i64 (kernel-cpuid-edx l s))\n"
       "(defn ts [] :i64 (kernel-rdtsc))\n"
       "(defn rr [] :i64 (kernel-rdrand))\n"))
(def cpuid-core (str "53" "0fa2"))
(def cpuid-move [["eax" ""] ["ebx" "89d8"] ["ecx" "89c8"] ["edx" "89d0"]])
(def rdtsc (str "0faee8" "0f31" "48c1e220" "4809d0"))
(def rdrand (str "b90a000000" "480fc7f0" "7206" "ffc9" "75f6" "31c0"))
(def refusals
  [["cpu-as-base" "(ns refused (:export [f]))\n(defn f [n :i64 i :i64] :i64 (kernel-load-u8 (kernel-rdtsc) n i))\n" "E7106"]
   ["arity" "(ns refused (:export [f]))\n(defn f [l :i64] :i64 (kernel-cpuid-eax l))\n" nil]])

(defn main [compiler output]
  (lib/start! compiler output)
  (let [report (u/pydict)
        [_ obj] (lib/compile-source compiler output "cpu" source)
        text (.hex (lib/text-section obj))
        found (u/pydict-from
               (concat
                (for [[reg move] cpuid-move]
                  ;; the leaf and subleaf come from their frame slots: mov rax,[rbp+d]; mov rcx,[rbp+d]; then the core
                  [(str "cpuid-" reg) (if (seq move) (.count text (str cpuid-core move "5b")) (.count text (str cpuid-core "5b")))])
                [["rdtsc" (.count text rdtsc)] ["rdrand" (.count text rdrand)]]))
        _ (when-not (u/deq found (u/pydict "cpuid-eax" 1 "cpuid-ebx" 1 "cpuid-ecx" 1 "cpuid-edx" 1 "rdtsc" 1 "rdrand" 1))
            (mac/fail (str "CPU sequences " (python/dict found) "; want each exactly once")))
        _ (when (or (not= 4 (.count text "0fa2")) (not= 1 (.count text "0f31")) (not= 1 (.count text "0fc7f0")))
            (mac/fail "a CPU instruction appears outside its sequence"))
        _ (.__setitem__ report "six" (u/pydict "sequences" found "sha256" (lib/sha-of obj)))]
    (lib/check-widths-unchanged! compiler output report)
    (doseq [[name src code] refusals]
      (let [[result obj] (lib/compile-source compiler output name src 1)
            message (lib/message-of result)]
        (when (or (.exists obj) (and code (not (.__contains__ message code))))
          (mac/fail (str name " was not refused" (when code (str " with " code)) " and no output: " message)))
        (.__setitem__ report name (str "refused " (or code (subs (first (.split (.strip message) ";")) 0 (min 60 (count (first (.split (.strip message) ";"))))))))))
    (lib/emit! output report "PASS_AIUEOS_OBJECT_CPU")))

(defn -main [& args] (lib/cli-main args main))

(when (some #(or (= % "check-aiueos-object-cpu.cljc") (str/ends-with? % "/check-aiueos-object-cpu.cljc")) sys/argv)
  (apply -main *command-line-args*))
