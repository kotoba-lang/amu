#!/usr/bin/env nbb
;; End-to-end runner for the first `kotoba/app` vertical slice on
;; runtime/http-service.mjs: compile `examples/approval-queue-app.kotoba`
;; fresh with the JVM compiler, then run the JVM-free Node host and real HTTP
;; requests against it.
;;
;; The compile step needs a JDK (the js target routes through `clojure -M:run`)
;; -- that is a BUILD-time dependency of this repo's tooling, not a runtime
;; dependency of the artifact this test proves works. The Node process that
;; serves HTTP and answers requests never touches java(1).
;;
;; ## Fuel is a compile-time argument here, deliberately
;;
;; This guest scans its own request body, so what it can afford is fixed when
;; it is compiled, not by the host. `--fuel` below is the measured number;
;; `scripts/approval-queue-fuel.cljs` is what measures it and will fail if the
;; artifact is compiled below what these bounds need.
;;
;; ## The deliberate break
;;
;;   --mutant-replace <text> --mutant-with <text>
;;
;; compiles a one-substitution copy of the guest and runs the SAME test file
;; against it. A detector nobody has watched fail is not known to
;; discriminate, so the intended use is to flip a rule the test asserts and
;; watch exactly that assertion go red. If the text is not found in the
;; source, this refuses (exit 2) rather than reporting a mutation that was
;; never applied as one that was survived.
(ns approval-queue-e2e
  (:require ["node:child_process" :as child]
            ["node:fs" :as fs]
            ["node:os" :as os]
            ["node:path" :as path]))

(def root (.resolve path (.dirname path *file*) ".."))
(def tmp (.mkdtempSync fs (.join path (.tmpdir os) "kotoba-approval-e2e-")))
(def kotoba (.join path root "bin" "kotoba"))
(def nbb-cli (.join path root "node_modules" "nbb" "cli.js"))

(def argv (vec (.slice js/process.argv 2)))
(defn arg [flag fallback]
  (let [i (.indexOf argv flag)]
    (if (neg? i) fallback (nth argv (inc i) fallback))))

;; Measured by scripts/approval-queue-fuel.cljs against a 1024-byte body and
;; a 1024-byte state. See that script's output for the worst-case minimum.
(def fuel (arg "--fuel" "262144"))
(def mutant-replace (arg "--mutant-replace" nil))
(def mutant-with (arg "--mutant-with" nil))

(defn run! [command args env]
  (let [result (.spawnSync child command (clj->js args)
                           #js {:cwd root :stdio "inherit"
                                :env (js/Object.assign #js {} js/process.env (clj->js env))})]
    (when (.-error result) (throw (.-error result)))
    (.-status result)))

(defn must! [command args env]
  (let [status (run! command args env)]
    (when-not (zero? (or status 70))
      (throw (js/Error. (str "approval-queue-e2e command failed: " command " " (pr-str args)))))))

(defn compile-js! [source output]
  (must! js/process.execPath
         [nbb-cli kotoba "-M" "compile" source
          "--target" "js" "--fuel" fuel "--output" output]
         {}))

(def app-source (.join path root "examples/approval-queue-app.kotoba"))

(try
  (let [source-path
        (if mutant-replace
          (let [text (.readFileSync fs app-source "utf8")]
            (when-not mutant-with
              (println "approval-queue-e2e: --mutant-replace needs --mutant-with")
              (.rmSync fs tmp #js {:recursive true :force true})
              (js/process.exit 2))
            (when-not (.includes text mutant-replace)
              (println (str "approval-queue-e2e: REFUSING to report a mutation result -- "
                            (pr-str mutant-replace) " is not present in " app-source
                            ". A mutation that was never applied must not be reported as"
                            " a mutation that was survived."))
              (.rmSync fs tmp #js {:recursive true :force true})
              (js/process.exit 2))
            (let [copy (.join path tmp "approval-queue-app.kotoba")]
              (.writeFileSync fs copy (.replace text mutant-replace mutant-with))
              (println (str "approval-queue-e2e: MUTANT ACTIVE -- guest compiles a copy with "
                            (pr-str mutant-replace) " -> " (pr-str mutant-with) "."))
              copy))
          app-source)
        out (or (arg "--out" nil) (.join path tmp "approval-queue-app.mjs"))]

    (println (str "approval-queue-e2e: compiling the guest (--fuel " fuel ")"))
    (compile-js! source-path out)

    (let [status (run! js/process.execPath
                       [(.join path root "test/http/approval_queue_test.mjs")]
                       {:KOTOBA_HTTP_TEST_APPROVAL_APP out})]
      (if mutant-replace
        ;; Under a mutant the expected outcome is INVERTED: a green run means
        ;; the battery did not discriminate, which is the failure.
        (if (zero? (or status 70))
          (do (println "\napproval-queue-e2e: FAIL -- the mutant SURVIVED. The test passed"
                       " against a guest whose rule was flipped, so it does not discriminate.")
              (js/process.exit 1))
          (do (println (str "\napproval-queue-e2e: the mutant was CAUGHT (test exited "
                            status "). The detector discriminates."))
              (js/process.exit 0)))
        (if (zero? (or status 70))
          (println "\napproval-queue-e2e: PASS")
          (do (println "\napproval-queue-e2e: FAIL") (js/process.exit 1))))))
  (finally (.rmSync fs tmp #js {:recursive true :force true})))
