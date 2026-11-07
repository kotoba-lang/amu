;; Policy-shape controls; cryptographic verification is exercised separately.
;; Ported from test_verified_attestation.py.
(ns test-verified-attestation
  (:require [basilisp.test :refer [deftest is]]
            [verified-attestation :as v]))

(def base-policy (v/attestation-policy "kotoba-lang/amu" "1297097065" ".github/workflows/producer.yml"
                                       "refs/heads/main" (apply str (repeat 40 "a")) (apply str (repeat 40 "b")) "push"))
(def identity "https://github.com/kotoba-lang/amu/.github/workflows/producer.yml@refs/heads/main")
(def certificate
  {"issuer" "https://token.actions.githubusercontent.com" "subjectAlternativeName" identity
   "buildSignerURI" identity "buildSignerDigest" (apply str (repeat 40 "b"))
   "sourceRepositoryURI" "https://github.com/kotoba-lang/amu" "sourceRepositoryIdentifier" "1297097065"
   "sourceRepositoryDigest" (apply str (repeat 40 "a")) "sourceRepositoryRef" "refs/heads/main"
   "runnerEnvironment" "github-hosted" "buildTrigger" "push"})

(deftest every-certificate-field-is-required
  (v/validate base-policy)
  (is (v/certificate-matches? certificate base-policy))
  (doseq [k (keys certificate)]
    (is (not (v/certificate-matches? (assoc certificate k "untrusted") base-policy)) k)
    (is (not (v/certificate-matches? (dissoc certificate k) base-policy)) k)))

(deftest unbounded-policy-inputs-are-refused
  (doseq [[field value] [[:repository "kotoba-lang/amu/other"] [:repository-id "0"]
                         [:workflow ".github/workflows/../../producer.yml"] [:ref "refs/pull/1/merge"]
                         [:ref "refs/heads/../main"] [:ref "refs/heads/main//other"] [:ref "refs/heads/main.lock"]
                         [:source-sha (apply str (repeat 39 "a"))] [:signer-sha (apply str (repeat 39 "b"))]
                         [:trigger "pull_request"]]]
    (is (thrown? python/ValueError (v/validate (assoc base-policy field value))) (str field " " value))))

(deftest explicit-task-branch-is-not-main
  (let [branch (assoc base-policy :ref "refs/heads/codex/task-branch")]
    (v/validate branch)
    (is (not (v/certificate-matches? certificate branch)))))

(deftest nil-certificate-and-non-map-never-match
  (is (not (v/certificate-matches? nil base-policy)))
  (is (not (v/certificate-matches? "x" base-policy))))
