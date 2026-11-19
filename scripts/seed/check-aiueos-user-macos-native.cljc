;; Build the user-target Amu source with Mac native Amu and emit its ELF.
;;
;; This stages pinned source bytes and observes native processes. The signed compiler and packager are explicit
;; inputs; no Linux, JVM, Node or C compiler process is part of this Mac gate. This is compiler/artifact evidence,
;; not a guest, Itonami turn or release qualification. Ported from check-aiueos-user-macos-native.py (Basilisp,
;; JUN-974); the work lives in macos_user_target.cljc.
;; Run: basilisp run -p scripts/seed scripts/seed/check-aiueos-user-macos-native.cljc -- --output DIR
;;      [--compiler-image F --compiler-sha256 H --packager-image F --packager-sha256 H]
(ns check-aiueos-user-macos-native
  (:require [basilisp.string :as str]
            [gate-util :as u]
            [macos-user-target :as target])
  (:import sys))

(defn -main [& args]
  (target/main {:compiler-image (u/opt args "--compiler-image") :compiler-sha256 (u/opt args "--compiler-sha256")
                :packager-image (u/opt args "--packager-image") :packager-sha256 (u/opt args "--packager-sha256")
                :output (or (u/opt args "--output") (sys/exit "--output is required"))}))

(when (some #(or (= % "check-aiueos-user-macos-native.cljc") (str/ends-with? % "/check-aiueos-user-macos-native.cljc")) sys/argv)
  (apply -main *command-line-args*))
