;; The aiueos kernel object route's spin-wait hint (JUN-633 slice 5, ADR 0393).
;;
;; kernel-pause [] is id 29 of seed/74-x86_64-aiueos-object.kotoba: pause, returning 0. Compiles with a native Amu
;; compiler and checks (this script stages and observes; it emits nothing):
;;
;; * pause: an object exporting one pause carries exactly pause; xor eax,eax once;
;; * opt-in: the wait object of check-aiueos-object-halt, which does not name the stub, carries no pause and keeps the
;;   bytes it had before this block existed;
;; * unchanged: the 512-byte width object keeps its pinned SHA-256;
;; * refused, nothing written: the stub called with an argument.
;;
;; Not shown here: execution. docs/evidence/pause-intrinsic-20261031/ runs the pause under QEMU.
;; Ported from check-aiueos-object-pause.py (Basilisp, JUN-974).
;; Run: basilisp run -p scripts/seed scripts/seed/check-aiueos-object-pause.cljc -- --compiler C --output DIR
(ns check-aiueos-object-pause
  (:require [basilisp.string :as str]
            [aiueos-object-lib :as lib]
            [gate-util :as u]
            [macos-native-lib :as mac])
  (:import sys))

;; the wait object's SHA-256 under slice 4 (amu 0de77b5e): the pause block must leave it as it was
(def halt-wait-sha256 "83d8375aba61aab71cde8cc6625ba41d43c566c5281de7caf4c9c7a6c25414f7")
(def source
  (str "(ns ps (:export [kotoba_aiueos_spin]))\n"
       "(defn kotoba_aiueos_spin [] :i64 (kernel-pause))\n"))
(def pause (str "f390" "31c0"))
(def refusals [["argument" "(ns r (:export [f]))\n(defn f [] :i64 (kernel-pause 1))\n"]])

(defn main [compiler output]
  (lib/start! compiler output)
  (let [report (u/pydict)
        [_ obj] (lib/compile-source compiler output "pause" source)
        text (lib/text-section obj)
        found (u/pydict "pause" (.count (.hex text) pause) "f390" (.count text (u/hex->bytes "f390")))
        _ (when-not (u/deq found (u/pydict "pause" 1 "f390" 1)) (mac/fail (str "pause sequence " (python/dict found))))
        _ (.__setitem__ report "pause" (u/pydict "sequence" found "sha256" (lib/sha-of obj)))
        [_ obj] (lib/compile-source compiler output "wait" lib/halt-source)
        digest (lib/sha-of obj)
        _ (when (or (u/has-bytes? (u/hex->bytes "f390") (lib/text-section obj)) (not= digest halt-wait-sha256))
            (mac/fail (str "the wait object changed or carries a pause: " digest)))
        _ (.__setitem__ report "optIn" digest)]
    (lib/check-widths-unchanged! compiler output report)
    (lib/check-refusals! compiler output report refusals "E2103")
    (lib/emit! output report "PASS_AIUEOS_OBJECT_PAUSE")))

(defn -main [& args] (lib/cli-main args main))

(when (some #(or (= % "check-aiueos-object-pause.cljc") (str/ends-with? % "/check-aiueos-object-pause.cljc")) sys/argv)
  (apply -main *command-line-args*))
