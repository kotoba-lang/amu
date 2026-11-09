;; Exercise the browser keyword intern runtime on Wasm and JS (JUN-772). Ported from
;; check-browser-keyword-intern.py (Basilisp, JUN-974).
;; Run: basilisp run -p scripts/seed scripts/seed/check-browser-keyword-intern.cljc -- --compiler F
;;      [--baseline OLD_F] --output NEW_DIR --browser CHROME
(ns check-browser-keyword-intern
  (:require [basilisp.string :as str]
            [gate-util :as u]
            [macos-native-lib :as mac]
            [wasm32-browser-lib :as w])
  (:import json operator pathlib re sys))

(defn fail [msg] (throw (python/ValueError msg)))

(defn run [compiler-arg output-arg browser-arg baseline-arg]
  (let [out (.resolve (pathlib/Path output-arg))
        _ (.mkdir out ** :parents false :exist_ok false)
        src-path (pathlib/Path u/root "seed/tests/browser-keyword-intern.kotoba")
        source (.read_text src-path ** :encoding "utf-8")
        old "(string=? (keyword-name a) \"名\")"
        _ (when (not= (.count source old) 1) (fail "mutant anchor changed"))
        _ (doseq [[name text] [["good" source] ["mutant" (.replace source old (.replace old "\"名\"" "\"別\""))]]]
            (.write_text (pathlib/Path out (str name ".kotoba")) text ** :encoding "utf-8"))
        compiler (.resolve (pathlib/Path compiler-arg) ** :strict true)
        baseline (when baseline-arg (.resolve (pathlib/Path baseline-arg) ** :strict true))
        rows (atom [])]
    (doseq [[target ext] [["wasm32-browser" ".wasm"] ["js-browser" ".mjs"]]]
      (when baseline
        (let [refused (mac/native-run baseline out ["compile" "good.kotoba" "--target" target "--output" (str "baseline-" target)] :expected 1)]
          (when-not (u/has-bytes? (.encode "E7101") (.-stderr refused))
            (fail (str "baseline did not refuse missing runtime slot: " target)))))
      (doseq [name ["good" "mutant"]]
        (let [artifact (str name "-" target ext)]
          (mac/native-run compiler out ["compile" (str name ".kotoba") "--target" target "--output" artifact])
          (swap! rows conj [(str name "-" target) (pathlib/Path out artifact) (python/dict)]))))
    (let [browser (w/find-browser (str (.resolve (pathlib/Path browser-arg) ** :strict true)))
          [version lines] (w/run-js browser out @rows 600)]
      (doseq [[name expected] [["good-wasm32-browser" 0] ["mutant-wasm32-browser" 1] ["good-js-browser" 0] ["mutant-js-browser" 1]]]
        (let [line (operator/getitem lines name)
              report (or (.get line "report") "")]
          (when (or (not= (.get line "exit") 0) (some? (.get line "wasmTrap"))
                    (nil? (re/search (str "\\{:status :ok :result " expected "(?:\\s|\\})") report)))
            (fail (str name ": unexpected run " (python/repr line))))))
      (doseq [name ["good" "mutant"]]
        (when (not= (.get (operator/getitem lines (str name "-wasm32-browser")) "report")
                    (.get (operator/getitem lines (str name "-js-browser")) "report"))
          (fail (str name ": Wasm and JS result/fuel mismatch"))))
      (let [receipt (u/pydict "status" "PASS_BROWSER_KEYWORD_INTERN" "browser" version
                              "compiler" (mac/pin compiler) "baseline" (when baseline (mac/pin baseline))
                              "source" (mac/pin src-path)
                              "runs" (u/pydict-from (for [[name line] (.items lines)]
                                                      [name (u/pydict "report" (.get line "report") "exit" (.get line "exit")
                                                                      "wasmTrap" (.get line "wasmTrap"))])))]
        (.write_text (pathlib/Path out "browser-keyword-intern.json") (u/json-dump receipt))
        (println (str "PASS_BROWSER_KEYWORD_INTERN: 4 browser results" (when baseline " and baseline refusals")))))))

(defn -main [& args]
  (run (or (u/opt args "--compiler") (sys/exit "--compiler is required"))
       (or (u/opt args "--output") (sys/exit "--output is required"))
       (or (u/opt args "--browser") (sys/exit "--browser is required"))
       (u/opt args "--baseline")))

(when (some #(or (= % "check-browser-keyword-intern.cljc") (str/ends-with? % "/check-browser-keyword-intern.cljc")) sys/argv)
  (apply -main *command-line-args*))
