(ns kotoba.compiler.aggregate-abi-test
  (:require [clojure.edn :as edn]
            [clojure.test :refer [deftest is]]
            [kotoba.native.aggregate-abi :as aggregate-abi]
            [kotoba.native.machine-ir :as machine]))

(defn- dependency-pin [coordinate]
  (get-in (edn/read-string (slurp "deps.edn")) [:deps coordinate :git/sha]))

(deftest pinned-closure-carries-the-scalar-call-boundary
  (is (= "1eb54af54ce12667af4138bb4fdb0cb02cbe465b"
         (dependency-pin 'io.github.kotoba-lang/kotoba-native)))
  (is (= "f1d8e07c49d90e8670bf1f375cb1bb2155c1a52c"
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
           (mapv :gmir/name (:gmir/functions gmir))))
    (doseq [target [:x86-64 :aarch64]]
      (let [mc (machine/compile-gmir target gmir)
            caller (second (:mc/functions mc))
            encodings (map :mc/encoding (:mc/instructions caller))]
        (is (= :call-live (:mc/frame-policy caller)) target)
        (is (= 1 (:mc/frame-slots caller)) target)
        (is (= 1 (count (filter #{(keyword (name target) "spill-store")}
                                encodings))) target)
        (is (= 1 (count (filter #{(keyword (name target) "spill-load")}
                                encodings))) target)))))

(deftest pinned-closure-carries-the-zero-frame-four-argument-entry
  (let [module {:format :kotoba.kir/v4
                :exports ['main]
                :functions
                [{:name 'sum-four :params ['a 'b 'c 'd] :result :i64
                  :body '(+ (+ a b) (+ c d))}
                 {:name 'main :params [] :result :i64
                  :body '(sum-four 1 2 4 8)}]}]
    (doseq [target [:x86-64 :aarch64]]
      (let [[callee caller]
            (:mc/functions (->> module machine/lower-kir-module
                                (machine/compile-gmir target)))
            spill-encodings #{(keyword (name target) "spill-store")
                              (keyword (name target) "spill-load")}]
        (is (= [0 0] (mapv :mc/frame-slots [callee caller])) target)
        (is (= [:allocator :call-live]
               (mapv :mc/frame-policy [callee caller])) target)
        (is (not-any? #(contains? spill-encodings (:mc/encoding %))
                      (mapcat :mc/instructions [callee caller])) target)))))
