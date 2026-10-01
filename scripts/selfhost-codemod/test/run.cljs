;; node --stack-size=4096 nbb/cli.js --classpath scripts/selfhost-codemod/src:scripts/selfhost-codemod/test scripts/selfhost-codemod/test/run.cljs
(ns run
  (:require [cljs.test :as t]
            [codemod.codemod-test]))

(t/run-tests 'codemod.codemod-test)
