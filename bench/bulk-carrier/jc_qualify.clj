;; J-C pre-pricing via perfgate.core/qualify (single judge).
;; Input: EDN {:host .. :fixture-sha256 {..} :gate [..]
;;        :runs [{:svec-touch .. :svec-base .. :svec-noref ..
;;                :loop-touch .. :loop-base .. :loop-noref ..}]}
;; (ns/element slope samples, one per slope round; two process-cold runs
;;  of 9 interleaved rounds each per spelling).
;; Pairs priced (candidate over baseline, lower-is-better):
;;   loop-touch  vs svec-touch  : removing the per-iteration assert-ref crossing
;;   loop-base   vs svec-base   : the carry-only arm (no vector-at)
;;   loop-noref  vs svec-noref  : control (should NOT qualify)
(ns jc-qualify
  (:require [clojure.java.io :as io]
            [machine.core :as m]
            [perfgate.core :as g]))

(def machine
  (m/measured
   {:format m/format-id
    :machine/id "darwin-arm64-benjamin"
    :cpu {:arch :aarch64 :cores 10}}
   "ssh benjamin; node v26.5.0; os.cpus()/loadavg probe on fleet node darwin arm64 10-core"))

(defn obs [id arm runs source]
  (g/observation {:id id
                  :plan-id :jc-host-crossing-priced
                  :machine machine
                  :metric :steady-state-runtime
                  :unit :nanoseconds-per-element
                  :samples (mapv #(get % (keyword arm)) runs)
                  :source source
                  :lower-is-better? true}))

(defn r4 [x]
  (when (number? x)
    (/ (double (Math/round (* 10000.0 (double x)))) 10000.0)))

(defn pair [label base cand runs source]
  (let [b (obs (keyword (name label) "-baseline") base runs source)
        c (obs (keyword (name label) "-candidate") cand runs source)
        v (g/qualify c b)
        sd (:separation v)]
    {:label label
     :base base :cand cand
     :qualified? (:qualified? v)
     :reasons (mapv :reason (:reasons v))
     :improvement (r4 (:improvement v))
     :gap (r4 (:gap sd))
     :summed-stdev (r4 (:summed-stdev sd))
     :separated? (:separated? sd)
     :n (get-in c [:observation/summary :n])
     :rel-stdev-base (r4 (get-in b [:observation/summary :relative-stdev]))
     :rel-stdev-cand (r4 (get-in c [:observation/summary :relative-stdev]))
     :baseline-mean (r4 (get-in b [:observation/summary :mean]))
     :candidate-mean (r4 (get-in c [:observation/summary :mean]))}))

(defn -main [path & _]
  (let [{:keys [host gate runs fixtures]} (read-string (slurp (io/file path)))
        source (str "bench/bulk-carrier wasmvec.kotoba.wasm sha256 "
                    (:wasmvec fixtures) " + wasmloop.kotoba.wasm sha256 "
                    (:wasmloop fixtures)
                    "; nbb slope.cljs <artifact> 200 9 (A=200, B=400, cpu time"
                    " slope, arms interleaved, checksum-verified vs kotoba.kir);"
                    " 2 process-cold runs; host " host
                    " load gate " (pr-str gate))]
    (println
     {:host host
      :gate gate
      :pairs (mapv (fn [[label base cand]] (pair label base cand runs source))
                   [["loop-vs-svec-touch" "svec-touch" "loop-touch"]
                    ["loop-vs-svec-base" "svec-base" "loop-base"]
                    ["loop-vs-svec-noref-CONTROL" "svec-noref" "loop-noref"]])})))
