;; Observe bounded contiguous grants from the sealed fifteen-page allocation.
;; Ported from check-aiueos-owned-window-native.py (Basilisp). Linux only.
;; Run: basilisp run scripts/seed/check-aiueos-owned-window-native.cljc -- (--build DIR | --complete DIR) --output OUT
(ns check-aiueos-owned-window-native
  (:require [aiueos-gate :as g]
            [aiueos-native-proof :as proof]
            [basilisp.string :as str]
            [gate-util :as u])
  (:import sys))

(def source
  "(ns entry (:export [main]))
(defn main [] :i64
 (let [h (kernel-subregion (kernel-boot-info) 16544 0 160)
       original (kernel-load-u64 h 160 80)
       changed (kernel-store-u64 h 160 80 0)
       w (kernel-owned-window 1 12288)
       page (kernel-owned-page 1)
       last (kernel-subregion w 12288 8192 4096)
       third (kernel-owned-page 3)
       saved (kernel-load-u64-16k w 12288 12280)
       write (kernel-store-u64-16k w 12288 12280 42)
       readback (kernel-load-u64-4k last 4096 4088)
       restored (kernel-store-u64-16k w 12288 12280 saved)
       metadata (kernel-store-u64 h 160 80 original)]
  (if (and (= changed 0) (= w page) (= last third) (= write 42)
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
        (ok "sealed-window" source)
        (doseq [[name slot size] [["zero" 0 0] ["unaligned" 0 4095] ["negative-size" 0 -4096] ["too-wide" 0 65536]
                                  ["cross-end" 14 8192] ["invalid-slot" 15 4096] ["negative-slot" -1 4096] ["valid-window" 0 61440]]]
          (ok name (str "(ns entry (:export [main]))\n(defn main [] :i64 (if (> (kernel-owned-window " slot " " size ") 0) 42 0))\n")))
        (bad "wrong-length" (.replace source "(kernel-load-u64-16k w 12288 12280)" "(kernel-load-u64-16k w 16384 12280)"))
        (bad "computed-root" (.replace source "(kernel-load-u64-16k w 12288 12280)" "(kernel-load-u64-16k (+ w 0) 12288 12280)"))
        (.append routes (u/pydict "compiler" (u/pin compiler) "artifacts" artifacts "compileRefusals" 2))))
    (u/chk (u/deq (u/geti (u/geti routes 0) "artifacts") (u/geti (u/geti routes 1) "artifacts")))
    (let [report (u/pydict "status" "PASS_NATIVE_OWNED_WINDOW_PACKAGING" "source" graph "routes" routes
                           "guestExecution" false "fullKernel" false "nativeCDCI" false)]
      (.write_text (.joinpath out "native-owned-window.json") (u/json-dump report))
      (println (u/geti report "status") "sealed contiguous allocation,7 runtime bounds fixtures and2 provenance refusals; guest separate"))))

(defn -main [& args]
  (let [[build out complete] (u/parse-build-complete-output args)]
    (main build out complete)))

(when (some #(or (= % "check-aiueos-owned-window-native.cljc") (str/ends-with? % "/check-aiueos-owned-window-native.cljc")) sys/argv)
  (apply -main *command-line-args*))
