;; Stage private metadata and stack fixtures; missing device grants refuse.
;; Ported from check-aiueos-private-context-native.py (Basilisp). Linux only.
;; Run: basilisp run scripts/seed/check-aiueos-private-context-native.cljc -- (--build DIR | --complete DIR) --output OUT
(ns check-aiueos-private-context-native
  (:require [aiueos-gate :as g]
            [aiueos-proof :as proof]
            [basilisp.string :as str]
            [gate-util :as u])
  (:import sys))

(def catalog
  "(ns entry (:export [main]))
(defn main [] :i64
 (let [m (kernel-subregion (kernel-boot-info) 16544 160 16384)
       state (kernel-owned-page 14)
       kind (kernel-load-u32-16k m 16384 0)
       base (kernel-load-u64-16k m 16384 8)
       pages (kernel-load-u64-16k m 16384 24)
       k (kernel-store-u64-4k state 4096 0 kind)
       b (kernel-store-u64-4k state 4096 8 base)
       p (kernel-store-u64-4k state 4096 16 pages)
       forged-kind (kernel-store-u32-16k m 16384 0 11)
       forged-base (kernel-store-u64-16k m 16384 8 4096)
       forged-pages (kernel-store-u64-16k m 16384 24 16)]
  (if (and (= k kind) (= b base) (= p pages) (= forged-kind 11)
           (= forged-base 4096) (= forged-pages 16)) 42 0)))
")

(def deep
  "(ns entry (:export [main]))
(defn- deep [n :i64] :i64 (if (= n 0) 42 (+ 1 (deep (- n 1)))))
(defn main [] :i64 (if (> (kernel-owned-page 0) 0) (deep 10000) 0))
")

(defn main [build out complete]
  (let [[graph producers _] (proof/load-native-producers :build build :complete complete)
        _ (.mkdir out ** :parents true :exist_ok false)
        routes (python/list)]
    (doseq [compiler producers]
      (let [scope (g/start-scope compiler (.joinpath out (.-stem compiler)))
            artifacts (python/dict)]
        (g/case! scope artifacts "catalog" catalog :source-text true)
        (doseq [[name operation] [["retired-classification" "kernel-firmware-mmio"]]]
          (g/case! scope artifacts name (str "(ns entry (:export [main]))\n(defn main [] :i64 (" operation " 4096 512))\n")
                   :source-text true :refuse "E2101"))
        (g/case! scope artifacts "stack-exhaustion" deep :source-text true)
        (g/case! scope artifacts "shallow-stack" (.replace deep "deep 10000" "deep 0") :source-text true)
        (.append routes (u/pydict "compiler" (u/pin compiler) "artifacts" artifacts "missingPrimitiveRefusals" 1))))
    (u/chk (u/deq (u/geti (u/geti routes 0) "artifacts") (u/geti (u/geti routes 1) "artifacts")))
    (let [report (u/pydict "status" "PASS_NATIVE_PRIVATE_CONTEXT_PACKAGING"
                           "observer" (u/pin (.joinpath u/root "scripts/seed/check-aiueos-private-context-native.cljc"))
                           "source" graph "routes" routes "guestExecution" false "positivePlatformMMIOQualified" false
                           "fullKernel" false "nativeCDCI" false)]
      (.write_text (.joinpath out "native-private-context.json") (u/json-dump report))
      (println (u/geti report "status") "private metadata + stack fixtures; retired classification API refuses"))))

(defn -main [& args]
  (let [[build out complete] (u/parse-build-complete-output args)]
    (main build out complete)))

(when (some #(or (= % "check-aiueos-private-context-native.cljc") (str/ends-with? % "/check-aiueos-private-context-native.cljc")) sys/argv)
  (apply -main *command-line-args*))
