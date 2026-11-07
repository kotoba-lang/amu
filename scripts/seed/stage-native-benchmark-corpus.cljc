;; Stage unchanged original libraries and native export observations, not timing.
;; Ported from stage-native-benchmark-corpus.py (Basilisp).
;; Run: basilisp run scripts/seed/stage-native-benchmark-corpus.cljc -- (--one DIR | --complete DIR) --out OUT
(ns stage-native-benchmark-corpus
  (:require [basilisp.string :as str]
            [embench-candidate-lib :as C]
            [gate-util :as u]
            [native-profile :as profile])
  (:import json operator pathlib re subprocess sys))

(defn main [one complete out]
  (let [repo u/root
        one (when one (.resolve one)) complete (when complete (.resolve complete)) out (.resolve out)
        [compiler machine _target receipt sources] (C/provenance one complete)
        package (.joinpath repo "bench/embench/reproduce-20261015")
        _ (C/verify-bundle-data package (.joinpath repo "bench/embench/proof-v1/native-entry.kotoba"))
        table (json/loads (.read_text (.joinpath package "round-sa-m104-20261015/expected/measured-images.json")))
        workloads (vec (json/loads (.read_text (.joinpath package "round-sa-m104-20261015/workloads.json"))))
        _ (u/chk (and (= 19 (python/len table)) (= 19 (count workloads))))
        _ (u/chk (= 19 (count (set (map #(u/geti % "workload") workloads)))))
        _ (u/chk (= (set (python/list table)) (set (map #(u/geti % "workload") workloads))))
        _ (.mkdir out ** :mode 0700 :parents true :exist_ok false)
        _ (.write_bytes (.joinpath out "observer.cljc") (.read_bytes (.joinpath repo "scripts/seed/stage-native-benchmark-corpus.cljc")))
        report (u/pydict "status" "running" "compiler" (C/elf compiler machine) "receipt" (C/pin receipt)
                         "observer" (C/pin (.joinpath repo "scripts/seed/stage-native-benchmark-corpus.cljc")) "sources" sources
                         "executed" false "performanceQualified" false "qualificationReplacement" false "workloads" (python/list))
        persist (fn [] (profile/atomic-json (.joinpath out "observations.json") report))
        run (fn [row directory label argv]
              (let [env (python/dict {"PATH" "/nonexistent" "KEXE_ALLOW" "35,37,38,39" "KEXE_CAP_RESOURCES_35" (str out) "KEXE_STACK_BYTES" "8388608"})
                    [status stdout stderr]
                    (try (let [r (u/run-process argv env 300 :cwd directory)] [(.-returncode r) (.-stdout r) (.-stderr r)])
                         (catch subprocess/TimeoutExpired e ["timeout" (or (.-stdout e) (u/bytes-of)) (or (.-stderr e) (u/bytes-of))]))]
                (.write_bytes (.joinpath directory (str label ".stdout")) stdout)
                (.write_bytes (.joinpath directory (str label ".stderr")) stderr)
                (.append (u/geti row "calls")
                         (u/pydict "name" label "argv" (python/list (map str argv)) "exit" status
                                   "stdout" (C/pin (.joinpath directory (str label ".stdout"))) "stderr" (C/pin (.joinpath directory (str label ".stderr")))))
                (persist)
                (println (u/geti row "workload") label status)
                (.flush sys/stdout)
                [status stdout stderr]))]
    (persist)
    (doseq [spec workloads]
      (let [name (u/geti spec "workload")
            historical (u/geti table name)
            original (.joinpath (.joinpath package "ports") (str "official-" name ".kotoba"))
            identity (C/pin original)
            _ (u/chk (= (u/geti identity "sha256") (u/geti historical "sourceSHA256")))
            _ (u/chk (= (u/geti spec "nativeSHA256") (u/geti (u/geti historical "native") "sha256")))
            _ (u/chk (and (true? (u/geti spec "sourceFunctionsUnchanged")) (not (seq (u/geti spec "extraCaps")))))
            _ (u/chk (and (instance? python/int (u/geti spec "n")) (pos? (u/geti spec "n"))))
            directory (.joinpath out name)
            _ (.mkdir directory ** :mode 0700)
            [src lock image] (map #(.joinpath directory (str "original." %)) ["kotoba" "ksl" "kseed"])
            _ (.write_bytes src (.read_bytes original))
            _ (u/chk (u/deq (C/pin src) identity))
            _ (.write_text lock (str "KSL1\nentry " src "\nfile " (u/geti identity "sha256") " " src "\n"))
            row (u/pydict "workload" name "originalSource" identity "registered" spec "calls" (python/list)
                          "exports" (python/list) "status" "compiling" "sourceUnchanged" true)]
        (.append (u/geti report "workloads") row)
        ;; C-equivalent build (JUN-578 owner decision): the registered images use the scalar SHA-256 path, so the
        ;; benchmark corpus is compiled with --no-crypto-hw.
        (let [[status _ stderr] (run row directory "compile"
                                     [compiler "compile" src "--target" "aarch64-macos" "--output" image "--source-lock" lock
                                      "--source-lock-sha256" (u/geti (C/pin lock) "sha256") "--no-crypto-hw"])]
          (if (or (not (zero? status)) (u/nonempty? stderr) (not (.is_file image)))
            (do (operator/setitem row "status" "refused-native-library-compile") (persist))
            (do
              (operator/setitem row "image" (C/pin image))
              (operator/setitem row "historicalContainerMatches" (u/deq (u/geti row "image") (u/geti historical "kseed")))
              (doseq [[symbol expected] (.items (u/geti historical "exports"))]
                (let [[expected-offset arity] (vec expected)
                      _ (u/chk (re/fullmatch "[a-zA-Z0-9_-]+" symbol))
                      payload (.joinpath directory (str symbol ".bin"))
                      [status stdout stderr] (run row directory symbol [compiler "extract-native" image "--symbol" symbol "--output" payload])
                      header (re/fullmatch (.encode "\\{:ok true, :output \"([^\"\\r\\n]+)\", :offset ([0-9]+), :length ([0-9]+), :arity ([0-9]+)\\}\n") stdout)
                      valid (and (zero? status) (not (u/nonempty? stderr)) (some? header) (.is_file payload))
                      valid (and valid
                                 (= (.decode (.group header 1)) (str payload))
                                 (= (python/int (.group header 3)) (.-st_size (.stat payload)))
                                 (= (python/int (.group header 4)) arity)
                                 (<= 0 (python/int (.group header 2)) (dec (.-st_size (.stat payload))))
                                 (zero? (mod (python/int (.group header 2)) 4)))]
                  (.append (u/geti row "exports")
                           (u/pydict "name" symbol "valid" (boolean valid) "arity" arity
                                     "offset" (when valid (python/int (.group header 2)))
                                     "historicalOffsetMatches" (if valid (= (python/int (.group header 2)) expected-offset) false)
                                     "payload" (when valid (C/pin payload))
                                     "historicalPayloadMatches" (if valid (u/deq (C/pin payload) (u/geti historical "native")) false)))))
              (let [measured (into {} (for [e (u/geti row "exports")] [(u/geti e "name") e]))]
                (u/chk (contains? measured (u/geti spec "measuredSymbol")))
                (u/chk (= (u/geti spec "measuredArity") (u/geti (get measured (u/geti spec "measuredSymbol")) "arity")))
                ;; xgboost's original verifier consumes (state, n); do not adapt its API.
                (u/chk (contains? #{1 2} (u/geti (get measured "verify-state") "arity")))
                (operator/setitem row "verificationArguments"
                                  (python/list (if (= 1 (u/geti (get measured "verify-state") "arity")) ["state"] ["state" "registered-n"])))
                (u/chk (or (nil? (u/geti spec "seedSymbol")) (= 1 (u/geti (get measured (u/geti spec "seedSymbol")) "arity")))))
              (operator/setitem row "status"
                                (if (and (u/geti row "historicalContainerMatches")
                                         (every? #(and (u/geti % "valid") (u/geti % "historicalOffsetMatches") (u/geti % "historicalPayloadMatches")) (u/geti row "exports")))
                                  "native-original-library-byte-identical" "native-original-library-mismatch"))
              (u/chk (and (u/deq (C/pin original) identity) (u/deq (C/pin src) identity)))
              (persist))))))
    (u/chk (every? (fn [[name value]] (u/deq (C/pin (.joinpath repo name)) value)) (.items sources)))
    (let [rows (python/list (u/geti report "workloads"))
          historical (count (filter #(= "native-original-library-byte-identical" (u/geti % "status")) rows))
          passed (count (filter #(and (u/geti % "sourceUnchanged") (= 0 (u/geti (u/geti (u/geti % "calls") 0) "exit"))
                                      (seq (u/geti % "exports")) (every? (fn [e] (u/geti e "valid")) (u/geti % "exports"))) rows))]
      (doseq [[k v] [["status" (if (= 19 passed) "native-original-corpus-staged" "native-original-corpus-incomplete")]
                     ["observed" passed] ["historicalByteIdentical" historical]]]
        (operator/setitem report k v))
      (persist)
      (println (u/geti report "status") passed "/19; historical equality" historical "/19")
      (.flush sys/stdout)
      (if (= 19 passed) 0 2))))

(defn -main [& args]
  (let [one (u/opt args "--one") complete (u/opt args "--complete")]
    (sys/exit (main (when one (pathlib/Path one)) (when complete (pathlib/Path complete))
                    (pathlib/Path (or (u/opt args "--out") (sys/exit "--out is required")))))))

(when (some #(or (= % "stage-native-benchmark-corpus.cljc") (str/ends-with? % "/stage-native-benchmark-corpus.cljc")) sys/argv)
  (apply -main *command-line-args*))
