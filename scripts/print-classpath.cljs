#!/usr/bin/env nbb
;; Print the dependency directories `bin/kotoba`'s nbb fast path needs, one
;; per line, resolved from `deps-lock.edn` with git alone.
;;
;; Separate from `kotoba.compiler.nbb.classpath` so that namespace stays
;; require-able (and therefore testable) without running anything on load.
;;
;;   nbb --classpath src scripts/print-classpath.cljs [root]

(ns print-classpath
  (:require [kotoba.compiler.nbb.classpath :as classpath]))

(apply classpath/-main *command-line-args*)
