;; Differential harness for the Kotoba-route module passes of kotoba-sema's frontend/infer.cljk
;; (check-value-types!, elaborate-named-abilities, infer-loop-helper-results, check-loop-recur-argument-types!,
;; resolve-loop-helper-param-types, infer-closure-refinements) against the HOST functions.
;;
;; HOST side: every program embedded in kotoba-sema's tests (strings that read as programs) is analysed with the host
;; pipeline; the six passes are tapped where `analyze` calls them, and each call's arguments, dynamic context
;; (*schemas*, *row-op-schemas*, *state-handlers*) and answer (value or refusal message) become one case line
;; [op ctx functions extra expected]. KOTOBA side: infer.cljk's :kotoba view (gen-guest.py) compiled natively
;; (guest-run.sh) answers OK / OKERR / DIFF ... per line; the comparison is `form/eq` inside the guest.
(ns ie-host
  (:require ["node:fs" :as fs]
            [clojure.string :as str]
            [clojure.walk :as walk]
            [kotoba.sema :as sema]
            [kotoba.compiler.frontend :as fe]
            [kotoba.compiler.frontend.closure-types :as fct]
            [kotoba.compiler.frontend.infer :as fi]
            [kotoba.compiler.frontend.analyze :as fa]))

(set! *print-namespace-maps* false)
(def env js/process.env)
(def test-dir (.-KTEST env))
(def argv (vec (drop 1 (js->clj (.-argv js/process)))))
(defn opt [k default] (if-let [i (some (fn [[a i]] (when (= a k) i)) (map vector argv (range)))] (js/parseInt (nth argv (inc i))) default))
(defn opt-str [k default] (if-let [i (some (fn [[a i]] (when (= a k) i)) (map vector argv (range)))] (nth argv (inc i)) default))
(def limit-programs (opt "--programs" 1000000))
(def cases-file (opt-str "--cases" "ie-cases.txt"))

;; ---- corpus (strings out of the test sources) ----
(defn files-under [dir suffixes]
  (mapcat (fn [n]
            (let [p (str dir "/" n)]
              (cond (.isDirectory (fs/statSync p)) (files-under p suffixes)
                    (some #(str/ends-with? n %) suffixes) [p]
                    :else [])))
          (sort (js->clj (fs/readdirSync dir)))))
(defn unescape [s] (str/replace s #"\\(.)" (fn [[_ c]] (case c "n" "\n" "t" "\t" "r" "\r" c))))
(defn regex-strings [text] (map (comp unescape second) (re-seq #"\"((?:[^\"\\]|\\.)*)\"" text)))
(defn strings-of-file [f]
  (let [text (fs/readFileSync f "utf8")]
    (try (let [acc (atom [])]
           (walk/postwalk (fn [y] (when (string? y) (swap! acc conj y)) y) (vec (fe/read-forms text)))
           @acc)
         (catch :default _ (regex-strings text)))))
(def test-files (files-under test-dir [".cljk"]))
(def fixture-programs (keep (fn [f] (try (fs/readFileSync f "utf8") (catch :default _ nil))) (files-under test-dir [".kotoba"])))
(defn program-variants [s]
  (cond (not (str/includes? s "(")) []
        (str/starts-with? (str/triml s) "(ns ") [s]
        :else [(str "(ns m.p {:kotoba/export [main]})\n" s)]))
(def extra-dirs (remove str/blank? (str/split (or (.-IE_EXTRA env) "") #":")))
(def extra-programs
  (keep (fn [f] (try (fs/readFileSync f "utf8") (catch :default _ nil)))
        (mapcat #(files-under % [".kotoba"]) extra-dirs)))
(def programs (distinct (concat (mapcat program-variants (distinct (concat (mapcat strings-of-file test-files) fixture-programs)))
                                (if (some #{"--only-extra"} argv) [] [])
                                extra-programs)))
(def only-extra? (some #{"--only-extra"} argv))

;; ---- printing ----
(defn mark-f64 [x]
  (cond (and (seq? x) (true? (:kotoba.reader/f64-literal (meta x)))) (list '__ds_f64 (second x))
        (seq? x) (apply list (map mark-f64 x))
        (vector? x) (mapv mark-f64 x)
        (set? x) (set (map mark-f64 x))
        (map? x) (into {} (map (fn [[k v]] [(mark-f64 k) (mark-f64 v)])) x)
        :else x))
(defn ep [x]
  (cond
    (nil? x) "nil"
    (boolean? x) (str x)
    (string? x) (pr-str x)
    (keyword? x) (str x)
    (symbol? x) (str x)
    (number? x) (str x)
    (and (some? x) (some? (.-constructor x)) (= "BigInt" (.-name (.-constructor x)))) (str x)
    (seq? x) (str "(" (str/join " " (map ep x)) ")")
    (map? x) (str "{" (str/join " " (mapcat (fn [[k v]] [(ep k) (ep v)]) x)) "}")
    (set? x) (str "#{" (str/join " " (map ep x)) "}")
    (sequential? x) (str "[" (str/join " " (map ep x)) "]")
    :else (str "#unprintable" (pr-str x))))
(defn line-of [x] (str/replace (ep (mark-f64 x)) #"\n" "\\n"))

;; ---- taps ----
(def cases (atom []))
(defn ctx-now []
  {:schemas (some-> fct/*schemas*) :row-schemas (some-> fi/*row-op-schemas* deref) :handlers (some-> fi/*state-handlers* deref)})
(defn norm [s] (-> s (str/replace #"#object\[BigInt (-?\d+)\]" "$1") (str/replace #"(\d+)n\b" "$1")))
(defn record! [op ctx functions extra thunk]
  ;; the host's elaboration is lazy: a refusal can surface only when the answer is realized, so it is printed here
  (let [ctxs (line-of ctx) fs (line-of functions) ex (line-of extra)
        head (str "[\"" op "\" " ctxs " " fs " " ex " ")
        outcome (try [:value (thunk)] (catch :default e [:throw e]))]
    (if (= :throw (first outcome))
      (do (swap! cases conj {:line (str head "[:err " (pr-str (norm (str (ex-message (second outcome))))) "]]")})
          (throw (second outcome)))
      (let [r (second outcome)
            shown (try [:shown (line-of (if (= op "cvt") nil r))] (catch :default e [:err (ex-message e)]))]
        (swap! cases conj {:line (if (= :shown (first shown))
                                   (str head "[:ok " (second shown) "]]")
                                   (str head "[:err " (pr-str (norm (str (second shown)))) "]]"))})
        r))))

(def o-cvt fi/check-value-types!)
(def o-ela fi/elaborate-named-abilities)
(def o-lhr fi/infer-loop-helper-results)
(def o-clr fi/check-loop-recur-argument-types!)
(def o-icr fi/infer-closure-refinements)
(def o-rlh fa/resolve-loop-helper-param-types)
(set! fi/check-value-types! (fn [fs] (record! "cvt" (ctx-now) fs nil #(o-cvt fs))))
(set! fi/elaborate-named-abilities (fn [fs] (record! "ela" (ctx-now) fs nil #(o-ela fs))))
(set! fi/infer-loop-helper-results (fn [fs shapes] (record! "lhr" (ctx-now) fs shapes #(o-lhr fs shapes))))
(set! fi/check-loop-recur-argument-types! (fn [fs shapes] (record! "clr" (ctx-now) fs shapes #(o-clr fs shapes))))
(set! fi/infer-closure-refinements (fn [fs infos] (record! "icr" (ctx-now) fs infos #(o-icr fs infos))))
(set! fa/resolve-loop-helper-param-types
      (fn ([fs] (o-rlh fs))
        ([fs shapes] (record! "rlh" (ctx-now) fs shapes #(o-rlh fs shapes)))))

(defn -main []
  (doseq [[i p] (map-indexed vector (take limit-programs (if only-extra? extra-programs programs)))]
    (try (sema/analyze p) (catch :default _ nil))
    (when (zero? (mod (inc i) 50)) (println "analysed" (inc i) "programs, cases" (count @cases))))
  (let [lines (distinct (map :line @cases))]
    (fs/writeFileSync cases-file (str (str/join "\n" lines) "\n"))
    (println "programs" (count (take limit-programs (if only-extra? extra-programs programs))) "cases" (count @cases) "distinct" (count lines) "written" cases-file)))
(-main)
