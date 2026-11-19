;; Observe the bounded AIUEOS user-v2 Goal input ELF contract: verify an ELF file's shape.
;; Ported from check-aiueos-user-v2-native.py (Basilisp, JUN-974); the checks live in aiueos_user_v2.cljc.
;; Run: basilisp run -p scripts/seed scripts/seed/check-aiueos-user-v2-native.cljc -- ELF
(ns check-aiueos-user-v2-native
  (:require [basilisp.string :as str]
            [aiueos-user-v2 :as v2]
            [gate-util :as u])
  (:import pathlib sys))

(defn -main [& args]
  (v2/verify (.read_bytes (pathlib/Path (or (first args) (sys/exit "usage: check-aiueos-user-v2-native ELF")))))
  (println "PASS_AIUEOS_USER_V2_ELF_SHAPE")
  (.flush sys/stdout))

(when (some #(or (= % "check-aiueos-user-v2-native.cljc") (str/ends-with? % "/check-aiueos-user-v2-native.cljc")) sys/argv)
  (apply -main *command-line-args*))
