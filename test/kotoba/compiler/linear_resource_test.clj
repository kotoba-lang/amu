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

(deftest linear-cond-multi-arm-consume-is-admitted
  "ADR 0139: cond desugars to nested if; every arm may consume the binding."
  (let [checked
        (compiler/check-source
         "(ns app (:export [size]))
          (defn size [url :string a :i64 b :i64] :i64
            (let [task (typed-cap-call :http/get-stream :string
                         [:task [:stream :bytes]] url)]
              (cond a (bytes-task-byte-count task)
                    b (task-ready? task)
                    :else (bytes-task-byte-count task))))"
         {:allow #{[:cap/call 13]}})]
    (is (= :i64 (get-in checked [:hir :functions 0 :result])))))

(deftest linear-case-multi-arm-consume-is-admitted
  "ADR 0139: case desugars to (let [tmp dispatch] nested if); exclusive-use
  walks the dispatch let so multi-arm consume is admitted."
  (let [checked
        (compiler/check-source
         "(ns app (:export [size]))
          (defn size [url :string k :i64] :i64
            (let [task (typed-cap-call :http/get-stream :string
                         [:task [:stream :bytes]] url)]
              (case k
                0 (bytes-task-byte-count task)
                1 (task-ready? task)
                (bytes-task-byte-count task))))"
         {:allow #{[:cap/call 13]}})]
    (is (= :i64 (get-in checked [:hir :functions 0 :result])))
    (is (= 'let (first (get-in checked [:hir :functions 0 :body]))))))

(deftest linear-case-multi-arm-move-is-admitted
  (let [checked
        (compiler/check-source
         "(ns app (:export [open]))
          (defn open [url :string k :i64] [:task [:stream :bytes]]
            (let [task (typed-cap-call :http/get-stream :string
                         [:task [:stream :bytes]] url)]
              (case k
                0 task
                1 task
                task)))"
         {:allow #{[:cap/call 13]}})]
    (is (= [:task [:stream :bytes]]
           (get-in checked [:hir :functions 0 :result])))))

(deftest linear-case-unbalanced-is-rejected
  (is (try
        (compiler/check-source
         "(ns app (:export [bad]))
          (defn bad [url :string k :i64] :i64
            (let [task (typed-cap-call :http/get-stream :string
                         [:task [:stream :bytes]] url)]
              (case k
                0 (bytes-task-byte-count task)
                1 0
                (bytes-task-byte-count task))))"
         {:allow #{[:cap/call 13]}})
        false
        (catch clojure.lang.ExceptionInfo error
          (boolean (re-find #"one direct typed capability move"
                            (.getMessage error)))))))

(deftest linear-condp-multi-arm-consume-is-admitted
  "ADR 0139: condp also desugars through dispatch let + nested if."
  (let [checked
        (compiler/check-source
         "(ns app (:export [size]))
          (defn size [url :string k :i64] :i64
            (let [task (typed-cap-call :http/get-stream :string
                         [:task [:stream :bytes]] url)]
              (condp = k
                0 (bytes-task-byte-count task)
                1 (task-ready? task)
                (bytes-task-byte-count task))))"
         {:allow #{[:cap/call 13]}})]
    (is (= :i64 (get-in checked [:hir :functions 0 :result])))))

(deftest linear-one-arm-if-consume-is-admitted
  "ADR 0142: linear produce+consume fully closed in one if arm."
  (let [checked
        (compiler/check-source
         "(ns app (:export [size]))
          (defn size [url :string flag :i64] :i64
            (if flag
              (let [task (typed-cap-call :http/get-stream :string
                           [:task [:stream :bytes]] url)]
                (bytes-task-byte-count task))
              0))"
         {:allow #{[:cap/call 13]}})]
    (is (= :i64 (get-in checked [:hir :functions 0 :result])))))

(deftest linear-one-arm-if-unclosed-else-producer-is-rejected
  "Else arm must not introduce a second unconsumed linear producer."
  (is (try
        (compiler/check-source
         "(ns app (:export [bad]))
          (defn bad [url :string flag :i64] :i64
            (if flag
              (let [task (typed-cap-call :http/get-stream :string
                           [:task [:stream :bytes]] url)]
                (bytes-task-byte-count task))
              (bytes-task-byte-count
                (typed-cap-call :http/get-stream :string
                  [:task [:stream :bytes]] url))))"
         {:allow #{[:cap/call 13]}})
        ;; Two distinct producers — ownership rejects even if both consume
        false
        (catch clojure.lang.ExceptionInfo error
          (boolean (re-find #"one direct typed capability move"
                            (.getMessage error)))))))
