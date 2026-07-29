(ns kotoba.compiler.fuel-estimate
  "T7.3: crude compile-time fuel estimate (function-entry charge model, T7.2).

  Best-effort only — not a sound WCET analysis."
  (:require [kotoba.compiler.frontend :as frontend]
            [clojure.string :as str]))

(defn- walk-forms [form f]
  (f form)
  (cond
    (seq? form) (doseq [x form] (walk-forms x f))
    (vector? form) (doseq [x form] (walk-forms x f))
    (map? form) (doseq [x (vals form)] (walk-forms x f))))

(defn- call-sites
  "Count list heads that look like function calls to simple symbols (not special)."
  [body specials]
  (let [n (atom 0)]
    (walk-forms body
                (fn [form]
                  (when (and (seq? form)
                             (simple-symbol? (first form))
                             (not (contains? specials (first form))))
                    (swap! n inc))))
    @n))

(def ^:private specials
  '#{if if-not when when-not let do and or quote
     string-concat string-length string-byte-length string-from-i64
     string=? string-substring string-contains? string-split-count
     string-fold-case string-code-point-at
     string-join inc dec record-new record-get
     + - * / quot rem mod < > <= >= = not not=
     pair pair-first pair-second first second rest empty? cons list
     cap-call typed-cap-call})

(defn estimate-hir
  "Estimate from analyzed HIR map (frontend/analyze result)."
  [hir]
  (let [fns (or (:functions hir) (:defs hir) [])
        ;; frontend analyze returns :functions as map or list depending on path
        fn-list (cond
                  (map? fns) (vals fns)
                  (sequential? fns) fns
                  :else [])
        entries (count fn-list)
        ;; Prefer :body on each function
        total-calls
        (reduce + 0
                (map (fn [function]
                       (let [body (or (:body function) (:form function))]
                         (if body (call-sites body specials) 0)))
                     fn-list))
        ;; Conservative: entry of main + one unit per static call site (each call
        ;; charges on callee entry). Self-recursion not unrolled.
        crude (+ (max 1 entries) total-calls)
        default-budget 512]
    {:format :kotoba.fuel-estimate/v1
     :wbs "T7.3"
     :model "1 unit per function entry (T7.2); static call-sites counted once"
     :function-count entries
     :static-call-sites total-calls
     :crude-units crude
     :default-budget default-budget
     :within-default-budget? (<= crude default-budget)
     :note "Does not expand recursion or loops; adversarial depth still needs runtime fuel."}))

(defn estimate-source
  "Analyze source and return crude fuel estimate."
  ([source] (estimate-source source nil))
  ([source opts]
   (let [hir (frontend/analyze source opts)]
     (assoc (estimate-hir hir)
            :exports (:exports hir)
            :language-profile (:language-profile hir)))))

(defn -main
  "CLI: clojure -M -m kotoba.compiler.fuel-estimate <file.kotoba>
        clojure -M -m kotoba.compiler.fuel-estimate --expr '(defn main [] (+ 1 2))'"
  [& args]
  (let [[mode a] (if (= "--expr" (first args))
                   [:expr (second args)]
                   [:file (first args)])]
    (when-not a
      (binding [*out* *err*]
        (println "usage: fuel-estimate <file.kotoba> | --expr <source>"))
      (System/exit 2))
    (let [src (if (= mode :expr) a (slurp a))
          report (estimate-source src)]
      (prn report)
      (System/exit (if (:within-default-budget? report) 0 0)))))
