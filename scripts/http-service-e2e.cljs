#!/usr/bin/env nbb
;; End-to-end runner for runtime/http-service.mjs. Mirrors the shape of
;; scripts/browser-matrix.cljs: compile the .kotoba inputs fresh with the JVM
;; compiler, run the JVM-free Node host + real HTTP requests against them,
;; and fail loudly rather than silently if the shipped decision core has
;; drifted from its source.
;;
;; The compile step needs a JDK (js/js-browser targets route through
;; `clojure -M:run`, per browser-matrix's own note) -- that is a BUILD-time
;; dependency of this repo's tooling, not a runtime dependency of the
;; artifact this test proves works. The Node process this script spawns to
;; actually serve HTTP and answer requests never touches java(1).
(ns http-service-e2e
  (:require ["node:child_process" :as child]
            ["node:fs" :as fs]
            ["node:os" :as os]
            ["node:path" :as path]))

(def root (.resolve path (.dirname path *file*) ".."))
(def tmp (.mkdtempSync fs (.join path (.tmpdir os) "kotoba-http-service-e2e-")))
(def kotoba (.join path root "bin" "kotoba"))
(def nbb-cli (.join path root "node_modules" "nbb" "cli.js"))

(defn run! [command args env]
  (let [result (.spawnSync child command (clj->js args)
                           #js {:cwd root :stdio "inherit"
                                :env (js/Object.assign #js {} js/process.env (clj->js env))})]
    (when (.-error result) (throw (.-error result)))
    (when-not (zero? (or (.-status result) 70))
      (throw (js/Error. (str "http-service-e2e command failed: " command " " (pr-str args)))))))

(defn nbb! [args env] (run! js/process.execPath (into [nbb-cli] args) env))

(defn compile-js!
  "Compile a .kotoba source to the :js-kotoba-v1 restricted-ESM target."
  [source output & more]
  (nbb! (into [kotoba "-M" "compile" (.join path root source)
               "--target" "js" "--output" (.join path tmp output)] more) {}))

(defn source-digest [mjs-path]
  (let [text (.readFileSync fs mjs-path "utf8")
        m (re-find #"sourceDigest:\"([0-9a-f]+)\"" text)]
    (when-not m (throw (js/Error. (str "could not read sourceDigest from " mjs-path))))
    (second m)))

(try
  ;; -- drift gate: the shipped decision core must equal a fresh recompile.
  (println "http-service-e2e: recompiling runtime/http/route-decide.kotoba to check for drift")
  (compile-js! "runtime/http/route-decide.kotoba" "route-decide-fresh.mjs")
  (let [shipped (source-digest (.join path root "runtime/http/route-decide.mjs"))
        fresh (source-digest (.join path tmp "route-decide-fresh.mjs"))]
    (when-not (= shipped fresh)
      (throw (js/Error. (str "runtime/http/route-decide.mjs has DRIFTED from its source.\n"
                             "  shipped sourceDigest: " shipped "\n"
                             "  fresh   sourceDigest: " fresh "\n"
                             "Regenerate with: node node_modules/nbb/cli.js bin/kotoba -M compile "
                             "runtime/http/route-decide.kotoba --target js --output runtime/http/route-decide.mjs")))))
  (println "http-service-e2e: decision core matches its source (no drift)")

  ;; -- fixtures the E2E test needs, compiled fresh every run.
  (compile-js! "examples/http-service-demo.kotoba" "http-service-demo.mjs")
  (compile-js! "test/http/fixtures/decide-double.kotoba" "decide-double.mjs")
  (compile-js! "examples/capability.kotoba" "cap-probe.mjs"
               "--policy" (.join path root "examples/capability-policy.edn"))

  (run! js/process.execPath [(.join path root "test/http/http_service_test.mjs")]
        {:KOTOBA_HTTP_TEST_DEMO (.join path tmp "http-service-demo.mjs")
         :KOTOBA_HTTP_TEST_DECIDE_DOUBLE (.join path tmp "decide-double.mjs")
         :KOTOBA_HTTP_TEST_CAP (.join path tmp "cap-probe.mjs")})

  (println "http-service-e2e: PASS")
  (finally (.rmSync fs tmp #js {:recursive true :force true})))
