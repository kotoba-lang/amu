#!/usr/bin/env nbb
;; Admission-decision parity for cloud-itonami-app's
;; `oauth_resource_core.kotoba` -- the RFC 9728 protected-resource gate for
;; `GET /.well-known/oauth-protected-resource/mcp`. ADR-2608760000 addendum 2.
;;
;; THIS IS NOW A DELEGATOR. The harness -- compile, run both runtimes,
;; compare, the positive-admitted floor, cross-admission coverage, the
;; mutation hook -- lives once in `scripts/cloud-itonami-route-parity.cljs`,
;; and this route's battery (28 cases, verbatim as landed) lives in that
;; script's registry under the id `oauth-resource`. Addendum 2 itself called
;; for this extraction at the third route rather than a third copy of the
;; mechanism.
;;
;; Equivalent to:
;;   scripts/cloud-itonami-route-parity.cljs --route oauth-resource --app-dir <dir>
;;
;; Both floors this script introduced over addendum 1's are now enforced by
;; the harness FOR EVERY ROUTE, not just this one: the positive case must be
;; admitted by both runtimes (checked separately from mismatch counting), and
;; the detector is mutation-verified via `--mutant-replace` / `--mutant-with`.
(ns cloud-itonami-oauth-resource-parity
  (:require ["node:child_process" :as child]
            ["node:path" :as path]))

(def here (.dirname path *file*))
(def harness (.join path here "cloud-itonami-route-parity.cljs"))
(def nbb-cli (.join path here ".." "node_modules" "nbb" "cli.js"))

;; `--route oauth-resource` FIRST: the harness reads the first occurrence of
;; a flag, so this route cannot be overridden by a trailing `--route`.
(def result
  (.spawnSync child js/process.execPath
              (.concat #js [nbb-cli harness "--route" "oauth-resource"]
                       (.slice js/process.argv 2))
              #js {:stdio "inherit"}))

(when (.-error result) (throw (.-error result)))
(.exit js/process (or (.-status result) 70))
