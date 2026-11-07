;; Same-host native whole-core comparison; no qualification substitution.
;;
;; The admitted public image builds both C0 variants. Original core18 and the same lock are fed to each
;; variant. Both cold compiler algorithms run; there is no result cache. This script only stages Git bytes and
;; observes processes. Ported from compare-proof-scans.py (Basilisp, JUN-974). Linux x86_64 only.
;; Run: basilisp run -p scripts/seed scripts/seed/compare-proof-scans.cljc -- --baseline-revision REV --output DIR
(ns compare-proof-scans
  (:require [basilisp.string :as str]
            [gate-util :as u])
  (:import json operator os pathlib platform resource statistics subprocess sys time))

(defn pin [p]
  (let [b (.read_bytes (pathlib/Path p))]
    (u/pydict "bytes" (python/len b) "sha256" (u/sha256-hex b))))

(defn main [output revision]
  (u/chk (and (= "Linux" (platform/system)) (= "x86_64" (platform/machine))))
  (.mkdir output ** :parents false :exist_ok false)
  ;; a single admitted CPU for both variants, with no parallel compilation
  (let [root u/root
        affinity (python/sorted ((python/getattr os "sched_getaffinity") 0))
        _ ((python/getattr os "sched_setaffinity") 0 (python/set [(first affinity)]))
        cpuinfo (.read_text (pathlib/Path "/proc/cpuinfo"))
        metadata (u/pydict "kernel" (platform/release) "machine" (platform/machine) "cpus" (os/cpu_count)
                           "allowedCPUs" affinity "selectedCPU" (first affinity)
                           "cpuModel" (first (filter #(.startswith % "model name") (.splitlines cpuinfo)))
                           "cgroup" (u/pydict))
        _ (doseq [path ["/sys/fs/cgroup/cpu.max" "/sys/fs/cgroup/cpu.stat" "/sys/fs/cgroup/memory.max"]]
            (let [p (pathlib/Path path)]
              (when (.exists p) (operator/setitem (u/geti metadata "cgroup") path (.read_text p)))))
        old (fn [path]
              (.-stdout (subprocess/run (python/list ["git" "show" (str revision ":" path)]) ** :cwd root :check true :capture_output true)))
        paths (fn [manifest] (vec (filter #(and (seq %) (not (.startswith % "#"))) (.splitlines (.decode (old manifest))))))
        corepaths (paths "seed/MANIFEST")
        staticpaths (paths "seed/CORE-STATIC-MANIFEST")
        _ (u/chk (= 18 (count corepaths) (count staticpaths)))
        source (.joinpath output "core.kotoba")
        _ (.write_bytes source (.join (u/bytes-of) (python/list (for [p corepaths] (operator/add (old p) (.encode "\n"))))))
        corepin (pin source)
        policy (json/loads (.decode (old "seed/cdci/policy.json")))
        _ (u/chk (= (u/geti corepin "sha256") (u/geti policy "coreSourceSHA256")))
        lock (.joinpath output "core.ksl")
        _ (.write_text lock (str "KSL1\nentry " source "\nfile " (u/geti corepin "sha256") " " source "\n"))
        producer (.joinpath root "bin/amu-linux-x86_64")
        report (u/pydict "schema" "amu.native-proof-scan-comparison.v1" "qualificationReplacement" false
                         "candidateAdopted" false "host" metadata "baselineRevision" revision "producer" (pin producer)
                         "input" corepin "lock" (pin lock) "sourceBindings" (u/pydict) "calls" (python/list)
                         "targetSeconds" 600 "coldCompile" true)
        env (python/dict {"PATH" "/nonexistent" "KEXE_STACK_BYTES" "8388608" "KEXE_CAP_RESOURCES_35" (str output)})
        save (fn [] (.write_text (.joinpath output "observations.json") (u/json-dump report)))
        run (fn [name argv timeout]
              (let [started (time/monotonic)
                    before (resource/getrusage resource/RUSAGE_CHILDREN)
                    load (os/getloadavg)
                    stdout-path (.joinpath output (str name ".stdout"))
                    stderr-path (.joinpath output (str name ".stderr"))
                    out (.open stdout-path "wb")
                    err (.open stderr-path "wb")
                    r (try
                        (subprocess/run (python/list (map str argv)) ** :cwd output :env env :stdout out :stderr err :timeout timeout)
                        (finally (.close out) (.close err)))
                    after (resource/getrusage resource/RUSAGE_CHILDREN)
                    row (u/pydict "name" name "argv" (python/list (map str argv)) "exit" (.-returncode r)
                                  "seconds" (- (time/monotonic) started)
                                  "cpuSeconds" (- (+ (.-ru_utime after) (.-ru_stime after)) (.-ru_utime before) (.-ru_stime before))
                                  "loadStart" load "loadEnd" (os/getloadavg))]
                (.append (u/geti report "calls") row)
                (save)
                (println (json/dumps row))
                (.flush sys/stdout)
                (u/chk (and (zero? (.-returncode r)) (zero? (.-st_size (.stat stderr-path))))
                       (str name " " (.-returncode r) " " (.read_bytes stderr-path)))
                row))
        images (atom {})]
    (doseq [variant ["baseline" "candidate"]]
      (let [data (u/pydict-from (for [p staticpaths] [p (if (= variant "baseline") (old p) (.read_bytes (.joinpath root p)))]))
            _ (operator/setitem (u/geti report "sourceBindings") variant
                                (u/pydict-from (for [p staticpaths] [p (u/pydict "bytes" (python/len (u/geti data p)) "sha256" (u/sha256-hex (u/geti data p)))])))
            unit (.joinpath output (str variant ".kotoba"))
            _ (.write_bytes unit (.join (u/bytes-of) (python/list (for [p staticpaths] (operator/add (u/geti data p) (.encode "\n"))))))
            image (.joinpath output (str variant ".elf"))]
        (run (str "build-" variant) [producer "compile" unit "--target" "x86_64-linux" "--output" image "--format" "static"] 900)
        (.chmod image 0755)
        (swap! images assoc variant image)
        (operator/setitem report (str variant "Compiler") (pin image))))
    (u/chk (= ["seed/41-a64gen.kotoba"]
              (vec (filter #(not (u/deq (u/geti (u/geti (u/geti report "sourceBindings") "baseline") %)
                                        (u/geti (u/geti (u/geti report "sourceBindings") "candidate") %)))
                           staticpaths))))
    (doseq [[index variant] (map-indexed vector ["baseline" "candidate" "candidate" "baseline"])]
      (let [artifact (.joinpath output (str index "-" variant ".kseed"))
            row (run (str index "-" variant)
                     [(get @images variant) "compile" source "--target" "aarch64-macos" "--output" artifact
                      "--source-lock" lock "--source-lock-sha256" (u/geti (pin lock) "sha256")] 7200)]
        (operator/setitem row "artifact" (pin artifact))
        (u/chk (= (u/geti (u/geti row "artifact") "sha256") (u/geti policy "coreContainerSHA256"))
               (str "semantic drift " variant))
        (operator/setitem report "wholeCoreArtifactByteIdentical" true)
        (save)))
    (let [samples (u/pydict-from
                   (for [v ["baseline" "candidate"]]
                     [v (python/list (for [r (u/geti report "calls")
                                           :when (and (.isdigit (first (u/geti r "name"))) (.endswith (u/geti r "name") v))]
                                       (u/geti r "seconds")))]))
          ratio (/ (statistics/median (u/geti samples "candidate")) (statistics/median (u/geti samples "baseline")))]
      (.update report (u/pydict "status" "PASS_SAME_HOST_NATIVE_WHOLE_CORE_PARITY" "samples" samples
                                "candidateToBaselineRatio" ratio
                                "underTenMinutes" (every? #(<= % 600) (u/geti samples "candidate"))))
      (save)
      (println (u/geti report "status") ratio (u/geti report "underTenMinutes"))
      (.flush sys/stdout))))

(defn -main [& args]
  (main (.resolve (pathlib/Path (or (u/opt args "--output") (sys/exit "--output is required"))))
        (or (u/opt args "--baseline-revision") (sys/exit "--baseline-revision is required"))))

(when (some #(or (= % "compare-proof-scans.cljc") (str/ends-with? % "/compare-proof-scans.cljc")) sys/argv)
  (apply -main *command-line-args*))
