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

(defn -main [& [output]]
  (when-not output
    (throw (ex-info "output path required" {:phase :ipld-adl-source-compile})))
  (Files/write (Paths/get output (make-array String 0))
               (:bytes (compiler/compile-ipld-adl-source identity-source))
               (make-array java.nio.file.OpenOption 0)))
