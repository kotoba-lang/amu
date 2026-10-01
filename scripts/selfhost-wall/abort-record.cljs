;; Records real calls of the host absence/abort passes while `sema/analyze` runs the programs embedded in kotoba-sema's
;; tests, as case lines for the Kotoba-route port (abort_guest.cljk). One line per distinct call:
;;   [:abort ctx fns expected] [:elab ctx fns aet expected] [:results ctx fns expected] [:params ctx fns expected]
;;   [:absence ctx form locals sigs statement? expected]
;; ctx = {:schemas .. :row .. :handlers .. :final bool :known {..}}; expected is the host answer, or (:err "message").
(ns abort-record
  (:require ["node:fs" :as fs]
            [clojure.string :as str]
            [clojure.edn :as edn]
            [kotoba.sema :as sema]
            [kotoba.compiler.frontend.infer :as inf]
            [kotoba.compiler.frontend.closure-types :as ct]))

(set! *print-namespace-maps* false)
(def env js/process.env)
(def tests-dir (.-DS_TESTS env))
(def out-path (.-OUT env))
(def max-programs (if-let [v (.-MAX_PROGRAMS env)] (js/parseInt v) 100000))

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
    (set? x) (str "#{" (str/join " " (map w x)) "}")
    :else (throw (ex-info "unwritable" {:x (pr-str x)}))))

(def fn-keys [:name :source-name :params :param-types :result :body :result-inferred? :param-types-inferred
              :loop-helper? :lazy-thunk? :abort-error-type :abort-own-throw? :abort-catches?])

(defn proj [f] (select-keys f fn-keys))

(defn ctx-now []
  {:schemas (or ct/*schemas* {})
   :row (let [h inf/*row-op-schemas*] (cond (map? h) h (satisfies? IDeref h) (or @h {}) :else {}))
   :handlers (let [h inf/*state-handlers*] (cond (map? h) h (satisfies? IDeref h) @h :else {}))
   :final (boolean inf/*numeric-resolution-final*)
   :known (or inf/*abort-error-types* {})})

(def cases (atom {}))
(def counts (atom {}))
(def skipped (atom 0))

(defn record! [op line-fn]
  (try
    (let [line (line-fn)]
      (when-not (contains? @cases line)
        (swap! cases assoc line op)
        (swap! counts update op (fnil inc 0))))
    (catch :default e (swap! skipped inc) (when (< @skipped 4) (println "skip:" (ex-message e) (pr-str (ex-data e)))))))

(defn run-host [thunk]
  (try [:ok (thunk)] (catch :default e [:err e])))

(defn expected-of [a project]
  (if (= :ok (first a)) (w (project (second a))) (str "(:err " (pr-str (ex-message (second a))) ")")))

(defn result! [a] (if (= :ok (first a)) (second a) (throw (second a))))

(defn wrap! [sym op f]
  (let [v (resolve (symbol "kotoba.compiler.frontend.infer" (name sym)))
        orig @v]
    (alter-var-root v (fn [_] (f orig)))))

(defn install! []
  (wrap! 'infer-abort-error-types :abort
         (fn [orig]
           (fn [fns]
             (let [ctx (ctx-now)
                   a (run-host #(orig fns))
                   pr (fn [r] {:functions (mapv proj (:functions r)) :abort-error-types (:abort-error-types r)})]
               (record! :abort #(str "[:abort " (w ctx) " " (w (mapv proj fns)) " " (expected-of a pr) "]"))
               (result! a)))))
  (wrap! 'elaborate-aborts :elab
         (fn [orig]
           (fn [fns aet]
             (let [ctx (ctx-now)
                   a (run-host #(orig fns aet))]
               (record! :elab #(str "[:elab " (w ctx) " " (w (mapv proj fns)) " " (w aet) " " (expected-of a (partial mapv proj)) "]"))
               (result! a)))))
  (wrap! 'infer-absent-results :results
         (fn [orig]
           (fn [fns]
             (let [ctx (ctx-now)
                   a (run-host #(orig fns))]
               (record! :results #(str "[:results " (w ctx) " " (w (mapv proj fns)) " " (expected-of a (partial mapv proj)) "]"))
               (result! a)))))
  (wrap! 'infer-absent-parameter-types :params
         (fn [orig]
           (fn [fns]
             (let [ctx (ctx-now)
                   a (run-host #(orig fns))]
               (record! :params #(str "[:params " (w ctx) " " (w (mapv proj fns)) " " (expected-of a (partial mapv proj)) "]"))
               (result! a)))))
  (wrap! 'resolve-absence-if :absence
         (fn [orig]
           (fn
             ([form locals sigs] (orig form locals sigs false))
             ([form locals sigs statement?]
              (let [ctx (ctx-now)
                    a (run-host #(orig form locals sigs statement?))
                    sg (into {} (map (fn [[k v]] [k (select-keys v [:params :param-types :result])])) sigs)]
                (record! :absence #(str "[:absence " (w ctx) " " (w form) " " (w locals) " " (w sg) " " (w (boolean statement?)) " " (expected-of a identity) "]"))
                (result! a)))))))

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
