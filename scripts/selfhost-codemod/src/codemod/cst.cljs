;; Lossless concrete syntax tree for .cljk/.cljc/.clj source.
;;
;; Why not the repo reader (kotoba.compiler.kotoba-reader / kr/read-forms)?  It reads the `.kotoba` grammar only
;; (no regex literals, `^:dynamic`, `'x`, `@x`, `#()`, character literals ...), so it cannot read frontend.cljk, and it
;; drops comments.  This parser keeps what a rewrite needs: EVERY node has absolute character offsets [:s :e) into the
;; source text (the same contract as the reader's :end-offset), comments and whitespace are never nodes, so a rewrite is a
;; list of text edits over those offsets and everything it does not touch stays byte-identical, comments included.
;;
;; Node = {:type T :s start :e end :kids [nodes] :text atom-text}.  Types:
;;   :list :vec :map :set :fnlit        collections (kids = forms, no trivia)
;;   :rc                                #?( ... ) / #?@( ... ); :splice? ; kids alternate feature-key, form
;;   :prefix                            ' ` ~ ~@ @ #' #:ns #tag  (:prefix "text"), kids = [form]
;;   :meta                              ^meta form, kids = [meta form]
;;   :sym :kw :num :str :char :regex    atoms (:text = exact source text)
;; `#_ form` is discarded (it stays inside the parent's text, untouched).
(ns codemod.cst)

(defn- rx [src] (js/RegExp. src "y"))
(def ^:private ws-rx (rx "(?:[\\s,]+|;[^\\n]*)*"))
(def ^:private atom-rx (rx "[^\\s,()\\[\\]{}\";]+"))
(def ^:private str-rx (rx "\"(?:[^\"\\\\]|\\\\[\\s\\S])*\""))
(def ^:private char-rx (rx "\\\\(?:u[0-9a-fA-F]{4}|o[0-7]{1,3}|[a-zA-Z]+|[\\s\\S])"))

(defn- match-at [^js r ^string src i]
  (set! (.-lastIndex r) i)
  (let [m (.exec r src)]
    (when m (aget m 0))))

(def ^:private closers {"(" ")" "[" "]" "{" "}"})

(declare read-form)

(defn- skip-ws [src i]
  (+ i (count (match-at ws-rx src i))))

(defn- ch [^string src i] (when (< i (count src)) (.charAt src i)))

(defn- read-until-close [src i close]
  ;; i is just after the opener; returns [kids end]
  (loop [i i kids []]
    (let [i (skip-ws src i)
          c (ch src i)]
      (cond
        (nil? c) (throw (ex-info "unterminated collection" {:at i :close close}))
        (= c close) [kids (inc i)]
        (contains? #{")" "]" "}"} c) (throw (ex-info (str "mismatched " c) {:at i}))
        :else (let [[n e] (read-form src i)]
                (recur e (if n (conj kids n) kids)))))))

(defn- atom-type [t]
  (cond (= \: (.charAt t 0)) :kw
        (re-find #"^[+-]?\d" t) :num
        :else :sym))

(defn read-form
  "Read one form at i (after whitespace).  Returns [node end]; node is nil for a `#_` discard."
  [src i]
  (let [c (ch src i)]
    (cond
      (contains? #{"(" "[" "{"} c)
      (let [[kids e] (read-until-close src (inc i) (closers c))]
        [{:type (case c "(" :list "[" :vec "{" :map) :s i :e e :kids kids} e])

      (= c "\"") (let [t (match-at str-rx src i)]
                   (when-not t (throw (ex-info "bad string" {:at i})))
                   [{:type :str :s i :e (+ i (count t)) :text t} (+ i (count t))])

      (= c "\\") (let [t (match-at char-rx src i)]
                   [{:type :char :s i :e (+ i (count t)) :text t} (+ i (count t))])

      (= c "^") (let [i1 (skip-ws src (inc i))
                      [m e1] (read-form src i1)
                      i2 (skip-ws src e1)
                      [f e2] (read-form src i2)]
                  [{:type :meta :s i :e e2 :kids [m f]} e2])

      (contains? #{"'" "`" "@"} c)
      (let [[f e] (read-form src (skip-ws src (inc i)))]
        [{:type :prefix :prefix c :s i :e e :kids [f]} e])

      (= c "~") (let [p (if (= "@" (ch src (inc i))) "~@" "~")
                      [f e] (read-form src (skip-ws src (+ i (count p))))]
                  [{:type :prefix :prefix p :s i :e e :kids [f]} e])

      (= c "#")
      (let [c2 (ch src (inc i))]
        (cond
          (= c2 "(") (let [[kids e] (read-until-close src (+ i 2) ")")]
                       [{:type :fnlit :s i :e e :kids kids} e])
          (= c2 "{") (let [[kids e] (read-until-close src (+ i 2) "}")]
                       [{:type :set :s i :e e :kids kids} e])
          (= c2 "\"") (let [t (match-at str-rx src (inc i))]
                        [{:type :regex :s i :e (+ i 1 (count t)) :text (str "#" t)} (+ i 1 (count t))])
          (= c2 "_") (let [[_ e] (read-form src (skip-ws src (+ i 2)))] [nil e])
          (= c2 "?") (let [splice? (= "@" (ch src (+ i 2)))
                           o (+ i 2 (if splice? 1 0))
                           _ (when-not (= "(" (ch src o)) (throw (ex-info "bad reader conditional" {:at i})))
                           [kids e] (read-until-close src (inc o) ")")]
                       [{:type :rc :splice? splice? :s i :e e :kids kids} e])
          (= c2 "#") (let [t (match-at atom-rx src (+ i 2))]
                       [{:type :sym :s i :e (+ i 2 (count t)) :text (str "##" t)} (+ i 2 (count t))])
          (= c2 "'") (let [[f e] (read-form src (skip-ws src (+ i 2)))]
                       [{:type :prefix :prefix "#'" :s i :e e :kids [f]} e])
          :else ;; #tag form  /  #:ns{...}
          (let [t (match-at atom-rx src (inc i))
                p (str "#" t)
                [f e] (read-form src (skip-ws src (+ i (count p))))]
            [{:type :prefix :prefix p :s i :e e :kids [f]} e])))

      :else (let [t (match-at atom-rx src i)]
              (when-not t (throw (ex-info "unreadable" {:at i :char c})))
              [{:type (atom-type t) :s i :e (+ i (count t)) :text t} (+ i (count t))]))))

(defn parse
  "All top-level forms of src (discards dropped)."
  [src]
  (loop [i 0 out []]
    (let [i (skip-ws src i)]
      (if (>= i (count src))
        out
        (let [[n e] (read-form src i)]
          (recur e (if n (conj out n) out)))))))

;; ---- node helpers ------------------------------------------------------------------------------------------------

(defn text [src n] (subs src (:s n) (:e n)))
(defn sym? ([n] (= :sym (:type n))) ([n s] (and (= :sym (:type n)) (= s (:text n)))))
(defn kw? ([n] (= :kw (:type n))) ([n s] (and (= :kw (:type n)) (= s (:text n)))))
(defn lst? [n] (= :list (:type n)))
(defn vec? [n] (= :vec (:type n)))
(defn map? [n] (= :map (:type n)))
(defn head [n] (when (lst? n) (first (:kids n))))
(defn head-text [n] (let [h (head n)] (when (and h (sym? h)) (:text h))))
(defn call-node?
  "A list or a #( ) literal: something whose first kid is the callee."
  [n] (contains? #{:list :fnlit} (:type n)))
(defn call-head-text [n]
  (when (call-node? n) (let [h (first (:kids n))] (when (and h (sym? h)) (:text h)))))
(defn call? [n s] (and (lst? n) (= s (head-text n))))
(defn args [n] (vec (rest (:kids n))))
(defn strip-meta
  "The form under ^meta wrappers."
  [n] (if (= :meta (:type n)) (recur (second (:kids n))) n))

(defn rc-branches
  "[[feature-key-text form-node] ...] of a #?( ) node."
  [n]
  (mapv (fn [[k f]] [(:text k) f]) (partition 2 (:kids n))))

(defn region-of-feature [k] (if (= k ":kotoba") :kotoba :default))

(defn walk
  "Pre-order walk.  (f node ctx) is called for every node; ctx = {:region R :path [ancestors...] :index i-in-parent}.
  Returning :skip prevents descending."
  [f nodes]
  (letfn [(go [n region path idx]
            (let [r (f n {:region region :path path :index idx})]
              (when-not (= r :skip)
                (let [path' (conj path n)]
                  (if (= :rc (:type n))
                    (doseq [[i [k form]] (map-indexed vector (partition 2 (:kids n)))]
                      (go form (region-of-feature (:text k)) (conj path' k) (inc (* 2 i))))
                    (doseq [[i k] (map-indexed vector (:kids n))]
                      (go k region path' i)))))))]
    (doseq [[i n] (map-indexed vector nodes)] (go n :shared [] i))))

(defn ->fn-view
  "A (defn name doc? params body) node seen as (fn params body): drops the name and docstring/attr-map so the
  fn-shaped helpers apply to it."
  [n]
  (let [kids (:kids n)
        rest-kids (drop 2 kids)
        rest-kids (drop-while #(or (= :str (:type %)) (= :map (:type %))) rest-kids)]
    {:type :list :kids (vec (cons (first kids) rest-kids)) :s (:s n) :e (:e n)}))
