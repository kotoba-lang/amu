;; bootstrap-tooling
;; Differential for src/kotoba/compiler/wall_cache.cljk: the nbb reading (`:default`) against the Kotoba reading
;; (linked, analyzed, lowered to KIR and executed by the reference interpreter) on keys, the affected closure,
;; record digests and golden keys. The only capability the module uses, hash/sha256 (wire 3), is node:crypto here.
;;   KROOTS=<every classpath src dir, this repo's src, kotoba-lang/lang/compat, joined with :> \
;;   nbb --stack-size=30000 --classpath <cp + this repo's src> scripts/selfhost-wall/wall-cache-conformance.cljs
(ns wall-cache-conformance
  (:require ["node:crypto" :as crypto]
            [clojure.string :as str]
            [kotoba.compiler.project :as project]
            [kotoba.compiler.project-files :as project-files]
            [kotoba.compiler.wall-cache :as wc]
            [kotoba.kir :as ir]
            [kotoba.sema :as sema]))

(def roots (vec (str/split (.-KROOTS js/process.env) #":")))
(defn sha [s] (-> (.createHash crypto "sha256") (.update s) (.digest "hex")))
(defn typed-cap-call [id _ _ request]
  (case (js/Number id) 3 (sha request) (throw (ex-info "unhandled capability" {:id id}))))

(def kir
  (let [graph (project-files/load-closed-graph (str (first roots) "/kotoba/compiler/wall_cache.cljk") roots)
        linked (project/link-source (:sources graph) (:root graph))]
    (ir/lower (sema/analyze (:source linked) {:admit-linked-synthetics? true}) {})))

(defn guest [f args]
  (try (ir/execute kir f args {:typed-cap-call typed-cap-call :fuel 4000000000 :frames 400000 :cells 1000000000 :bytes 1000000000})
       (catch :default e (str "TRAP " (ex-message e)))))

(def tab "\t")
(defn lines [& ls] (str (str/join "\n" ls) "\n"))
(def cases
  [;; a chain, a diamond, a cycle, an isolated node, a missing sha, an unknown changed path, a path with a non-ASCII byte
   (lines "H\tcp1\tv1" "N\ta.cljk\taaa\t1 2" "N\tb.cljk\tbbb\t2" "N\tc.cljk\tccc\t" "N\td.cljk\tddd\t0" "X\tc.cljk")
   (lines "H\tcp\tv" "N\tx\t1\t1" "N\ty\t2\t0" "N\tz\t3\t" "N\tw\tMISSING\t2 0" "X\tq" "X\tz")
   (lines "H\tcp\tv" "N\t/p/é日.cljk\tabc\t" "N\t/p/b.cljk\tdef\t0" "X\t/p/é日.cljk")
   (lines "H\tcp\tv" "N\ta\t1\t" "R\tk1\tOK\tdeadbeef" "S\tk2\tOK" "S\tk3\trefused: nope" "G\tfn\ta\tCASE" "G\tfn2\ta;zz\tCASE")
   (lines "N\ta\t1\t")
   ""])

(def bad (atom 0))
(doseq [c cases]
  (let [h (wc/plan c) g (guest 'plan [c])]
    (when (not= h g) (swap! bad inc) (println "DIFF on" (pr-str c) "\n host :" (pr-str h) "\n guest:" (pr-str g)))))
;; the host reading against an independent hash of the documented key material
(let [h (wc/plan (lines "H\tcp1\tv1" "N\tc.cljk\tccc\t"))]
  (when-not (= h (str "K\tc.cljk\t" (sha "kotoba.wall-key/v1\nH\tcp1\tv1\nS\tc.cljk\tccc\n") "\n"))
    (swap! bad inc) (println "KEY MATERIAL differs from the documented one:" h)))
(let [d (wc/record-digest "k" "OK") g (guest 'record-digest ["k" "OK"])]
  (when-not (and (= d g) (= d (sha "kotoba.wall-cache/v1\nk\nOK\n"))) (swap! bad inc) (println "record-digest" d g)))
(println (if (zero? @bad) "wall-cache: nbb reading == Kotoba reading on" "wall-cache: DISAGREEMENTS on") (count cases) "inputs")
(js/process.exit (if (zero? @bad) 0 1))
