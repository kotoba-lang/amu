(ns run-cljs-backend
  "The cljs backend's own portable suite on nbb -- no JVM in this path.

   nbb --classpath \"src:test:$(clojure -Spath -M:test)\" run-cljs-backend.cljs"
  (:require [cljs.test :as t]
            [kotoba.compiler.backend-cljs-portable-test]))

(defmethod t/report [:cljs.test/default :end-run-tests] [m]
  (println (str "\nnbb: " (:test m) " tests, " (:pass m) " passed, "
                (:fail m) " failed, " (:error m) " errors"))
  (when (pos? (+ (or (:fail m) 0) (or (:error m) 0)))
    (set! (.-exitCode js/process) 1)))

(t/run-tests 'kotoba.compiler.backend-cljs-portable-test)
