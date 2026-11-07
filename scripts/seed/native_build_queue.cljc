;; Bound native build admission across cooperating processes/worktrees.
;;
;; This is process scheduling, not compilation or native qualification. A held flock is inherited by the
;; launched harness, and kernel cleanup releases it. Existing unmanaged builds are reported separately; they are
;; never stopped.
;; Ported from native_build_queue.py (Basilisp). Linux/macOS (flock). The Python context manager `build_slot`
;; becomes a callback: (with-build-slot directory capacity (fn [handle admission] ...)).
;; Run: basilisp run scripts/seed/native_build_queue.cljc -- [--slot-dir D] [--capacity N] [--jobs N]
;;        (--manifest M --phase P --output O | [--output O] -- COMMAND...)
(ns native-build-queue
  (:require [basilisp.string :as str]
            [gate-util :as u]
            [native-profile :as profile])
  (:import concurrent.futures fcntl json operator os pathlib signal subprocess sys time))

(defn default-slot-dir []
  (cond
    (.get os/environ "KOTOBA_NATIVE_SLOT_DIR") (pathlib/Path (operator/getitem os/environ "KOTOBA_NATIVE_SLOT_DIR"))
    (.get os/environ "RUNNER_TEMP") (.joinpath (pathlib/Path (operator/getitem os/environ "RUNNER_TEMP")) "native-build-slots")
    :else (.joinpath (.home pathlib/Path) "github/workspaces/codex/native-build-slots-v1")))

(defn with-build-slot
  ([directory f] (with-build-slot directory 2 f))
  ([directory capacity f]
   (when (or (< capacity 1) (> capacity 64)) (throw (python/ValueError "slot capacity must be 1..64")))
   (let [directory (pathlib/Path directory)]
     (.mkdir directory ** :parents true :exist_ok true)
     (with-open [guard (.open (.joinpath directory "capacity.lock") "a+")]
       (fcntl/flock guard fcntl/LOCK_EX)
       (let [config (.joinpath directory "capacity.json")]
         (if (.exists config)
           (when (not= capacity (u/geti (json/loads (.read_text config)) "slots"))
             (throw (python/ValueError "shared slot capacity mismatch; use the existing capacity")))
           (profile/atomic-json config (u/pydict "slots" capacity)))))
     (let [started (time/monotonic)]
       (loop []
         (let [handle (some (fn [index]
                              (let [h (.open (.joinpath directory (str "slot-" index ".lock")) "a+")]
                                (try (fcntl/flock h (bit-or fcntl/LOCK_EX fcntl/LOCK_NB))
                                     [index h]
                                     (catch python/BlockingIOError _ (.close h) nil))))
                            (range capacity))]
           (if handle
             (let [[index h] handle]
               ;; The command inherits the descriptor. If the outer wrapper is killed, its still-running
               ;; harness keeps its admission slot.
               (try
                 (f h (u/pydict "slot" index "capacity" capacity "queuedSeconds" (- (time/monotonic) started)))
                 (finally
                   ;; Do not explicitly LOCK_UN: the child may still hold this same open-file description after
                   ;; an interrupted wrapper.
                   (.close h))))
             (do (time/sleep 0.1) (recur)))))))))

(defn execute
  [argv & {:keys [directory capacity stdout stderr cwd env] :or {capacity 2}}]
  (let [started (time/monotonic)]
    (let [[admission code admitted]
          (with-build-slot directory capacity
            (fn [handle admission]
              (let [admitted (time/monotonic)
                    child (subprocess/Popen (python/list (map str argv)) ** :cwd cwd :env env :stdout stdout :stderr stderr
                                            :pass_fds (python/tuple [(.fileno handle)]) :start_new_session true)]
                (try [admission (.wait child) admitted]
                     (catch python/BaseException e
                       (os/killpg (.-pid child) signal/SIGTERM)
                       (try (.wait child ** :timeout 10)
                            (catch subprocess/TimeoutExpired _
                              (os/killpg (.-pid child) signal/SIGKILL)
                              (.wait child)))
                       (throw e))))))]
      (let [row (python/dict admission)]
        (operator/setitem row "exit" code)
        (operator/setitem row "runSeconds" (- (time/monotonic) admitted))
        (operator/setitem row "totalSeconds" (- (time/monotonic) started))
        row))))

(defn plan-jobs [manifest phase environment]
  (let [data (json/loads (.read_text (pathlib/Path manifest)))]
    (when (not= "amu.native-gate-plan.v1" (u/geti data "schema")) (throw (python/ValueError "unknown native gate plan")))
    (let [rows (u/geti (u/geti data "phases") phase)
          names (mapv #(u/geti % "name") rows)]
      (when (not= (count names) (count (set names))) (throw (python/ValueError "duplicate gate names")))
      ;; Only substitute complete argv tokens, never splice data into shell code.
      (let [temp (u/geti environment "RUNNER_TEMP")]
        (vec (for [row rows]
               {:name (u/geti row "name")
                :argv (mapv #(.replace % "@TEMP@" temp) (u/geti row "argv"))}))))))

(defn run-plan
  [manifest phase output & {:keys [jobs capacity directory] :or {jobs 2 capacity 2}}]
  (when (or (< jobs 1) (> jobs capacity)) (throw (python/ValueError "jobs must be 1..shared capacity")))
  (let [gates (plan-jobs manifest phase os/environ)
        output (pathlib/Path output)
        _ (.mkdir output ** :exist_ok false)
        report (u/pydict "schema" "amu.native-gate-scheduling.v1" "nativeVerdictAuthority" false
                         "qualificationReplacement" false "jobs" jobs "capacity" capacity
                         "phase" phase "status" "RUNNING" "gates" (python/list))
        started (time/monotonic)
        _ (profile/atomic-json (.joinpath output "schedule.json") report)
        run (fn [row submitted]
              (let [worker-started (time/monotonic)
                    name (:name row)]
                (when (or (empty? name) (not (every? #(contains? (set "abcdefghijklmnopqrstuvwxyz0123456789-") %) name)))
                  (throw (python/ValueError "invalid gate name")))
                (let [timing (with-open [log (.open (.joinpath output (str name ".log")) "wb")]
                               (execute (:argv row) :directory (or directory (default-slot-dir)) :capacity capacity
                                        :stdout log :stderr subprocess/STDOUT))]
                  (.write_text (.joinpath output (str name ".rc")) (str (u/geti timing "exit") "\n"))
                  (let [worker-queue (- worker-started submitted)]
                    (u/pydict "name" name "argv" (python/list (:argv row))
                              "slot" (u/geti timing "slot") "capacity" (u/geti timing "capacity")
                              "queuedSeconds" (+ worker-queue (u/geti timing "queuedSeconds"))
                              "exit" (u/geti timing "exit") "runSeconds" (u/geti timing "runSeconds")
                              "totalSeconds" (u/geti timing "totalSeconds")
                              "workerQueueSeconds" worker-queue "slotQueueSeconds" (u/geti timing "queuedSeconds")
                              "startSeconds" (+ (- worker-started started) (u/geti timing "queuedSeconds"))
                              "endSeconds" (- (time/monotonic) started))))))]
    ;; Every submitted gate is awaited even if another fails. No lost pipeline exit, cancelled assertion,
    ;; swallowed exception or shared JSON writer.
    (with-open [pool (concurrent.futures/ThreadPoolExecutor ** :max_workers jobs)]
      (let [futures (python/dict (python/list (for [row gates] (python/tuple [(.submit pool run row (time/monotonic)) row]))))
            it (python/iter (concurrent.futures/as_completed futures))]
        (loop []
          (when-let [future (python/next it nil)]
            (let [row (operator/getitem futures future)
                  result (try (.result future)
                              (catch python/Exception error
                                (u/pydict "name" (:name row) "exit" 1 "error" (str (.-__name__ (python/type error)) ": " error))))]
              (.append (u/geti report "gates") result)
              (profile/atomic-json (.joinpath output "schedule.json") report)
              (println (str (:name row) ": exit=" (u/geti result "exit")))
              (.flush sys/stdout)
              (let [log (.joinpath output (str (:name row) ".log"))]
                (when (.exists log)
                  (.write (.-buffer sys/stdout) (.read_bytes log))
                  (.flush sys/stdout)))
              (recur))))))
    (operator/setitem report "status" "COMPLETED")
    (operator/setitem report "seconds" (- (time/monotonic) started))
    (operator/setitem report "exit" (if (every? #(zero? (u/geti % "exit")) (u/geti report "gates")) 0 1))
    (profile/atomic-json (.joinpath output "schedule.json") report)
    (u/geti report "exit")))

(defn- parse-args [args]
  (loop [m {:slot-dir (default-slot-dir)
            :capacity (python/int (or (.get os/environ "KOTOBA_NATIVE_SLOT_CAPACITY") "2"))
            :jobs 2 :manifest nil :phase nil :output nil}
         [a & more :as xs] (seq args)]
    (cond
      (empty? xs) (assoc m :command [])
      (= a "--slot-dir") (recur (assoc m :slot-dir (pathlib/Path (first more))) (rest more))
      (= a "--capacity") (recur (assoc m :capacity (python/int (first more))) (rest more))
      (= a "--jobs") (recur (assoc m :jobs (python/int (first more))) (rest more))
      (= a "--manifest") (recur (assoc m :manifest (pathlib/Path (first more))) (rest more))
      (= a "--phase") (recur (assoc m :phase (first more)) (rest more))
      (= a "--output") (recur (assoc m :output (pathlib/Path (first more))) (rest more))
      :else (assoc m :command (vec xs)))))

(defn main [args]
  (let [{:keys [slot-dir capacity jobs manifest phase output command]} (parse-args args)]
    (if manifest
      (do (when (or (not phase) (not output) (seq command))
            (sys/exit "plan requires --phase and --output, with no command"))
          (run-plan manifest phase output :jobs jobs :capacity capacity :directory slot-dir))
      (let [command (if (= ["--"] (vec (take 1 command))) (vec (rest command)) command)]
        (when (empty? command) (sys/exit "provide a command after --, or a --manifest plan"))
        (let [timing (execute command :directory slot-dir :capacity capacity)]
          (when output
            (let [row (u/pydict "schema" "amu.native-build-admission.v1")]
              (.update row timing)
              (profile/atomic-json output row)))
          (.write sys/stderr (str (json/dumps timing) "\n"))
          (let [code (u/geti timing "exit")]
            (if (>= code 0) code (- 128 code))))))))

(when (some #(or (= % "native_build_queue.cljc") (str/ends-with? % "/native_build_queue.cljc")) sys/argv)
  (sys/exit (main *command-line-args*)))
