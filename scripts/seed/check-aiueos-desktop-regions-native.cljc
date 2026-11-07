;; Native admission/refusal evidence for closed GOP/Browser/font regions.
;; Ported from check-aiueos-desktop-regions-native.py (Basilisp). Linux only.
;; Run: basilisp run scripts/seed/check-aiueos-desktop-regions-native.cljc -- (--build DIR | --complete DIR) --output OUT
(ns check-aiueos-desktop-regions-native
  (:require [aiueos-gate :as g]
            [aiueos-native-proof :as proof]
            [basilisp.string :as str]
            [gate-util :as u])
  (:import sys))

(def base (g/load-source-var "check-aiueos-value-call-native.cljc" 'check-aiueos-value-call-native/source))

(def source
  (str (subs base 0 (.index base "(defn main "))
       "(defn main [] :i64
  (let [s (kernel-browser-surface) c (kernel-browser-context)
        f (kernel-native-font) p (kernel-framebuffer-page 0)
        a (kernel-store-u32 (kernel-subregion s 8192 0 4) 4 0 42)
        b (kernel-store-u32 (kernel-subregion c 8192 0 4) 4 0 7)
        font (kernel-subregion f 524288 0 16384)]
    (+ (kernel-load-u32-4k p 4096 0)
       (kernel-load-u32-16k font 16384 0))))
"))

(def controls
  [["literal-framebuffer" (.replace source "(kernel-framebuffer-page 0)" "3221225472")]
   ["scalar-width-is-not-region" (.replace source "(kernel-framebuffer-page 0)" "(kernel-framebuffer-width)")]
   ["computed-font-pointer" (.replace source "(kernel-native-font)" "(+ (kernel-native-font) 0)")]
   ["font-extent-forgery" (.replace source "kernel-subregion f 524288" "kernel-subregion f 1048576")]
   ["surface-extent-forgery" (.replace source "kernel-subregion s 8192" "kernel-subregion s 16384")]
   ["context-extent-forgery" (.replace source "kernel-subregion c 8192" "kernel-subregion c 16384")]])

(defn main [build complete out]
  (let [[graph producers _] (proof/load-native-producers :build build :complete complete)
        _ (.mkdir out ** :parents true :exist_ok false)
        routes (python/list)]
    (doseq [compiler producers]
      (let [scope (g/start-scope compiler (.joinpath out (.-stem compiler)))
            dest (g/success! scope "owned-gop-browser-font" source)
            image (.read_bytes dest) rw (g/ph-rw image)
            _ (u/chk (= 0x240000 (u/geti rw 5)))
            _ (u/chk (= 0x334c5652 (g/u64-at image (+ (u/geti rw 2) 464))))
            good (u/pin dest)]
        (doseq [[name text] controls] (g/refusal! scope name text "E7106"))
        (.append routes (u/pydict "compiler" (u/pin compiler) "image" good "refusals" (count controls)))))
    (u/chk (u/deq (u/geti (u/geti routes 0) "image") (u/geti (u/geti routes 1) "image")))
    (g/finish! out "native-desktop-regions.json"
               (u/pydict "status" "PASS_NATIVE_DESKTOP_REGION_ADMISSION" "source" graph "routes" routes
                         "firmwareExecution" false "guestBoot" false "desktopInput" false))))

(defn -main [& args]
  (let [[build out complete] (u/parse-build-complete-output args)]
    (main build complete out)))

(when (some #(or (= % "check-aiueos-desktop-regions-native.cljc") (str/ends-with? % "/check-aiueos-desktop-regions-native.cljc")) sys/argv)
  (apply -main *command-line-args*))
