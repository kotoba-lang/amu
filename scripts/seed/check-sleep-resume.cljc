;; SIGSTOP/SIGCONT across native clock_nanosleep; explicit native probe only.
;; Ported from check-sleep-resume.py (Basilisp). Linux only.
;; Run: basilisp run scripts/seed/check-sleep-resume.cljc -- (--probe P [--control C] | --compiler COMPILER) --output FILE
(ns check-sleep-resume
  (:require [basilisp.string :as str]
            [gate-util :as u])
  (:import json operator os pathlib platform signal subprocess sys time))

(defn- pin [path] (u/pin path))

(defn- build [compiler output]
  (let [root u/root
        target (get {"aarch64" "aarch64-linux" "arm64" "aarch64-linux" "x86_64" "x86_64-linux" "AMD64" "x86_64-linux"} (platform/machine))
        art (.joinpath (.-parent (.resolve output)) "artifacts")
        _ (.mkdir art ** :parents true :exist_ok false)
        manifest "seed/X86_64-LINUX-SELFHOST-MANIFEST"
        paths (u/manifest-paths (.joinpath root manifest))
        text (apply str (for [v paths] (str (.read_text (.joinpath root v)) "\n")))
        ;; Keep clock_nanosleep allowed; remove only restart_syscall in both runtimes.
        ;; The control must start sleeping before STOP/CONT exposes the missing rule.
        text (reduce (fn [text [clock restart]]
                       (let [old (str "(kxrt-allow-nr p (kxrt-allow-nr p i7 " clock ") " restart ")")]
                         (u/chk (= 1 (.count text old)) ["restart control anchor" clock restart (.count text old)])
                         (.replace text old (str "(kxrt-allow-nr p i7 " clock ")"))))
                     text [[115 128] [230 219]])
        control-source (.joinpath art "no-restart-compiler.kotoba")
        _ (.write_text control-source text)
        source (.joinpath art "probe.kotoba")
        _ (.write_bytes source (.read_bytes (.joinpath root "seed/tests/clock-sleep-resume/probe.kotoba")))
        calls (python/list)
        compile- (fn [compiler src dst]
                   (let [result (u/run-process [(.resolve compiler) "compile" src "--target" target "--output" dst "--format" "static"]
                                               (python/dict {"PATH" "/nonexistent" "KEXE_CAP_RESOURCES_35" (str art) "KEXE_STACK_BYTES" "8388608"}) 1800)]
                     (.write_bytes (.joinpath art (str (.-name dst) ".stdout")) (.-stdout result))
                     (.write_bytes (.joinpath art (str (.-name dst) ".stderr")) (.-stderr result))
                     (u/chk (and (zero? (.-returncode result)) (not (u/nonempty? (.-stderr result)))) [dst (.-returncode result) (u/bslice (.-stderr result) -600 nil)])
                     (.chmod dst 0755)
                     (.append calls (u/pydict "source" (pin src) "image" (pin dst) "exit" 0))))
        control-compiler (.joinpath art "no-restart-compiler.elf")
        probe (.joinpath art "candidate.elf")
        control (.joinpath art "no-restart.elf")]
    (compile- compiler control-source control-compiler)
    (compile- compiler source probe)
    (compile- control-compiler source control)
    [probe control
     (u/pydict "compiler" (pin compiler) "target" target
               "sourceGraph" (u/pydict-from (for [v (cons manifest paths)] [v (pin (.joinpath root v))]))
               "probeSource" (pin source)
               "controlMutation" "only restart_syscall removed; clock_nanosleep retained in both runtimes" "calls" calls)]))

(defn- run [path expected]
  (let [env (let [e (python/dict os/environ)] (operator/setitem e "KEXE_ALLOW" "7,37,39") (operator/setitem e "KEXE_CAP_RESOURCES_35" "") e)
        child (subprocess/Popen (python/list [(str (.resolve path))]) ** :env env :stdout subprocess/PIPE :stderr subprocess/PIPE :text true)]
    (u/chk (= "ready\n" (.readline (.-stderr child))))
    (time/sleep 0.05)
    (os/kill (.-pid child) signal/SIGSTOP)
    (let [[_ st] (vec (os/waitpid (.-pid child) os/WUNTRACED))]
      (u/chk (os/WIFSTOPPED st)))
    (time/sleep 0.15)
    (os/kill (.-pid child) signal/SIGCONT)
    (let [[out err] (vec (.communicate child ** :timeout 8))]
      (u/chk (= expected (.-returncode child)) [out err (.-returncode child)])
      (if (zero? expected)
        (u/chk (and (= "resumed\n" out) (not (seq err))) [out err])
        (u/chk (str/includes? err "SIGSYS") [out err]))
      (u/pydict "artifactSha256" (u/sha256-hex (.read_bytes path)) "exit" (.-returncode child) "stdout" out "stderr" err "passed" true))))

(defn main [args]
  (let [probe-arg (u/opt args "--probe") compiler-arg (u/opt args "--compiler") control-arg (u/opt args "--control")
        output (pathlib/Path (or (u/opt args "--output") (sys/exit "--output is required")))]
    (when (= (nil? probe-arg) (nil? compiler-arg)) (sys/exit "exactly one of --probe/--compiler is required"))
    (u/chk (= "Linux" (platform/system)))
    (when (and compiler-arg control-arg) (sys/exit "--compiler builds its own control; --control is only for --probe"))
    (let [[probe control built] (if compiler-arg
                                  (build (pathlib/Path compiler-arg) output)
                                  [(pathlib/Path probe-arg) (when control-arg (pathlib/Path control-arg)) nil])
          r (u/pydict "schema" "amu.native.sleep-resume.gate.v1" "host" (platform/machine) "candidate" (run probe 0))]
      (when control (operator/setitem r "oldRuntimeControl" (run control 120)))
      (when built (operator/setitem r "nativeBuild" built))
      (.write_text output (u/json-dump r))
      (println (u/json-dump r)))))

(defn -main [& args] (main args))

(when (some #(or (= % "check-sleep-resume.cljc") (str/ends-with? % "/check-sleep-resume.cljc")) sys/argv)
  (apply -main *command-line-args*))
