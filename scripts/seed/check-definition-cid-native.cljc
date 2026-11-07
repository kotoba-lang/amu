;; Stage fixed identity vectors and observe an Amu-built native validator.
;;
;; The native module owns CBOR/normalized-payload checks, SHA-256 and CIDv1. This script neither canonicalizes
;; definitions nor emits native formats. This is identity codec qualification, not checked-frontend, SCC or cache
;; qualification. Ported from check-definition-cid-native.py (Basilisp, JUN-974).
;; Run: basilisp run -p scripts/seed scripts/seed/check-definition-cid-native.cljc -- --compiler C --output DIR
(ns check-definition-cid-native
  (:require [basilisp.string :as str]
            [gate-util :as u]
            [macos-image :as macos])
  (:import json operator pathlib platform re subprocess sys time))

(def modules ["seed/03-source-sha256.kotoba" "seed/04-definition-cid.kotoba" "seed/tests/native-definition-cid.kotoba"])

(defn replace-once [block before after]
  (u/chk (= 1 (.count block before)) before)
  (.replace block before after))

(defn hexs [s] (.hex (.encode s)))

(defn main [compiler out]
  (let [darwin (macos/available?)
        _ (u/chk (or darwin (and (= "Linux" (platform/system)) (contains? #{"aarch64" "x86_64"} (platform/machine)))))
        root u/root
        _ (.mkdir out ** :parents false :mode 0700 :exist_ok false)
        packager (when darwin (second (macos/root-images)))
        vectors-path (.joinpath root "seed/tests/definition-cid-vectors.json")
        vectors (u/read-json vectors-path)
        vecs (vec (u/geti vectors "vectors"))
        _ (u/chk (= 10 (count vecs)))
        source (.joinpath out "definition-cid.kotoba")
        _ (.write_bytes source (operator/add (.encode "(ns seed.definition-cid (:export [main]))\n")
                                             (.join (.encode "\n") (python/list (for [p modules] (.read_bytes (.joinpath root p)))))))
        target (cond darwin "aarch64-macos" (= "aarch64" (platform/machine)) "aarch64-linux" :else "x86_64-linux")
        image (atom (.joinpath out (if darwin "definition-cid.macho" "definition-cid.elf")))
        env (python/dict {"PATH" "/nonexistent" "KEXE_STACK_BYTES" "8388608" "KEXE_FUEL" "1000000000"})
        env+ (fn [& kvs] (let [d (python/dict env)] (doseq [[k v] (partition 2 kvs)] (operator/setitem d k v)) d))
        report (u/pydict "schema" "amu.native-definition-cid-codec.v1" "host" (python/list [(platform/system) (platform/machine)])
                         "compiler" (u/pin compiler)
                         "modules" (u/pydict-from (for [p modules] [p (u/pin (.joinpath root p))]))
                         "frozenVectors" (u/pin vectors-path) "source" (u/pin source) "calls" (python/list)
                         "nativeVerdictAuthority" false "checkedFrontendQualified" false "sccQualified" false
                         "persistentBuildQualified" false "admittedTextProfile" "ASCII" "emulation" false)
        save (fn [] (.write_text (.joinpath out "observations.json") (u/json-dump report)))
        run (fn run [name argv process-env & {:keys [result cid canonical unexpected-cid]}]
              (let [started (time/monotonic)
                    mac-run? (and darwin (not= (str (first argv)) (str compiler)))
                    p (if mac-run?
                        (macos/run (first argv) out (rest argv) :timeout 300)
                        (subprocess/run (python/list (map str argv)) ** :env process-env :cwd out :capture_output true :timeout 300))]
                (doseq [[stream raw] [["stdout" (.-stdout p)] ["stderr" (.-stderr p)]]]
                  (.write_bytes (.joinpath out (str name "." stream)) raw))
                (let [row (u/pydict "name" name "exit" (.-returncode p) "seconds" (- (time/monotonic) started)
                                    "stdoutSHA256" (u/sha256-hex (.-stdout p)) "stderrSHA256" (u/sha256-hex (.-stderr p)))
                      expected-exit (if mac-run? (or result 0) 0)]
                  (.append (u/geti report "calls") row)
                  (save)
                  (u/chk (and (= expected-exit (.-returncode p)) (not (u/nonempty? (.-stderr p)))) (str name " " (.-returncode p)))
                  (when-not (nil? result)
                    (when-not darwin
                      (u/chk (re/search (operator/add (operator/add (.encode ":result ") (.encode (str result))) (.encode "\\b")) (.-stdout p)) name))
                    (let [actual (vec (re/findall (.encode "^b[a-z2-7]+$") (.-stdout p) re/M))]
                      (if unexpected-cid
                        (u/chk (= 1 (count actual)) name)
                        (u/chk (= actual (if (nil? cid) [] [(.encode cid)])) name))
                      (when-not (nil? canonical)
                        (u/chk (u/deq (first (.splitlines (.-stdout p))) (.encode canonical)) name))))
                  (println (json/dumps row))
                  (.flush sys/stdout))))]
    (if darwin
      (let [[img unsigned] (macos/build compiler packager out (.-name source) "definition-cid")]
        (reset! image img)
        (operator/setitem report "unsignedImage" (u/pin unsigned)))
      (do (run "build" [compiler "compile" source "--target" target "--output" @image "--format" "static"]
               (env+ "KEXE_CAP_RESOURCES_35" (str out) "KEXE_ALLOW" "35,37,38,39"))
          (.chmod @image 0755)))
    (operator/setitem report "image" (u/pin @image))
    (let [execution-env (env+ "KEXE_ALLOW" "37,38" "KEXE_STRUCTURED_REPORT" "1")]
      (doseq [v vecs]
        (run (u/geti v "name") [@image (u/geti v "hex")] execution-env :result 0 :cid (u/geti v "cid"))
        (run (str "construct-" (u/geti v "name")) [@image (str "construct:" (u/geti v "name"))] execution-env
             :result 0 :cid (u/geti v "cid") :canonical (u/geti v "hex")))
      (let [pure (u/geti (first vecs) "hex")
            effects (u/geti (first (filter #(= "effect-row-two" (u/geti % "name")) vecs)) "hex")
            deps (u/geti (first (filter #(= "dependencies-two" (u/geti % "name")) vecs)) "hex")
            first-pair "8282626b776c646570656e64656e63696573826376656380"
            desugar "8282626b777818646573756761722d636f6e74726163742d76657273696f6e8263696e746131"
            one "82626b7774686f73742f636c6f636b2d6d6f6e6f746f6e6963"
            two "82626b7769686f73742f68747470"
            dep-names ["bafyreib4oafkwcwsvzyxjysuwmsb2zigmiece4pihcwzoekssg4fk34cha"
                       "bafyreihzlbfbvi3w24l3n6ofovirnqvyj74zkwtld6pqaor2qg4zk26wgi"]
            [dep-one dep-two] (for [s dep-names] (str "8263737472783b" (hexs s)))
            tail (fn [s n] (subs s (- (count s) n)))
            cases [["empty" ""] ["odd-hex" (subs pure 0 (dec (count pure)))] ["bad-hex" (str "zz" (subs pure 2))]
                   ["truncated" (subs pure 0 (- (count pure) 2))] ["trailing" (str pure "00")] ["wrong-major" (str "a2" (subs pure 2))]
                   ["overlong-array" (str "9802" (subs pure 2))] ["indefinite-array" (str "9f" (subs pure 2))]
                   ["unknown-normal-tag" (replace-once pure "82636d617087" "8263666f6f87")]
                   ["unsorted-map" (replace-once pure (str first-pair desugar) (str desugar first-pair))]
                   ["duplicate-map-key" (replace-once pure desugar first-pair)]
                   ["extra-sealed-field" (str (replace-once pure "82636d617087" "82636d617088") "8282626b77627a7a8263696e746130")]
                   ["wrong-payload-version" (replace-once pure "696f6e8263696e746132" "696f6e8263696e746133")]
                   ["missing-field" (replace-once pure "6a6566666563742d726f77" "6a6566666563742d726f78")]
                   ["wrong-effect-type" (replace-once pure "826373657480" "826376656380")]
                   ["wire-effect" (replace-once effects "82626b7769686f73742f68747470" "826373747269686f73742f68747470")]
                   ["unsorted-effects" (replace-once effects (str one two) (str two one))]
                   ["duplicate-effects" (replace-once effects (str one two) (str two two))]
                   ["unsorted-dependencies" (replace-once deps (str dep-one dep-two) (str dep-two dep-one))]
                   ["duplicate-dependencies" (replace-once deps dep-two dep-one)]
                   ["bad-cid-padding" (replace-once deps (hexs (first dep-names)) (hexs (str (subs (first dep-names) 0 (dec (count (first dep-names)))) "b")))]
                   ["bad-cid-header" (replace-once deps (hexs (first dep-names)) (hexs (str (subs (first dep-names) 0 7) "z" (subs (first dep-names) 8))))]
                   ["non-ascii" (replace-once pure "65636f6e7374" "66636f6ec3a974")]
                   ["too-deep" (str (apply str (repeat 66 "82")) "636e696c")]]
            cmap (into {} cases)]
        (doseq [[name block] cases]
          (run (str "refuse-" name) [@image block] execution-env :result 1))
        (run "native-boundaries" [@image "native-boundary-tests"] execution-env :result 0)
        (run "native-encoder-refusals" [@image "native-encoder-refusals"] execution-env :result 0)
        (run "refuse-no-argument" [@image] execution-env :result 2)
        (run "refuse-extra-argument" [@image pure pure] execution-env :result 2)
        ;; Each changed validator builds successfully, then actually demonstrates the forbidden acceptance (or fails the
        ;; paired boundary self-check). A compiler error or an unexecuted mutant is never a detected mutation.
        (let [original (.read_text source)
              mutations [["map-set-order" "(or (= mode 0) (= last 0) (< (dc-compare D V last item) 0))" "true" "unsorted-map"]
                         ["dependency-uniqueness" "(> (string-compare text last) 0)" "true" "duplicate-dependencies"]
                         ["sealed-field-count" "(= (dc-at D (dc-child D n 1) 2) 7)" "true" "extra-sealed-field"]
                         ["minimal-cbor" "(or (< value minimum) (> value dc-limit))" "(> value dc-limit)" "overlong-array"]
                         ["complete-block" "(not= (vector-at D 0) (vector-count V))\n                (not (dc-payload? D V 1))"
                          "false\n                (not (dc-payload? D V 1))" "trailing"]
                         ["block-bound" "(> (string-length s) (* dc-limit 2))" "false" nil]
                         ["depth-bound" "(> depth (dip-codec-depth (vector-at D 5)))" "false" nil]]]
          (operator/setitem report "mutationControls" (python/list))
          (doseq [[name old new probe] mutations]
            (u/chk (= 1 (.count original old)) (str name " mutation anchor drift"))
            (let [changed (.joinpath out (str "mutant-" name ".kotoba"))
                  _ (.write_text changed (.replace original old new))
                  mutant (if darwin
                           (first (macos/build compiler packager out (.-name changed) (str "mutant-" name)))
                           (let [m (.joinpath out (str "mutant-" name ".elf"))]
                             (run (str "build-mutant-" name)
                                  [compiler "compile" changed "--target" target "--output" m "--format" "static"]
                                  (env+ "KEXE_CAP_RESOURCES_35" (str out) "KEXE_ALLOW" "35,37,38,39"))
                             (.chmod m 0755)
                             m))]
              (run (str "detect-mutant-" name) [mutant (if probe (get cmap probe) "native-boundary-tests")] execution-env
                   :result (if probe 0 1) :unexpected-cid (boolean probe))
              (.append (u/geti report "mutationControls")
                       (u/pydict "removedGuard" name "source" (u/pin changed) "image" (u/pin mutant)
                                 "builtSuccessfully" true "executed" true))))
          (.update report (u/pydict "status" "PASS_NATIVE_DEFINITION_CID_CODEC" "positiveVectors" 10 "nativeEncodedVectors" 10
                                    "refusalControls" (+ (count cases) 2) "nativeBoundaryPairs" 3 "nativeEncoderChecks" 9
                                    "sourceIdentity" (u/geti vectors "sourceSHA256")))
          (save)
          (println (u/geti report "status"))
          (.flush sys/stdout))))))

(defn -main [& args]
  (main (.resolve (pathlib/Path (or (u/opt args "--compiler") (sys/exit "--compiler is required"))))
        (.resolve (pathlib/Path (or (u/opt args "--output") (sys/exit "--output is required"))))))

(when (some #(or (= % "check-definition-cid-native.cljc") (str/ends-with? % "/check-definition-cid-native.cljc")) sys/argv)
  (apply -main *command-line-args*))
