;; Observe the fixed loader-owned boot region, never arbitrary physical roots.
;; Ported from check-aiueos-boot-region-native.py (Basilisp). Linux only.
;; Run: basilisp run scripts/seed/check-aiueos-boot-region-native.cljc -- (--build DIR | --complete DIR) --output OUT
(ns check-aiueos-boot-region-native
  (:require [aiueos-gate :as g]
            [aiueos-proof :as proof]
            [basilisp.string :as str]
            [gate-util :as u])
  (:import sys))

(def boot "(ns entry (:export [main]))\n(defn main [] :i64 (let [h (kernel-subregion (kernel-boot-info) 16544 0 160)] (if (= (kernel-load-u8 h 160 0) 65) 42 0)))\n")

(def rows
  (vec (for [tier ["" "-4k" "-16k" "-64k"]
             [width want] [[8 239] [16 52719] [32 2309737967] [64 81985529216486895]]]
         [(str "kernel-store-u" width tier) (str "kernel-load-u" width tier) want])))

(def widths
  (let [bindings (concat ["r (kernel-subregion (kernel-boot-info) 16544 152 8)" "saved (kernel-load-u64 r 8 0)"]
                         (mapcat (fn [i [store load _]] [(str "s" i " (" store " r 8 0 81985529216486895)") (str "v" i " (" load " r 8 0)")])
                                 (range) rows)
                         ["restored (kernel-store-u64 r 8 0 saved)"])
        conditions (mapcat (fn [i [_ _ want]] [(str "(= s" i " 81985529216486895)") (str "(= v" i " " want ")")]) (range) rows)]
    (str "(ns entry (:export [main]))\n(defn main [] :i64 (let [" (str/join "\n" bindings) "] (if (and "
         (str/join " " conditions) " (= restored saved)) 42 0)))\n")))

(defn main [build out complete]
  (let [[graph producers _] (proof/load-native-producers :build build :complete complete)
        _ (.mkdir out ** :parents true :exist_ok false)
        results (python/list)]
    (doseq [producer producers]
      (let [scope (g/start-scope producer (.joinpath out (.-stem producer)))
            artifacts (python/dict)
            ok (fn [name text] (g/case! scope artifacts name text :pin-source true :source-text true))
            bad (fn [name text code] (g/case! scope artifacts name text :pin-source true :source-text true :refuse code))]
        (ok "boot-region" boot)
        (ok "widths" widths)
        ;; JUN-483: a plain-tier access over the 16544-byte boot block can only reach its ud2 at run time; it is
        ;; now refused at compile time, naming the intrinsic, the size and the tier maximum
        (bad "oversized-tier" "(ns entry (:export [main]))\n(defn main [] :i64 (kernel-load-u8 (kernel-boot-info) 16544 0))\n"
             "E7108 kernel-load-u8 size 16544 is above its tier maximum 512")
        (ok "valid-tier" "(ns entry (:export [main]))\n(defn main [] :i64 (- (kernel-load-u8-64k (kernel-boot-info) 16544 0) 23))\n")
        (doseq [[name text] [["wrong-boot-length" (.replace boot "16544" "16480")]
                             ["computed-root" (.replace boot "(kernel-boot-info)" "(+ (kernel-boot-info) 0)")]
                             ["literal-root" (.replace boot "(kernel-boot-info)" "1089536")]
                             ["wrong-sub-length" (.replace boot "(kernel-load-u8 h 160 0)" "(kernel-load-u8 h 64 0)")]
                             ["loaded-root" (.replace boot "(kernel-load-u8 h 160 0)" "(kernel-load-u8 (kernel-load-u64 h 160 0) 160 0)")]]]
          (bad name text "E7106"))
        (.append results (u/pydict "producer" (u/pin producer) "artifacts" artifacts "compileRefusals" 6))))
    (u/chk (u/deq (u/geti (u/geti results 0) "artifacts") (u/geti (u/geti results 1) "artifacts")))
    (let [report (u/pydict "status" "PASS_NATIVE_BOOT_REGION_PACKAGING" "source" graph "results" results
                           "guestExecution" false "fullKernel" false "nativeCDCI" false)]
      (.write_text (.joinpath out "native-boot-region.json") (u/json-dump report))
      (println (u/geti report "status") "fixed boot ABI, all32 memory ops and 6 refusal controls; guest gates separate"))))

(defn -main [& args]
  (let [[build out complete] (u/parse-build-complete-output args)]
    (main build out complete)))

(when (some #(or (= % "check-aiueos-boot-region-native.cljc") (str/ends-with? % "/check-aiueos-boot-region-native.cljc")) sys/argv)
  (apply -main *command-line-args*))
