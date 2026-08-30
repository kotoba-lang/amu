(ns kotoba.compiler.logic-manifest-test
  (:require [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.logic-manifest :as logic]))

(def cid
  "bafkreihteekkh5xzrg6bat5mjthbtylimi36nifl62c2ladfyftplijcke")

(def input
  {:definition-cid cid
   :artifact-cid cid
   :compiler-contract cid
   :semantics-cid cid
   :world-cid cid
   :dependency-cids []
   :intent-schema-cids [cid]
   :resource-bounds {:limit/fuel 1000 :limit/memory-bytes 65536}})

(def compiled
  {:kir {:format :kotoba.kir/v3
         :effects #{[:cap/call 7] [:cap/call 4]}
         :functions [{:name 'main :effects #{[:cap/call 7]}}
                     {:name 'notify :effects #{[:cap/call 4]}}]}})

(deftest effects-come-only-from-checked-kir
  (let [manifest (logic/build! compiled input)]
    (is (logic/valid? manifest))
    (is (= #{:clock/now :http/post} (:effects manifest)))
    (is (= #{[:cap/call 7] [:cap/call 4]} (:wire-effects manifest)))
    (is (= :kotoba.logic-manifest/v1 (:format manifest)))
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"input is not exact"
                          (logic/build! compiled (assoc input :effects #{:kernel/format}))))))

(deftest manifest-projects-inert-provenance-separated-facts
  (let [manifest (logic/build! compiled input)
        evidence (logic/authorizer-evidence! cid manifest)
        facts (set (:facts evidence))]
    (is (= :kotoba.compiler-facts/v1 (:format evidence)))
    (is (contains? facts ["amu:definition" cid]))
    (is (contains? facts ["amu:requires" cid :clock/now]))
    (is (contains? facts ["amu:requires" cid :http/post]))
    (is (contains? facts ["amu:world" cid cid]))
    (testing "facts are data tuples, not executable list forms"
      (is (every? vector? (:facts evidence)))
      (is (every? string? (map first (:facts evidence)))))))

(deftest tampering-breaks-the-content-bound-manifest
  (let [manifest (logic/build! compiled input)]
    (is (false? (logic/valid? (assoc manifest :effects #{:kernel/format}))))
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"invalid logic manifest"
                          (logic/authorizer-facts
                           (assoc manifest :world-cid "not-a-cid"))))))

(deftest link-order-is-not-manifest-identity
  (let [other "bafkreigh2akiscaildcxmhjr7m6exfzucg5c44d6pnz3zqdvv2cesgbxmi"
        a (logic/build! compiled (assoc input :dependency-cids [cid other]))
        b (logic/build! compiled (assoc input :dependency-cids [other cid]))]
    (is (= (:manifest-sha256 a) (:manifest-sha256 b)))
    (is (= (:dependency-cids a) (:dependency-cids b)))))
