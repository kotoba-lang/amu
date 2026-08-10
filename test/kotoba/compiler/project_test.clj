(ns kotoba.compiler.project-test
  (:require [clojure.string :as str]
            [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]
            [kotoba.compiler.frontend :as frontend]
            [kotoba.kir :as ir]
            [kotoba.compiler.project :as project]))

(def text-source
  "(ns example.text (:export [greet]))
   (defn- prefix [name :string] :string (string-concat \"こんにちは、\" name))
   (defn greet [name :string] :string (prefix name))")

(def app-source
  "(ns example.app
     (:require [example.text :as text])
     (:export [welcome]))
   (defn welcome [name :string] :string (text/greet name))")

(deftest closed-project-links-exported-functions
  (let [{:keys [source module-order modules]}
        (project/link-source {'example.app app-source 'example.text text-source} 'example.app)
        compiled (compiler/compile-source source :js-kotoba-v1)]
    (is (= ['example.text 'example.app] module-order))
    (is (= #{'example.text 'example.app} modules))
    (is (= "こんにちは、言葉" (ir/execute (:kir compiled) 'welcome ["言葉"])))
    (is (= ['welcome] (get-in compiled [:kir :exports])))
    (is (not-any? #{'greet 'prefix} (get-in compiled [:kir :exports])))))

(deftest compile-project-component-target-multi-file
  "T8.3: compile-project accepts component target (link → compile-component)."
  (let [lib "(ns example.lib (:export [answer])) (defn answer [] :i64 42)"
        app "(ns example.root (:require [example.lib :as lib]) (:export [main]))
             (defn main [] :i64 (lib/answer))"
        compiled (compiler/compile-project
                  {'example.lib lib 'example.root app}
                  'example.root :wasm-component-kotoba-v1)]
    (is (= :wasm-component/v1 (:format compiled)))
    (is (= :scalar (:canonical-lowering compiled)))
    (is (= ['example.lib 'example.root] (get-in compiled [:project :kotoba.module/order])))
    (is (bytes? (:bytes compiled)))
    (is (pos? (alength ^bytes (:bytes compiled))))))

(deftest compile-project-component-admits-linked-or-synthetics
  "T8.3: linked monomorph re-emits desugared `or` as __kotoba_or_*; second
  frontend pass must admit those synthetics (user source still cannot invent them)."
  (let [lib "(ns example.bounds (:export [in-range?]))
             (defn in-range? [n :i64] :i64
               (if (or (< n 0) (> n 999)) 0 1))"
        app "(ns example.root (:require [example.bounds :as b]) (:export [main]))
             (defn main [] :i64 (b/in-range? 42))"
        compiled (compiler/compile-project
                  {'example.bounds lib 'example.root app}
                  'example.root :wasm-component-kotoba-v1)]
    (is (= :wasm-component/v1 (:format compiled)))
    (is (pos? (alength ^bytes (:bytes compiled)))))
  (is (thrown-with-msg? clojure.lang.ExceptionInfo
                        #"reserved __kotoba_ prefix"
                        (compiler/compile-component
                         "(ns u (:export [main])) (defn main [] :i64 (let [__kotoba_or_1 1] __kotoba_or_1))"
                         {}))))

(deftest project-stubs-preserve-typed-boolean-export-signatures
  (let [provider
        "(ns example.coverage (:export [covered?]))
         (defn covered? [covered [:set :keyword] item :keyword] :bool
           (typed-set-contains [:set :keyword] covered item))"
        consumer
        "(ns example.check
           (:require [example.coverage :as coverage])
           (:export [ready? pending?]))
         (defn ready? [] :bool
           (coverage/covered? (typed-set [:set :keyword] :ready) :ready))
         (defn pending? [] :bool
           (coverage/covered? (typed-set [:set :keyword] :ready) :pending))"
        compiled (compiler/compile-project
                  {'example.coverage provider 'example.check consumer}
                  'example.check :js-kotoba-v1)]
    (is (true? (ir/execute (:kir compiled) 'ready? [])))
    (is (false? (ir/execute (:kir compiled) 'pending? [])))))

(deftest project-stubs-preserve-structured-export-results
  (let [person-type "[:record :example/person [[:name :string] [:age :i64]]]"
        provider (str "(ns example.person (:export [make]))"
                      "(defn make [name :string age :i64] " person-type
                      " (record " person-type " name age))")
        consumer (str "(ns example.age (:require [example.person :as person])"
                      " (:export [age]))"
                      "(defn age [] :i64 (record-get " person-type
                      " (person/make \"Kotoba\" 7) :age))")
        compiled (compiler/compile-project
                  {'example.person provider 'example.age consumer}
                  'example.age :js-kotoba-v1)]
    (is (= 7 (ir/execute (:kir compiled) 'age [])))))

(deftest project-interfaces-preserve-public-callable-contracts
  (let [provider
        "(ns example.callables (:export [apply-one make-renderer make-document]))
         (defn apply-one [f [:fn [[:i64] :i64]] x :i64] :i64 (f x))
         (defn make-renderer [] [:fn [[:i64] :string]]
           (fn [x] (string-from-i64 x)))
         (defn make-document [] [:fn [[] :document]]
           (fn [] (document-vector (document-i64 1))))"
        consumer
        "(ns example.use-callables
           (:require [example.callables :as callables])
           (:export [main]))
         (defn main []
           (+ (+ (callables/apply-one (fn [x] (+ x 1)) 4)
                 (string-length
                  (let [render (callables/make-renderer)] (render 42))))
              (document-count
               (let [build (callables/make-document)] (build)))))"
        linked (project/link-source
                {'example.callables provider 'example.use-callables consumer}
                'example.use-callables)
        compiled (compiler/compile-project
                  {'example.callables provider 'example.use-callables consumer}
                  'example.use-callables :js-kotoba-v1)]
    (is (str/includes? (:source linked) "[:fn [[:i64] :i64]]"))
    (is (str/includes? (:source linked) "[:fn [[:i64] :string]]"))
    (is (str/includes? (:source linked) "[:fn [[] :document]]"))
    (is (= 8 (ir/execute (:kir compiled) 'main [])))))

(deftest project-stubs-cover-scalar-f64-and-f32-export-results
  ;; Regression for kotoba-lang/amu#206 Bug 2: a cross-file :require of a
  ;; function whose declared result type is scalar :f64 (or :f32) failed at
  ;; :project-link with "project import result type has no closed stub value"
  ;; -- project/stub-value had :vector-f64 but no :f64 / :f32 case. Only the
  ;; import-boundary stub is exercised here, which is exactly what was missing.
  (let [provider (str "(ns example.num (:export [scale narrow]))"
                      "(defn scale [x :f64] :f64 (f64-mul x 2.0))"
                      "(defn narrow [x :f64] :f32 (f64-to-f32-rounded x))")
        consumer (str "(ns example.use (:require [example.num :as num])"
                      " (:export [doubled ratio]))"
                      "(defn doubled [] :f64 (num/scale 3.0))"
                      "(defn ratio [] :bool (f32-unordered (num/narrow 2.0)"
                      " (f32-from-bits 0)))")
        compiled (compiler/compile-project
                  {'example.num provider 'example.use consumer}
                  'example.use :js-kotoba-v1)]
    (is (= ['doubled 'ratio] (get-in compiled [:kir :exports])))))

(deftest project-linking-keeps-nested-option-match-type-descriptors-idempotent
  (let [person "[:record :example/person [[:name :string] [:age :i64]]]"
        option (str "[:option " person "]")
        provider (str "(ns example.provider (:export [none-person]))"
                      "(defn none-person [] " option
                      " (option-none-of " option "))")
        consumer (str
                  "(ns example.consumer (:require [example.provider :as provider])"
                  " (:export [main]))"
                  "(defn choose [left " option " right " option "] " option
                  " (match-option left " option
                  "  (none right)"
                  "  (some left-person"
                  "   (match-option right " option
                  "    (none left)"
                  "    (some right-person right)))))"
                  "(defn main [] :i64"
                  " (record-get " person
                  "  (option-value-of " option
                  "   (choose (provider/none-person)"
                  "    (option-some-of " option
                  "     (record " person " \"Kotoba\" 42)))"
                  "   (record " person " \"fallback\" 0)) :age))")
        compiled (compiler/compile-project
                  {'example.provider provider 'example.consumer consumer}
                  'example.consumer :js-kotoba-v1)]
    (is (= 42 (ir/execute (:kir compiled) 'main [])))))

(deftest project-modules-admit-the-same-bounded-namespace-docstrings
  (let [dependency (str/replace text-source "(ns example.text"
                                "(ns example.text \"bounded project documentation\"")
        linked (project/link-source {'example.app app-source 'example.text dependency}
                                    'example.app)]
    (is (= ['example.text 'example.app] (:module-order linked))))
  (is (thrown-with-msg?
       clojure.lang.ExceptionInfo #"namespace docstring exceeds admission limit"
       (project/link-source
        {'example.text
         (str "(ns example.text "
              (pr-str (apply str (repeat (inc frontend/max-namespace-docstring-chars) "x")))
              " (:export [greet])) (defn greet [] 0)")}
        'example.text))))

(deftest project-linking-is-deterministic
  (let [a (project/link-source (array-map 'example.app app-source
                                           'example.text text-source)
                               'example.app)
        b (project/link-source (array-map 'example.text text-source
                                           'example.app app-source)
                               'example.app)]
    (is (= a b))))

(deftest compiler-seals-the-closed-module-graph
  (let [sources {'example.app app-source 'example.text text-source}
        a (compiler/compile-project sources 'example.app :js-kotoba-v1)
        b (compiler/compile-project (into (array-map) (reverse sources))
                                    'example.app :js-kotoba-v1)
        changed (compiler/compile-project
                 (assoc sources 'example.text (str/replace text-source "こんにちは" "こんばんは"))
                 'example.app :js-kotoba-v1)]
    (is (= (:project-digest a) (:project-digest b)))
    (is (= (:project-digest a)
           (get-in a [:manifest :kotoba.artifact/module-graph-digest])))
    (is (= ['example.text 'example.app]
           (get-in a [:project :kotoba.module/order])))
    (is (= #{'example.text 'example.app}
           (set (keys (get-in a [:manifest :kotoba.artifact/module-source-digests])))))
    (is (str/includes? (:source a)
                       (str "moduleGraphDigest:\"" (:project-digest a) "\"")))
    (is (str/includes? (:source a) "moduleSourceDigests:Object.freeze"))
    (is (str/includes? (:source a) "\"example.app\""))
    (is (str/includes? (:source a) "\"example.text\""))
    (is (not= (:project-digest a)
              (:project-digest changed)))
    (is (not= (get-in a [:manifest :kotoba.artifact/output-digest])
              (get-in changed [:manifest :kotoba.artifact/output-digest])))))

(deftest compiler-seals-verified-supply-chain-identity
  (let [digest (fn [character] (apply str (repeat 64 character)))
        supply-chain {:package-lock-digest (digest "a")
                      :trust-policy-digest (digest "b")
                      :package-receipt-digest (digest "c")}
        compiled (compiler/compile-project
                  {'sealed.app "(ns sealed.app (:export [answer])) (defn answer [] 42)"}
                  'sealed.app :js-kotoba-v1 {} supply-chain)]
    (is (= (digest "a")
           (get-in compiled [:manifest :kotoba.artifact/package-lock-digest])))
    (is (= (digest "b")
           (get-in compiled [:manifest :kotoba.artifact/trust-policy-digest])))
    (is (= (digest "c")
           (get-in compiled [:manifest :kotoba.artifact/package-receipt-digest])))
    (is (str/includes? (:source compiled)
                       (str "packageLockDigest:\"" (digest "a") "\"")))
    (is (thrown-with-msg? clojure.lang.ExceptionInfo
                          #"invalid verified supply-chain identity"
                          (compiler/compile-project
                           {'sealed.app "(ns sealed.app (:export [answer])) (defn answer [] 42)"}
                           'sealed.app :js-kotoba-v1 {}
                           {:package-lock-digest (digest "a")})))))

(deftest project-imports-fail-closed
  (testing "missing source"
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"outside the closed project"
                          (project/link-source {'example.app app-source} 'example.app))))
  (testing "private function"
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"not an admitted exported import"
                          (project/link-source
                           {'example.text text-source
                            'example.app (str/replace app-source "text/greet" "text/prefix")}
                           'example.app))))
  (testing "cycle"
    (let [a "(ns cycle.a (:require [cycle.b :as b]) (:export [a])) (defn a [] (b/b))"
          b "(ns cycle.b (:require [cycle.a :as a]) (:export [b])) (defn b [] (a/a))"]
      (is (thrown-with-msg? clojure.lang.ExceptionInfo #"cyclic module dependency"
                            (project/link-source {'cycle.a a 'cycle.b b} 'cycle.a)))))
  (testing "non alias import"
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"imports require"
                          (project/link-source
                           {'example.app (str/replace app-source
                                                      "[example.text :as text]"
                                                      "[example.text :refer [greet]]")
                            'example.text text-source}
                           'example.app)))))

(defn- dependency-project [count all-previous?]
  (into {}
        (map (fn [index]
               (let [module (symbol (str "bounds.m" index))
                     dependencies (if all-previous?
                                    (range index)
                                    (when (pos? index) [(dec index)]))
                     specs (mapv (fn [dependency]
                                   [(symbol (str "bounds.m" dependency))
                                    :as (symbol (str "m" dependency))])
                                 dependencies)]
                 [module
                  (str (pr-str (list 'ns module
                                     (list* :require specs)
                                     (list :export ['value])))
                       "\n(defn value [] 0)")]))
        (range count))))

(deftest project-wide-resource-bounds-fail-before-linking
  (testing "aggregate source bytes"
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"source bytes exceed"
                          (project/link-source
                           {'large.module
                            (apply str (repeat (inc project/max-project-source-bytes) "x"))}
                           'large.module))))
  (testing "dependency depth"
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"dependency depth exceeds"
                          (project/link-source (dependency-project 66 false)
                                               'bounds.m65))))
  (testing "dependency edge count"
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"dependency edges exceed"
                          (project/link-source (dependency-project 24 true)
                                               'bounds.m23))))
  (testing "aggregate expression nodes"
    (let [body (apply str (repeat 100000 "(f) "))
          source (fn [namespace]
                   (str "(ns " namespace " (:export [f])) "
                        "(defn f [] (do " body "0))"))]
      (is (thrown-with-msg? clojure.lang.ExceptionInfo #"expression nodes exceed"
                            (project/link-source
                             {'bounds.expr-a (source 'bounds.expr-a)
                              'bounds.expr-b (source 'bounds.expr-b)}
                             'bounds.expr-a)))))
  (testing "aggregate literal count"
    (let [body (apply str (repeat 33000 "0 "))
          source (fn [namespace]
                   (str "(ns " namespace " (:export [f])) "
                        "(defn f [] (do " body "0))"))]
      (is (thrown-with-msg? clojure.lang.ExceptionInfo #"project literals exceed"
                            (project/link-source
                             {'bounds.literal-a (source 'bounds.literal-a)
                              'bounds.literal-b (source 'bounds.literal-b)}
                             'bounds.literal-a)))))
  (testing "aggregate string literal bytes"
    (let [literal (pr-str (apply str (repeat 4096 "x")))
          body (str/join " " (repeat 15 literal))
          sources (into {}
                        (map (fn [index]
                               (let [namespace (symbol (str "bounds.str" index))]
                                 [namespace
                                  (str "(ns " namespace " (:export [f])) "
                                       "(defn f [] (do " body "))")]))
                        (range 18)))]
      (is (thrown-with-msg? clojure.lang.ExceptionInfo #"string literal bytes exceed"
                            (project/link-source sources 'bounds.str0))))))

(deftest capability-effects-close-across-module-boundaries
  (let [sources
        {'effects.leaf
         "(ns effects.leaf (:export [read]))
          (defn- hidden-audit [value] (cap-call 9 value))
          (defn read [value] (cap-call 7 value))"
         'effects.middle
         "(ns effects.middle (:require [effects.leaf :as leaf]) (:export [forward]))
          (defn forward [value] (leaf/read value))"
         'effects.root
         "(ns effects.root (:require [effects.middle :as middle]) (:export [run]))
          (defn run [value] (middle/forward value))"}]
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"denies required effects"
                          (compiler/compile-project sources 'effects.root :js-kotoba-v1)))
    (let [compiled (compiler/compile-project
                    sources 'effects.root :js-kotoba-v1
                    {:allow #{[:cap/call 7] [:cap/call 9] [:cap/call 10]}})]
      (is (= #{[:cap/call 7] [:cap/call 9]}
             (get-in compiled [:admission :required])))
      (is (= #{[:cap/call 10]} (get-in compiled [:admission :unused-grants])))
      (is (= #{[:cap/call 7] [:cap/call 9]} (get-in compiled [:kir :effects])))
      (is (str/includes? (:source compiled)
                         "requiredCapabilities:Object.freeze([7,9])")))))

(deftest changed-exports-and-dependency-substitution-fail-or-reseal
  (let [root "(ns substitution.root
                (:require [substitution.dep :as dep])
                (:export [run]))
              (defn run [] (dep/value))"
        dependency "(ns substitution.dep (:export [value])) (defn value [] 41)"
        sources {'substitution.root root 'substitution.dep dependency}
        original (compiler/compile-project sources 'substitution.root :js-kotoba-v1)
        substituted (compiler/compile-project
                     (assoc sources 'substitution.dep
                            "(ns substitution.dep (:export [value])) (defn value [] 42)")
                     'substitution.root :js-kotoba-v1)]
    (testing "changing an imported export fails before backend emission"
      (is (thrown-with-msg?
           clojure.lang.ExceptionInfo #"not an admitted exported import"
           (compiler/compile-project
            (assoc sources 'substitution.dep
                   "(ns substitution.dep (:export [replacement]))
                    (defn replacement [] 41)")
            'substitution.root :js-kotoba-v1))))
    (testing "same-interface dependency bytes produce a distinct sealed artifact"
      (is (not= (:project-digest original) (:project-digest substituted)))
      (is (not= (get-in original [:manifest :kotoba.artifact/module-source-digests])
                (get-in substituted [:manifest :kotoba.artifact/module-source-digests])))
      (is (not= (get-in original [:manifest :kotoba.artifact/output-digest])
                (get-in substituted [:manifest :kotoba.artifact/output-digest]))))))

;; --- ns :capabilities inside a project ------------------------------------
;; Before this, a project module could declare `:export` and alias-only
;; `:require` and nothing else, while a SINGLE-module compile had accepted
;; `:capabilities` since ADR-2607182410. The two paths disagreeing meant a
;; program could be multi-module or effectful, never both -- which put every
;; effectful application outside project mode.

(def commit-source
  "(ns caps.render
     (:capabilities #{:ui/commit})
     (:export [commit-tree]))
   (defn commit-tree [revision :i64] :i64 (cap-call :ui/commit revision))")

(def poll-source
  "(ns caps.events
     (:capabilities #{:ui/next-event})
     (:export [poll]))
   (defn poll [after :i64] :i64 (cap-call :ui/next-event after))")

(def caps-app-source
  "(ns caps.app
     (:require [caps.render :as render] [caps.events :as events])
     (:export [main]))
   (defn main [] :i64 (events/poll (render/commit-tree 0)))")

(def caps-sources
  {'caps.render commit-source 'caps.events poll-source 'caps.app caps-app-source})

(deftest project-modules-admit-a-declared-capability-set
  (let [{:keys [source]} (project/link-source caps-sources 'caps.app)
        compiled (compiler/compile-source source :js-kotoba-v1
                                          {:allow #{[:cap/call 9] [:cap/call 10]}})]
    (testing "each module keeps its own declaration"
      (is (= #{:ui/commit} (:capabilities (project/module-info (frontend/read-forms commit-source)))))
      (is (= #{:ui/next-event} (:capabilities (project/module-info (frontend/read-forms poll-source)))))
      ;; nil, not #{}: the app module writes no clause at all, and the
      ;; frontend distinguishes "no declaration to check" from "declares that
      ;; it uses nothing".
      (is (nil? (:capabilities (project/module-info (frontend/read-forms caps-app-source))))))
    (testing "the linked namespace carries no :capabilities clause"
      ;; Bodies reach the linked unit already lowered to integer cap-calls,
      ;; which populate no used-keyword set; re-declaring the union would fail
      ;; the frontend's own declare-then-check.
      (is (str/includes? source "(cap-call 9 "))
      (is (str/includes? source "(cap-call 10 "))
      (is (not (str/includes? source ":capabilities"))))
    (testing "effects still reach the artifact through the integer form"
      (is (= 77 (ir/execute (:kir compiled) 'main []
                            {:cap-call (fn [id value]
                                         (case (long id)
                                           9 7
                                           10 (* 11 value)))}))))))

(deftest project-capability-declarations-fail-closed
  (testing "declared but never used is still rejected per module"
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"never used via cap-call"
         (project/link-source
          (assoc caps-sources 'caps.render
                 (str/replace commit-source "#{:ui/commit}" "#{:ui/commit :ui/next-event}"))
          'caps.app))))
  (testing "used but never declared is still rejected per module"
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"not declared in namespace :capabilities"
         (project/link-source
          (assoc caps-sources 'caps.render
                 (str/replace commit-source "#{:ui/commit}" "#{:ui/next-event}"))
          'caps.app))))
  (testing "the policy, not the clause, is what actually gates an effect"
    ;; `:capabilities` is an optional per-module lint -- a module that writes
    ;; no clause may still name a cap-call, exactly as in single-module mode.
    ;; What stops it is admission against the compile policy, so a project
    ;; cannot gain an effect by simply omitting the declaration.
    (let [undeclared (str/replace caps-app-source
                                  "(defn main [] :i64 (events/poll (render/commit-tree 0)))"
                                  "(defn main [] :i64 (cap-call :ui/commit 0))")
          sources (assoc caps-sources 'caps.app undeclared)
          {:keys [source]} (project/link-source sources 'caps.app)]
      (is (str/includes? source "(cap-call 9 "))
      (is (thrown-with-msg?
           clojure.lang.ExceptionInfo #"policy denies"
           (compiler/compile-source source :js-kotoba-v1 {:allow #{}})))))
  (testing ":capabilities must be a set of namespaced keywords"
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"bounded set of namespaced keywords"
         (project/link-source
          (assoc caps-sources 'caps.render
                 (str/replace commit-source "#{:ui/commit}" "#{:commit}"))
          'caps.app))))
  (testing "at most one :capabilities clause"
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"are admitted"
         (project/link-source
          (assoc caps-sources 'caps.render
                 (str/replace commit-source
                              "(:capabilities #{:ui/commit})"
                              "(:capabilities #{:ui/commit}) (:capabilities #{:ui/commit})"))
          'caps.app))))
  (testing ":schemas remains rejected in project mode rather than silently dropped"
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"are admitted"
         (project/link-source
          (assoc caps-sources 'caps.render
                 (str/replace commit-source
                              "(:capabilities #{:ui/commit})"
                              "(:capabilities #{:ui/commit}) (:schemas {})"))
          'caps.app)))))
