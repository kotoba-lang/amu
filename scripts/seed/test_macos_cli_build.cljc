;; Source inventory regression; does not execute the compiler or qualify pins.
(ns test-macos-cli-build
  (:require [basilisp.test :refer [deftest is]]
            [gate-util :as u]
            [macos-cli-build :as build])
  (:import operator))

(deftest source-report-includes-only-declared-sources
  (let [root u/root
        names ["seed/00-ns-static.kotoba" "seed/19-decimal.kotoba"]
        expected (set (concat names ["seed/macos-cli-api.kotoba" "seed/runtime/llm-v1-wire.kotoba"
                                     "seed/macos-cli-murakumo.kotoba" "seed/macos-cli-llm.kotoba" "seed/macos-cli.kotoba"]))
        report (build/source-report root names)
        missing (.copy report)
        extra (.copy report)]
    (is (= expected (set (.keys report))))
    (.pop missing "seed/19-decimal.kotoba")
    (operator/setitem extra ".agent-output/repin/macos-cli-pins.kotoba" (get report "seed/19-decimal.kotoba"))
    (is (not (u/deq report missing)))
    (is (not (u/deq report extra)))))
