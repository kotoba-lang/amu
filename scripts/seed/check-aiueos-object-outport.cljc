;; The aiueos kernel object route's literal-bounded output ports (JUN-600, ADR 0400).
;;
;; kernel-out-u8 [port value] and kernel-out-u32 [port value] are ids 4 and 5 of seed/74-x86_64-aiueos-object.kotoba.
;; The port must be an integer LITERAL in its width's closed list (E7107), as kernel-in-u32's is (ADR 0399):
;;   out-u8:  0x20, 0x21 (master 8259), 0xa0, 0xa1 (slave 8259), 0x80 (the io_wait delay)   -- pic-disable
;;   out-u32: 0xcf8, 0xcfc (PCI configuration address and data)                              -- pci-config-read / -write
;; The value stays a run-time operand. Compiles with a native Amu compiler and checks (this script stages and observes;
;; it emits nothing):
;;
;; * sequences: one object writing every listed port, the values literal, a parameter and computed, in the shapes the
;;   kernel's pic-disable, pci-config-read and pci-config-write objects use, carries
;;     out-u8:  mov rdx,[port]; mov rax,[value]; out dx,al    seven times
;;     out-u32: mov rdx,[port]; mov rax,[value]; out dx,eax   three times
;;   and its bytes are those main's root (amu fe7b5b1c) emitted for the same source: the rule changes no admitted object;
;; * the plain image artifact (--artifact image) shares the check: a listed port compiles, an unlisted one is refused;
;; * refused, nothing written, for each width: an unlisted literal (out-u8: 0x3f8 COM1, 0xe9 the debug console, 0x22,
;;   0xcf9 reset control; out-u32: 0xcfd, 0xcf9, 0xf4 the QEMU exit port), the other width's port (out-u8 0xcf8, out-u32
;;   0x20), a parameter port, a computed port, a let-bound literal, a port selected by a branch (E7107); each with the
;;   wrong number of arguments (E2103).
;;
;; Not shown here: execution. The bytes are main's, so the QEMU port traces of the kernel objects that use these stubs
;; are unchanged; kotoba's port-trace differentials cover them.
;; Ported from check-aiueos-object-outport.py (Basilisp, JUN-974).
;; Run: basilisp run -p scripts/seed scripts/seed/check-aiueos-object-outport.cljc -- --compiler C --output DIR
(ns check-aiueos-object-outport
  (:require [basilisp.string :as str]
            [aiueos-object-lib :as lib]
            [gate-util :as u]
            [macos-native-lib :as mac])
  (:import operator re sys))

;; every listed port, with literal, parameter and computed values, as pic-disable / pci-config-read / pci-config-write
(def source
  (str "(ns outport (:export [pic pcw pcr]))\n"
       "(defn pic [m :i64 s :i64] :i64\n"
       "  (if (and (>= m 32) (>= s 32))\n"
       "    (let [c1 (kernel-out-u8 32 17) d1 (kernel-out-u8 128 0) c2 (kernel-out-u8 160 17)\n"
       "          c3 (kernel-out-u8 33 m) c4 (kernel-out-u8 161 s) c9 (kernel-out-u8 33 255) c10 (kernel-out-u8 161 255)]\n"
       "      1)\n"
       "    0))\n"
       "(defn pcw [a :i64 v :i64] :i64\n"
       "  (let [x (kernel-out-u32 3320 (bit-or 2147483648 (bit-and a 252))) y (kernel-out-u32 3324 v)] 1))\n"
       "(defn pcr [a :i64] :i64 (let [x (kernel-out-u32 3320 (bit-or 2147483648 a))] (kernel-in-u32 3324)))\n"))
;; source compiled by main's root (seed/bootstrap/aarch64-macos/amu-full-root.macho at amu fe7b5b1c), before this rule
(def source-sha256 "6377fce8f681ff0c760798f8fb41281e247f5b8627000ba5348c24464b1fd0d7")
(defn cat [& parts] (reduce operator/add parts))
(defn out-pattern [opcode]
  (re/compile (cat (u/hex->bytes "488b95") (.encode ".{4}") (u/hex->bytes "488b85") (.encode ".{4}") (u/hex->bytes opcode)) re/DOTALL))
(def image-ok "(ns i (:export [main]))\n(defn main [] :i64 (let [x (kernel-out-u8 128 0)] 42))\n")
(def image-bad "(ns i (:export [main]))\n(defn main [] :i64 (let [x (kernel-out-u8 1016 65)] 42))\n")
(defn one
  ([form] (one form ""))
  ([form params] (str "(ns r (:export [f]))\n(defn f [" params "] :i64 " form ")\n")))
(def refusals
  [["u8-com1" (one "(kernel-out-u8 1016 65)") "E7107"]
   ["u8-debugcon" (one "(kernel-out-u8 233 65)") "E7107"]
   ["u8-elcr-neighbour" (one "(kernel-out-u8 34 0)") "E7107"]
   ["u8-reset" (one "(kernel-out-u8 3321 6)") "E7107"]
   ["u8-u32-port" (one "(kernel-out-u8 3320 0)") "E7107"]
   ["u8-parameter" (one "(kernel-out-u8 p 0)" "p :i64") "E7107"]
   ["u8-computed" (one "(kernel-out-u8 (bit-or p 32) 0)" "p :i64") "E7107"]
   ["u8-let-bound" (one "(let [p 32] (kernel-out-u8 p 0))") "E7107"]
   ["u8-branch" (one "(kernel-out-u8 (if (= s 0) 32 160) 0)" "s :i64") "E7107"]
   ["u32-cfd" (one "(kernel-out-u32 3325 0)") "E7107"]
   ["u32-reset" (one "(kernel-out-u32 3321 6)") "E7107"]
   ["u32-qemu-exit" (one "(kernel-out-u32 244 16)") "E7107"]
   ["u32-u8-port" (one "(kernel-out-u32 32 0)") "E7107"]
   ["u32-parameter" (one "(kernel-out-u32 p 0)" "p :i64") "E7107"]
   ["u32-computed" (one "(kernel-out-u32 (+ p 3320) 0)" "p :i64") "E7107"]
   ["u32-let-bound" (one "(let [p 3320] (kernel-out-u32 p 0))") "E7107"]
   ["u32-branch" (one "(kernel-out-u32 (if (= s 0) 3320 3324) 0)" "s :i64") "E7107"]
   ["u8-one" (one "(kernel-out-u8 32)") "E2103"]
   ["u8-three" (one "(kernel-out-u8 32 0 0)") "E2103"]
   ["u32-one" (one "(kernel-out-u32 3320)") "E2103"]
   ["u32-three" (one "(kernel-out-u32 3320 0 0)") "E2103"]])

(defn image [compiler output name src expected]
  (.write_text (.joinpath output (str name ".kotoba")) src)
  [(mac/native-run compiler output ["compile" (str name ".kotoba") "--target" "x86_64-aiueos-kernel-v1" "--artifact" "image"
                                    "--output" (str name ".elf") "--fuel" "1000000"] :expected expected)
   (.joinpath output (str name ".elf"))])

(defn main [compiler output]
  (lib/start! compiler output)
  (let [report (u/pydict)
        [_ obj] (lib/compile-source compiler output "outport" source)
        text (lib/text-section obj)
        found (u/pydict "out-u8" (python/len (re/findall (out-pattern "ee") text))
                        "out-u32" (python/len (re/findall (out-pattern "ef") text)))
        _ (when-not (u/deq found (u/pydict "out-u8" 7 "out-u32" 3))
            (mac/fail (str "output-port sequences " (python/dict found) ", want 7 and 3")))
        digest (lib/sha-of obj)
        _ (when (not= digest source-sha256)
            (mac/fail (str "the admitted output-port object changed: " digest ", main's root gave " source-sha256)))
        _ (.__setitem__ report "sequences" (u/pydict "found" found "sha256" digest))
        [_ elf] (image compiler output "image-ok" image-ok 0)
        _ (when-not (.exists elf) (mac/fail "the image artifact with a listed port was not written"))
        [result elf] (image compiler output "image-bad" image-bad 1)
        message (lib/message-of result)
        _ (when (or (not (.__contains__ message "E7107")) (.exists elf))
            (mac/fail (str "the image artifact with port 0x3f8 was not refused with E7107: " message)))
        _ (.__setitem__ report "image" (u/pydict "listed" "compiled" "unlisted" "refused E7107"))]
    (doseq [[name src code] refusals]
      (lib/check-refusals! compiler output report [[name src]] code))
    (lib/emit! output report "PASS_AIUEOS_OBJECT_OUTPORT")))

(defn -main [& args] (lib/cli-main args main))

(when (some #(or (= % "check-aiueos-object-outport.cljc") (str/ends-with? % "/check-aiueos-object-outport.cljc")) sys/argv)
  (apply -main *command-line-args*))
