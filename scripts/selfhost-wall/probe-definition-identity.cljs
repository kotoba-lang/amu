;; Differential probe: the guest twin lang/compat/kotoba/kir/definition_identity.kotoba (run on the KIR interpreter
;; over a linked project) against the host kotoba.kir.definition-identity/canonical-hex on five definitions.
;; KROOTS = colon-separated source roots (every classpath src dir, this src, lang/compat).
(ns di-probe
  (:require ["node:fs" :as fs]
            [clojure.string :as str]
            [kotoba.sema :as sema]
            [kotoba.kir :as kir]
            [kotoba.compiler.project :as project]
            [kotoba.compiler.project-files :as pf]
            [kotoba.kir.definition-identity :as host-di]))

(def roots (vec (str/split (.-KROOTS js/process.env) #":")))

(defn form-src [x]
  (let [mk (fn [t s n k kids] (str "(form/mk-probe " t " " (pr-str s) " " n " " k " " kids ")"))
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
      (map? x) (mk 9 "" 0 ":none" (lst (mapcat identity x)))
      :else (throw (ex-info "no" {:x x})))))

(def fmt (fn [s] s))
(defn run-case [x]
  (let [root (str "/tmp/probe_di_main.cljk")
        src (str "(ns probe.di-main\n  {:kotoba/export [main]}\n  (:require [kotoba.kir.definition-identity :as di])\n  (:schemas {:form/r [:record :form/r [[:tag :i64] [:s :string] [:n :i64] [:k :keyword] [:kids [:list [:ref :form/r]]] [:span :i64] [:data :bytes]]]}))\n"
                 "(defn mk [t :i64 s :string n :i64 k :keyword kids [:list [:ref :form/r]]] [:ref :form/r]\n"
                 "  (record-new [:ref :form/r] t s n k kids 0 (bytes-empty)))\n"
                 "(defn main [] :string (di/canonical-hex " (str/replace (form-src x) "form/mk-probe" "mk") "))\n")]
    (.writeFileSync fs root src)
    (let [graph (pf/load-closed-graph root roots)
          linked (project/link-source (:sources graph) (:root graph))
          hir (sema/analyze (:source linked) {:admit-linked-synthetics? true})
          r (kir/execute (kir/lower hir) 'main [] {:fuel 100000000 :frames 4000 :cells 100000000 :bytes 100000000})
          want (host-di/canonical-hex x)]
      {:x x :got r :want want :ok (= r want)})))

(def dep-a "bafkreigh2akiscaildcqabsyg3dfr6chu3fgpregiymsck7e7aqa4s52zy")
(def dep-b "bafkreiaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
(def base {:definition/profile-version 6 :definition/desugar-contract-version 2
           :definition/kir {:op :const :type :i64 :value 5}
           :definition/effect-row #{} :definition/interface {:params [] :result :i64}
           :definition/dependencies []})
(def cases
  [base
   (assoc base :definition/effect-row #{:abort :state/transact})
   (assoc base :definition/kir {:op :let :binds [['x {:op :const :value -12}] ['y {:op :const :value true}]]
                                 :body '(+ x y) :s #{3 1 2 "b" "a" [1] [0 2]} :n nil
                                 :f {:kotoba.lang.code-identity/f64 "3FF0000000000000"}
                                 :g {:kotoba.lang.code-identity/i64 "9223372036854775807"}
                                 :m {"z" 1 "aa" 2 :k 3 [1] 4}})
   (assoc base :definition/dependencies [dep-a dep-b])
   (assoc base :definition/dependencies [dep-b dep-a])])

(doseq [c cases]
  (let [r (try (run-case c) (catch :default e {:ok false :err (str e) :x c}))]
    (println (if (:ok r) "ok  " "FAIL")
             (cond (:ok r) ""
                   (:got r) (let [g (:got r) w (:want r)
                                  i (count (take-while true? (map = g w)))]
                              (str "first diff at " i " of " (count g) "/" (count w) " got=" (subs g (max 0 (- i 20)) (min (count g) (+ i 40))) " want=" (subs w (max 0 (- i 20)) (min (count w) (+ i 40)))))
                   :else (subs (pr-str (dissoc r :x)) 0 300)))))
