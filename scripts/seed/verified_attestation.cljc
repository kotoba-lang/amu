;; Verify GitHub provenance before using a sealed artifact.
;;
;; The policy and gh image pin must be selected by a trusted host, never by the
;; artifact or a PR-controlled manifest. This is a transport/identity check; it
;; does not validate compiler input closure or confer native admission.
;; Ported from verified_attestation.py (Basilisp). The policy is a map with the keys
;; :repository :repository-id :workflow :ref :source-sha :signer-sha :trigger (all strings).
(ns verified-attestation
  (:require [basilisp.string :as str]
            [sealed-image :as sealed])
  (:import json operator os re subprocess tempfile))

(defn attestation-policy
  [repository repository-id workflow ref source-sha signer-sha trigger]
  {:repository repository :repository-id repository-id :workflow workflow :ref ref
   :source-sha source-sha :signer-sha signer-sha :trigger trigger})

(defn- invalid [message] (python/ValueError message))

(defn validate
  "Throws ValueError unless the policy is a bounded, well formed one."
  [policy]
  (when-not (re/fullmatch "[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+" (:repository policy)) (throw (invalid "invalid repository")))
  (when-not (re/fullmatch "[1-9][0-9]*" (:repository-id policy)) (throw (invalid "invalid repository ID")))
  (when-not (re/fullmatch "\\.github/workflows/[A-Za-z0-9_.-]+\\.ya?ml" (:workflow policy)) (throw (invalid "invalid workflow")))
  (let [ref (:ref policy)
        branch (if (str/starts-with? ref "refs/heads/") (subs ref (count "refs/heads/")) ref)]
    (when (or (not (str/starts-with? ref "refs/heads/"))
              (not (re/fullmatch "[A-Za-z0-9_-][A-Za-z0-9_.-]*(?:/[A-Za-z0-9_-][A-Za-z0-9_.-]*)*" branch))
              (str/includes? branch "..")
              (some #(or (str/ends-with? % ".") (str/ends-with? % ".lock")) (.split branch "/")))
      (throw (invalid "invalid source ref"))))
  (doseq [value [(:source-sha policy) (:signer-sha policy)]]
    (when-not (re/fullmatch "[0-9a-f]{40}" value) (throw (invalid "invalid source or signer SHA"))))
  (when-not (contains? #{"push" "schedule" "workflow_dispatch"} (:trigger policy))
    (throw (invalid "invalid trigger"))))

(defn- identity-of [policy]
  (str "https://github.com/" (:repository policy) "/" (:workflow policy) "@" (:ref policy)))

(defn certificate-matches? [certificate policy]
  (let [identity (identity-of policy)
        expected {"issuer" "https://token.actions.githubusercontent.com"
                  "subjectAlternativeName" identity
                  "buildSignerURI" identity
                  "buildSignerDigest" (:signer-sha policy)
                  "sourceRepositoryURI" (str "https://github.com/" (:repository policy))
                  "sourceRepositoryIdentifier" (:repository-id policy)
                  "sourceRepositoryDigest" (:source-sha policy)
                  "sourceRepositoryRef" (:ref policy)
                  "runnerEnvironment" "github-hosted"
                  "buildTrigger" (:trigger policy)}]
    (and (map? certificate)
         (every? (fn [[k v]] (and (contains? certificate k) (= v (get certificate k)))) expected))))

(defn- from-py [x]
  (cond (instance? python/dict x) (into {} (map (fn [[k v]] [k (from-py v)])) (.items x))
        (instance? python/list x) (mapv from-py x)
        :else x))

(defn- verified-rows-match? [stdout policy artifact-digest]
  (try
    (let [rows (from-py (json/loads stdout))]
      (boolean
        (and (sequential? rows)
             (some (fn [row]
                     (let [result (get row "verificationResult")]
                       (and (certificate-matches? (get-in result ["signature" "certificate"]) policy)
                            (some #(= artifact-digest (get-in % ["digest" "sha256"]))
                                  (get-in result ["statement" "subject"])))))
                   rows))))
    (catch python/Exception _ false)))

(defn with-verified-artifact*
  "Private: verifier-test-args supports offline cryptographic test fixtures; the public entry passes []."
  [path gh gh-sha256 policy verifier-test-args f]
  (validate policy)
  (sealed/with-sealed-blob path
    (fn [artifact-fd artifact-digest]
      (sealed/with-sealed-image gh gh-sha256
        (fn [gh-fd _]
          (let [identity (identity-of policy)
                args (vec (concat [(str "/proc/self/fd/" gh-fd) "attestation" "verify" (str "/proc/self/fd/" artifact-fd)
                                   "--repo" (:repository policy) "--cert-identity" identity
                                   "--source-ref" (:ref policy) "--source-digest" (:source-sha policy)
                                   "--signer-digest" (:signer-sha policy) "--deny-self-hosted-runners" "--format" "json"]
                                  verifier-test-args))
                result (with-open [config (tempfile/TemporaryDirectory ** :prefix "kotoba-gh-")]
                         (let [env (python/dict {"PATH" "/usr/bin:/bin" "GH_HOST" "github.com" "GH_PROMPT_DISABLED" "1"
                                                 "HOME" config "GH_CONFIG_DIR" config})]
                           (when (contains? os/environ "GH_TOKEN") (operator/setitem env "GH_TOKEN" (operator/getitem os/environ "GH_TOKEN")))
                           (subprocess/run (python/list args) ** :env env :capture_output true :timeout 120
                                           :pass_fds (python/tuple [gh-fd artifact-fd]))))]
            (when (not= 0 (.-returncode result)) (throw (invalid "attestation verification failed")))
            (when-not (verified-rows-match? (.-stdout result) policy artifact-digest)
              (throw (invalid "attestation certificate or subject mismatch")))
            (os/lseek artifact-fd 0 os/SEEK_SET)
            (f artifact-fd artifact-digest)))))))

(defn with-verified-artifact
  "Calls (f fd sha256); only the sealed fd is verified and may be used.

  Attestations are fetched online from GitHub for the current repository ID.
  No caller-provided bundle, cache record, or predicate is an authority."
  [path gh gh-sha256 policy f]
  (with-verified-artifact* path gh gh-sha256 policy [] f))
