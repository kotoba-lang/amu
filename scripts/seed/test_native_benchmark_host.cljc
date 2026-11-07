;; Observer/source golden checks only; never replaces executed native gates.
;; Ported from test_native_benchmark_host.py (Basilisp). Run from the repo root:
;;   PYTHONPATH=scripts/seed basilisp test -p no:cacheprovider --rootdir scripts/seed scripts/seed/test_native_benchmark_host.cljc
(ns test-native-benchmark-host
  (:require [basilisp.test :refer [deftest is]]
            [basilisp.string :as str]
            [gate-util :as u]
            [native-benchmark-lib :as lib])
  (:import json operator re))

(defn form [text name]
  (let [start (.index text (str "(defn- " name " "))]
    (loop [i start depth 0]
      (when (>= i (python/len text)) (throw (python/AssertionError "unclosed function")))
      (let [c (operator/getitem text i)
            depth (+ depth (if (= c "(") 1 0) (if (= c ")") -1 0))]
        (if (zero? depth) (subs text start (inc i)) (recur (inc i) depth))))))

(defn cases
  "Fixed numeric case tables only, not a Kotoba interpreter or verdict."
  [text]
  (let [tokens (vec (.split (.strip text)))]
    (u/chk (and (= ["(case" "id"] (subvec tokens 0 2)) (str/ends-with? (last tokens) ")")))
    (let [values (mapv #(python/int %) (.split (.removesuffix (str/join " " (subvec tokens 2)) ")")))]
      (u/chk (odd? (count values)))
      (assoc (into {} (map vec (partition 2 (butlast values)))) "default" (last values)))))

(def host (.read_text (.joinpath u/root "seed/bench/host-arm.kotoba")))
(def reference (json/loads (.read_text (.joinpath u/root "bench/embench/reproduce-20261015/round-sa-m104-20261015/records/round/expected-accounting-mw.json"))))

(deftest exact-factory-bindings
  (let [factory (.read_text (.joinpath u/root "seed/79-native-cdci.kotoba"))]
    (doseq [path ["seed/bench/host-arm.kotoba" "seed/bench/registry-arm.kotoba"]]
      (is (= 1 (.count factory (u/sha256-hex (.read_bytes (.joinpath u/root path)))))))
    (is (not (str/includes? (form factory "xc-role-hash") "bench")))))

(deftest fixed-fuel-tables
  (let [tables (vec (re/findall "\\(case id[^()]*\\)" (form host "kb-expected-fuel")))]
    (is (= 2 (count tables)))
    (doseq [[table field] (map vector tables ["verifyFuel" "benchmarkFuel"])]
      (let [actual (cases table)]
        (is (= 20 (count actual)))
        (is (= (mapv #(u/geti (u/geti % "expectedSample") field) reference) (mapv #(get actual %) (range 19))))
        (is (= -1 (get actual "default")))))))

(deftest fixed-arena-tables
  (let [tables (vec (re/findall "([0-9]+) (\\(case id[^()]*\\))" (form host "kb-expected-arena")))
        actual (into {} (for [[field table] tables] [(python/int field) (cases table)]))]
    (is (= #{0 2 3 4} (set (keys actual))))
    (doseq [[i row] (map-indexed vector reference)]
      (let [fields (mapv python/int (re/findall ":[a-z-]+ ([0-9]+)" (u/geti row "expectedStderr")))]
        (is (= 17 (count fields)))
        (is (= fields (mapv (fn [f] (if (contains? actual f) (get (get actual f) i (get (get actual f) "default")) 0)) (range 17))))))))

(deftest mutations-are-closed-and-preserve-oracle
  (let [mutants (lib/mutations host)]
    (is (= 13 (count mutants)))
    (is (= (count mutants) (count (set (map first mutants)))))
    (is (= (count mutants) (count (set (map #(nth % 3) mutants)))))
    (doseq [[name _ refusal source] mutants]
      (is (not= source host) name)
      (is (pos? refusal) name)
      (doseq [f ["kb-accounting" "kb-expected-fuel" "kb-expected-arena"]]
        (is (= (form host f) (form source f)) (str name " " f))))))

(defn base-row []
  (u/pydict "schema" "KOTOBA_NATIVE_BENCH_CANDIDATE_V1" "workloadId" 1 "iterations" 2785280 "diagnostic" 0 "elapsedNs" 1
            "benchmarkFuel" 5709824002 "verifyFuel" 0 "warmSeed" 0 "highwaterAfterReset" 0 "highwaterAfterVerify" 0
            "benchmarkArena" (python/list (repeat 17 0)) "finalArena" (python/list (repeat 17 0)) "result" 1 "warmupBodies" 1
            "calls" 1 "verifyOutsideTiming" true "sameContextVerify" true "resetIncluded" false "performanceQualified" false))

(defn valid [row] (lib/valid-observation row 1 2785280 0))
(defn with-field [row k v] (let [r (python/dict row)] (operator/setitem r k v) r))

(deftest native-record-shape
  (is (valid (base-row)))
  (doseq [[field value] [["workloadId" true] ["iterations" 2785280.0] ["diagnostic" 1] ["result" true] ["calls" true] ["elapsedNs" -1]
                         ["benchmarkFuel" "5709824002"] ["verifyOutsideTiming" 1] ["performanceQualified" true]
                         ["finalArena" (python/list (repeat 16 0))] ["finalArena" (python/list (repeat 17 false))]]]
    (is (not (valid (with-field (base-row) field value))) (str field " " value)))
  (is (not (valid (with-field (base-row) "unexpected" 0))))
  (let [r (base-row)] (.pop r "warmSeed") (is (not (valid r)))))

(deftest duplicate-fields-refuse
  (is (thrown? python/ValueError (json/loads "{\"result\":0,\"result\":1}" ** :object_pairs_hook lib/unique-fields))))
