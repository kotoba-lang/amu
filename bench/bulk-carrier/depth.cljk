;; How far can a guest traversal get before it traps, per loop spelling?
;;
;; wasm32 does not turn guest self-tail-recursion into a loop, so a
;; self-recursive traversal is bounded by the HOST call stack and stops with a
;; `RangeError`, not a Kotoba diagnostic -- it does not present as a language
;; limit at all. `loop`/`recur` becomes a real wasm loop and is O(1) in depth.
;;
;; A FRESH INSTANCE PER PROBE is not optional: a trap leaves the scratch bump
;; global unrestored, so every later call on that instance also traps and a
;; reused instance reports a ceiling of 1 whatever the real one is.
;;
;;   nbb depth.cljs <artifact.wasm> <export> <outer> ...

(ns depth
  (:require ["fs" :as fs]
            ["../../runtime/browser-host.mjs" :as host]))

(def artifact (first *command-line-args*))
(def export-name (second *command-line-args*))
(def counts (map js/parseInt (drop 2 *command-line-args*)))
(def bytes (.readFileSync fs artifact))

(defn probe [n]
  (-> (host/instantiateKotoba bytes #js {})
      (.then (fn [k]
               (try ((aget (.. k -instance -exports) export-name) (js/BigInt n)) "ok"
                    (catch :default e (str (.. e -constructor -name) ": " (.-message e))))))
      (.catch (fn [e] (str "instantiate failed: " (.-message e))))))

(defn run [remaining]
  (when (seq remaining)
    (let [n (first remaining)]
      (-> (probe n)
          (.then (fn [r]
                   (println artifact export-name (str "outer=" n) r)
                   (run (rest remaining))))))))

(run counts)
