;; Save a narrow, path-free summary of a macOS native crash for CI triage. Ported from
;; collect-macos-crash-summary.py (Basilisp, JUN-974).
;; Run: basilisp run -p scripts/seed scripts/seed/collect-macos-crash-summary.cljc -- --process NAME --output FILE
;;      [--report-dir DIR]
(ns collect-macos-crash-summary
  (:require [basilisp.string :as str]
            [gate-util :as u])
  (:import json operator os pathlib sys time))

(defn g [m k] (operator/getitem m k))
(defn has? [m k] (operator/contains m k))
(defn pick
  "{k m[k]} for the listed keys present in m, in the listed order."
  [m ks]
  (u/pydict-from (for [k ks :when (has? m k)] [k (g m k)])))

(defn summary [path]
  (let [lines (.splitlines (.read_text path ** :errors "replace"))]
    (when (< (python/len lines) 2) (throw (python/ValueError "incomplete ips report")))
    (let [header (json/loads (operator/getitem lines 0))
          body (json/loads (.join "\n" (operator/getitem lines (python/slice 1 nil))))
          threads (.get body "threads" (python/list))
          faulting (.get body "faultingThread")
          frames (python/list
                  (if-not (and (instance? python/int faulting) (<= 0 faulting) (< faulting (python/len threads)))
                    []
                    (for [frame (operator/getitem (.get (operator/getitem threads faulting) "frames" (python/list)) (python/slice nil 16))]
                      (pick frame ["imageIndex" "imageOffset" "symbol" "symbolLocation"]))))
          images (.get body "usedImages" (python/list))
          frame-images (python/dict)]
      (doseq [frame frames]
        (let [index (.get frame "imageIndex")]
          (when (and (instance? python/int index) (<= 0 index) (< index (python/len images)))
            (operator/setitem frame-images (python/str index) (pick (operator/getitem images index) ["arch" "uuid" "base" "size"])))))
      (u/pydict "report" (.-name path) "timestamp" (.get header "timestamp") "osVersion" (.get body "osVersion")
                "modelCode" (.get body "modelCode") "exception" (.get body "exception") "termination" (.get body "termination")
                "faultingThread" faulting "frames" frames "frameImages" frame-images))))

(defn -main [& args]
  (let [process (or (u/opt args "--process") (sys/exit "--process is required"))
        output (pathlib/Path (or (u/opt args "--output") (sys/exit "--output is required")))
        report-dir (u/opt args "--report-dir")]
    (when (or (empty? process) (not (every? #(str/includes? "abcdefghijklmnopqrstuvwxyz0123456789-" (str %)) process)))
      (sys/exit "process must be a lowercase executable basename"))
    (let [deadline (+ (time/monotonic) 12)
          directories (if report-dir
                        [(pathlib/Path report-dir)]
                        [(pathlib/Path (.home pathlib/Path) "Library/Logs/DiagnosticReports") (pathlib/Path "/Library/Logs/DiagnosticReports")])
          candidates (loop []
                       (let [cs (python/list [])]
                         (doseq [d directories]
                           (try (.extend cs (.glob d (str process "*.ips")))
                                (catch python/PermissionError _ nil)))
                         (.sort cs ** :key (fn [p] (.-st_mtime (.stat p))) :reverse true)
                         (cond (pos? (python/len cs)) cs
                               (>= (time/monotonic) deadline) cs
                               :else (do (time/sleep 1) (recur)))))
          result (u/pydict "schema" "amu.macos-native-crash-summary.v1" "process" process "reportFound" (pos? (python/len candidates)))]
      (when (pos? (python/len candidates))
        (try (operator/setitem result "crash" (summary (operator/getitem candidates 0)))
             (catch python/Exception e
               (if (or (instance? python/OSError e) (instance? python/ValueError e) (instance? python/KeyError e) (instance? python/TypeError e))
                 (operator/setitem result "parseError" (.-__name__ (python/type e)))
                 (throw e)))))
      (.mkdir (.-parent output) ** :parents true :exist_ok true)
      (.write_text output (str (json/dumps result ** :indent 2 :default str) "\n"))
      (println (json/dumps result ** :default str)))))

(when (some #(or (= % "collect-macos-crash-summary.cljc") (str/ends-with? % "/collect-macos-crash-summary.cljc")) sys/argv)
  (apply -main *command-line-args*))
