(ns kotoba.compiler.aggregate-abi-test
  (:require [clojure.edn :as edn]
            [clojure.test :refer [deftest is]]
            [kotoba.native.aggregate-abi :as aggregate-abi]
            [kotoba.native.machine-ir :as machine]))

(defn- dependency-pin [coordinate]
  (get-in (edn/read-string (slurp "deps.edn")) [:deps coordinate :git/sha]))

(deftest pinned-closure-carries-the-scalar-call-boundary
  (is (= "228e389ccc449d6256a7f6ba0b623203e0a439d9"
         (dependency-pin 'io.github.kotoba-lang/kotoba-native)))
  (is (= "6df0626c78c60d45103d2d18ea23afc8471acf7b"
         (dependency-pin 'io.github.kotoba-lang/kotoba-verifier)))
  (is (= 2 (:abi/version aggregate-abi/contract)))
  (is (= :held (get-in aggregate-abi/contract
                        [:extracted :record-boundary])))
  (is (= :held (get-in aggregate-abi/contract
                        [:extracted :variant-boundary])))
  (is (= :scalar-admitted (get-in aggregate-abi/contract
                                   [:extracted :call-admission])))
  (is (= :all-allocator-registers
         (get-in aggregate-abi/contract
                 [:targets :x86-64 :call-clobbers])))
  (is (= :all-allocator-registers
         (get-in aggregate-abi/contract
                 [:targets :aarch64 :call-clobbers]))))

(deftest standalone-expressions-still-reject-calls-but-modules-admit-them
  (is (not (machine/pilot-expression? ['x] '(callee x))))
  (try
    (machine/lower-kir-expression ['x] '(callee x))
    (is false "call-shaped KIR must remain on the established emitter")
    (catch clojure.lang.ExceptionInfo error
      (is (= :aggregate-abi (:phase (ex-data error))))
      (is (= :call-abi-not-admitted (:problem (ex-data error))))))
  (let [module {:format :kotoba.kir/v4
                :exports ['main]
                :functions [{:name 'inc-one :params ['x] :result :i64
                             :body '(+ x 1)}
                            {:name 'main :params [] :result :i64
                             :body '(let [live 40]
                                      (+ live (inc-one 1)))}]}
        gmir (machine/lower-kir-module module)]
    (is (machine/pilot-module? module))
    (is (= 3 (:gmir/version gmir)))
    (is (= ['inc-one 'main]
           (mapv :gmir/name (:gmir/functions gmir))))))
