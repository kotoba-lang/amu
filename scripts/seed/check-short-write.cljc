;; Short writes for wire 35: the WRITE/APPEND forms and the KPV1 private-store frames (AWAI-52). Ported from
;; check-short-write.py (Basilisp, JUN-974); the Python docstring has the full case table.
;;
;; The seccomp fault gates refuse a whole write(2). This gate makes the kernel accept part of one: the guest runs
;; with RLIMIT_FSIZE at 14 bytes and SIGXFSZ ignored, so a 37-byte write first returns a short count and the
;; runtime's retry then gets EFBIG. Every form must refuse, and the gate pins the torn prefix it leaves. No seccomp
;; profile or container is needed: the limit is set in the child and the gate observes.
;; Run (Linux arm64): basilisp run -p scripts/seed scripts/seed/check-short-write.cljc --
;;   --compiler seed/bootstrap/aarch64-linux-static-root.elf --output OUT
(ns check-short-write
  (:require [basilisp.string :as str]
            [gate-util :as u])
  (:import json operator pathlib platform resource signal subprocess sys))

(def root u/root)
(defn rp [rel] (pathlib/Path root rel))
(def probe-src (rp "seed/tests/private-store/probe.kotoba"))
(def runner-src (rp "seed/x86_64-kx64-runner.kotoba"))
(def text (str (apply str (repeat 36 "x")) "\n"))   ; 37 bytes
(def limit 14)
(def guest (str "(ns t (:export [main]))\n"
                "(defn- fs [s :string] :string (typed-cap-call :fs/app-data :string :string s))\n"
                "(defn- say [s :string] :i64 (let [x (typed-cap-call :io/write :string :string (string-concat s \"|\"))] 0))\n"
                "(defn- arg [i :i64] :string (typed-cap-call :cli/args :string :string (string-from-i64 i)))\n"
                "(defn main [] :i64 (let [r (say (fs (arg 0)))] 7))\n"))

(defn pin [p] (let [d (.read_bytes (pathlib/Path p))] (u/pydict "bytes" (python/len d) "sha256" (u/sha256-hex d))))

(defn limited []
  (signal/signal signal/SIGXFSZ signal/SIG_IGN)
  (resource/setrlimit resource/RLIMIT_FSIZE (python/tuple [limit limit])))

(defn build [producer art]
  (let [cenv (u/pydict "PATH" "/nonexistent" "KEXE_STACK_BYTES" "8388608" "KEXE_CAP_RESOURCES_35" (str art))
        o (fn [n] (pathlib/Path art n))]
    (.write_bytes (o "probe.kotoba") (.read_bytes probe-src))
    (.write_bytes (o "runner.kotoba") (.read_bytes runner-src))
    (.write_text (o "guest.kotoba") guest)
    (doseq [[step argv] [["probe" ["compile" (o "probe.kotoba") "--target" "aarch64-linux" "--output" (o "probe.elf") "--format" "static"]]
                         ["guest" ["compile" (o "guest.kotoba") "--target" "aarch64-macos" "--output" (o "guest.kseed")]]
                         ["pack" ["compile" (o "runner.kotoba") "--target" "aarch64-linux" "--output" (o "guest.elf") "--format" "packed" "--payload" (o "guest.kseed")]]]]
      (let [r (subprocess/run (python/list (map str (cons producer argv))) ** :cwd art :env cenv :capture_output true :timeout 1800)]
        (u/chk (and (= (.-returncode r) 0) (zero? (python/len (.-stderr r)))) (str [step (.-returncode r) (.-stderr r)]))))
    (doseq [name ["probe.elf" "guest.elf"]] (.chmod (o name) 0755))
    [(o "probe.elf") (o "guest.elf")]))

(defn g-status [report] (operator/getitem report "status"))

(defn run [compiler output]
  (u/chk (and (= (platform/system) "Linux") (contains? #{"aarch64" "arm64"} (platform/machine))) "run on Linux arm64")
  (.mkdir output ** :parents true :exist_ok false)
  (let [art (pathlib/Path output "artifacts")
        _ (.mkdir art)
        producer (pathlib/Path art "compiler.elf")
        _ (.write_bytes producer (.read_bytes compiler))
        _ (.chmod producer 0755)
        [probe guest-elf] (build producer art)
        penv (u/pydict "PATH" "/usr/bin:/bin" "KEXE_ALLOW" "35,37,38,39" "KEXE_CAP_RESOURCES_35" (str output))
        genv (u/pydict "PATH" "/usr/bin:/bin" "KEXE_STRUCTURED_REPORT" "1" "KEXE_FUEL" "100000000" "KEXE_ALLOW" "35,37,38" "KEXE_CAP_RESOURCES_35" (str output))
        head (subs text 0 (- limit 5))
        orig "orig\n"
        ;; name, argv builder, env, staged content, limited [exit journal], unlimited [exit journal]
        cases [["private create" (fn [f] [probe "C" f text]) penv nil [2 (subs text 0 limit)] [0 text]]
               ["private append" (fn [f] [probe "A" f orig text]) penv orig [2 (str orig head)] [0 (str orig text)]]
               ["WRITE_SEP" (fn [f] [guest-elf (str f "WRITE_SEP" text)]) genv orig [120 (subs text 0 limit)] [0 text]]
               ["APPEND_SEP" (fn [f] [guest-elf (str f "APPEND_SEP" text)]) genv orig [120 (str orig head)] [0 (str orig text)]]]
        results (python/list [])]
    (doseq [[name argv env staged short control] cases
            [mode [want-exit want-disk]] [["limited" short] ["unlimited" control]]]
      ;; numbered, not named: a directory called WRITE_SEP-... would put a second token in the request
      (let [directory (pathlib/Path output (str "case" (python/len results)))
            _ (.mkdir directory ** :mode 0700)
            path (pathlib/Path directory "journal")]
        (when (some? staged)
          (.write_text path staged)
          (.chmod path 0600))
        (let [x (subprocess/run (python/list (map str (argv path))) ** :env env :capture_output true :text true :timeout 30
                                :preexec_fn (when (= mode "limited") limited))
              on-disk (when (.exists path) (.read_text path))
              out (.-stdout x) err (.-stderr x)]
          (u/chk (and (= (.-returncode x) want-exit) (= on-disk want-disk))
                 (str [name mode (.-returncode x) (subs out (max 0 (- (count out) 200))) (subs err (max 0 (- (count err) 200))) on-disk]))
          (cond
            (str/starts-with? name "private")
            (u/chk (and (= out (if (zero? want-exit) "1 1 \n" "0 1 \n")) (zero? (count err))) (str [name mode out err]))
            (not (zero? want-exit))
            (u/chk (and (str/includes? out ":status :trap") (= (operator/getitem (.split out "{:status" 1) 0) "")) (str [name mode (subs out 0 (min 200 (count out)))]))
            :else
            (u/chk (= (operator/getitem (.split out "{:status" 1) 0) (str text "|")) (str [name mode (subs out 0 (min 200 (count out)))])))
          (.append results (u/pydict "form" name "mode" mode "exit" (.-returncode x) "journal" on-disk)))))
    (let [report (u/pydict "status" "PASS_SHORT_WRITE" "limitBytes" limit "results" results "compiler" (pin compiler)
                           "probe" (pin probe) "guest" (pin guest-elf)
                           "host" (python/list [(platform/system) (platform/machine) (platform/release)])
                           "notCovered" (python/list ["a power cut: a write the kernel accepted is what is checked, not the device"
                                                      "a short write followed by success: RLIMIT_FSIZE makes the retry fail with EFBIG"]))]
      (.write_text (pathlib/Path output "short-write.json") (u/json-dump report))
      (println (g-status report) (str/join " " (for [r results] (str (.replace (operator/getitem r "form") " " "-") "/" (operator/getitem r "mode") "=" (operator/getitem r "exit")))))
      (.flush sys/stdout))))

(defn -main [& args]
  (run (.resolve (pathlib/Path (or (u/opt args "--compiler") (sys/exit "--compiler is required"))))
       (.resolve (pathlib/Path (or (u/opt args "--output") (sys/exit "--output is required"))))))

(when (some #(or (= % "check-short-write.cljc") (str/ends-with? % "/check-short-write.cljc")) sys/argv)
  (apply -main *command-line-args*))
