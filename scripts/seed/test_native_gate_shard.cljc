;; Coverage/refusal checks for scheduling metadata, never native semantics.
;; Ported from test_native_gate_shard.py. Run from the repo root:
;;   PYTHONPATH=scripts/seed basilisp test -p no:cacheprovider --rootdir scripts/seed scripts/seed/test_native_gate_shard.cljc
(ns test-native-gate-shard
  (:require [basilisp.test :refer [deftest is]]
            [gate-util :as u]
            [native-gate-shard :as S])
  (:import copy json operator pathlib tempfile))

(def plan-path (.joinpath u/root "seed/native-gate-plan.json"))
(defn load-plan [] (json/loads (.read_text plan-path)))
(defn x86 [plan] (u/geti (u/geti plan "phases") "x86"))
(defn shard-names [] (vec (python/list S/shards)))
(defn select-x86 [plan shard] (python/list (x86 (S/select plan shard))))
(defn write-json [p v] (.write_text p (json/dumps v)))

(deftest complete-disjoint-partition-preserves-every-original-argv
  (let [plan (load-plan)
        before (copy/deepcopy plan)
        original (into {} (map (fn [row] [(u/geti row "name") row])) (x86 plan))
        selected (vec (mapcat #(select-x86 plan %) (shard-names)))]
    (is (= 19 (count selected)))
    (is (= 19 (count (set (map #(u/geti % "name") selected)))))
    (is (every? (fn [row] (u/deq row (get original (u/geti row "name")))) selected))
    (is (u/deq plan before))
    (.append (u/geti (first selected) "argv") "--invalid-test-token")
    (is (u/deq plan before))))

(deftest missing-gate-refuses-both-partitions
  (let [plan (load-plan)]
    (.pop (x86 plan))
    (doseq [shard (shard-names)]
      (is (thrown-with-msg? python/ValueError #"incomplete" (S/select plan shard))))))

(deftest duplicate-gate-cannot-be-hidden-by-name-lookup
  (let [plan (load-plan)]
    (.append (x86 plan) (copy/deepcopy (u/geti (x86 plan) 0)))
    (is (thrown-with-msg? python/ValueError #"duplicate" (S/select plan "core")))))

(deftest new-gate-requires-explicit-partition-update
  (let [plan (load-plan)]
    (.append (x86 plan) (u/pydict "name" "new-mandatory-gate" "argv" (python/list ["native"])))
    (is (thrown-with-msg? python/ValueError #"incomplete" (S/select plan "extensions")))))

(deftest unknown-shard-and-schema-refuse
  (let [plan (load-plan)]
    (is (thrown? python/ValueError (S/select plan "skip")))
    (operator/setitem plan "schema" "unknown")
    (is (thrown? python/ValueError (S/select plan "core")))))

(deftest staging-records-exact-source-and-never-overwrites
  (with-open [temporary (tempfile/TemporaryDirectory)]
    (let [output (.joinpath (pathlib/Path temporary) "plan.json")]
      (S/main plan-path "core" output)
      (is (u/deq (json/loads (.read_text output)) (S/select (load-plan) "core")))
      (let [coverage (json/loads (.read_text (.with_suffix output ".coverage.json")))]
        (is (= (vec (u/geti S/shards "core")) (vec (u/geti coverage "selected"))))
        (is (false? (u/geti coverage "nativeVerdictAuthority"))))
      (is (thrown? python/FileExistsError (S/main plan-path "core" output))))))

(defn proofs
  ([root] (proofs root 2 nil))
  ([root capacity shards]
   (doseq [shard (or shards (shard-names))]
     (let [folder (.joinpath root shard)]
       (.mkdir (.joinpath folder "pg-x86") ** :parents true)
       (S/main plan-path shard (.joinpath folder "x86-shard-plan.json"))
       (let [rows (copy/deepcopy (python/list (x86 (S/select (load-plan) shard))))]
         (doseq [row rows]
           (operator/setitem row "argv" (python/list (map #(.replace % "@TEMP@" (str folder)) (u/geti row "argv"))))
           (operator/setitem row "exit" 0))
         (write-json (.joinpath folder "pg-x86/schedule.json")
                     (u/pydict "status" "COMPLETED" "exit" 0 "jobs" capacity "capacity" capacity "gates" rows)))))))

(defmacro with-root [[sym] & body]
  `(with-open [temporary# (tempfile/TemporaryDirectory)]
     (let [~sym (pathlib/Path temporary#)] ~@body)))

(deftest join-accepts-all-nineteen-original-process-records
  (with-root [root]
    (proofs root)
    (let [result (S/verify plan-path root "success")]
      (is (= 19 (u/geti result "executedGates")))
      (is (false? (u/geti result "qualificationReplacement"))))))

(deftest join-accepts-the-four-vcpu-runner-capacity
  (with-root [root]
    (proofs root 4 nil)
    (let [result (S/verify plan-path root "success")]
      (is (= [19 4] [(u/geti result "executedGates") (u/geti result "capacityPerRunner")])))))

(deftest join-refuses-an-unbounded-capacity
  (doseq [capacity [1 3 8]]
    (with-root [root]
      (proofs root capacity nil)
      (is (thrown? python/ValueError (S/verify plan-path root "success")) capacity))))

(deftest pull-request-tier-defers-only-the-arm64-duplicates
  (with-root [root]
    (proofs root 2 ["core" "extensions"])
    (let [result (S/verify plan-path root "success" "pr")]
      (is (= 16 (u/geti result "executedGates")))
      (is (= (sort (vec (u/geti S/shards "x86-dupes"))) (sort (vec (u/geti result "deferredToMain")))))
      ;; main and full still require all nineteen
      (doseq [tier ["main" "full"]]
        (is (thrown? python/Exception (S/verify plan-path root "success" tier)) tier)))))

(deftest pull-request-tier-refuses-a-deferral-arm64-no-longer-covers
  (with-root [root]
    (let [plan (load-plan)
          phases (u/geti plan "phases")
          _ (operator/setitem phases "arm64" (python/list (filter #(not= "ccf-filter" (u/geti % "name")) (u/geti phases "arm64"))))
          manifest (.joinpath root "plan.json")]
      (.write_text manifest (str (json/dumps plan) "\n"))
      (is (thrown-with-msg? python/ValueError #"arm64" (S/verify manifest root "success" "pr"))))))

(deftest join-refuses-a-missing-execution-despite-success-header
  (with-root [root]
    (proofs root)
    (let [path (.joinpath root "core/pg-x86/schedule.json")
          data (json/loads (.read_text path))]
      (.pop (u/geti data "gates"))
      (write-json path data)
      (is (thrown-with-msg? python/ValueError #"missing" (S/verify plan-path root "success"))))))

(deftest join-refuses-failed-gate-or-changed-argv
  (doseq [[field value] [["exit" 7] ["argv" (python/list ["native" "--skip-refusals"])]]]
    (with-root [root]
      (proofs root)
      (let [path (.joinpath root "extensions/pg-x86/schedule.json")
            data (json/loads (.read_text path))]
        (operator/setitem (u/geti (u/geti data "gates") 0) field value)
        (write-json path data)
        (is (thrown-with-msg? python/ValueError #"refused" (S/verify plan-path root "success")) field)))))

(deftest join-refuses-source-manifest-drift
  (with-root [root]
    (proofs root)
    (let [manifest (.joinpath root "changed-source.json")]
      (.write_text manifest (str (json/dumps (load-plan)) "\n"))
      (is (thrown-with-msg? python/ValueError #"changed" (S/verify manifest root "success"))))))

(deftest post-gate-runtime-or-browser-failure-cannot-pass-aggregate
  (with-root [root]
    (proofs root)
    (doseq [result ["failure" "cancelled" "skipped" nil]]
      (is (thrown-with-msg? python/ValueError #"job did not succeed" (S/verify plan-path root result)) (str result)))))
