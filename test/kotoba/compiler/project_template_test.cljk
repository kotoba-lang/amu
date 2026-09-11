(ns kotoba.compiler.project-template-test
  "Template modules: `(:params [elem])` in a library's `ns`, `:with {elem T}`
  in the importer's require spec, instantiated by the linker per binding
  (superproject ADR adr-2609113100, option C). The frontend is unchanged and
  never sees a parameter symbol.

  Every refusal here is asserted by its MESSAGE. The failures are easy to
  confuse -- each one ends in a module that did not link -- and a control that
  only checks for a throw counts a run that died for another reason."
  (:require [clojure.java.shell :as shell]
            [clojure.set :as set]
            [clojure.test :refer [deftest is testing]]
            [kotoba.lang.text :as str]
            [kotoba.compiler.core :as compiler]
            [kotoba.compiler.definition-identity :as definition-identity]
            [kotoba.compiler.diagnostic :as diagnostic]
            [kotoba.compiler.project :as project]
            [kotoba.kir :as ir]
            [kotoba.sema :as sema]))

;; The program from the ADR, verbatim: one template, two instantiations, and a
;; `main` that answers 5 (|{1 2} ∪ {2 3}| + |{x} ∪ {y}|).
(def union-template
  "(ns kotoba.set.union
  (:params [elem])
  (:export [union]))
(defn union [s1 [:set elem] s2 [:set elem]] [:set elem]
  (loop [i 0 acc s1]
    (if (< i (typed-set-count [:set elem] s2))
      (recur (+ i 1) (typed-set-conj [:set elem] acc (typed-set-nth [:set elem] s2 i)))
      acc)))")

(def root-source
  "(ns root
  (:require [kotoba.set.union :as ui :with {elem :i64}]
            [kotoba.set.union :as us :with {elem :symbol}])
  (:export [main]))
(defn main [] :i64
  (+ (typed-set-count [:set :i64] (ui/union (typed-set-new [:set :i64] 1 2) (typed-set-new [:set :i64] 2 3)))
     (typed-set-count [:set :symbol] (us/union (typed-set-new [:set :symbol] (symbol \"x\")) (typed-set-new [:set :symbol] (symbol \"y\"))))))")

(def sources {'kotoba.set.union union-template 'root root-source})

;; The same two instantiations written out BY HAND, which is what was measured
;; before templates existed: link ok, distinct CIDs, main -> 5.
(defn- hand-written [namespace type]
  (-> union-template
      (str/replace "kotoba.set.union" (str namespace))
      (str/replace "\n  (:params [elem])" "")
      (str/replace "elem" (str type))))

(def hand-sources
  {'kotoba.set.union-i64 (hand-written 'kotoba.set.union-i64 :i64)
   'kotoba.set.union-symbol (hand-written 'kotoba.set.union-symbol :symbol)
   'root (-> root-source
             (str/replace "[kotoba.set.union :as ui :with {elem :i64}]" "[kotoba.set.union-i64 :as ui]")
             (str/replace "[kotoba.set.union :as us :with {elem :symbol}]" "[kotoba.set.union-symbol :as us]"))})

(defn- definition-cids
  "Function name -> CID for a linked project, through the same report
  `amu definition-cids` prints."
  [sources root]
  (let [linked (project/link-source sources root)
        hir (sema/analyze (:source linked) {:admit-linked-synthetics? true})
        report (definition-identity/describe {:hir hir :kir (ir/lower hir)})]
    (is (map? (:entries report)) (pr-str (:reason report)))
    (into {} (map (fn [[name entry]] [name (:cid entry)])) (:entries report))))

(defn- module-cids
  "The CIDs of the functions the linker emitted for the module at INDEX in
  the module order -- `kotoba_module__<index>__<j>` -- as a set."
  [cids index]
  (into #{} (keep (fn [[name cid]]
                    (when (str/starts-with? name (str "kotoba_module__" index "__")) cid)))
        cids))

(defn- execute
  "Link PROJECT at ROOT and run EXPORT through the KIR interpreter. (Not the
  restricted-ESM backend: that one has no lowering for typed sets, which is a
  fact about that backend and not about linking.)"
  [project root export args]
  (let [linked (project/link-source project root)
        hir (sema/analyze (:source linked) {:admit-linked-synthetics? true})]
    (ir/execute (ir/lower hir) export args)))

(defn- rejection
  "The message of the refusal THUNK raises, or a description of its absence."
  [thunk]
  (try (thunk) "no refusal was raised"
       (catch clojure.lang.ExceptionInfo error (ex-message error))))

;; ---------------------------------------------------------------------------
;; 1. The program links, and main answers 5 -- in KIR and on wasm32-browser
;;    through runtime/browser-host.mjs, which is what a browser runs.

(deftest template-instantiates-per-binding-and-runs-to-five
  (let [{:keys [module-order modules]} (project/link-source sources 'root)]
    (is (= [['kotoba.set.union {'elem :i64}] ['kotoba.set.union {'elem :symbol}] 'root]
           module-order)
        "one module per distinct binding, keyed by namespace and binding")
    (is (= 3 (count modules))))
  (is (= 5 (execute sources 'root 'main [])) "in the KIR interpreter")
  (let [artifact (compiler/compile-project sources 'root :wasm32-browser-kotoba-v1)
        encoded (.encodeToString (java.util.Base64/getEncoder) (:bytes artifact))
        result (shell/sh "node" "--input-type=module" "-e"
                         (str "import('./runtime/browser-host.mjs').then(async m=>{"
                              "const h=await m.instantiateKotoba(Buffer.from('" encoded "','base64'));"
                              "process.stdout.write(String(h.instance.exports.main()));})"))]
    (is (= 0 (:exit result)) (:err result))
    (is (= "5" (:out result)) "main on wasm32-browser, through the browser host")))

;; ---------------------------------------------------------------------------
;; 2. Identity: the two instantiations are two definitions; the alias is not
;;    part of either; the same binding twice is one module.

(deftest instantiations-have-distinct-cids-that-do-not-depend-on-the-alias
  (let [cids (definition-cids sources 'root)
        i64-cids (module-cids cids 0)
        symbol-cids (module-cids cids 1)]
    (is (= 2 (count i64-cids)) "union and its loop helper")
    (is (= 2 (count symbol-cids)))
    (is (empty? (set/intersection i64-cids symbol-cids))
        "the two instantiations share no definition CID")
    (testing "renaming both aliases changes no CID"
      (let [renamed (update sources 'root #(-> % (str/replace ":as ui" ":as a")
                                                (str/replace ":as us" ":as b")
                                                (str/replace "ui/union" "a/union")
                                                (str/replace "us/union" "b/union")))]
        (is (= cids (definition-cids renamed 'root)))))
    (testing "the template instantiated by hand is the same definition"
      (is (= cids (definition-cids hand-sources 'root))))))

(deftest two-importers-of-one-binding-share-one-instantiation
  (let [mid "(ns mid (:require [kotoba.set.union :as b :with {elem :i64}]) (:export [two]))
(defn two [] :i64 (typed-set-count [:set :i64] (b/union (typed-set-new [:set :i64] 1) (typed-set-new [:set :i64] 2))))"
        root "(ns root (:require [kotoba.set.union :as a :with {elem :i64}] [mid :as m]) (:export [main]))
(defn main [] :i64 (+ (m/two) (typed-set-count [:set :i64] (a/union (typed-set-new [:set :i64] 1 2) (typed-set-new [:set :i64] 2 3)))))"
        project {'kotoba.set.union union-template 'mid mid 'root root}
        {:keys [module-order]} (project/link-source project 'root)]
    (is (= [['kotoba.set.union {'elem :i64}] 'mid 'root] module-order)
        "the binding is reached from two importers and linked once")
    (is (= 5 (execute project 'root 'main [])))
    (is (= (module-cids (definition-cids sources 'root) 0)
           (module-cids (definition-cids project 'root) 0))
        "and it is the same definition as when one importer binds it")))

;; ---------------------------------------------------------------------------
;; 3. Fail closed in both directions, each by name.

(deftest template-reached-without-a-binding-is-refused-by-name
  (testing "as a project dependency without :with"
    (is (= "template module kotoba.set.union declares (:params [elem]) and needs an instantiation: require it with :with {elem <type>}"
           (rejection #(project/link-source
                        (assoc sources 'root (str/replace root-source " :with {elem :i64}" ""))
                        'root)))))
  (testing "as the root"
    (is (= "template module kotoba.set.union declares (:params [elem]) and needs an instantiation: require it with :with {elem <type>}"
           (rejection #(project/link-source sources 'kotoba.set.union)))))
  (testing "as a single file, on the frontend path"
    (let [error (try (compiler/check-source union-template) nil
                     (catch clojure.lang.ExceptionInfo error error))
          refined (diagnostic/refine error)]
      (is (some? error) "the frontend does not admit a (:params ...) clause")
      (is (= :kotoba.error/namespace-params-needs-instantiation (:code refined)))
      (is (str/starts-with? (:message refined)
                            "template module declares (:params [elem]) and needs an instantiation: require it with :with {elem <type>}")
          (:message refined)))))

(deftest binding-shapes-are-refused-by-name
  (testing ":with on a module that declares no :params"
    (is (= "module plain declares no (:params ...) but is required with :with {elem :i64}"
           (rejection #(project/link-source
                        {'plain "(ns plain (:export [one])) (defn one [] :i64 1)"
                         'root "(ns root (:require [plain :as p :with {elem :i64}]) (:export [main])) (defn main [] :i64 (p/one))"}
                        'root)))))
  (testing ":with naming a parameter the template does not declare"
    (is (= "template module kotoba.set.union is required with :with {elem :i64, foo :i64}, which names parameter(s) it does not declare: [foo]"
           (rejection #(project/link-source
                        (assoc sources 'root (str/replace root-source "{elem :i64}" "{elem :i64 foo :i64}"))
                        'root)))))
  (testing ":with missing a declared parameter"
    (let [two-params (str/replace union-template "(:params [elem])" "(:params [elem other])")]
      (is (= "template module kotoba.set.union is required with :with {elem :i64}, which does not bind its parameter(s) [other]"
             (rejection #(project/link-source (assoc sources 'kotoba.set.union two-params) 'root))))))
  (testing ":with binding a parameter to a value rather than a type"
    (is (= "import :with binds a parameter to something that is not a type form"
           (rejection #(project/module-info
                        (sema/read-forms "(ns root (:require [kotoba.set.union :as u :with {elem 42}]) (:export [main]))"))))))
  (testing ":params that are not simple symbols, or repeat"
    (doseq [params ["[a/b]" "[elem elem]" "[]" "[\"elem\"]"]]
      (is (= "namespace :params must be a non-empty vector of distinct simple symbols"
             (rejection #(project/module-info
                          (sema/read-forms (str "(ns t (:params " params ") (:export [f]))")))))
          params)))
  (testing ":params beyond the bound"
    (is (= "namespace :params exceed the template parameter limit"
           (rejection #(project/module-info
                        (sema/read-forms (str "(ns t (:params [" (str/join " " (map (fn [i] (str "p" i)) (range 9)))
                                              "]) (:export [f]))"))))))
    (is (= 8 project/max-template-parameters))))

(deftest a-parameter-symbol-used-as-a-name-is-refused
  ;; `[elem]` in a parameter vector would mean "an i64 named elem" in a module
  ;; whose header says elem is a type. Refused rather than guessed.
  (is (= "template parameter is used as a parameter name; a parameter symbol may only stand in a type position"
         (rejection #(project/link-source
                      {'t "(ns t (:params [elem]) (:export [f])) (defn f [elem] :i64 elem)"
                       'root "(ns root (:require [t :as t :with {elem :i64}]) (:export [main])) (defn main [] :i64 (t/f 1))"}
                      'root))))
  ;; And a parameter in a VALUE position that is not a bound local never
  ;; reaches the frontend as an unbound variable in a synthetic text.
  (is (str/starts-with?
       (rejection #(project/link-source
                    {'t "(ns t (:params [elem]) (:export [f])) (defn f [x elem] elem (+ x elem))"
                     'root "(ns root (:require [t :as t :with {elem :i64}]) (:export [main])) (defn main [] :i64 (t/f 1))"}
                    'root))
       "template parameter elem reaches the frontend unsubstituted")))

;; ---------------------------------------------------------------------------
;; 4. Substitution reaches type positions only: a LOCAL named elem is a local.

(deftest a-local-named-like-a-parameter-is-not-substituted
  (let [template "(ns t.local (:params [elem]) (:export [f]))
(defn f [x elem] elem (let [elem 7] (+ x elem)))"
        root "(ns root (:require [t.local :as t :with {elem :i64}]) (:export [main]))
(defn main [] :i64 (t/f 1))"
        project {'t.local template 'root root}
        forms (project/instantiate-forms (sema/read-forms template) {'elem :i64} 't.local)]
    (is (= '(defn f [x :i64] :i64 (let [elem 7] (+ x elem))) (second forms))
        "the parameter and result slots are :i64; the let-bound elem is untouched")
    (is (= 8 (execute project 'root 'main [])))))

;; ---------------------------------------------------------------------------
;; 5. A refusal inside an instantiation says which one.

(deftest a-refusal-inside-an-instantiation-names-the-binding
  (let [template "(ns t.plus (:params [elem]) (:export [plus]))
(defn plus [a elem b elem] elem (+ a b))"
        root "(ns root (:require [t.plus :as pi :with {elem :i64}] [t.plus :as ps :with {elem :string}]) (:export [main]))
(defn main [] :i64 (pi/plus 1 2))"
        error (try (project/link-source {'t.plus template 'root root} 'root) nil
                   (catch clojure.lang.ExceptionInfo error error))
        data (ex-data error)]
    (is (some? error) "+ on :string is refused under one binding and not the other")
    (is (str/ends-with? (ex-message error) " in t.plus with {elem :string}") (ex-message error))
    (is (= 't.plus (:source-module data)))
    (is (= {'elem :string} (:source-binding data)))
    (is (= 2 (get-in data [:span :line])) "the defn line in the template's own source"))
  (testing "and the source map carries the binding of every instantiated function"
    (let [{:keys [source-map]} (project/link-source sources 'root)
          bindings (into #{} (map (juxt :module :binding)) (:entries source-map))]
      (is (= #{['kotoba.set.union {'elem :i64}] ['kotoba.set.union {'elem :symbol}] ['root nil]}
             bindings)))))

;; ---------------------------------------------------------------------------
;; 6. Byte identity for projects without templates. These CIDs were captured
;;    on origin/main b57284d6, before templates existed, with
;;    `amu definition-cids root.kotoba --source-path .` on the hand-written
;;    project above. A project that declares no `:params` and no `:with` must
;;    link to the same definitions it linked to before.

(def cids-before-templates
  {"kotoba_module__0__0" "bafyreigplqb6xyzpt4gkw7drhvuf74ta3xy35j74rsktk6sklmh4wdyexq"
   "kotoba_module__0__1" "bafyreicw2bizu3ns43b5mjnpxw4zdyozi2nhpb3krd75j3gqhjoovovcmu"
   "kotoba_module__1__0" "bafyreihomhcef4yz2hcnxkarhtzj7qlevkgdixgex6xxadq42pq6mmuuvy"
   "kotoba_module__1__1" "bafyreihwv5igzxn657aqhdzig2sj2kxvhhltwp236t62jinpbuacthjgua"
   "kotoba_module__2__0" "bafyreicv3mwfirvwrnsebwl4imeuwomhnypejgeoyjjwdozcubg2bncd54"
   "main" "bafyreib4zr3xtmmivldtfype6eqqmuxfgh2hhjadbq46q75vci6gk36v2a"})

(deftest a-project-without-templates-links-to-the-same-definitions-as-before
  (is (= cids-before-templates (definition-cids hand-sources 'root)))
  (let [{:keys [module-order source-map]} (project/link-source hand-sources 'root)]
    (is (= ['kotoba.set.union-i64 'kotoba.set.union-symbol 'root] module-order)
        "plain namespace keys, as before")
    (is (not-any? #(contains? % :binding) (:entries source-map))
        "source-map entries have the shape they had before")))
