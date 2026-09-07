(ns kotoba.compiler.test-runner-completeness-test
  "Every test namespace on disk must be in the aggregate runner.

  `clojure -M:test` runs `kotoba.compiler.test-runner`, which lists its
  namespaces by hand -- twice, in the `:require` vector and again in the
  `run-tests` call. A file missing from either list is simply never executed,
  and nothing says so: the suite reports a smaller number and passes.

  Measured 2026-07-30: twelve namespaces were absent, four of them RED
  (#447). The four green ones were the harder case -- tests sitting outside the
  gate produce no symptom at all, unlike tests failing inside it.

  kotoba-lang/kotoba had the same gap and the same fix. An auto-discovering
  runner such as cognitect.test-runner cannot develop it; a hand-maintained one
  needs this check."
  (:require [clojure.java.io :as io]
            [clojure.string :as str]
            [clojure.test :refer [deftest is]]))

(defn- ns-symbol [^java.io.File f]
  (-> (str f)
      (str/replace #"^test/" "")
      (str/replace #"\.cljc?$" "")
      (str/replace "/" ".")
      (str/replace "_" "-")
      symbol))

(defn- test-namespaces-on-disk []
  (->> (file-seq (io/file "test"))
       (filter #(re-find #"_test\.cljc?$" (.getName ^java.io.File %)))
       (map ns-symbol)
       set))

(defn- region
  "The text of one named list in the runner, or nothing.

  Reading the whole file was the defect this check had: a namespace named
  anywhere in it -- in the `:require` vector alone, say -- satisfied a scan of
  the file, while the runner only executes what the `suite` vector holds. A
  namespace in one list and not the other is never run, and this check said
  nothing about it. Measured 2026-09-06: three namespaces were in that state,
  one of them `dom-app-driver-test`, the end-to-end test for the application
  driver."
  [source start-marker]
  (when-let [start (str/index-of source start-marker)]
    (when-let [end (str/index-of source "])" start)]
      (subs source start end))))

(defn- names-in [source start-marker]
  (some->> (region source start-marker)
           (re-seq #"kotoba\.compiler\.[a-z0-9.-]+-test")
           (into #{} (map symbol))))

(deftest every-test-namespace-is-in-the-runner
  (let [source (slurp "test/kotoba/compiler/test_runner.clj")
        required (names-in source "(:require")
        suite (names-in source "(def ^:private suite")]
    ;; A check that could not read its inputs must not report a pass. Both
    ;; lists are located by shape, so a rename that moves them turns this red
    ;; rather than turning it into a scan of nothing.
    (is (some? required) "test-runner has no readable :require vector")
    (is (some? suite) "test-runner has no readable suite vector")
    (when (and required suite)
      (let [on-disk (disj (test-namespaces-on-disk)
                          'kotoba.compiler.test-runner-completeness-test)
            missing-from-suite (sort (remove suite on-disk))
            missing-from-require (sort (remove required on-disk))]
        ;; The suite is what actually runs, so it is named first and separately:
        ;; a namespace missing from it produces no symptom at all.
        (is (empty? missing-from-suite)
            (str "test namespaces never executed -- absent from the `suite` vector: "
                 (pr-str missing-from-suite)))
        (is (empty? missing-from-require)
            (str "test namespaces absent from the runner's :require vector: "
                 (pr-str missing-from-require)))))))
