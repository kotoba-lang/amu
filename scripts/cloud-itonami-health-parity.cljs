#!/usr/bin/env nbb
;; Admission-decision parity, not "it runs": proves the SAME compiled
;; decision core -- cloud-itonami-app's `health_core.kotoba`, the real
;; `GET /health` liveness-probe gate cloud-itonami-app's production server
;; calls in production via `cloud.itonami.app.kotoba-oracle` -- gives
;; IDENTICAL admission answers under two independent runtimes:
;;
;;   1. the JVM/KIR-interpreter oracle path cloud-itonami-app runs today
;;      (`cloud.itonami.app.health/health-route?`, calling
;;      `kotoba.kir/execute` on the shipped `resources/.../health.kir.edn`)
;;   2. this repo's `:js-kotoba-v1` restricted-ESM target
;;      (`amu compile --target js`), which `runtime/http-service.mjs` hosts
;;      JVM-free on Node
;;
;; across a battery of (method, path) inputs including negative cases
;; (wrong method, wrong path, trailing slash, case, whitespace).
;;
;; This is ADR-2608760000's "Proposed next slice", read literally: the
;; slice is the ADMISSION DECISION's parity across runtimes, not a served
;; endpoint (that is scripts/cloud-itonami-health-route-e2e.cljs, a
;; separate and less precise claim -- see its header).
;;
;; cloud-itonami-app is NOT modified by this script: its `health_core.kotoba`
;; source is read byte-for-byte from a checkout named by
;; CLOUD_ITONAMI_APP_DIR (or --app-dir), and its JVM-side answers come from
;; running the UNMODIFIED, ALREADY-SHIPPED `cloud.itonami.app.health`
;; namespace via `clojure -M` in that checkout -- the exact code path
;; cloud-itonami-app's real server calls on every request, not a copy.
(ns cloud-itonami-health-parity
  (:require ["node:child_process" :as child]
            ["node:fs" :as fs]
            ["node:os" :as os]
            ["node:path" :as path]))

(def root (.resolve path (.dirname path *file*) ".."))
(def kotoba (.join path root "bin" "kotoba"))
(def nbb-cli (.join path root "node_modules" "nbb" "cli.js"))

(defn arg [flag]
  (let [args (vec (.slice js/process.argv 2))
        i (.indexOf args flag)]
    (when (and (>= i 0) (< (inc i) (count args))) (nth args (inc i)))))

(def app-dir
  (or (arg "--app-dir") (aget js/process.env "CLOUD_ITONAMI_APP_DIR")))

(when-not app-dir
  (.error js/console
    (str "cloud-itonami-health-parity: need a cloud-itonami-app checkout.\n"
         "  pass --app-dir <path> or set CLOUD_ITONAMI_APP_DIR"))
  (.exit js/process 2))

(def app-dir-real (.resolve path app-dir))
(def health-core-source (.join path app-dir-real "src" "cloud" "itonami" "app" "health_core.kotoba"))

(when-not (.existsSync fs health-core-source)
  (.error js/console (str "cloud-itonami-health-parity: not found: " health-core-source))
  (.exit js/process 2))

;; -- the battery: positive, wrong method, wrong path, case, trailing slash,
;;    whitespace, unrelated paths, and a couple of adversarial-looking
;;    strings that must still resolve to false.
(def cases
  [["GET" "/health"]
   ["POST" "/health"]
   ["DELETE" "/health"]
   ["PUT" "/health"]
   ["HEAD" "/health"]
   ["get" "/health"]
   ["GET" "/Health"]
   ["GET" "/HEALTH"]
   ["GET" "/health/"]
   ["GET" "/health "]
   ["GET" " /health"]
   ["GET" "/healthz"]
   ["GET" "/health/storage"]
   ["GET" "/"]
   ["GET" ""]
   ["GET" "/nope"]
   ["GET" "/echo"]
   ["GET" "/health?x=1"]
   ["GET" "/health/../health"]
   ["" ""]
   ["POST" "/echo"]])

(def tmp (.mkdtempSync fs (.join path (.tmpdir os) "kotoba-cloud-itonami-health-parity-")))
(def cases-json-path (.join path tmp "cases.json"))
(.writeFileSync fs cases-json-path (js/JSON.stringify (clj->js cases)))

;; ---------------------------------------------------------------------
;; 1. compile health_core.kotoba (unmodified, verbatim) to :js-kotoba-v1
;; ---------------------------------------------------------------------
(println "cloud-itonami-health-parity: compiling health_core.kotoba to --target js")
(def compiled-path (.join path tmp "health-core-js.mjs"))
(let [result (.spawnSync child js/process.execPath
                         #js [nbb-cli kotoba "-M" "compile" health-core-source
                              "--target" "js" "--output" compiled-path]
                         #js {:cwd root :stdio "inherit"})]
  (when (.-error result) (throw (.-error result)))
  (when-not (zero? (or (.-status result) 70))
    (throw (js/Error. "compile failed"))))

;; ---------------------------------------------------------------------
;; 2. JS-side answers: import the compiled module, call health-route?
;; ---------------------------------------------------------------------
(def js-runner-path (.join path tmp "js-runner.mjs"))
(.writeFileSync fs js-runner-path
  (str "import fs from 'node:fs';\n"
       "const cases = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));\n"
       "const mod = await import(process.argv[3]);\n"
       "const inst = mod.instantiateKotoba({});\n"
       "const out = cases.map(([m, p]) => inst['health-route?'](m, p));\n"
       "process.stdout.write(JSON.stringify(out));\n"))

(def js-answers
  (let [result (.spawnSync child js/process.execPath
                           #js [js-runner-path cases-json-path compiled-path]
                           #js {:encoding "utf8"})]
    (when (.-error result) (throw (.-error result)))
    (when-not (zero? (or (.-status result) 70))
      (throw (js/Error. (str "js runner failed: " (.-stderr result)))))
    (js->clj (js/JSON.parse (.-stdout result)))))

;; ---------------------------------------------------------------------
;; 3. JVM-side answers: the REAL, UNMODIFIED production oracle path,
;;    `cloud.itonami.app.health/health-route?`, running in cloud-itonami-
;;    app's own checkout on its own classpath.
;; ---------------------------------------------------------------------
(println "cloud-itonami-health-parity: running the JVM/KIR-interpreter oracle path in cloud-itonami-app")
(def jvm-expr
  (str "(require (quote json.data-json) (quote cloud.itonami.app.health))"
       "(let [cases (json.data-json/read-str (slurp \"" cases-json-path "\"))]"
       "  (print (json.data-json/write-str"
       "           (mapv (fn [[m p]] (cloud.itonami.app.health/health-route? m p)) cases))))"))

(def jvm-answers
  (let [result (.spawnSync child "clojure" #js ["-M" "-e" jvm-expr]
                           #js {:cwd app-dir-real :encoding "utf8" :timeout 120000})]
    (when (.-error result) (throw (.-error result)))
    (when-not (zero? (or (.-status result) 70))
      (do (.error js/console (.-stderr result))
          (throw (js/Error. "jvm oracle path failed"))))
    ;; clojure -M prints warnings to stdout before the payload on this repo's
    ;; classpath (protocol-overwrite / namespace-shadow warnings) -- take the
    ;; LAST line, which is the JSON payload from `print`.
    (let [lines (-> (.-stdout result) (.trim) (.split "\n"))
          last-line (last lines)]
      (js->clj (js/JSON.parse last-line)))))

;; ---------------------------------------------------------------------
;; 4. compare, case by case, and report honestly.
;; ---------------------------------------------------------------------
(println (str "\n" (count cases) " cases:\n"))
(def mismatches (atom []))
(doseq [i (range (count cases))]
  (let [[m p] (nth cases i)
        js-a (nth js-answers i)
        jvm-a (nth jvm-answers i)
        agree? (= js-a jvm-a)]
    (println (str (if agree? "AGREE " "MISMATCH ")
                   (pr-str [m p]) " js=" js-a " jvm=" jvm-a))
    (when-not agree? (swap! mismatches conj [m p js-a jvm-a]))))

(.rmSync fs tmp #js {:recursive true :force true})

(if (empty? @mismatches)
  (do (println (str "\ncloud-itonami-health-parity: PASS -- " (count cases)
                     " cases, 0 mismatches (js target vs JVM/KIR-interpreter oracle)"))
      (.exit js/process 0))
  (do (println (str "\ncloud-itonami-health-parity: FAIL -- " (count @mismatches)
                     "/" (count cases) " mismatches:"))
      (doseq [[m p js-a jvm-a] @mismatches]
        (println (str "  " (pr-str [m p]) " js=" js-a " jvm=" jvm-a)))
      (.exit js/process 1)))
