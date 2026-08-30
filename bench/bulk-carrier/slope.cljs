;; Per-element cost of a wasm32 element access, measured as a SLOPE between two
;; outer counts A and 2A. Everything constant -- module compile, JIT warmup, the
;; export call, the 64-element vector construction -- appears in both terms and
;; cancels, so no constant can inflate the result and no warmup round is needed.
;;
;; CPU time (process.cpuUsage user+system), never wall clock. Arms are
;; interleaved inside each round. Every arm's return value is checked against
;; the value kotoba.kir/execute returned for the same source BEFORE any timing:
;; an arm computing a different function must not be timed.
;;
;; These timings are DIAGNOSTIC, not claim-grade. This workstation carries
;; concurrent sessions and was measured at load1 12-700; a run at load1 394-613
;; read 3x the same arm's load1 12-23 figure and produced negative slopes in the
;; sub-nanosecond arms. Emit the samples and let `perfgate.core/qualify` decide;
;; do not compute a mean here and call it a result.
;;
;;   nbb slope.cljs <artifact.wasm> <A> <rounds>

(ns slope
  (:require ["fs" :as fs]
            ["../../runtime/browser-host.mjs" :as host]))

(def artifact (first *command-line-args*))
(def A (js/parseInt (or (second *command-line-args*) "200")))
(def rounds (js/parseInt (or (nth *command-line-args* 2 nil) "9")))
(def B (* 2 A))
(def per-outer (* 64 64))

;; From kotoba.kir/execute on the same source, at outer = 1 and 2.
(def expected {"run-touch" [(js/BigInt 133120) (js/BigInt 266240)]
               "run-base"  [(js/BigInt 129024) (js/BigInt 258048)]
               "run-noref" [(js/BigInt 129024) (js/BigInt 258048)]})

(defn cpu-us [] (let [u (.cpuUsage js/process)] (+ (.-user u) (.-system u))))

(defn timed [f n]
  (let [t0 (cpu-us)] (f (js/BigInt n)) (- (cpu-us) t0)))

(-> (host/instantiateKotoba (.readFileSync fs artifact) #js {})
    (.then
     (fn [k]
       (let [ex (.. k -instance -exports)
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
                                " " (map (fn [[k v]] (str ":" k " [" (clojure.string/join " " v) "]"))
                                         @samples)) "}")))))))
    (.catch (fn [e] (println "ERR" (.-message e)) (set! (.-exitCode js/process) 1))))
