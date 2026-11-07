;; Supplemental native profile observations, not a replacement CDCI verdict.
;; Ported from check-native-runtime-profile.py (Basilisp). Linux only.
;; Run: basilisp run scripts/seed/check-native-runtime-profile.cljc -- --compiler C --output OUT
(ns check-native-runtime-profile
  (:require [basilisp.string :as str]
            [gate-util :as u])
  (:import json operator pathlib platform re sys time))

(def standard 4194304)
(def large 67108864)

(defn vectors [n]
  (str "(ns profile-bound (:export [main]))\n(defn main [] :i64\n"
       " (loop [i 0] (if (= i " n ") 0\n"
       "  (let [v (vector-alloc 0)] (if (= (vector-count v) 0) (recur (inc i)) 1)))))\n"))

(defn- ok-result? [stdout] (u/has-bytes? (.encode ":status :ok :result 0 ") stdout))
(defn- group-int [pattern data] (python/int (.group (re/search (.encode pattern) data) 1)))

(defn main [compiler out]
  (u/chk (and (= "Linux" (platform/system)) (contains? #{"aarch64" "x86_64"} (platform/machine))))
  (let [target (if (= "aarch64" (platform/machine)) "aarch64-linux" "x86_64-linux")
        root u/root
        _ (.mkdir out ** :parents true :exist_ok false :mode 0700)
        paths (u/manifest-paths (.joinpath root "seed/FULL-MANIFEST"))
        report (u/pydict "schema" "amu.native-runtime-profile-controls.v1" "status" "running"
                         "nativeVerdictAuthority" false "qualificationReplacement" false
                         "wholeCompilerQualified" false "performanceQualified" false
                         "compiler" (u/pin compiler)
                         "observer" (u/pin (.joinpath root "scripts/seed/check-native-runtime-profile.cljc"))
                         "host" (python/list [(platform/system) (platform/machine)])
                         "sources" (u/pydict-from (for [p paths] [p (u/pin (.joinpath root p))]))
                         "calls" (python/list) "mutations" (python/list))
        env (python/dict {"PATH" "/nonexistent" "KEXE_ALLOW" "35,37,38,39" "KEXE_CAP_RESOURCES_35" (str out) "KEXE_STACK_BYTES" "8388608"})
        runtime (python/dict {"PATH" "/nonexistent" "KEXE_ALLOW" "-" "KEXE_FUEL" "1000000000000" "KEXE_WALL_SECONDS" "300"
                              "KEXE_ARENA_USE" "1" "KEXE_STRUCTURED_REPORT" "1"})
        save (fn [] (.write_text (.joinpath out "observations.json") (u/json-dump report)))
        call (fn [name argv run-env]
               (let [start (time/monotonic)
                     r (u/run-process argv run-env 900 :cwd out)]
                 (doseq [[stream raw] [["stdout" (.-stdout r)] ["stderr" (.-stderr r)]]]
                   (.write_bytes (.joinpath out (str name "." stream)) raw))
                 (.append (u/geti report "calls")
                          (u/pydict "name" name "argv" (python/list (map str argv)) "exit" (.-returncode r) "seconds" (- (time/monotonic) start)))
                 (save)
                 (println name (.-returncode r))
                 (.flush sys/stdout)
                 r))
        build (fn [name text & {:keys [profile producer extra expected] :or {extra [] expected true}}]
                (let [source (.joinpath out (str name ".kotoba")) image (.joinpath out (str name ".elf"))
                      _ (.write_text source text)
                      argv (concat [(or producer compiler) "compile" source "--target" target "--output" image "--format" "static"]
                                   (when (some? profile) ["--runtime-profile" profile]) extra)
                      r (call (str "build-" name) argv env)]
                  (if expected
                    (do (u/chk (and (zero? (.-returncode r)) (not (u/nonempty? (.-stderr r))) (.is_file image)) [name (u/bslice (.-stderr r) -1000 nil)])
                        (.chmod image 0700)
                        (let [selected (or (not-empty profile) "standard-v1")]
                          (u/chk (u/has-bytes? (.encode (str ":runtime-profile :" selected)) (.-stdout r)))
                          (u/chk (u/has-bytes? (.encode (str ":vector-descriptors " (if (= selected "large-vectors-v1") large standard))) (.-stdout r))))
                        image)
                    (do (u/chk (and (not (zero? (.-returncode r))) (not (.exists image))) [name "accepted invalid profile"])
                        nil))))
        observe (fn [name image]
                  (let [r (call name [image] runtime)
                        fields (into {} (for [[k v] (re/findall (.encode ":([a-z-]+) ([0-9]+)") (.-stderr r))] [(.decode k) (python/int v)]))]
                    [r fields]))
        bounded (fn [name n profile & {:keys [overflow]}]
                  (let [image (build name (vectors n) :profile profile)
                        [r fields] (observe (str "run-" name) image)
                        limit (if (= profile "large-vectors-v1") large standard)]
                    (u/chk (and (= (get fields "vectors") (min n limit)) (= (get fields "vector-items") 0)) [name fields])
                    (if overflow
                      (u/chk (and (not (zero? (.-returncode r))) (u/has-bytes? (.encode "vector-table-exhausted") (.-stderr r))) [name (.-returncode r)])
                      (u/chk (and (zero? (.-returncode r)) (ok-result? (.-stdout r))) [name (.-stdout r) (.-stderr r)]))
                    image))
        plain (vectors 1)
        default (build "default" plain)
        std (build "standard" plain :profile "standard-v1")]
    (u/chk (= (.read_bytes default) (.read_bytes std)) "omission changed standard profile")
    (build "unknown" plain :profile "large-vectors-v2" :expected false)
    (build "empty" plain :profile "" :expected false)
    (build "duplicate" plain :profile "standard-v1" :extra ["--runtime-profile" "large-vectors-v1"] :expected false)
    (build "duplicate-identical" plain :profile "standard-v1" :extra ["--runtime-profile" "standard-v1"] :expected false)
    (build "missing-value" plain :extra ["--runtime-profile"] :expected false)
    (bounded "standard-at-limit" standard "standard-v1")
    (bounded "standard-over-limit" (inc standard) "standard-v1" :overflow true)
    (bounded "large-cross-standard" (inc standard) "large-vectors-v1")
    (bounded "large-at-limit" large "large-vectors-v1")
    (bounded "large-over-limit" (inc large) "large-vectors-v1" :overflow true)
    (doseq [case (u/geti (u/read-json (.joinpath root "seed/static-cases.json")) "cases")]
      (let [name (u/geti case "name")
            image (build (str "case-" name) (u/geti case "source") :profile "large-vectors-v1")
            e (python/dict runtime)
            _ (operator/setitem e "KEXE_FUEL" "1000000")
            r (call (str "case-" name) [image] e)
            remaining (re/search (.encode ":remaining ([0-9]+)") (.-stdout r))]
        (u/chk (u/deq (u/pydict "exit" (.-returncode r) "remainingFuel" (when remaining (python/int (.group remaining 1)))) (u/geti case "reference")))
        (if (u/geti case "trap")
          (u/chk (u/has-bytes? (.encode ":status :trap") (.-stdout r)))
          (u/chk (= (group-int ":result (-?[0-9]+)" (.-stdout r)) (u/geti case "result"))))))
    (let [zero-source (.read_text (.joinpath root "seed/tests/native-zero-watermark.kotoba"))
          zero (build "zero-rollback" zero-source :profile "large-vectors-v1")
          [r _] (observe "zero-rollback" zero)
          _ (u/chk (and (zero? (.-returncode r)) (ok-result? (.-stdout r))))
          unity (.decode (.join (u/bytes-of) (python/list (for [p paths] (operator/add (.read_bytes (.joinpath root p)) (.encode "\n"))))))
          marker "(mem-u2dec (if (= profile 1) 67108864 4194304))"
          start (.index unity "(defn- xs-profile-prelude ")
          end (.index unity "(defn- xs-command " start)
          prelude (subs unity start end)
          _ (u/chk (= 1 (.count prelude marker)))
          changed (str (subs unity 0 start) (.replace prelude marker "(mem-u2dec 4194304)") (subs unity end))
          mutant (build "selection-mutant-compiler" changed)
          bad (build "selection-mutant" (vectors (inc standard)) :profile "large-vectors-v1" :producer mutant)
          [r fields] (observe "detect-selection-mutant" bad)]
      (u/chk (and (not (zero? (.-returncode r))) (u/has-bytes? (.encode "vector-table-exhausted") (.-stderr r)) (= standard (get fields "vectors"))))
      (.append (u/geti report "mutations") (u/pydict "name" "wrong-profile-selection" "builtSuccessfully" true "executed" true
                                                    "compiler" (u/pin mutant) "image" (u/pin bad)))
      ;; Real unchanged growth-row limit, including the exact-copy fallback.
      (let [region-source (.read_text (.joinpath root "seed/tests/native-profile-region-bound.kotoba"))
            region (build "region-at-limit-plus-one" region-source :profile "large-vectors-v1")
            [r fields] (observe "region-at-limit-plus-one" region)]
        (u/chk (and (zero? (.-returncode r)) (ok-result? (.-stdout r))))
        (u/chk (= {"regions" standard "reserved-words" (* standard 2) "vectors" (* (inc standard) 3) "vector-items" (- (* (inc standard) 6) 2)}
                  (into {} (for [k ["regions" "reserved-words" "vectors" "vector-items"]] [k (get fields k)]))))
        (let [region-marker "(def KXRT-REGIONS 4194304)"
              _ (u/chk (= 2 (.count unity region-marker)))
              region-mutant (build "region-mutant-compiler" (.replace unity region-marker "(def KXRT-REGIONS 67108864)"))
              region-bad (build "region-mutant" region-source :profile "large-vectors-v1" :producer region-mutant)
              [r fields] (observe "detect-region-mutant" region-bad)]
          (u/chk (and (zero? (.-returncode r)) (ok-result? (.-stdout r))))
          (u/chk (and (= (inc standard) (get fields "regions")) (= (* (inc standard) 2) (get fields "reserved-words"))))
          (.append (u/geti report "mutations") (u/pydict "name" "region-limit-broadening" "builtSuccessfully" true "executed" true
                                                        "compiler" (u/pin region-mutant) "image" (u/pin region-bad)
                                                        "detectedBy" "native arena accounting differs from fixed region oracle"))))
      (let [bound-marker "(>= u KXRT-VECTORS)"
            _ (u/chk (= 2 (.count unity bound-marker)))
            bound-mutant (build "bound-mutant-compiler" (.replace unity bound-marker "(> u KXRT-VECTORS)"))
            bound-bad (build "bound-mutant" (vectors (inc standard)) :profile "standard-v1" :producer bound-mutant)
            [r _] (observe "detect-bound-mutant" bound-bad)]
        (u/chk (not (u/has-bytes? (.encode "vector-table-exhausted") (.-stderr r))) "mutant did not remove the expected refusal")
        (.append (u/geti report "mutations") (u/pydict "name" "off-by-one-vector-bound" "builtSuccessfully" true "executed" true
                                                      "compiler" (u/pin bound-mutant) "image" (u/pin bound-bad)
                                                      "detectedBy" "missing named vector-table refusal")))
      (let [highwater "r (kxrt-store64 (+ (kxrt-gl 688) (* u 8)) 0) high (if (> (+ off n) (kxrt-gl 760)) (kxrt-gs 760 (+ off n)) 0) w (kxrt-gs 48 (inc u))"
            without "r (kxrt-store64 (+ (kxrt-gl 688) (* u 8)) 0) w (kxrt-gs 48 (inc u))"]
        (u/chk (= 2 (.count unity highwater)))
        (doseq [[name changed] [["missing-watermark" (.replace unity highwater without)]
                                ["relative-watermark" (.replace unity "(kxrt-gs 760 (+ off n))" "(kxrt-gs 760 n)")]
                                ["last-word" (.replace unity "byte-end (+ base (* 8 count))" "byte-end (+ base (* 8 (if (> count 0) (dec count) 0)))")]]]
          (let [mutated (build (str name "-compiler") changed)
                bad (build (str name "-oracle") zero-source :profile "large-vectors-v1" :producer mutated)
                [r _] (observe (str "detect-" name) bad)]
            (u/chk (and (zero? (.-returncode r)) (u/has-bytes? (.encode ":status :ok :result 1 ") (.-stdout r))))
            (.append (u/geti report "mutations") (u/pydict "name" name "builtSuccessfully" true "executed" true
                                                          "compiler" (u/pin mutated) "image" (u/pin bad)
                                                          "detectedBy" "native zero/rollback oracle returns one"))))))
    (u/chk (every? (fn [[p value]] (u/deq (u/pin (.joinpath root p)) value)) (.items (u/geti report "sources"))))
    (doseq [[k v] [["status" "PASS_NATIVE_PROFILE_OBSERVATIONS"] ["defaultExplicitStandardIdentical" true]
                   ["regionMutationControlsPending" false] ["nativeControllerQualificationPending" true]]]
      (operator/setitem report k v))
    (save)))

(defn -main [& args]
  (main (.resolve (pathlib/Path (or (u/opt args "--compiler") (sys/exit "--compiler is required"))))
        (.resolve (pathlib/Path (or (u/opt args "--output") (sys/exit "--output is required"))))))

(when (some #(or (= % "check-native-runtime-profile.cljc") (str/ends-with? % "/check-native-runtime-profile.cljc")) sys/argv)
  (apply -main *command-line-args*))
