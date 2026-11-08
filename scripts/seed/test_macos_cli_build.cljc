;; Source inventory regression; does not execute the compiler or qualify pins.
(ns test-macos-cli-build
  (:require [basilisp.test :refer [deftest is]]
            [gate-util :as u]
            [macos-cli-build :as build])
  (:import operator pathlib))

(deftest source-report-excludes-generated-pins-independent-of-work-directory
  (let [root u/root
        names ["seed/00-ns-static.kotoba" "seed/19-decimal.kotoba"]
        inside (.joinpath root ".agent-output/repin/macos-cli-pins.kotoba")
        outside (.joinpath (.-parent root) "repin-outside/macos-cli-pins.kotoba")
        prefix-trick (pathlib/Path (str root "-other/macos-cli-pins.kotoba"))
        expected (set (concat names ["seed/macos-cli-api.kotoba" "seed/macos-cli.kotoba"]))]
    (doseq [pins [inside outside prefix-trick]]
      (let [inputs (build/cli-input-paths root names pins)
            declared (:declared inputs)
            assembly (:assembly inputs)
            report (build/source-report root inputs)
            missing (.copy report)
            extra (.copy report)]
        (is (= expected (set (.keys report))))
        (is (= (concat (take 2 declared) [(nth declared 2) pins (nth declared 3)]) assembly))
        (.pop missing "seed/19-decimal.kotoba")
        (operator/setitem extra ".agent-output/repin/macos-cli-pins.kotoba" (get report "seed/19-decimal.kotoba"))
        (is (not (u/deq report missing)))
        (is (not (u/deq report extra)))))))
