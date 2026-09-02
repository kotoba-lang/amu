(ns kotoba.compiler.nbb.project-source
  "How a compile's source text is found: one file, a path-resolved closed
  graph, or a CID-pinned one.

  This lived inside `kotoba.compiler.nbb.wasm-cli`, which is why project mode
  was a Wasm-only capability on the JDK-free route. Nothing in it is
  Wasm-specific -- `kotoba.compiler.project/link-source` is portable `.cljc`
  and both resolvers beneath it already were -- so the native driver refused a
  module that declared `(:require ...)` for no reason other than where the
  function was written. Measured 2026-09-02 against a two-module fixture on
  `x86_64-aiueos-kernel-v1`: `--source-path` and `--unpinned` were BOTH read
  and BOTH ignored, and the refusal was byte-identical to the one you get with
  neither flag (`:kotoba.error/namespace-require-needs-project`) -- an
  invocation naming its source roots and one that did not got the same answer.

  Not in `cli-support`: `link-source` requires `kotoba.sema`, and that
  namespace deliberately keeps the frontend out of its load closure so
  `output-set-cli` does not pay 15.8s to verify a signature. Both drivers that
  require this one already load `kotoba.sema`."
  (:require [kotoba.compiler.nbb.cli-support :as support]
            [kotoba.compiler.nbb.io :as io]
            [kotoba.compiler.nbb.module-lock :as module-lock]
            [kotoba.compiler.nbb.project-files :as project-files]
            [kotoba.compiler.project :as project]))

(defn analyze-opts
  "Frontend options for a compile whose source may have been linked.

  A linked unit contains forms no author wrote -- import stubs, project
  dispatchers, export wrappers -- so the frontend must be told to admit them.
  Passing an unlinked options map for a linked source does not produce a
  wrong artifact; it produces a refusal that names a synthetic form, which
  reads as a defect in the author's module."
  [policy linked?]
  (cond-> (support/analyze-options policy)
    linked? (assoc :admit-linked-synthetics? true)))

(defn resolve-source!
  "Answer the source text to compile and whether it came from a linked graph.

  A guest that declares `(:require ...)` is a module of a project, so it is
  read as a closed graph from the explicit `--source-path` roots and linked
  into one bounded unit by `project/link-source` -- the same linker the JVM
  path uses.

  `--module-lock` is the same shape with the resolution step replaced. The
  lock names every module in the closed graph by CID and the bytes are
  rejected unless they hash to the name they were asked for, so nothing is
  found by searching a path. Both resolvers hand the same `{:sources :root}`
  to the same `project/link-source`; only whether the finding was verified
  differs. The two are mutually exclusive here rather than combined: a lock
  that fell back to a path search for anything it did not pin would be a lock
  in name only.

  Reads no policy: the caller owns when policy is decoded, and that ordering
  is load-bearing for the artifact cache."
  [args]
  (let [lock-path (support/option args "--module-lock")
        source-roots (support/options args "--source-path")]
    (cond
      lock-path
      (let [blocks (or (support/option args "--blocks")
                       (support/usage-error! "--module-lock requires --blocks <dir>"))
            graph (support/timed
                   "module-lock-load"
                   #(module-lock/load-locked-graph lock-path blocks))
            linked (support/timed "project-link"
                                  #(project/link-source (:sources graph) (:root graph)))]
        {;; A pinned build has no input PATH to name the artifact after --
         ;; that is the point -- so the root namespace does, exactly as the
         ;; JVM CLI does it.
         :input (str (:root graph))
         :source (:source linked)
         :linked? true
         :lock {:module-lock lock-path :lock-cid (:lock-cid graph)}
         :project {:root (:root graph)
                   :module-order (:module-order linked)
                   :modules (:modules graph)
                   :lock-cid (:lock-cid graph)}})

      (seq source-roots)
      (let [input (support/timed "source-admit" #(support/source! (second args)))
            graph (support/timed "project-load"
                                 #(project-files/load-closed-graph input source-roots))
            linked (support/timed "project-link"
                                  #(project/link-source (:sources graph) (:root graph)))]
        {:input input
         :source (:source linked)
         :linked? true
         :project {:root (:root graph)
                   :module-order (:module-order linked)
                   :paths (:paths graph)}})

      :else
      (let [input (support/timed "source-admit" #(support/source! (second args)))]
        {:input input
         :source (support/timed "source-read" #(io/read-text-file input))
         :linked? false}))))

(defn inputs-record
  "How the inputs were found, in the compile's answer rather than only in the
  shell history. The JVM CLI writes this beside the artifact as
  `.inputs.edn`; this route cannot, because its output set is a two-file
  commit marker and a third member would make every artifact fail its own
  verification. `:lock-cid` is the value that actually identifies the pinned
  input set, which the JVM's record also carries."
  [resolved]
  (if-let [lock (:lock resolved)]
    {:kotoba.compile/inputs :module-lock
     :module-lock (:module-lock lock)
     :lock-cid (:lock-cid lock)}
    {:kotoba.compile/inputs (if (:linked? resolved)
                              :unpinned-source-path
                              :single-file)}))
