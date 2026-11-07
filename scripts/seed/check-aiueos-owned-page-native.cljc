;; Observe the bounded slot constructor and immutable pre-main metadata seal.
;; Ported from check-aiueos-owned-page-native.py (Basilisp). Linux only.
;; Run: basilisp run scripts/seed/check-aiueos-owned-page-native.cljc -- (--build DIR | --complete DIR) --output OUT
(ns check-aiueos-owned-page-native
  (:require [aiueos-gate :as g]
            [aiueos-native-proof :as proof]
            [basilisp.string :as str]
            [gate-util :as u])
  (:import sys))

(def source
  "(ns entry (:export [main]))
(defn main [] :i64
 (let [header (kernel-subregion (kernel-boot-info) 16544 0 160)
       original (kernel-load-u64 header 160 80)
       changed (kernel-store-u64 header 160 80 0)
       first (kernel-owned-page 0) last (kernel-owned-page 14)
       saved (kernel-load-u64-4k first 4096 0)
       stored (kernel-store-u8-4k first 4096 0 42)
       readback (kernel-load-u8-4k first 4096 0)
       restored (kernel-store-u64-4k first 4096 0 saved)
       metadata (kernel-store-u64 header 160 80 original)]
  (if (and (> original 0) (= first original) (= (- last first) 57344)
           (= (bit-and first 4095) 0) (= changed 0) (= stored 42)
           (= readback 42) (= restored saved) (= metadata original)) 42 0)))
")

(defn main [build out complete]
  (let [[graph producers _] (proof/load-native-producers :build build :complete complete)
        _ (.mkdir out ** :parents true :exist_ok false)
        routes (python/list)]
    (doseq [compiler producers]
      (let [scope (g/start-scope compiler (.joinpath out (.-stem compiler)))
            artifacts (python/dict)
            ok (fn [name text] (g/case! scope artifacts name text :source-text true))
            bad (fn [name text] (g/case! scope artifacts name text :source-text true :refuse "E7106"))]
        (ok "sealed-pages" source)
        (doseq [[name slot] [["invalid-slot" "15"] ["negative-slot" "-1"] ["valid-slot" "0"]]]
          (ok name (str "(ns entry (:export [main]))\n(defn main [] :i64 (if (> (kernel-owned-page " slot ") 0) 42 0))\n")))
        (bad "loaded-pointer" (.replace source "(kernel-load-u8-4k first 4096 0)" "(kernel-load-u8-4k original 4096 0)"))
        (bad "computed-pointer" (.replace source "(kernel-load-u8-4k first 4096 0)" "(kernel-load-u8-4k (+ first 0) 4096 0)"))
        (bad "wrong-length" (.replace source "(kernel-load-u8-4k first 4096 0)" "(kernel-load-u8-4k first 64 0)"))
        (bad "forged-recovery-pages" "(ns entry (:export [main]))\n(defn main [] :i64 (kernel-configure-page-fault-recovery 4096 8192))\n")
        (.append routes (u/pydict "compiler" (u/pin compiler) "artifacts" artifacts "compileRefusals" 4))))
    (u/chk (u/deq (u/geti (u/geti routes 0) "artifacts") (u/geti (u/geti routes 1) "artifacts")))
    (let [report (u/pydict "status" "PASS_NATIVE_OWNED_PAGE_PACKAGING" "source" graph "routes" routes
                           "guestExecution" false "nativeCDCI" false "fullKernel" false "liveRuntime" false)]
      (.write_text (.joinpath out "native-owned-page.json") (u/json-dump report))
      (println (u/geti report "status") "15 sealed pages, mutable-header forgery fixture and4 refusal controls; guest execution separate"))))

(defn -main [& args]
  (let [[build out complete] (u/parse-build-complete-output args)]
    (main build out complete)))

(when (some #(or (= % "check-aiueos-owned-page-native.cljc") (str/ends-with? % "/check-aiueos-owned-page-native.cljc")) sys/argv)
  (apply -main *command-line-args*))
