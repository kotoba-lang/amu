;; Namespace capability declarations name every admitted wire (KOTOBA-173).
;;
;; The checker admits `:entropy/draw` (wire 23) and `:sys/cwd` (wire 40), but the declaration table (`pj-r5b-wire`,
;; 60-proj) and the diagnostic name tables (`drv-r5b-wire` / `drv-r5b-wname`, 90-drv) did not list them: a module that
;; declared and called `:entropy/draw` got E2176 for its own declaration, and naming wire 23 in that message crashed
;; the checker (SIGILL).
;;
;; Runs the source-locked `check` of one-function modules with a Linux arm64 static compiler and requires, for each of
;; the two wires and the `:clock/now` control: declared + called passes; called under a declaration that omits it is
;; refused with E2176 naming the capability. Linux arm64 only (podman or CI).
;; Ported from check-capability-declaration-names.py (Basilisp).
;; Run: basilisp run scripts/seed/check-capability-declaration-names.cljc -- --compiler C --compiler-sha256 SHA --output OUT
(ns check-capability-declaration-names
  (:require [basilisp.string :as str]
            [gate-util :as u])
  (:import json pathlib platform sys))

(def calls
  [[":entropy/draw" "(string-length (typed-cap-call :entropy/draw :string :string \"2\"))"]
   [":sys/cwd" "(string-length (typed-cap-call :sys/cwd :string :string \"\"))"]
   [":clock/now" "(string-length (typed-cap-call :clock/now :string :string \"wall\"))"]])

(defn- tail [b n] (let [s (.decode b ** :errors "replace")] (if (> (python/len s) n) (subs s (- (python/len s) n)) s)))

(defn check [compiler out name source]
  (let [root (.joinpath (.joinpath out name) "src")
        _ (.mkdir (.joinpath root "r") ** :parents true)
        module (.joinpath (.joinpath root "r") "m.kotoba")
        _ (.write_text module (str source "\n"))
        lock (.joinpath out (str name ".ksl"))
        _ (.write_text lock (str "KSL1\nentry " module "\nroot " root "\nfile " (u/sha256-hex (.read_bytes module)) " " module "\n"))
        r (u/run-process [compiler "check" module "--source-path" root "--source-lock" lock
                          "--source-lock-sha256" (u/sha256-hex (.read_bytes lock))]
                         (python/dict {"PATH" "/nonexistent" "KEXE_STACK_BYTES" "8388608" "KEXE_CAP_RESOURCES_35" (str out)}) 600)]
    (u/pydict "case" name "exit" (.-returncode r) "stdout" (tail (.-stdout r) 300) "stderr" (tail (.-stderr r) 300))))

(defn main [compiler compiler-sha256 output]
  (when-not (and (= "Linux" (platform/system)) (contains? #{"aarch64" "arm64"} (platform/machine)))
    (sys/exit "run on Linux arm64"))
  (when (not= (u/sha256-hex (.read_bytes compiler)) compiler-sha256) (sys/exit "compiler digest mismatch"))
  (.mkdir output ** :parents true :exist_ok false)
  (let [results (python/list)]
    (doseq [[cap call] calls]
      (let [slug (.replace (.strip cap ":") "/" "-")
            declared (check compiler output (str slug "-declared")
                            (str "(ns r.m (:export [main]) (:capabilities [" cap "])) (defn main [] :i64 " call ")"))
            _ (u/chk (and (= 0 (u/geti declared "exit")) (= "" (u/geti declared "stderr"))) declared)
            omitted (check compiler output (str slug "-omitted")
                           (str "(ns r.m (:export [main]) (:capabilities [:cli/args])) (defn main [] :i64 " call ")"))
            text (str (u/geti omitted "stderr") (u/geti omitted "stdout"))]
        (u/chk (and (not= 0 (u/geti omitted "exit")) (str/includes? text "E2176") (str/includes? text cap)) omitted)
        (.extend results (python/list [declared omitted]))
        (println cap "declared ok; omitted refused E2176")
        (.flush sys/stdout)))
    (.write_text (.joinpath output "receipt.json")
                 (str (json/dumps (u/pydict "schema" "amu.capability-declaration-names.v1" "issue" "KOTOBA-173"
                                            "compiler" (u/pydict "path" (str compiler) "sha256" compiler-sha256) "results" results)
                                  ** :indent 1) "\n"))
    (println "PASS_CAPABILITY_DECLARATION_NAMES")))

(defn -main [& args]
  (main (pathlib/Path (or (u/opt args "--compiler") (sys/exit "--compiler is required")))
        (or (u/opt args "--compiler-sha256") (sys/exit "--compiler-sha256 is required"))
        (pathlib/Path (or (u/opt args "--output") (sys/exit "--output is required")))))

(when (some #(or (= % "check-capability-declaration-names.cljc") (str/ends-with? % "/check-capability-declaration-names.cljc")) sys/argv)
  (apply -main *command-line-args*))
