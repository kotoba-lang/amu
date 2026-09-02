#!/usr/bin/env nbb
;; ADR 0300. The four claims the definition-CID-keyed emission cache makes,
;; asked of a REAL worker over its NDJSON protocol rather than of the cache
;; namespace in isolation -- the interesting failure is not "the map does not
;; remember", it is "the key does not say what the compiler thought it said".
;;
;;   a  recompile an unchanged module                -> hit, .wasm byte-identical
;;   b  rename private functions AND their call sites
;;                                                   -> emission HIT, same bytes
;;   c  change a body                                -> miss for that closure
;;   d  change the sealed profile-version constant   -> a different key, so miss
;;
;; The metric is DEFINITIONS RECOMPILED, never wall clock. This workstation
;; runs many agents at once, so a duration measures the machine's mood; a count
;; measures the cache.
;;
;; (d) is measured on the KEY, not on a hit/miss verdict. A fresh worker misses
;; for the trivial reason -- its cache is empty -- so "the second process
;; missed" is exactly the shape of check that passes without discriminating.
;; The key is therefore reported by the compiler and compared directly.
;;
;;   nbb scripts/test-definition-cid-cache.cljs

(ns scripts.test-definition-cid-cache
  (:require [clojure.string :as str]
            [scripts.lib :as lib]
            ["node:child_process" :as child]
            ["node:fs" :as fs]))

(def directory (lib/temp-dir "kotoba-defcid-cache-"))

(def sources
  {"base.kotoba"
   (str "(ns d (:export [main]))\n"
        "(defn helper [a] (+ a 2))\n"
        "(defn other [a] (* a 5))\n"
        "(defn main [] (+ (helper 3) (other 4)))\n")
   ;; (b) Every private name changed, and every call site with it. The exported
   ;; name is untouched on purpose: an exported name IS in the emitted bytes,
   ;; so renaming it must miss, and `cache-material` puts the export list in
   ;; the key for exactly that reason.
   "renamed.kotoba"
   (str "(ns d (:export [main]))\n"
        "(defn assistant [a] (+ a 2))\n"
        "(defn another [a] (* a 5))\n"
        "(defn main [] (+ (assistant 3) (another 4)))\n")
   ;; (c) One body, one constant.
   "body.kotoba"
   (str "(ns d (:export [main]))\n"
        "(defn helper [a] (+ a 3))\n"
        "(defn other [a] (* a 5))\n"
        "(defn main [] (+ (helper 3) (other 4)))\n")})

(doseq [[nm text] sources]
  (lib/write-text! (lib/join directory nm) text))

(def failures (atom []))
(defn check! [ok? message]
  (println (if ok? "PASS" "FAIL") message)
  (when-not ok? (swap! failures conj message)))

;; ---------------------------------------------------------------------------
;; One worker, every request piped in at once.
;;
;; The worker reads bounded NDJSON lines sequentially and answers each on
;; stdout, so a whole scenario fits in one `spawnSync` with `input`. Sequential
;; is the point: request 2 must see the cache request 1 filled.

(defn run-worker [root requests]
  (let [input (str (str/join "\n" (map #(.stringify js/JSON (clj->js %)) requests)) "\n")
        result (.spawnSync child js/process.execPath
                           (clj->js [(lib/join root "bin" "amu") "worker" "--target" "wasm32"])
                           #js {:cwd root :encoding "utf8" :input input
                                :maxBuffer (* 32 1024 1024)
                                :timeout 900000
                                :env (js/Object.assign
                                      #js {} js/process.env
                                      #js {"KOTOBA_WORKER_MAX_REQUESTS" "64"})})
        lines (->> (str/split-lines (or (.-stdout result) ""))
                   (remove str/blank?)
                   (mapv #(js->clj (.parse js/JSON %) :keywordize-keys true)))]
    (when (and (.-error result) (not (seq lines)))
      (throw (js/Error. (str "worker failed: " (.-message (.-error result))
                             "\n" (.-stderr result)))))
    (when-not (= "ready" (:type (first lines)))
      (throw (js/Error. (str "worker never became ready\n" (.-stderr result)))))
    (into {} (keep (fn [line] (when (:id line) [(:id line) line]))) lines)))

(defn- answer! [responses id]
  (let [response (get responses id)]
    (when-not response (throw (js/Error. (str "no worker answer for " id))))
    (when-not (zero? (:status response))
      (throw (js/Error. (str id " failed: " (:stderr response)))))
    (:stdout response)))

(defn- verdict [text prefix]
  (cond (str/includes? text (str prefix " :hit")) :hit
        (str/includes? text (str prefix " :miss")) :miss
        :else :none))

(defn- recompiled [text]
  (some-> (re-find #":definitions-recompiled (\d+|:unmeasured)" text) second))

(defn- emit-key [text]
  (some-> (re-find #":emit-cache-key \"([0-9a-f]+)\"" text) second))

(defn scenario [root label]
  (let [out (fn [n] (lib/join directory (str label "-" n ".wasm")))
        req (fn [id src] {:id id :args ["compile" (lib/join directory src)
                                        "--target" "wasm32" "--output" (out id)]})
        responses (run-worker root [(req "base1" "base.kotoba")
                                    (req "base2" "base.kotoba")
                                    (req "renamed" "renamed.kotoba")
                                    (req "body" "body.kotoba")
                                    {:id "bye" :op "shutdown"}])]
    {:base1 (answer! responses "base1")
     :base2 (answer! responses "base2")
     :renamed (answer! responses "renamed")
     :body (answer! responses "body")
     :sha (into {} (map (fn [id] [id (lib/sha256 (out id))]))
                ["base1" "base2" "renamed" "body"])}))

;; ---------------------------------------------------------------------------
;; (d): a checkout whose sealed profile-version constant is different.
;;
;; Only what `bin/amu --jvm-free` reads is copied; `node_modules` is symlinked
;; because it is large, unchanged, and the same install either way.

(defn mutated-checkout! []
  (let [root (lib/join directory "checkout")
        file (lib/join root "src" "kotoba" "compiler" "definition_identity.cljc")]
    (.mkdirSync fs root #js {:recursive true})
    (doseq [entry ["src" "resources" "bin" "scripts" "deps.edn" "deps-lock.edn"
                   "package.json"]]
      (.cpSync fs (lib/join lib/root entry) (lib/join root entry)
               #js {:recursive true}))
    (.symlinkSync fs (lib/join lib/root "node_modules") (lib/join root "node_modules"))
    (let [text (lib/read-text file)
          bumped (str/replace text
                              #"(\n\(def profile-version\n[\s\S]*?\n)  6\)"
                              "$1  4321)")]
      (when (= text bumped)
        (throw (js/Error. "the profile-version constant was not found to mutate")))
      (lib/write-text! file bumped))
    root))

(defn definition-cids [root]
  (:stdout (lib/run js/process.execPath
                    [(lib/join root "bin" "amu") "definition-cids"
                     (lib/join directory "base.kotoba") "--jvm-free"]
                    {:cwd root})))

;; ---------------------------------------------------------------------------

(let [base (scenario lib/root "stock")]
  ;; (a)
  (check! (= :miss (verdict (:base1 base) ":cache"))
          "(a) the first compile of a module misses")
  (check! (= :hit (verdict (:base2 base) ":cache"))
          "(a) recompiling the unchanged module hits")
  (check! (= (get-in base [:sha "base1"]) (get-in base [:sha "base2"]))
          "(a) the hit's .wasm is byte-identical")
  (check! (= "3" (recompiled (:base1 base)))
          (str "(a) the first compile recompiled 3 definitions, got "
               (pr-str (recompiled (:base1 base)))))
  (check! (= "0" (recompiled (:base2 base)))
          (str "(a) the hit recompiled 0 definitions, got "
               (pr-str (recompiled (:base2 base)))))

  ;; (b)
  (check! (= :miss (verdict (:renamed base) ":cache"))
          "(b) a rename misses the ARTIFACT cache -- provenance seals the source")
  (check! (= :hit (verdict (:renamed base) ":wasm"))
          (str "(b) a rename HITS the definition-CID emission stage, got "
               (pr-str (verdict (:renamed base) ":wasm"))))
  (check! (= "0" (recompiled (:renamed base)))
          (str "(b) a rename recompiled 0 definitions, got "
               (pr-str (recompiled (:renamed base)))))
  (check! (= (get-in base [:sha "base1"]) (get-in base [:sha "renamed"]))
          "(b) the renamed module's .wasm is byte-identical to the original")
  (check! (= (emit-key (:base1 base)) (emit-key (:renamed base)))
          "(b) a rename produces the SAME emission key")

  ;; (c)
  (check! (= :miss (verdict (:body base) ":wasm"))
          (str "(c) a body change misses the emission stage, got "
               (pr-str (verdict (:body base) ":wasm"))))
  (check! (= "3" (recompiled (:body base)))
          (str "(c) a body change recompiled 3 definitions, got "
               (pr-str (recompiled (:body base)))))
  (check! (not= (emit-key (:base1 base)) (emit-key (:body base)))
          "(c) a body change produces a DIFFERENT emission key")
  (check! (not= (get-in base [:sha "base1"]) (get-in base [:sha "body"]))
          "(c) a body change emits different bytes")

  ;; (d)
  (let [mutated (mutated-checkout!)
        stock-cids (definition-cids lib/root)
        moved-cids (definition-cids mutated)
        after (scenario mutated "bumped")]
    (check! (str/includes? moved-cids ":profile-version 4321")
            "(d) the mutated checkout reports the bumped profile version")
    (check! (not= stock-cids moved-cids)
            "(d) bumping the sealed profile version moves every definition CID")
    (check! (not= (emit-key (:base1 base)) (emit-key (:base1 after)))
            "(d) a bumped profile version produces a DIFFERENT emission key")
    ;; The bytes must NOT move: the profile version is sealed into identity,
    ;; not into the emitter. If this ever goes red the key is under-specified
    ;; rather than over-specified, which is the safe direction but still a lie
    ;; about what the number means.
    (check! (= (get-in base [:sha "base1"]) (get-in after [:sha "base1"]))
            "(d) a bumped profile version does not change the emitted bytes"))

  (lib/remove-tree! directory)
  (println (count @failures) "failed")
  (when (seq @failures) (.exit js/process 1)))
