;; Observe native value/immutability and the unchanged runtime24 corpus.
;;
;; Basilisp stages exact sources and observes processes. The Kotoba fixture owns the copy/value verdict; this does
;; not replace either mandatory native CDCI role or promote compiler/root/public pins.
;; Ported from check-native-byte-copy.py (Basilisp). Linux only.
;; Run: basilisp run scripts/seed/check-native-byte-copy.cljc -- --compiler C --baseline B --output OUT
(ns check-native-byte-copy
  (:require [basilisp.string :as str]
            [gate-util :as u])
  (:import json operator pathlib platform re sys))

(defn main [compiler-arg baseline-arg output-arg]
  (u/chk (and (= "Linux" (platform/system)) (contains? #{"x86_64" "aarch64" "arm64"} (platform/machine))))
  (let [root u/root
        target (if (= "x86_64" (platform/machine)) "x86_64-linux" "aarch64-linux")
        out (.resolve output-arg)
        _ (.mkdir out ** :parents true :exist_ok false)
        raw (.joinpath out "raw")
        _ (.mkdir raw)
        ledger (python/list)
        build-env (python/dict {"PATH" "/nonexistent" "KEXE_CAP_RESOURCES_35" (str out) "KEXE_STACK_BYTES" "8388608"})
        guest-env (python/dict {"PATH" "/nonexistent" "KEXE_ALLOW" "-" "KEXE_FUEL" "1000000" "KEXE_STRUCTURED_REPORT" "1" "KEXE_ARENA_USE" "1"})
        compilers [["baseline" (.resolve baseline-arg)] ["candidate" (.resolve compiler-arg)]]
        fixture (.joinpath root "seed/tests/native-byte-copy.kotoba")
        cases (vec (u/geti (u/read-json (.joinpath root "seed/static-cases.json")) "cases"))
        _ (u/chk (= 24 (count cases)))
        records (python/dict)
        refused-src [["bytes-negative" "(bytes-count (bytes-from-vector-i64 [-1]))"]
                     ["bytes-256" "(bytes-count (bytes-from-vector-i64 [256]))"]
                     ["bytes-index-end" "(bytes-at (bytes-from-vector-i64 [0 255]) 2)"]
                     ["bytes-index-negative" "(bytes-at (bytes-from-vector-i64 [0 255]) -1)"]
                     ["bytes-slice-reversed" "(bytes-count (bytes-slice (bytes-from-vector-i64 [0 255]) 2 1))"]]
        refused (set (map first refused-src))]
    (operator/setitem records "copy-fixture" (.read_text fixture))
    (doseq [row cases] (operator/setitem records (u/geti row "name") (u/geti row "source")))
    ;; Deliberately wrong native value expectation must produce the fixture's negative verdict, not a successful
    ;; positive check or a build refusal.
    (operator/setitem records "copy-wrong-expectation"
                      (.replace (.read_text fixture) "want (bit-and (+ (* i 17) 23) 255)" "want (bit-and (+ (* i 17) 24) 255)"))
    (doseq [[k v] refused-src]
      (operator/setitem records k (str "(ns refused (:export [main]))\n(defn main [] :i64 " v ")\n")))
    (doseq [[name source] (.items records)]
      (let [observations (atom {})]
        (doseq [[lane compiler] compilers]
          (let [src (.joinpath out (str lane "-" name ".kotoba")) image (.joinpath out (str lane "-" name ".elf"))
                _ (.write_text src source)
                p (u/run-process [compiler "compile" src "--target" target "--output" image "--format" "static"] build-env 180 :cwd out)]
            (.write_bytes (.joinpath raw (str lane "-" name "-build.stdout")) (.-stdout p))
            (.write_bytes (.joinpath raw (str lane "-" name "-build.stderr")) (.-stderr p))
            (u/chk (and (zero? (.-returncode p)) (not (u/nonempty? (.-stderr p)))) [name lane (.-stdout p) (.-stderr p)])
            (.chmod image 0700)
            (let [env (if (str/starts-with? name "copy-")
                        (let [e (python/dict guest-env)] (operator/setitem e "KEXE_FUEL" "10000000") e)
                        guest-env)
                  p2 (u/run-process [image] env 30 :cwd out)]
              (.write_bytes (.joinpath raw (str lane "-" name ".stdout")) (.-stdout p2))
              (.write_bytes (.joinpath raw (str lane "-" name ".stderr")) (.-stderr p2))
              (swap! observations assoc lane [(.-returncode p2) (.-stdout p2) (.-stderr p2)])
              (.append ledger (u/pydict "name" name "lane" lane "source" (u/pin src) "image" (u/pin image) "exit" (.-returncode p2)
                                        "stdout" (u/pin (.joinpath raw (str lane "-" name ".stdout")))
                                        "stderr" (u/pin (.joinpath raw (str lane "-" name ".stderr")))))
              (.write_text (.joinpath out "calls.json") (u/json-dump ledger)))))
        (u/chk (= (get @observations "baseline") (get @observations "candidate")) ["result/fuel/arena drift" name])
        (let [[code stdout stderr] (get @observations "candidate")]
          (cond
            (str/starts-with? name "copy-")
            (let [want (if (= name "copy-wrong-expectation") -1 42)]
              (u/chk (and (zero? code) (u/has-bytes? (.encode (str ":result " want " ")) stdout)) [name code stdout stderr]))
            (contains? refused name)
            (u/chk (and (= 120 code) (u/has-bytes? (.encode "KEXE_TRAP") stderr)) [name code stdout stderr])
            :else
            (let [row (first (filter #(= name (u/geti % "name")) cases))
                  reference (u/geti row "reference")]
              (u/chk (= (u/geti reference "exit") code) [name code])
              (when-not (u/geti row "trap")
                (u/chk (u/has-bytes? (.encode (str ":result " (u/geti row "result") " ")) stdout) [name stdout])
                (u/chk (= (.encode (str (u/geti reference "remainingFuel")))
                          (.group (re/search (.encode ":remaining (\\d+)") stdout) 1))
                       [name stdout])))))))
    (let [report (u/pydict "schema" "amu.native-byte-copy-observation.v1" "status" "PASS_NATIVE_BYTE_COPY_AND_RUNTIME24"
                           "host" (python/list [(platform/system) (platform/machine)])
                           "compilers" (u/pydict-from (for [[k v] compilers] [k (u/pin v)]))
                           "fixture" (u/pin fixture) "corpus" (u/pin (.joinpath root "seed/static-cases.json")) "calls" ledger
                           "identicalResultsFuelAndArena" true "nativeFixturePositive" 42 "nativeWrongExpectation" -1
                           "runtimeCases" 24 "extraByteRefusals" (count refused-src) "publicReleaseQualified" false
                           "mandatoryCDCIReplaced" false)]
      (.write_text (.joinpath out "report.json") (u/json-dump report))
      (println (u/geti report "status"))
      (.flush sys/stdout))))

(defn -main [& args]
  (main (pathlib/Path (or (u/opt args "--compiler") (sys/exit "--compiler is required")))
        (pathlib/Path (or (u/opt args "--baseline") (sys/exit "--baseline is required")))
        (pathlib/Path (or (u/opt args "--output") (sys/exit "--output is required")))))

(when (some #(or (= % "check-native-byte-copy.cljc") (str/ends-with? % "/check-native-byte-copy.cljc")) sys/argv)
  (apply -main *command-line-args*))
