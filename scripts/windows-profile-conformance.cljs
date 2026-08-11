#!/usr/bin/env nbb
(ns windows-profile-conformance
  (:require [cljs.reader :as reader]
            [scripts.lib :as lib]
            ["node:child_process" :as child]
            ["node:fs" :as fs]
            ["node:os" :as os]
            ["node:path" :as path]))

(def tmp (.mkdtempSync fs (.join path (.tmpdir os) "kotoba-windows-profile-")))
(def nbb-cli (.join path lib/root "node_modules" "nbb" "cli.js"))
(def kotoba (.join path lib/root "bin" "kotoba"))
(def source (.join path lib/root "examples" "structured.kotoba"))
(def nested-source (.join path lib/root "examples" "nested-record.kotoba"))
(def held-source (.join path lib/root "examples" "held-operations.kotoba"))
(def arm64? (= "arm64" (.-arch js/process)))
(def target (if arm64? "aarch64-windows" "x86_64-windows"))
(def target-profile (if arm64? ":aarch64-windows-kotoba-v1" ":x86_64-windows-kotoba-v1"))
(def isa (if arm64? "aarch64" "x86_64"))
(def abi (if arm64? ":kotoba-aapcs64-v1" ":kotoba-sysv-v1"))
(def context-mode (if arm64? ":hidden-context-x7" ":hidden-context-r9"))
(defn artifact [name] (.join path tmp name))
(defn run-k! [args]
  (let [result (.spawnSync child js/process.execPath (clj->js (into [nbb-cli kotoba "-M"] args))
                           #js {:cwd lib/root :encoding "utf8" :maxBuffer 1048576})]
    (when (.-error result) (throw (.-error result)))
    (lib/ensure! (zero? (or (.-status result) 70))
                 (str "windows-profile: command failed: " (.-stderr result)))
    result))
(defn run-k-fails! [args needle]
  (let [result (.spawnSync child js/process.execPath (clj->js (into [nbb-cli kotoba "-M"] args))
                           #js {:cwd lib/root :encoding "utf8" :maxBuffer 1048576})
        status (or (.-status result) 70)
        stderr (or (.-stderr result) "")]
    (when (.-error result) (throw (.-error result)))
    (lib/ensure! (not= 0 status) "windows-profile: negative vector unexpectedly succeeded")
    (lib/ensure! (.includes stderr needle)
                 (str "windows-profile: negative vector missed " needle ": " stderr))
    result))
(defn run-external
  ([command args] (run-external command args {} false))
  ([command args env allow-failure?]
   (let [result (.spawnSync child command (clj->js args)
                            #js {:cwd lib/root :encoding "utf8" :maxBuffer 1048576
                                 :env (js/Object.assign #js {} js/process.env (clj->js env))})]
     (when (.-error result) (throw (.-error result)))
     (when-not (or allow-failure? (zero? (or (.-status result) 70)))
       (throw (js/Error. (str "windows-profile: external command failed: " (.-stderr result)))))
     result)))
(defn extract! [kexe symbol output]
  (let [result (run-k! ["extract-native" kexe "--symbol" symbol "--output" output])
        text (.-stdout result)
        [_ offset] (re-find #":offset ([0-9]+)" text)
        [_ arity] (re-find #":arity ([0-9]+)" text)]
    (lib/ensure! (and offset arity) (str "windows-profile: missing export metadata for " symbol))
    [offset arity]))
(defn loader-check! [loader raw offset arity expected & args]
  (let [result (run-external loader (into [raw offset arity isa "-"] args))]
    (lib/ensure! (= expected (.trim (.-stdout result)))
                 (str "windows-profile: runtime result mismatch, expected " expected))))
(defn loader-report! [loader raw offset arity result-type args]
  (let [result (run-external loader (into [raw offset arity isa "-"] args)
                             {:KEXE_STRUCTURED_REPORT "1"
                              :KEXE_RESULT_TYPE result-type}
                             false)
        report (reader/read-string (.trim (.-stdout result)))]
    (lib/ensure! (= :ok (:status report))
                 (str "windows-profile: tagged runtime did not report :ok: " report))
    report))

(try
  (run-k! ["compile" source "--target" target "--output" (artifact "first.kexe")])
  (run-k! ["compile" source "--target" target "--output" (artifact "second.kexe")])
  (let [first (.readFileSync fs (artifact "first.kexe"))
        second (.readFileSync fs (artifact "second.kexe"))
        text (.toString first "utf8")]
    (lib/ensure! (.equals first second) "windows-profile: artifact is not reproducible")
    (doseq [needle [(str ":target " target-profile)
                    ":os :windows" (str ":abi " abi)
                    ":runtime :kotoba-windows-supervisor-v1"
                    (str ":mode " context-mode)]]
      (lib/ensure! (.includes text needle) (str "windows-profile: missing binding " needle))))
  (run-k! ["verify" (artifact "first.kexe")])
  (println (str "windows-profile: reproducible " isa " Windows KEXE verified"))
  (run-k! ["compile" nested-source "--target" target
           "--output" (artifact "nested-record.kexe")])
  (run-k! ["verify" (artifact "nested-record.kexe")])
  (println (str "windows-profile: recursive-record " isa
                " Windows KEXE verified"))
  (run-k! ["compile" held-source "--target" target
           "--output" (artifact "held-operations.kexe")])
  (run-k! ["verify" (artifact "held-operations.kexe")])
  (println (str "windows-profile: aggregate-variant callable bounded-apply " isa
                " Windows KEXE verified"))
  ;; Compile the entryless tagged-value library on every host. Runtime vectors
  ;; still require Windows, but native-library admission is target semantics and
  ;; must not regress silently on non-Windows CI nodes.
  (.writeFileSync
   fs (artifact "tagged-boundary.kotoba")
   (str "(ns maturity.windows-tagged\n"
        "  (:export [echo-option make-none make-some inspect-option\n"
        "            echo-result make-ok make-err inspect-result]))\n"
        "(defn echo-option [value :option-i64] :option-i64 value)\n"
        "(defn make-none [witness :i64] :option-i64 (option-none))\n"
        "(defn make-some [value :i64] :option-i64 (option-some value))\n"
        "(defn inspect-option [value :option-i64] :i64 (option-value value 99))\n"
        "(defn echo-result [value :result-i64] :result-i64 value)\n"
        "(defn make-ok [value :i64] :result-i64 (result-ok value))\n"
        "(defn make-err [value :i64] :result-i64 (result-err value))\n"
        "(defn inspect-result [value :result-i64] :i64\n"
        "  (+ (result-value value 1000) (result-error value 2000)))\n"))
  (run-k! ["compile" (artifact "tagged-boundary.kotoba")
           "--target" target "--output" (artifact "tagged-boundary.kexe")])
  (run-k! ["verify" (artifact "tagged-boundary.kexe")])
  (println (str "windows-profile: entryless " isa " Windows library verified"))
  (when (= "win32" (.-platform js/process))
    (let [loader (artifact "kexe-loader-windows.exe")
          raw (artifact "program.bin")
          _ (run-external "clang" ["-std=c11" "-O2" "-Wall" "-Wextra" "-Werror"
                                    (.join path lib/root "tools/kexe_loader_windows.c")
                                    "-o" loader "-ladvapi32" "-luserenv" "-lws2_32"
                                    "-lfwpuclnt" "-lrpcrt4"])
          [main-offset main-arity] (extract! (artifact "first.kexe") "main" raw)
          [score-offset score-arity] (extract! (artifact "first.kexe") "score" raw)
          [calc-offset calc-arity] (extract! (artifact "first.kexe") "calc" raw)]
      (loader-check! loader raw main-offset main-arity "42")
      (loader-check! loader raw score-offset score-arity "12" "-7" "2")
      (loader-check! loader raw calc-offset calc-arity "21" "20" "4")
      (let [nested-raw (artifact "nested-record.bin")
            [nested-offset nested-arity]
            (extract! (artifact "nested-record.kexe") "nested-score" nested-raw)]
        (loader-check! loader nested-raw nested-offset nested-arity "15"))
      (let [raw-tagged (artifact "tagged-boundary.bin")
            exports (into {}
                          (map (fn [symbol]
                                 [symbol (extract! (artifact "tagged-boundary.kexe")
                                                   symbol raw-tagged)]))
                          ["echo-option" "make-none" "make-some" "inspect-option"
                           "echo-result" "make-ok" "make-err" "inspect-result"])
            tagged (fn [symbol result-type args]
                     (let [[offset arity] (get exports symbol)]
                       (loader-report! loader raw-tagged offset arity result-type args)))
            word (fn [report]
                   (select-keys report [:status :result-type :result-tag :result-word]))]
        (lib/ensure!
         (= {:status :ok :result-type :option-i64 :result-tag false :result-word 0}
            (word (tagged "echo-option" "option-i64" ["o:none"])))
         "windows-profile: option none did not cross the host boundary")
        (lib/ensure!
         (= {:status :ok :result-type :option-i64 :result-tag true
             :result-word -9223372036854775808}
            (word (tagged "echo-option" "option-i64"
                          ["o:some:-9223372036854775808"])))
         "windows-profile: option some/MIN did not cross the host boundary")
        (lib/ensure!
         (= {:status :ok :result-type :option-i64 :result-tag false :result-word 0}
            (word (tagged "make-none" "option-i64" ["0"])))
         "windows-profile: guest option-none construction was not observed")
        (lib/ensure!
         (= {:status :ok :result-type :option-i64 :result-tag true
             :result-word 9223372036854775807}
            (word (tagged "make-some" "option-i64" ["9223372036854775807"])))
         "windows-profile: guest option-some/MAX construction was not observed")
        (let [[offset arity] (get exports "inspect-option")]
          (loader-check! loader raw-tagged offset arity "99" "o:none")
          (loader-check! loader raw-tagged offset arity "-7" "o:some:-7"))
        (lib/ensure!
         (= {:status :ok :result-type :result-i64 :result-tag true
             :result-word -9223372036854775808}
            (word (tagged "echo-result" "result-i64"
                          ["e:ok:-9223372036854775808"])))
         "windows-profile: result ok/MIN did not cross the host boundary")
        (lib/ensure!
         (= {:status :ok :result-type :result-i64 :result-tag false
             :result-word 9223372036854775807}
            (word (tagged "echo-result" "result-i64"
                          ["e:err:9223372036854775807"])))
         "windows-profile: result err/MAX did not cross the host boundary")
        (lib/ensure!
         (= {:status :ok :result-type :result-i64 :result-tag true :result-word -9}
            (word (tagged "make-ok" "result-i64" ["-9"])))
         "windows-profile: guest result-ok construction was not observed")
        (lib/ensure!
         (= {:status :ok :result-type :result-i64 :result-tag false :result-word 11}
            (word (tagged "make-err" "result-i64" ["11"])))
         "windows-profile: guest result-err construction was not observed")
        (let [[offset arity] (get exports "inspect-result")]
          (loader-check! loader raw-tagged offset arity "2007" "e:ok:7")
          (loader-check! loader raw-tagged offset arity "1008" "e:err:8"))
        (doseq [[result-type expected-exit reason]
                [["option-i64" 128 ":reason :invalid-option-i64"]
                 ["result-i64" 129 ":reason :invalid-result-i64"]]]
          (let [invalid (run-external loader [raw main-offset main-arity isa "-"]
                                      {:KEXE_STRUCTURED_REPORT "1"
                                       :KEXE_RESULT_TYPE result-type}
                                      true)]
            (lib/ensure! (= expected-exit (.-status invalid))
                         (str "windows-profile: " result-type " invalid handle exit mismatch"))
            (lib/ensure! (.includes (or (.-stderr invalid) "") reason)
                         (str "windows-profile: " result-type " invalid handle reason missing"))))
        (println "windows-profile: option/result host boundary vectors passed"))
      (let [structured (run-external loader [raw main-offset main-arity isa "-"]
                                             {:KEXE_STRUCTURED_REPORT "1"} false)]
        (lib/ensure! (= "{:status :ok :result 42 :fuel {:initial 512 :remaining 509} :heap {:capacity 4096 :used 0}}"
                        (.trim (.-stdout structured)))
                     "windows-profile: structured supervisor report mismatch"))
      (.writeFileSync
       fs (artifact "typed-capability.kotoba")
       "(defn main [] :i64\n  (+ (string-byte-length (typed-cap-call 4 :string :string \"hello😀\"))\n     (option-value (typed-cap-call 4 :option-i64 :option-i64 (some 41)) 0)\n     (option-value (typed-cap-call 4 :option-i64 :option-i64 (option-none)) 5)\n     (result-value (typed-cap-call 4 :result-i64 :result-i64 (result-ok 7)) 0)\n     (result-error (typed-cap-call 4 :result-i64 :result-i64 (result-err 9)) 0)))\n")
      (.writeFileSync fs (artifact "typed-policy.edn") "{:allow #{[:cap/call 4]}}\n")
      (run-k! ["compile" (artifact "typed-capability.kotoba")
               "--target" target "--policy" (artifact "typed-policy.edn")
               "--output" (artifact "typed-capability.kexe")])
      (let [[typed-offset typed-arity]
            (extract! (artifact "typed-capability.kexe") "main"
                      (artifact "typed-capability.bin"))
            typed-result
            (run-external loader [(artifact "typed-capability.bin")
                                  typed-offset typed-arity isa "4"])]
        (lib/ensure! (= "71" (.trim (.-stdout typed-result)))
                     "windows-profile: typed string/option/result callback mismatch"))
      (doseq [[probe reason] [[:KEXE_FILESYSTEM_PROBE "filesystem-denied"]
                              [:KEXE_PROCESS_PROBE "process-denied"]
                              [:KEXE_NETWORK_PROBE "network-denied"]
                              [:KEXE_NETWORK_LISTEN_PROBE "network-listen-denied"]]]
        (let [result (run-external loader [raw main-offset main-arity isa "-"]
                                   {probe "1"} true)
              status (.-status result)
              stderr (or (.-stderr result) "")]
          ;; Include the actual exit status and the loader's own stderr
          ;; diagnostics in the failure message -- previously this reported
          ;; only the generic "exit mismatch"/"report mismatch" text, which
          ;; discarded the child process's own diagnostic output and made a
          ;; CI failure here undiagnosable from the log alone (see the
          ;; 2026-07 windows-network-denial PR #67 CI failure).
          (lib/ensure! (= 77 status)
                       (str "windows-profile: " reason " exit mismatch (status=" status "): " stderr))
          (lib/ensure! (.includes stderr (str ":reason :" reason))
                       (str "windows-profile: " reason " report mismatch (status=" status "): " stderr))))
      (run-k! ["compile" (.join path lib/root "examples/heap.kotoba")
               "--target" target "--output" (artifact "heap.kexe")])
      (let [[offset arity] (extract! (artifact "heap.kexe") "main" (artifact "heap.bin"))
            report (run-external loader [(artifact "heap.bin") offset arity isa "-"]
                                 {:KEXE_STRUCTURED_REPORT "1"} false)]
        (lib/ensure! (= "{:status :ok :result 42 :fuel {:initial 512 :remaining 511} :heap {:capacity 4096 :used 2}}"
                        (.trim (.-stdout report)))
                     "windows-profile: bounded heap report mismatch"))
      (run-k! ["compile" (.join path lib/root "tests/browser/capability.kotoba")
               "--target" target "--policy" (.join path lib/root "examples/capability-policy.edn")
               "--output" (artifact "capability.kexe")])
      (let [[offset arity] (extract! (artifact "capability.kexe") "main" (artifact "capability.bin"))]
        (let [allowed (run-external loader [(artifact "capability.bin") offset arity isa "7"])]
          (lib/ensure! (= "42" (.trim (.-stdout allowed))) "windows-profile: capability result mismatch"))
        (let [denied (run-external loader [(artifact "capability.bin") offset arity isa "-"] {} true)]
          (lib/ensure! (not= 0 (.-status denied)) "windows-profile: denied capability executed")))
      (println (str "windows-profile: W^X supervisor, " abi
                    " adapter, sandbox, capability, fuel, and heap vectors passed"))
      (.writeFileSync fs (artifact "policy.edn") "{:allow #{}}\n")
      (.writeFileSync fs (artifact "input.edn") "{:args []}\n")
      (run-k! ["keygen" "--output" (artifact "key.edn")])
      (run-k! ["public-key" (artifact "key.edn") "--output" (artifact "public.edn")])
      (run-k! ["trust-key" (artifact "public.edn") "--output" (artifact "trust.edn")])
      (run-k! ["measure-runtime" "--output" (artifact "runtime.edn")
               "--loader-output" (artifact "measured-loader.exe")])
      (run-k! ["trust-runtime" (artifact "runtime.edn") "--trust" (artifact "trust.edn")
               "--output" (artifact "runtime-trust.edn")])
      (run-k! ["sign" (artifact "first.kexe") "--key" (artifact "key.edn")
               "--not-before" "1000" "--expires" "2000" "--output" (artifact "signed.kexe")])
      (run-k! ["run" (artifact "signed.kexe") "--trust" (artifact "runtime-trust.edn")
               "--runtime" (artifact "runtime.edn") "--loader" (artifact "measured-loader.exe")
               "--policy" (artifact "policy.edn") "--input" (artifact "input.edn")
               "--executor-key" (artifact "key.edn") "--now" "1500"
               "--result-output" (artifact "result.edn") "--output" (artifact "receipt.edn")])
      (run-k! ["verify-receipt" (artifact "receipt.edn")
               "--signed" (artifact "signed.kexe") "--trust" (artifact "runtime-trust.edn")
               "--policy" (artifact "policy.edn") "--input" (artifact "input.edn")
               "--result" (artifact "result.edn") "--now" "1500"])
      (let [result (.readFileSync fs (artifact "result.edn") "utf8")]
        (lib/ensure! (and (.includes result ":status :ok")
                          (.includes result ":result 42")
                          (.includes result ":format :kotoba.native-runtime/v6"))
                     "windows-profile: measured product evidence mismatch"))
      (lib/ensure! (.includes (.readFileSync fs (artifact "runtime.edn") "utf8")
                              ":runtime :kotoba-windows-supervisor-v1")
                   "windows-profile: measured runtime profile mismatch")
      (let [run-args (fn [runtime loader suffix]
                       ["run" (artifact "signed.kexe") "--trust" (artifact "runtime-trust.edn")
                        "--runtime" runtime "--loader" loader
                        "--policy" (artifact "policy.edn") "--input" (artifact "input.edn")
                        "--executor-key" (artifact "key.edn") "--now" "1500"
                        "--result-output" (artifact (str suffix "-result.edn"))
                        "--output" (artifact (str suffix "-receipt.edn"))])
            runtime-text (.readFileSync fs (artifact "runtime.edn") "utf8")
            substituted (.replace runtime-text ":os :windows" ":os :linux")
            loader-bytes (.readFileSync fs (artifact "measured-loader.exe"))]
        (lib/ensure! (not= runtime-text substituted)
                     "windows-profile: runtime profile substitution fixture missed field")
        (.writeFileSync fs (artifact "substituted-runtime.edn") substituted)
        (run-k-fails! (run-args (artifact "substituted-runtime.edn")
                                (artifact "measured-loader.exe") "substituted")
                      ":error :runtime-identity")
        (aset loader-bytes (dec (.-length loader-bytes))
              (bit-xor 1 (aget loader-bytes (dec (.-length loader-bytes)))))
        (.writeFileSync fs (artifact "mutated-loader.exe") loader-bytes)
        (run-k-fails! (run-args (artifact "runtime.edn")
                                (artifact "mutated-loader.exe") "mutated")
                      ":error :runtime-identity"))
      (println "windows-profile: measured trust-runtime and signed product run passed")))
  (finally (.rmSync fs tmp #js {:recursive true :force true})))
