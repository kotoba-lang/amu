;; J-C residual (vector-at) pricing via perfgate.core/qualify (single judge),
;; tick 33 (JIT axis), 2026-09-09 12:49-14:10 JST on benjamin.
;; Input EDN: bench/runtime-comparison/jc_residual_benjamin_t33.edn shape:
;;   {:host .. :fixtures {..} :gate {..} :hand-runs .. :svec-runs ..
;;    :runs [{:hand-slice .. :hand-noref ..
;;            :svec-touch .. :svec-base .. :svec-noref ..}]}
;; Pairs (candidate over baseline, lower-is-better):
;;   hand-vs-svec-touch : hand-wasm slice arm (vector-at lowered to bounds-check
;;                       + load, zero host crossings) vs kotoba run-touch
;;                       (assert-ref crossing per element + vector-at lowering)
;;   hand-vs-svec-base  : carry-only arms (vector allocated but not read)
;;   hand-vs-svec-noref : control (no vector at all in either arm)
;;   hand-slice-vs-hand-noref : element access inside the hand module (context)
;; Run on benjamin:
;;   cd /tmp && clojure -Sdeps '{:paths ["~/jc_t32/perfgate/src" "~/jc_t32/machine/src" "/tmp"]}' -M -m jc-qualify-hand /tmp/runs_t33.edn
;; (with jc_qualify_hand.clj scp'd to /tmp; perfgate + machine sources are the
;; tick-32 on-node copies.)
(ns jc-qualify-hand
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
                  :plan-id :jc-residual-vector-at-priced
                  :machine machine
                  :metric :steady-state-runtime
                  :unit :nanoseconds-per-element
                  :samples (mapv #(get % (keyword (name arm))) runs)
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
  (let [{:keys [host gate runs fixtures hand-runs svec-runs]}
        (read-string (slurp (io/file path)))
        source (str "hand-wasm arms gen_slice_wasm.cljs module sha256 "
                    (:handslice fixtures)
                    " (plain WebAssembly.instantiate, no browser-host layer;"
                    " module is not a kotoba component) + kotoba wasmvec.kotoba.wasm sha256 "
                    (:wasmvec fixtures)
                    "; nbb slope 2000 9, CPU-time slope A vs 2A, arms interleaved,"
                    " checksum-verified (hand arms 133120/266240/129024/258048 vs"
                    " plain-instantiate; kotoba arms vs kotoba.kir); hand runs "
                    hand-runs " process-cold, kotoba runs " svec-runs
                    " process-cold; host " host
                    " load gate " (pr-str gate))]
    (println
     {:host host
      :gate gate
      :pairs (mapv (fn [[label base cand]] (pair label base cand runs source))
                   [["hand-vs-svec-touch" "svec-touch" "hand-slice"]
                    ["hand-vs-svec-base" "svec-base" "hand-slice"]
                    ["hand-vs-svec-noref-CONTROL" "svec-noref" "hand-noref"]
                    ["hand-slice-vs-hand-noref" "hand-noref" "hand-slice"]])})))
