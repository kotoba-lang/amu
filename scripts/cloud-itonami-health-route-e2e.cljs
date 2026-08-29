#!/usr/bin/env nbb
;; End-to-end runner for serving a real cloud-itonami-app route (GET /health)
;; over runtime/http-service.mjs. Mirrors scripts/http-service-e2e.cljs's
;; shape: compile the .kotoba input fresh with the JVM compiler, run the
;; JVM-free Node host + real HTTP requests, fail loudly on drift.
;;
;; See examples/cloud-itonami-health-route.kotoba's header and
;; test/http/cloud_itonami_health_test.mjs's header for what this proves and
;; what it explicitly does NOT prove (that claim is
;; scripts/cloud-itonami-health-parity.cljs).
(ns cloud-itonami-health-route-e2e
  (:require ["node:child_process" :as child]
            ["node:fs" :as fs]
            ["node:os" :as os]
            ["node:path" :as path]))

(def root (.resolve path (.dirname path *file*) ".."))
(def tmp (.mkdtempSync fs (.join path (.tmpdir os) "kotoba-cloud-itonami-health-e2e-")))
(def kotoba (.join path root "bin" "kotoba"))
(def nbb-cli (.join path root "node_modules" "nbb" "cli.js"))

(defn run! [command args env]
  (let [result (.spawnSync child command (clj->js args)
                           #js {:cwd root :stdio "inherit"
                                :env (js/Object.assign #js {} js/process.env (clj->js env))})]
    (when (.-error result) (throw (.-error result)))
    (when-not (zero? (or (.-status result) 70))
      (throw (js/Error. (str "cloud-itonami-health-route-e2e command failed: " command " " (pr-str args)))))))

(defn nbb! [args env] (run! js/process.execPath (into [nbb-cli] args) env))

(defn compile-js!
  [source output & more]
  (nbb! (into [kotoba "-M" "compile" (.join path root source)
               "--target" "js" "--output" (.join path tmp output)] more) {}))

(try
  (compile-js! "examples/cloud-itonami-health-route.kotoba" "cloud-itonami-health-route.mjs")

  (run! js/process.execPath [(.join path root "test/http/cloud_itonami_health_test.mjs")]
        {:KOTOBA_HTTP_TEST_CLOUD_ITONAMI_HEALTH_ROUTE (.join path tmp "cloud-itonami-health-route.mjs")})

  (println "cloud-itonami-health-route-e2e: PASS")
  (finally (.rmSync fs tmp #js {:recursive true :force true})))
