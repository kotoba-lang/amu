;; Observe the native static-capacity generator and bounded refusal cases.
;; Ported from check-static-profile-native.py (Basilisp). Linux only.
;; Run: basilisp run scripts/seed/check-static-profile-native.cljc -- (--build DIR | --complete DIR) --output OUT
(ns check-static-profile-native
  (:require [aiueos-native-proof :as proof]
            [basilisp.string :as str]
            [gate-util :as u])
  (:import operator platform shutil sys))

(defn main [build complete out]
  (let [[graph producers _] (proof/load-native-producers :build build :complete complete)
        _ (.mkdir out ** :parents true :exist_ok false)
        routes (python/list)
        root u/root
        parts (mapv #(.joinpath root %) ["seed/00-ns-static.kotoba" "seed/01-mem.kotoba" "seed/02-io.kotoba" "seed/gen-static-ns.kotoba"])
        target (if (= "x86_64" (platform/machine)) "x86_64-linux" "aarch64-linux")
        expected-static (.read_bytes (.joinpath root "seed/00-ns-static.kotoba"))]
    (doseq [compiler producers]
      (let [work (.joinpath out (.-stem compiler))
            _ (.mkdir work)
            source (.joinpath work "generator.kotoba")
            _ (.write_bytes source (.join (u/bytes-of) (python/list (for [p parts] (operator/add (.read_bytes p) (.encode "\n"))))))
            normal (.joinpath work "normal.kotoba")
            _ (shutil/copy2 (.joinpath root "seed/00-ns.kotoba") normal)
            policy (.joinpath work "MEMORY-MAP")
            _ (shutil/copy2 (.joinpath root "seed/MEMORY-MAP") policy)
            env (python/dict {"PATH" "/nonexistent" "KEXE_ALLOW" "35,37,38,39" "KEXE_CAP_RESOURCES_35" (str work) "KEXE_STACK_BYTES" "8388608"})
            calls (python/list)
            run (fn [name args & {:keys [expected custom] :or {expected 0}}]
                  (let [r (u/run-process args (or custom env) 300)]
                    (.write_bytes (.joinpath work (str name ".stdout")) (.-stdout r))
                    (.write_bytes (.joinpath work (str name ".stderr")) (.-stderr r))
                    (.append calls (u/pydict "name" name "exit" (.-returncode r)))
                    (.write_text (.joinpath work "calls.json") (u/json-dump calls))
                    (u/chk (= expected (.-returncode r)) [name (.-returncode r) (u/bslice (.-stderr r) -1000 nil)])
                    (when (zero? expected) (u/chk (not (u/nonempty? (.-stderr r)))))
                    r))
            tool (.joinpath work "generator.elf")
            _ (run "compile" [compiler "compile" source "--target" target "--output" tool "--format" "static"])
            _ (.chmod tool 0755)
            good (.joinpath work "static.kotoba")
            _ (run "generate" [tool normal policy good])
            _ (u/chk (= expected-static (.read_bytes good)))
            _ (run "existing-output" [tool normal policy good] :expected 1)
            _ (u/chk (= expected-static (.read_bytes good)))
            text (.read_text policy)
            cases [["zero-node" (.replace text ";; [:s MM-NODE-CAP 786432]" ";; [:s MM-NODE-CAP 0]")]
                   ["zero-sir" (.replace text ";; [:s MM-SIR-CAP 589824]" ";; [:s MM-SIR-CAP 0]")]
                   ["missing-sir" (.replace text ";; [:s MM-SIR-CAP 589824]\n" "")]
                   ["vector-budget" (.replace text ";; [:s MM-NODE-CAP 786432]" ";; [:s MM-NODE-CAP 33554432]")]
                   ["duplicate-override" (str text "\n;; [:s MM-NODE-CAP 786432]\n")]
                   ["missing-override" (.replace text ";; [:s MM-OUT-CAP 12582912]\n" "")]]]
        (doseq [[name bad] cases]
          (u/chk (not= bad text))
          (let [p (.joinpath work (str name ".policy")) destination (.joinpath work (str name ".kotoba"))]
            (.write_text p bad)
            (run name [tool normal p destination] :expected 1)
            (u/chk (not (.exists destination)))))
        (let [denied (.joinpath work "denied.kotoba")
              env2 (python/dict env)
              _ (operator/setitem env2 "KEXE_ALLOW" "37,38,39")
              r (run "no-fs-grant" [tool normal policy denied] :expected 120 :custom env2)]
          (u/chk (and (u/has-bytes? (.encode ":wire 35 :refused :not-granted") (.-stderr r)) (not (.exists denied)))))
        (.append routes (u/pydict "compiler" (u/pin compiler) "generator" (u/pin tool) "output" (u/pin good) "refusals" 8))))
    (u/chk (u/deq (u/geti (u/geti routes 0) "output") (u/geti (u/geti routes 1) "output")))
    (let [report (u/pydict "status" "PASS_NATIVE_STATIC_PROFILE_GENERATOR" "source" graph
                           "inputs" (u/pydict-from (for [p ["seed/MEMORY-MAP" "seed/00-ns.kotoba" "seed/gen-static-ns.kotoba"]] [p (u/pin (.joinpath root p))]))
                           "routes" routes "nativeGeneration" true "PythonGeneration" false)]
      (.write_text (.joinpath out "native-static-profile.json") (u/json-dump report))
      (println (u/geti report "status")))))

(defn -main [& args]
  (let [[build out complete] (u/parse-build-complete-output args)]
    (main build complete out)))

(when (some #(or (= % "check-static-profile-native.cljc") (str/ends-with? % "/check-static-profile-native.cljc")) sys/argv)
  (apply -main *command-line-args*))
