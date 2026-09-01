(ns kotoba.compiler.reference-runtime-test
  (:require [clojure.test :refer [deftest is]]
            [kotoba.compiler.core :as compiler]
            [kotoba.kir :as ir]
            [kotoba.compiler.reference-runtime :as runtime]))

(def source
  "(ns app.reference (:export [invoke]) (:capabilities #{:http/post}))
   (defn invoke [request :string] :string
     (typed-cap-call :http/post :string :string request))")

(defn- kir []
  (ir/lower (:hir (compiler/check-source source {:allow #{[:cap/call 4]}}))))

(def scope
  {:capability 4 :action :http/post :resource "https://api.example.test/messages"})

(def authority-context
  {:format :kotoba.authority-context/v1
   :principal {:format :kotoba.principal/v1
               :id "did:key:z6Mk-test"
               :proof-sha256 (apply str (repeat 64 "a"))}
   :grant {:format :kotoba.authority-grant/v1
           :id "grant:message-post"
           :subject "did:key:z6Mk-test"
           :audience "amu://reference-runtime"
           :not-before 100 :expires 200
           :capabilities #{scope}
           :evidence-sha256 (apply str (repeat 64 "b"))}
   :local-policy {:format :kotoba.authority-policy/v1
                  :id "policy:reference-runtime"
                  :audience "amu://reference-runtime"
                  :principals #{"did:key:z6Mk-test"}
                  :capabilities #{scope}}
   :audience "amu://reference-runtime"
   :now 150})

(deftest portable-reference-runtime-dispatches-an-exact-provider
  (let [host (runtime/instantiate
              (kir)
              {:allow #{4}
               :providers {4 {:request-type :string :result-type :string
                              :invoke #(str % "!")}}})]
    (is (= :kotoba.reference-runtime/v1 (:format host)))
    (is (= "hello!" ((:invoke host) 'invoke ["hello"])))))

(deftest provider-contracts-are-closed-and-deny-by-default
  (is (thrown-with-msg? clojure.lang.ExceptionInfo #"keyed by capability ids"
                        (runtime/instantiate (kir) {:providers {:http/post {}}})))
  (is (thrown-with-msg? clojure.lang.ExceptionInfo #"does not match"
                        (runtime/instantiate
                         (kir)
                         {:allow #{4}
                          :providers {4 {:request-type :i64 :result-type :string
                                         :invoke identity}}})))
  (let [host (runtime/instantiate (kir))]
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"capability denied"
                          ((:invoke host) 'invoke ["hello"])))))

(deftest lisp-eval-is-the-exact-typed-code-eval-provider
  (let [source "(ns app.eval (:export [run]) (:capabilities #{:code/eval}))
                (defn run [request :document] :i64 (eval request))"
        kir (ir/lower
             (:hir (compiler/check-source source {:allow #{[:cap/call 30]}})))
        body (-> kir :functions first :body)
        request ["map" []]]
    (is (= '(typed-cap-call 30 :document :i64 request) body))
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"capability denied"
         ((:invoke (runtime/instantiate kir)) 'run [request])))
    (let [host (runtime/instantiate
                kir {:allow #{30}
                     :providers
                     {30 {:request-type :document :result-type :i64
                          :invoke (fn [_] 42)}}})]
      (is (= 42 ((:invoke host) 'run [request]))))
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"does not match"
         (runtime/instantiate
          kir {:allow #{30}
               :providers
               {30 {:request-type :string :result-type :i64
                    :invoke (fn [_] 42)}}})))))

(deftest dynamic-authority-is-intersected-at-provider-invocation
  (let [host (runtime/instantiate
              (kir)
              {:allow #{4}
               :authority authority-context
               :providers {4 {:request-type :string :result-type :string
                              :scope (constantly scope)
                              :invoke #(str % "!")}}})
        {:keys [result authority-decisions]}
        ((:invoke-authorized host) 'invoke ["hello"])
        decision (first authority-decisions)]
    (is (= "hello!" result))
    (is (= 1 (count authority-decisions)))
    (is (= "did:key:z6Mk-test" (:principal decision)))
    (is (= (select-keys scope [:capability :action :resource])
           (select-keys decision [:capability :action :resource])))
    (is (= "grant:message-post" (:grant-id decision)))
    (is (= "policy:reference-runtime" (:policy-id decision)))))

(deftest dynamic-authority-denies-before-provider-side-effects
  (let [invoked? (atom false)
        host (runtime/instantiate
              (kir)
              {:allow #{4}
               :authority authority-context
               :providers {4 {:request-type :string :result-type :string
                              :scope (fn [_]
                                       (assoc scope :resource
                                              "https://api.example.test/admin"))
                              :invoke (fn [request]
                                        (reset! invoked? true)
                                        request)}}})]
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"delegated authority"
                          ((:invoke host) 'invoke ["hello"])))
    (is (false? @invoked?))))

(deftest expired-dynamic-authority-fails-closed-at-use-time
  (let [host (runtime/instantiate
              (kir)
              {:allow #{4}
               :authority (assoc authority-context :now 200)
               :providers {4 {:request-type :string :result-type :string
                              :scope (constantly scope)
                              :invoke identity}}})]
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"grant rejected"
                          ((:invoke host) 'invoke ["hello"])))))
