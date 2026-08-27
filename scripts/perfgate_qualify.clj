(ns perfgate-qualify
  (:require [clojure.data.json :as json]
            [clojure.string :as str]
            [machine.core :as m]
            [perfgate.core :as g]))

(defn sysctl [name]
  (try
    (let [pb (ProcessBuilder. (into-array String ["sysctl" name]))
          proc (.start pb)]
      (when (zero? (.waitFor proc))
        (second (str/split (str/trim (slurp (.getInputStream proc))) #":\s+" 2))))
    (catch Exception _ nil)))

(defn measured-machine []
  (let [brand (or (sysctl "machdep.cpu.brand_string") "unknown-cpu")
        cores (or (some-> (sysctl "hw.logicalcpu") parse-long)
                  (.availableProcessors (Runtime/getRuntime)))
        line (or (some-> (sysctl "hw.cachelinesize") parse-long) 64)
        l1 (or (some-> (sysctl "hw.l1dcachesize") parse-long) 32768)
        l2 (or (some-> (sysctl "hw.l2cachesize") parse-long) 262144)]
    (m/measured
     {:format m/format-id
      :machine/id (str "darwin-" (str/replace (str/lower-case brand) #"[^a-z0-9]+" "-"))
      :cpu {:arch (if (= "arm64" (System/getProperty "os.arch")) :aarch64 :x86-64)
            :cores cores
            :cache [{:level 1 :kind :data :bytes l1 :line-bytes line :shared-by 1}
                    {:level 2 :kind :unified :bytes l2 :line-bytes line :shared-by 1}]}
      :page {:base-bytes (or (some-> (sysctl "hw.pagesize") parse-long) 4096) :huge []}
      :numa {:nodes 1 :distance [[10]]}}
     (str "sysctl darwin host probe on "
          (.. java.net.InetAddress getLocalHost getHostName)))))

(defn observation [id plan-id metric unit samples source]
  (g/observation {:id id
                  :plan-id plan-id
                  :machine (measured-machine)
                  :metric metric
                  :unit unit
                  :samples (vec samples)
                  :source source
                  :lower-is-better? true}))

(defn host-load-qualified? [report]
  (let [host (or (:hostLoadQualified (:environment report))
                 (get-in report [:qualification :hostLoad :qualified]))]
    (boolean host)))

(defn performance-verdict [report]
  (or (get-in report [:qualification :performance :verdict])
      (when-not (host-load-qualified? report) "unqualified-host-load")
      "deferred-quiet-host-rerun"))

(defn qualify-arm [label report-key metric-key metric unit plan-id source report]
  (let [baseline-samples (mapv metric-key (get-in report [report-key :baseline :samples]))
        candidate-samples (mapv metric-key (get-in report [report-key :candidate :samples]))
        baseline (observation (keyword (name label) "baseline") plan-id metric unit baseline-samples source)
        candidate (observation (keyword (name label) "candidate") plan-id metric unit candidate-samples source)
        raw-verdict (g/qualify candidate baseline)
        verdict (if (host-load-qualified? report)
                  raw-verdict
                  (assoc raw-verdict
                         :qualified? false
                         :verdict :unqualified-host-load
                         :reason "host load exceeds logical CPU count"))]
    {:label label
     :metric metric
     :unit unit
     :baseline (:observation/summary baseline)
     :candidate (:observation/summary candidate)
     :verdict verdict}))

(defn -main [& args]
  (let [input (first args)]
    (when-not (and (string? input) (seq input))
      (binding [*out* *err*]
        (println "usage: perfgate-qualify <benchmark.json>"))
      (System/exit 2))
    (let [report (json/read-str (slurp input) :key-fn keyword)
          fixture (:fixture report)
          target (:target report)
          plan-id (keyword "postalloc-scheduling" (str fixture "." target))
          source (str "scripts/postalloc-scheduling-benchmark.mjs --fixture " fixture
                      " --target " target)
          runtime (qualify-arm :runtime :runtime :nanosecondsPerKernel :runtime :ns plan-id source report)
          compile (when (and (:compile report)
                             (not (:error (:compile report)))
                             (get-in report [:compile :baseline :samples]))
                    (qualify-arm :compile :compile :compileWallMilliseconds :compile :ms plan-id source report))]
      (println (json/write-str
                {:format "amu.perfgate-qualification/v1"
                 :fixture fixture
                 :target target
                 :plan-id plan-id
                 :host-load-qualified? (host-load-qualified? report)
                 :performance-verdict (performance-verdict report)
                 :runtime runtime
                 :compile compile
                 :any-qualified? (and (host-load-qualified? report)
                                      (or (:qualified? (:verdict runtime))
                                          (boolean (and compile (:qualified? (:verdict compile))))))}
                :value-fn (fn [_ v] (if (keyword? v) (name v) v)))))))
