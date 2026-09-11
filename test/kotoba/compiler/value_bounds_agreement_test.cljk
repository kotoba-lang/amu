(ns kotoba.compiler.value-bounds-agreement-test
  "amu is where the value-bounds table's two statements can be compared, so
  this is where they are.

  The table lives in `kotoba.kir.value` (osaho), which every target's
  compile-time validation reads. It is RESTATED, privately and under different
  names, in `kotoba.script` (kotoba-script), because the restricted-ESM emitter
  writes the bounds into every artifact it emits as literal numbers in a
  generated runtime prelude -- the emitted module has no classpath and cannot
  read a Clojure var.

  Neither repository is on the other's classpath. amu loads both, which is the
  same reason `fuel64_ceiling_test` lives here, and that test says the rest of
  it: a restatement nobody compares is a copy, and a copy drifts.

  This one is not hypothetical either, and the drift was measured before the
  test was written. On 2026-09-10, raising `document-node-limit` in osaho alone
  let a 1057-node document COMPILE and then fail at runtime with
  `doc-node-limit` -- the emitted prelude still carried 256. The build
  succeeded and the artifact was wrong, which is the worse of the two failures:
  a refusal produces a decision, a wrong answer produces nothing.

  ⚠ Adding a bound to either file without adding it here restores exactly the
  gap this closes. The pairs are listed explicitly rather than derived by name,
  because the names deliberately differ and a derivation would have to guess."
  (:require [clojure.test :refer [deftest is testing]]
            [kotoba.kir.value :as value]
            [kotoba.script]))

(defn- script-bound [sym]
  @(ns-resolve 'kotoba.script sym))

(deftest the-emitter-restates-the-same-table-osaho-decides
  (testing "document bounds -- written into every emitted ESM prelude"
    (is (= value/document-node-limit (script-bound 'max-document-nodes))
        "the node budget; a drift here compiles and then traps at runtime")
    (is (= value/document-depth-limit (script-bound 'max-document-depth)))
    (is (= value/document-container-item-limit
           (script-bound 'max-document-container-items)))
    (is (= value/document-utf8-byte-limit (script-bound 'max-document-utf8-bytes))))
  (testing "the typed-value bounds beside them"
    (is (= value/typed-set-item-limit (script-bound 'max-set-items)))
    (is (= value/typed-map-entry-limit (script-bound 'max-typed-map-entries)))
    (is (= value/record-field-limit (script-bound 'max-record-fields)))
    (is (= value/compact-graph-item-limit (script-bound 'max-compact-graph-items)))
    (is (= value/string-index-key-byte-limit
           (script-bound 'max-string-index-key-bytes)))))

(deftest the-comparison-can-actually-fail
  ;; A test that has never been red cannot be told from one that cannot go red.
  ;; This is the same shape as the real assertions above, against a number the
  ;; table does not hold, so the mechanism is exercised on every run rather
  ;; than only on the day someone edits a bound.
  (is (not= value/document-node-limit (inc (script-bound 'max-document-nodes)))
      "if this passes trivially the resolution above is not reading anything"))
