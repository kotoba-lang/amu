(ns codemod.codemod-test
  (:require [cljs.test :refer [deftest is testing]]
            [nbb.core :as nbb]
            [clojure.string :as str]
            ["node:fs" :as fs]
            ["node:path" :as path]
            [codemod.cst :as cst]
            [codemod.core :as core]
            [codemod.rules.destructure :as a]
            [codemod.rules.reject :as b]
            [codemod.rules.dynvars :as c]
            [codemod.rules.kwcallback :as d]
            [codemod.rules.letdestructure :as e]
            [codemod.rules.lowerloops :as f]))

(def here (path/dirname (path/dirname (path/dirname (path/resolve nbb/*file*)))))
(defn slurp* [p] (str (.readFileSync fs p "utf8")))
(defn rewrite
  ([src rules] (rewrite src rules {}))
  ([src rules opts] (:src (core/run src rules opts))))
(defn find* [src rules opts]
  (let [r (core/run src rules (assoc opts :dry-run true))] (:first r)))
(defn last-form [out] (cst/text out (last (cst/parse out))))
(defn real [fs] (remove #(= :info (:status %)) fs))

;; ---- the CST ---------------------------------------------------------------------------------------------------------------

(deftest cst-offsets-and-trivia
  (let [src "(ns x) ; c1\n(defn f [a] ;; c2\n  #_(ignored) (g a \"s;\\\"t\" \\space #\"re\" 'q @r ^:m z #?(:kotoba k :default d)))\n"
        ns (cst/parse src)]
    (is (= 2 (count ns)))
    (is (= "(defn f [a] ;; c2\n  #_(ignored) (g a \"s;\\\"t\" \\space #\"re\" 'q @r ^:m z #?(:kotoba k :default d)))" (cst/text src (second ns))))
    (is (= [:sym :sym :vec :list] (map :type (:kids (second ns)))))
    (testing "an empty edit list is the identity, comments included"
      (is (= src (:src (core/run src [] {})))))))

(deftest cst-parses-the-real-frontend
  (let [p "/Users/junkawasaki/github/kotoba-lang/kotoba-sema/src/kotoba/compiler/frontend.cljk"]
    (when (.existsSync fs p)
      (let [src (slurp* p) ns (cst/parse src)]
        (is (> (count ns) 500))
        (is (str/blank? (subs src (:e (last ns)))) "the last form ends where the file's text ends (trailing trivia only)")))))

;; ---- (a) destructuring lambdas -------------------------------------------------------------------------------------------

(deftest destructure-pair
  (is (= "(map (fn [dd__12_1] (let [k (fe-nth dd__12_1 0) v (fe-nth dd__12_1 1)] [k v])) m)"
         (last-form (rewrite "(ns x)\n(map (fn [[k v]] [k v]) m)" [a/rule]))))
  (is (str/includes? (rewrite "(ns x)\n(map (fn [[k v]] [k v]) m)" [a/rule]) "(defn- fe-nth [c i] (nth c i nil))")
      "the helper is inserted once, after ns"))

(deftest destructure-shapes
  (let [out (rewrite "(ns x)\n(def f (fn [{:keys [a b] :or {b 1} :as w} [x y & more]] body))" [a/rule])]
    (is (str/includes? out "(fe-get-or dd__"))
    (is (str/includes? out "(fe-nthnext dd__"))
    (is (str/includes? out "w dd__") ":as binds the whole value")
    (is (str/includes? out "body)"))))

(deftest destructure-human
  (testing "kwargs rest, empty body, pre/post map"
    (is (= [:human :human :human]
           (map :status
                (real (concat (find* "(fn [[a & {:keys [k]}]] a)" [a/rule] {})
                              (find* "(fn [[a b]])" [a/rule] {})
                              (find* "(fn [[a b]] {:pre [(pos? a)]} a)" [a/rule] {}))))))))

(deftest destructure-multi-arity
  (let [fs (real (find* "(fn ([[a b]] a) ([[a b] [c d]] c))" [a/rule] {}))]
    (is (= :auto (:status (first fs))))
    (is (= 3 (count (filter #(str/starts-with? (:text %) "dd__") (mapcat :edits fs)))) "three destructured params replaced")))

(deftest kotoba-types-are-not-patterns
  (is (empty? (real (find* "(defn f [x [:ref :form/r]] x)" [a/rule] {})))))

;; ---- (b) reject! ----------------------------------------------------------------------------------------------------------

(deftest reject-shapes
  (let [src "(defn f [x form]\n  (when-not (pos? x) (reject! \"m\" form :a/b))\n  (let [_ (when (neg? x) (reject! \"n\" form))]\n    (if (zero? x) (reject! \"z\" form :a/z) x)))"
        out (rewrite src [b/rule])]
    (is (str/includes? out "(let [_ #?(:kotoba (require-k (pos? x) \"m\" \"a/b\" form) :default (when-not (pos? x) (reject! \"m\" form :a/b)))]"))
    (is (str/includes? out "_ #?(:kotoba (require-k (not (neg? x)) \"n\" \"kotoba.error/subset-reject\" form) :default (when (neg? x) (reject! \"n\" form)))"))
    (is (str/includes? out "#?(:kotoba (throw (fe-error \"z\" \"a/z\" form)) :default (reject! \"z\" form :a/z))"))
    (is (= out (rewrite out [b/rule])) "idempotent")
    (testing "the host text survives byte for byte inside the :default arms"
      (is (str/includes? out ":default (when-not (pos? x) (reject! \"m\" form :a/b))")))))

(deftest reject-human
  (let [reasons (fn [src] (set (map :reason (filter #(= :human (:status %)) (find* src [b/rule] {})))))]
    (is (= #{"inside a loop/doseq/for/dotimes body (split into answer + throw)"}
           (reasons "(defn f [xs form] (doseq [x xs] (when-not x (reject! \"m\" form))) 1)")))
    (is (= #{"inside a lambda"} (reasons "(defn f [xs form] (mapv (fn [x] (if x x (reject! \"m\" form))) xs))")))
    (is (= #{"reject! with a data map (4-arity)"} (reasons "(defn f [form] (reject! \"m\" form :c {:k 1}))")))
    (is (= #{"reject! in value position (argument of another form)"} (reasons "(defn f [form] (foo (reject! \"m\" form)))")))
    (is (= #{"inside try/catch"} (reasons "(defn f [form] (try (reject! \"m\" form) (catch :default e nil)))")))
    (is (= #{"non-literal code argument"} (reasons "(defn f [form c] (reject! \"m\" form c))")))))

;; ---- (d) keyword callbacks ------------------------------------------------------------------------------------------------

(deftest kwcallback
  (is (= "(map (fn [e] (:a e)) xs)" (rewrite "(map :a xs)" [d/rule])))
  (is (= "(->> xs (filter (fn [e] (:ok e))) (map (fn [e] (:n e))))" (rewrite "(->> xs (filter :ok) (map :n))" [d/rule])))
  (is (= "(fn [e] [(:a e) (:b e)])" (rewrite "(juxt :a :b)" [d/rule])))
  (is (= "(map (fn [e] (fe-get e :a)) xs)" (last-form (rewrite "(ns x)\n(map :a xs)" [d/rule] {:lower-accessor true}))))
  (is (= "(map :a xs ys)" (rewrite "(map :a xs ys)" [d/rule])) "multi-collection map is left alone and reported")
  (is (= :human (:status (first (real (find* "(map :a xs ys)" [d/rule] {}))))))
  (is (= :human (:status (first (real (find* "(map (comp :a :b) xs)" [d/rule] {})))))))

;; ---- (e) let -----------------------------------------------------------------------------------------------------------------

(deftest let-destructuring
  (let [out (last-form (rewrite "(ns x)\n(let [[a b] (f x) m 1] (+ a b m))" [e/rule]))]
    (is (= "(let [dd__7_1 (f x) a (fe-nth dd__7_1 0) b (fe-nth dd__7_1 1) m 1] (+ a b m))" out))
    (is (= "(let [[a b] (f x)] 1)" (rewrite "(let [[a b] (f x)] 1)" [e/rule] {:regions #{:kotoba}})) "regions can be restricted")))

;; ---- (c) dynamic vars --------------------------------------------------------------------------------------------------------

(def dyn-src
  "(ns d)\n(def ^:dynamic *schemas* nil)\n(def ^:dynamic *counter* nil)\n(defn- leaf [x] (get *schemas* x))\n(defn- mid [x] (binding [*schemas* {:a 1}] (leaf x)))\n(defn- tick [] (vswap! *counter* inc))\n(defn top [x] (mid x))\n")

(deftest dynvars-analysis
  (let [nodes (cst/parse dyn-src)
        dual (c/analyze dyn-src nodes :dual)
        host (c/analyze dyn-src nodes :host-env)]
    (is (= #{"leaf" "mid" "tick" "top"} (:C dual)))
    (is (= #{"leaf" "mid" "top"} (:E dual)) "tick mutates a counter (needs result threading): blocked in dual")
    (is (contains? (:blocked dual) "tick"))
    (is (= #{"leaf" "mid" "tick"} (:E host)) "host-env keeps ref identity, so a counter is fine; public top stays an entry")
    (is (= #{"public function (signature observable)"} (get (:blocked host) "top")))))

(deftest dynvars-dual-output
  (let [out (rewrite dyn-src [c/rule] {:target :dual})]
    (is (str/includes? out "#?(:kotoba (defn- leaf [fenv x] (get (env-schemas fenv) x))"))
    (is (str/includes? out ":default (defn- leaf [x] (get *schemas* x)))"))
    (is (str/includes? out "(let [fenv (with-schemas fenv {:a 1})] (leaf fenv x))"))))

;; ---- host equivalence by evaluation -----------------------------------------------------------------------------------------

(defn load-ns! [src ns-name]
  (js/eval "0")
  (cljs.core/load-string (str/replace src "equiv.NS" ns-name)))

(defn v [ns-name nm] @(resolve (symbol ns-name nm)))

(def inputs
  {"pairs->map" [[{:a 1 :b 2}] [[]] [{}]]
   "sum-keys" [[[{:a 1} {:a 1 :b 2} {}]]]
   "nested" [[[[1 [2 3] 4 5] [1] []]]]
   "multi-arity-fn" [[[[1 2] [3]]]]
   "reduce-pairs" [[{:a 1 :b 2}]]
   "map-patterns" [[[{:a 1 :x 2 :pq [3 4]} {} {:pq [5]}]]]
   "kw-callbacks" [[[{:a 1 :ok true :n 3 :g :x :hit nil :kids [1 2]} {:a 2 :n 1 :g :y :hit 9 :kids [3]}]]]
   "check" [[5] [0] [-3] [100] ["s"]]
   "lets" [[{:p 1 :q 2}] [{}]]
   "outer" [[1] [5]]
   "counting" [[0] [3]]
   "read-depth" [[]]})

(defn call [ns-name nm args]
  (try {:ok (apply (v ns-name nm) args)}
       (catch :default e {:err [(ex-message e) (some-> (ex-data e) (select-keys [:code :data]))]})))

(defn equivalent? [rules opts tag]
  (let [src (slurp* (str here "/fixtures/equiv.cljk"))
        out (rewrite src rules opts)]
    (is (not= src out) (str tag ": the rewrite changed something"))
    (load-ns! src (str "equiv.orig" tag))
    (load-ns! out (str "equiv.new" tag))
    (doseq [[nm argsets] inputs, args argsets]
      (is (= (call (str "equiv.orig" tag) nm args) (call (str "equiv.new" tag) nm args)) (str tag " " nm " " (pr-str args))))))

(deftest host-equivalence-abde
  (equivalent? [a/rule b/rule d/rule e/rule] {} "abde"))

(deftest host-equivalence-c-host-env
  (equivalent? [c/rule] {:target :host-env} "c"))

(deftest host-equivalence-all
  (equivalent? [a/rule b/rule d/rule e/rule] {} "all1")
  (let [src (slurp* (str here "/fixtures/equiv.cljk"))
        s1 (rewrite src [a/rule b/rule d/rule e/rule])
        s2 (rewrite s1 [c/rule] {:target :host-env})]
    (load-ns! src "equiv.origall")
    (load-ns! s2 "equiv.newall")
    (doseq [[nm argsets] inputs, args argsets]
      (is (= (call "equiv.origall" nm args) (call "equiv.newall" nm args)) (str "a,b,d,e then c: " nm " " (pr-str args))))))

(deftest idempotent
  (let [src (slurp* (str here "/fixtures/equiv.cljk"))
        s1 (rewrite src [a/rule b/rule d/rule e/rule])]
    (is (= s1 (rewrite s1 [a/rule b/rule d/rule e/rule])))))

;; ---- (f) loops over Form collections ---------------------------------------------------------------------------------------

(deftest lowerloops
  (let [src "(ns x)\n(defn g [f] (mapv (fn [x] (inc x)) f))\n(defn h [f] (reduce (fn [acc x] (+ acc x)) 0 f))\n(defn q [f] (filter (fn [x] (pos? x)) f))"
        out (rewrite src [f/rule])]
    (is (str/includes? out "#?(:kotoba (let [fe-lc__"))
    (is (str/includes? out ":default (mapv (fn [x] (inc x)) f))") "the host call is the :default arm, byte for byte")
    (is (str/includes? out ":default (reduce (fn [acc x] (+ acc x)) 0 f))"))
    (is (str/includes? out "(form/append-form fe-la__"))
    (is (= out (rewrite out [f/rule])) "idempotent"))
  (testing "destructuring callbacks wait for rule (a)"
    (is (= :human (:status (first (real (find* "(mapv (fn [[a b]] a) f)" [f/rule] {}))))))
    (is (str/includes? (rewrite "(ns x)\n(defn g [f] (mapv (fn [[a b]] a) f))" [a/rule f/rule]) "(typed-list-nth [:list [:ref :form/r]]"))))
