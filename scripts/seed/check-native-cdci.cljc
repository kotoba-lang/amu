;; Stage pinned bytes and exercise the native Kotoba CDCI controller.
;;
;; Basilisp transports files and records process observations. The sealed native controller alone decides the
;; Amu selfhost / complete24 Kotoba verdict.
;; Ported from check-native-cdci.py (Basilisp). Linux x86_64 only for `main`; `controller-pin-metadata` is pure
;; and is also used by check-native-identities.
;; Run: basilisp run scripts/seed/check-native-cdci.cljc -- --complete DIR --output OUT [--stage preflight|full]
(ns check-native-cdci
  (:require [basilisp.string :as str]
            [gate-util :as u]
            [native-profile :as profile])
  (:import concurrent.futures json operator os pathlib platform re shutil signal subprocess sys threading time))

(def env-pin (python/dict {"PATH" "/nonexistent"}))

(defn sha [data] (u/sha256-hex data))
(defn pin-sha [path] (sha (.read_bytes path)))

(defn receipt [path header]
  (let [raw (.read_bytes path)
        [body digest end] (vec (.rsplit raw (.encode "\n") 2))]
    (u/chk (and (= (u/bytes-of) end) (.startswith raw (operator/add header (.encode "\n")))))
    (u/chk (= (.encode (sha (operator/add body (.encode "\n")))) digest))
    (u/pydict "sha256" (sha raw) "bodySHA256" (.decode digest) "bytes" (python/len raw))))

(defn process-running? [pid]
  ;; A child can disappear between existence and read; disappearance is the expected cleanup result.
  ;; Permission/malformed-state errors still fail.
  (try
    (let [state (nth (u/geti (.split (.read_text (pathlib/Path (str "/proc/" pid "/stat"))) ") " 1) 1) 0)]
      (not= "Z" state))
    (catch python/FileNotFoundError _ false)
    (catch python/ProcessLookupError _ false)))

(defn controller-pin-metadata
  "Audit literal pin bytes; this is transport preflight, not a native verdict."
  [policy]
  (let [source (.read_text (.joinpath u/root "seed/cdci/controller.kotoba"))
        fields ["coreSourceSHA256" "coreContainerSHA256" "amuSelfhostGateSHA256" "kotobaNativeGateSHA256" "kotobaGateSourceSHA256"]
        observed (python/dict)]
    (doseq [[index field] (map-indexed vector fields)]
      (let [rows (vec (re/findall (str "\\bh" index "_(\\d+)\\s+\\(kc-word\\s+\\(\\+\\s+\\(kc-g\\)\\s+(\\d+)\\)\\s+0x([0-9a-f]+)\\s+8\\)") source))]
        (u/chk (and (= 8 (count rows)) (= (vec (range 0 64 8)) (mapv #(python/int (first %)) rows))) ["controller pin layout" field])
        (u/chk (every? (fn [[offset address _]] (= (python/int address) (+ 20100000 (* index 64) (python/int offset)))) rows)
               ["controller pin destination" field])
        (let [value (.decode (.join (u/bytes-of) (python/list (for [[_ _ bits] rows] (.to_bytes (python/int bits 16) 8 "little")))) "ascii")]
          (u/chk (= value (u/geti policy field)) ["stale controller pin" field value (u/geti policy field)])
          (operator/setitem observed field value))))
    observed))

(defn main [complete out stage-name]
  (u/chk (and (= "Linux" (platform/system)) (= "x86_64" (platform/machine))))
  (let [root u/root
        proof (u/read-json (.joinpath complete "complete-x86.json"))
        _ (u/chk (= "PASS_COMPLETE_NATIVE_X86_COMPILER_BUILD" (u/geti proof "status")))
        _ (.mkdir out ** :parents true :exist_ok false)
        _ (.mkdir (.joinpath out "raw"))
        calls (python/list)
        calls-lock (threading/Lock)
        cases (vec (u/geti (u/read-json (.joinpath root "seed/static-cases.json")) "cases"))
        policy (u/read-json (.joinpath root "seed/cdci/policy.json"))
        binding (controller-pin-metadata policy)
        observer-sha (u/geti (u/pin (.joinpath root "scripts/seed/check-native-cdci.cljc")) "sha256")
        stage (fn [name]
                (let [r (.joinpath out name)]
                  (.mkdir r ** :mode 0700)
                  (doseq [role ["controller" "amu-selfhost" "kotoba-native"]]
                    (let [src (.joinpath complete (str "cdci-" role ".elf"))]
                      (u/chk (= (pin-sha src) (u/geti (u/geti (u/geti proof "cdci") role) "sha256")))
                      (shutil/copy2 src (.joinpath r (str role ".elf")))
                      (.chmod (.joinpath r (str role ".elf")) 0755)))
                  (u/chk (= (pin-sha (.joinpath r "amu-selfhost.elf")) (u/geti policy "amuSelfhostGateSHA256")))
                  (u/chk (= (pin-sha (.joinpath r "kotoba-native.elf")) (u/geti policy "kotobaNativeGateSHA256")))
                  (let [modules (u/manifest-paths (.joinpath root "seed/MANIFEST"))
                        source (.joinpath r "core.kotoba")
                        _ (.write_bytes source (.join (u/bytes-of) (python/list (for [p modules] (operator/add (.read_bytes (.joinpath root p)) (.encode "\n"))))))
                        _ (u/chk (= (pin-sha source) (u/geti policy "coreSourceSHA256")))
                        lock (.joinpath r "core.ksl")
                        _ (.write_text lock (str "KSL1\nentry " source "\nfile " (pin-sha source) " " source "\n"))
                        combined (.join (u/bytes-of) (python/list (for [p ["entry.kotoba" "runtime.kotoba" "kotoba-gate.kotoba"]] (.read_bytes (.joinpath (.joinpath root "seed/cdci") p)))))
                        _ (.write_bytes (.joinpath r "kotoba-gate-source.kotoba") combined)
                        _ (u/chk (= (sha combined) (u/geti policy "kotobaGateSourceSHA256")))
                        _ (shutil/copy2 (.joinpath complete "complete-x86.json") (.joinpath r "provenance.json"))
                        proof-cases (vec (u/geti proof "cases"))
                        _ (u/chk (= (count cases) (count proof-cases)))
                        lines (python/list ["KCGATE1" (str r) (pin-sha (.joinpath r "kotoba-native.elf")) "24"])]
                    (doseq [[i [case observed]] (map-indexed vector (map vector cases proof-cases))]
                      (u/chk (= (u/geti case "name") (u/geti observed "name")))
                      (let [src (str "case-" i ".kotoba") image (str "case-" i ".elf")]
                        (.write_text (.joinpath r src) (u/geti case "source"))
                        (shutil/copy2 (.joinpath complete (str "case-" (u/geti case "name") ".elf")) (.joinpath r image))
                        (.chmod (.joinpath r image) 0755)
                        (u/chk (= (pin-sha (.joinpath r image)) (u/geti (u/geti observed "image") "sha256")))
                        (let [reference (u/geti case "reference")]
                          (.extend lines (python/list [(pin-sha (.joinpath r src)) (pin-sha (.joinpath r image)) src image
                                                       (str (if (not= 0 (u/geti reference "exit")) 0 (u/geti case "result")))
                                                       (str (u/geti reference "exit")) (str (u/geti reference "remainingFuel"))])))))
                    (u/chk (= 172 (python/len lines)))
                    (.write_text (.joinpath r "cases.kcg") (str (.join "\n" lines) "\n"))
                    (let [manifest-lines (python/list ["KCDCI1" (str r) (pin-sha (.joinpath r "controller.elf")) (pin-sha (.joinpath r "amu-selfhost.elf"))
                                                       (pin-sha source) (pin-sha lock) (u/geti policy "coreContainerSHA256") (pin-sha (.joinpath r "kotoba-native.elf"))
                                                       "amu-selfhost.elf" "core.kotoba" "core.ksl" "rebuilt.kseed" "kotoba-native.elf"
                                                       (pin-sha (.joinpath r "provenance.json")) "provenance.json" (sha combined) "kotoba-gate-source.kotoba"
                                                       (pin-sha (.joinpath r "cases.kcg")) "cases.kcg"])
                          manifest (.joinpath r "controller.kcd")]
                      (.write_text manifest (str (.join "\n" manifest-lines) "\n"))
                      [r manifest manifest-lines]))))
        run (fn [name argv & {:keys [expected timeout diagnostic] :or {expected 0 timeout 60}}]
              (let [started (time/monotonic)
                    r (if (= name "controller-positive")
                        (profile/observe-controller argv :env env-pin :cwd out :timeout timeout :output (.joinpath out "controller-profile.json"))
                        (u/run-process argv env-pin timeout :cwd out))]
                (.write_bytes (.joinpath (.joinpath out "raw") (str name ".stdout")) (.-stdout r))
                (.write_bytes (.joinpath (.joinpath out "raw") (str name ".stderr")) (.-stderr r))
                (let [row (u/pydict "name" name "exit" (.-returncode r) "seconds" (python/round (- (time/monotonic) started) 3)
                                    "stdoutSHA256" (sha (.-stdout r)) "stderrSHA256" (sha (.-stderr r)))]
                  (with-open [_ calls-lock]
                    (.append calls row)
                    (.write_text (.joinpath out "calls.json") (u/json-dump calls)))
                  (u/chk (= expected (.-returncode r)) [name (.-returncode r) (u/bslice (.-stderr r) -300 nil)])
                  (cond diagnostic (u/chk (u/has-bytes? (.encode diagnostic) (.-stderr r)) [name (.-stderr r)])
                        (zero? expected) (u/chk (not (u/nonempty? (.-stderr r))) [name (.-stderr r)]))
                  row)))
        ;; Exercise all actual result/exit/fuel checks before the expensive rebuild.
        [groot gmanifest _] (stage "gate-positive")
        _ (run "gate-positive" [(.joinpath groot "kotoba-native.elf") (.joinpath groot "cases.kcg") (pin-sha (.joinpath groot "cases.kcg"))])
        standalone-gate-receipt (receipt (.joinpath groot "kotoba-gate.receipt") (.encode "KCGATE-R1"))
        probes [["wrong-manifest-pin" nil "CDCI:E2001"] ["extra-field" nil "CDCI:E1002"] ["nul-manifest" nil "CDCI:E1002"]
                ["missing-final-lf" nil "CDCI:E1002"] ["wrong-core-pin" [4 (apply str (repeat 64 "0"))] "CDCI:E2001"]
                ["substitute-amu-image" [3 (apply str (repeat 64 "0"))] "CDCI:E2001"]
                ["substitute-kotoba-image" [7 (apply str (repeat 64 "0"))] "CDCI:E2001"]
                ["substitute-gate-source" [15 (apply str (repeat 64 "0"))] "CDCI:E2001"]
                ["escaping-path" [9 "../core.kotoba"] "CDCI:E1002"] ["wire-control-path" [9 "core_SEP.kotoba"] "CDCI:E1002"]
                ["unknown-root-permissions" nil "CDCI:E1008"] ["symlink-source" nil "CDCI:E1003"] ["fifo-source" nil "CDCI:E1003"]
                ["non-executable-image" nil "CDCI:E2002"] ["existing-output" nil "CDCI:E1006"]]
        ;; The refusal probes are independent: each stages its own root under out/<name> and refuses before any
        ;; compiler execution. Run them concurrently so their serial wall time does not scale with the probe count.
        one-probe (fn [[name change diagnostic]]
                    (let [[r manifest lines] (stage name)]
                      (when change (operator/setitem lines (first change) (second change)))
                      (let [raw0 (.encode (str (.join "\n" lines) "\n"))
                            raw (cond-> raw0
                                  (= name "extra-field") (operator/add (.encode "extra\n"))
                                  (= name "nul-manifest") (.replace (.encode "KCDCI1") (operator/add (.encode "KCDCI") (u/bytes-of 0)))
                                  (= name "missing-final-lf") (u/bslice 0 -1))]
                        (.write_bytes manifest raw)
                        (when (= name "unknown-root-permissions") (.chmod r 0755))
                        (when (= name "symlink-source")
                          (.rename (.joinpath r "core.kotoba") (.joinpath r "real.kotoba"))
                          (.symlink_to (.joinpath r "core.kotoba") "real.kotoba"))
                        (when (= name "fifo-source")
                          (.unlink (.joinpath r "core.kotoba"))
                          (os/mkfifo (.joinpath r "core.kotoba")))
                        (when (= name "non-executable-image") (.chmod (.joinpath r "amu-selfhost.elf") 0644))
                        (when (= name "existing-output") (.write_bytes (.joinpath r "rebuilt.kseed") (.encode "preserve")))
                        (let [digest (if (= name "wrong-manifest-pin") (apply str (repeat 64 "0")) (pin-sha manifest))]
                          (run name [(.joinpath r "controller.elf") manifest digest] :expected 2 :diagnostic diagnostic)
                          (u/chk (not (.exists (.joinpath r "cdci.receipt"))))
                          (u/chk (not (.exists (.joinpath r "amu.stdout"))) [name "unexpected compiler execution"])))))]
    (with-open [pool (concurrent.futures/ThreadPoolExecutor ** :max_workers 8)]
      (doseq [_ (python/list (.map pool one-probe probes))] nil))
    (doseq [[field value] [[8 "43"] [9 "1"] [10 "999998"]]]
      (let [name (str "gate-forged-field-" field)
            [r _ _] (stage name)
            ledger (.joinpath r "cases.kcg")
            lines (python/list (.splitlines (.read_text ledger)))]
        (operator/setitem lines field value)
        (.write_text ledger (str (.join "\n" lines) "\n"))
        (run name [(.joinpath r "kotoba-native.elf") ledger (pin-sha ledger)] :expected 2 :diagnostic "CDCI:E4002")
        (u/chk (not (.exists (.joinpath r "kotoba-gate.receipt"))))))
    ;; Cancellation must kill the native compiler child without a false receipt.
    (let [[r manifest _] (stage "parent-death")]
      (with-open [stdout (.open (.joinpath out "raw/cancel.stdout") "wb")
                  stderr (.open (.joinpath out "raw/cancel.stderr") "wb")]
        (let [p (subprocess/Popen (python/list [(str (.joinpath r "controller.elf")) (str manifest) (pin-sha manifest)])
                                  ** :env env-pin :stdout stdout :stderr stderr)
              children (atom [])]
          (try
            (let [deadline (+ (time/monotonic) 60)]
              (loop []
                (when (and (< (time/monotonic) deadline) (nil? (.poll p)))
                  (reset! children (vec (.split (.read_text (pathlib/Path (str "/proc/" (.-pid p) "/task/" (.-pid p) "/children"))))))
                  (when (empty? @children)
                    (time/sleep 0.05)
                    (recur))))
              (u/chk (seq @children) "controller did not start its compiler child"))
            (finally
              (when (nil? (.poll p)) (.kill p))
              (.wait p ** :timeout 10)))
          (let [deadline (+ (time/monotonic) 10)
                running (loop []
                          (let [running (filterv process-running? @children)]
                            (if (and (seq running) (< (time/monotonic) deadline))
                              (do (time/sleep 0.05) (recur))
                              running)))]
            (u/chk (empty? running) ["compiler child survived controller death" running])
            (u/chk (not (.exists (.joinpath r "cdci.receipt"))))))))
    (if (= stage-name "preflight")
      (let [report (u/pydict "status" "PASS_NATIVE_CDCI_PREFLIGHT_ONLY" "caseCount" 24 "refusalCount" (+ (count probes) 3)
                             "parentDeathChildCleanup" true "fullControllerQualified" false "compilerRebuildCompleted" false
                             "observerSourceSHA256" observer-sha "controller" (u/geti (u/geti proof "cdci") "controller") "policy" policy)]
        (.write_text (.joinpath out "preflight.json") (u/json-dump report))
        (println (u/geti report "status"))
        (.flush sys/stdout))
      (let [[r manifest _] (stage "positive")
            _ (run "controller-positive" [(.joinpath r "controller.elf") manifest (pin-sha manifest)] :timeout 10900)
            _ (u/chk (= (pin-sha (.joinpath r "rebuilt.kseed")) (u/geti policy "coreContainerSHA256")))
            controller-receipt (receipt (.joinpath r "cdci.receipt") (.encode "KCDCI-R1"))
            gate-receipt (receipt (.joinpath r "kotoba-gate.receipt") (.encode "KCGATE-R1"))
            _ (u/chk (not (u/deq gate-receipt standalone-gate-receipt)) "staged ledgers must have distinct receipt identities")
            controller-fields (.splitlines (.read_bytes (.joinpath r "cdci.receipt")))
            gate-fields (.splitlines (.read_bytes (.joinpath r "kotoba-gate.receipt")))
            _ (u/chk (and (= (u/geti controller-fields 10) (u/geti gate-fields 1) (.encode (pin-sha (.joinpath r "cases.kcg"))))
                          (= (u/geti controller-fields 7) (u/geti gate-fields 2) (.encode (u/geti policy "kotobaNativeGateSHA256")))))
            profile-path (.joinpath out "controller-profile.json")
            profile-report (u/read-json profile-path)
            _ (u/chk (and (= "COMPLETED" (u/geti profile-report "status")) (= 0 (u/geti profile-report "exit"))))
            _ (u/chk (false? (u/geti profile-report "nativeVerdictAuthority")))
            _ (u/chk (u/geti profile-report "completePhaseObservation") "missing controller child phase observations")
            report (u/pydict "status" "PASS_NATIVE_KOTOBA_CDCI" "host" (python/list [(platform/system) (platform/machine) (platform/release)])
                             "controllerPinMetadata" binding "observerSourceSHA256" observer-sha
                             "controller" (u/geti (u/geti proof "cdci") "controller") "compiler" (u/geti (u/geti proof "generations") 0)
                             "policy" policy "controllerReceipt" controller-receipt "gateReceipt" gate-receipt
                             "gateReceiptPath" "positive/kotoba-gate.receipt" "standaloneGateReceipt" standalone-gate-receipt
                             "manifestSHA256" (pin-sha manifest) "coreOutputSHA256" (pin-sha (.joinpath r "rebuilt.kseed"))
                             "controllerProfile" (u/pydict "path" (.-name profile-path) "sha256" (pin-sha profile-path)
                                                           "elapsedSeconds" (u/geti profile-report "elapsedSeconds"))
                             "refusalCount" (+ (count probes) 3) "caseCount" 24 "parentDeathChildCleanup" true
                             "nativeVerdictAuthority" true "CLoader" false "NodeNBBJVMFallback" false)]
        (.write_text (.joinpath out "native-cdci.json") (u/json-dump report))
        (println (u/geti report "status") "24 cases" (u/geti report "refusalCount") "refusals; parent-death cleanup")
        (.flush sys/stdout)))))

(defn -main [& args]
  (let [stage (or (u/opt args "--stage") "full")]
    (when-not (contains? #{"preflight" "full"} stage) (sys/exit (str "invalid --stage: " stage)))
    (main (.resolve (pathlib/Path (or (u/opt args "--complete") (sys/exit "--complete is required"))))
          (.resolve (pathlib/Path (or (u/opt args "--output") (sys/exit "--output is required"))))
          stage)))

(when (some #(or (= % "check-native-cdci.cljc") (str/ends-with? % "/check-native-cdci.cljc")) sys/argv)
  (apply -main *command-line-args*))
