(ns kotoba.compiler.kir-trap-source-test
  "T3.3 via pinned kotoba-kir: fuel traps cite function names."
  (:require [clojure.test :refer [deftest is]]
            [kotoba.kir :as ir]))

(defn- deep-spin-kir []
  {:format :kotoba.kir/v4
   :exports ['main]
   :entry 'main
   :effects #{}
   :functions
   [{:name 'main :params [] :body (list 'spin 0)}
    {:name 'spin :params ['n] :body (list 'spin (list '+ 'n 1))}]})

(deftest fuel-exhausted-cites-function-from-pinned-kir
  (try
    (ir/execute (deep-spin-kir) 'main [])
    (is false "expected fuel exhausted")
    (catch clojure.lang.ExceptionInfo e
      (let [d (ex-data e)]
        (is (= :fuel-exhausted (:trap d)))
        (is (= :ir (:phase d)))
        (is (= 'spin (:function d)))
        (is (vector? (:call-stack d)))
        (is (some #{'spin} (:call-stack d)))
        (is (string? (:hint d)))))))
