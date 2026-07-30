(ns kotoba.compiler.linear-resource-test
  (:require [clojure.test :refer [deftest is]]
            [kotoba.compiler.core :as compiler]))

(def direct-stream-source
  "(ns app (:export [open]))
   (defn open [url :string] [:task [:stream :bytes]]
     (typed-cap-call :http/get-stream :string [:task [:stream :bytes]] url))")

(deftest direct-task-stream-capability-result-is-typed
  (let [checked (compiler/check-source
                 direct-stream-source {:allow #{[:cap/call 13]}})
        function (first (get-in checked [:hir :functions]))]
    (is (= [:task [:stream :bytes]] (:result function)))
    (is (= '(typed-cap-call 13 :string [:task [:stream :bytes]] url)
           (:body function)))))

(deftest task-stream-capability-compiles-to-a-validated-component
  (let [source
        "(ns app (:export [open]))
         (defn open [request :i64] [:task [:stream :bytes]]
           (typed-cap-call :http/get-stream :i64
             [:task [:stream :bytes]] request))"
        compiled (compiler/compile-component
                  source {:allow #{[:cap/call 13]}}
                  {:profile :async
                   :budgets {:deadline-ms 1000
                             :max-items 32
                             :max-bytes 65536
                             :cancellation true}})]
    (is (= :wasm-component/v1 (:format compiled)))
    (is (= :task-stream-capability-call (:canonical-lowering compiled)))
    (is (= [:http/get-stream] (:imports compiled)))
    (is (= :async (get-in compiled [:admission-request :profile])))
    (is (pos? (alength ^bytes (:bytes compiled))))))

(deftest linear-resources-cannot-be-copied-through-ordinary-parameters
  (is (try
        (compiler/check-source
         "(ns app (:export [copy]))
          (defn copy [task [:task [:stream :bytes]]]
            [:task [:stream :bytes]] task)"
         {})
        false
        (catch clojure.lang.ExceptionInfo error
          (boolean (re-find #"move-aware" (.getMessage error)))))))

(deftest linear-result-must-be-one-direct-capability-move
  (is (try
        (compiler/check-source
         "(ns app (:export [bad]))
          (defn bad [url :string] [:task [:stream :bytes]]
            (let [task (typed-cap-call :http/get-stream :string
                         [:task [:stream :bytes]] url)]
              task))"
         {:allow #{[:cap/call 13]}})
        false
        (catch clojure.lang.ExceptionInfo error
          (boolean (re-find #"one direct typed capability move"
                            (.getMessage error)))))))
