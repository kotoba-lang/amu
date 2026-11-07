;; Observe typed role/range admission; actual guest call execution is separate.
;; Ported from check-aiueos-value-call-native.py (Basilisp). Linux only.
;; Run: basilisp run scripts/seed/check-aiueos-value-call-native.cljc -- (--build DIR | --complete DIR) --output OUT
(ns check-aiueos-value-call-native
  (:require [aiueos-gate :as g]
            [aiueos-proof :as proof]
            [basilisp.string :as str]
            [gate-util :as u])
  (:import sys))

(def roles
  [["aiueos-value-runtime-entry" "a :i64 p :i64 u :i64 r :i64 c :i64"
    "(+ (kernel-load-u8-4k a 4096 0) (kernel-load-u8-4k u 4096 0) (kernel-load-u8 r 96 0) (kernel-load-u8-4k c 4096 0))"]
   ["aiueos-value-runtime-syscall-plan" "n :i64 d :i64 p :i64 i :i64 s :i64" "0"]
   ["aiueos-value-runtime-publish-domain" "d :i64" "0"]
   ["aiueos-value-runtime-provider-status" "g :i64 a :i64" "0"]
   ["aiueos-value-runtime-capability-grant" "a :i64 s :i64 g :i64 r :i64 o :i64" "0"]
   ["aiueos-value-runtime-provider-claim" "" "0"]
   ["aiueos-value-runtime-provider-complete" "t :i64 r :i64 b :i64 n :i64 d :i64" "(kernel-load-u8-16k b n 0)"]
   ["aiueos-value-runtime-cas-verify" "b :i64 n :i64 e :i64 o :i64 w :i64"
    "(+ (kernel-load-u8-16k b n 0) (kernel-load-u8 e 32 0) (kernel-load-u8 o 32 0) (kernel-load-u8 w 352 0))"]])

(def source
  (str "(ns entry (:export [main " (str/join " " (map first roles)) "]))\n"
       (apply str (for [[name args body] roles] (str "(defn " name " [" args "] :i64 " body ")\n")))
       "(defn main [] :i64 (let [r (kernel-value-runtime-invoke 5 0 0 0 0 0)] (+ 42 r)))\n"))

(defn- verify-and-package [scope name image]
  (let [b (.read_bytes image) rx (g/ph-rx b) rw (g/ph-rw b)
        targets (g/unpack "<8Q" b (+ (u/geti rw 2) 30208))]
    (u/chk (and (= 147456 (u/geti rw 5)) (= 8 (count (set targets)))
                (every? #(< (+ (u/geti rx 3) 77) % (+ (u/geti rx 3) (u/geti rx 5))) targets)))
    (u/chk (= (g/u64-at b (+ (u/geti rw 2) 172)) (+ (u/geti rw 3) 131072)))
    (u/chk (zero? (g/u64-at b (+ (u/geti rw 2) 328))) "typed roles must not become ISR callbacks")
    (let [efi (g/package-efi! scope name image)]
      (u/chk (= 1 (.count (.read_bytes efi) b)))
      (u/pydict "kernel" (u/pin image) "efi" (u/pin efi)))))

(defn main [build complete output]
  (let [[graph producers _] (proof/load-native-producers :build build :complete complete)
        _ (.mkdir output ** :parents true :exist_ok false)
        routes (python/list)]
    (doseq [compiler producers]
      (let [scope (g/start-scope compiler (.joinpath output (.-stem compiler)))
            good (let [image (g/success! scope "typed-roles" source :pin-source true)] (verify-and-package scope "typed-roles" image))
            refuse (fn [name text code] (g/refusal! scope name text code :pin-source true))]
        (refuse "partial-family" (.replace source "main aiueos-value-runtime-entry" "main" 1) "E7102")
        (refuse "wrong-role-type" (.replace source "[g :i64 a :i64]" "[g :i64 a :bool]") "E7102")
        (refuse "extra-export" (str (.replace source "(:export [main" "(:export [other main") "(defn other [] :i64 0)\n") "E7102")
        (refuse "direct-role-call" (.replace source "(kernel-value-runtime-invoke 5 0 0 0 0 0)" "(aiueos-value-runtime-provider-claim)") "E7106")
        (refuse "scalar-role-is-not-region"
                (.replace source "(defn aiueos-value-runtime-publish-domain [d :i64] :i64 0)"
                          "(defn aiueos-value-runtime-publish-domain [d :i64] :i64 (kernel-load-u8 d 512 0))") "E7106")
        (refuse "computed-abi-pointer" (.replace source "(kernel-load-u8-16k b n 0)" "(kernel-load-u8-16k (+ b 0) n 0)") "E7106")
        (refuse "unbound-invoke" "(ns entry (:export [main]))\n(defn main [] :i64 (kernel-value-runtime-invoke 5 0 0 0 0 0))\n" "E7102")
        (.append routes (u/pydict "compiler" (u/pin compiler) "artifacts" good "refusals" 7))))
    (u/chk (u/deq (u/geti (u/geti routes 0) "artifacts") (u/geti (u/geti routes 1) "artifacts")))
    (g/finish! output "native-value-call.json"
               (u/pydict "status" "PASS_NATIVE_TYPED_VALUE_CALL_ADMISSION" "source" graph "routes" routes
                         "guestExecution" false "userSyscall" false "nativeCDCI" false))))

(defn -main [& args]
  (let [[build out complete] (u/parse-build-complete-output args)]
    (main build complete out)))

(when (some #(or (= % "check-aiueos-value-call-native.cljc") (str/ends-with? % "/check-aiueos-value-call-native.cljc")) sys/argv)
  (apply -main *command-line-args*))
