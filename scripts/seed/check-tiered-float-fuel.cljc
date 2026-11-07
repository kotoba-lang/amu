;; Observe float results and fuel using a pinned tiered native bootstrap.
;;
;; This bounded F/runner test also checks the C0 producer in full tier; it does not claim C0 executed the compiled
;; cases, complete compiler adoption, CDCI qualification, or performance.
;; Ported from check-tiered-float-fuel.py (Basilisp). Linux arm64 only.
;; Run: basilisp run scripts/seed/check-tiered-float-fuel.cljc -- --repo DIR --bootstrap DIR --output OUT
(ns check-tiered-float-fuel
  (:require [basilisp.string :as str]
            [gate-util :as u])
  (:import json operator pathlib platform re sys))

(defn- fail [message] (throw (python/ValueError (str message))))

(defn- pin-of [p]
  (u/pydict "bytes" (python/len (.read_bytes p)) "sha256" (u/sha256-hex (.read_bytes p))))

(defn- check-source-graph! [repo graph what]
  (doseq [[name expected] (.items graph)]
    (let [path (pathlib/Path name)]
      (when (or (.is_absolute path) (contains? (set (.-parts path)) "..") (not (u/deq (pin-of (.joinpath repo path)) expected)))
        (fail (str what name))))))

(defn main [repo boot out]
  (when-not (and (= "Linux" (platform/system)) (contains? #{"aarch64" "arm64"} (platform/machine)))
    (fail "requires a Linux arm64 execution host"))
  (let [repo (.resolve repo ** :strict true) boot (.resolve boot ** :strict true) out (.resolve out)
        this (.joinpath u/root "scripts/seed/check-tiered-float-fuel.cljc")
        receipt-path (.joinpath boot "selfhost-bootstrap.json")
        receipt (u/read-json receipt-path)
        _ (when (or (not= "PASS_LOADERLESS_SELFHOST_BOOTSTRAP" (.get receipt "status")) (not (contains? #{"pr" "main" "full"} (.get receipt "tier"))))
            (fail "invalid bootstrap status"))
        generation (u/geti (u/geti receipt "generations") -1)
        producer (.joinpath boot (str (u/geti generation "name") ".elf"))
        _ (when (not (u/deq (pin-of producer) (u/geti generation "image"))) (fail "bootstrap F image mismatch"))
        _ (check-source-graph! repo (u/geti (u/geti receipt "sourceGraph") "full") "bootstrap source drift: ")
        _ (check-source-graph! repo (u/geti (u/geti receipt "adopted") "sourceGraph") "bootstrap source drift: ")
        c0 (when (= "full" (u/geti receipt "tier"))
             (let [c0 (.joinpath boot "C0.elf")]
               (when (not (u/deq (pin-of c0) (u/geti (u/geti (u/geti receipt "provenance") "coreStatic") "C0"))) (fail "bootstrap C0 image mismatch"))
               (check-source-graph! repo (u/geti (u/geti (u/geti receipt "provenance") "coreStatic") "sourceGraph") "bootstrap C0 source drift: ")
               c0))
        _ (.mkdir out ** :parents true :exist_ok false)
        source (.joinpath repo "seed/x86_64-kx64-runner.kotoba")
        tracked (cond-> [receipt-path producer source (.joinpath repo "seed/float-cases.json") (.joinpath repo "seed/static-cases.json") this]
                  c0 (conj c0))
        before (into {} (for [p tracked] [(str p) (pin-of p)]))
        _ (.write_bytes (.joinpath out "runner.kotoba") (.read_bytes source))
        env {"PATH" "/nonexistent" "KEXE_CAP_RESOURCES_35" (str out) "KEXE_STACK_BYTES" "8388608"}
        rows (python/list)
        run (fn [name args & {:keys [overrides expected] :or {expected 0}}]
              (let [e (python/dict (merge env overrides))
                    p (u/run-process args e 900 :cwd out)]
                (.write_bytes (.joinpath out (str name ".stdout")) (.-stdout p))
                (.write_bytes (.joinpath out (str name ".stderr")) (.-stderr p))
                (when (and (some? expected) (or (not= expected (.-returncode p)) (u/nonempty? (.-stderr p))))
                  (throw (python/RuntimeError (str [name (.-returncode p) (u/bslice (.-stderr p) -500 nil)]))))
                (.append rows (u/pydict "name" name "exit" (.-returncode p) "stdout" (pin-of (.joinpath out (str name ".stdout")))
                                        "stderr" (pin-of (.joinpath out (str name ".stderr")))))
                p))
        runner (.joinpath out "runner.elf")
        _ (run "runner-compile" [producer "compile" (.joinpath out "runner.kotoba") "--target" "aarch64-linux" "--output" runner "--format" "runner"])
        _ (.chmod runner 0700)
        _ (when (not (u/deq (pin-of runner) (u/geti (u/geti receipt "built") "aarch64Runner"))) (fail "fresh runner differs from bootstrap runner pin"))
        compile-payload (fn [name body & [compiler]]
                          (let [compiler (or compiler producer)
                                source-file (.joinpath out (str name ".kotoba"))]
                            (.write_text source-file body)
                            (let [container (.joinpath out (str name ".kseed")) raw (.joinpath out (str name ".bin"))]
                              (run (str name "-compile") [compiler "compile" source-file "--target" "aarch64-macos" "--output" container])
                              (run (str name "-extract") [compiler "extract-native" container "--symbol" "main" "--output" raw])
                              raw)))
        execute (fn [name payload fuel]
                  (run name [runner payload "0" "0" "aarch64" "35,37,38,39" "--"]
                       :overrides {"KEXE_COMMAND" "1" "KEXE_STRUCTURED_REPORT" "1" "KEXE_FUEL" (str fuel) "KEXE_ALLOW" "-"} :expected nil))
        corpus (.joinpath repo "seed/float-cases.json")
        cases (vec (u/geti (u/read-json corpus) "cases"))
        _ (when (not= 11 (count cases)) (fail "float corpus changed"))
        re-int (fn [pattern data] (re/search (.encode pattern) data))
        results (python/list)]
    (doseq [case cases]
      (let [name (u/geti case "name")
            _ (when-not (re/fullmatch "[a-z0-9-]+" name) (fail "invalid case name"))
            payload (compile-payload name (u/geti case "source"))
            p (execute (str name "-run") payload 1000000)
            fuel (re-int ":remaining ([0-9]+)" (.-stdout p))
            result (re-int ":result (-?[0-9]+)" (.-stdout p))
            observed (u/pydict "exit" (.-returncode p) "remainingFuel" (when fuel (python/int (.group fuel 1))))]
        (when (or (u/nonempty? (.-stderr p)) (not (u/deq observed (u/geti case "reference"))) (u/geti case "trap") (nil? result)
                  (not= (python/int (.group result 1)) (u/geti case "result")) (u/has-bytes? (.encode ":status :trap") (.-stdout p)))
          (fail (str ["float result/fuel mismatch" name observed (u/bslice (.-stdout p) -500 nil) (u/bslice (.-stderr p) -500 nil)])))
        (.append results (u/pydict "name" name "observed" observed "result" (python/int (.group result 1)) "payload" (pin-of payload)))
        (when c0
          (let [c0-payload (compile-payload (str "c0-" name) (u/geti case "source") c0)
                c0-result (execute (str "c0-" name "-run") c0-payload 1000000)
                c0-fuel (re-int ":remaining ([0-9]+)" (.-stdout c0-result))
                c0-value (re-int ":result (-?[0-9]+)" (.-stdout c0-result))
                c0-observed (u/pydict "exit" (.-returncode c0-result) "remainingFuel" (when c0-fuel (python/int (.group c0-fuel 1))))]
            (when (or (u/nonempty? (.-stderr c0-result)) (not (u/deq c0-observed (u/geti case "reference"))) (nil? c0-value)
                      (not= (python/int (.group c0-value 1)) (u/geti case "result")) (u/has-bytes? (.encode ":status :trap") (.-stdout c0-result)))
              (fail (str ["C0 float result/fuel mismatch" name c0-observed (u/bslice (.-stdout c0-result) -500 nil)])))
            (operator/setitem (u/geti results -1) "c0" (u/pydict "observed" c0-observed "result" (python/int (.group c0-value 1)) "payload" (pin-of c0-payload)))))
        (println name observed)
        (.flush sys/stdout)))
    (let [static (u/geti (u/read-json (.joinpath repo "seed/static-cases.json")) "cases")
          fuel-case (first (filter #(= "string-call" (u/geti % "name")) static))
          _ (when (not= 999998 (u/geti (u/geti fuel-case "reference") "remainingFuel")) (fail "fuel-control reference drift"))
          payload (compile-payload "fuel-control" (u/geti fuel-case "source"))
          fuel (execute "fuel-control-run" payload 1)
          _ (when (or (not= 120 (.-returncode fuel)) (not (u/has-bytes? (.encode ":status :trap") (.-stdout fuel))) (re/search (.encode ":result (-?[0-9]+)") (.-stdout fuel)))
              (fail (str ["low-fuel control did not trap" (.-returncode fuel) (u/bslice (.-stdout fuel) -500 nil) (u/bslice (.-stderr fuel) -500 nil)])))
          _ (when c0
              (let [c0-fuel-payload (compile-payload "c0-fuel-control" (u/geti fuel-case "source") c0)
                    c0-fuel (execute "c0-fuel-control-run" c0-fuel-payload 1)]
                (when (or (not= 120 (.-returncode c0-fuel)) (not (u/has-bytes? (.encode ":status :trap") (.-stdout c0-fuel))) (re/search (.encode ":result (-?[0-9]+)") (.-stdout c0-fuel)))
                  (fail (str ["C0 low-fuel control did not trap" (.-returncode c0-fuel) (u/bslice (.-stdout c0-fuel) -500 nil)])))))
          bad (.joinpath out "unknown.kotoba")
          _ (.write_text bad "(ns unknown (:export [main]))\n(defn main [] :i64 (does-not-exist 1))\n")
          bad-image (.joinpath out "unknown.kseed")
          bad-result (run "compile-refusal" [producer "compile" bad "--target" "aarch64-macos" "--output" bad-image] :expected nil)
          _ (when (or (zero? (.-returncode bad-result)) (.exists bad-image) (not (u/has-bytes? (.encode "E2101") (.-stderr bad-result))))
              (fail (str ["compile negative did not refuse" (.-returncode bad-result) (u/bslice (.-stderr bad-result) -500 nil)])))
          _ (when c0
              (let [bad-c0-image (.joinpath out "unknown-c0.kseed")
                    c0-bad (run "c0-compile-refusal" [c0 "compile" bad "--target" "aarch64-macos" "--output" bad-c0-image] :expected nil)]
                (when (or (zero? (.-returncode c0-bad)) (.exists bad-c0-image) (not (u/has-bytes? (.encode "E2101") (.-stderr c0-bad))))
                  (fail (str ["C0 compile negative did not refuse" (.-returncode c0-bad) (u/bslice (.-stderr c0-bad) -500 nil)])))))
          _ (when (some #(not (u/deq (pin-of %) (get before (str %)))) tracked)
              (fail "bootstrap, source, corpus or observer changed during run"))
          report (u/pydict "status" "PASS_CURRENT_ARM_FLOAT_RESULT_FUEL"
                           "host" (python/list [(platform/system) (platform/machine) (platform/release)])
                           "bootstrap" (pin-of receipt-path) "compiler" (pin-of producer) "runner" (pin-of runner) "runnerSource" (pin-of source)
                           "floatCorpus" (pin-of corpus) "staticCorpus" (pin-of (.joinpath repo "seed/static-cases.json"))
                           "observer" (pin-of this) "cases" results
                           "fuelNegative" (u/pydict "exit" (.-returncode fuel) "stdout" (pin-of (.joinpath out "fuel-control-run.stdout")))
                           "compileNegative" (u/pydict "exit" (.-returncode bad-result) "stderr" (pin-of (.joinpath out "compile-refusal.stderr")))
                           "calls" rows "c0CompiledCases" (some? c0) "c0ExecutedCases" false
                           "c0Compiler" (when c0 (pin-of c0)) "fullNativeCorpusQualified" false "publicReleaseReady" false)]
      (.write_text (.joinpath out "receipt.json") (u/json-dump report))
      (println (u/geti report "status") (python/len results))
      (.flush sys/stdout))))

(defn -main [& args]
  (let [need (fn [k] (pathlib/Path (or (u/opt args k) (sys/exit (str k " is required")))))]
    (main (need "--repo") (need "--bootstrap") (need "--output"))))

(when (some #(or (= % "check-tiered-float-fuel.cljc") (str/ends-with? % "/check-tiered-float-fuel.cljc")) sys/argv)
  (apply -main *command-line-args*))
