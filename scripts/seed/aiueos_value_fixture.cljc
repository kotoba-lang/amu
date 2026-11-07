;; Reuse the typed role fixture without importing a hyphenated script name.
;; Ported from check_aiueos_value_fixture.py (Basilisp).
(ns aiueos-value-fixture
  (:require [aiueos-gate :as g]))

(defn user-source []
  (let [source (g/load-source-var "check-aiueos-value-call-native.cljc" 'check-aiueos-value-call-native/source)
        start (.index source "(defn main ")]
    (str (subs source 0 start)
         "(defn main [] :i64
  (let [registered (kernel-register-value-domain 73)
        published (kernel-publish-current-domain 73)
        code (kernel-value-domain-code-page 73)
        stack (kernel-value-domain-stack-page 73)
        a (kernel-store-u8-4k code 4096 0 144)
        b (kernel-store-u8-4k stack 4096 0 0)
        enabled (kernel-value-enable-user)]
    (+ 42 enabled)))
")))
