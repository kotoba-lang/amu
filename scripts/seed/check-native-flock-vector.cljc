;; Observe native flock/vector coexistence and an executed slot-alias mutant.
;;
;; The Kotoba fixture decides its lock, zeroing and outer-value result. Basilisp only stages source/paths and
;; records native process exits and hashes.
;; Ported from check-native-flock-vector.py (Basilisp). Linux only.
;; Run: basilisp run scripts/seed/check-native-flock-vector.cljc -- --compiler C --output OUT
(ns check-native-flock-vector
  (:require [basilisp.string :as str]
            [gate-util :as u])
  (:import json operator pathlib platform sys))

(defn main [compiler out]
  (u/chk (and (= "Linux" (platform/system)) (contains? #{"aarch64" "x86_64"} (platform/machine))))
  (let [root u/root
        target (if (= "aarch64" (platform/machine)) "aarch64-linux" "x86_64-linux")
        _ (.mkdir out ** :parents true :exist_ok false :mode 0700)
        scope (.joinpath out "scope")
        _ (.mkdir scope ** :mode 0700)
        _ (.write_text (.joinpath out "outside-target") "outside\n")
        _ (.symlink_to (.joinpath scope "link.lock") (.joinpath out "outside-target"))
        fixture (.joinpath root "seed/tests/native-flock-vector.kotoba")
        src (.joinpath out "fixture.kotoba")
        _ (.write_bytes src (.read_bytes fixture))
        paths (u/manifest-paths (.joinpath root "seed/FULL-MANIFEST"))
        env (python/dict {"PATH" "/nonexistent" "KEXE_STACK_BYTES" "8388608" "KEXE_CAP_RESOURCES_35" (str out)
                          "KEXE_ALLOW" "35,37,38,39" "KEXE_FUEL" "10000000000" "KEXE_COMMAND" "1"})
        operation-env (fn []
                        (let [e (python/dict env)]
                          (operator/setitem e "KEXE_CAP_RESOURCES_35" (str scope))
                          (operator/setitem e "KEXE_ALLOW" "35,38")
                          e))
        report (u/pydict "schema" "amu.native-flock-vector.v1" "host" (python/list [(platform/system) (platform/machine)])
                         "producer" (u/pin compiler) "fixture" (u/pin fixture)
                         "sourceBindings" (u/pydict-from (for [p paths] [p (u/pin (.joinpath root p))]))
                         "calls" (python/list))
        run (fn [name argv & {:keys [expected] :or {expected 0}}]
              (let [r (u/run-process argv (if (str/starts-with? name "build-") env (operation-env)) 900 :cwd out)]
                (doseq [[stream raw] [["stdout" (.-stdout r)] ["stderr" (.-stderr r)]]]
                  (.write_bytes (.joinpath out (str name "." stream)) raw))
                (.append (u/geti report "calls") (u/pydict "name" name "exit" (.-returncode r)))
                (u/chk (and (= expected (.-returncode r)) (not (u/nonempty? (.-stderr r)))) [name (.-returncode r) (u/bslice (.-stderr r) -800 nil)])
                (when-not (str/starts-with? name "build-")
                  (u/chk (not (u/nonempty? (.-stdout r))) [name "unexpected fixture output"]))))
        build (fn [name producer source]
                (let [dst (.joinpath out (str name ".elf"))]
                  (run (str "build-" name) [producer "compile" source "--target" target "--output" dst "--format" "static"])
                  (.chmod dst 0700)
                  dst))
        good (build "fixture" compiler src)
        fixture-args (fn [name] [(.joinpath scope name) (str scope "//" name) (.joinpath scope "link.lock") (.joinpath out "outside.lock")])
        _ (run "lock-vector-rollback-and-unlock" (cons good (fixture-args "good.lock")))
        keyword-fixture (.joinpath root "seed/tests/native-keyword-flock.kotoba")
        keyword-source (.joinpath out "keyword-flock.kotoba")
        _ (.write_bytes keyword-source (.read_bytes keyword-fixture))
        keyword-image (build "keyword-flock" compiler keyword-source)
        _ (run "keyword-lock-interleaving" [keyword-image (.joinpath scope "keyword.lock")])
        keyword-parts
        (vec (for [p paths]
               (let [text (.read_text (.joinpath root p))]
                 (str (if (= p "seed/73-keyword-intern.kotoba")
                        (do (u/chk (and (= 3 (.count text "kxrt-gl 800")) (= 1 (.count text "kxrt-gs 800"))))
                            (u/chk (and (= 2 (.count text "kxrt-gl 808")) (= 2 (.count text "kxrt-gs 808"))))
                            (-> text (.replace "kxrt-gl 800" "kxrt-gl 776") (.replace "kxrt-gs 800" "kxrt-gs 776")
                                (.replace "kxrt-gl 808" "kxrt-gl 784") (.replace "kxrt-gs 808" "kxrt-gs 784")))
                        text)
                      "\n"))))
        keyword-mutant-source (.joinpath out "keyword-alias.kotoba")
        _ (.write_text keyword-mutant-source (apply str keyword-parts))
        keyword-mutant-compiler (build "keyword-alias-compiler" compiler keyword-mutant-source)
        keyword-mutant (build "keyword-alias-fixture" keyword-mutant-compiler keyword-source)
        bad (u/run-process [keyword-mutant (.joinpath scope "keyword-mutant.lock")] (operation-env) 900 :cwd out)
        _ (.write_bytes (.joinpath out "detect-keyword-alias.stdout") (.-stdout bad))
        _ (.write_bytes (.joinpath out "detect-keyword-alias.stderr") (.-stderr bad))
        _ (u/chk (and (= 120 (.-returncode bad)) (u/has-bytes? (.encode "SIGSEGV") (.-stderr bad))) [(.-returncode bad) (u/bslice (.-stderr bad) -800 nil)])
        _ (operator/setitem report "keywordFlock"
                            (u/pydict "fixture" (u/pin keyword-fixture) "image" (u/pin keyword-image)
                                      "mutantCompiler" (u/pin keyword-mutant-compiler) "mutantImage" (u/pin keyword-mutant)
                                      "mutantExit" (.-returncode bad) "detectedBy" "SIGSEGV"))
        changed (atom 0)
        parts (vec (for [p paths]
                     (let [text (.read_text (.joinpath root p))]
                       (str (if (contains? #{"seed/76-x86_64-static-rt.kotoba" "seed/77-aarch64-static-rt.kotoba"} p)
                              (let [start (.index text "(defn- kxrt-fs-lock ")
                                    end (.index text ";; ---- wire 42" start)
                                    body (subs text start end)]
                                (u/chk (and (= 1 (.count body "kxrt-gl 792")) (= 2 (.count body "kxrt-gs 792"))))
                                (swap! changed inc)
                                (str (subs text 0 start)
                                     (-> body (.replace "kxrt-gl 792" "kxrt-gl 760") (.replace "kxrt-gs 792" "kxrt-gs 760"))
                                     (subs text end)))
                              text)
                            "\n"))))
        _ (u/chk (= 2 @changed))
        mutant-source (.joinpath out "slot-alias.kotoba")
        _ (.write_text mutant-source (apply str parts))
        mutant-compiler (build "slot-alias-compiler" compiler mutant-source)
        bad-image (build "slot-alias-fixture" mutant-compiler src)]
    (run "detect-slot-alias" (cons bad-image (fixture-args "bad.lock")) :expected 1)
    (u/chk (and (u/deq (u/pin fixture) (u/geti report "fixture")) (u/deq (u/pin compiler) (u/geti report "producer"))))
    (u/chk (every? (fn [[p expected]] (u/deq (u/pin (.joinpath root p)) expected)) (.items (u/geti report "sourceBindings"))))
    (doseq [[k v] [["status" "PASS_NATIVE_FLOCK_VECTOR"] ["image" (u/pin good)]
                   ["mutant" (u/pydict "source" (u/pin mutant-source) "compiler" (u/pin mutant-compiler) "image" (u/pin bad-image)
                                       "builtSuccessfully" true "executed" true "exit" 1)]
                   ["qualificationReplacement" false]]]
      (operator/setitem report k v))
    (.write_text (.joinpath out "observations.json") (u/json-dump report))
    (println (u/geti report "status"))
    (.flush sys/stdout)))

(defn -main [& args]
  (main (.resolve (pathlib/Path (or (u/opt args "--compiler") (sys/exit "--compiler is required"))))
        (.resolve (pathlib/Path (or (u/opt args "--output") (sys/exit "--output is required"))))))

(when (some #(or (= % "check-native-flock-vector.cljc") (str/ends-with? % "/check-native-flock-vector.cljc")) sys/argv)
  (apply -main *command-line-args*))
