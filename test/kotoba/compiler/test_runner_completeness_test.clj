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

(defn- listed-in-runner []
  (into #{} (map symbol)
        (re-seq #"kotoba\.compiler\.[a-z0-9.-]+-test"
                (slurp "test/kotoba/compiler/test_runner.clj"))))

(deftest every-test-namespace-is-in-the-runner
  (let [on-disk (disj (test-namespaces-on-disk)
                      'kotoba.compiler.test-runner-completeness-test)
        listed (listed-in-runner)
        missing (sort (remove listed on-disk))]
    (is (empty? missing)
        (str "test namespaces not run by kotoba.compiler.test-runner: "
             (pr-str missing)
             " — add each to BOTH the :require vector and the run-tests call"))))
