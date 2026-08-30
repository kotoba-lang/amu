;; Puts the bulk-carrier arms through `perfgate.core/qualify` and prints every
;; refusal. No JVM: perfgate and machine are pure .cljc, so nbb runs them.
;;
;;   nbb --classpath <perfgate>/src:<machine>/src gate.cljs \
;;     <samples.edn> ... [candidate:baseline ...]
;;
;; Each samples file is `{:arm-name [ns-per-element ...]}` as emitted by
;; slope.cljs or native_model.c. A mean is never printed as a result on its own;
;; the verdict is perfgate's, and a refusal is reported rather than worked
;; around by relaxing the policy.

(ns gate
  (:require [perfgate.core :as g]
            [machine.core :as m]
            [clojure.edn :as edn]
            [clojure.string :as str]
            ["fs" :as fs]
            ["child_process" :as cp]))

(defn sysctl [k]
  (str/trim (.toString (.execSync cp (str "sysctl -n " k)))))

;; `:measured` provenance is a policy requirement -- perfgate refuses
;; `:assumed`, on the grounds that a claim resting on assumed hardware numbers
;; rests on nothing measured.
(def machine
  {:format :kotoba.machine/v1
   :machine/id (sysctl "hw.model")
   :machine/provenance :measured
   :machine/source "sysctl -n hw.model hw.ncpu hw.cachelinesize hw.pagesize hw.l1dcachesize hw.l2cachesize"
   :cpu {:arch :aarch64
         :cores (js/parseInt (sysctl "hw.ncpu"))
         :cache [{:level 1 :kind :data :bytes (js/parseInt (sysctl "hw.l1dcachesize"))
                  :line-bytes (js/parseInt (sysctl "hw.cachelinesize")) :shared-by 1}
                 {:level 2 :kind :unified :bytes (js/parseInt (sysctl "hw.l2cachesize"))
                  :line-bytes (js/parseInt (sysctl "hw.cachelinesize")) :shared-by 4}]}
   :page {:base-bytes (js/parseInt (sysctl "hw.pagesize")) :huge []}})

(let [errs (m/validation-errors machine)]
  (when (seq errs)
    (println "MACHINE INVALID:" (pr-str errs))
    (set! (.-exitCode js/process) 4)))

(def files (remove #(str/includes? % ":") *command-line-args*))
;; Pairs are named on the command line rather than inferred from argument order,
;; so the output records WHICH comparison was asked for and cannot silently
;; compare an arm against the wrong baseline (or against itself).
(def pairs (map #(mapv keyword (str/split % #":"))
                (filter #(str/includes? % ":") *command-line-args*)))

(def arms
  (reduce (fn [acc path]
            (merge acc (edn/read-string (.readFileSync fs path "utf8"))))
          {} files))

(defn obs [id samples]
  (g/observation {:id id :plan-id id :machine machine :metric :ns-per-element
                  :unit :ns :samples samples
                  :source (str "bench/bulk-carrier, " (str/join " " files))}))

(println "arm\tmean\tstdev\trel-stdev\tn")
(doseq [[k v] (sort arms)]
  (let [s (:observation/summary (obs k v))]
    (println (str (name k) "\t"
                  (.toFixed (:mean s) 4) "\t" (.toFixed (:stdev s) 4) "\t"
                  (.toFixed (:relative-stdev s) 4) "\t" (:n s)))))

;; An unqualified pair still prints its improvement, because hiding it would be
;; its own dishonesty -- but it prints the reasons beside it, and a refusal is
;; never worked around by relaxing the policy.
(println "\n--- qualify (perfgate default policy) ---")
(doseq [[cand base] pairs]
  (if-not (and (arms cand) (arms base))
    (println (str "\nMISSING ARM: " (name cand) " or " (name base)
                  " not present in " (str/join " " files)))
    (let [q (g/qualify (obs cand (arms cand)) (obs base (arms base)))]
      (println (str "\n" (name cand) " vs " (name base)
                    "\n  qualified? " (:qualified? q)
                    "  improvement " (.toFixed (:improvement q) 4)
                    "\n  separation " (pr-str (:separation q))
                    "\n  reasons " (pr-str (:reasons q)))))))
