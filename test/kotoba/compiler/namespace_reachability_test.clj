(ns kotoba.compiler.namespace-reachability-test
  "Every namespace under src must be reachable from the test suite.

  A namespace nothing requires is either dead or untested, and both are worth
  knowing about. This is a require-graph reachability check, not a name-matching
  one: external `kotoba.sema` owns semantic analysis, while this graph verifies
  that every orchestration namespace remaining under `src` is exercised.

  Measured 2026-07-31: 32 of 34 reachable. The two that were not (named here
  without their prefix on purpose -- see below):

    ...target                  a stale copy of the extracted kir target ns, left
                               behind by the Phase B extraction (adda825).
                               Everything actually uses the extracted one; the
                               copy differed only in a comment still naming a
                               pre-extraction namespace.

    ...generated-capabilities  a self-described \"generated projection\" of
                               kotoba-lang's capability-semantics.edn with no
                               consumer and nothing checking it against the
                               catalog it projects.

  Both were landed by automated cleanup commits, which is how unreferenced files
  arrive without anyone deciding to add them.

  Two things keep this check from defeating itself. It excludes its own file
  from the test side of the graph, and it does not spell those two names in
  full. Without the first, writing the evidence down would mark both reachable
  and the check would pass while protecting nothing -- verified by restoring one
  of the deleted files and watching it stay green."
  (:require [clojure.java.io :as io]
            [clojure.string :as str]
            [clojure.test :refer [deftest is]]))

(def ^:private ns-pattern #"kotoba\.compiler\.[a-zA-Z0-9._-]+")

;; These namespaces are executable roots selected by bin/kotoba as files. They
;; intentionally are not required by a test namespace because loading one
;; consumes command-line arguments and may exit the test JVM/nbb process. Their
;; behavior is exercised through the launcher by the nbb, worker, benchmark,
;; and conformance tests; listing the roots here makes the reachability model
;; represent that real invocation edge.
(def ^:private executable-roots
  '#{kotoba.compiler.nbb.wasm-cli
     kotoba.compiler.nbb.aarch64-cli
     kotoba.compiler.nbb.x86-64-cli})

(defn- clj-files [root]
  (->> (file-seq (io/file root))
       (filter #(re-find #"\.clj[cs]?$" (.getName ^java.io.File %)))))

(defn- declared-ns [^java.io.File f]
  (some-> (re-find #"\(ns\s+([a-zA-Z0-9._-]+)" (slurp f)) second symbol))

(defn- graph [root]
  (into {} (keep (fn [f]
                   (when-let [n (declared-ns f)]
                     [n (into #{} (map symbol) (re-seq ns-pattern (slurp f)))])))
        (clj-files root)))

(deftest consumers-use-the-public-sema-boundary
  (let [implementation-ns (str "kotoba.compiler." "frontend")
        dependency-pattern (re-pattern
                            (str "\\[" (java.util.regex.Pattern/quote implementation-ns)
                                 "(?:\\s|\\])"))
        consumers (concat (clj-files "src")
                          (remove #(= "namespace_reachability_test.clj"
                                      (.getName ^java.io.File %))
                                  (clj-files "test")))
        violations (->> consumers
                        (filter #(re-find dependency-pattern (slurp %)))
                        (map #(.getPath ^java.io.File %))
                        sort
                        vec)]
    (is (empty? violations)
        (str "consumers must depend on public kotoba.sema, not its implementation: "
             (pr-str violations)))))

(deftest every-source-namespace-is-reachable-from-the-tests
  (let [src (graph "src")
        ;; This namespace names the very things it looks for, so counting its
        ;; own mentions would make every finding reachable by the act of
        ;; recording it.
        tests (dissoc (graph "test") 'kotoba.compiler.namespace-reachability-test)
        reachable (loop [seen #{} todo (concat executable-roots (mapcat val tests))]
                    (if-let [n (first todo)]
                      (if (seen n)
                        (recur seen (rest todo))
                        (recur (conj seen n) (concat (rest todo) (get src n))))
                      seen))
        unreachable (sort (remove reachable (keys src)))]
    (is (empty? unreachable)
        (str "src namespaces no test reaches, directly or transitively: "
             (pr-str unreachable)
             " — each is dead code or untested code; delete it or cover it"))))
