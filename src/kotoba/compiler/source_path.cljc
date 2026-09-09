(ns kotoba.compiler.source-path
  (:require [clojure.string :as str]))

(def extensions
  "Closed source-discovery contract. Extensions select discovery intent only;
  they never select a runtime, weaken the Kotoba grammar, or imply JVM use."
  {".kotoba" :kotoba
   ".cljk" :clj-kotoba
   ".cljc" :portable-common})

(defn source-kind [path]
  (when (string? path)
    (some (fn [[extension kind]]
            (when (str/ends-with? path extension) kind))
          extensions)))

(defn admit! [path]
  (or (source-kind path)
      (throw (ex-info "source input must use .kotoba, .cljk, or .cljc"
                      {:phase :usage
                       :path path
                       :extensions (vec (sort (keys extensions)))})))
  path)

(defn admit-native-artifact!
  "Answer VALUE if it is a native artifact read from PATH, or refuse.

  `extract-native` does not read source. It reads the EDN artifact that
  `compile --output` writes, and its usage line says only `<file>` -- so the
  easiest wrong file to hand it is the `.kotoba` that produced the artifact.
  Handed that, nothing decided anything: the value flowed into `update`/`get`
  and died there with a protocol error that carried no `:phase`, which put it
  in the CLI's `:internal` bucket and answered `internal compiler error`,
  exit 70. That is the code reserved for the compiler breaking, and it was
  being spent on a caller naming the wrong file.

  Measured 2026-09-09 on the nbb route, before this function existed:

    amu extract-native examples/todo-app.kotoba --symbol main
    => {:error :internal, :message \"internal compiler error\"}   exit 70

  and underneath, discarded, `No protocol method IAssociative.-assoc defined
  for type object: (ns todo-app ...)`. Three separate inputs answered that way
  in one session and were read as one compiler defect blocking a migration;
  all three were this.

  ADR-2609081600 states the general rule -- a refusal may not guess its own
  reason. This is its dual: a refusal that HAD a decidable reason and declined
  to decide it. Both halves here are decided, not inferred. The extension is
  the closed contract this namespace already owns, so `source-kind` naming a
  file is a fact about the argument, not a guess about intent; and the shape
  test names the keys `extract-native` is about to read, so the refusal cannot
  outlive the code it protects."
  [value path]
  (when-let [kind (source-kind path)]
    (throw (ex-info "extract-native reads a compiled artifact, not a source file"
                    {:phase :decode
                     :path path
                     :source-kind kind
                     :expected "the EDN artifact written by `compile --output`"})))
  (when-not (map? value)
    (throw (ex-info "extract-native input did not read as a native artifact"
                    {:phase :decode
                     :path path
                     :expected "the EDN artifact written by `compile --output`"})))
  (let [missing (vec (remove #(contains? value %) [:exports :code]))]
    (when (seq missing)
      (throw (ex-info "extract-native input is missing native artifact keys"
                      {:phase :decode
                       :path path
                       :missing missing
                       :present (vec (sort (keys value)))}))))
  value)
