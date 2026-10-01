;; bootstrap-tooling
;; BOOTSTRAP REFERENCE (nbb + KIR interpreter): GUEST=<module.cljk> ENTRY=<export> < input > output
(ns interp-run
  (:require ["node:fs" :as fs] ["node:crypto" :as crypto] [clojure.string :as str]
            [kotoba.sema :as sema] [kotoba.kir :as kir]
            [kotoba.compiler.project :as project] [kotoba.compiler.project-files :as pf]))
(def env js/process.env)
(def roots (vec (str/split (.-KROOTS env) #":")))
(defn typed-cap-call [id _ _ request]
  (case (js/Number id)
    3 (-> (.createHash crypto "sha256") (.update request) (.digest "hex"))
    (throw (ex-info "unhandled capability" {:id id}))))
(let [graph (pf/load-closed-graph (.-GUEST env) roots)
      linked (project/link-source (:sources graph) (:root graph))
      lowered (kir/lower (sema/analyze (:source linked) {:admit-linked-synthetics? true}))
      text (.readFileSync fs 0 "utf8")
      out (kir/execute lowered (symbol (.-ENTRY env)) [text]
                       {:typed-cap-call typed-cap-call :fuel 100000000000 :frames 100000 :cells 1000000000 :bytes 1000000000})]
  (.writeSync fs 1 (if (map? out) (throw (ex-info "guest trap" {:out (pr-str out)})) out)))
