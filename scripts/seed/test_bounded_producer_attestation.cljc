;; Refuse untrusted event contexts before any artifact or verifier is opened.
;; Ported from test_bounded_producer_attestation.py.
(ns test-bounded-producer-attestation
  (:require [basilisp.test :refer [deftest is]]
            [check-bounded-producer-attestation :as c])
  (:import operator os))

(defn- with-env
  "Run f with os.environ replaced (clear=True semantics) by `env`, restoring afterwards."
  [env f]
  (let [saved (python/dict os/environ)]
    (.clear os/environ)
    (try
      (doseq [[k v] env] (operator/setitem os/environ k v))
      (f)
      (finally
        (.clear os/environ)
        (.update os/environ saved)))))

(def trusted {"GITHUB_REPOSITORY" "kotoba-lang/amu" "GITHUB_REPOSITORY_ID" "1297097065"
              "GITHUB_REF" "refs/heads/main" "GITHUB_EVENT_NAME" "push" "GITHUB_SHA" (apply str (repeat 40 "a"))})

(deftest untrusted-contexts-refuse-before-io
  (doseq [[name value] [["GITHUB_REPOSITORY" "other/amu"] ["GITHUB_REPOSITORY_ID" "1"]
                        ["GITHUB_REF" "refs/pull/1/merge"] ["GITHUB_EVENT_NAME" "pull_request"]
                        ["GITHUB_SHA" "invalid"]]]
    (is (with-env (assoc trusted name value)
          #(try (c/main "/nonexistent/artifact" "/nonexistent/gh") false
                (catch python/ValueError _ true)))
        name)))
