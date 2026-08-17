(ns ipld-adl-source-compile
  (:require [kotoba.compiler.core :as compiler])
  (:import (java.nio.file Files Paths)
           (java.nio.file.attribute FileAttribute)))

(def ^:private identity-source
  "(ns adl.identity
       (:export [validate-representation decode encode validate-logical]))
   (defn validate-representation [value :bytes] :bool true)
   (defn decode [value :bytes] :bytes value)
   (defn encode [value :bytes] :bytes value)
   (defn validate-logical [value :bytes] :bool true)")

(def ^:private closed-source
  "(ns adl.closed
       (:export [validate-representation decode encode validate-logical]))
   (defn validate-representation [value :bytes] :bool true)
   (defn decode [value :bytes] :bytes (bytes))
   (defn encode [value :bytes] :bytes value)
   (defn validate-logical [value :bytes] :bool false)")

(def ^:private projection-source
  "(ns adl.projection
       (:export [validate-representation decode encode validate-logical]))
   (defn validate-representation [value :bytes] :bool true)
   (defn decode [value :bytes] :bytes (bytes))
   (defn encode [value :bytes] :bytes value)
   (defn validate-logical [value :bytes] :bool true)")

(def ^:private input-count-source
  "(ns adl.input-count
       (:export [validate-representation decode encode validate-logical]))
   (defn validate-representation [value :bytes] :bool (= (bytes-count value) 4))
   (defn decode [value :bytes] :bytes value)
   (defn encode [value :bytes] :bytes value)
   (defn validate-logical [value :bytes] :bool (= (bytes-count value) 4))")

(defn -main [& [output profile]]
  (when-not output
    (throw (ex-info "output path required" {:phase :ipld-adl-source-compile})))
  (Files/write (Paths/get output (make-array String 0))
               (:bytes (compiler/compile-ipld-adl-source
                        (case profile
                          "closed" closed-source
                          "projection" projection-source
                          "input-count" input-count-source
                          identity-source)))
               (make-array java.nio.file.OpenOption 0)))
