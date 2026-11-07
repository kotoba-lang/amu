;; Partition process argv only; all original native gates remain mandatory on main (on a pull request the x86 copies of
;; the gates that also run on arm64 are deferred to main, JUN-629).
;; Ported from native_gate_shard.py (Basilisp). Plans and receipts are Python dicts so JSON layout and equality
;; match the original exactly.
;; Run: basilisp run scripts/seed/native_gate_shard.cljc -- --manifest M (--shard S --output O | --verify-root R --workflow-result X --output O [--tier T])
(ns native-gate-shard
  (:require [basilisp.string :as str]
            [gate-util :as u])
  (:import copy hashlib json operator pathlib sys))

(def shards
  (u/pydict "core" (python/tuple ["native-cdci" "aiueos-projects" "zero-watermark" "live-abi"
                                  "kototama-receipt" "b2-image" "kototama-i64" "b2-libc"
                                  "fs2-x86" "aiueos-boot" "clock-entropy" "aiueos-image"])
            "extensions" (python/tuple ["kernel-memory" "flock-vector" "kototama-cache-abi" "kototama-cache-host"])
            "x86-dupes" (python/tuple ["label-proof-index" "runtime-profile" "ccf-filter"])))

;; JUN-629 (owner decision 2026-10-30): on a pull request the x86 copies of these three gates are deferred to main.
;; Each also runs in the arm64 phase of the same plan on every pull request, and verify refuses the deferral unless it
;; still does. Main, the schedule and a manual dispatch run all nineteen x86 gates, as before.
(def deferred-on-pr ["x86-dupes"])
(def tiers ["pr" "main" "full"])

(defn- value-error [m] (python/ValueError m))
(defn- shard-names [shard] (vec (u/geti shards shard)))
(defn- all-shard-names [] (vec (mapcat shard-names (python/list shards))))
(defn- string-arg? [x] (instance? python/str x))

(defn select [plan shard]
  (when (or (not= "amu.native-gate-plan.v1" (.get plan "schema")) (not (operator/contains shards shard)))
    (throw (value-error "unknown native gate plan or shard")))
  (let [rows (python/list (u/geti (u/geti plan "phases") "x86"))
        names (mapv #(u/geti % "name") rows)
        expected (all-shard-names)]
    (when (or (not= (count (set expected)) (count expected)) (not= (count (set names)) (count names)))
      (throw (value-error "duplicate native gate")))
    (when (not= (set names) (set expected))
      (throw (value-error "native gate partition is incomplete or stale")))
    (when (some #(or (not (seq (u/geti % "argv"))) (not (every? string-arg? (u/geti % "argv")))) rows)
      (throw (value-error "invalid original native argv")))
    (let [original (into {} (map (fn [row] [(u/geti row "name") row])) rows)
          ;; Preserve every complete row and argv token. No shell/option rewriting, fixture filtering, cached
          ;; verdict or resource-profile change is allowed.
          selected (json/loads (json/dumps (python/list (for [n (shard-names shard)] (get original n)))))]
      (u/pydict "schema" (u/geti plan "schema") "baseline" (u/geti plan "baseline") "phases" (u/pydict "x86" selected)))))

(defn main [manifest shard output]
  (let [raw (.read_bytes manifest)
        source (json/loads raw)
        selected (select source shard)]
    (with-open [stream (.open output "x")]
      (.write stream (str (json/dumps selected ** :indent 2) "\n")))
    (let [coverage (u/pydict "schema" "amu.native-gate-partition.v1" "sourceManifest" (.as_posix manifest)
                             "sourceManifestSHA256" (u/sha256-hex raw) "shard" shard
                             "temporaryRoot" (.as_posix (.-parent output))
                             "allPartitions" shards
                             "selected" (python/list (map #(u/geti % "name") (u/geti (u/geti selected "phases") "x86")))
                             "originalArgvPreserved" true "nativeVerdictAuthority" false "qualificationReplacement" false)]
      (.write_text (.with_suffix output ".coverage.json") (str (json/dumps coverage ** :indent 2) "\n")))))

(defn verify
  ([manifest root workflow-result] (verify manifest root workflow-result "full"))
  ([manifest root workflow-result tier]
   ;; Native schedules alone do not cover the runtime/browser checks before and after them. A failed shard job
   ;; must fail the legacy aggregate check.
   (when (not= workflow-result "success") (throw (value-error "native qualification shard job did not succeed")))
   (when-not (contains? (set tiers) tier) (throw (value-error "unknown tier")))
   (let [raw (.read_bytes manifest)
         original (json/loads raw)
         deferred (if (= tier "pr") (vec (mapcat shard-names deferred-on-pr)) [])
         arm64 (set (map #(u/geti % "name") (.get (u/geti original "phases") "arm64" (python/list))))
         _ (when (some #(not (contains? arm64 %)) deferred)
             (throw (value-error "a gate deferred to main does not run in the arm64 phase")))
         required (vec (for [shard (python/list shards) :when (not (and (= tier "pr") (some #{shard} deferred-on-pr)))] shard))
         raw-digest (u/sha256-hex raw)
         seen (atom []) capacities (atom #{})]
     (doseq [shard required]
       (let [folder (.joinpath root shard)
             coverage (json/loads (.read_text (.joinpath folder "x86-shard-plan.coverage.json")))
             staged (json/loads (.read_text (.joinpath folder "x86-shard-plan.json")))
             schedule (json/loads (.read_text (.joinpath folder "pg-x86/schedule.json")))
             expected (select original shard)]
         (when (or (not= raw-digest (u/geti coverage "sourceManifestSHA256")) (not= shard (u/geti coverage "shard"))
                   (not (u/deq staged expected)))
           (throw (value-error "changed native gate source or partition")))
         ;; A runner schedules at most its vCPU count: 2 (the original bounded runner) or 4 (JUN-629, the 4-vCPU CI
         ;; runner), with jobs equal to the capacity. Scheduling only: every gate below still runs with its original argv.
         (when (or (not= "COMPLETED" (u/geti schedule "status")) (not= 0 (u/geti schedule "exit"))
                   (not (contains? #{2 4} (u/geti schedule "capacity"))) (not= (u/geti schedule "jobs") (u/geti schedule "capacity")))
           (throw (value-error "native gate shard did not complete at a bounded capacity (2 or 4)")))
         (swap! capacities conj (u/geti schedule "capacity"))
         (let [rows (python/list (u/geti schedule "gates"))
               names (mapv #(u/geti % "name") rows)]
           (when (or (not= (count (set names)) (count names)) (not= (set names) (set (shard-names shard))))
             (throw (value-error "missing or duplicate executed native gate")))
           (let [by-name (into {} (map (fn [row] [(u/geti row "name") row])) (u/geti (u/geti expected "phases") "x86"))]
             (doseq [row rows]
               (let [argv (python/list (map #(.replace % "@TEMP@" (u/geti coverage "temporaryRoot")) (u/geti (get by-name (u/geti row "name")) "argv")))]
                 (when (or (not= 0 (u/geti row "exit")) (not (u/deq (u/geti row "argv") argv)))
                   (throw (value-error "refused native gate or changed original argv"))))))
           (swap! seen into names))))
     (when (or (not= 19 (+ (count @seen) (count deferred))) (not= 19 (count (set (concat @seen deferred)))))
       (throw (value-error "incomplete native x86 qualification")))
     (u/pydict "schema" "amu.native-gate-partition-review.v1" "status" "PASS" "tier" tier "executedGates" (count @seen)
               "deferredToMain" (python/list deferred) "deferredGatesRunOnArm64" (boolean (seq deferred))
               "originalArgvPreserved" true "capacityPerRunner" (apply max @capacities) "nativeVerdictAuthority" false
               "qualificationReplacement" false))))

(defn- usage-error [message] (.write sys/stderr (str "native_gate_shard: error: " message "\n")) (sys/exit 2))

(defn -main [& args]
  (let [manifest (u/opt args "--manifest") shard (u/opt args "--shard") output (u/opt args "--output")
        verify-root (u/opt args "--verify-root") workflow-result (u/opt args "--workflow-result")
        tier (or (u/opt args "--tier") "full")]
    (when-not manifest (usage-error "the following arguments are required: --manifest"))
    (when (and shard (not (operator/contains shards shard))) (usage-error (str "argument --shard: invalid choice: " shard)))
    (when-not (contains? (set tiers) tier) (usage-error (str "argument --tier: invalid choice: " tier)))
    (let [manifest (pathlib/Path manifest) output (when output (pathlib/Path output))]
      (if verify-root
        (do (when (or shard (not output) (not workflow-result))
              (usage-error "verification requires --verify-root, --workflow-result and --output"))
            (.write_text output (str (json/dumps (verify manifest (pathlib/Path verify-root) workflow-result tier) ** :indent 2) "\n")))
        (do (when (or (not shard) (not output) workflow-result)
              (usage-error "staging requires only --shard and --output"))
            (main manifest shard output))))))

(when (some #(or (= % "native_gate_shard.cljc") (str/ends-with? % "/native_gate_shard.cljc")) sys/argv)
  (apply -main *command-line-args*))
