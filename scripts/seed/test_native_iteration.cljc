;; Observer/scheduler negative controls, not native compiler qualification.
;; Ported from test_native_iteration.py (Basilisp). The independent wrappers are real `basilisp run` processes
;; of native_build_queue.cljc, as the Python wrappers were real processes of native_build_queue.py; because a
;; Basilisp start-up is slower than a Python one, the guarded programs hold their slot for seconds, not .35s,
;; so the processes still overlap.
;; Run from the repo root:
;;   PYTHONPATH=scripts/seed basilisp test -p no:cacheprovider --rootdir scripts/seed scripts/seed/test_native_iteration.cljc
(ns test-native-iteration
  (:require [basilisp.test :refer [deftest is]]
            [basilisp.string :as str]
            [gate-util :as u]
            [native-build-queue :as q]
            [native-profile :as profile])
  (:import json operator os pathlib shutil subprocess sys tempfile time))

(def queue (str (.joinpath u/root "scripts/seed/native_build_queue.cljc")))
(def basilisp (shutil/which "basilisp"))

(defmacro with-root [[sym] & body]
  `(with-open [temporary# (tempfile/TemporaryDirectory)]
     (let [~sym (pathlib/Path temporary#)] ~@body)))

(defn wrappers-peak
  "Five independent wrappers on one slot directory; returns the most that ever held a slot at once."
  [root capacity-env]
  (let [events (.joinpath root "events.jsonl")
        program (str "import fcntl,json,time,sys; "
                     "f=open(sys.argv[1],'a'); "
                     "fcntl.flock(f,fcntl.LOCK_EX); f.write(json.dumps([time.monotonic(),1])+'\\n'); f.flush(); "
                     "fcntl.flock(f,fcntl.LOCK_UN); time.sleep(4); "
                     "fcntl.flock(f,fcntl.LOCK_EX); f.write(json.dumps([time.monotonic(),-1])+'\\n'); f.flush()")
        env (python/dict (for [[k v] (.items os/environ) :when (not= k "KOTOBA_NATIVE_SLOT_CAPACITY")] (python/tuple [k v])))
        _ (when capacity-env (operator/setitem env "KOTOBA_NATIVE_SLOT_CAPACITY" capacity-env))
        processes (vec (for [_ (range 5)]
                         (subprocess/Popen (python/list [basilisp "run" queue "--" "--slot-dir" (str (.joinpath root "slots"))
                                                         "--" sys/executable "-c" program (str events)])
                                           ** :stdout subprocess/DEVNULL :stderr subprocess/DEVNULL :env env)))]
    (doseq [p processes] (is (= 0 (.wait p ** :timeout 90))))
    (let [rows (sort-by first (map #(vec (json/loads %)) (.splitlines (.read_text events))))
          [active peak] (reduce (fn [[active peak] [_ delta]] (let [a (+ active delta)] [a (max peak a)])) [0 0] rows)]
      (is (= 0 active))
      peak)))

(deftest independent-wrappers-share-two-slots
  ;; the default, whatever the caller's environment (a CI job sets KOTOBA_NATIVE_SLOT_CAPACITY)
  (with-root [root] (is (= 2 (wrappers-peak root nil)))))

(deftest slot-capacity-comes-from-the-environment
  ;; JUN-629: a 4-vCPU CI runner sets the capacity for every call in its job
  (with-root [root] (is (= 4 (wrappers-peak root "4")))))

(deftest capacity-mismatch-refuses
  (with-root [root]
    (q/with-build-slot (.joinpath root "slots") 2
      (fn [_ _]
        (is (thrown-with-msg? python/ValueError #"capacity mismatch"
                              (q/with-build-slot (.joinpath root "slots") 3 (fn [_ _] (throw (python/AssertionError "mismatched capacity admitted"))))))))))

(deftest slot-remains-held-by-child-after-wrapper-kill
  (with-root [root]
    (let [ready (.joinpath root "ready")
          wrapper (subprocess/Popen (python/list [basilisp "run" queue "--" "--capacity" "1" "--slot-dir" (str (.joinpath root "slots"))
                                                  "--" sys/executable "-c"
                                                  "import pathlib,sys,time; pathlib.Path(sys.argv[1]).touch(); time.sleep(.8)" (str ready)])
                                    ** :stdout subprocess/DEVNULL :stderr subprocess/DEVNULL)
          deadline (+ (time/monotonic) 60)]
      (loop []
        (when (and (not (.exists ready)) (< (time/monotonic) deadline))
          (time/sleep 0.01)
          (recur)))
      (is (.exists ready))
      (.kill wrapper)
      (.wait wrapper)
      (let [timing (q/execute [sys/executable "-c" "pass"] :directory (.joinpath root "slots") :capacity 1)]
        (is (> (u/geti timing "queuedSeconds") 0.3))))))

(defn- with-runner-temp [root f]
  (let [old (.get os/environ "RUNNER_TEMP")]
    (operator/setitem os/environ "RUNNER_TEMP" (str root))
    (try (f)
         (finally
           (if (nil? old) (.pop os/environ "RUNNER_TEMP") (operator/setitem os/environ "RUNNER_TEMP" old))))))

(deftest failure-does-not-skip-other-gates-or-hide-pipeline
  (with-root [root]
    (let [manifest (.joinpath root "plan.json")
          marker (.joinpath root "other-ran")]
      (.write_text manifest
                   (json/dumps (u/pydict "schema" "amu.native-gate-plan.v1"
                                         "phases" (u/pydict "test" (python/list
                                                                     [(u/pydict "name" "broken" "argv" (python/list ["bash" "-euo" "pipefail" "-c" "exit 7 | cat"]))
                                                                      (u/pydict "name" "other" "argv" (python/list [sys/executable "-c" "import pathlib,sys; pathlib.Path(sys.argv[1]).touch()" (str marker)]))])))))
      (let [code (with-runner-temp root #(q/run-plan manifest "test" (.joinpath root "logs") :directory (.joinpath root "slots")))]
        (is (= 1 code))
        (is (.exists marker))
        (let [report (json/loads (.read_text (.joinpath root "logs/schedule.json")))]
          (is (= [0 7] (vec (sort (map #(u/geti % "exit") (u/geti report "gates")))))))))))

(deftest worker-queue-is-recorded-separately-from-slot-wait
  (with-root [root]
    (let [manifest (.joinpath root "queue-plan.json")]
      (.write_text manifest
                   (json/dumps (u/pydict "schema" "amu.native-gate-plan.v1"
                                         "phases" (u/pydict "test" (python/list
                                                                     (for [i (range 5)]
                                                                       (u/pydict "name" (str "gate-" i) "argv" (python/list [sys/executable "-c" "import time; time.sleep(.2)"]))))))))
      (is (= 0 (with-runner-temp root #(q/run-plan manifest "test" (.joinpath root "logs") :directory (.joinpath root "slots")))))
      (let [rows (vec (u/geti (json/loads (.read_text (.joinpath root "logs/schedule.json"))) "gates"))]
        (is (= 5 (count rows)))
        (is (> (apply max (map #(u/geti % "workerQueueSeconds") rows)) 0.2))
        (doseq [row rows]
          (is (< (python/abs (- (u/geti row "queuedSeconds") (+ (u/geti row "workerQueueSeconds") (u/geti row "slotQueueSeconds")))) 1e-6))
          (is (< (u/geti row "startSeconds") (u/geti row "endSeconds"))))))))

(deftest observer-preserves-outputs-exit-and-accounts-children
  ;; These are explicitly harness controls, not compiler artifacts.
  (with-root [root]
    (doseq [name ["amu-selfhost.elf" "kotoba-native.elf"]] (shutil/copy2 sys/executable (.joinpath root name)))
    (let [controller (.joinpath root "control.py")]
      (.write_text controller "import subprocess,sys,time,stat,os
from pathlib import Path
p=Path(__file__).parent
assert stat.S_ISFIFO(os.fstat(1).st_mode) and stat.S_ISFIFO(os.fstat(2).st_mode)
spin='import time; end=time.monotonic()+.35\\nwhile time.monotonic()<end: pass'
time.sleep(.15)
subprocess.run([p/'amu-selfhost.elf','-c',spin],check=True)
time.sleep(.15)
subprocess.run([p/'kotoba-native.elf','-c',spin],check=True)
time.sleep(.15)
print('verdict bytes')
print('control stderr',file=sys.stderr)
raise SystemExit(7)
")
      (let [profile-path (.joinpath root "profile.json")
            result (profile/observe-controller [sys/executable controller] :cwd root :env (python/dict os/environ) :timeout 10 :output profile-path)]
        (is (= 7 (.-returncode result)))
        (is (= (.encode "verdict bytes\n") (.-stdout result)))
        (is (= (.encode "control stderr\n") (.-stderr result)))
        (let [data (json/loads (.read_text profile-path))]
          (is (= "COMPLETED" (u/geti data "status")))
          (is (false? (u/geti data "nativeVerdictAuthority")))
          (is (= #{"amu-rebuild" "kotoba-gate"} (set (map #(u/geti % "role") (u/geti data "children")))))
          (is (< (python/abs (- (reduce + (map #(u/geti % "seconds") (u/geti data "phases"))) (u/geti data "elapsedSeconds"))) 1e-6))
          (is (> (u/geti data "reapedChildrenCPUSeconds") 0.15))
          (is (>= (u/geti data "controllerCPUSeconds") 0)))))))

(deftest timeout-is-not-success-and-cleans-parent
  (with-root [root]
    (let [profile-path (.joinpath root "timeout.json")]
      (is (thrown? subprocess/TimeoutExpired
                   (profile/observe-controller [sys/executable "-c" "import time;time.sleep(10)"] :cwd root
                                               :env (python/dict os/environ) :timeout 0.1 :output profile-path)))
      (is (= "TIMEOUT" (u/geti (json/loads (.read_text profile-path)) "status"))))))
