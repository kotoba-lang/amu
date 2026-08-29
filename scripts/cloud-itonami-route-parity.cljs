#!/usr/bin/env nbb
;; ONE parameterised admission-decision parity harness for cloud-itonami-app's
;; Kotoba route cores. Replaces the copy-paste growth that ADR-2608760000
;; addendum 2 flagged: "at the third route it is worth extracting the
;; now-thrice-repeated parity harness into one parameterised script rather
;; than copying it a third time."
;;
;; The claim, per route, is admission-decision parity -- not "it runs". The
;; SAME compiled decision core, read byte-for-byte from an UNMODIFIED
;; cloud-itonami-app checkout, must give IDENTICAL admission answers under
;; two independent runtimes:
;;
;;   1. the JVM/KIR-interpreter oracle path cloud-itonami-app runs today
;;      (its shipped `cloud.itonami.app.*` namespace, which calls
;;      `cloud.itonami.app.kotoba-oracle/call` -> `kotoba.kir/execute` on the
;;      shipped `.kir.edn`) -- the exact code path the real server takes on
;;      every request, run via `clojure -M` in that checkout
;;   2. this repo's `:js-kotoba-v1` restricted-ESM target
;;      (`amu compile --target js`), which `runtime/http-service.mjs` hosts
;;      JVM-free on Node
;;
;; cloud-itonami-app is NEVER modified by this script. It is read only.
;;
;; ---------------------------------------------------------------------------
;; What is SHARED here and what is deliberately NOT
;; ---------------------------------------------------------------------------
;; Shared (the mechanism): compile, run both runtimes, compare case by case,
;; the positive-admitted floor, the cross-admission coverage report, the
;; mutation hook, the exit codes.
;;
;; Not shared (the claim): each route's BATTERY stays per-route data in the
;; registry below. A battery is what a parity run actually proves; folding
;; six batteries into one generated list would quietly change what the two
;; landed proofs asserted. `:health` and `:oauth-resource` therefore carry
;; their landed case lists VERBATIM (21 and 28) so that migrating them onto
;; this harness is a refactor of the mechanism and not of the claim.
;;
;; ---------------------------------------------------------------------------
;; Floors this harness enforces (all three, on every route)
;; ---------------------------------------------------------------------------
;; 1. POSITIVE ADMITTED BY BOTH, checked separately from mismatch counting.
;;    A battery on which both runtimes answer `false` everywhere "agrees"
;;    with itself while proving nothing -- CLAUDE.md's
;;    "測れなかった検査が、測って問題が無かった検査と同じ値を返す".
;; 2. EVIDENCE FLOOR. Zero cases is not a pass; it is a refusal to answer.
;; 3. CROSS-ADMISSION COVERAGE is computed against the registry and PRINTED
;;    for every route, so a battery that has not been asked about its
;;    siblings is visibly distinguishable from one that has and passed --
;;    CLAUDE.md's "「飛ばした」と「合格した」が出力で区別できるか". Routes
;;    declaring `:cross-admission :required` FAIL on any gap.
;;
;; ---------------------------------------------------------------------------
;; Mutation verification (`--mutant-replace` / `--mutant-with`)
;; ---------------------------------------------------------------------------
;; A detector nobody has seen fail is not known to discriminate. These flags
;; copy the core source to a temp dir, apply one textual substitution, and
;; compile THAT for the JS side -- while the JVM side keeps running the
;; shipped, unmutated namespace. A mutant that wrongly flips exactly one case
;; must produce `FAIL` naming that case with exit 1.
;;
;; ADR-2608760000 addendum 3.
(ns cloud-itonami-route-parity
  (:require ["node:child_process" :as child]
            ["node:fs" :as fs]
            ["node:os" :as os]
            ["node:path" :as path]
            [clojure.string :as str]))

(def root (.resolve path (.dirname path *file*) ".."))
(def kotoba (.join path root "bin" "kotoba"))
(def nbb-cli (.join path root "node_modules" "nbb" "cli.js"))

;; ---------------------------------------------------------------------------
;; The registry. One entry per admission decision under proof.
;; ---------------------------------------------------------------------------
;; :admitted is the ONE (method, path) the core is supposed to say true to. It
;; is also what every OTHER route's battery must carry as a negative, which is
;; what makes cross-admission coverage computable rather than remembered.

(def health-cases
  ;; VERBATIM from scripts/cloud-itonami-health-parity.cljs as landed
  ;; (ADR-2608760000 addendum 1). 21 cases. Do not edit to "improve" it:
  ;; changing it changes what addendum 1 proved.
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

(def oauth-resource-cases
  ;; VERBATIM from scripts/cloud-itonami-oauth-resource-parity.cljs as landed
  ;; (ADR-2608760000 addendum 2). 28 cases.
  [["GET" "/.well-known/oauth-protected-resource/mcp"]
   ["POST" "/.well-known/oauth-protected-resource/mcp"]
   ["DELETE" "/.well-known/oauth-protected-resource/mcp"]
   ["PUT" "/.well-known/oauth-protected-resource/mcp"]
   ["HEAD" "/.well-known/oauth-protected-resource/mcp"]
   ["OPTIONS" "/.well-known/oauth-protected-resource/mcp"]
   ["get" "/.well-known/oauth-protected-resource/mcp"]
   ["Get" "/.well-known/oauth-protected-resource/mcp"]
   ["GET" "/.well-known/oauth-protected-resource/MCP"]
   ["GET" "/.WELL-KNOWN/oauth-protected-resource/mcp"]
   ["GET" "/.well-known/oauth-protected-resource/mcp/"]
   ["GET" "/.well-known/oauth-protected-resource/mcp "]
   ["GET" " /.well-known/oauth-protected-resource/mcp"]
   ["GET" "/.well-known/oauth-protected-resource/mcp?x=1"]
   ["GET" "/.well-known/oauth-protected-resource"]
   ["GET" "/.well-known/oauth-protected-resource/"]
   ["GET" "/.well-known/oauth-protected-resource/mcp/extra"]
   ["GET" "/.well-known/oauth-protected-resource/a2a"]
   ["GET" "/well-known/oauth-protected-resource/mcp"]
   ["GET" "/.well-known/oauth-protected-resource/../oauth-protected-resource/mcp"]
   ["GET" "/health"]
   ["GET" "/healthz"]
   ["GET" "/mcp"]
   ["GET" "/"]
   ["GET" ""]
   ["GET" "/nope"]
   ["" ""]
   ["" "/.well-known/oauth-protected-resource/mcp"]])

;; Every admitted path in the registry. Computed, not remembered: adding a
;; route automatically makes its path a required negative for the others.
(def all-admitted-paths
  ["/health"
   "/.well-known/oauth-protected-resource/mcp"
   "/.well-known/did.json"
   "/.well-known/did.jsonl"
   "/.well-known/did-witness.json"
   "/.well-known/itonami-domain-binding.json"])

(defn upper-tail
  "Uppercase everything after the last `/` -- a case attack on the leaf only."
  [p]
  (let [i (.lastIndexOf p "/")]
    (if (neg? i) (str/upper-case p)
        (str (subs p 0 (inc i)) (str/upper-case (subs p (inc i)))))))

(defn standard-battery
  "The uniform battery for a route admitting exactly (GET, `admitted`).

  Positive FIRST (the harness's positive floor reads case 0), then method
  variants, then mutations of the admitted path, then -- generated from the
  registry, so it cannot silently fall behind -- every OTHER admitted path in
  the workspace as a negative, then generic negatives.

  The mutations deliberately include one-character neighbours (`p` minus its
  last char, `p` plus \"l\", `p` plus \"/\"). `/.well-known/did.json` and
  `/.well-known/did.jsonl` are a strict-prefix pair that a per-route battery
  would never generate on its own; here each is the other's negative twice
  over -- once as a sibling and once as a neighbour."
  [admitted]
  (vec
   (concat
    [["GET" admitted]]
    ;; wrong method (the core's answer; see the note on POST did-witness.json
    ;; in the registry entry -- the HOST widens method policy, the core does not)
    [["POST" admitted]
     ["DELETE" admitted]
     ["PUT" admitted]
     ["HEAD" admitted]
     ["OPTIONS" admitted]
     ["PATCH" admitted]
     ["get" admitted]
     ["Get" admitted]
     ["GET " admitted]
     ["" admitted]]
    ;; mutations of the admitted path
    [["GET" (upper-tail admitted)]
     ["GET" (str/replace admitted "/.well-known/" "/.WELL-KNOWN/")]
     ["GET" (str admitted "/")]
     ["GET" (str admitted " ")]
     ["GET" (str " " admitted)]
     ["GET" (str admitted "?x=1")]
     ["GET" (str admitted "#f")]
     ["GET" (str admitted "/extra")]
     ["GET" (str admitted "l")]
     ["GET" (subs admitted 0 (dec (count admitted)))]
     ["GET" (str/replace admitted "/.well-known/" "/well-known/")]
     ["GET" (str/replace admitted "/.well-known/" "/.well-known/../.well-known/")]
     ["GET" (str "/" admitted)]]
    ;; cross-admission: every OTHER route's admitted path, from the registry
    (for [p all-admitted-paths :when (not= p admitted)] ["GET" p])
    ;; the health family's second path, which is not itself a registry entry
    [["GET" "/healthz"]]
    ;; generic negatives
    [["GET" "/"]
     ["GET" ""]
     ["GET" "/nope"]
     ["" ""]])))

(def registry
  [{:id "health"
    :label "cloud-itonami-health-parity"
    :core "health_core.kotoba"
    :export "health-route?"
    :jvm-ns "cloud.itonami.app.health"
    :jvm-fn "health-route?"
    :admitted ["GET" "/health"]
    :cases health-cases
    ;; Landed 2026-08-29 (addendum 1), before the did-web and domain-binding
    ;; cores were under proof. Its battery is frozen at what it proved; the
    ;; coverage line below reports the gap rather than hiding it. Extending
    ;; it is a deliberate act, not a side effect of this refactor.
    :cross-admission :legacy-partial}

   {:id "oauth-resource"
    :label "cloud-itonami-oauth-resource-parity"
    :core "oauth_resource_core.kotoba"
    :export "oauth-resource-route?"
    :jvm-ns "cloud.itonami.app.oauth-resource"
    :jvm-fn "oauth-resource-route?"
    :admitted ["GET" "/.well-known/oauth-protected-resource/mcp"]
    :cases oauth-resource-cases
    :cross-admission :legacy-partial}

   {:id "did-web"
    :label "cloud-itonami-did-web-parity"
    :core "did_web_core.kotoba"
    :export "did-web-route?"
    :jvm-ns "cloud.itonami.app.did-web"
    :jvm-fn "did-web-route?"
    :admitted ["GET" "/.well-known/did.json"]
    :cases (standard-battery "/.well-known/did.json")
    :cross-admission :required}

   {:id "did-log"
    :label "cloud-itonami-did-log-parity"
    :core "did_web_core.kotoba"
    :export "did-log-route?"
    :jvm-ns "cloud.itonami.app.did-web"
    :jvm-fn "did-log-route?"
    :admitted ["GET" "/.well-known/did.jsonl"]
    :cases (standard-battery "/.well-known/did.jsonl")
    :cross-admission :required}

   {:id "did-witness"
    :label "cloud-itonami-did-witness-parity"
    :core "did_web_core.kotoba"
    :export "did-witness-route?"
    :jvm-ns "cloud.itonami.app.did-web"
    :jvm-fn "did-witness-route?"
    :admitted ["GET" "/.well-known/did-witness.json"]
    :cases (standard-battery "/.well-known/did-witness.json")
    ;; NOTE, and it is not a defect: `server.clj`'s own `did-witness-route?`
    ;; wrapper admits POST and normalises it to "GET" before calling this
    ;; core. So the CORE answers false to POST (proved below, under both
    ;; runtimes) while the ENDPOINT accepts POST. The core decides "is this
    ;; that document"; the host decides method policy. Do not read case
    ;; `["POST" "/.well-known/did-witness.json"] = false` as "the endpoint
    ;; rejects POST".
    :cross-admission :required}

   {:id "domain-binding-nonce"
    :label "cloud-itonami-domain-binding-nonce-parity"
    :core "domain_binding_core.kotoba"
    :export "nonce-route?"
    :jvm-ns "cloud.itonami.app.domain-binding"
    :jvm-fn "nonce-route?"
    :admitted ["GET" "/.well-known/itonami-domain-binding.json"]
    :cases (standard-battery "/.well-known/itonami-domain-binding.json")
    :cross-admission :required}])

(defn entry-by-id [id] (first (filter #(= id (:id %)) registry)))

;; ---------------------------------------------------------------------------
;; args
;; ---------------------------------------------------------------------------
(def argv (vec (.slice js/process.argv 2)))

(defn arg [flag]
  (let [i (.indexOf argv flag)]
    (when (and (>= i 0) (< (inc i) (count argv))) (nth argv (inc i)))))

(defn flag? [f] (>= (.indexOf argv f) 0))

(when (flag? "--list")
  (doseq [e registry]
    (println (str (.padEnd (:id e) 24) (:jvm-ns e) "/" (:jvm-fn e)
                  "  <- " (pr-str (:admitted e))
                  "  (" (count (:cases e)) " cases)")))
  (.exit js/process 0))

(def app-dir (or (arg "--app-dir") (aget js/process.env "CLOUD_ITONAMI_APP_DIR")))

(when-not app-dir
  (.error js/console
    (str "cloud-itonami-route-parity: need a cloud-itonami-app checkout.\n"
         "  pass --app-dir <path> or set CLOUD_ITONAMI_APP_DIR\n"
         "  --route <id>   one of: " (str/join ", " (map :id registry)) ", all\n"
         "  --list         show the registry"))
  (.exit js/process 2))

(def app-dir-real (.resolve path app-dir))

(def selected
  (let [r (or (arg "--route") "all")]
    (if (= r "all") registry
        (if-let [e (entry-by-id r)] [e]
          (do (.error js/console
                (str "cloud-itonami-route-parity: unknown --route " (pr-str r)
                     "; known: " (str/join ", " (map :id registry)) ", all"))
              (.exit js/process 2))))))

(def mutant-from (arg "--mutant-replace"))
(def mutant-to (arg "--mutant-with"))

(when (and (or mutant-from mutant-to) (not (and mutant-from mutant-to)))
  (.error js/console "cloud-itonami-route-parity: --mutant-replace and --mutant-with must be given together")
  (.exit js/process 2))

(when (and mutant-from (> (count selected) 1))
  (.error js/console "cloud-itonami-route-parity: --mutant-* needs a single --route")
  (.exit js/process 2))

;; ---------------------------------------------------------------------------
;; one route
;; ---------------------------------------------------------------------------
(defn run-route [e]
  (let [label (:label e)
        cases (:cases e)
        core-source (.join path app-dir-real "src" "cloud" "itonami" "app" (:core e))]

    (when-not (.existsSync fs core-source)
      (.error js/console (str label ": not found: " core-source))
      (.exit js/process 2))

    ;; FLOOR 2: an empty battery is a refusal to answer, not a pass.
    (when (zero? (count cases))
      (println (str "\n" label ": REFUSING to report a pass -- 0 cases."))
      (.exit js/process 2))

    (let [tmp (.mkdtempSync fs (.join path (.tmpdir os) (str "kotoba-" (:id e) "-parity-")))
          cases-json-path (.join path tmp "cases.json")
          _ (.writeFileSync fs cases-json-path (js/JSON.stringify (clj->js cases)))

          ;; ---- the source the JS side compiles ----
          ;; Unmutated: cloud-itonami-app's file, read in place, untouched.
          ;; Mutated: a COPY in tmp with one textual substitution. The JVM
          ;; side always runs the shipped, unmutated namespace either way,
          ;; which is what makes a mutant show up as a mismatch.
          js-source
          (if mutant-from
            (let [orig (.readFileSync fs core-source "utf8")]
              (when-not (.includes orig mutant-from)
                (.error js/console
                  (str label ": --mutant-replace text not found in " (:core e)
                       " -- refusing to report a mutation result for a mutation"
                       " that was never applied."))
                (.exit js/process 2))
              (let [mutated (.replace orig mutant-from mutant-to)
                    p (.join path tmp (:core e))]
                (when (= mutated orig)
                  (.error js/console (str label ": mutation was a no-op; refusing."))
                  (.exit js/process 2))
                (.writeFileSync fs p mutated)
                (println (str label ": MUTANT ACTIVE -- js side compiles a copy with "
                              (pr-str mutant-from) " -> " (pr-str mutant-to)
                              "; jvm side runs the shipped, unmutated namespace."))
                p))
            core-source)

          ;; ---- 1. compile the core to :js-kotoba-v1 ----
          _ (println (str label ": compiling " (:core e) " to --target js"))
          compiled-path (.join path tmp (str (:id e) "-js.mjs"))
          _ (let [result (.spawnSync child js/process.execPath
                                     #js [nbb-cli kotoba "-M" "compile" js-source
                                          "--target" "js" "--output" compiled-path]
                                     #js {:cwd root :stdio "inherit"})]
              (when (.-error result) (throw (.-error result)))
              (when-not (zero? (or (.-status result) 70))
                (throw (js/Error. (str label ": compile failed")))))

          ;; ---- 2. JS-side answers ----
          js-runner-path (.join path tmp "js-runner.mjs")
          _ (.writeFileSync fs js-runner-path
              (str "import fs from 'node:fs';\n"
                   "const cases = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));\n"
                   "const mod = await import(process.argv[3]);\n"
                   "const inst = mod.instantiateKotoba({});\n"
                   "const fn = inst[process.argv[4]];\n"
                   "if (typeof fn !== 'function') {\n"
                   "  throw new Error('no such export: ' + process.argv[4] +\n"
                   "    ' (have: ' + Object.keys(inst).join(',') + ')');\n"
                   "}\n"
                   "const out = cases.map(([m, p]) => fn(m, p));\n"
                   "process.stdout.write(JSON.stringify(out));\n"))
          js-answers
          (let [result (.spawnSync child js/process.execPath
                                   #js [js-runner-path cases-json-path compiled-path (:export e)]
                                   #js {:encoding "utf8"})]
            (when (.-error result) (throw (.-error result)))
            (when-not (zero? (or (.-status result) 70))
              (throw (js/Error. (str label ": js runner failed: " (.-stderr result)))))
            (js->clj (js/JSON.parse (.-stdout result))))

          ;; ---- 3. JVM-side answers: the REAL, UNMODIFIED production oracle ----
          _ (println (str label ": running the JVM/KIR-interpreter oracle path in cloud-itonami-app"))
          jvm-expr
          (str "(require (quote clojure.data.json) (quote " (:jvm-ns e) "))"
               "(let [cases (clojure.data.json/read-str (slurp \"" cases-json-path "\"))]"
               "  (print (clojure.data.json/write-str"
               "           (mapv (fn [[m p]] (" (:jvm-ns e) "/" (:jvm-fn e) " m p)) cases))))")
          jvm-answers
          (let [result (.spawnSync child "clojure" #js ["-M" "-e" jvm-expr]
                                   #js {:cwd app-dir-real :encoding "utf8" :timeout 600000})]
            (when (.-error result) (throw (.-error result)))
            (when-not (zero? (or (.-status result) 70))
              (do (.error js/console (.-stderr result))
                  (throw (js/Error. (str label ": jvm oracle path failed")))))
            ;; `clojure -M` prints classpath warnings to stdout before the
            ;; payload on this repo's classpath -- take the LAST line, which
            ;; is the JSON from `print`.
            (let [lines (-> (.-stdout result) (.trim) (.split "\n"))]
              (js->clj (js/JSON.parse (last lines)))))

          ;; ---- 4. compare ----
          _ (println (str "\n" label ": " (count cases) " cases:\n"))
          mismatches (atom [])
          _ (doseq [i (range (count cases))]
              (let [[m p] (nth cases i)
                    js-a (nth js-answers i)
                    jvm-a (nth jvm-answers i)
                    agree? (= js-a jvm-a)]
                (println (str (if agree? "AGREE " "MISMATCH ")
                              (pr-str [m p]) " js=" js-a " jvm=" jvm-a))
                (when-not agree? (swap! mismatches conj [m p js-a jvm-a]))))

          ;; FLOOR 1: the positive case must actually be admitted by BOTH.
          positive-admitted? (and (true? (first js-answers)) (true? (first jvm-answers)))

          ;; FLOOR 3: cross-admission coverage, computed from the registry.
          battery-paths (set (map second cases))
          siblings (remove #(= % (second (:admitted e))) all-admitted-paths)
          covered (filter battery-paths siblings)
          missing (remove battery-paths siblings)]

      (.rmSync fs tmp #js {:recursive true :force true})

      (println (str "\n" label ": cross-admission coverage " (count covered) "/" (count siblings)
                    " sibling admitted paths present as negatives"
                    (when (seq missing) (str "; MISSING " (pr-str (vec missing))))))

      (cond
        (not positive-admitted?)
        (do (println (str "\n" label ": FAIL -- the positive case " (pr-str (first cases))
                          " was not admitted by both runtimes (js=" (first js-answers)
                          " jvm=" (first jvm-answers) "). A battery that refuses"
                          " everything agrees with itself and proves nothing."))
            false)

        (seq @mismatches)
        (do (println (str "\n" label ": FAIL -- " (count @mismatches) "/" (count cases)
                          " mismatches:"))
            (doseq [[m p js-a jvm-a] @mismatches]
              (println (str "  " (pr-str [m p]) " js=" js-a " jvm=" jvm-a)))
            false)

        (and (= :required (:cross-admission e)) (seq missing))
        (do (println (str "\n" label ": FAIL -- declares :cross-admission :required but "
                          (count missing) " sibling admitted path(s) are absent from the"
                          " battery: " (pr-str (vec missing))))
            false)

        :else
        (do (println (str "\n" label ": PASS -- " (count cases)
                          " cases, 0 mismatches (js target vs JVM/KIR-interpreter oracle),"
                          " positive case admitted by both"))
            true)))))

;; ---------------------------------------------------------------------------
(def results (mapv (fn [e] [(:label e) (run-route e)]) selected))
(def failed (filterv (comp not second) results))

(when (> (count results) 1)
  (println "\n=== summary ===")
  (doseq [[l ok?] results] (println (str (if ok? "PASS " "FAIL ") l))))

(if (seq failed)
  (do (println (str "\ncloud-itonami-route-parity: FAIL -- " (count failed) "/"
                    (count results) " route(s) failed"))
      (.exit js/process 1))
  (do (println (str "\ncloud-itonami-route-parity: PASS -- " (count results)
                    " route(s), 0 failures"))
      (.exit js/process 0)))
