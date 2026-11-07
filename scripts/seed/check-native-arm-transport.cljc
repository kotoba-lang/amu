;; Check fresh ARM artifact identity before execution; never qualification.
;; Ported from check-native-arm-transport.py (Basilisp). Linux only.
;; Run: basilisp run scripts/seed/check-native-arm-transport.cljc -- --bootstrap DIR --one DIR --output FILE
(ns check-native-arm-transport
  (:require [aiueos-native-proof :as proof]
            [basilisp.string :as str]
            [gate-util :as u])
  (:import platform sys))

(defn main [boot one output]
  (u/chk (and (= "Linux" (platform/system)) (contains? #{"aarch64" "arm64"} (platform/machine))))
  (let [[graph producers baseline] (proof/load-native-producers :build boot)
        product (u/read-json (.joinpath u/root "native-product.json"))
        root (u/read-json (.joinpath u/root "seed/bootstrap/aarch64-linux-static-root.json"))
        _ (u/chk (and (u/deq (u/pin baseline) (u/geti root "image")) (u/deq (u/geti root "image") (u/geti product "rootImage"))))
        proof-doc (u/read-json (.joinpath one "one-compiler.json"))
        _ (u/chk (= "PASS_COMBINED_COMPILER" (u/geti proof-doc "status")))
        _ (u/chk (= ["Linux" (platform/machine)] (vec (take 2 (u/geti proof-doc "host")))))
        _ (u/chk (and (not (u/geti proof-doc "cCompilerOrLoader")) (not (u/geti proof-doc "emulation"))))
        _ (u/chk (u/deq (u/geti (u/geti proof-doc "bootstrap") "receipt") (u/pin (.joinpath boot "selfhost-bootstrap.json"))))]
    (doseq [bindings (.values (u/geti proof-doc "sources"))
            [path identity] (.items bindings)]
      (u/chk (u/deq (u/pin (.joinpath u/root path)) identity) ["transport source drift" path]))
    (let [f (u/geti proof-doc "F")]
      (u/chk (and (u/deq (u/pin (.joinpath one "F2.elf")) (u/geti f "image")) (u/deq (u/geti f "image") (u/geti f "packedByF"))
                  (u/deq (u/geti f "packedByF") (u/geti root "image"))))
      (u/chk (and (u/deq (u/pin (.joinpath one "F-x86_64.elf")) (u/geti proof-doc "completeX86Compiler"))
                  (u/deq (u/geti proof-doc "completeX86Compiler") (u/geti product "image")))))
    ;; Artifact downloads lose execute bits. Restore them only after all checks.
    (doseq [p (concat [baseline] producers [(.joinpath one "F2.elf")])]
      (.chmod p 0755))
    (.write_text output (u/json-dump (u/pydict "schema" "amu.native-arm-transport.v1"
                                               "status" "PASS_CURRENT_NATIVE_ARM_TRANSPORT_IDENTITIES"
                                               "nativeVerdictAuthority" false "qualificationReplacement" false "fullQualification" false
                                               "sourceGraph" graph "root" (u/pin baseline)
                                               "completeARM" (u/pin (.joinpath one "F2.elf"))
                                               "completeX86" (u/pin (.joinpath one "F-x86_64.elf"))
                                               "allRemainingARMAndX86GatesRequired" true)))
    (println "PASS_CURRENT_NATIVE_ARM_TRANSPORT_IDENTITIES")
    (.flush sys/stdout)))

(defn -main [& args]
  (let [boot (u/opt args "--bootstrap") one (u/opt args "--one") out (u/opt args "--output")]
    (when-not (and boot one out) (sys/exit "--bootstrap, --one and --output are required"))
    (main (.resolve (u/path boot)) (.resolve (u/path one)) (.resolve (u/path out)))))

(when (some #(or (= % "check-native-arm-transport.cljc") (str/ends-with? % "/check-native-arm-transport.cljc")) sys/argv)
  (apply -main *command-line-args*))
