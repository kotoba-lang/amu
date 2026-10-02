;; The LINKED end-to-end differential, host side: for every program embedded in kotoba-sema's tests (and the .kotoba programs under DS_EXTRA)
;; the HOST's `kotoba.sema/analyze` answer, as one case line per program:
;;   [:hir "<program text, EDN-escaped>" <HIR as EDN>]      or      [:hir "<program>" (:err "message")]
;; The guest (guests/e2e.cljk) analyses the same text on the Kotoba route (the frontend facade's analyze, compiled/interpreted from the
;; :kotoba reading) and compares the HIR with form/eq. env: DS_TESTS, DS_EXTRA, OUT, E2E_MAX (programs), E2E_MAXBYTES (per HIR, default 60000).
(ns e2e-record
  (:require ["node:fs" :as fs]
            [clojure.string :as str]
            [clojure.edn :as edn]
            [kotoba.sema :as sema]))

(set! *print-namespace-maps* false)
(def env js/process.env)
(def tests-dir (.-DS_TESTS env))
(def out-path (.-OUT env))
(def max-programs (if-let [v (.-E2E_MAX env)] (js/parseInt v) 100000))
(def max-bytes (if-let [v (.-E2E_MAXBYTES env)] (js/parseInt v) 60000))

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

(let [files (filter #(re-find #"\.(cljk|clj|cljc)$" %) (files-under tests-dir))
      extra (mapcat (fn [d] (map (fn [f] (str (fs/readFileSync f "utf8"))) (filter #(re-find #"\.kotoba$" %) (files-under d))))
                    (remove str/blank? (str/split (or (.-DS_EXTRA env) "") #":")))
      progs (take max-programs (distinct (concat (mapcat (fn [f] (programs-in (str (fs/readFileSync f "utf8")))) files) extra)))
      kept (atom 0) dropped (atom 0) errs (atom 0)
      lines (keep (fn [p]
                    (try
                      (let [r (try [:ok (sema/analyze p)] (catch :default e [:err (ex-message e)]))
                            body (if (= :ok (first r)) (w (second r)) (str "(:err " (pr-str (second r)) ")"))]
                        (if (> (count body) max-bytes)
                          (do (swap! dropped inc) nil)
                          (do (swap! kept inc) (when (= :err (first r)) (swap! errs inc))
                              (str "[:hir " (pr-str p) " " body "]"))))
                      (catch :default _ (swap! dropped inc) nil)))
                  progs)]
  (fs/writeFileSync out-path (str (str/join "\n" lines) "\n"))
  (println "programs:" (count progs) "kept:" @kept "(refusals:" @errs ") dropped:" @dropped))
