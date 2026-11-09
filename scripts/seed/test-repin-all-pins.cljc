;; Negative controls for repin-all-pins --check (JUN-759). Mac arm64. Ported from test-repin-all-pins.py
;; (Basilisp, JUN-974).
;; usage: basilisp run -p scripts/seed scripts/seed/test-repin-all-pins.cljc -- [--mac-build DIR]
;; DIR is a mac-root fixed-point build of the current tree (default: built here). Each control runs the checker on
;; a scratch copy of the pin inputs: current tree -> exit 0; stale policy amuSelfhostGate pin, stale controller pin
;; row, stale kotoba-gate image row, stale seed/79 role hash -> exit 10; core module changed (adoption) -> exit 11.
;; A control that does not fail as required fails this test.
(ns test-repin-all-pins
  (:require [basilisp.string :as str]
            [gate-util :as u])
  (:import json operator pathlib re shutil subprocess sys tempfile))

(def root u/root)
(def seed-dir (pathlib/Path root "scripts/seed"))
(def tool (pathlib/Path seed-dir "repin-all-pins.cljc"))

(defn basilisp [& args]
  (subprocess/run (python/list (concat ["basilisp" "run" "-p" (str seed-dir)] (map str args))) ** :capture_output true :text true :cwd root))

(defn copy-tree [dst]
  (shutil/copytree (pathlib/Path root "seed") (pathlib/Path dst "seed") ** :symlinks true))

(defn sub-once [path pattern repl]
  (let [t (.read_text path)
        [n c] (re/subn pattern repl t ** :count 1)]
    (u/chk (= c 1) (str [path pattern]))
    (.write_text path n)))

(defn flip-policy [s]
  (let [p (pathlib/Path s "seed/cdci/policy.json")
        d (json/loads (.read_text p))]
    (operator/setitem d "amuSelfhostGateSHA256" (apply str (repeat 64 "0")))
    (.write_text p (u/json-dump d))))

(defn -main [& args]
  (let [mac-arg (u/opt args "--mac-build")
        work (pathlib/Path (tempfile/mkdtemp ** :prefix "test-repin-all-"))
        mac (if mac-arg
              (.resolve (pathlib/Path mac-arg))
              (do (let [r (subprocess/run (python/list ["basilisp" "run" "-p" (str seed-dir) (str (pathlib/Path seed-dir "check-aiueos-user-macos-native.cljc"))
                                                        "--" "--output" (str (pathlib/Path work "mac-root"))]) ** :cwd root :check true)] r)
                  (.resolve (pathlib/Path work "mac-root"))))
        control (fn [name mutate want]
                  (let [scratch (pathlib/Path work name)]
                    (.mkdir scratch)
                    (copy-tree scratch)
                    (mutate scratch)
                    (let [r (basilisp tool "--root" scratch "--check" "--mac-build" mac)
                          ok (= (.-returncode r) want)]
                      (println (str (if ok "PASS " "FAIL ") name) "exit" (.-returncode r) "want" want)
                      (when-not ok
                        (let [o (.-stdout r) e (.-stderr r)]
                          (println (subs o (max 0 (- (count o) 600))) (subs e (max 0 (- (count e) 600))))))
                      ok)))
        results [(control "current" (fn [_] nil) 0)
                 (control "stale-policy" flip-policy 10)
                 (control "stale-controller-row" (fn [s] (sub-once (pathlib/Path s "seed/cdci/controller.kotoba") "(h2_0 \\(kc-word [^\\n]*?)0x[0-9a-f]+" "\\g<1>0x3030303030303030")) 10)
                 (control "stale-gate-row" (fn [s] (sub-once (pathlib/Path s "seed/cdci/kotoba-gate.kotoba") "(h1_0 \\(kc-word [^\\n]*?)0x[0-9a-f]+" "\\g<1>0x3030303030303030")) 10)
                 (control "stale-role-hash" (fn [s] (sub-once (pathlib/Path s "seed/79-native-cdci.kotoba") "(string=\\? role \"controller\"\\) \")[0-9a-f]{64}" (str "\\g<1>" (apply str (repeat 64 "0"))))) 10)
                 (control "core-drift" (fn [s] (let [p (pathlib/Path s "seed/10-lex.kotoba")] (.write_text p (str (.read_text p) "\n;; drift\n")))) 11)]]
    (shutil/rmtree work ** :ignore_errors true)
    (if (every? true? results)
      (do (println "PASS_REPIN_ALL_PINS_NEGATIVE_CONTROLS") (sys/exit 0))
      (sys/exit 1))))

(when (some #(or (= % "test-repin-all-pins.cljc") (str/ends-with? % "/test-repin-all-pins.cljc")) sys/argv)
  (apply -main *command-line-args*))
