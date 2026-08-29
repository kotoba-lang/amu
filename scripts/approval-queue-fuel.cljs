#!/usr/bin/env nbb
;; Measure the fuel a compiled `kotoba/app` guest actually needs at the
;; request bounds its host admits, so the `--fuel` number baked into the
;; shipped artifact is a measured choice rather than a round number someone
;; liked.
;;
;; ## Why this has to be measured rather than reasoned about
;;
;; Fuel is charged per function ENTRY and is a per-INSTANCE budget, opened by
;; `instantiateKotoba()` and never replenished. A guest that scans its own
;; JSON body enters a function per code point, so what it can afford is fixed
;; at COMPILE time and cannot be raised by the host later. If the host admits
;; a body larger than the guest was compiled to scan, the guest does not
;; answer wrongly -- it traps -- and the host turns that into a 500. The
;; number therefore has to be chosen against the admitted bound, and the only
;; honest way to know it is to run the worst case.
;;
;; ## How the minimum is found without recompiling
;;
;; The `:js-kotoba-v1` artifact carries its budget as a literal `fuel=N` in
;; the emitted JS. Measurement copies rewrite that literal and re-import, so
;; a bisection costs milliseconds instead of a JVM compile each. The SHIPPED
;; artifact is never rewritten -- it is compiled at the chosen value, and
;; this script then checks the shipped literal against what it measured.
;;
;; ## What it refuses to do
;;
;; If the worst case cannot be made to run at ANY fuel in range, the answer
;; is not "0, therefore cheap" -- it exits 2 (neither pass nor fail), because
;; a measurement that could not be taken must not read like one that was.
(ns approval-queue-fuel
  (:require ["node:fs" :as fs]
            ["node:os" :as os]
            ["node:path" :as path]))

(defn arg [flag fallback]
  (let [argv (vec (.slice js/process.argv 2))
        i (.indexOf argv flag)]
    (if (neg? i) fallback (nth argv (inc i) fallback))))

(def module-path (arg "--module" nil))
(def body-bytes (js/parseInt (arg "--body-bytes" "1024")))
(def state-bytes (js/parseInt (arg "--state-bytes" "1024")))
(def margin (js/parseFloat (arg "--margin" "3.0")))
(def ceiling (js/parseInt (arg "--ceiling" "8000000")))

(when-not module-path
  (println "usage: approval-queue-fuel.cljs --module <compiled.mjs> [--body-bytes N] [--state-bytes N] [--margin R]")
  (js/process.exit 2))

(def tmp (.mkdtempSync fs (.join path (.tmpdir os) "kotoba-fuel-")))
(def source (.readFileSync fs module-path "utf8"))

(def shipped-fuel
  (let [m (re-find #"fuel=(\d+)" source)]
    (when-not m
      (println "REFUSING to report: no `fuel=<n>` literal found in" module-path)
      (js/process.exit 2))
    (js/parseInt (second m))))

;; ---------------------------------------------------------------------------
;; Worst-case inputs, built to the bounds the host declares.
;;
;; Worst case for a field read is a member the scan reaches LAST, behind a
;; member it has to skip structurally. Worst case for the fold is an ELIGIBLE
;; decision, because an ineligible one short-circuits into `ignore-one` and
;; never renders the lists. Both are built that way on purpose: measuring the
;; cheap path and shipping the number would be the same defect this script
;; exists to prevent.
;; ---------------------------------------------------------------------------

(defn pad-to
  "Grow VALUE's padding field until the rendered JSON is exactly N bytes."
  [n build]
  (loop [fill 0]
    (let [s (build fill)
          len (.byteLength js/Buffer s "utf8")]
      (cond
        (= len n) s
        (> len n) (if (zero? fill)
                    (throw (js/Error. (str "cannot build an input as small as " n " bytes")))
                    (build (dec fill)))
        :else (recur (inc fill))))))

(def worst-state
  ;; A state at the cap: the accumulated approved list is what grows, so the
  ;; cap is reached with real content rather than filler in an unread field.
  (pad-to state-bytes
          (fn [fill]
            (js/JSON.stringify
             #js {"item" "work-1" "hash" "sha256-a1" "minimum" "2" "veto" "true"
                  "separation" "true" "submitter" "carol"
                  "approved" (.join (clj->js (mapv #(str "actor-" %) (range fill))) ",")
                  "rejected" "" "ignored" "0"}))))

(def worst-event
  ;; Eligible, and every field the guest reads sits behind a member it must
  ;; skip structurally -- a nested object carrying braces, commas and quotes.
  (pad-to body-bytes
          (fn [fill]
            (js/JSON.stringify
             #js {"meta" #js {"note" (.repeat "a{b},c:\\d " (inc fill))}
                  "actor" "newcomer" "decision" "approved" "item" "work-1"
                  "hash" "sha256-a1" "person" "true" "role" "true"}))))

(defn instance-at
  "Import a copy of the artifact whose fuel literal is FUEL, and instantiate."
  [fuel n]
  (let [copy (.join path tmp (str "probe-" n ".mjs"))]
    (.writeFileSync fs copy (.replace source #"fuel=\d+" (str "fuel=" fuel)))
    (-> (js/import (str "file://" copy))
        (.then (fn [m] ((.-instantiateKotoba m) #js {}))))))

(def attempt (atom 0))

(defn runs?
  "Does the WHOLE worst case complete at FUEL? `step` and `view` each get
  their own fresh instance, exactly as runtime/http-service.mjs does, so the
  budget has to cover the larger of the two -- not their sum."
  [fuel]
  (let [n (swap! attempt inc)]
    (-> (instance-at fuel n)
        (.then (fn [step-instance]
                 (let [next ((aget step-instance "step") worst-state worst-event)]
                   (-> (instance-at fuel (str n "-v"))
                       (.then (fn [view-instance]
                                ((aget view-instance "view") next)
                                true))))))
        (.catch (fn [_] false)))))

(defn bisect
  "Smallest fuel in (lo, hi] at which the worst case completes."
  [lo hi]
  (if (<= (- hi lo) 1)
    (js/Promise.resolve hi)
    (let [mid (js/Math.floor (/ (+ lo hi) 2))]
      (-> (runs? mid)
          (.then (fn [ok] (if ok (bisect lo mid) (bisect mid hi))))))))

(-> (runs? ceiling)
    (.then
     (fn [reachable]
       (when-not reachable
         (println (str "REFUSING to report a fuel number: the worst case did not complete even at "
                       ceiling " units. Either the bounds are wrong or the guest does not"
                       " terminate on this input; a measurement that could not be taken"
                       " must not be reported as a cheap one."))
         (.rmSync fs tmp #js {:recursive true :force true})
         (js/process.exit 2))
       (bisect 0 ceiling)))
    (.then
     (fn [minimum]
       (let [needed (js/Math.ceil (* minimum margin))]
         (println "approval-queue-fuel: measured against the bounds the host admits")
         (println (str "  module                 " module-path))
         (println (str "  body bound (bytes)     " body-bytes))
         (println (str "  state bound (bytes)    " state-bytes))
         (println (str "  worst-case minimum     " minimum " fuel units"))
         (println (str "  margin                 " margin "x -> " needed " units recommended"))
         (println (str "  shipped in artifact    " shipped-fuel))
         (.rmSync fs tmp #js {:recursive true :force true})
         (cond
           (< shipped-fuel minimum)
           (do (println (str "\napproval-queue-fuel: FAIL -- the shipped artifact carries " shipped-fuel
                             " but the worst case this host admits needs " minimum
                             ". A body the host accepts would trap the guest."))
               (js/process.exit 1))

           (< shipped-fuel needed)
           (do (println (str "\napproval-queue-fuel: FAIL -- the shipped artifact carries " shipped-fuel
                             ", above the measured minimum " minimum " but below the " margin
                             "x margin (" needed "). Recompile with --fuel " needed " or state"
                             " why a thinner margin is right here."))
               (js/process.exit 1))

           :else
           (do (println (str "\napproval-queue-fuel: PASS -- " shipped-fuel " is "
                             (.toFixed (/ shipped-fuel minimum) 2)
                             "x the measured worst case at these bounds."))
               (js/process.exit 0))))))
    (.catch (fn [error]
              (println "approval-queue-fuel: REFUSING to report --" (.-message error))
              (js/process.exit 2))))
