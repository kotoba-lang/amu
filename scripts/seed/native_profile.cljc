;; Linux process observations only; never supplies a native gate verdict.
;;
;; The controller and its sealed children run with their original argv/env/limits.
;; No ptrace, injected code, native format writer or controller change is needed.
;; Phase edges are polling observations, not instruction-level instrumentation.
;; Ported from native_process_profile.py (Basilisp). Linux only (/proc, wait4). Named native_profile while the Python original is still imported by unported gates.
(ns native-profile
  (:require [gate-util :as u])
  (:import hashlib json operator os pathlib subprocess threading time))

(defn atomic-json [path value]
  (let [path (pathlib/Path path)
        temporary (.with_suffix path (str (.-suffix path) ".tmp"))]
    (.write_text temporary (u/json-dump value))
    (.replace temporary path)))

(defn proc-stat [pid]
  (try
    (let [text (.read_text (pathlib/Path (str "/proc/" pid "/stat")))
          fields (.split (u/geti (.rsplit text ") " 1) 1))
          hz (os/sysconf "SC_CLK_TCK")
          f (fn [i] (python/int (u/geti fields i)))]
      (u/pydict "state" (u/geti fields 0) "parent" (f 1)
                "selfCPU" (operator/truediv (+ (f 11) (f 12)) hz) "childrenCPU" (operator/truediv (+ (f 13) (f 14)) hz)
                "startTicks" (f 19) "rssBytes" (* (f 21) (os/sysconf "SC_PAGE_SIZE"))))
    (catch python/FileNotFoundError _ nil)
    (catch python/ProcessLookupError _ nil)))

(defn child-role [pid]
  (try
    (let [argv0 (u/geti (.split (.read_bytes (pathlib/Path (str "/proc/" pid "/cmdline"))) (u/bytes-of 0) 1) 0)
          base (u/geti (.rsplit argv0 (.encode "/") 1) -1)]
      (get {(.encode "amu-selfhost.elf") "amu-rebuild" (.encode "kotoba-native.elf") "kotoba-gate"} base))
    (catch python/FileNotFoundError _ nil)
    (catch python/ProcessLookupError _ nil)))

(defn- set-many! [d & kvs]
  (doseq [[k v] (partition 2 kvs)] (operator/setitem d k v)))

(defn observe-controller
  "Return CompletedProcess while separately recording diagnostic timing.

  wait4 retains final CPU usage including reaped descendants. /proc samples divide the two direct native
  children; cumulative child CPU is assigned only after the controller actually reaps them. The residual is the
  native controller's own CPU, including hashes, IO and wait supervision."
  [argv & {:keys [cwd env timeout output interval] :or {interval 0.05}}]
  (when-not (.exists (pathlib/Path "/proc/self/stat"))
    (throw (python/RuntimeError "Linux /proc required for controller profiling")))
  (when (or (<= interval 0) (> interval 0.1))
    (throw (python/ValueError "sampling interval must be in (0, 0.1]")))
  (let [output (pathlib/Path output)
        started (time/monotonic)
        phases (python/list)
        children (python/dict)
        phase (atom "preflight")
        phase-start (atom 0.0)
        parent-last (atom (u/pydict "selfCPU" 0.0 "childrenCPU" 0.0))
        reaped-cpu (atom 0.0)
        departed (atom [])
        final-usage (atom nil)
        returncode (atom nil)
        report (u/pydict "schema" "amu.native-controller-profile.v1" "nativeVerdictAuthority" false
                         "qualificationReplacement" false "pollIntervalSeconds" interval
                         "observerSourceSHA256" (u/sha256-hex (.read_bytes (.joinpath u/root "scripts/seed/native_profile.cljc")))
                         "status" "RUNNING" "phases" phases "children" (python/list)
                         "hostCPUs" (os/cpu_count) "loadStart" (python/list (os/getloadavg)))
        snapshot (fn [elapsed status]
                   (set-many! report "status" status "elapsedSeconds" elapsed "activePhase" @phase
                              "phases" (python/list (concat (python/list phases)
                                                            [(u/pydict "name" @phase "startSeconds" @phase-start "seconds" (- elapsed @phase-start))]))
                              "children" (python/list (.values children)) "parentSample" @parent-last)
                   (atomic-json output report))
        stdout-path (.with_suffix output ".stdout")
        stderr-path (.with_suffix output ".stderr")]
    ;; Keep the original pipe endpoint types. Reader threads drain them while wait4 remains the sole reaper, so
    ;; neither backpressure nor communicate() can interfere with phase sampling or final CPU accounting.
    (with-open [stdout (.open stdout-path "wb")
                stderr (.open stderr-path "wb")]
      (let [process (subprocess/Popen (python/list (map str argv)) ** :cwd cwd :env env :stdout subprocess/PIPE :stderr subprocess/PIPE)
            drain (fn [source destination]
                    (with-open [s source]
                      (loop []
                        (let [block (.read s 65536)]
                          (when (u/nonempty? block)
                            (.write destination block)
                            (recur))))))
            readers (mapv (fn [[source destination]] (threading/Thread ** :target drain :args (python/tuple [source destination])))
                          [[(.-stdout process) stdout] [(.-stderr process) stderr]])]
        (doseq [r readers] (.start r))
        (try
          (loop [last-write -10.0]
            (let [elapsed (- (time/monotonic) started)
                  parent (proc-stat (.-pid process))
                  active (atom nil)]
              (when parent
                (reset! parent-last parent)
                (let [pids (try (.split (.read_text (pathlib/Path (str "/proc/" (.-pid process) "/task/" (.-pid process) "/children"))))
                                (catch python/FileNotFoundError _ []) (catch python/ProcessLookupError _ []))
                      seen (atom #{})]
                  (doseq [pid pids]
                    (let [state (proc-stat pid) role (child-role pid)]
                      (when (and (some? state) (some? role))
                        (let [key (str pid ":" (u/geti state "startTicks"))]
                          (swap! seen conj key)
                          (when-not (operator/contains children key)
                            (operator/setitem children key (u/pydict "role" role "firstSeenSeconds" elapsed "lastSeenSeconds" elapsed
                                                                    "sampledCPUSeconds" 0.0 "peakRSSBytes" 0 "reaped" false)))
                          (let [row (u/geti children key)]
                            (set-many! row "lastSeenSeconds" elapsed
                                       "sampledCPUSeconds" (+ (u/geti state "selfCPU") (u/geti state "childrenCPU"))
                                       "peakRSSBytes" (max (u/geti row "peakRSSBytes") (u/geti state "rssBytes"))))
                          (reset! active role)))))
                  (doseq [[key row] (python/list (.items children))]
                    (when (and (not (contains? @seen key)) (not (.get row "departed")))
                      (set-many! row "departed" true "departureObservedSeconds" elapsed)
                      (swap! departed conj row)))
                  (when (and (> (u/geti parent "childrenCPU") @reaped-cpu) (seq @departed))
                    (let [row (first @departed)]
                      (swap! departed subvec 1)
                      (set-many! row "reaped" true "reapedCPUSeconds" (- (u/geti parent "childrenCPU") @reaped-cpu))
                      (reset! reaped-cpu (u/geti parent "childrenCPU"))))))
              (when (nil? @active)
                (let [roles (set (map #(u/geti % "role") (.values children)))]
                  (reset! active (cond (contains? roles "kotoba-gate") "receipt-finalization"
                                       (contains? roles "amu-rebuild") "post-rebuild-verification"
                                       :else "preflight"))))
              (when (not= @active @phase)
                (.append phases (u/pydict "name" @phase "startSeconds" @phase-start "seconds" (- elapsed @phase-start)))
                (reset! phase @active)
                (reset! phase-start elapsed)
                (snapshot elapsed "RUNNING"))
              (let [[pid status usage] (vec (os/wait4 (.-pid process) os/WNOHANG))]
                (cond
                  (not (zero? pid))
                  (let [rc (os/waitstatus_to_exitcode status)]
                    (reset! returncode rc)
                    (set! (.-returncode process) rc)
                    (reset! final-usage usage))

                  (>= elapsed timeout)
                  (do (.kill process)
                      (let [[_ status usage] (vec (os/wait4 (.-pid process) 0))]
                        (set! (.-returncode process) (os/waitstatus_to_exitcode status))
                        (reset! final-usage usage))
                      (snapshot (- (time/monotonic) started) "TIMEOUT")
                      (throw (subprocess/TimeoutExpired argv timeout)))

                  :else
                  (let [last-write (if (>= (- elapsed last-write) 5) (do (snapshot elapsed "RUNNING") elapsed) last-write)]
                    (time/sleep interval)
                    (recur last-write))))))
          (catch python/BaseException error
            (when (nil? (.-returncode process))
              (.kill process)
              (let [[_ status _] (vec (os/wait4 (.-pid process) 0))]
                (set! (.-returncode process) (os/waitstatus_to_exitcode status))))
            (snapshot (- (time/monotonic) started)
                      (if (instance? subprocess/TimeoutExpired error) "TIMEOUT" "OBSERVER_INTERRUPTED"))
            (throw error))
          (finally
            (doseq [r readers] (.join r))))))
    (let [elapsed (- (time/monotonic) started)
          usage @final-usage
          total-cpu (+ (.-ru_utime usage) (.-ru_stime usage))
          remaining-cpu (- total-cpu (u/geti @parent-last "selfCPU") @reaped-cpu)
          unaccounted (vec (filter #(not (u/geti % "reaped")) (.values children)))]
      (when (and (= 1 (count unaccounted)) (>= remaining-cpu 0))
        (set-many! (first unaccounted) "reaped" true "reapedCPUSeconds" remaining-cpu "finalWait4Residual" true
                   "cpuResidualIncludesControllerFinalSamplingInterval" true)
        (swap! reaped-cpu + remaining-cpu))
      (set-many! report "exit" @returncode "totalCPUSeconds" total-cpu "controllerCPUSeconds" (- total-cpu @reaped-cpu)
                 "reapedChildrenCPUSeconds" @reaped-cpu "maxRSSKiB" (.-ru_maxrss usage) "loadEnd" (python/list (os/getloadavg))
                 "phaseEdges" "/proc polling; <= one sampling interval plus observer scheduling per edge"
                 "cpuAccounting" "wait4 process+reaped descendants; child boundaries from controller /proc cutime/cstime")
      (operator/setitem report "completePhaseObservation"
                        (= #{"amu-rebuild" "kotoba-gate"} (set (map #(u/geti % "role") (.values children)))))
      (snapshot elapsed "COMPLETED")
      (subprocess/CompletedProcess argv @returncode (.read_bytes stdout-path) (.read_bytes stderr-path)))))
