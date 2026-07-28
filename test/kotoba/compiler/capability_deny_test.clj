(ns kotoba.compiler.capability-deny-test
  "T3.2: capability deny names missing grants."
  (:require [clojure.test :refer [deftest is]]
            [kotoba.compiler.core :as compiler]))

(deftest missing-grant-names-effect
  (try
    (compiler/check-source
     "(ns t (:export [main])) (defn main [] (cap-call 7 0))"
     {:allow #{}})
    (is false "expected deny")
    (catch clojure.lang.ExceptionInfo e
      (is (= :kotoba.error/capability-missing-grant
             (:kotoba.error/code (ex-data e))))
      (is (re-find #"missing grants" (ex-message e)))
      (is (re-find #":cap/call 7" (ex-message e)))
      (is (= #{[:cap/call 7]} (:missing (ex-data e)))))))
