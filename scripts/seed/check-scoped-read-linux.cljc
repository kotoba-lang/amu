;; Exercise KFR1 in an isolated Linux container using an Amu compiler. The compiler, packaged runner and guest
;; are Amu-built native artifacts; this stages and observes. It does not qualify the Darwin runtime. The
;; observer (observe-scoped-read-linux.py) runs inside the container image, not on the host. Ported from
;; check-scoped-read-linux.py (Basilisp, JUN-974).
;; Run: basilisp run -p scripts/seed scripts/seed/check-scoped-read-linux.cljc -- --compiler F --output OUT [--arch arm64|amd64]
(ns check-scoped-read-linux
  (:require [basilisp.string :as str]
            [gate-util :as u]
            [macos-native-lib :as mac])
  (:import json operator os pathlib subprocess sys))

(defn rp [rel] (pathlib/Path u/root rel))
(defn fail [m] (throw (python/ValueError m)))

(defn podman [args timeout]
  (subprocess/run (python/list (concat ["podman"] args)) ** :capture_output true :text true :timeout timeout))

(defn run [compiler-arg output-arg arch]
  (let [out (.resolve (pathlib/Path output-arg))
        _ (.mkdir out ** :parents true :exist_ok false)
        compiler (.resolve (pathlib/Path compiler-arg) ** :strict true)
        source (rp "seed/tests/scoped-read/probe.kotoba")
        arm? (= arch "arm64")
        o (fn [n] (pathlib/Path out n))
        nr (fn [& args] (mac/native-run compiler out (vec args)))]
    (.write_bytes (o "probe.kotoba") (.read_bytes source))
    (.write_bytes (o "binary.kotoba") (.read_bytes (rp "seed/tests/scoped-read/binary.kotoba")))
    (.write_bytes (o "runner.kotoba") (.read_bytes (rp "seed/x86_64-kx64-runner.kotoba")))
    (doseq [stem ["probe" "binary"]]
      (if arm?
        (do (nr "compile" (str stem ".kotoba") "--target" "aarch64-macos" "--output" (str stem ".kseed"))
            (nr "compile" "runner.kotoba" "--target" "aarch64-linux" "--output" (str stem ".elf")
                "--format" "packed" "--payload" (str stem ".kseed")))
        (nr "compile" (str stem ".kotoba") "--target" "x86_64-linux" "--output" (str stem ".elf") "--format" "static"))
      (.chmod (o (str stem ".elf")) 0755))
    (let [image (if arm? "docker.io/library/python:3.12-alpine" "localhost/jun555-linux:amd64")
          info (let [r (podman ["image" "inspect" image "--format" "{{.Id}} {{.Architecture}}"] 30)]
                 (when (not= (.-returncode r) 0) (fail (str "podman image inspect failed: " (.-stderr r))))
                 (.strip (.-stdout r)))
          _ (when-not (str/ends-with? info (str " " arch)) (fail "local architecture-matched test image required"))
          observer (rp "scripts/seed/observe-scoped-read-linux.py")
          run- (podman ["run" "--rm" "--pull" "never" "--network" "none" "--platform" (str "linux/" arch)
                        "-v" (str out ":/work:rw") "-v" (str observer ":/observer.py:ro") image "python3" "/observer.py"] 180)
          _ (when (not= (.-returncode run-) 0) (fail (str [(.-returncode run-) (.-stdout run-) (.-stderr run-)])))
          receipt (json/loads (.read_text (o "scoped-read-result.json")))]
      (when arm?
        (let [fault (o "fault")]
          (.mkdir fault)
          (.write_bytes (pathlib/Path fault "probe.elf") (.read_bytes (o "probe.elf")))
          (.chmod (pathlib/Path fault "probe.elf") 0755)
          (let [profile (o "pread-eio.json")]
            (.write_text profile
                         (json/dumps (u/pydict "defaultAction" "SCMP_ACT_ALLOW" "architectures" (python/list ["SCMP_ARCH_AARCH64"])
                                              "syscalls" (python/list [(u/pydict "names" (python/list ["pread64"]) "action" "SCMP_ACT_ERRNO" "errnoRet" 5
                                                                                 "args" (python/list [(u/pydict "index" 2 "value" 6 "op" "SCMP_CMP_EQ")]))]))))
            (let [failed (podman ["run" "--rm" "--pull" "never" "--network" "none" "--platform" "linux/arm64"
                                  "--security-opt" (str "seccomp=" profile)
                                  "-v" (str fault ":/work:rw") "-v" (str observer ":/observer.py:ro") image
                                  "python3" "/observer.py" "pread-fault"] 180)]
              (when (not= (.-returncode failed) 0)
                (fail (str ["fault" (.-returncode failed) (.-stdout failed) (.-stderr failed)])))
              (operator/setitem receipt "preadFault" (json/loads (.read_text (pathlib/Path fault "fault-result.json"))))))))
      (.update receipt (u/pydict "compilerSha256" (u/sha256-hex (.read_bytes compiler)) "image" info
                                 "sourceSha256" (u/sha256-hex (.read_bytes source))
                                 "elfSha256" (u/sha256-hex (.read_bytes (o "probe.elf")))
                                 "scope" (str "Linux " arch ", isolated synthetic data; seccomp if available; fleet integration unqualified")))
      (.write_text (o "receipt.json") (u/json-dump receipt))
      (println (str "PASS_SCOPED_READ_LINUX_" (str/upper-case arch))))))

(defn -main [& args]
  (let [arch (or (u/opt args "--arch") "arm64")]
    (when-not (#{"arm64" "amd64"} arch) (sys/exit "--arch must be arm64 or amd64"))
    (run (or (u/opt args "--compiler") (sys/exit "--compiler is required"))
         (or (u/opt args "--output") (sys/exit "--output is required"))
         arch)))

(when (some #(or (= % "check-scoped-read-linux.cljc") (str/ends-with? % "/check-scoped-read-linux.cljc")) sys/argv)
  (apply -main *command-line-args*))
