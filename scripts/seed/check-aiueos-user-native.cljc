;; Observe native v3 admission and refusals; hardware entry is a QEMU gate.
;; Ported from check-aiueos-user-native.py (Basilisp). Linux only.
;; Run: basilisp run scripts/seed/check-aiueos-user-native.cljc -- (--build DIR | --complete DIR) --output OUT
(ns check-aiueos-user-native
  (:require [aiueos-gate :as g]
            [aiueos-native-proof :as proof]
            [basilisp.string :as str]
            [aiueos-value-fixture :as fixture]
            [gate-util :as u])
  (:import sys))

(defn main [build complete output]
  (let [[graph producers _] (proof/load-native-producers :build build :complete complete)
        _ (.mkdir output ** :parents true :exist_ok false)
        routes (python/list)]
    (doseq [compiler producers]
      (let [scope (g/start-scope compiler (.joinpath output (.-stem compiler)))
            text (fixture/user-source)
            image-path (g/success! scope "owned-user-pages" text :pin-source true)
            b (.read_bytes image-path) rx (g/ph-rx b) rw (g/ph-rw b)
            _ (u/chk (and (= 0x240000 (u/geti rw 5)) (= 0x334c5652 (g/u64-at b (+ (u/geti rw 2) 464)))))
            _ (u/chk (< (+ (u/geti rx 3) 77) (g/u64-at b (+ (u/geti rw 2) 30400)) (+ (u/geti rx 3) (u/geti rx 5))))
            _ (u/chk (= (g/u64-at b (+ (u/geti rw 2) 172)) (+ (u/geti rw 3) 131072)))
            efi (g/package-efi! scope "owned-user-pages" image-path)
            _ (u/chk (= 1 (.count (.read_bytes efi) b)))
            good (u/pydict "kernel" (u/pin image-path) "efi" (u/pin efi))
            refuse (fn [name t code] (g/refusal! scope name t code :pin-source true))]
        (doseq [vector [6 13 14]]
          (refuse (str "reserved-vector-" vector)
                  (str (.replace text "(:export [main" (str "(:export [aiueos-isr-" vector " main"))
                       "\n(defn aiueos-isr-" vector " [v :i64 e :i64 p :i64 s :i64] :i64 0)\n")
                  "E7102"))
        (refuse "partial-family" (.replace text "main aiueos-value-runtime-entry" "main" 1) "E7102")
        (refuse "literal-code-address" (.replace text "(kernel-value-domain-code-page 73)" "1970176") "E7106")
        (refuse "entry-result-is-scalar" (.replace text "(kernel-value-domain-code-page 73)" "(kernel-value-enter-user 73)") "E7106")
        (.append routes (u/pydict "compiler" (u/pin compiler) "artifacts" good "refusals" 6))))
    (u/chk (u/deq (u/geti (u/geti routes 0) "artifacts") (u/geti (u/geti routes 1) "artifacts")))
    (g/finish! output "native-user-context.json"
               (u/pydict "status" "PASS_NATIVE_USER_CONTEXT_ADMISSION" "source" graph "routes" routes
                         "guestExecution" false "userSyscall" false "nativeCDCI" false))))

(defn -main [& args]
  (let [[build out complete] (u/parse-build-complete-output args)]
    (main build complete out)))

(when (some #(or (= % "check-aiueos-user-native.cljc") (str/ends-with? % "/check-aiueos-user-native.cljc")) sys/argv)
  (apply -main *command-line-args*))
