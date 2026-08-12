#!/usr/bin/env nbb
(ns check-workflows
  (:require [clojure.string :as str]
            [scripts.lib :as lib]
            ["node:fs" :as fs]))

(def workflow-dir (lib/join lib/root ".github" "workflows"))
(def workflows
  (map #(lib/join workflow-dir %)
       (filter #(or (.endsWith % ".yml") (.endsWith % ".yaml"))
               (.readdirSync fs workflow-dir))))

(lib/ensure! (seq workflows) "workflow-lint: no workflows found")
(def action-count (volatile! 0))
(doseq [workflow workflows
        :let [text (lib/read-text workflow)]
        line (str/split-lines text)]
  (when-let [[_ action reference] (re-find #"^\s*-?\s*uses:\s*([^\s@]+)@([^\s#]+)" line)]
    (vswap! action-count inc)
    (lib/ensure! (boolean (re-matches #"[0-9a-f]{40}" reference))
                 (str "workflow-lint: action is not commit-pinned: " action "@" reference))))
(lib/ensure! (>= @action-count 6)
             "workflow-lint: expected action references were not inspected")

(let [repository-files
      (letfn [(walk [directory]
                (mapcat (fn [name]
                          (let [entry (lib/join directory name)
                                stat (.lstatSync fs entry)]
                            (cond
                              (.isSymbolicLink stat) []
                              (.isDirectory stat) (if (= name "node_modules") [] (walk entry))
                              :else [entry])))
                        (.readdirSync fs directory)))]
        (walk lib/root))
      shell-files (filter #(.endsWith % ".sh") repository-files)]
  (lib/ensure! (empty? shell-files)
               (str "workflow-lint: POSIX shell execution files found: " shell-files)))

(doseq [workflow workflows]
  (lib/ensure! (.includes (lib/read-text workflow) "node-version: \"24.12.0\"")
               (str "workflow-lint: Node runtime is not exactly pinned in " workflow)))
(let [test-workflow (lib/read-text (lib/join workflow-dir "test.yml"))]
  (lib/ensure! (.includes test-workflow "cli: 1.12.5.1654")
               "workflow-lint: Clojure CLI is not exactly pinned")
  (lib/ensure! (.includes test-workflow
                          "node scripts/ci-dependency-prefetch.mjs\n")
               "workflow-lint: provider dependency prefetch is missing")
  (lib/ensure! (.includes test-workflow
                          "node scripts/ci-dependency-prefetch.mjs --alias test")
               "workflow-lint: test dependency prefetch is missing")
  (lib/ensure! (.includes test-workflow "npm run test-ci-dependency-prefetch")
               "workflow-lint: dependency prefetch regression test is missing")
  (lib/ensure! (>= (count (re-seq #"npm run test-nbb-io" test-workflow)) 2)
               "workflow-lint: primary Node output publication test is missing from full or Windows CI")
  (lib/ensure! (.includes test-workflow "npm run test-nbb-classpath-hermetic")
               "workflow-lint: dependency lock digest gate is missing")
  (lib/ensure! (.includes test-workflow "npm run test-jdk-free-native")
               "workflow-lint: JDK-free native compiler conformance is missing")
  (lib/ensure! (.includes test-workflow "npm run test-policy-bound-provenance")
               "workflow-lint: policy-bound output provenance parity gate is missing"))

(doseq [name ["test.yml" "browser-matrix.yml"]
        :let [workflow (lib/read-text (lib/join workflow-dir name))]]
  (lib/ensure! (.includes workflow "push:\n    branches: [main]")
               (str "workflow-lint: feature-branch pushes duplicate pull-request CI in " name))
  (lib/ensure! (.includes workflow
                          "group: ${{ github.workflow }}-${{ github.event.pull_request.number || github.ref }}")
               (str "workflow-lint: missing ref-scoped concurrency group in " name))
  (lib/ensure! (.includes workflow "cancel-in-progress: true")
               (str "workflow-lint: superseded runs are not cancelled in " name)))

(println (str "workflow-lint: " (count workflows) " workflows and " @action-count
              " action references use commit pins, pinned toolchains, and deduplicated CI"))
