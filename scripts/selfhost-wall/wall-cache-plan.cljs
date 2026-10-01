;; bootstrap-tooling
;; BOOTSTRAP scaffolding: runs kotoba.compiler.wall-cache/plan (pure, Kotoba-checkable) under nbb, stdin -> stdout.
;; The product driver is the Kotoba-built binary of the same module; scan-cached.sh takes it through WALL_PLAN.
;; Missing for that: a Kotoba `main` with stdin/stdout abilities for a native build of wall_cache.cljk (see
;; docs/selfhost-wall-cache.md).
(ns wall-cache-plan
  (:require ["node:fs" :as fs]
            [kotoba.compiler.wall-cache :as w]))
(.writeSync fs 1 (w/plan (.readFileSync fs 0 "utf8")))
