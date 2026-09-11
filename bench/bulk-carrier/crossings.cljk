;; Counts host-boundary crossings per guest element for a compiled wasm32
;; artifact, by wrapping every import before instantiation.
;;
;; This is the load-independent half of the bulk-carrier evidence. A count does
;; not drift with host load, and this workstation runs at load1 12-700 from
;; concurrent sessions, so the counts are what the ADR's structural claims rest
;; on; the timings in `slope.cljs` are diagnostic.
;;
;;   nbb crossings.cljs <artifact.wasm> [export ...]

(ns crossings
  (:require ["fs" :as fs]
            ["../../runtime/browser-host.mjs" :as host]))

;; `*command-line-args*`, not `process.argv`: under nbb the script path itself
;; sits at argv[2], so a `(drop 2 process.argv)` reads the .cljs file as the
;; artifact and reports "Wasm compilation failed" for a perfectly good module.
(def artifact (first *command-line-args*))
(def exports (or (seq (rest *command-line-args*)) ["run-touch" "run-base" "run-noref"]))

(def counts (atom {}))

;; Wrap WebAssembly.instantiate rather than editing the host: the host builds
;; the import object itself, and a count taken anywhere else would be counting
;; something we constructed instead of what it passes.
(def real-instantiate js/WebAssembly.instantiate)
(set! (.-instantiate js/WebAssembly)
      (fn [module imports]
        (let [wrapped #js {}]
          (doseq [[ns-name obj] (js->clj imports)]
            (let [out #js {}]
              (doseq [k (js/Object.keys (aget imports ns-name))]
                (let [v (aget (aget imports ns-name) k)
                      key (str ns-name "/" k)]
                  (aset out k (if (fn? v)
                                (fn [& a] (swap! counts update key (fnil inc 0))
                                  (apply v a))
                                v))))
              (aset wrapped ns-name out)))
          (real-instantiate module wrapped))))

(defn -main []
  (-> (host/instantiateKotoba (.readFileSync fs artifact) #js {})
      (.then (fn [k]
                            (doseq [e exports]
                              (reset! counts {})
                              (let [v ((aget (.. k -instance -exports) e) (js/BigInt 1))
                                    elems (* 64 64)
                                    total (reduce + 0 (vals @counts))]
                                (println)
                                (println (str e "(1) = " v "   elements=" elems
                                              "  host-calls=" total
                                              "  per-element=" (.toFixed (/ total elems) 3)))
                                (doseq [[key n] (sort-by (comp - val) @counts)]
                                  (println "   " key n))))))
      (.catch (fn [e] (println "ERR" (.-message e)) (set! (.-exitCode js/process) 1)))))

(-main)
