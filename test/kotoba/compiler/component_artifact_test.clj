(ns kotoba.compiler.component-artifact-test
  (:require [clojure.edn :as edn]
            [clojure.java.io :as io]
            [clojure.java.shell :as shell]
            [clojure.test :refer [deftest is]]
            [clojure.string :as str]
            [kotoba.wasm.core :as wasm]
            [kotoba.component.artifact :as component]
            [kotoba.component.core :as component-core]
            [kotoba.component.wit :as wit]
            [kotoba.compiler.core :as compiler]
            [kotoba.kir :as ir]
            [kotoba.kir.value :as value])
  (:import [java.nio.file Files]
           [java.nio.file.attribute FileAttribute]))

(def ^:private wasmtime-binary
  (let [pinned (io/file ".tools" "wasmtime" "wasmtime")]
    (if (.canExecute pinned) (.getPath pinned) "wasmtime")))

(def scalar-kir
  {:format :kotoba.kir/v4 :exports ['add]
   :schemas {}
   :functions [{:name 'add :params ['left 'right]
                :param-types [:i64 :i64] :result :i64 :body '(+ left right)}]})

(deftest scalar-slice-and-unsupported-boundaries-are-explicit
  (is (true? (component/assert-scalar-slice! scalar-kir (wit/emit scalar-kir))))
  (is (thrown-with-msg? clojure.lang.ExceptionInfo #"no qualified Canonical lowering"
                        (component/assert-scalar-slice!
                         (assoc-in scalar-kir [:functions 0 :result] :string)
                         (wit/emit (assoc-in scalar-kir [:functions 0 :result] :string)))))
  (let [cap-kir (assoc scalar-kir
                       :exports ['invoke]
                       :functions [{:name 'invoke :params ['request]
                                    :param-types [:i64] :result :i64
                                    :body '(typed-cap-call 4 :i64 :i64 request)}])]
    (is (true? (component/assert-scalar-slice! cap-kir (wit/emit cap-kir))))
    (let [artifact (component/package
                    (component-core/emit cap-kir :wasm32-wasi-kotoba-v1)
                    cap-kir (wit/emit cap-kir))]
      (is (= :scalar-capability-call (:canonical-lowering artifact)))
      (is (= [:http/post] (:imports artifact)))
      (is (= :wasm-component/v1 (:format artifact))))))

(deftest bounded-string-expression-slice-is-explicit
  (let [identity-kir
        {:format :kotoba.kir/v4 :exports ['echo] :schemas {} :effects #{}
         :functions [{:name 'echo :params ['value] :param-types [:string]
                      :result :string :body 'value}]}]
    (is (true? (component/assert-scalar-slice! identity-kir (wit/emit identity-kir))))
    (let [concat-kir (-> identity-kir
                         (assoc-in [:functions 0 :params] ['left 'right])
                         (assoc-in [:functions 0 :param-types] [:string :string])
                         (assoc-in [:functions 0 :body]
                                   '(string-concat left (string-concat " / " right))))]
      (is (true? (component/assert-scalar-slice! concat-kir (wit/emit concat-kir)))))
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"no qualified Canonical lowering"
                          (component/assert-scalar-slice!
                           (assoc-in identity-kir [:functions 0 :body]
                                     '(string-replace-all value "a" "b"))
                           (wit/emit identity-kir))))))

(deftest bounded-vector-i64-round-trips-through-a-real-component
  (let [source
        "(ns component.list (:export [echo]))
         (defn echo [items :vector-i64] :vector-i64 items)"
        artifact (compiler/compile-component source)
        kir (:kir (compiler/compile-source source :wasm32-wasi-kotoba-v1))
        world (:wit artifact)
        core (component-core/emit kir :wasm32-wasi-kotoba-v1)
        dir (Files/createTempDirectory
             "kotoba-component-list-" (make-array FileAttribute 0))
        component-path (.resolve dir "list.component.wasm")
        core-path (.resolve dir "list.core.wasm")]
    (try
      (Files/write component-path ^bytes (:bytes artifact)
                   (make-array java.nio.file.OpenOption 0))
      (Files/write core-path ^bytes core
                   (make-array java.nio.file.OpenOption 0))
      (let [round-trip
            (shell/sh wasmtime-binary "run" "--invoke"
                      "echo([1, 2, 3, -4])" (str component-path))
            empty-round-trip
            (shell/sh wasmtime-binary "run" "--invoke"
                      "echo([])" (str component-path))
            maximum-call
            (str "echo([" (str/join "," (repeat 16384 "0")) "])")
            maximum-round-trip
            (shell/sh wasmtime-binary "run" "--invoke"
                      maximum-call (str component-path))
            oversize
            (shell/sh wasmtime-binary "run" "--invoke" "cm32p2||echo"
                      (str core-path) "8" "16385")]
        (is (= :vector-i64-identity (:canonical-lowering artifact)))
        (is (= "list<s64>"
               (second (re-find #"(list<s64>)" (:source world)))))
        (is (zero? (:exit round-trip)) (:err round-trip))
        (is (= "[1, 2, 3, -4]" (str/trim (:out round-trip))))
        (is (= "[]" (str/trim (:out empty-round-trip))))
        (is (zero? (:exit maximum-round-trip)) (:err maximum-round-trip))
        (is (= 16384 (count (edn/read-string (:out maximum-round-trip)))))
        (is (not (zero? (:exit oversize)))
            "a length above vector-item-limit must trap in the core"))
      (finally
        (Files/deleteIfExists component-path)
        (Files/deleteIfExists core-path)
        (Files/deleteIfExists dir)))))

(deftest vector-i64-single-shot-literal-and-conj-policy-are-executable
  (let [artifact
        (compiler/compile-component
         "(ns component.list-literal (:export [items]))
          (defn items [] :vector-i64 (vector-i64 7 -8 9))")
        oracle-kir
        (:kir
         (compiler/compile-source
          "(ns component.list-literal (:export [items]))
           (defn items [] :vector-i64 (vector-i64 7 -8 9))"
          :wasm32-wasi-kotoba-v1))
        path (Files/createTempFile
              "kotoba-component-list-literal-" ".wasm"
              (make-array FileAttribute 0))]
    (try
      (Files/write path ^bytes (:bytes artifact)
                   (make-array java.nio.file.OpenOption 0))
      (let [result (shell/sh wasmtime-binary "run" "--invoke"
                             "items()" (str path))]
        (is (= :vector-i64-literal (:canonical-lowering artifact)))
        (is (= [7 -8 9] (ir/execute oracle-kir 'items [])))
        (is (zero? (:exit result)) (:err result))
        (is (= "[7, -8, 9]" (str/trim (:out result)))))
      (finally
        (Files/deleteIfExists path))))
  (is (thrown-with-msg?
       clojure.lang.ExceptionInfo
       #"vector-conj requires linearity analysis \(ADR 0077\)"
       (compiler/compile-component
        "(ns component.list-conj (:export [append]))
         (defn append [items :vector-i64] :vector-i64
           (vector-conj items 1))"))))

(deftest structural-option-and-result-round-trip-through-a-real-component
  (doseq [{:keys [descriptor calls expected]}
          [{:descriptor [:option :i64]
            :calls ["echo(none)" "echo(some(7))"]
            :expected ["none" "some(7)"]}
           {:descriptor [:result :i64 :i64]
            :calls ["echo(ok(7))" "echo(err(-8))"]
            :expected ["ok(7)" "err(-8)"]}]]
    (let [kir {:format :kotoba.kir/v4 :exports ['echo] :schemas {} :effects #{}
               :functions [{:name 'echo :params ['value]
                            :param-types [descriptor] :result descriptor
                            :body 'value}]}
          world (wit/emit kir)
          artifact (component/package
                    (component-core/emit kir :wasm32-wasi-kotoba-v1)
                    kir world)
          core (component-core/emit kir :wasm32-wasi-kotoba-v1)
          dir (Files/createTempDirectory
               "kotoba-component-union-" (make-array FileAttribute 0))
          component-path (.resolve dir "union.component.wasm")
          core-path (.resolve dir "union.core.wasm")]
      (try
        (Files/write component-path ^bytes (:bytes artifact)
                     (make-array java.nio.file.OpenOption 0))
        (Files/write core-path ^bytes core
                     (make-array java.nio.file.OpenOption 0))
        (is (= :structural-union-identity (:canonical-lowering artifact)))
        (doseq [[call output] (map vector calls expected)]
          (let [run (shell/sh wasmtime-binary "run" "--invoke" call
                              (str component-path))]
            (is (zero? (:exit run)) (:err run))
            (is (= output (str/trim (:out run))))))
        (let [malformed (shell/sh wasmtime-binary "run" "--invoke"
                                  "cm32p2||echo" (str core-path) "2" "0")]
          (is (not (zero? (:exit malformed)))
              "an out-of-range option/result discriminant must trap"))
        (finally
          (Files/deleteIfExists component-path)
          (Files/deleteIfExists core-path)
          (Files/deleteIfExists dir))))))

(deftest structural-option-record-round-trips-through-the-extracted-backend
  (let [point [:ref :demo/point]
        descriptor [:option point]
        kir {:format :kotoba.kir/v4
             :exports ['echo]
             :schemas {:demo/point
                       [:record :demo/point [[:x :i64] [:visible :bool]]]}
             :effects #{}
             :functions
             [{:name 'echo :params ['value] :param-types [descriptor]
               :result descriptor :effects #{} :body 'value}]}
        world (wit/emit kir)
        core-bytes (component-core/emit kir :wasm32-wasi-kotoba-v1)
        artifact (component/package core-bytes kir world)
        component-path (Files/createTempFile
                        "kotoba-component-option-record-" ".wasm"
                        (make-array FileAttribute 0))
        core-path (Files/createTempFile
                   "kotoba-component-option-record-core-" ".wasm"
                   (make-array FileAttribute 0))]
    (try
      (is (= :structural-union-identity (:canonical-lowering artifact)))
      (Files/write component-path ^bytes (:bytes artifact)
                   (make-array java.nio.file.OpenOption 0))
      (Files/write core-path ^bytes core-bytes
                   (make-array java.nio.file.OpenOption 0))
      (doseq [[invoke expected]
              [["echo(none)" "none"]
               ["echo(some({x: 7, visible: true}))"
                "some({x: 7, visible: true})"]]]
        (let [run (shell/sh wasmtime-binary "run" "--invoke" invoke
                            (str component-path))]
          (is (zero? (:exit run)) (:err run))
          (is (= expected (str/trim (:out run))) invoke)))
      (let [inactive (shell/sh wasmtime-binary "run" "--invoke"
                               "cm32p2||echo" (str core-path) "0" "0" "2")
            active (shell/sh wasmtime-binary "run" "--invoke"
                             "cm32p2||echo" (str core-path) "1" "7" "2")]
        (is (zero? (:exit inactive)))
        (is (not (zero? (:exit active)))))
      (finally
        (Files/deleteIfExists component-path)
        (Files/deleteIfExists core-path)))))

(deftest nested-record-and-string-unions-use-the-extracted-recursive-codec
  (let [schemas {:demo/inner
                 [:record :demo/inner [[:label :string] [:enabled :bool]]]
                 :demo/outer
                 [:record :demo/outer
                  [[:id :i64] [:inner [:ref :demo/inner]]]]}]
    (doseq [{:keys [descriptor invoke expected]}
            [{:descriptor [:option [:ref :demo/outer]]
              :invoke
              "echo(some({id: 9, inner: {label: \"hi\", enabled: true}}))"
              :expected
              "some({id: 9, inner: {label: \"hi\", enabled: true}})"}
             {:descriptor [:option :string]
              :invoke "echo(some(\"hello\"))"
              :expected "some(\"hello\")"}]]
      (let [kir {:format :kotoba.kir/v4 :exports ['echo]
                 :schemas schemas :effects #{}
                 :functions
                 [{:name 'echo :params ['value] :param-types [descriptor]
                   :result descriptor :effects #{} :body 'value}]}
            world (wit/emit kir)
            artifact (component/package
                      (component-core/emit kir :wasm32-wasi-kotoba-v1)
                      kir world)
            path (Files/createTempFile
                  "kotoba-component-recursive-union-" ".wasm"
                  (make-array FileAttribute 0))]
        (try
          (is (= :structural-union-identity
                 (:canonical-lowering artifact)))
          (Files/write path ^bytes (:bytes artifact)
                       (make-array java.nio.file.OpenOption 0))
          (let [run (shell/sh wasmtime-binary "run" "--invoke" invoke
                              (str path))]
            (is (zero? (:exit run)) (:err run))
            (is (= expected (str/trim (:out run)))))
          (finally
            (Files/deleteIfExists path)))))))

(deftest structural-option-and-result-constructors-compile-from-kotoba
  (doseq [{:keys [source export invoke output args oracle]}
          [{:source "(ns component.make-none (:export [make-none]))
                     (defn make-none [] [:option :i64]
                       (option-none-of [:option :i64]))"
            :export 'make-none :invoke "make-none()" :output "none"
            :args [] :oracle [[:option :i64] false]}
           {:source "(ns component.make-some (:export [make-some]))
                     (defn make-some [value :i64] [:option :i64]
                       (option-some-of [:option :i64] value))"
            :export 'make-some :invoke "make-some(7)" :output "some(7)"
            :args [7] :oracle [[:option :i64] true 7]}
           {:source "(ns component.make-ok (:export [make-ok]))
                     (defn make-ok [value :i64] [:result :i64 :i64]
                       (result-ok-of [:result :i64 :i64] value))"
            :export 'make-ok :invoke "make-ok(8)" :output "ok(8)"
            :args [8] :oracle [true 8]}
           {:source "(ns component.make-err (:export [make-err]))
                     (defn make-err [value :i64] [:result :i64 :i64]
                       (result-err-of [:result :i64 :i64] value))"
            :export 'make-err :invoke "make-err(-9)" :output "err(-9)"
            :args [-9] :oracle [false -9]}]]
    (let [artifact (compiler/compile-component source)
          kir (:kir (compiler/compile-source source :wasm32-wasi-kotoba-v1))
          path (Files/createTempFile
                "kotoba-component-union-constructor-" ".wasm"
                (make-array FileAttribute 0))]
      (try
        (Files/write path ^bytes (:bytes artifact)
                     (make-array java.nio.file.OpenOption 0))
        (let [run (shell/sh wasmtime-binary "run" "--invoke" invoke (str path))]
          (is (= :structural-union-construction
                 (:canonical-lowering artifact)))
          (is (= oracle (ir/execute kir export args)))
          (is (zero? (:exit run)) (:err run))
          (is (= output (str/trim (:out run)))))
        (finally
          (Files/deleteIfExists path))))))

(deftest structural-option-and-result-eliminators-compile-from-kotoba
  (doseq [{:keys [source export calls]}
          [{:source "(ns component.is-some (:export [is-some]))
                     (defn is-some [value [:option :i64]] :bool
                       (option-some?-of [:option :i64] value))"
            :export 'is-some
            :calls [["is-some(none)" "false" [[[:option :i64] false]]]
                    ["is-some(some(7))" "true" [[[:option :i64] true 7]]]]}
           {:source "(ns component.read-option (:export [read-option]))
                     (defn read-option
                       [value [:option :i64] fallback :i64] :i64
                       (option-value-of [:option :i64] value fallback))"
            :export 'read-option
            :calls [["read-option(none, 41)" "41"
                     [[[:option :i64] false] 41]]
                    ["read-option(some(7), 41)" "7"
                     [[[:option :i64] true 7] 41]]]}
           {:source "(ns component.is-ok (:export [is-ok]))
                     (defn is-ok [value [:result :i64 :i64]] :bool
                       (result-ok?-of [:result :i64 :i64] value))"
            :export 'is-ok
            :calls [["is-ok(ok(8))" "true" [[true 8]]]
                    ["is-ok(err(-9))" "false" [[false -9]]]]}
           {:source "(ns component.read-ok (:export [read-ok]))
                     (defn read-ok
                       [value [:result :i64 :i64] fallback :i64] :i64
                       (result-value-of [:result :i64 :i64] value fallback))"
            :export 'read-ok
            :calls [["read-ok(ok(8), 41)" "8" [[true 8] 41]]
                    ["read-ok(err(-9), 41)" "41" [[false -9] 41]]]}
           {:source "(ns component.read-error (:export [read-error]))
                     (defn read-error
                       [value [:result :i64 :i64] fallback :i64] :i64
                       (result-error-of [:result :i64 :i64] value fallback))"
            :export 'read-error
            :calls [["read-error(ok(8), 41)" "41" [[true 8] 41]]
                    ["read-error(err(-9), 41)" "-9" [[false -9] 41]]]}]]
    (let [artifact (compiler/compile-component source)
          kir (:kir (compiler/compile-source source :wasm32-wasi-kotoba-v1))
          path (Files/createTempFile
                "kotoba-component-union-eliminator-" ".wasm"
                (make-array FileAttribute 0))]
      (try
        (Files/write path ^bytes (:bytes artifact)
                     (make-array java.nio.file.OpenOption 0))
        (is (= :structural-union-elimination
               (:canonical-lowering artifact)))
        (doseq [[invoke output args] calls]
          (let [run (shell/sh wasmtime-binary "run" "--invoke" invoke (str path))]
            (is (= output (str/trim (:out run))) (:err run))
            (is (zero? (:exit run)) (:err run))
            (is (= output (str (ir/execute kir export args))))))
        (finally
          (Files/deleteIfExists path))))))

(deftest structural-option-bool-projection-validates-only-the-active-case
  (let [source "(ns component.option-bool (:export [read-bool]))
                (defn read-bool
                  [value [:option :bool] fallback :bool] :bool
                  (option-value-of [:option :bool] value fallback))"
        artifact (compiler/compile-component source)
        kir (:kir (compiler/compile-source source :wasm32-wasi-kotoba-v1))
        core (component-core/emit kir :wasm32-wasi-kotoba-v1)
        dir (Files/createTempDirectory
             "kotoba-component-option-bool-" (make-array FileAttribute 0))
        component-path (.resolve dir "option-bool.component.wasm")
        core-path (.resolve dir "option-bool.core.wasm")]
    (try
      (Files/write component-path ^bytes (:bytes artifact)
                   (make-array java.nio.file.OpenOption 0))
      (Files/write core-path ^bytes core
                   (make-array java.nio.file.OpenOption 0))
      (let [component-run
            (shell/sh wasmtime-binary "run" "--invoke"
                      "read-bool(some(true), false)" (str component-path))
            malformed-active
            (shell/sh wasmtime-binary "run" "--invoke" "cm32p2||read-bool"
                      (str core-path) "1" "2" "0")
            malformed-inactive
            (shell/sh wasmtime-binary "run" "--invoke" "cm32p2||read-bool"
                      (str core-path) "0" "2" "0")]
        (is (zero? (:exit component-run)) (:err component-run))
        (is (= "true" (str/trim (:out component-run))))
        (is (not (zero? (:exit malformed-active)))
            "the selected bool payload must be canonical")
        (is (zero? (:exit malformed-inactive)) (:err malformed-inactive))
        (is (= "0" (str/trim (:out malformed-inactive)))
            "an inactive payload is not interpreted"))
      (finally
        (Files/deleteIfExists component-path)
        (Files/deleteIfExists core-path)
        (Files/deleteIfExists dir)))))

(deftest structural-option-and-result-matches-reuse-general-wasm-expressions
  (doseq [{:keys [source export calls]}
          [{:source "(ns component.match-option (:export [choose]))
                     (defn choose
                       [value [:option :i64] fallback :i64] :i64
                       (match-option value [:option :i64]
                         (none (+ fallback 2))
                         (some item (* item 3))))"
            :export 'choose
            :calls [["choose(none, 10)" "12" [[[:option :i64] false] 10]]
                    ["choose(some(7), 10)" "21"
                     [[[:option :i64] true 7] 10]]]}
           {:source "(ns component.match-result (:export [choose]))
                     (defn choose
                       [value [:result :i64 :i64] offset :i64] :i64
                       (match-result value [:result :i64 :i64]
                         (ok item (+ item offset))
                         (err error (- offset error))))"
            :export 'choose
            :calls [["choose(ok(7), 10)" "17" [[true 7] 10]]
                    ["choose(err(3), 10)" "7" [[false 3] 10]]]}]]
    (let [artifact (compiler/compile-component source)
          kir (:kir (compiler/compile-source source :wasm32-wasi-kotoba-v1))
          path (Files/createTempFile
                "kotoba-component-union-match-" ".wasm"
                (make-array FileAttribute 0))]
      (try
        (Files/write path ^bytes (:bytes artifact)
                     (make-array java.nio.file.OpenOption 0))
        (is (= :structural-union-match (:canonical-lowering artifact)))
        (is (= :module-global (:fuel-enforcement artifact)))
        (doseq [[invoke expected args] calls]
          (let [run (shell/sh wasmtime-binary "run" "--invoke" invoke (str path))]
            (is (zero? (:exit run)) (:err run))
            (is (= expected (str/trim (:out run))))
            (is (= expected (str (ir/execute kir export args))))))
        (finally
          (Files/deleteIfExists path))))))

(deftest structural-union-matches-cover-all-canonical-scalar-types
  (doseq [{:keys [source export calls]}
          [{:source "(ns component.match-option-f64 (:export [choose]))
                     (defn choose
                       [value [:option :f64] fallback :f64] :f64
                       (match-option value [:option :f64]
                         (none (f64-add fallback 0.5))
                         (some item (f64-mul item 2.0))))"
            :export 'choose
            :calls [["choose(none, 2.0)" "2.5"
                     [[[:option :f64] false] 2.0]]
                    ["choose(some(1.75), 2.0)" "3.5"
                     [[[:option :f64] true 1.75] 2.0]]]}
           {:source "(ns component.match-result-f32 (:export [choose]))
                     (defn choose
                       [value [:result :f32 :f32] fallback :f32] :f32
                       (match-result value [:result :f32 :f32]
                         (ok item (f32-add item fallback))
                         (err error (f32-sub fallback error))))"
            :export 'choose
            :calls [["choose(ok(1.5), 2.0)" "3.5"
                     [[true (float 1.5)] (float 2.0)]]
                    ["choose(err(0.5), 2.0)" "1.5"
                     [[false (float 0.5)] (float 2.0)]]]}
           {:source "(ns component.match-option-bool (:export [choose]))
                     (defn choose
                       [value [:option :bool] fallback :bool] :bool
                       (match-option value [:option :bool]
                         (none (bool-not fallback))
                         (some item (bool-not item))))"
            :export 'choose
            :calls [["choose(none, false)" "true"
                     [[[:option :bool] false] false]]
                    ["choose(some(true), false)" "false"
                     [[[:option :bool] true true] false]]]}]]
    (let [artifact (compiler/compile-component source)
          kir (:kir (compiler/compile-source source :wasm32-wasi-kotoba-v1))
          path (Files/createTempFile
                "kotoba-component-scalar-union-match-" ".wasm"
                (make-array FileAttribute 0))]
      (try
        (Files/write path ^bytes (:bytes artifact)
                     (make-array java.nio.file.OpenOption 0))
        (is (= :structural-union-match (:canonical-lowering artifact)))
        (is (empty? (:required-imports artifact))
            "canonical scalar matching must remain host-free")
        (doseq [[invoke expected args] calls]
          (let [run (shell/sh wasmtime-binary "run" "--invoke" invoke (str path))]
            (is (zero? (:exit run)) (:err run))
            (is (= expected (str/trim (:out run))))
            (is (= expected (str (ir/execute kir export args))))))
        (finally
          (Files/deleteIfExists path)))))
  (is (thrown-with-msg?
       clojure.lang.ExceptionInfo #"requires a host value"
       (compiler/compile-component
        "(ns component.match-host-value (:export [choose]))
         (defn choose [value [:option :i64]] :i64
           (match-option value [:option :i64]
             (none (string-byte-length \"not-ambient\"))
             (some item item)))"))
      "a scalar result must not smuggle a host-backed value into the adapter"))

(deftest structural-bool-union-match-validates-only-selected-payload
  (let [source "(ns component.match-option-bool-validation (:export [choose]))
                (defn choose
                  [value [:option :bool] fallback :bool] :bool
                  (match-option value [:option :bool]
                    (none (bool-not fallback))
                    (some item item)))"
        kir (:kir (compiler/compile-source source :wasm32-wasi-kotoba-v1))
        core (component-core/emit kir :wasm32-wasi-kotoba-v1)
        path (Files/createTempFile
              "kotoba-component-bool-union-core-" ".wasm"
              (make-array FileAttribute 0))]
    (try
      (Files/write path ^bytes core (make-array java.nio.file.OpenOption 0))
      (let [inactive (shell/sh wasmtime-binary "run" "--invoke" "cm32p2||choose"
                               (str path) "0" "2" "0")
            active (shell/sh wasmtime-binary "run" "--invoke" "cm32p2||choose"
                             (str path) "1" "2" "0")
            malformed-fallback
            (shell/sh wasmtime-binary "run" "--invoke" "cm32p2||choose"
                      (str path) "0" "0" "2")]
        (is (zero? (:exit inactive)) (:err inactive))
        (is (= "1" (str/trim (:out inactive)))
            "the inactive joined payload is not interpreted")
        (is (not (zero? (:exit active)))
            "a selected bool payload must be canonical")
        (is (not (zero? (:exit malformed-fallback)))
            "an ordinary bool parameter is validated at entry"))
      (finally
        (Files/deleteIfExists path)))))

(deftest structural-result-match-decodes-every-heterogeneous-scalar-join
  (let [fixtures
        {:i64 {:invoke "-7" :value -7 :encoded -7
               :body (fn [binder] binder)}
         :f32 {:invoke "-1.5" :value (float -1.5)
               :encoded (value/f32-to-i64-bits (float -1.5))
               :body (fn [binder] (str "(f32-to-bits " binder ")"))}
         :f64 {:invoke "-1.5" :value -1.5
               :encoded (value/f64-to-i64-bits -1.5)
               :body (fn [binder] (str "(f64-to-bits " binder ")"))}
         :bool {:invoke "true" :value true :encoded 1
                :body (fn [binder] (str "(if " binder " 1 0)"))}}]
    (doseq [ok-type [:i64 :f32 :f64 :bool]
            err-type [:i64 :f32 :f64 :bool]
            :when (not= ok-type err-type)]
      (let [ok (get fixtures ok-type)
            err (get fixtures err-type)
            descriptor [:result ok-type err-type]
            source
            (str "(ns component.match-heterogeneous (:export [choose])) "
                 "(defn choose [value " (pr-str descriptor) "] :i64 "
                 "(match-result value " (pr-str descriptor) " "
                 "(ok item " ((:body ok) "item") ") "
                 "(err error " ((:body err) "error") ")))")
            artifact (compiler/compile-component source)
            kir (:kir (compiler/compile-source source :wasm32-wasi-kotoba-v1))
            path (Files/createTempFile
                  "kotoba-component-heterogeneous-result-" ".wasm"
                  (make-array FileAttribute 0))]
        (try
          (Files/write path ^bytes (:bytes artifact)
                       (make-array java.nio.file.OpenOption 0))
          (is (= :structural-union-match (:canonical-lowering artifact)))
          (is (empty? (:required-imports artifact)))
          (doseq [[case-name fixture tag]
                  [["ok" ok true] ["err" err false]]]
            (let [invoke (str "choose(" case-name "(" (:invoke fixture) "))")
                  run (shell/sh wasmtime-binary "run" "--invoke" invoke (str path))
                  expected (str (:encoded fixture))
                  oracle-arg [[tag (:value fixture)]]]
              (is (zero? (:exit run))
                  (str descriptor " " invoke ": " (:err run)))
              (is (= expected (str/trim (:out run))) (str descriptor " " invoke))
              (is (= expected (str (ir/execute kir 'choose oracle-arg))))))
          (finally
            (Files/deleteIfExists path)))))))

(deftest heterogeneous-result-bool-validation-is-case-dependent
  (doseq [{:keys [descriptor valid-tag invalid-tag]}
          [{:descriptor [:result :bool :f32] :valid-tag "1" :invalid-tag "0"}
           {:descriptor [:result :f32 :bool] :valid-tag "0" :invalid-tag "1"}]]
    (let [source
          (str "(ns component.match-heterogeneous-bool (:export [choose])) "
               "(defn choose [value " (pr-str descriptor) "] :i64 "
               "(match-result value " (pr-str descriptor) " "
               "(ok item "
               (if (= :bool (second descriptor)) "(if item 1 0)" "(f32-to-bits item)")
               ") (err error "
               (if (= :bool (nth descriptor 2)) "(if error 1 0)" "(f32-to-bits error)")
               ")))")
          kir (:kir (compiler/compile-source source :wasm32-wasi-kotoba-v1))
          core (component-core/emit kir :wasm32-wasi-kotoba-v1)
          path (Files/createTempFile
                "kotoba-component-heterogeneous-bool-core-" ".wasm"
                (make-array FileAttribute 0))]
      (try
        (Files/write path ^bytes core (make-array java.nio.file.OpenOption 0))
        (let [inactive-bits
              (shell/sh wasmtime-binary "run" "--invoke" "cm32p2||choose"
                        (str path) valid-tag "2")
              active-bool
              (shell/sh wasmtime-binary "run" "--invoke" "cm32p2||choose"
                        (str path) invalid-tag "2")]
          (is (zero? (:exit inactive-bits)) (:err inactive-bits))
          (is (= "2" (str/trim (:out inactive-bits)))
              "f32 case reinterprets the same i32 bits without bool validation")
          (is (not (zero? (:exit active-bool)))
              "the bool case validates the selected joined slot"))
        (finally
          (Files/deleteIfExists path))))))

(deftest multiple-scalar-union-match-exports-share-one-component-module
  (let [source
        "(ns component.multiple-matches
           (:export [choose-option choose-result negate]))
         (defn- twice [value :i64] :i64 (* value 2))
         (defn choose-option
           [value [:option :i64] fallback :i64] :i64
           (match-option value [:option :i64]
             (none fallback)
             (some item (twice item))))
         (defn choose-result
           [value [:result :bool :f32]] :i64
           (match-result value [:result :bool :f32]
             (ok flag (if flag 1 0))
             (err ratio (f32-to-bits ratio))))
         (defn negate [flag :bool] :bool (bool-not flag))"
        artifact (compiler/compile-component source)
        kir (:kir (compiler/compile-source source :wasm32-wasi-kotoba-v1))
        component-path (Files/createTempFile
                        "kotoba-component-multiple-matches-" ".wasm"
                        (make-array FileAttribute 0))
        fuel-one-path (Files/createTempFile
                       "kotoba-component-multiple-fuel-one-" ".wasm"
                       (make-array FileAttribute 0))
        fuel-two-path (Files/createTempFile
                       "kotoba-component-multiple-fuel-two-" ".wasm"
                       (make-array FileAttribute 0))]
    (try
      (Files/write component-path ^bytes (:bytes artifact)
                   (make-array java.nio.file.OpenOption 0))
      (Files/write fuel-one-path
                   ^bytes (component-core/emit
                           kir :wasm32-wasi-kotoba-v1 {:fuel 1})
                   (make-array java.nio.file.OpenOption 0))
      (Files/write fuel-two-path
                   ^bytes (component-core/emit
                           kir :wasm32-wasi-kotoba-v1 {:fuel 2})
                   (make-array java.nio.file.OpenOption 0))
      (is (= :structural-union-match-module (:canonical-lowering artifact)))
      (is (= :module-global (:fuel-enforcement artifact)))
      (is (empty? (:required-imports artifact)))
      (is (= #{'choose-option 'choose-result 'negate}
             (set (:exports artifact))))
      (doseq [[invoke expected export args]
              [["choose-option(none, 9)" "9" 'choose-option
                [[[:option :i64] false] 9]]
               ["choose-option(some(7), 9)" "14" 'choose-option
                [[[:option :i64] true 7] 9]]
               ["choose-result(ok(true))" "1" 'choose-result [[true true]]]
               ["choose-result(err(-1.5))"
                (str (value/f32-to-i64-bits (float -1.5)))
                'choose-result [[false (float -1.5)]]]
               ["negate(false)" "true" 'negate [false]]]]
        (let [run (shell/sh wasmtime-binary "run" "--invoke" invoke
                            (str component-path))]
          (is (zero? (:exit run)) (:err run))
          (is (= expected (str/trim (:out run))) invoke)
          (is (= expected (str (ir/execute kir export args))) invoke)))
      (let [fuel-one
            (shell/sh wasmtime-binary "run" "--invoke" "cm32p2||choose-option"
                      (str fuel-one-path) "1" "7" "0")
            fuel-two
            (shell/sh wasmtime-binary "run" "--invoke" "cm32p2||choose-option"
                      (str fuel-two-path) "1" "7" "0")
            active-f32
            (shell/sh wasmtime-binary "run" "--invoke" "cm32p2||choose-result"
                      (str fuel-two-path) "1" "2")
            active-bool
            (shell/sh wasmtime-binary "run" "--invoke" "cm32p2||choose-result"
                      (str fuel-two-path) "0" "2")
            ordinary-bool
            (shell/sh wasmtime-binary "run" "--invoke" "cm32p2||negate"
                      (str fuel-two-path) "2")]
        (is (not (zero? (:exit fuel-one)))
            "the match and its private helper share the module fuel global")
        (is (zero? (:exit fuel-two)) (:err fuel-two))
        (is (= "14" (str/trim (:out fuel-two))))
        (is (zero? (:exit active-f32)) (:err active-f32))
        (is (= "2" (str/trim (:out active-f32)))
            "joined payload validation is scoped to this export's selected case")
        (is (not (zero? (:exit active-bool)))
            "the same joined bits trap in this export's bool case")
        (is (not (zero? (:exit ordinary-bool)))
            "another export's ordinary bool parameter remains entry-validated"))
      (finally
        (Files/deleteIfExists component-path)
        (Files/deleteIfExists fuel-one-path)
        (Files/deleteIfExists fuel-two-path)))))

(deftest structural-union-match-is-lazy-and-rejects-malformed-tags
  (let [source "(ns component.lazy-match (:export [choose]))
                (defn choose
                  [value [:option :i64] fallback :i64] :i64
                  (match-option value [:option :i64]
                    (none fallback)
                    (some item (quot 1 0))))"
        artifact (compiler/compile-component source)
        kir (:kir (compiler/compile-source source :wasm32-wasi-kotoba-v1))
        core (component-core/emit kir :wasm32-wasi-kotoba-v1)
        dir (Files/createTempDirectory
             "kotoba-component-lazy-union-match-" (make-array FileAttribute 0))
        component-path (.resolve dir "lazy.component.wasm")
        core-path (.resolve dir "lazy.core.wasm")]
    (try
      (Files/write component-path ^bytes (:bytes artifact)
                   (make-array java.nio.file.OpenOption 0))
      (Files/write core-path ^bytes core
                   (make-array java.nio.file.OpenOption 0))
      (let [inactive (shell/sh wasmtime-binary "run" "--invoke"
                               "choose(none, 41)" (str component-path))
            active (shell/sh wasmtime-binary "run" "--invoke"
                             "choose(some(7), 41)" (str component-path))
            malformed (shell/sh wasmtime-binary "run" "--invoke"
                                "cm32p2||choose" (str core-path) "2" "0" "41")]
        (is (zero? (:exit inactive)) (:err inactive))
        (is (= "41" (str/trim (:out inactive))))
        (is (not (zero? (:exit active)))
            "the selected branch executes and traps")
        (is (not (zero? (:exit malformed)))
            "a tag outside the two-case union traps before branch dispatch"))
      (finally
        (Files/deleteIfExists component-path)
        (Files/deleteIfExists core-path)
        (Files/deleteIfExists dir))))
  (let [descriptor [:option :i64]
        malformed {:format :kotoba.kir/v4 :exports ['choose] :schemas {} :effects #{}
                   :functions [{:name 'choose :params ['value]
                                :param-types [descriptor] :result :i64
                                :body (list 'option-match descriptor 'value 0)}]}]
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"no qualified Canonical lowering"
         (component/assert-scalar-slice! malformed (wit/emit malformed))))))

(deftest named-scalar-record-identity-is-admitted
  (let [descriptor [:ref :demo/point]
        kir {:format :kotoba.kir/v4 :exports ['echo] :effects #{}
             :schemas {:demo/point
                       [:record :demo/point
                        [[:x :i64] [:weight :f64] [:visible :bool]]]}
             :functions [{:name 'echo :params ['value] :param-types [descriptor]
                          :result descriptor :body 'value}]}]
    (is (true? (component/assert-scalar-slice! kir (wit/emit kir))))
    ;; A field outside the admitted flat-leaf type set (i64/f32/f64/bool/
    ;; string/keyword) remains fail-closed. Before ADR 0053, this assertion
    ;; used `:string` here; as of ADR 0053 a `:string` field is admitted (via
    ;; the dedicated `:string-field-record-identity` path, not this scalar
    ;; path -- see `string-and-keyword-field-record-identity-is-admitted`),
    ;; so a genuinely still-unadmitted field type (`[:vector :i64]`) is
    ;; needed to keep testing "an out-of-set field type is rejected".
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"no qualified Canonical lowering"
                          (component/assert-scalar-slice!
                           (assoc-in kir [:schemas :demo/point 2 0 1] [:vector :i64])
                           (wit/emit kir))))))

(deftest one-level-nested-scalar-record-identity-is-admitted
  (let [descriptor [:ref :demo/outer]
        schemas {:demo/inner [:record :demo/inner [[:code :i64] [:ratio :f64]]]
                 :demo/outer [:record :demo/outer
                              [[:id :i64] [:inner [:ref :demo/inner]] [:active :bool]]]}
        kir {:format :kotoba.kir/v4 :exports ['echo] :effects #{}
             :schemas schemas
             :functions [{:name 'echo :params ['value] :param-types [descriptor]
                          :result descriptor :body 'value}]}]
    (is (true? (component/assert-scalar-slice! kir (wit/emit kir))))
    (let [artifact (component/package
                    (component-core/emit kir :wasm32-wasi-kotoba-v1)
                    kir (wit/emit kir))]
      (is (= :nested-record-identity (:canonical-lowering artifact)))
      (is (= :wasm-component/v1 (:format artifact)))
      (is (= [0 97 115 109 13 0 1 0]
             (mapv #(bit-and (int %) 0xff) (take 8 (:bytes artifact))))))
    ;; Two levels of nesting remain fail-closed: a nested field's own field
    ;; may not itself be a nested record.
    (let [two-level-schemas
          (assoc schemas
                 :demo/middle [:record :demo/middle [[:leaf [:ref :demo/inner]]]]
                 :demo/deep [:record :demo/deep [[:mid [:ref :demo/middle]]]])
          deep-kir (-> kir
                      (assoc :schemas two-level-schemas)
                      (assoc-in [:functions 0 :param-types] [[:ref :demo/deep]])
                      (assoc-in [:functions 0 :result] [:ref :demo/deep]))]
      (is (thrown-with-msg? clojure.lang.ExceptionInfo #"no qualified Canonical lowering"
                            (component/assert-scalar-slice! deep-kir (wit/emit deep-kir)))))
    ;; A nested field with a non-scalar (string) leaf remains fail-closed.
    (let [string-leaf-schemas
          {:demo/inner-str [:record :demo/inner-str [[:label :string]]]
           :demo/outer-str [:record :demo/outer-str
                            [[:id :i64] [:inner [:ref :demo/inner-str]]]]}
          string-kir (-> kir
                        (assoc :schemas string-leaf-schemas)
                        (assoc-in [:functions 0 :param-types] [[:ref :demo/outer-str]])
                        (assoc-in [:functions 0 :result] [:ref :demo/outer-str]))]
      (is (thrown-with-msg? clojure.lang.ExceptionInfo #"no qualified Canonical lowering"
                            (component/assert-scalar-slice! string-kir (wit/emit string-kir)))))
    ;; A nested field descriptor whose sealed schema identity has drifted
    ;; remains fail-closed.
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"no qualified Canonical lowering"
                          (component/assert-scalar-slice!
                           (assoc-in kir [:schemas :demo/inner 1] :demo/renamed)
                           (wit/emit kir))))))

(deftest variant-with-record-and-scalar-cases-identity-is-admitted
  (let [descriptor [:ref :demo/outcome]
        schemas {:demo/entry [:record :demo/entry
                              [[:code :i64] [:ratio :f64] [:present :bool]]]
                 :demo/short [:record :demo/short [[:code :i64] [:flag :bool]]]
                 :demo/outcome [:variant :demo/outcome
                                [[:found [:ref :demo/entry]]
                                 [:missing :bool]
                                 [:failed :f32]
                                 [:short [:ref :demo/short]]]]}
        kir {:format :kotoba.kir/v4 :exports ['echo] :effects #{}
             :schemas schemas
             :functions [{:name 'echo :params ['value] :param-types [descriptor]
                          :result descriptor :body 'value}]}]
    (is (true? (component/assert-scalar-slice! kir (wit/emit kir))))
    (let [artifact (component/package
                    (component-core/emit kir :wasm32-wasi-kotoba-v1)
                    kir (wit/emit kir))]
      (is (= :variant-identity (:canonical-lowering artifact)))
      (is (= :wasm-component/v1 (:format artifact)))
      (is (= [0 97 115 109 13 0 1 0]
             (mapv #(bit-and (int %) 0xff) (take 8 (:bytes artifact))))))
    ;; A case wrapping a record with a field outside the admitted set
    ;; entirely remains fail-closed. Before ADR 0054, this assertion used a
    ;; case wrapping a record with a `:string` field; as of ADR 0054 that
    ;; shape is admitted (via the dedicated `:variant-identity` path with a
    ;; string/keyword-bearing case -- see
    ;; `variant-with-string-keyword-record-and-scalar-cases-identity-is-
    ;; admitted`), so a genuinely still-unsupported field type
    ;; (`[:vector :i64]`) is needed to keep testing "an out-of-set case
    ;; payload shape is rejected", mirroring ADR 0053's own regression-test
    ;; update to `named-scalar-record-identity-is-admitted`.
    (let [vector-case-schemas
          {:demo/label [:record :demo/label [[:tags [:vector :i64]]]]
           :demo/status [:variant :demo/status
                         [[:ready :bool] [:labeled [:ref :demo/label]]]]}
          vector-kir (-> kir
                        (assoc :schemas vector-case-schemas)
                        (assoc-in [:functions 0 :param-types] [[:ref :demo/status]])
                        (assoc-in [:functions 0 :result] [:ref :demo/status]))]
      ;; `wit/emit` is called on the original, still-valid `kir` here (not
      ;; `vector-kir`) because `component-wit/type-text` has no rendering
      ;; for a bare `[:vector :i64]` field type at all (it only recognizes
      ;; `[:vector [<types>...]]` as a WIT tuple) and would throw its own,
      ;; unrelated exception before `assert-scalar-slice!` ever runs;
      ;; `assert-qualified-slice!` only consults `wit` for its
      ;; already-empty `:imports`, so the stale WIT does not affect what
      ;; this assertion actually checks. Mirrors the identical `(wit/emit
      ;; kir)` substitution in `named-scalar-record-identity-is-admitted`'s
      ;; own `[:vector :i64]` regression case.
      (is (thrown-with-msg? clojure.lang.ExceptionInfo #"no qualified Canonical lowering"
                            (component/assert-scalar-slice! vector-kir (wit/emit kir)))))
    ;; A case wrapping a record that is itself one level nested (the ADR
    ;; 0051 shape) remains fail-closed: a variant case payload is bounded to
    ;; the flat ADR 0043 record shape only in this slice.
    (let [nested-case-schemas
          {:demo/inner [:record :demo/inner [[:code :i64]]]
           :demo/wrapper [:record :demo/wrapper [[:inner [:ref :demo/inner]]]]
           :demo/status [:variant :demo/status
                         [[:ready :bool] [:wrapped [:ref :demo/wrapper]]]]}
          nested-kir (-> kir
                        (assoc :schemas nested-case-schemas)
                        (assoc-in [:functions 0 :param-types] [[:ref :demo/status]])
                        (assoc-in [:functions 0 :result] [:ref :demo/status]))]
      (is (thrown-with-msg? clojure.lang.ExceptionInfo #"no qualified Canonical lowering"
                            (component/assert-scalar-slice! nested-kir (wit/emit nested-kir)))))
    ;; A case wrapping another variant remains fail-closed: only scalars and
    ;; sealed all-scalar records are admitted case payloads in this slice.
    (let [variant-case-schemas
          {:demo/inner-variant [:variant :demo/inner-variant [[:a :bool]]]
           :demo/status [:variant :demo/status
                         [[:ready :bool] [:nested [:ref :demo/inner-variant]]]]}
          variant-case-kir (-> kir
                               (assoc :schemas variant-case-schemas)
                               (assoc-in [:functions 0 :param-types] [[:ref :demo/status]])
                               (assoc-in [:functions 0 :result] [:ref :demo/status]))]
      (is (thrown-with-msg? clojure.lang.ExceptionInfo #"no qualified Canonical lowering"
                            (component/assert-scalar-slice! variant-case-kir
                                                            (wit/emit variant-case-kir)))))
    ;; A case schema whose sealed identity has drifted remains fail-closed.
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"no qualified Canonical lowering"
                          (component/assert-scalar-slice!
                           (assoc-in kir [:schemas :demo/entry 1] :demo/renamed)
                           (wit/emit kir))))
    ;; A computed variant body (anything other than a bare parameter
    ;; passthrough) remains fail-closed.
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"no qualified Canonical lowering"
                          (component/assert-scalar-slice!
                           (assoc-in kir [:functions 0 :body] '(record-get schemas value :found))
                           (wit/emit kir))))))

(deftest variant-with-only-bool-and-f32-cases-identity-is-admitted
  ;; Dedicated to the Component Model spec's other join outcome (the
  ;; i32/f32 special case): neither case ever touches i64/f64, so the
  ;; shared payload position stays i32 instead of widening to i64, and the
  ;; f32 case needs the single-instruction `f32.reinterpret_i32` coercion
  ;; that the record-and-scalar-cases test above never exercises (every
  ;; payload position there is i64-dominated).
  (let [descriptor [:ref :demo/flag-or-ratio]
        schemas {:demo/flag-or-ratio [:variant :demo/flag-or-ratio
                                      [[:urgent :bool] [:weight :f32]]]}
        kir {:format :kotoba.kir/v4 :exports ['echo] :effects #{}
             :schemas schemas
             :functions [{:name 'echo :params ['value] :param-types [descriptor]
                          :result descriptor :body 'value}]}]
    (is (true? (component/assert-scalar-slice! kir (wit/emit kir))))
    (let [artifact (component/package
                    (component-core/emit kir :wasm32-wasi-kotoba-v1)
                    kir (wit/emit kir))]
      (is (= :variant-identity (:canonical-lowering artifact)))
      (is (= :wasm-component/v1 (:format artifact))))))

(deftest variant-with-string-keyword-record-and-scalar-cases-identity-is-admitted
  ;; `demo/state-result` is structurally a slice of `state-v1.edn`'s actual
  ;; `:result` type: `demo/entry` is exactly `state-v1`'s own `entry` record
  ;; (`key: keyword, value: string, version: i64`), and `:found`/`:missing`
  ;; are two of `state-v1`'s own five cases. ADR 0052 admitted a variant case
  ;; wrapping a sealed all-scalar record; ADR 0053 admitted a record with
  ;; string/keyword fields, but only as a *top-level* export, never as a
  ;; variant case payload. ADR 0054 is the first slice to admit a variant
  ;; case wrapping a string/keyword-bearing record, which this test exercises
  ;; concretely for the first time.
  (let [entry-schema [:record :demo/entry [[:key :keyword] [:value :string] [:version :i64]]]
        descriptor [:ref :demo/state-result]
        schemas {:demo/entry entry-schema
                 :demo/state-result [:variant :demo/state-result
                                     [[:found [:ref :demo/entry]] [:missing :bool]]]}
        kir {:format :kotoba.kir/v4 :exports ['echo] :effects #{}
             :schemas schemas
             :functions [{:name 'echo :params ['value] :param-types [descriptor]
                          :result descriptor :body 'value}]}]
    (is (true? (component/assert-scalar-slice! kir (wit/emit kir))))
    (let [artifact (component/package
                    (component-core/emit kir :wasm32-wasi-kotoba-v1)
                    kir (wit/emit kir))]
      (is (= :variant-identity (:canonical-lowering artifact)))
      (is (= :wasm-component/v1 (:format artifact)))
      (is (= [0 97 115 109 13 0 1 0]
             (mapv #(bit-and (int %) 0xff) (take 8 (:bytes artifact))))))
    ;; A case whose own string/keyword field exceeds its bound remains a
    ;; schema-admission concern only at the layout level, not here -- the
    ;; runtime trap is exercised manually under Wasmtime (see ADR 0054); at
    ;; the admission level, a case record with a field outside the whole
    ;; admitted set (i64/f32/f64/bool/string/keyword) still fails closed.
    (let [out-of-set-schemas
          {:demo/entry [:record :demo/entry [[:key :keyword] [:tags [:vector :i64]]]]
           :demo/state-result [:variant :demo/state-result
                               [[:found [:ref :demo/entry]] [:missing :bool]]]}
          out-of-set-kir (-> kir (assoc :schemas out-of-set-schemas))]
      ;; `wit/emit` uses the original `kir` here, not `out-of-set-kir`, for
      ;; the same `[:vector :i64]`-has-no-WIT-rendering reason documented in
      ;; `variant-with-record-and-scalar-cases-identity-is-admitted`.
      (is (thrown-with-msg? clojure.lang.ExceptionInfo #"no qualified Canonical lowering"
                            (component/assert-scalar-slice! out-of-set-kir
                                                            (wit/emit kir)))))))

(deftest variant-with-scalar-and-both-record-kinds-mixed-in-one-case-set-is-admitted
  ;; Beyond the state-v1 slice above: a single variant may freely mix all
  ;; three admitted case-payload kinds -- a bare scalar, a sealed all-scalar
  ;; record (ADR 0052), and a sealed string/keyword-bearing record (ADR
  ;; 0054) -- with no requirement that every record case be the same kind.
  (let [entry-schema [:record :demo/mixed-entry
                      [[:key :keyword] [:value :string] [:version :i64]]]
        tally-schema [:record :demo/mixed-tally [[:count :i64] [:ok :bool]]]
        descriptor [:ref :demo/mixed-outcome]
        schemas {:demo/mixed-entry entry-schema
                 :demo/mixed-tally tally-schema
                 :demo/mixed-outcome [:variant :demo/mixed-outcome
                                      [[:found [:ref :demo/mixed-entry]]
                                       [:tally [:ref :demo/mixed-tally]]
                                       [:missing :bool]]]}
        kir {:format :kotoba.kir/v4 :exports ['echo] :effects #{}
             :schemas schemas
             :functions [{:name 'echo :params ['value] :param-types [descriptor]
                          :result descriptor :body 'value}]}]
    (is (true? (component/assert-scalar-slice! kir (wit/emit kir))))
    (let [artifact (component/package
                    (component-core/emit kir :wasm32-wasi-kotoba-v1)
                    kir (wit/emit kir))]
      (is (= :variant-identity (:canonical-lowering artifact)))
      (is (= :wasm-component/v1 (:format artifact))))))

(deftest variant-capability-call-with-scalar-or-record-cases-is-admitted
  ;; ADR 0055: a direct `typed-cap-call` may now use one sealed variant
  ;; (bare-scalar cases only) as its same-identity request/result, the first
  ;; slice to cross a *structured* (multi-case) type through a capability
  ;; boundary rather than a single bare scalar (ADR 0046) or a flat record
  ;; (ADR 0048). `demo/flag-or-ratio` is the exact ADR 0052 bool/f32
  ;; join-table fixture, reused here crossing a capability boundary for the
  ;; first time.
  (let [descriptor [:ref :demo/flag-or-ratio]
        schemas {:demo/flag-or-ratio [:variant :demo/flag-or-ratio
                                      [[:urgent :bool] [:weight :f32]]]}
        kir {:format :kotoba.kir/v4 :exports ['invoke] :schemas schemas
             :functions [{:name 'invoke :params ['request]
                          :param-types [descriptor] :result descriptor
                          :body (list 'typed-cap-call 8 descriptor descriptor 'request)}]}]
    (is (true? (component/assert-scalar-slice! kir (wit/emit kir))))
    (let [artifact (component/package
                    (component-core/emit kir :wasm32-wasi-kotoba-v1)
                    kir (wit/emit kir))]
      (is (= :variant-capability-call (:canonical-lowering artifact)))
      (is (= [:state/transact] (:imports artifact)))
      (is (= :wasm-component/v1 (:format artifact)))
      (is (= [0 97 115 109 13 0 1 0]
             (mapv #(bit-and (int %) 0xff) (take 8 (:bytes artifact))))))
    ;; ADR 0056: a case wrapping a sealed all-scalar record (the ADR 0052
    ;; shape) is now admitted for a capability-call boundary too -- ADR 0055
    ;; found this blocked at the `wac plug` layer (`type not valid to be
    ;; used as import`); `wac` 0.10.0 fixes exactly that failure mode
    ;; (bytecodealliance/wac#205). `demo/cap-outcome` is the same fixture ADR
    ;; 0055 recorded as blocked, now proven admitted at the KIR-admission
    ;; layer this test exercises (`component_composition_test.clj` proves
    ;; the same shape through a real composed component and Wasmtime
    ;; execution).
    (let [record-case-schemas
          {:demo/cap-tally [:record :demo/cap-tally [[:count :i64]]]
           :demo/cap-outcome [:variant :demo/cap-outcome
                              [[:tally [:ref :demo/cap-tally]] [:empty :bool]]]}
          record-case-kir (-> kir
                              (assoc :schemas record-case-schemas)
                              (assoc-in [:functions 0 :param-types] [[:ref :demo/cap-outcome]])
                              (assoc-in [:functions 0 :result] [:ref :demo/cap-outcome])
                              (assoc-in [:functions 0 :body]
                                        (list 'typed-cap-call 8 [:ref :demo/cap-outcome]
                                              [:ref :demo/cap-outcome] 'request)))]
      (is (true? (component/assert-scalar-slice! record-case-kir (wit/emit record-case-kir))))
      (let [record-case-artifact (component/package
                                  (component-core/emit record-case-kir :wasm32-wasi-kotoba-v1)
                                  record-case-kir (wit/emit record-case-kir))]
        (is (= :variant-capability-call (:canonical-lowering record-case-artifact)))
        (is (= :wasm-component/v1 (:format record-case-artifact)))))
    ;; ADR 0057: a case wrapping a sealed *string/keyword-bearing* record
    ;; (the ADR 0053 shape) is now admitted for a capability-call boundary
    ;; too -- ADR 0056 only widened admission to the all-scalar record case;
    ;; string/keyword data crossing a capability-call boundary at all was a
    ;; separate, unattempted gap both ADR 0055 and ADR 0056 named as
    ;; remaining. `demo/cap-entry` is exactly `state-v1`'s own real `entry`
    ;; shape (`key: keyword, value: string, version: i64`).
    ;; `component_composition_test.clj` proves the same shape through a real
    ;; composed component and Wasmtime execution.
    (let [string-case-schemas
          {:demo/cap-entry [:record :demo/cap-entry
                            [[:key :keyword] [:value :string] [:version :i64]]]
           :demo/cap-string-outcome [:variant :demo/cap-string-outcome
                                     [[:found [:ref :demo/cap-entry]] [:missing :bool]]]}
          string-case-kir (-> kir
                              (assoc :schemas string-case-schemas)
                              (assoc-in [:functions 0 :param-types] [[:ref :demo/cap-string-outcome]])
                              (assoc-in [:functions 0 :result] [:ref :demo/cap-string-outcome])
                              (assoc-in [:functions 0 :body]
                                        (list 'typed-cap-call 8 [:ref :demo/cap-string-outcome]
                                              [:ref :demo/cap-string-outcome] 'request)))]
      (is (true? (component/assert-scalar-slice! string-case-kir (wit/emit string-case-kir))))
      (let [string-case-artifact (component/package
                                  (component-core/emit string-case-kir :wasm32-wasi-kotoba-v1)
                                  string-case-kir (wit/emit string-case-kir))]
        (is (= :variant-capability-call (:canonical-lowering string-case-artifact)))
        (is (= :wasm-component/v1 (:format string-case-artifact)))))
    ;; A case wrapping an ADR 0051 one-level-nested record (a field whose own
    ;; type is itself a sealed record, rather than a scalar or string/
    ;; keyword leaf) remains fail-closed: `variant-capability-case?` only
    ;; admits a bare scalar, a sealed all-scalar record, or a sealed flat
    ;; string/keyword-bearing record as a case payload, never one level
    ;; deeper.
    (let [nested-case-schemas
          {:demo/cap-inner [:record :demo/cap-inner [[:count :i64]]]
           :demo/cap-nested-entry [:record :demo/cap-nested-entry
                                   [[:inner [:ref :demo/cap-inner]] [:label :string]]]
           :demo/cap-nested-outcome [:variant :demo/cap-nested-outcome
                                     [[:found [:ref :demo/cap-nested-entry]] [:missing :bool]]]}
          nested-case-kir (-> kir
                              (assoc :schemas nested-case-schemas)
                              (assoc-in [:functions 0 :param-types] [[:ref :demo/cap-nested-outcome]])
                              (assoc-in [:functions 0 :result] [:ref :demo/cap-nested-outcome])
                              (assoc-in [:functions 0 :body]
                                        (list 'typed-cap-call 8 [:ref :demo/cap-nested-outcome]
                                              [:ref :demo/cap-nested-outcome] 'request)))]
      (is (thrown-with-msg? clojure.lang.ExceptionInfo #"no qualified Canonical lowering"
                            (component/assert-scalar-slice! nested-case-kir
                                                            (wit/emit nested-case-kir)))))
    ;; A bare `:string`/`:keyword` case payload (not wrapped in a record)
    ;; remains fail-closed -- only a record *field* carries string/keyword
    ;; data across this boundary in this slice.
    (let [bare-string-case-schemas
          {:demo/cap-label-outcome [:variant :demo/cap-label-outcome
                                    [[:label :string] [:missing :bool]]]}
          bare-string-case-kir (-> kir
                                   (assoc :schemas bare-string-case-schemas)
                                   (assoc-in [:functions 0 :param-types]
                                             [[:ref :demo/cap-label-outcome]])
                                   (assoc-in [:functions 0 :result] [:ref :demo/cap-label-outcome])
                                   (assoc-in [:functions 0 :body]
                                             (list 'typed-cap-call 8 [:ref :demo/cap-label-outcome]
                                                   [:ref :demo/cap-label-outcome] 'request)))]
      (is (thrown-with-msg? clojure.lang.ExceptionInfo #"no qualified Canonical lowering"
                            (component/assert-scalar-slice! bare-string-case-kir
                                                            (wit/emit bare-string-case-kir)))))
    ;; ADR 0058: different request/result variant identities are now
    ;; admitted, provided each independently satisfies the narrower
    ;; scalar-or-sealed-all-scalar-record case-kind set
    ;; (`asymmetric-variant-capability-schema` -- ADR 0055/0056's own
    ;; case-kind union, deliberately not widened to ADR 0057's string/
    ;; keyword-bearing record case in this same increment). `demo/flag-or-
    ;; ratio` (bool/f32, request) crossing to `demo/other-outcome` (bare
    ;; bool, result) -- a genuinely different, genuinely smaller variant --
    ;; is the first shape in this ADR chain ever admitted with request-type
    ;; != result-type.
    (let [other-schemas
          {:demo/flag-or-ratio [:variant :demo/flag-or-ratio
                                [[:urgent :bool] [:weight :f32]]]
           :demo/other-outcome [:variant :demo/other-outcome [[:urgent :bool]]]}
          different-identity-kir
          (-> kir
             (assoc :schemas other-schemas)
             (assoc-in [:functions 0 :result] [:ref :demo/other-outcome])
             (assoc-in [:functions 0 :body]
                       (list 'typed-cap-call 8 descriptor [:ref :demo/other-outcome] 'request)))]
      (is (true? (component/assert-scalar-slice! different-identity-kir
                                                  (wit/emit different-identity-kir))))
      (let [different-identity-artifact
            (component/package
             (component-core/emit different-identity-kir :wasm32-wasi-kotoba-v1)
             different-identity-kir (wit/emit different-identity-kir))]
        (is (= :different-variant-capability-call
               (:canonical-lowering different-identity-artifact)))
        (is (= :wasm-component/v1 (:format different-identity-artifact)))))
    ;; ADR 0058 also admits a case wrapping a sealed all-scalar record (the
    ;; ADR 0052 shape) on either side of a different-identity crossing, not
    ;; only a bare scalar -- `demo/cap-outcome` (`tally: cap-tally`/`empty:
    ;; bool`, request) crossing to `demo/other-record-outcome`
    ;; (`total: cap-total`, result), two different record-cased variants.
    (let [record-other-schemas
          {:demo/cap-tally [:record :demo/cap-tally [[:count :i64]]]
           :demo/cap-outcome [:variant :demo/cap-outcome
                              [[:tally [:ref :demo/cap-tally]] [:empty :bool]]]
           :demo/cap-total [:record :demo/cap-total [[:sum :i64] [:ok :bool]]]
           :demo/other-record-outcome [:variant :demo/other-record-outcome
                                       [[:total [:ref :demo/cap-total]]]]}
          record-different-identity-kir
          (-> kir
             (assoc :schemas record-other-schemas)
             (assoc-in [:functions 0 :param-types] [[:ref :demo/cap-outcome]])
             (assoc-in [:functions 0 :result] [:ref :demo/other-record-outcome])
             (assoc-in [:functions 0 :body]
                       (list 'typed-cap-call 8 [:ref :demo/cap-outcome]
                             [:ref :demo/other-record-outcome] 'request)))]
      (is (true? (component/assert-scalar-slice! record-different-identity-kir
                                                  (wit/emit record-different-identity-kir))))
      (let [record-different-identity-artifact
            (component/package
             (component-core/emit record-different-identity-kir :wasm32-wasi-kotoba-v1)
             record-different-identity-kir (wit/emit record-different-identity-kir))]
        (is (= :different-variant-capability-call
               (:canonical-lowering record-different-identity-artifact)))
        (is (= :wasm-component/v1 (:format record-different-identity-artifact)))))
    ;; ADR 0059: a different-identity crossing where one side's case wraps a
    ;; sealed *string/keyword-bearing* record (the ADR 0053/0057 shape) is
    ;; now admitted too -- ADR 0058 deliberately left this combination
    ;; unattempted (`asymmetric-variant-capability-schema` was narrower than
    ;; `variant-capability-schema`, the same-identity path); ADR 0059 closes
    ;; exactly that gap. `demo/cap-string-outcome` (`found: cap-entry`/
    ;; `missing: bool`, `cap-entry` = `state-v1`'s own real `entry` shape)
    ;; crossing to `demo/other-outcome` (bare bool) is the smallest such
    ;; shape; `component_composition_test.clj` proves this (and
    ;; `state-v1`'s own literal shape) through a real composed component
    ;; and Wasmtime execution.
    (let [string-other-schemas
          {:demo/cap-entry [:record :demo/cap-entry
                            [[:key :keyword] [:value :string] [:version :i64]]]
           :demo/cap-string-outcome [:variant :demo/cap-string-outcome
                                     [[:found [:ref :demo/cap-entry]] [:missing :bool]]]
           :demo/other-outcome [:variant :demo/other-outcome [[:urgent :bool]]]}
          string-different-identity-kir
          (-> kir
             (assoc :schemas string-other-schemas)
             (assoc-in [:functions 0 :param-types] [[:ref :demo/cap-string-outcome]])
             (assoc-in [:functions 0 :result] [:ref :demo/other-outcome])
             (assoc-in [:functions 0 :body]
                       (list 'typed-cap-call 8 [:ref :demo/cap-string-outcome]
                             [:ref :demo/other-outcome] 'request)))]
      (is (true? (component/assert-scalar-slice! string-different-identity-kir
                                                  (wit/emit string-different-identity-kir))))
      (let [string-different-identity-artifact
            (component/package
             (component-core/emit string-different-identity-kir :wasm32-wasi-kotoba-v1)
             string-different-identity-kir (wit/emit string-different-identity-kir))]
        (is (= :different-variant-capability-call
               (:canonical-lowering string-different-identity-artifact)))
        (is (= :wasm-component/v1 (:format string-different-identity-artifact)))))
    ;; A different-identity crossing where one side's case wraps an ADR 0051
    ;; one-level-nested record remains fail-closed too, for the same reason
    ;; it remains fail-closed on the same-identity path.
    (let [nested-other-schemas
          {:demo/cap-inner [:record :demo/cap-inner [[:count :i64]]]
           :demo/cap-nested-entry [:record :demo/cap-nested-entry
                                   [[:inner [:ref :demo/cap-inner]] [:label :string]]]
           :demo/cap-nested-outcome [:variant :demo/cap-nested-outcome
                                     [[:found [:ref :demo/cap-nested-entry]] [:missing :bool]]]
           :demo/other-outcome [:variant :demo/other-outcome [[:urgent :bool]]]}
          nested-different-identity-kir
          (-> kir
             (assoc :schemas nested-other-schemas)
             (assoc-in [:functions 0 :param-types] [[:ref :demo/cap-nested-outcome]])
             (assoc-in [:functions 0 :result] [:ref :demo/other-outcome])
             (assoc-in [:functions 0 :body]
                       (list 'typed-cap-call 8 [:ref :demo/cap-nested-outcome]
                             [:ref :demo/other-outcome] 'request)))]
      (is (thrown-with-msg? clojure.lang.ExceptionInfo #"no qualified Canonical lowering"
                            (component/assert-scalar-slice! nested-different-identity-kir
                                                            (wit/emit nested-different-identity-kir)))))
    ;; A computed capability request (anything other than a bare parameter
    ;; passthrough) remains fail-closed.
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"no qualified Canonical lowering"
                          (component/assert-scalar-slice!
                           (assoc-in kir [:functions 0 :body]
                                     (list 'typed-cap-call 8 descriptor descriptor
                                           (list 'typed-cap-call 8 descriptor descriptor 'request)))
                           (wit/emit kir))))
    ;; An unknown capability id remains fail-closed.
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"no qualified Canonical lowering"
                          (component/assert-scalar-slice!
                           (assoc-in kir [:functions 0 :body]
                                     (list 'typed-cap-call 999999 descriptor descriptor 'request))
                           (wit/emit
                            (assoc-in kir [:functions 0 :body]
                                      (list 'typed-cap-call 8 descriptor descriptor 'request))))))))

(deftest string-and-keyword-field-record-identity-is-admitted
  ;; `demo/state-entry` mirrors `state-v1.edn`'s actual `entry` record
  ;; shape (`key: keyword, value: string, version: i64`) -- the concrete
  ;; motivating target ADR 0051's own remaining gaps named.
  (let [descriptor [:ref :demo/state-entry]
        schema [:record :demo/state-entry
                [[:key :keyword] [:value :string] [:version :i64]]]
        schemas {:demo/state-entry schema}
        kir {:format :kotoba.kir/v4 :exports ['echo] :effects #{}
             :schemas schemas
             :functions [{:name 'echo :params ['value] :param-types [descriptor]
                          :result descriptor :body 'value}]}]
    (is (true? (component/assert-scalar-slice! kir (wit/emit kir))))
    (let [artifact (component/package
                    (component-core/emit kir :wasm32-wasi-kotoba-v1)
                    kir (wit/emit kir))]
      (is (= :string-field-record-identity (:canonical-lowering artifact)))
      (is (= :wasm-component/v1 (:format artifact)))
      (is (= [0 97 115 109 13 0 1 0]
             (mapv #(bit-and (int %) 0xff) (take 8 (:bytes artifact))))))
    ;; A record with a bare string field but no scalar field at all remains
    ;; admitted too -- the identity path does not require a scalar leaf,
    ;; only "no field outside i64/f32/f64/bool/string/keyword".
    (let [label-schema [:record :demo/label [[:text :string]]]
          label-kir (-> kir
                       (assoc :schemas {:demo/label label-schema})
                       (assoc-in [:functions 0 :param-types] [[:ref :demo/label]])
                       (assoc-in [:functions 0 :result] [:ref :demo/label]))]
      (is (true? (component/assert-scalar-slice! label-kir (wit/emit label-kir))))
      (let [artifact (component/package
                      (component-core/emit label-kir :wasm32-wasi-kotoba-v1)
                      label-kir (wit/emit label-kir))]
        (is (= :string-field-record-identity (:canonical-lowering artifact)))))
    ;; A field that is itself a nested record (the ADR 0051 shape) remains
    ;; fail-closed: string/keyword leaves are only admitted at the top
    ;; level in this slice, never inside a nested field.
    (let [nested-schemas
          {:demo/inner [:record :demo/inner [[:text :string]]]
           :demo/wrapper [:record :demo/wrapper
                          [[:key :keyword] [:inner [:ref :demo/inner]]]]}
          nested-kir (-> kir
                        (assoc :schemas nested-schemas)
                        (assoc-in [:functions 0 :param-types] [[:ref :demo/wrapper]])
                        (assoc-in [:functions 0 :result] [:ref :demo/wrapper]))]
      (is (thrown-with-msg? clojure.lang.ExceptionInfo #"no qualified Canonical lowering"
                            (component/assert-scalar-slice! nested-kir (wit/emit nested-kir)))))
    ;; A record schema whose sealed identity has drifted remains fail-closed.
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"no qualified Canonical lowering"
                          (component/assert-scalar-slice!
                           (assoc-in kir [:schemas :demo/state-entry 1] :demo/renamed)
                           (wit/emit kir))))
    ;; A computed body (anything other than a bare parameter passthrough)
    ;; remains fail-closed.
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"no qualified Canonical lowering"
                          (component/assert-scalar-slice!
                           (assoc-in kir [:functions 0 :body]
                                     (list 'record-get schema 'value :key))
                           (wit/emit kir))))))

(deftest named-scalar-record-field-projection-is-admitted
  (let [schema [:record :demo/point
                [[:x :i64] [:weight :f64] [:visible :bool]]]
        descriptor [:ref :demo/point]
        kir {:format :kotoba.kir/v4 :exports ['weight] :effects #{}
             :schemas {:demo/point schema}
             :functions [{:name 'weight :params ['value] :param-types [descriptor]
                          :result :f64 :body (list 'record-get schema 'value :weight)}]}]
    (is (true? (component/assert-scalar-slice! kir (wit/emit kir))))
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"no qualified Canonical lowering"
                          (component/assert-scalar-slice!
                           (assoc-in kir [:functions 0 :body]
                                     (list 'record-get schema 'value :missing))
                           (wit/emit kir))))))

(deftest scalar-record-construction-and-update-are-admitted
  (let [schema [:record :demo/point [[:x :i64] [:weight :f64] [:visible :bool]]]
        base {:format :kotoba.kir/v4 :exports ['make] :effects #{}
              :schemas {:demo/point schema}}
        construction
        (assoc base :functions
               [{:name 'make :params ['x 'weight 'visible]
                 :param-types [:i64 :f64 :bool] :result schema
                 :body (list 'record-new schema 'x 'weight 'visible)}])
        update
        (assoc base :exports ['set-weight]
               :functions
               [{:name 'set-weight :params ['point 'weight]
                 :param-types [schema :f64] :result schema
                 :body (list 'record-assoc schema 'point :weight 'weight)}])]
    (is (true? (component/assert-scalar-slice! construction (wit/emit construction))))
    (is (true? (component/assert-scalar-slice! update (wit/emit update))))
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"no qualified Canonical lowering"
                          (component/assert-scalar-slice!
                           (assoc-in update [:functions 0 :body]
                                     (list 'record-assoc schema 'point :weight 1))
                           (wit/emit update))))))

(defn- binary-text [bytes]
  (String. ^bytes bytes java.nio.charset.StandardCharsets/ISO_8859_1))

(deftest standard32-core-names-are-explicit-and-target-local
  (let [standard32 (binary-text
                    (wasm/emit-component-core scalar-kir :wasm32-wasi-kotoba-v1))
        ordinary (binary-text (wasm/emit scalar-kir :wasm32-wasi-kotoba-v1))]
    (doseq [name ["cm32p2||add" "cm32p2||add_post" "cm32p2_memory"
                  "cm32p2_realloc" "cm32p2_initialize"]]
      (is (str/includes? standard32 name)))
    (is (str/includes? ordinary "add"))
    (is (not (str/includes? ordinary "cm32p2||add")))))
