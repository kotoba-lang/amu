;; Differential probe: the guest twin lang/compat/kotoba/value/codec.kotoba (encode-value on the KIR interpreter
;; over a linked project) against the host ipld.value/encode-value. KROOTS as in probe-definition-identity.cljs.
(ns vc-probe
  (:require ["node:fs" :as fs]
            [clojure.string :as str]
            [kotoba.sema :as sema]
            [kotoba.kir :as kir]
            [kotoba.compiler.project :as project]
            [kotoba.compiler.project-files :as pf]
            [ipld.value :as host-v]))

(def roots (vec (str/split (.-KROOTS js/process.env) #":")))

(defn f64-bits [d]
  (let [buf (js/ArrayBuffer. 8) v (js/DataView. buf)]
    (.setFloat64 v 0 d false)
    (str (.getBigInt64 v 0 false))))

(defn form-src [x]
  (let [mk (fn [t s n k kids] (str "(mk " t " " (pr-str s) " " n " " k " " kids ")"))
        lst (fn [xs] (str "(typed-list-new [:list [:ref :form/r]] " (str/join " " (map form-src xs)) ")"))]
    (cond
      (nil? x) (mk 0 "" 0 ":none" (lst []))
      (boolean? x) (mk 1 "" (if x 1 0) ":none" (lst []))
      (integer? x) (mk 2 "" x ":none" (lst []))
      (string? x) (mk 3 x 0 ":none" (lst []))
      (keyword? x) (mk 4 "" 0 (str x) (lst []))
      (symbol? x) (mk 5 (str x) 0 ":none" (lst []))
      (list? x) (mk 6 "" 0 ":none" (lst x))
      (vector? x) (mk 7 "" 0 ":none" (lst x))
      (set? x) (mk 8 "" 0 ":none" (lst x))
      (map? x) (if (contains? x :f64)
                 (mk 10 "" (f64-bits (:f64 x)) ":none" (lst []))
                 (mk 9 "" 0 ":none" (lst (mapcat identity x))))
      :else (throw (ex-info "no" {:x x})))))

(defn host-val [x]
  (cond (and (map? x) (contains? x :f64)) (host-v/float64 (:f64 x))
        (vector? x) (mapv host-val x)
        (list? x) (apply list (map host-val x))
        (set? x) (set (map host-val x))
        (map? x) (into {} (map (fn [[k v]] [(host-val k) (host-val v)])) x)
        :else x))

(def cases
  [nil true 5 -7 "s" :k/x :plain 'sym/x [1 2 [3]] '(1 2) #{3 1 2 "a" :z [1]}
   {"b" 1 :a 2 [1] 3 "aa" {"z" nil}} {:f64 1.5} [{:f64 -2.25} {:f64 0.1}]])

(defn run-case [x]
  (let [root "/tmp/probe_vc_main.cljk"
        src (str "(ns probe.vc-main\n  {:kotoba/export [main]}\n  (:require [kotoba.value.codec :as vc])\n"
                 "  (:schemas {:form/r [:record :form/r [[:tag :i64] [:s :string] [:n :i64] [:k :keyword] [:kids [:list [:ref :form/r]]] [:span :i64] [:data :bytes]]]}))\n"
                 "(defn mk [t :i64 s :string n :i64 k :keyword kids [:list [:ref :form/r]]] [:ref :form/r]\n"
                 "  (record-new [:ref :form/r] t s n k kids 0 (bytes-empty)))\n"
                 "(defn main [] :vector-i64 (vector-i64-from-bytes (vc/encode-value " (form-src x) ")))\n")]
    (.writeFileSync fs root src)
    (let [graph (pf/load-closed-graph root roots)
          linked (project/link-source (:sources graph) (:root graph))
          hir (sema/analyze (:source linked) {:admit-linked-synthetics? true})
          r (kir/execute (kir/lower hir) 'main [] {:fuel 100000000 :frames 4000 :cells 100000000 :bytes 100000000})
          got (mapv #(js/Number %) r)
          want (mapv #(bit-and % 0xff) (array-seq (host-v/encode-value (host-val x))))]
      {:x x :got got :want want :ok (= got want)})))

(doseq [c cases]
  (let [r (try (run-case c) (catch :default e {:ok false :err (subs (str e) 0 300)}))]
    (println (if (:ok r) "ok  " "FAIL") (pr-str c) (if (:ok r) "" (pr-str (dissoc r :x))))))
