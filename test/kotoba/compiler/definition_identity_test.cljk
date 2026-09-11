(ns kotoba.compiler.definition-identity-test
  "ADR 0300. What a definition CID is allowed to depend on, and what it is not.

  Every case here is a claim about the SEALED payload, so each one is written
  as a pair: two modules that must agree, or two that must differ. A test that
  only asserts a CID is a well-formed string would pass for an identity that
  hashed the source text.

  The genuinely JVM-only quarter of this coverage, after the 2026-09-08 split:
  `profile-version-matches-the-grammar-authority` and
  `desugar-contract-version-matches-the-elaboration-pipeline-authority` read a
  classpath resource through `io/resource`/`slurp` (nbb has no classpath
  reader), `provenance-carries-the-definition-graph` requires
  `kotoba.compiler.core`, which is `.clj`-only by construction, and
  `abort-now-reaches-the-sealed-row` keeps only its first `testing` block,
  which reads `test/nbb/fixtures/abort-callee.kotoba` through `io/file`/
  `slurp`. Its second block -- the with/without-`:abort` CID comparison,
  synthetic and file-free -- moved to
  `kotoba.compiler.definition-identity-portable-test` (.cljc) as
  `abort-is-sealed-with-and-without-the-ability`, registered on both hosts.
  Every other deftest that lived in this namespace moved there unchanged; see
  that file for the rest of ADR 0300's coverage."
  (:require [clojure.edn :as edn]
            [clojure.java.io :as io]
            [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]
            [kotoba.compiler.definition-identity :as di]
            [kotoba.kir :as ir]
            [kotoba.sema :as sema]))

(defn- report [source]
  (let [hir (sema/analyze source {})]
    (di/definitions hir (ir/lower hir))))

(defn- cids [source]
  (into {} (map (fn [[k v]] [k (:cid v)])) (:entries (report source))))

(def ^:private base
  (str "(ns d (:export [main]))\n"
       "(defn helper [a] (+ a 2))\n"
       "(defn main [] (helper 3))\n"))

;; ---------------------------------------------------------------------------
;; Refusals are answers, and they are not CIDs

(deftest abort-now-reaches-the-sealed-row
  (testing "MEASURED 2026-09-02, and this test was the opposite assertion until
  then. `:abort` was refused as `not a wire capability call`, and these tests
  used an aborting fixture to reach the refusal markers. kotoba-kir d082a57
  made control effects bridge through unchanged: `:abort` has no capability and
  no wire id because there is no numeric ABI behind a control effect, but the
  difference between a function that can leave its caller by aborting and one
  that cannot is semantic -- their interfaces are `[:result T E]` against `T` --
  so it must reach the sealed row. Restating the old refusal here would be
  asserting something the upstream change deliberately made false."
    (let [entries (:entries (report (slurp (io/file "test/nbb/fixtures/abort-callee.kotoba"))))]
      (is (every? string? (map :cid (vals entries)))
          "every definition in an aborting module is identified")
      (is (every? nil? (map :definition-cid (vals entries)))
          "and none of them carries a refusal marker"))))

;; ---------------------------------------------------------------------------
;; The two version constants

(deftest profile-version-matches-the-grammar-authority
  (testing "the constant exists because the authority is a JVM classpath
  resource and the nbb route has no classpath reader. This is the assertion
  that makes it a copy rather than a guess."
    (let [grammar (edn/read-string
                   (slurp (io/resource "kotoba/lang/guest-grammar.edn")))]
      (is (= (:kotoba.lang.guest-grammar/profile-version grammar)
             di/profile-version)
          "bump `kotoba.compiler.definition-identity/profile-version` with the
          grammar, and expect every definition CID to move -- that is what the
          sealed input means"))))

(deftest desugar-contract-version-matches-the-elaboration-pipeline-authority
  (testing "was `desugar-contract-version-is-pinned-because-no-authority-
  declares-one`, and the gap that named it was mis-stated. kotoba-lang
  lang/elaboration-pipeline.edn [:contract-versions :desugar-contract] had
  declared this number since W0 and had read 2 since 2026-09-01, when `eval`
  moved out of :forbidden-heads and into the desugar table. So the compiler was
  not sealing an unowned number; it was sealing a STALE one, and two definitions
  compiled either side of a desugar change claimed one identity. This is now the
  same assertion profile-version has: read the resource, compare the constant."
    (let [pipeline (edn/read-string
                    (slurp (io/resource "kotoba/lang/elaboration-pipeline.edn")))]
      (is (= (get-in pipeline [:contract-versions :desugar-contract])
             di/desugar-contract-version)
          "bump `kotoba.compiler.definition-identity/desugar-contract-version`
          with the authority, and expect every definition CID to move -- that is
          what the sealed input means"))))

;; ---------------------------------------------------------------------------
;; Provenance

(deftest provenance-carries-the-definition-graph
  (let [result (compiler/compile-source base :wasm32-kotoba-v1)
        definitions (get-in result [:provenance :definitions])]
    (is (= :kotoba.definition-identity/v1 (:contract definitions)))
    (is (= (cids base) (into {} (map (fn [[k v]] [k (:cid v)])) (:entries definitions))))
    (is (= ["helper" "main"] (:order definitions)))))
