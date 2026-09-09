;; J-C residual pricing: hand-wasm arms (gen_slice_wasm.cljs module) measured
;; with the SAME slope method as the kotoba arms (slope.cljs), without the
;; browser-host admission layer (the hand module is not a kotoba component —
;; it carries no compatibility metadata — so instantiateKotoba would reject it;
;; plain WebAssembly.instantiate is the honest route; module compile + export
;; instantiation are outside every timed region, and the A vs 2A slope cancels
;; all constants regardless).
;;
;;   nbb slope_hand.cljs <hand.wasm> 2000 9
;;   -> {:hand-slice [..] :hand-noref [..]}  (ns/element CPU-time slopes)

(ns slope-hand
  (:require ["fs" :as fs]))

(def artifact (first *command-line-args*))
(def A (js/parseInt (or (second *command-line-args*) "200")))
(def rounds (js/parseInt (or (nth *command-line-args* 2 nil) "9")))
(def B (* 2 A))
(def per-outer (* 64 64))

;; Verified on benjamin 2026-09-09 before any timing (plain instantiate):
;;   run-slice 1 133120, 2 266240; run-noref 1 129024, 2 258048
;; — byte-identical to the kotoba wasmvec expectations in slope.cljs.
(def expected {"run-slice" [(js/BigInt 133120) (js/BigInt 266240)]
               "run-noref" [(js/BigInt 129024) (js/BigInt 258048)]})

(defn cpu-us [] (let [u (.cpuUsage js/process)] (+ (.-user u) (.-system u))))

(defn timed [f n]
  (let [t0 (cpu-us)] (f (js/BigInt n)) (- (cpu-us) t0)))

(-> (js/WebAssembly.instantiate (.readFileSync fs artifact) #js {})
    (.then
     (fn [res]
       (let [ex (.. res -instance -exports)
             arms (filterv #(some? (aget ex %)) (keys expected))]
         (doseq [name arms, [i n] (map-indexed vector [1 2])]
           (let [got ((aget ex name) (js/BigInt n))
                 want (nth (expected name) i)]
             (when (not= got want)
               (println "WRONG" name n "got" got "want" want)
               (set! (.-exitCode js/process) 3))))
         (when (zero? (or (.-exitCode js/process) 0))
           (let [samples (atom (zipmap arms (repeat [])))]
             (dotimes [_ rounds]
               (doseq [name arms]
                 (let [f (aget ex name)
                       ta (timed f A) tb (timed f B)]
                   (swap! samples update name conj
                          (/ (* (- tb ta) 1000.0) (* (- B A) per-outer))))))
             (println (str "{" (clojure.string/join
                                " " (map (fn [[k v]] (str ":" (clojure.string/replace k #"^run-" "hand-") " [" (clojure.string/join " " v) "]"))
                                         @samples)) "}")))))))
    (.catch (fn [e] (println "ERR" (.-message e)) (set! (.-exitCode js/process) 1))))
