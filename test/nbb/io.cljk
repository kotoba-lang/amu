(ns test.nbb.io
  "Behavioral regression tests for the primary Node compiler's publication
  boundary. Runs directly on NBB so no JVM implementation can satisfy these
  assertions accidentally."
  (:require ["node:fs" :as fs]
            ["node:os" :as os]
            ["node:path" :as path]
            [cljs.reader :as reader]
            [kotoba.compiler.nbb.io :as io]
            [kotoba.compiler.nbb.output-set :as output-set]))

(def failures (atom 0))

(defn- check [label ok?]
  (if ok?
    (println "PASS" label)
    (do (println "FAIL" label) (swap! failures inc))))

(defn- temporary-entries [dir]
  (filter #(.startsWith % ".kotoba-output-") (.readdirSync fs dir)))

(let [dir (.mkdtempSync fs (.join path (.tmpdir os) "amu-output-test-"))
      target (.join path dir "program.kexe")
      referent (.join path dir "referent")
      linked (.join path dir "linked.kexe")]
  (try
    (io/write-bytes! target (.from js/Buffer #js [0 1 2 255]))
    (check "binary output is published byte-for-byte"
           (.equals (.readFileSync fs target) (.from js/Buffer #js [0 1 2 255])))
    (check "successful publication removes its private temporary location"
           (empty? (temporary-entries dir)))

    (io/write-text! target "replacement")
    (check "an existing artifact is atomically replaced"
           (= "replacement" (.readFileSync fs target "utf8")))
    (check "bounded verifier reads exact regular-file bytes"
           (= "replacement"
              (.toString (io/read-bounded-bytes-file target 32) "utf8")))
    (check "bounded verifier rejects an oversized member before reading"
           (= :verify
              (try (io/read-bounded-bytes-file target 4) :no-error
                   (catch :default error (:phase (ex-data error))))))

    (let [reason (try (io/write-bytes! target nil) :no-error
                      (catch :default error (:reason (ex-data error))))]
      (check "a failed write reports the write phase" (= :write reason))
      (check "a failed write preserves the prior artifact"
             (= "replacement" (.readFileSync fs target "utf8")))
      (check "a failed write removes its private temporary location"
             (empty? (temporary-entries dir))))

    (let [artifact (.join path dir "committed.wasm")
          provenance (str artifact ".provenance.edn")
          publication (str artifact ".publication.edn")
          artifact-bytes (.from js/Buffer #js [0 97 115 109])
          provenance-text "{:format :kotoba.provenance/v1}"
          marker-text (output-set/serialize artifact artifact-bytes provenance-text)]
      (io/write-set! [{:path artifact :bytes artifact-bytes}
                      {:path provenance :text provenance-text}
                      {:path publication :text marker-text}])
      (check "commit marker verifies the complete published output set"
             (= output-set/format
                (:format (output-set/verify!
                          artifact (.readFileSync fs artifact)
                          (.readFileSync fs provenance "utf8")
                          (reader/read-string (.readFileSync fs publication "utf8"))))))
      (check "malformed marker shapes fail as uncommitted rather than internal"
             (= :output-set-mismatch
                (try
                  (output-set/verify! artifact artifact-bytes provenance-text [])
                  :no-error
                  (catch :default error (:reason (ex-data error))))))
      (check "commit marker rejects a renamed artifact basename"
             (= :output-set-mismatch
                (try
                  (output-set/verify!
                   (.join path dir "renamed.wasm") artifact-bytes provenance-text
                   (reader/read-string marker-text))
                  :no-error
                  (catch :default error (:reason (ex-data error))))))

      ;; Force the second rename to fail after the artifact was replaced. The
      ;; old marker remains visible but no longer validates the mixed version.
      (let [blocked (.join path dir "blocked")
            old-marker (.readFileSync fs publication "utf8")]
        (.mkdirSync fs blocked)
        (let [reason (try
                       (io/write-set!
                        [{:path artifact :bytes (.from js/Buffer #js [1 2 3])}
                         {:path blocked :text "cannot replace a directory"}
                         {:path publication :text "must-not-commit"}])
                       :no-error
                       (catch :default error (:reason (ex-data error))))]
          (check "a mid-publication failure is reported at rename" (= :rename reason))
          (check "a mid-publication failure does not advance the commit marker"
                 (= old-marker (.readFileSync fs publication "utf8")))
          (check "a mixed-version output set fails closed"
                 (= :output-set-mismatch
                    (try
                      (output-set/verify!
                       artifact (.readFileSync fs artifact)
                       (.readFileSync fs provenance "utf8")
                       (reader/read-string old-marker))
                      :no-error
                      (catch :default error (:reason (ex-data error))))))
          (check "failed set publication removes its shared staging directory"
                 (empty? (temporary-entries dir))))))

    (.writeFileSync fs referent "do-not-touch")
    (try
      (.symlinkSync fs referent linked "file")
      (check "bounded verifier rejects a symbolic-link member"
             (= :verify
                (try (io/read-bounded-bytes-file linked 32) :no-error
                     (catch :default error (:phase (ex-data error))))))
      (io/write-text! linked "sealed")
      (check "publication never follows the destination symlink"
             (= "do-not-touch" (.readFileSync fs referent "utf8")))
      (check "the destination symlink is replaced by the artifact"
             (and (not (.isSymbolicLink (.lstatSync fs linked)))
                  (= "sealed" (.readFileSync fs linked "utf8"))))
      (catch :default error
        (if (= "win32" (.-platform js/process))
          (println "SKIP destination symlink fixture (Windows privilege unavailable)")
          (throw error))))

    (when-not (= "win32" (.-platform js/process))
      (check "published output remains owner-only on POSIX"
             (= 384 (bit-and 511 (.-mode (.statSync fs target))))))
    (finally (.rmSync fs dir #js {:recursive true :force true}))))

(println (str (if (zero? @failures) "PASS" "FAIL") " nbb durable output publication"))
(when (pos? @failures) (.exit js/process 1))
