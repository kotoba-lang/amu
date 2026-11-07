;; Observe native CAS lock/unlock and extended-control-register fixtures.
;;
;; The owner fixes 0->1 / 1->0 and returns the swap's Boolean result. The
;; privileged guest tests run separately; this observer does not own CDCI.
;; Ported from check-aiueos-lock-native.py (Basilisp). Linux only.
;; Run: basilisp run scripts/seed/check-aiueos-lock-native.cljc -- (--build DIR | --complete DIR) --output OUT
(ns check-aiueos-lock-native
  (:require [aiueos-gate :as g]
            [aiueos-native-proof :as proof]
            [basilisp.string :as str]
            [gate-util :as u])
  (:import sys))

(def lock
  "(ns entry (:export [main]))
(defn main [] :i64
 (let [r (kernel-subregion (kernel-boot-info) 16544 152 8)
       saved (kernel-load-u64 r 8 0)
       cleared (kernel-store-u32 r 8 0 0)
       a (kernel-try-lock-u32 r 8 0)
       held (kernel-load-u32 r 8 0)
       b (kernel-try-lock-u32 r 8 0)
       u (kernel-unlock-u32 r 8 0)
       free (kernel-load-u32 r 8 0)
       v (kernel-unlock-u32 r 8 0)
       other (kernel-store-u32 r 8 0 2)
       denied (kernel-unlock-u32 r 8 0)
       unchanged (kernel-load-u32 r 8 0)
       z (kernel-store-u32 r 8 1 0)
       odd (kernel-try-lock-u32 r 8 1)
       odd-held (kernel-load-u8 r 8 1)
       odd-u (kernel-unlock-u32 r 8 1)
       restored (kernel-store-u64 r 8 0 saved)]
   (if (and (= cleared 0) (= a 1) (= held 1) (= b 0)
            (= u 1) (= free 0) (= v 0) (= other 2) (= denied 0)
            (= unchanged 2) (= z 0) (= odd 1) (= odd-held 1)
            (= odd-u 1) (= restored saved)) 42 0)))
")

(def xcr
  "(ns entry (:export [main]))
(defn main [] :i64
 (let [features (kernel-cpuid-ecx 1 0) old (kernel-read-cr4)
       enabled (kernel-write-cr4 (bit-or old 262144))
       xcr (kernel-xgetbv 0) written (kernel-xsetbv 0 xcr)
       readback (kernel-xgetbv 0) restored (kernel-write-cr4 old)]
  (if (and (not= (bit-and features 67108864) 0)
           (= enabled (bit-or old 262144)) (= xcr written)
           (= readback xcr) (= restored old)) 42 0)))
")

(defn main [build out complete]
  (let [[graph producers _] (proof/load-native-producers :build build :complete complete)
        _ (.mkdir out ** :parents true :exist_ok false)
        routes (python/list)]
    (doseq [compiler producers]
      (let [scope (g/start-scope compiler (.joinpath out (.-stem compiler)))
            artifacts (python/dict)
            ok (fn [name text] (g/case! scope artifacts name text :pin-source true :source-text true))
            bad (fn [name text] (g/case! scope artifacts name text :pin-source true :source-text true :refuse "E7106"))]
        (ok "lock" lock)
        (ok "xcr" xcr)
        (ok "lock-oversized" "(ns entry (:export [main]))\n(defn main [] :i64 (kernel-try-lock-u32 (kernel-boot-info) 16544 0))\n")
        (bad "literal-lock" (.replace lock "(kernel-try-lock-u32 r 8 0)" "(kernel-try-lock-u32 1089536 8 0)"))
        (bad "wrong-lock-length" (.replace lock "(kernel-try-lock-u32 r 8 0)" "(kernel-try-lock-u32 r 64 0)"))
        (bad "wrong-unlock-length" (.replace lock "(kernel-unlock-u32 r 8 0)" "(kernel-unlock-u32 r 64 0)"))
        (.append routes (u/pydict "compiler" (u/pin compiler) "artifacts" artifacts "refusals" 3))))
    (u/chk (u/deq (u/geti (u/geti routes 0) "artifacts") (u/geti (u/geti routes 1) "artifacts")))
    (let [report (u/pydict "status" "PASS_NATIVE_LOCK_PACKAGING" "source" graph "routes" routes
                           "guestExecution" false "ISRLiveRuntime" false "fullKernel" false "nativeCDCI" false)]
      (.write_text (.joinpath out "native-lock.json") (u/json-dump report))
      (println (u/geti report "status") "CAS success/failure/preserved word/unaligned; XCR0 read/write; guest gates separate"))))

(defn -main [& args]
  (let [[build out complete] (u/parse-build-complete-output args)]
    (main build out complete)))

(when (some #(or (= % "check-aiueos-lock-native.cljc") (str/ends-with? % "/check-aiueos-lock-native.cljc")) sys/argv)
  (apply -main *command-line-args*))
