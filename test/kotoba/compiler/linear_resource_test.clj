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

(deftest task-stream-capability-direct-i64-request-is-typed
  "Direct linear move with an i64 request is admitted at the HIR layer."
  (let [source
        "(ns app (:export [open]))
         (defn open [request :i64] [:task [:stream :bytes]]
           (typed-cap-call :http/get-stream :i64
             [:task [:stream :bytes]] request))"
        checked (compiler/check-source source {:allow #{[:cap/call 13]}})]
    (is (= [:task [:stream :bytes]]
           (get-in checked [:hir :functions 0 :result])))
    (is (= #{[:cap/call 13]}
           (get-in checked [:hir :functions 0 :effects])))))

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

(deftest linear-let-move-is-admitted
  "ADR 0137: single affine let that returns the bound task is a valid move."
  (let [checked
        (compiler/check-source
         "(ns app (:export [open]))
          (defn open [url :string] [:task [:stream :bytes]]
            (let [task (typed-cap-call :http/get-stream :string
                         [:task [:stream :bytes]] url)]
              task))"
         {:allow #{[:cap/call 13]}})
        function (first (get-in checked [:hir :functions]))
        body (:body function)]
    (is (= [:task [:stream :bytes]] (:result function)))
    (is (= 'let (first body)))
    (is (= 'task (first (second body))))
    (is (= '(typed-cap-call 13 :string [:task [:stream :bytes]] url)
           (second (second body))))
    (is (= 'task (nth body 2)))))

(deftest linear-let-consume-byte-count-is-admitted
  "ADR 0137: let-bound task consumed exactly once via bytes-task-byte-count."
  (let [checked
        (compiler/check-source
         "(ns app (:export [size]))
          (defn size [url :string] :i64
            (let [task (typed-cap-call :http/get-stream :string
                         [:task [:stream :bytes]] url)]
              (bytes-task-byte-count task)))"
         {:allow #{[:cap/call 13]}})
        function (first (get-in checked [:hir :functions]))
        body (:body function)]
    (is (= :i64 (:result function)))
    (is (= 'let (first body)))
    (is (= 'bytes-task-byte-count (first (nth body 2))))
    (is (= 'task (second (nth body 2))))))

(deftest linear-let-consume-task-ready-is-admitted
  (let [checked
        (compiler/check-source
         "(ns app (:export [ready]))
          (defn ready [url :string] :i64
            (let [task (typed-cap-call :http/get-stream :string
                         [:task [:stream :bytes]] url)]
              (task-ready? task)))"
         {:allow #{[:cap/call 13]}})
        function (first (get-in checked [:hir :functions]))]
    (is (= :i64 (:result function)))
    (is (= 'let (first (:body function))))))

(deftest linear-let-double-use-is-rejected
  "Two uses of the same affine binding is not a single move."
  (is (try
        (compiler/check-source
         "(ns app (:export [bad]))
          (defn bad [url :string] :i64
            (let [task (typed-cap-call :http/get-stream :string
                         [:task [:stream :bytes]] url)]
              (+ (bytes-task-byte-count task)
                 (bytes-task-byte-count task))))"
         {:allow #{[:cap/call 13]}})
        false
        (catch clojure.lang.ExceptionInfo error
          (boolean (re-find #"one direct typed capability move"
                            (.getMessage error)))))))

(deftest linear-let-with-non-linear-companion-binding-is-admitted
  "ADR 0138: non-linear companions may share a let with one linear binding."
  (let [checked
        (compiler/check-source
         "(ns app (:export [open]))
          (defn open [url :string] [:task [:stream :bytes]]
            (let [n 1
                  task (typed-cap-call :http/get-stream :string
                         [:task [:stream :bytes]] url)]
              task))"
         {:allow #{[:cap/call 13]}})
        function (first (get-in checked [:hir :functions]))]
    (is (= [:task [:stream :bytes]] (:result function)))
    (is (= 'let (first (:body function))))))

(deftest linear-nested-non-linear-outer-let-is-admitted
  "ADR 0138: non-linear outer lets may wrap an affine inner move."
  (let [checked
        (compiler/check-source
         "(ns app (:export [open]))
          (defn open [url :string] [:task [:stream :bytes]]
            (let [u url]
              (let [task (typed-cap-call :http/get-stream :string
                           [:task [:stream :bytes]] u)]
                task)))"
         {:allow #{[:cap/call 13]}})]
    (is (= [:task [:stream :bytes]]
           (get-in checked [:hir :functions 0 :result])))))

(deftest linear-if-balanced-consume-is-admitted
  "ADR 0138: both if arms may consume the same affine binding."
  (let [checked
        (compiler/check-source
         "(ns app (:export [size]))
          (defn size [url :string flag :i64] :i64
            (let [task (typed-cap-call :http/get-stream :string
                         [:task [:stream :bytes]] url)]
              (if flag
                (bytes-task-byte-count task)
                (task-ready? task))))"
         {:allow #{[:cap/call 13]}})]
    (is (= :i64 (get-in checked [:hir :functions 0 :result])))))

(deftest linear-if-unbalanced-consume-is-rejected
  "One arm consuming and the other ignoring the binding is not affine."
  (is (try
        (compiler/check-source
         "(ns app (:export [bad]))
          (defn bad [url :string flag :i64] :i64
            (let [task (typed-cap-call :http/get-stream :string
                         [:task [:stream :bytes]] url)]
              (if flag
                (bytes-task-byte-count task)
                0)))"
         {:allow #{[:cap/call 13]}})
        false
        (catch clojure.lang.ExceptionInfo error
          (boolean (re-find #"one direct typed capability move"
                            (.getMessage error)))))))

(deftest linear-if-balanced-move-is-admitted
  (let [checked
        (compiler/check-source
         "(ns app (:export [open]))
          (defn open [url :string flag :i64] [:task [:stream :bytes]]
            (let [task (typed-cap-call :http/get-stream :string
                         [:task [:stream :bytes]] url)]
              (if flag task task)))"
         {:allow #{[:cap/call 13]}})]
    (is (= [:task [:stream :bytes]]
           (get-in checked [:hir :functions 0 :result])))))
