;; Records real calls of the HOST passes of the frontend's remaining modules (state-ability, row, record-projection, analyze)
;; while `sema/analyze` runs the programs embedded in kotoba-sema's tests, as case lines for the Kotoba-route ports
;; (guests/ana.cljk). One line per distinct call:
;;   [:spec ctx fns lambda-helpers handlers exported shapes expected]       specialize-state-abilities
;;   [:thread ctx fns clones handlers expected]                             thread-state-abilities
;;   [:pred name args... expected]                                          the small state-ability predicates
;; ctx = {:schemas .. :row .. :handlers .. :final bool :known {..}}; expected is the host answer, or (:err "message").
;; env: DS_TESTS (kotoba-sema's test dir), DS_EXTRA (dir:dir of .kotoba programs), OUT (case file), MAX_PROGRAMS,
;;      ANA_OPS (comma list of ops to record, default all), ANA_SMALL (cap per small op, default 300).
(ns ana-record
  (:require ["node:fs" :as fs]
            [clojure.string :as str]
            [clojure.edn :as edn]
            [kotoba.sema :as sema]
            [kotoba.compiler.frontend.infer :as inf]
            [kotoba.compiler.frontend.closure-types :as ct]
            [kotoba.compiler.frontend.state-ability :as sa]
            [kotoba.compiler.frontend.record-projection :as rp]
            [kotoba.compiler.frontend.row :as row]))

(set! *print-namespace-maps* false)
(def env js/process.env)
(def tests-dir (.-DS_TESTS env))
(def out-path (.-OUT env))
(def max-programs (if-let [v (.-MAX_PROGRAMS env)] (js/parseInt v) 100000))
(def small-cap (if-let [v (.-ANA_SMALL env)] (js/parseInt v) 300))
(def wanted (when-let [v (.-ANA_OPS env)] (set (map keyword (str/split v #",")))))

(defn files-under [dir]
  (mapcat (fn [n]
            (let [p (str dir "/" n)]
              (if (.isDirectory (fs/statSync p)) (files-under p) [p])))
          (js->clj (fs/readdirSync dir))))

(defn programs-in [text]
  (for [lit (re-seq #"\"\(ns (?:[^\"\\]|\\.)*\"" text)
        :let [s (try (edn/read-string lit) (catch :default _ nil))]
        :when (string? s)]
    s))

(defn w [x]
  (cond
    (nil? x) "nil"
    (boolean? x) (str x)
    (keyword? x) (str x)
    (symbol? x) (str x)
    (string? x) (pr-str x)
    (and (not (coll? x)) (not (number? x)) (re-matches #"-?\d+" (str x))) (str x)
    (number? x) (if (and (integer? x) (< (js/Math.abs x) 9007199254740991)) (str x) (throw (ex-info "float" {})))
    (or (seq? x) (list? x)) (str "(" (str/join " " (map w x)) ")")
    (vector? x) (str "[" (str/join " " (map w x)) "]")
    (map? x) (str "{" (str/join " " (mapcat (fn [[k v]] [(w k) (w v)]) x)) "}")
    (set? x) (str "#{" (str/join " " (map w (sort-by str x))) "}")
    :else (throw (ex-info "unwritable" {:x (pr-str x)}))))

(def fn-keys [:name :source-name :params :param-types :result :body :result-inferred? :param-types-inferred
              :loop-helper? :lazy-thunk? :abort-error-type :abort-own-throw? :abort-catches?
              :state-handler :state-handler-clause :effects :callable-param-contracts :callable-result-contract])

(defn proj [f] (select-keys f fn-keys))

(defn deref-or [h dflt]
  (cond (nil? h) dflt (map? h) h (satisfies? IDeref h) (or @h dflt) :else dflt))

(defn ctx-now []
  {:schemas (or ct/*schemas* {})
   :row (deref-or inf/*row-op-schemas* {})
   :handlers (deref-or inf/*state-handlers* {})
   :final (boolean inf/*numeric-resolution-final*)
   :known (or inf/*abort-error-types* {})})

(def cases (atom {}))
(def counts (atom {}))
(def skipped (atom 0))

(defn record! [op line-fn]
  (when (or (nil? wanted) (contains? wanted op))
    (try
      (let [line (line-fn)]
        (when-not (contains? @cases line)
          (swap! cases assoc line op)
          (swap! counts update op (fnil inc 0))))
      (catch :default e (swap! skipped inc) (when (< @skipped 4) (println "skip:" (ex-message e) (pr-str (ex-data e))))))))

(defn small-room? [op] (< (get @counts op 0) small-cap))

(defn run-host [thunk]
  (try [:ok (thunk)] (catch :default e [:err e])))

(defn expected-of [a project]
  (if (= :ok (first a)) (w (project (second a))) (str "(:err " (pr-str (ex-message (second a))) ")")))

(defn result! [a] (if (= :ok (first a)) (second a) (throw (second a))))

(defn wrap! [ns-sym sym f]
  (let [v (resolve (symbol (str "kotoba.compiler.frontend." ns-sym) (name sym)))
        orig @v]
    (alter-var-root v (fn [_] (f orig)))))

(defn install! []
  (wrap! 'state-ability 'specialize-state-abilities
         (fn [orig]
           (fn [fns lambda-helpers handlers exported shapes]
             (let [ctx (ctx-now)
                   in-shapes (deref-or shapes {})
                   a (run-host #(orig fns lambda-helpers handlers exported shapes))
                   pr (fn [r] {:functions (mapv proj (:functions r)) :clones (:clones r) :handlers (:handlers r)
                               :shapes (deref-or shapes {})})]
               (record! :spec #(str "[:spec " (w ctx) " " (w (mapv proj fns)) " " (w (mapv proj lambda-helpers)) " " (w handlers)
                                    " " (w exported) " " (w in-shapes) " " (expected-of a pr) "]"))
               (result! a)))))
  (wrap! 'state-ability 'thread-state-abilities
         (fn [orig]
           (fn [fns clones handlers]
             (let [ctx (ctx-now)
                   a (run-host #(orig fns clones handlers))]
               (record! :thread #(str "[:thread " (w ctx) " " (w (mapv proj fns)) " " (w clones) " " (w handlers) " "
                                      (expected-of a (partial mapv proj)) "]"))
               (result! a)))))
  (doseq [[sym nm] [['state-escapes? :escapes] ['state-mentions? :mentions] ['state-first-stateful-operation :first-op]]]
    (wrap! 'state-ability sym
           (fn [orig]
             (fn [form x]
               (let [a (run-host #(orig form x))]
                 (when (small-room? nm)
                   (record! nm #(str "[:pred " (name nm) " " (w form) " " (w x) " " (expected-of a identity) "]")))
                 (result! a))))))
  (wrap! 'state-ability 'state-handle-bodies
         (fn [orig]
           (fn [form]
             (let [a (run-host #(orig form))]
               (when (small-room? :bodies)
                 (record! :bodies #(str "[:pred bodies " (w form) " " (expected-of a (partial vec)) "]")))
               (result! a)))))
  (wrap! 'state-ability 'state-split-resume
         (fn [orig]
           (fn [body part handler op]
             (let [a (run-host #(orig body part handler op))]
               (record! :split #(str "[:pred split " (w body) " " (w part) " " (w handler) " " (w op) " " (expected-of a identity) "]"))
               (result! a)))))
  (wrap! 'state-ability 'state-refuse-impure-handler!
         (fn [orig]
           (fn [handler op operations form]
             (let [a (run-host #(orig handler op operations form))]
               (record! :impure #(str "[:pred impure " (w handler) " " (w op) " " (w operations) " " (w form) " " (expected-of a identity) "]"))
               (result! a))))))

(def rp-depth (atom 0))

(defn install-rp! []
  ;; whole-module rewrite: the real differential (one counter for all functions)
  (wrap! 'record-projection 'rewrite-record-projections
         (fn [orig]
           (fn
             ([fns] (orig fns))
             ([fns schemas] (orig fns schemas))
             ([fns schemas dispatch]
              (let [ctx (ctx-now)
                    a (swap! rp-depth inc)
                    r (try (run-host #(orig fns schemas dispatch)) (finally (swap! rp-depth dec)))]
                (record! :rps #(str "[:rps " (w ctx) " " (w (mapv proj fns)) " " (w schemas) " " (w dispatch) " "
                                    (expected-of r (partial mapv proj)) "]"))
                (result! r))))))
  (doseq [[sym nm argn] [['collection-head-advice :advice 1] ['option-presence-test :presence 2] ['option-present-value :present 3]
                         ['resolve-float-operator :floatop 3] ['f64-bits-literal-form? :f64bits 1]
                         ['library-predicate-document-test :libdoc 2]]]
    (wrap! 'record-projection sym
           (fn [orig]
             (fn [& args]
               (let [a (run-host #(apply orig args))]
                 (when (small-room? nm)
                   (record! nm #(str "[:pred " (name nm) " " (str/join " " (map w args)) " "
                                     (expected-of a identity) "]")))
                 (result! a)))))))

(defn install-row! []
  (wrap! 'row 'specialize-row-parameters
         (fn [orig]
           (fn [fns exported]
             (let [ctx (ctx-now)
                   a (run-host #(orig fns exported))]
               (record! :rowspec #(str "[:rowspec " (w ctx) " " (w (mapv proj fns)) " " (w exported) " " (expected-of a (partial mapv proj)) "]"))
               (result! a)))))
  (wrap! 'row 'type-literals
         (fn [orig]
           (fn [fns]
             (let [ctx (ctx-now)
                   a (run-host #(orig fns))]
               (record! :tl #(str "[:tl " (w ctx) " " (w (mapv proj fns)) " " (expected-of a (partial mapv proj)) "]"))
               (result! a)))))
  (wrap! 'row 'row-generics
         (fn [orig]
           (fn [fns]
             (let [ctx (ctx-now)
                   a (run-host #(orig fns))]
               (record! :rowgen #(str "[:rowgen " (w ctx) " " (w (mapv proj fns)) " " (expected-of a identity) "]"))
               (result! a)))))
  (wrap! 'row 'type-literal
         (fn [orig]
           (fn [form locals table]
             (let [ctx (ctx-now)
                   a (run-host #(orig form locals table))]
               (when (small-room? :tlit)
                 (record! :tlit #(str "[:tlit " (w ctx) " " (w form) " " (w locals) " " (w table) " " (expected-of a identity) "]")))
               (result! a)))))
  (doseq [[sym nm] [['row-symbols-in :rsyms] ['row-rebinds? :rrebinds] ['row-if-branches :rif] ['row-joins :rjoins]
                    ['row-field-reads :rreads] ['row-operated? :roperated] ['row-pass-through :rpass]
                    ['row-text :rtext] ['row-name-part :rname] ['row-argument-text :rarg]]]
    (wrap! 'row sym
           (fn [orig]
             (fn [& args]
               (let [a (run-host #(apply orig args))]
                 (when (small-room? nm)
                   (record! nm #(str "[:pred " (name nm) " " (str/join " " (map w args)) " " (expected-of a identity) "]")))
                 (result! a))))))
  (wrap! 'row 'row-record-fields
         (fn [orig]
           (fn [t]
             (let [ctx (ctx-now)
                   a (run-host #(orig t))]
               (when (small-room? :rfields)
                 (record! :rfields #(str "[:pred rfields " (w (:schemas ctx)) " " (w t) " " (expected-of a identity) "]")))
               (result! a))))))

(install-row!)
(install-rp!)
(install!)

(let [files (filter #(re-find #"\.(cljk|clj|cljc)$" %) (files-under tests-dir))
      extra (mapcat (fn [d] (map (fn [f] (str (fs/readFileSync f "utf8"))) (filter #(re-find #"\.kotoba$" %) (files-under d))))
                    (remove str/blank? (str/split (or (.-DS_EXTRA env) "") #":")))
      progs (take max-programs (distinct (concat (mapcat (fn [f] (programs-in (str (fs/readFileSync f "utf8")))) files) extra)))]
  (println "programs:" (count progs))
  (doseq [[i p] (map-indexed vector progs)]
    (try (sema/analyze p) (catch :default _ nil))
    (when (zero? (mod i 25)) (println i (pr-str @counts))))
  (fs/writeFileSync out-path (str (str/join "\n" (keys @cases)) "\n"))
  (println "cases:" (pr-str @counts) "skipped" @skipped))
