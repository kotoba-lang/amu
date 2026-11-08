;; The aiueos kernel object route's halt-until-interrupt (JUN-633 slice 4, ADR 0392).
;;
;; kernel-wait-interrupt [] is id 28 of seed/74-x86_64-aiueos-object.kotoba: sti; hlt; cli, returning 0. Compiles with a
;; native Amu compiler and checks (this script stages and observes; it emits nothing):
;;
;; * wait: an object exporting one wait carries exactly sti; hlt; cli; xor eax,eax once, and no other sti / hlt / cli;
;; * opt-in: an object that does not name the stub (the extended-state source of check-aiueos-object-xstate) carries no
;;   sti, hlt or cli at all;
;; * unchanged: the 512-byte width object keeps its pinned SHA-256;
;; * refused, nothing written: the stub called with an argument.
;;
;; Not shown here: execution. docs/evidence/halt-intrinsic-20261031/ runs the wait under a 100 Hz PIT interrupt in QEMU.
;; Ported from check-aiueos-object-halt.py (Basilisp, JUN-974).
;; Run: basilisp run -p scripts/seed scripts/seed/check-aiueos-object-halt.cljc -- --compiler C --output DIR
(ns check-aiueos-object-halt
  (:require [basilisp.string :as str]
            [aiueos-object-lib :as lib]
            [gate-util :as u]
            [macos-native-lib :as mac])
  (:import sys))

(def wait (str "fb" "f4" "fa" "31c0"))
(def refusals [["argument" "(ns r (:export [f]))\n(defn f [] :i64 (kernel-wait-interrupt 1))\n"]])

(defn main [compiler output]
  (lib/start! compiler output)
  (let [report (u/pydict)
        [_ obj] (lib/compile-source compiler output "wait" lib/halt-source)
        text (lib/text-section obj)
        found (u/pydict "wait" (.count (.hex text) wait) "sti" (.count text (u/hex->bytes "fb"))
                        "hlt" (.count text (u/hex->bytes "f4")) "cli" (.count text (u/hex->bytes "fa")))
        _ (when (or (not= 1 (u/geti found "wait")) (not (u/has-bytes? (u/hex->bytes wait) text)))
            (mac/fail (str "wait sequence " (python/dict found))))
        _ (.__setitem__ report "wait" (u/pydict "sequence" found "sha256" (lib/sha-of obj)))
        [_ obj] (lib/compile-source compiler output "no-wait" lib/xstate-source)
        _ (when (u/has-bytes? (u/hex->bytes "fbf4fa") (lib/text-section obj))
            (mac/fail "an object that names no wait carries the halt sequence"))
        _ (.__setitem__ report "optIn" (lib/sha-of obj))]
    (lib/check-widths-unchanged! compiler output report)
    (lib/check-refusals! compiler output report refusals "E2103")
    (lib/emit! output report "PASS_AIUEOS_OBJECT_HALT")))

(defn -main [& args] (lib/cli-main args main))

(when (some #(or (= % "check-aiueos-object-halt.cljc") (str/ends-with? % "/check-aiueos-object-halt.cljc")) sys/argv)
  (apply -main *command-line-args*))
