;; J-B2 lever-pair qualification via perfgate.core/qualify (single judge).
;; Input: EDN file {:host .. :fixture-sha256 .. :gate [{:busy .. :load1 ..}]
;;                  :runs [{:A .. :B .. :C .. :D ..}]}  (ns/elem medians)
;; Output: EDN verdicts for A->B (lever1), A->C (lever2), A->D (both),
;; B->D (marginal inline on const), C->D (marginal const on inline).
(ns jb-qualify
  (:require [clojure.java.io :as io]
            [machine.core :as m]
            [perfgate.core :as g]))

(def machine
  (m/measured
   {:format m/format-id
    :machine/id "darwin-arm64-benjamin"
    :cpu {:arch :aarch64 :cores 10}}
   "ssh benjamin; os.cpus()/loadavg probe on fleet node darwin arm64 10-core"))

(defn obs [id arm runs source]
  (g/observation {:id id
                  :plan-id :jb-imod-lever-matrix-4arm
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
  (let [{:keys [host gate runs fixture-sha256]}
        (read-string (slurp (io/file path)))
        source (str "bench/runtime-comparison/jb_imod_control_4arms.c sha256 "
                    fixture-sha256
                    "; cc (Apple clang) -O3; ./jb4_t28 4000000 24; one median per process-cold run; host "
                    host " busy-fraction gate " (pr-str gate))
        pairs (mapv (fn [[label base cand]] (pair label base cand runs source))
                    [["lever1-const-only" "A" "B"]
                     ["lever2-inline-only" "A" "C"]
                     ["both" "A" "D"]
                     ["marginal-inline-on-const" "B" "D"]
                     ["marginal-const-on-inline" "C" "D"]])]
    (binding [*print-namespace-maps* false]
      (println
       (pr-str
        {:format "amu.jb-lever-matrix-perfgate/v1"
         :fixture-sha256 fixture-sha256
         :host host
         :gate gate
         :n-runs (count runs)
         :policy-id :kotoba.perfgate.policy/default-v1
         :pairs pairs})))))
