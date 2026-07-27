(ns kotoba.compiler.effectful-component-source-test
  (:require [clojure.test :refer [deftest is testing]]
            [clojure.string :as str]
            [kotoba.compiler.core :as compiler]))

(def source
  "(ns app (:capabilities #{:clock/now}))
   (defn main [] (cap-call :clock/now 7))")

(def policy {:allow #{[:cap/call 7]}})
(def clock-ability
  {:target "clock://monotonic" :operation :clock/now
   :max-bytes 1 :max-items 1 :deadline-ms 1000 :audit-id "compiler-test"})

(deftest source-cap-call-becomes-a-closed-component-import
  (let [artifact (compiler/compile-component source policy)
        wit-source (get-in artifact [:wit :source])]
    (testing "source compiles to a real Component rather than generic core-Wasm"
      (is (= :wasm-component/v1 (:format artifact)))
      (is (pos? (alength ^bytes (:bytes artifact))))
      (is (= :wasm-component-kotoba-v1
             (get-in artifact [:provenance :target])))
      (is (= :wasm-component
             (get-in artifact [:provenance :outputs :primary :format])))
      (is (= (:sha256 artifact)
             (get-in artifact [:provenance :outputs :primary :sha256]))))
    (testing "the legacy scalar source operation is exposed as named s64 -> s64"
      (is (str/includes? wit-source "import clock"))
      (is (str/includes? wit-source "now: func(request: s64) -> s64"))
      (is (not (str/includes? wit-source "kotoba:cap::call")))))
  (let [artifact (compiler/compile-component
                  source policy {:component-abilities {7 clock-ability}})]
    (is (= #{:aiueos.component/aiueos-clock-now} (:capabilities artifact)))
    (is (= {:aiueos.component/aiueos-clock-now clock-ability}
           (:component-imports artifact))))
  (testing "memory ceiling is part of executable Component identity"
    (let [five (compiler/compile-component
                source policy {:component-abilities {7 clock-ability}
                               :budgets {:memory-pages 5}})
          eight (compiler/compile-component
                 source policy {:component-abilities {7 clock-ability}
                                :budgets {:memory-pages 8}})]
      (is (not= (:sha256 five) (:sha256 eight)))
      (is (thrown-with-msg?
           clojure.lang.ExceptionInfo #"memory budget"
           (compiler/compile-component
            source policy {:component-abilities {7 clock-ability}
                           :budgets {:memory-pages 4}}))))))

(deftest direct-capability-call-can-use-a-linear-wit-resource
  (let [source "(defn main [] (cap-call :clock/now 7))"
        artifact (compiler/compile-component
                  source policy
                  {:capability-mode :linear-resource
                   :component-abilities {7 clock-ability}})
        wit (get-in artifact [:wit :source])]
    (is (= :linear-resource (:capability-mode artifact)))
    (is (= :linear-resource (get-in artifact [:wit :capability-mode])))
    (is (re-find #"resource now-capability;" wit))
    (is (re-find #"issue-now: func\(\) -> own<now-capability>;" wit))
    (is (re-find #"execute-now: func\(cap: own<now-capability>, request: s64\) -> s64;" wit))
    (is (pos? (alength ^bytes (:bytes artifact))))
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"requires one direct"
         (compiler/compile-component
          "(defn main [] (+ 1 (cap-call :clock/now 7)))" policy
          {:capability-mode :linear-resource
           :component-abilities {7 clock-ability}})))))
