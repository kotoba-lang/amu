;; Hermetic controls for the Git-tree source revision audit. Ported from test-audit-descriptor-source-revision.py
;; (Basilisp, JUN-974). Each test builds an isolated scratch repository and points the audit at it.
;; Run: PYTHONPATH=scripts/seed basilisp test --rootdir scripts/seed scripts/seed/test_audit_descriptor_source_revision.cljc
(ns test-audit-descriptor-source-revision
  (:require [basilisp.test :refer [deftest is]]
            [audit-descriptor-source-revision :as audit]
            [gate-util :as u])
  (:import json operator pathlib subprocess tempfile))

(defn with-tmp [prefix f]
  (let [d (tempfile/TemporaryDirectory ** :prefix prefix)
        name (.__enter__ d)]
    (try (f (pathlib/Path name)) (finally (.__exit__ d nil nil nil)))))

(defn git [root & args]
  (.strip (.decode (.-stdout (subprocess/run (python/list (concat ["git" "-C" (str root)] args)) ** :check true
                                             :stdout subprocess/PIPE :stderr subprocess/PIPE)))))

(defn commit! [root message]
  (git root "add" ".")
  (git root "commit" "--quiet" "-m" message)
  (git root "rev-parse" "HEAD"))

(defn rj [p] (json/loads (.read_text p)))
(defn wj [p d] (.write_text p (json/dumps d)))
(defn gi [m k] (operator/getitem m k))
(defn status [result] (gi result "status"))
(defn put-bytes [root rel s] (.write_bytes (pathlib/Path root rel) (.encode s)))
(defn raises-type? [t f] (try (f) false (catch python/Exception e (instance? t e))))

(defn with-fixture [f]
  (with-tmp "amu-source-audit-"
    (fn [root]
      (let [old @audit/root]
        (reset! audit/root root)
        (try
          (git root "init" "--quiet")
          (git root "config" "user.name" "Test")
          (git root "config" "user.email" "test@example.invalid")
          (.mkdir (pathlib/Path root "seed"))
          (put-bytes root "seed/00-test.kotoba" "first\n")
          (.write_text (pathlib/Path root "seed/FULL-MANIFEST") "seed/00-test.kotoba\n")
          (let [source (commit! root "source")
                descriptor (u/pydict "sourceRevision" source "sourceManifest" "seed/FULL-MANIFEST" "sourceModuleCount" 1
                                     "sourceUnity" (u/pydict "bytes" 7 "sha256" (u/sha256-hex (.encode "first\n\n"))))
                _ (wj (pathlib/Path root "native-product.json") descriptor)
                good (commit! root "descriptor")
                _ (put-bytes root "seed/00-test.kotoba" "second\n")
                changed (commit! root "changed source")]
            (f {:root root :source source :good good :changed changed}))
          (finally (reset! audit/root old)))))))

(deftest expected-source-matches-but-is-not-provenance
  (with-fixture
    (fn [{:keys [good]}]
      (let [result (audit/audit good nil)]
        (is (= (status result) "MATCH"))
        (is (true? (gi result "comparedDeclaredSourceRevision")))
        (is (false? (gi result "compilerBuildProvenanceVerified")))
        (is (false? (gi result "publicReleaseQualified")))))))

(deftest matching-other-revision-does-not-claim-declared-revision-was-checked
  (with-fixture
    (fn [{:keys [good source]}]
      (let [result (audit/audit good good)]
        (is (= (status result) "MATCH"))
        (is (false? (gi result "comparedDeclaredSourceRevision")))
        (is (= (gi result "descriptorSourceRevision") source))))))

(deftest null-declared-revision-audits-the-descriptor-commit
  (with-fixture
    (fn [{:keys [root]}]
      (let [p (pathlib/Path root "native-product.json")
            descriptor (rj p)]
        (operator/setitem descriptor "sourceRevision" nil)
        (wj p descriptor)
        (put-bytes root "seed/00-test.kotoba" "first\n")
        (let [implicit (commit! root "regenerated descriptor")
              result (audit/audit implicit nil)]
          (is (= (status result) "MATCH"))
          (is (true? (gi result "sourceRevisionImplicit")))
          (is (= (gi result "sourceRevisionTested") implicit))
          (put-bytes root "seed/00-test.kotoba" "third\n")
          (let [stale (commit! root "source without regenerated descriptor")]
            (is (= (status (audit/audit stale nil)) "MISMATCH"))))))))

(deftest changed-source-does-not-match
  (with-fixture
    (fn [{:keys [good changed]}]
      (let [result (audit/audit good changed)]
        (is (= (status result) "MISMATCH"))
        (is (false? (gi result "comparedDeclaredSourceRevision")))
        (is (not (u/deq (gi result "expectedUnity") (gi result "actualUnity"))))))))

(deftest replacement-refs-do-not-change-audited-commit-bytes
  (with-fixture
    (fn [{:keys [root source changed good]}]
      (let [original (git root "rev-parse" (str source ":seed/00-test.kotoba"))
            replacement (git root "rev-parse" (str changed ":seed/00-test.kotoba"))]
        (git root "replace" original replacement)
        (is (= (git root "show" (str source ":seed/00-test.kotoba")) "second"))
        (is (= (status (audit/audit good nil)) "MATCH"))))))

(deftest mutable-or-missing-revision-refused
  (with-fixture
    (fn [{:keys [good]}]
      (is (raises-type? python/ValueError #(audit/audit "HEAD" nil)))
      (is (raises-type? subprocess/CalledProcessError #(audit/audit good (apply str (repeat 40 "0"))))))))

(deftest shallow-checkout-without-source-commit-is-refused
  (with-fixture
    (fn [{:keys [root changed]}]
      (with-tmp "amu-source-audit-shallow-"
        (fn [parent]
          (let [clone (pathlib/Path parent "checkout")]
            (subprocess/run (python/list ["git" "clone" "--quiet" "--no-local" "--depth=1" (str root) (str clone)]) ** :check true :capture_output true)
            (reset! audit/root clone)
            (is (raises-type? subprocess/CalledProcessError #(audit/audit changed nil)))))))))

(deftest partial-clone-missing-blob-is-refused-without-lazy-fetch
  (with-fixture
    (fn [{:keys [root good]}]
      (git root "config" "uploadpack.allowFilter" "true")
      (with-tmp "amu-source-audit-partial-"
        (fn [parent]
          (let [clone (pathlib/Path parent "checkout")
                present? (fn [] (= (.-returncode (subprocess/run (python/list ["git" "--no-lazy-fetch" "-C" (str clone) "cat-file" "-e" (str good ":native-product.json")])
                                                                  ** :capture_output true)) 0))]
            (subprocess/run (python/list ["git" "clone" "--quiet" "--filter=blob:none" "--no-checkout" (.as_uri root) (str clone)]) ** :check true :capture_output true)
            (is (not (present?)) "fixture must omit the descriptor blob")
            (reset! audit/root clone)
            (is (raises-type? subprocess/CalledProcessError #(audit/audit good nil)))
            (is (not (present?)) "audit must not fetch the missing blob")))))))

(deftest duplicate-or-unsafe-manifest-refused
  (with-fixture
    (fn [{:keys [root]}]
      (doseq [text ["seed/00-test.kotoba\nseed/00-test.kotoba\n" "seed/../secret.kotoba\n"]]
        (.write_text (pathlib/Path root "seed/FULL-MANIFEST") text)
        (let [p (pathlib/Path root "native-product.json")
              descriptor (rj p)]
          (operator/setitem descriptor "sourceModuleCount" (python/len (.splitlines text)))
          (wj p descriptor)
          (let [rev (commit! root "invalid manifest")]
            (is (raises-type? python/ValueError #(audit/audit rev nil)))))))))
