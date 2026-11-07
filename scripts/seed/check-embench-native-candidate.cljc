;; Stage original full19 through a native candidate, not a timing campaign.
;;
;; Amu alone compiles/links/extracts every payload and builds the native runner. Basilisp stages exact
;; bytes/locks, observes processes and compares old reference records. No result here qualifies performance,
;; adoption or external validation.
;; Ported from check-embench-native-candidate.py (Basilisp). The pure helpers live in embench_candidate_lib.cljc.
;; Run: basilisp run scripts/seed/check-embench-native-candidate.cljc -- (--one DIR | --complete DIR) --output OUT
;;        --runtime-profile standard-v1|large-vectors-v1 [--iteration-profile one-body|m104-counts] [--wall-seconds N]
;;        [--package DIR] [--entry FILE]
(ns check-embench-native-candidate
  (:require [basilisp.string :as str]
            [embench-candidate-lib :refer [pin elf arena entry-offset verify-bundle-data provenance]]
            [gate-util :as u]
            [native-profile :as profile])
  (:import json operator os pathlib platform re struct subprocess sys time))

(defn- sorted-names [coll] (vec (sort coll)))

(defn main [args]
  (let [{:keys [one complete package entry output runtime-profile iteration-profile wall-seconds]} args
        [compiler machine target receipt sources] (provenance one complete)
        root u/root
        package (.resolve package) entry (.resolve entry) out (.resolve output)
        _ (verify-bundle-data package entry)
        table-path (.joinpath package "round-sa-m104-20261015/expected/measured-images.json")
        count-path (.joinpath package "round-sa-m104-20261015/workloads.json")
        reference-path (.joinpath package "round-sa-m104-20261015/records/round/expected-accounting-mw.json")
        table (json/loads (.read_text table-path))
        counts (into {} (for [r (json/loads (.read_text count-path))] [(u/geti r "workload") (u/geti r "n")]))
        reference (into {} (for [r (json/loads (.read_text reference-path))] [(u/geti r "workload") r]))
        names (vec (python/list table))
        _ (u/chk (and (= 19 (count names)) (= (set names) (set (keys counts))) (= (set names) (set (keys reference)))))
        _ (u/chk (every? #(= (u/geti (get reference %) "n") (get counts %)) names))
        _ (.mkdir out ** :mode 0700 :parents true :exist_ok false)
        _ (.mkdir (.joinpath out "raw"))
        report (u/pydict "schema" "amu.embench.native-candidate-preparation.v1" "status" "running"
                         "performanceQualified" false "qualificationReplacement" false
                         "benchmarkVerifyFuelSeparatelyMeasured" false "publicProductAdopted" false
                         "host" (python/list [(platform/system) (platform/machine) (platform/release)])
                         "compiler" (elf compiler machine) "candidateReceipt" (pin receipt) "sources" sources
                         "observer" (pin (.joinpath root "scripts/seed/check-embench-native-candidate.cljc"))
                         "entryTemplate" (pin entry) "target" target "runtimeProfile" runtime-profile
                         "iterationProfile" iteration-profile "wallSeconds" wall-seconds "iterationTable" (pin count-path)
                         "originalSourceTable" (pin table-path) "historicalAccountingReference" (pin reference-path)
                         "route" (if (= machine 183) "adopted-core-locked-aarch64" "locked-x86-project")
                         "calls" (python/list)
                         "workloads" (python/list (for [n (sorted-names names)] (u/pydict "workload" n "status" "not-run"))))
        save (fn [] (profile/atomic-json (.joinpath out "observations.json") report))
        call (fn [name argv env & {:keys [timeout] :or {timeout 900}}]
               (let [logs {"stdout" (.joinpath (.joinpath out "raw") (str name ".stdout")) "stderr" (.joinpath (.joinpath out "raw") (str name ".stderr"))}
                     start (time/monotonic)
                     timed-out (atom false)
                     usage (atom nil)]
                 (with-open [stdout (.open (get logs "stdout") "xb") stderr (.open (get logs "stderr") "xb")]
                   (let [process (subprocess/Popen (python/list (map str argv)) ** :cwd out :env env :stdout stdout :stderr stderr)]
                     (loop []
                       (let [[pid status u] (vec (os/wait4 (.-pid process) os/WNOHANG))]
                         (cond
                           (not (zero? pid)) (do (set! (.-returncode process) (os/waitstatus_to_exitcode status)) (reset! usage u))
                           (> (- (time/monotonic) start) timeout)
                           (do (reset! timed-out true) (.kill process)
                               (let [[_ status u] (vec (os/wait4 (.-pid process) 0))]
                                 (set! (.-returncode process) (os/waitstatus_to_exitcode status))
                                 (reset! usage u)))
                           :else (do (time/sleep 0.05) (recur)))))
                     (let [row (u/pydict "name" name "argv" (python/list (map str argv)) "exit" (.-returncode process)
                                         "observerTimeout" @timed-out "seconds" (- (time/monotonic) start)
                                         "cpuSeconds" (+ (.-ru_utime @usage) (.-ru_stime @usage)) "maxRSSKiB" (.-ru_maxrss @usage))]
                       (doseq [s ["stdout" "stderr"]]
                         (operator/setitem row s (let [d (u/pydict "path" (.as_posix (.relative_to (get logs s) out)))]
                                                   (.update d (pin (get logs s))) d)))
                       (.append (u/geti report "calls") row)
                       (save)
                       (println name (.-returncode process))
                       (.flush sys/stdout)
                       [(.-returncode process) (.read_bytes (get logs "stdout")) (.read_bytes (get logs "stderr"))])))))
        _ (save)
        compile-env (python/dict {"PATH" "/nonexistent" "KEXE_ALLOW" "35,37,38,39" "KEXE_CAP_RESOURCES_35" (str out) "KEXE_STACK_BYTES" "8388608"})
        runner-source (.joinpath out "runner.kotoba")
        _ (.write_bytes runner-source (.read_bytes (.joinpath root "seed/x86_64-kx64-runner.kotoba")))
        runner (.joinpath out "runner.elf")
        fmt (if (= machine 183) "runner" "kx64-runner")
        [code stdout stderr] (call "runner-build" [compiler "compile" runner-source "--target" target "--output" runner "--format" fmt
                                                   "--runtime-profile" runtime-profile] compile-env)]
    (if (or (not (zero? code)) (u/nonempty? stderr) (not (.is_file runner)))
      (do (operator/setitem report "status" "rejected-runner-build") (save) 2)
      (do
        (u/chk (u/has-bytes? (.encode (str ":runtime-profile :" runtime-profile)) stdout))
        (.chmod runner 0700)
        (operator/setitem report "runner" (u/pydict "source" (pin runner-source) "image" (elf runner machine)))
        (doseq [row (python/list (u/geti report "workloads"))]
          (let [name (u/geti row "workload")
                original (.joinpath (.joinpath package "ports") (str "official-" name ".kotoba"))
                _ (u/chk (= (u/geti (pin original) "sha256") (u/geti (u/geti table name) "sourceSHA256")))
                namespace (re/match (.encode "\\(ns ([a-z0-9.-]+) ") (.read_bytes original))
                _ (u/chk namespace)
                module (.decode (.group namespace 1))
                src-root (.joinpath (.joinpath out name) "src")
                library (.joinpath src-root (str (.replace (.replace module "." "/") "-" "_") ".kotoba"))
                _ (.mkdir (.-parent library) ** :parents true)
                _ (.write_bytes library (.read_bytes original))
                source (.joinpath src-root "proof/native_entry.kotoba")
                _ (.mkdir (.-parent source))
                n (if (= iteration-profile "one-body") 1 (get counts name))
                _ (.write_bytes source (-> (.read_bytes entry)
                                           (.replace (.encode "[embench.workload :as") (operator/add (operator/add (.encode "[") (.group namespace 1)) (.encode " :as")))
                                           (.replace (.encode "(workload/bench-verify 1)") (.encode (str "(workload/bench-verify " n ")")))))
                lock (.joinpath out (str name ".ksl"))
                _ (.write_text lock (str "KSL1\nentry " source "\nroot " src-root "\n"
                                         (apply str (for [p (sort-by str [library source])] (str "file " (u/geti (pin p) "sha256") " " p "\n")))))
                image (.joinpath out (str name ".container")) payload (.joinpath out (str name ".bin"))
                _ (doseq [[k v] [["iterations" n] ["originalSource" (pin original)] ["stagedSource" (pin library)]
                                 ["entry" (pin source)] ["sourceLock" (pin lock)] ["status" "building"]]]
                    (operator/setitem row k v))
                flags ["--source-path" src-root "--source-lock" lock "--source-lock-sha256" (u/geti (pin lock) "sha256")]
                argv (concat [compiler "compile" source "--target" (if (= machine 183) "aarch64-macos" target) "--output" image]
                             (if (= machine 183) ["--no-crypto-hw"] ["--format" "kx64-v1"]) flags)
                [code _ stderr] (call (str name "-compile") argv compile-env)]
            (if (or (not (zero? code)) (u/nonempty? stderr) (not (.is_file image)))
              (do (operator/setitem row "status" "rejected-native-compile") (save))
              (let [offset
                    (if (= machine 183)
                      (let [[code extracted stderr] (call (str name "-extract") [compiler "extract-native" image "--symbol" "main" "--output" payload] compile-env)]
                        (if (or (not (zero? code)) (u/nonempty? stderr) (not (.is_file payload)))
                          (do (operator/setitem row "status" "rejected-native-extract") (save) nil)
                          (entry-offset extracted payload)))
                      (let [[header raw] (vec (.split (.read_bytes image) (.encode "\n\n") 1))
                            match (re/fullmatch (.encode "KX64V1 x86_64-linux sysv-ctx-v11 ([0-9]+) 0") header)]
                        (u/chk (and match (= (python/len raw) (python/int (.group match 1))) (= 0xe9 (u/geti raw 0))))
                        (.write_bytes payload raw)
                        0))]
                (when (some? offset)
                  (doseq [[k v] [["image" (pin image)] ["payload" (pin payload)] ["entryOffset" offset] ["status" "running"]]]
                    (operator/setitem row k v))
                  (save)
                  (let [env (python/dict {"PATH" "/nonexistent" "KEXE_ALLOW" "-" "KEXE_FUEL" "1000000000000" "KEXE_STRUCTURED_REPORT" "1"
                                          "KEXE_ARENA_USE" "1" "KEXE_WALL_SECONDS" (str wall-seconds)})
                        [code stdout stderr] (call (str name "-run") [runner payload (str offset) "0" (if (= machine 183) "aarch64" "x86_64") "-"] env
                                                   :timeout (+ wall-seconds 15))
                        result (re/fullmatch (.encode "\\{:status :ok :result 1 :fuel \\{:initial ([0-9]+) :remaining ([0-9]+)\\}\\}\n") stdout)
                        counters (arena stderr)
                        valid (and (some? result) (= (python/int (.group result 1)) 1000000000000)
                                   (<= 0 (python/int (.group result 2)) (python/int (.group result 1))))
                        fuel (when valid (- (python/int (.group result 1)) (python/int (.group result 2))))
                        expected (get reference name)
                        sample (u/geti expected "expectedSample")
                        predicted (+ (u/geti sample "benchmarkFuel") (u/geti sample "verifyFuel") 2)
                        full (= n (get counts name))]
                    (doseq [[k v] [["status" (if (and (zero? code) valid (some? counters)) "native-result-one" "rejected-native-execution")]
                                   ["resultOne" (and (zero? code) valid)] ["arena" counters] ["totalFuel" fuel]
                                   ["finalArenaMatchesReference" (when full (u/deq counters (arena (.encode (u/geti expected "expectedStderr")))))]
                                   ["predictedTotalFuelWithAdapter" (when full predicted)]
                                   ["totalFuelMatchesAdapterPrediction" (when full (= fuel predicted))]]]
                      (operator/setitem row k v))
                    (save)))))))
        (u/chk (every? (fn [[p v]] (u/deq (pin (.joinpath root p)) v)) (.items sources)))
        (let [rows (python/list (u/geti report "workloads"))
              passed (count (filter #(= "native-result-one" (.get % "status")) rows))
              arena-count (count (filter #(true? (.get % "finalArenaMatchesReference")) rows))
              fuel-count (count (filter #(true? (.get % "totalFuelMatchesAdapterPrediction")) rows))]
          (doseq [[k v] [["status" "completed-diagnostic-only"] ["nativeResultOneCount" passed]
                         ["all17ArenaReferenceMatchCount" arena-count] ["adapterFuelPredictionMatchCount" fuel-count]]]
            (operator/setitem report k v))
          (save)
          (if (and (= 19 passed) (or (= iteration-profile "one-body") (= 19 arena-count fuel-count))) 0 2))))))

(defn- parse [args]
  (let [one (u/opt args "--one") complete (u/opt args "--complete")
        output (u/opt args "--output") rp (u/opt args "--runtime-profile")
        ip (or (u/opt args "--iteration-profile") "m104-counts")
        ws (python/int (or (u/opt args "--wall-seconds") "300"))]
    (when (= (nil? one) (nil? complete)) (sys/exit "exactly one of --one/--complete is required"))
    (when-not output (sys/exit "--output is required"))
    (when-not (contains? #{"standard-v1" "large-vectors-v1"} rp) (sys/exit "--runtime-profile must be standard-v1 or large-vectors-v1"))
    (when-not (contains? #{"one-body" "m104-counts"} ip) (sys/exit "invalid --iteration-profile"))
    (when-not (<= 1 ws 600) (sys/exit "--wall-seconds must be 1..600"))
    {:one (when one (.resolve (pathlib/Path one))) :complete (when complete (.resolve (pathlib/Path complete)))
     :output (pathlib/Path output) :runtime-profile rp :iteration-profile ip :wall-seconds ws
     :package (pathlib/Path (or (u/opt args "--package") (str (.joinpath u/root "bench/embench/reproduce-20261015"))))
     :entry (pathlib/Path (or (u/opt args "--entry") (str (.joinpath u/root "bench/embench/proof-v1/native-entry.kotoba"))))}))

(defn -main [& args]
  (let [parsed (parse args)]
    (try (sys/exit (main parsed))
         (catch python/Exception error
           (let [path (.joinpath (.resolve (:output parsed)) "observations.json")]
             (when (.is_file path)
               (let [report (json/loads (.read_text path))]
                 (.update report (python/dict {"status" "rejected-observer" "error" (str (.-__name__ (python/type error)) ": " error)}))
                 (profile/atomic-json path report))))
           (throw error)))))

(when (some #(or (= % "check-embench-native-candidate.cljc") (str/ends-with? % "/check-embench-native-candidate.cljc")) sys/argv)
  (apply -main *command-line-args*))
