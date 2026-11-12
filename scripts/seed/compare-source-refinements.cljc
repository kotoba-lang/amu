;; Screen explicit implementation annotations, then compare B/C/C/B natively. This changes three source parameter
;; annotations, not the compiler algorithm. Every complete-prefix output must be byte-identical to the independently
;; qualified original image, and its semantic/refusal entry executes afresh. Stages fixed source edits and observes
;; processes; it infers no types. Ported from compare-source-refinements.py (Basilisp, JUN-974).
;; Run (Linux): basilisp run -p scripts/seed scripts/seed/compare-source-refinements.cljc -- --output DIR
;;      [--workload-file FILE]
(ns compare-source-refinements
  (:require [basilisp.string :as str]
            [gate-util :as u])
  (:import hashlib json operator os pathlib platform resource statistics struct subprocess sys time))

(def root u/root)
(defn rp [rel] (pathlib/Path root rel))
(defn g [m k] (operator/getitem m k))
(defn pin [p] (let [raw (.read_bytes (pathlib/Path p))] (u/pydict "bytes" (python/len raw) "sha256" (u/sha256-hex raw))))

(def annotations
  [["doctail" "(defn- ck-r6c-doctail [M :vector-i64 S c :i64]" "(defn- ck-r6c-doctail [M :vector-i64 S :string c :i64]"]
   ["dt" "(defn- ck-r6c-dt [M :vector-i64 S b :i64]" "(defn- ck-r6c-dt [M :vector-i64 S :string b :i64]"]
   ["lit" "(defn- ck-r6c-lit [M :vector-i64 S m :i64]" "(defn- ck-r6c-lit [M :vector-i64 S :string m :i64]"]])
(def source-sha "daa88291555eb738df9d0dd36a1a498d69d550eff89f97931318c20627fb5a8b")
(def input-revision "4abac3fd612de050fd7f7a4635deb80ca9a0cb73")
(def image-sha {"aarch64" "18c5b8d07c9722fb135127b81b1bb8389fe0b80eef13a06572bee38e4c17facc"
                "x86_64" "378fd3cd99fcd9951654612e2df4e2b055d00bf6c068c1b4eeec325325712591"})

(defn run [out workload-file]
  (u/chk (and (= (platform/system) "Linux") (contains? image-sha (platform/machine))) "Linux aarch64/x86_64 required")
  (let [host (platform/machine)
        aarch? (= host "aarch64")
        machine (if aarch? 183 62)
        word (fn [b] (first (struct/unpack_from "<H" b 18)))
        _ (u/chk (= (word (.read_bytes (pathlib/Path "/proc/self/exe"))) machine) "self machine")
        producer (rp (if aarch? "seed/bootstrap/aarch64-linux-static-root.elf" "bin/amu-linux-x86_64"))
        _ (u/chk (= (word (.read_bytes producer)) machine) "producer machine")
        _ (.mkdir out ** :parents true :exist_ok false)
        original (if workload-file
                   (.read_bytes (pathlib/Path workload-file))
                   (let [frozen (fn [path] (.-stdout (subprocess/run (python/list ["git" "show" (str input-revision ":" path)]) ** :cwd root :capture_output true :check true)))
                         paths (vec (filter #(and (seq %) (not (.startswith % "#"))) (.splitlines (.decode (frozen "seed/CORE-STATIC-MANIFEST")))))]
                     (operator/add (.join (u/bytes-of) (python/list (map #(operator/add (frozen %) (u/bytes-of 10)) (butlast paths))))
                                   (frozen "seed/tests/native-label-index.kotoba"))))
        _ (u/chk (= (u/sha256-hex original) source-sha) "workload digest")
        affinity (python/sorted (os/sched_getaffinity 0))
        _ (os/sched_setaffinity 0 (python/set [(operator/getitem affinity 0)]))
        report (u/pydict "schema" "amu.native-source-refinement-comparison.v1" "nativeVerdictAuthority" false
                         "qualificationReplacement" false "candidateAdopted" false "compilerAlgorithmChanged" false
                         "sourceWorkloadChanged" true "emulation" false "originalSourceSHA256" source-sha
                         "workloadRevision" input-revision "producer" (pin producer)
                         "host" (python/list [(platform/system) host (platform/release)])
                         "allowedCPUs" affinity "selectedCPU" (operator/getitem affinity 0) "variants" (python/dict) "calls" (python/list))
        cpuinfo (.read_text (pathlib/Path "/proc/cpuinfo"))
        write-report! (fn [] (.write_text (pathlib/Path out "observations.json") (u/json-dump report)))]
    (operator/setitem report "cpuModel" (or (first (filter #(.startswith % "model name") (.splitlines cpuinfo))) "unavailable"))
    (operator/setitem report "cgroup" (python/dict))
    (doseq [name ["cpu.max" "cpu.stat" "memory.max"]]
      (let [p (pathlib/Path "/sys/fs/cgroup" name)]
        (when (.exists p) (operator/setitem (g report "cgroup") name (.read_text p)))))
    (let [sources (atom {})]
      (doseq [variant ["baseline" "doctail" "dt" "lit" "all"]]
        (let [selected (cond (= variant "all") (mapv first annotations) (= variant "baseline") [] :else [variant])
              text (reduce (fn [text name]
                             (let [[_ old new] (first (filter #(= (first %) name) annotations))]
                               (u/chk (= (.count text old) 1) name)
                               (.replace text old new)))
                           (.decode original) selected)
              source (pathlib/Path out (str variant ".kotoba"))]
          (.write_text source text)
          (swap! sources assoc variant source)
          (operator/setitem (g report "variants") variant (u/pydict "source" (pin source) "explicitAnnotations" (python/list selected)))))
      (let [env (u/pydict "PATH" "/nonexistent" "KEXE_STACK_BYTES" "8388608" "KEXE_CAP_RESOURCES_35" (str out)
                          "KEXE_ALLOW" "35,37,38,39" "KEXE_FUEL" "10000000000" "KEXE_COMMAND" "1")
            target (if aarch? "aarch64-linux" "x86_64-linux")
            run-step (fn [name argv expected & [runtime-env]]
                       (let [started (time/monotonic)
                             before (resource/getrusage resource/RUSAGE_CHILDREN)
                             load- (os/getloadavg)
                             p (subprocess/run (python/list (map str argv)) ** :cwd out :env (or runtime-env env) :capture_output true :timeout 900)
                             after (resource/getrusage resource/RUSAGE_CHILDREN)]
                         (doseq [[stream raw] [["stdout" (.-stdout p)] ["stderr" (.-stderr p)]]]
                           (.write_bytes (pathlib/Path out (str name "." stream)) raw))
                         (let [row (u/pydict "name" name "exit" (.-returncode p) "seconds" (- (time/monotonic) started)
                                             "cpuSeconds" (- (+ (.-ru_utime after) (.-ru_stime after)) (.-ru_utime before) (.-ru_stime before))
                                             "loadStart" load- "loadEnd" (os/getloadavg))]
                           (.append (g report "calls") row)
                           (write-report!)
                           (println (json/dumps row))
                           (.flush sys/stdout)
                           (u/chk (and (= (.-returncode p) expected) (zero? (python/len (.-stderr p)))) (str [name (.-returncode p) (.-stderr p)]))
                           row)))]
        ;; Screen the isolated edits first, then B/C/C/B of original vs fully annotated source under one image.
        (doseq [[i variant] (map-indexed vector ["doctail" "dt" "lit" "baseline" "all" "all" "baseline"])]
          (let [name (str i "-" variant)
                image (pathlib/Path out (str name ".elf"))
                row (run-step (str "build-" name) [producer "compile" (get @sources variant) "--target" target "--output" image "--format" "static"] 0)]
            (operator/setitem row "image" (pin image))
            (u/chk (= (g (g row "image") "sha256") (get image-sha host)) (str [variant "emitted program changed"]))
            (.chmod image 0755)
            (let [runtime-env (let [d (python/dict env)] (operator/setitem d "KEXE_ALLOW" "38") d)]
              (run-step (str "semantic-" name) [image] 0 runtime-env)
              (run-step (str "refusal-" name) [image "fail-control"] 1 runtime-env))))
        (let [samples (u/pydict-from (for [v ["baseline" "all"]]
                                       [v (python/list (for [r (g report "calls")
                                                             :when (and (.startswith (g r "name") "build-") (.endswith (g r "name") (str "-" v)))]
                                                         (g r "seconds")))]))]
          (.update report (u/pydict "status" "PASS_NATIVE_EXPLICIT_ANNOTATION_COMPARISON" "samples" samples
                                    "candidateToBaselineRatio" (/ (statistics/median (g samples "all")) (statistics/median (g samples "baseline")))
                                    "allImagesByteIdentical" true "freshSemanticExecutions" 7 "freshRefusalExecutions" 7))
          (write-report!)
          (println (g report "status") (g report "candidateToBaselineRatio"))
          (.flush sys/stdout))))))

(defn -main [& args]
  (run (.resolve (pathlib/Path (or (u/opt args "--output") (sys/exit "--output is required"))))
       (when-let [w (u/opt args "--workload-file")] (.resolve (pathlib/Path w)))))

(when (some #(or (= % "compare-source-refinements.cljc") (str/ends-with? % "/compare-source-refinements.cljc")) sys/argv)
  (apply -main *command-line-args*))
