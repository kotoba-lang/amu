#!/usr/bin/env nbb
;; Admission-decision parity for cloud-itonami-app's `health_core.kotoba`
;; (`GET /health`), ADR-2608760000 addendum 1.
;;
;; THIS IS NOW A DELEGATOR. The harness -- compile, run both runtimes,
;; compare, the positive-admitted floor, cross-admission coverage, the
;; mutation hook -- lives once in `scripts/cloud-itonami-route-parity.cljs`,
;; and this route's battery (21 cases, verbatim as landed) lives in that
;; script's registry under the id `health`. ADR-2608760000 addendum 2 called
;; for exactly this at the third route rather than a third copy.
;;
;; Equivalent to:
;;   scripts/cloud-itonami-route-parity.cljs --route health --app-dir <dir>
;;
;; The entry point is kept because addenda 1 and 2 name it, and because the
;; harness reports under this script's original label so the output is
;; unchanged. What is NOT kept is a second implementation of the mechanism.
(ns cloud-itonami-health-parity
  (:require ["node:child_process" :as child]
            ["node:path" :as path]))

(def here (.dirname path *file*))
(def harness (.join path here "cloud-itonami-route-parity.cljs"))
(def nbb-cli (.join path here ".." "node_modules" "nbb" "cli.js"))

;; `--route health` FIRST: the harness reads the first occurrence of a flag,
;; so this route cannot be overridden by a trailing `--route`.
(def result
  (.spawnSync child js/process.execPath
              (.concat #js [nbb-cli harness "--route" "health"]
                       (.slice js/process.argv 2))
              #js {:stdio "inherit"}))

(when (.-error result) (throw (.-error result)))
(.exit js/process (or (.-status result) 70))
