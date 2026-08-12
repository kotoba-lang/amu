(ns test.nbb.io
  "Behavioral regression tests for the primary Node compiler's publication
  boundary. Runs directly on NBB so no JVM implementation can satisfy these
  assertions accidentally."
  (:require ["node:fs" :as fs]
            ["node:os" :as os]
            ["node:path" :as path]
            [kotoba.compiler.nbb.io :as io]))

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

    (let [reason (try (io/write-bytes! target nil) :no-error
                      (catch :default error (:reason (ex-data error))))]
      (check "a failed write reports the write phase" (= :write reason))
      (check "a failed write preserves the prior artifact"
             (= "replacement" (.readFileSync fs target "utf8")))
      (check "a failed write removes its private temporary location"
             (empty? (temporary-entries dir))))

    (.writeFileSync fs referent "do-not-touch")
    (try
      (.symlinkSync fs referent linked "file")
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
