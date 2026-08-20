(ns kotoba.compiler.backend-cljs-portable-test
  "The cljs backend, exercised on BOTH runtimes.

  `backend_cljs_test.clj` says in its own docstring that it evaluates emitted
  source under plain JVM Clojure `not a real cljs/nbb runtime -- deliberately`,
  and that real nbb execution `was independently verified by hand before this
  commit`. Hand verification does not survive the person who did it: nothing
  re-runs it, and nothing fails when it stops being true.

  This is that check, committed. It does not replace the JVM suite -- that one
  evaluates the emitted program and checks its semantics, which is the harder
  and more valuable thing. This one pins the narrower claim the extension makes:
  that the backend ITSELF runs where it emits for.

  Run without a JVM:
    nbb --classpath \"src:test:$(clojure -Spath -M:test)\" run-cljs-backend.cljs"
  (:require [clojure.string :as str]
            [clojure.test :refer [deftest is]]
            [kotoba.compiler.backend.cljs :as backend]))

(def ^:private one-function-module
  {:kotoba.kir/version 1
   :functions [{:name 'add2 :params '[a b] :body '(+ a b)}]})

(deftest emits-a-requireable-namespace
  (let [out (backend/emit one-function-module)
        lines (str/split-lines out)]
    (is (string? out))
    (is (pos? (count out)))
    ;; The emitted text must open with the ns form a cljs host would require.
    (is (= "(ns kotoba.compiled.generated)" (first lines)))
    ;; `declare` is load-bearing per this backend's own docstring: plain defn
    ;; forms compile in file order with no forward hoisting, so a KIR function
    ;; calling a sibling defined later would fail to resolve without it.
    (is (str/includes? out "(declare add2)"))
    (is (str/includes? out "(defn add2"))))

(deftest emits-the-schema-and-contract-defs
  ;; Both are emitted unconditionally, so their absence would mean the walk
  ;; over the KIR module silently produced nothing.
  (let [out (backend/emit one-function-module)]
    (is (str/includes? out "kotoba$schemas"))
    (is (str/includes? out "kotoba$typed-contracts"))))

(deftest emit-scales-with-the-module
  ;; An evidence floor rather than a shape check: a backend that returned a
  ;; constant prelude and ignored `:functions` would pass every assertion
  ;; above.
  (let [one (backend/emit one-function-module)
        two (backend/emit (update one-function-module :functions conj
                                  {:name 'sub2 :params '[a b] :body '(- a b)}))]
    (is (> (count two) (count one)))
    (is (str/includes? two "(defn sub2"))
    (is (not (str/includes? one "sub2")))))
