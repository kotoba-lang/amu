(ns kotoba.compiler.nbb.output-set-cli
  (:require [kotoba.compiler.nbb.cli-support :as support]
            [kotoba.compiler.nbb.io :as io]
            [kotoba.compiler.nbb.output-set :as output-set]))

(def ^:private max-artifact-bytes (* 64 1024 1024))
(def ^:private max-metadata-bytes (* 1024 1024))

(defn- decode-utf8! [path bytes]
  (try
    (.decode (js/TextDecoder. "utf-8" #js {:fatal true}) bytes)
    (catch :default error
      (throw (ex-info "output-set member is not valid UTF-8"
                      {:phase :verify :path path} error)))))

(defn- verify-output-set! [args]
  (let [output (second args)
        _ (when-not (= 2 (count args))
            (support/usage-error!
             "error: verify-output-set requires exactly one artifact path"))
        provenance-output (str output ".provenance.edn")
        publication-output (str output ".publication.edn")
        artifact-bytes (io/read-bounded-bytes-file output max-artifact-bytes)
        provenance-text (decode-utf8!
                         provenance-output
                         (io/read-bounded-bytes-file provenance-output
                                                     max-metadata-bytes))
        marker (support/parse-policy-material
                {:present? true
                 :text (decode-utf8!
                        publication-output
                        (io/read-bounded-bytes-file publication-output
                                                    max-metadata-bytes))})]
    (output-set/verify! output artifact-bytes provenance-text marker)
    {:ok true :format output-set/format :output output
     :provenance-output provenance-output
     :publication-output publication-output}))

(support/execute!
 #(case (first %)
    "verify-output-set" (verify-output-set! %)
    (support/usage-error! "error: output-set path covers verify-output-set only")))
