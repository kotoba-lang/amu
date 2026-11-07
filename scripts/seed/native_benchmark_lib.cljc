;; Pure parts of the native benchmark observers: receipt-record validation, duplicate-field refusal and the closed
;; list of semantic host mutations. Split out of check-native-benchmark-host / check-native-benchmark-mutations
;; (Basilisp ports) so the tests and both observers can `require` them. Records are Python dicts (JSON), exactly as
;; the Python originals handled them.
(ns native-benchmark-lib
  (:require [gate-util :as u])
  (:import hashlib))

(defn unique-fields
  "object_pairs_hook: refuse a native receipt with a duplicated field."
  [pairs]
  (let [result (python/dict pairs)]
    (when (not= (python/len result) (python/len pairs))
      (throw (python/ValueError "duplicate native receipt field")))
    result))

(defn- exact-int? [x] (identical? (python/type x) python/int))

(defn valid-observation [row index n diagnostic]
  (let [scalars ["elapsedNs" "benchmarkFuel" "verifyFuel" "warmSeed" "highwaterAfterReset" "highwaterAfterVerify"]
        integers {"workloadId" index "iterations" n "diagnostic" diagnostic "result" 1 "warmupBodies" 1 "calls" 1}
        flags {"verifyOutsideTiming" true "sameContextVerify" true "resetIncluded" false "performanceQualified" false}
        keys (set (concat ["schema" "benchmarkArena" "finalArena"] scalars (keys integers) (keys flags)))]
    (boolean
      (and (instance? python/dict row)
           (= keys (set (python/list row)))
           (= "KOTOBA_NATIVE_BENCH_CANDIDATE_V1" (u/geti row "schema"))
           (every? (fn [[k value]] (and (exact-int? (u/geti row k)) (= value (u/geti row k)))) integers)
           (every? (fn [[k value]] (identical? value (u/geti row k))) flags)
           (every? (fn [k] (and (exact-int? (u/geti row k)) (>= (u/geti row k) 0))) scalars)
           (every? (fn [k] (let [v (u/geti row k)]
                             (and (instance? python/list v) (= 17 (python/len v))
                                  (every? #(and (exact-int? %) (>= % 0)) v))))
                   ["benchmarkArena" "finalArena"])
           (>= (u/geti row "highwaterAfterVerify") (u/geti row "highwaterAfterReset"))))))

(defn digest [raw] (u/sha256-hex raw))

(defn mutations
  "The 13 closed semantic host mutations: [name workload refusal source] each."
  [host]
  (let [change (fn [old new]
                 (u/chk (= 1 (.count host old)) old)
                 (.replace host old new))
        verify "verified (kb-verifier verifier state (if (= (kb-verify-arity id) 2) count 0))"
        end "end (kb-now 1) "
        before (str "        " verify)
        _ (u/chk (and (= 1 (.count host end)) (= 1 (.count host before))))
        inside (-> host (.replace end "") (.replace before (str before "\n        end (kb-now 1)")))
        begin "begin (kb-now 0)"
        reset (-> host (.replace begin "") (.replace "seed-ok (kb-pure) high (kb-reset)" (str "seed-ok (kb-pure) " begin " high (kb-reset)")))
        warm (-> host (.replace begin "") (.replace "warm-phase (if" (str begin "\n        warm-phase (if")))
        _ (u/chk (and (= 1 (.count host begin)) (= 1 (.count host "seed-ok (kb-pure) high (kb-reset)")) (= 1 (.count host "warm-phase (if"))))]
    [["wrong-warm-count" "tarfind" 3201 (change "warm (kb-invoke benchmark 1 0)" "warm (kb-invoke benchmark 2 0)")]
     ["missing-warm-seed" "tarfind" 3201 (change "seed (if (< (kb-seed id) 0) 0 (kb-invoke (+ payload (kb-seed id)) warm 0))" "seed 0")]
     ["missing-second-reset" "depthconv" 3203 (change "seed-ok (kb-pure) high (kb-reset)" "seed-ok (kb-pure) high (kxrt-gl 760)")]
     ["verification-inside-clock" "crc32" 3003 inside]
     ["missing-verification" "crc32" 3003 (change verify "verified 1")]
     ["wrong-benchmark-fuel" "crc32" 3202 (change "(- initial after-bench)" "(inc (- initial after-bench))")]
     ["wrong-verification-fuel" "crc32" 3202 (change "(- after-bench after-verify)" "(inc (- after-bench after-verify))")]
     ["missing-benchmark-snapshot" "depthconv" 3203 (change "snap1 (kb-snapshot (+ (kxrt-g) 22000))" "snap1 (kb-zero (+ (kxrt-g) 22000) 136)")]
     ["missing-final-snapshot" "depthconv" 3203 (change "snap2 (kb-snapshot (+ (kxrt-g) 22200))" "snap2 (kb-zero (+ (kxrt-g) 22200) 136)")]
     ["lowered-absolute-highwater" "depthconv" 2003 (change "d (kxrt-gs 64 0)" "d (kxrt-gs 64 0) lowered (kxrt-gs 760 0)")]
     ["missing-fuel-reset" "depthconv" 2003 (change "fuel (kxrt-store64 (+ (kxrt-ctx) 8) (kxrt-gl 168))" "fuel 0")]
     ["reset-inside-clock" "depthconv" 2004 reset]
     ["warmup-inside-clock" "crc32" 3003 warm]]))
