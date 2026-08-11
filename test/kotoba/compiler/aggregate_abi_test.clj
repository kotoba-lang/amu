(ns kotoba.compiler.aggregate-abi-test
  (:require [clojure.edn :as edn]
            [clojure.test :refer [deftest is]]
            [kotoba.native.aggregate-abi :as aggregate-abi]
            [kotoba.native.machine-ir :as machine]))

(defn- dependency-pin [coordinate]
  (get-in (edn/read-string (slurp "deps.edn")) [:deps coordinate :git/sha]))

(deftest pinned-closure-carries-the-complete-native-boundary
  (is (= "dd7fe0cf8972ef20bcc24894b7c7aaf9d086c1a6"
         (dependency-pin 'io.github.kotoba-lang/kotoba-native)))
  (is (= "d58972da61758584a5bec0e863bcb3ea6fdd6c64"
         (dependency-pin 'io.github.kotoba-lang/kotoba-kir)))
  (is (= "e2c0e3f49bd7828cd187aee6a90ba5e6f2474149"
         (dependency-pin 'io.github.kotoba-lang/kotoba-verifier)))
  (is (= 6 (:abi/version aggregate-abi/contract)))
  (is (= :recursive-word-handles
         (get-in aggregate-abi/contract
                 [:portable/record :boundary/field-representation])))
  (is (= 32
         (get-in aggregate-abi/contract
                 [:portable/record :boundary/max-nesting-depth])))
  (is (= :word-pair-chain-admitted (get-in aggregate-abi/contract
                        [:extracted :record-boundary])))
  (is (= :scalar-pair-handle-admitted (get-in aggregate-abi/contract
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
    (is false "standalone call-shaped KIR must require module lowering")
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

(deftest pinned-closure-carries-the-one-slot-five-argument-entry
  (let [module {:format :kotoba.kir/v4
                :exports ['main]
                :functions
                [{:name 'sum-five :params ['a 'b 'c 'd 'e] :result :i64
                  :body '(+ (+ (+ a b) (+ c d)) e)}
                 {:name 'main :params ['a 'b 'c 'd 'e] :result :i64
                  :body '(sum-five a b c d e)}]}]
    (doseq [target [:x86-64 :aarch64]]
      (let [[callee caller]
            (:mc/functions (->> module machine/lower-kir-module
                                (machine/compile-gmir target)))
            functions [callee caller]
            store-encoding (keyword (name target) "spill-store")
            load-encoding (keyword (name target) "spill-load")]
        (is (= [1 1] (mapv :mc/frame-slots functions)) target)
        (is (= [:allocator :call-live]
               (mapv :mc/frame-policy functions)) target)
        (doseq [function functions]
          (let [encodings (map :mc/encoding (:mc/instructions function))]
            (is (= 1 (count (filter #{store-encoding} encodings)))
                [target (:mc/name function)])
            (is (= 1 (count (filter #{load-encoding} encodings)))
                [target (:mc/name function)])))))))
