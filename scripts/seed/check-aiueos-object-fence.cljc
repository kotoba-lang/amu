;; The aiueos kernel object route's memory fences (JUN-708, ADR 0401).
;;
;; kernel-fence-load [], kernel-fence-store [] and kernel-fence-full [] are ids 43..45 of
;; seed/74-x86_64-aiueos-object.kotoba: lfence (0f ae e8), sfence (0f ae f8) and mfence (0f ae f0), each answering 0,
;; the bytes kotoba-native machine-ir encodes for :fence-load / :fence-store / :fence-full and that kotoba-compiler/1
;; emitted into the rtl8125 driver objects (`0f ae f8` in rtl8125-program.o, `0f ae e8` in rtl8125-rx-poll.o, each
;; followed by `mov r10d,0`). Compiles with a native Amu compiler and checks (this script stages and observes; it emits
;; nothing):
;;
;; * sequences: an object exporting fl, fs, ff (one function per fence) carries each of FENCE; xor eax,eax exactly once,
;;   in that order, and no other 0f ae fence byte sequence;
;; * in a driver shape: a store, sfence, then a doorbell store into the same 4 KiB window (as rtl8125-tx-submit does),
;;   and an lfence between two loads (as rtl8125-rx-poll does): the fence lies between the two accesses, in source order;
;; * opt-in: the 4 KiB width object of check-aiueos-object-windows4k, which names no fence, carries no fence bytes and
;;   keeps its pinned SHA-256; so do the objects that name neither block (the 512-byte and 16 KiB width objects and the
;;   out-port object, ids 0..34);
;; * refused, nothing written: each fence called with an argument (E2103).
;;
;; Not shown here: execution. docs/evidence/windows4k-fence-20261031/ runs the three fences under QEMU.
;; Ported from check-aiueos-object-fence.py (Basilisp, JUN-974).
;; Run: basilisp run -p scripts/seed scripts/seed/check-aiueos-object-fence.cljc -- --compiler C --output DIR
(ns check-aiueos-object-fence
  (:require [basilisp.string :as str]
            [aiueos-object-lib :as lib]
            [gate-util :as u]
            [macos-native-lib :as mac])
  (:import sys))

(def fences [["load" "0faee8"] ["store" "0faef8"] ["full" "0faef0"]])
(def source
  (str "(ns fence (:export [fl fs ff]))\n"
       "(defn fl [] :i64 (kernel-fence-load))\n"
       "(defn fs [] :i64 (kernel-fence-store))\n"
       "(defn ff [] :i64 (kernel-fence-full))\n"))
(def driver
  (str "(ns drv (:export [submit poll]))\n"
       "(defn submit [b :i64 n :i64 v :i64] :i64\n"
       "  (let [d (kernel-store-u32-4k b n 0 v) f (kernel-fence-store) bell (kernel-store-u8-4k b n 56 64)] (+ d f)))\n"
       "(defn poll [b :i64 n :i64] :i64\n"
       "  (let [s (kernel-load-u32-4k b n 0) f (kernel-fence-load) w (kernel-load-u64-4k b n 8)] (+ (+ s f) w)))\n"))

(defn main [compiler output]
  (lib/start! compiler output)
  (let [report (u/pydict)
        [_ obj] (lib/compile-source compiler output "fence" source)
        text (.hex (lib/text-section obj))
        found (u/pydict-from (for [[name code] fences] [name (.count text (str code "31c0"))]))
        at (mapv (fn [[_ code]] (.find text (str code "31c0"))) fences)
        ;; fl, fs, ff: the bodies lie in source order, so lfence, sfence, mfence in that order
        _ (when (or (not (u/deq found (u/pydict "load" 1 "store" 1 "full" 1))) (not= 3 (.count text "0fae"))
                    (not (< (nth at 0) (nth at 1) (nth at 2))))
            (mac/fail (str "fence sequences " (python/dict found) " at " at ", 0f ae occurrences " (.count text "0fae"))))
        _ (.__setitem__ report "fences" (u/pydict "sequences" found "sha256" (lib/sha-of obj)))
        [_ obj] (lib/compile-source compiler output "driver" driver)
        raw (lib/text-section obj)
        w (lib/windows raw 4096 #{2 4 8})
        sf (.find raw (u/hex->bytes "0faef8"))
        lf (.find raw (u/hex->bytes "0faee8"))
        order (mapv second w)
        ;; the accesses in the order the functions use them (the object places the bodies in source order)
        _ (when (or (not= order [["store" 4] ["store" 1] ["load" 4] ["load" 8]])
                    (not (< (first (nth w 0)) sf (first (nth w 1)) (first (nth w 2)) lf (first (nth w 3)))))
            (mac/fail (str "driver: windows " w ", sfence at " sf ", lfence at " lf)))
        _ (.__setitem__ report "driver" "store; sfence; doorbell store -- load; lfence; load")]
    (doseq [[name src digest] [["w4k" lib/w4k-source lib/w4k-sha256]
                               ["widths" lib/widths-source lib/widths-sha256]
                               ["widths16" lib/source16 lib/widths16-sha256]
                               ["outport" lib/outport-source lib/outport-sha256]]]
      (let [[_ o] (lib/compile-source compiler output name src)
            have (lib/sha-of o)]
        (when (or (u/has-bytes? (u/hex->bytes "0fae") (lib/text-section o)) (not= have digest))
          (mac/fail (str name ": an object naming no fence changed (" have ") or carries fence bytes")))
        (.__setitem__ report (str name "NoFence") have)))
    (doseq [[name _] fences]
      (lib/check-refusals! compiler output report
                           [[(str name "-argument") (str "(ns r (:export [f]))\n(defn f [] :i64 (kernel-fence-" name " 1))\n")]]
                           "E2103"))
    (lib/emit! output report "PASS_AIUEOS_OBJECT_FENCE")))

(defn -main [& args] (lib/cli-main args main))

(when (some #(or (= % "check-aiueos-object-fence.cljc") (str/ends-with? % "/check-aiueos-object-fence.cljc")) sys/argv)
  (apply -main *command-line-args*))
