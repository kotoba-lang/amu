;; nbb codemod.cli: node --stack-size=4096 nbb/cli.js --classpath scripts/selfhost-codemod/src scripts/selfhost-codemod/run.cljs ...
(ns codemod.cli
  (:require [clojure.string :as str]
            ["node:fs" :as fs]
            [codemod.core :as core]
            [codemod.rules.destructure :as a]
            [codemod.rules.reject :as b]
            [codemod.rules.dynvars :as c]
            [codemod.rules.kwcallback :as d]
            [codemod.rules.letdestructure :as e]
            [codemod.rules.lowerloops :as f]))

(def rule-table {"a" a/rule "destructure" a/rule "b" b/rule "reject" b/rule "c" c/rule "dynvars" c/rule "f" f/rule "lowerloops" f/rule "e" e/rule "let" e/rule "d" d/rule "kwcallback" d/rule})

(defn- parse-args [args]
  (loop [as args m {:rules []}]
    (if-let [x (first as)]
      (case x
        "--out" (recur (drop 2 as) (assoc m :out (second as)))
        "--rules" (recur (drop 2 as) (assoc m :rules (str/split (second as) #",")))
        "--dry-run" (recur (rest as) (assoc m :dry-run true))
        "--report" (recur (drop 2 as) (assoc m :report (second as)))
        "--lower-accessor" (recur (rest as) (assoc m :lower-accessor true))
        "--include-ported" (recur (rest as) (assoc m :include-ported true))
        "--target" (recur (drop 2 as) (assoc m :target (keyword (second as))))
        "--regions" (recur (drop 2 as) (assoc m :regions (set (map keyword (str/split (second as) #",")))))
        "--observable-from" (recur (drop 2 as) (assoc m :observable-from (str/split (second as) #",")))
        "--max-passes" (recur (drop 2 as) (assoc m :max-passes (js/parseInt (second as))))
        (recur (rest as) (assoc m :file x)))
      m)))

(defn- files-under [dir]
  (mapcat (fn [n] (let [p (str dir "/" n)]
                    (if (.isDirectory (.statSync fs p)) (files-under p)
                        (when (re-find #"\.(cljk|clj|cljc|cljs|kotoba|edn)$" n) [p]))))
          (array-seq (.readdirSync fs dir))))

(defn observable-names
  "Names of the frontend referenced from outside it: #'kotoba.compiler.frontend/f, frontend/f, fe/f."
  [dirs]
  (set (for [d dirs f (files-under d)
             m (re-seq #"(?:#')?(?:kotoba\.compiler\.frontend|frontend|fe)/([^\s()\[\]{}\"]+)" (str (.readFileSync fs f "utf8")))]
         (second m))))

(defn -main [args]
  (let [{:keys [file out rules report] :as o} (parse-args args)
        src (str (.readFileSync fs file "utf8"))
        rs (map #(or (get rule-table %) (throw (ex-info (str "unknown rule " %) {}))) (:rules o))
        o (cond-> o (:observable-from o) (assoc :observable (observable-names (:observable-from o))))
        res (core/run src rs o)
        summary (core/summarize (:first res) (:applied res))]
    (when out (.writeFileSync fs out (:src res)))
    (let [rep {:file file :passes (:passes res) :summary summary
               :human-sites (vec (for [f (:first res) :when (= :human (:status f))]
                                   (select-keys f [:rule :line :region :reason :context :kind])))}]
      (when report (.writeFileSync fs report (pr-str rep)))
      (prn (dissoc rep :human-sites))
      (doseq [inv (filter #(= :inventory (:kind %)) (:first res))] (prn :inventory (:rule inv) (:data inv))))))
