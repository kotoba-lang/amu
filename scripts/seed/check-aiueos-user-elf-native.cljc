;; Observe the selfhost AIUEOS user ELF v1 scalar ABI and refusals.
;;
;; The compiler emits the artifact. This script stages fixed source, checks bytes and records exits; this is not a
;; CPL3, signature or Itonami runtime qualification. Ported from check-aiueos-user-elf-native.py (Basilisp, JUN-974).
;; Run: basilisp run -p scripts/seed scripts/seed/check-aiueos-user-elf-native.cljc -- --compiler C --output DIR
(ns check-aiueos-user-elf-native
  (:require [basilisp.string :as str]
            [aiueos-user-elf :as elf]
            [gate-util :as u])
  (:import json operator pathlib subprocess sys))

(defn main [compiler out]
  (.mkdir out ** :parents true :exist_ok false)
  (let [env (python/dict {"PATH" "/nonexistent" "KEXE_CAP_RESOURCES_35" (str out) "KEXE_STACK_BYTES" "8388608"})
        cases (python/list)
        compile-case (fn compile-case
                       ([name src] (compile-case name src [] 0))
                       ([name src extra expected]
                        (let [srcp (.joinpath out (str name ".kotoba"))
                              dst (.joinpath out (str name ".elf"))]
                          (.write_text srcp src)
                          (let [result (subprocess/run (python/list (map str (concat [compiler "compile" srcp "--target" elf/target "--output" dst] extra)))
                                                       ** :cwd out :env env :capture_output true :timeout 120)]
                            (u/chk (= expected (.-returncode result)) (str name " " (.-returncode result) " " (.-stderr result)))
                            (if (pos? expected)
                              (u/chk (not (.exists dst)) (str name " refusal left an artifact"))
                              (u/chk (not (u/nonempty? (.-stderr result))) (str name " " (.-stderr result))))
                            (.append cases (u/pydict "name" name "exit" (.-returncode result)
                                                     "stderr" (.strip (.decode (.-stderr result)))))
                            dst))))
        last-stderr (fn [] (u/geti (operator/getitem cases -1) "stderr"))
        image (compile-case "scalar" elf/source)]
    (elf/verify (.read_bytes image))
    (let [mutation (python/bytearray (.read_bytes image))]
      (operator/setitem mutation 8208 1)
      (u/chk (try (elf/verify mutation) false (catch python/AssertionError _ true)) "bitmap-1 mutation was accepted"))
    (compile-case "effect" elf/effect [] 1)
    (u/chk (.__contains__ (last-stderr) "E7101") (last-stderr))
    (compile-case "parameter" elf/parameter [] 1)
    (u/chk (.__contains__ (last-stderr) "E7102") (last-stderr))
    (compile-case "format" elf/source ["--format" "static"] 1)
    (u/chk (.__contains__ (last-stderr) "E1 usage") (last-stderr))
    (let [report (u/pydict "status" "PASS_AIUEOS_ZERO_CAP_USER_ELF_NATIVE" "compiler" (u/pin compiler)
                           "source" (u/pin (.joinpath out "scalar.kotoba")) "image" (u/pin image) "target" elf/target
                           "cases" cases "bitmap1Rejected" true "parameterRefused" true "guestExecution" false
                           "signedAppAdmission" false "itonamiTurn" false)]
      (.write_text (.joinpath out "aiueos-user-elf-native.json") (u/json-dump report))
      (println (u/geti report "status") (subs (u/geti (u/geti report "image") "sha256") 0 16))
      (.flush sys/stdout))))

(defn -main [& args]
  (main (.resolve (pathlib/Path (or (u/opt args "--compiler") (sys/exit "--compiler is required"))))
        (.resolve (pathlib/Path (or (u/opt args "--output") (sys/exit "--output is required"))))))

(when (some #(or (= % "check-aiueos-user-elf-native.cljc") (str/ends-with? % "/check-aiueos-user-elf-native.cljc")) sys/argv)
  (apply -main *command-line-args*))
