;; Linux native private-store diagnostics. Basilisp orchestrates and hashes only.
;; Explicit selfhost compiler required; no hosted compiler/crypto/key fixture.
;; Ported from check-private-store.py (Basilisp). Linux only.
;; Run: basilisp run scripts/seed/check-private-store.cljc -- (--compiler C | --probe P) --output OUT
(ns check-private-store
  (:require [basilisp.string :as str]
            [gate-util :as u])
  (:import concurrent.futures json operator os pathlib platform shutil subprocess sys))

(defn- run-text
  "subprocess.run(argv, env, capture_output, text, timeout)"
  [argv env timeout]
  (subprocess/run (python/list (map str argv)) ** :env env :capture_output true :text true :timeout timeout))

(defn main [args]
  (let [compiler-arg (u/opt args "--compiler") probe-arg (u/opt args "--probe")
        _ (when (= (nil? compiler-arg) (nil? probe-arg)) (sys/exit "exactly one of --compiler/--probe is required"))
        compiler (when compiler-arg (pathlib/Path compiler-arg)) probe-in (when probe-arg (pathlib/Path probe-arg))
        _ (u/chk (and (= "Linux" (platform/system)) (contains? #{"aarch64" "x86_64"} (platform/machine))))
        repo u/root
        out (.resolve (pathlib/Path (or (u/opt args "--output") (sys/exit "--output is required"))))
        _ (.mkdir out ** :parents true :exist_ok false)
        private (.joinpath out "private")
        _ (.mkdir private ** :mode 0700)
        probe (.joinpath out "probe.elf")
        env (let [e (python/dict os/environ)] (operator/setitem e "KEXE_ALLOW" "35,37,38,39") (operator/setitem e "KEXE_CAP_RESOURCES_35" (str out)) e)
        source (.joinpath repo "seed/tests/private-store/probe.kotoba")
        compile-env (let [e (python/dict env)] (operator/setitem e "KEXE_CAP_RESOURCES_35" (str out ":" repo)) e)
        build (when compiler
                (subprocess/run (python/list [(str (.resolve compiler)) "compile" (str source) "--target"
                                              (if (= "aarch64" (platform/machine)) "aarch64-linux" "x86_64-linux")
                                              "--output" (str probe) "--format" "static"])
                                ** :env compile-env :capture_output true :text true))]
    (if build
      (u/chk (and (zero? (.-returncode build)) (not (seq (.-stderr build)))) build)
      (shutil/copyfile probe-in probe))
    (.chmod probe 0755)
    (let [cases (python/list)
          run (fn [op path & args] (run-text (concat [probe op path] args) env 20))
          check (fn [name op path & {:keys [args status stdout] :or {args [] status 0}}]
                  (let [r (apply run op path args)]
                    (u/chk (and (= status (.-returncode r)) (not (seq (.-stderr r))) (or (nil? stdout) (= stdout (.-stdout r)))) [name r])
                    (.append cases (u/pydict "case" name "exit" (.-returncode r) "passed" true))))
          f (.joinpath private "journal")]
      (check "exclusive create" "C" f :args ["first\n"] :stdout "1 1 \n")
      (check "read same owner 0600 in 0700 directory" "R" f :stdout "1 7 first\n\n")
      (u/chk (= 0600 (bit-and (.-st_mode (.stat f)) 07777)))
      (check "existing file never truncated" "C" f :args ["wrong"] :status 2)
      (u/chk (= "first\n" (.read_text f)))
      (check "compare append and fsync" "A" f :args ["first\n" "second\n"])
      (check "stale comparison refused" "A" f :args ["first\n" "replay\n"] :status 2)
      (u/chk (= "first\nsecond\n" (.read_text f)))
      (check "unsupported operation refused" "X" f :status 2)
      (.chmod f 0644)
      (check "public file refused" "R" f :status 2)
      (check "public file not appended" "A" f :args ["first\nsecond\n" "bad\n"] :status 2)
      (.chmod f 0600)
      (let [link (.joinpath private "hardlink")]
        (os/link f link)
        (check "hardlink read refused" "R" f :status 2)
        (check "hardlink append refused" "A" f :args ["first\nsecond\n" "bad\n"] :status 2)
        (.unlink link)
        (.symlink_to link f)
        (check "final symlink refused" "R" link :status 2)
        (check "final symlink create refused" "C" link :args ["bad"] :status 2))
      (let [parent-link (.joinpath out "parent-link")]
        (.symlink_to parent-link private ** :target_is_directory true)
        (check "parent symlink refused" "R" (.joinpath parent-link "journal") :status 2))
      (.chmod private 0755)
      (check "public parent refused" "R" f :status 2)
      (check "public parent create refused" "C" (.joinpath private "no-create") :args ["bad"] :status 2)
      (.chmod private 0700)
      (check "outside scope refused" "R" (.joinpath (.-parent out) "not-in-scope") :status 2)
      (let [content "WRITE_SEP RENAME_SEP FSYNC_SEP\n"]
        (check "private payload cannot invoke text tokens" "C" (.joinpath private "tokens") :args [content])
        (u/chk (= content (.read_text (.joinpath private "tokens")))))
      (let [old (.read_text f)]
        (with-open [pool (concurrent.futures/ThreadPoolExecutor ** :max_workers 8)]
          (let [raced (python/list (.map pool (fn [i] (run "A" f old (str "writer-" i "\n"))) (range 8)))]
            (u/chk (and (= 1 (count (filter #(zero? (.-returncode %)) raced))) (every? #(contains? #{0 2} (.-returncode %)) raced)) raced)))
        (u/chk (= 3 (count (.splitlines (.read_text f)))))
        (.append cases (u/pydict "case" "eight concurrent CAS writers: one success" "passed" true)))
      (let [refused (run-text [probe "R" f] (let [e (python/dict env)] (operator/setitem e "KEXE_ALLOW" "37,38,39") e) 20)]
        (u/chk (= 120 (.-returncode refused)) refused)
        (.append cases (u/pydict "case" "missing wire grant traps" "exit" 120 "passed" true)))
      (let [receipt (u/pydict "schema" "amu.native.private-store.gate.v1" "host" (platform/machine)
                              "compilerSha256" (when compiler (u/sha256-hex (.read_bytes compiler)))
                              "crossCompiledProbe" (boolean probe-arg) "probeSha256" (u/sha256-hex (.read_bytes probe))
                              "cases" cases "count" (python/len cases) "passed" true "cdciQualified" false
                              "note" "Process/fsync/atomic-comparison diagnostics, not a power-loss experiment or independent custody qualification")]
        (.write_text (.joinpath out "receipt.json") (u/json-dump receipt))
        (println (json/dumps receipt ** :indent 2))))))

(defn -main [& args] (main args))

(when (some #(or (= % "check-private-store.cljc") (str/ends-with? % "/check-private-store.cljc")) sys/argv)
  (apply -main *command-line-args*))
