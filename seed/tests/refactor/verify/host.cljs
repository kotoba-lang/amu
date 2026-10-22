;; seed/tests/refactor/verify/host.cljs -- the host verify.cljk's answer for two runner outputs, in probe.kotoba's format
;; (nbb --classpath <amu>/src host.cljs a b). BOOTSTRAP-TOOL: the oracle of the twin differential only.
(require '[kotoba.compiler.refactor.verify :as v] '["fs" :as fs])
(let [[a c] *command-line-args*
      a (str (fs/readFileSync a "utf8")) c (str (fs/readFileSync c "utf8"))
      r (v/compare-runs a c)]
  (doseq [l (v/outcomes a)] (println (str "OA " l)))
  (doseq [l (v/outcomes c)] (println (str "OB " l)))
  (println (str "SA " (or (v/summary a) "")))
  (println (str "OK " (:ok r) " RAN " (:ran r) " BN " (:outcome-lines (:baseline r)) " NN " (:outcome-lines (:candidate r)) " D " (:differences r)))
  (doseq [l (:only-baseline r)] (println (str "XB " l)))
  (doseq [l (:only-candidate r)] (println (str "XN " l)))
  (doseq [l (v/run-argv {:nbb-cli "cli.js" :stack-size 4096 :classpath "a:b" :first-root "base" :runner "run.cljk"})] (println (str "AV " l))))
