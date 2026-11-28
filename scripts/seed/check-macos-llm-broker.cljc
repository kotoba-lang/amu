;; Stage synthetic fixtures and observe the native compiler, packager and
;; broker. No provider or wire implementation runs in this harness.
;; basilisp run -p scripts/seed scripts/seed/check-macos-llm-broker.cljc -- --output NEW [--cli IMAGE]
(ns check-macos-llm-broker
  (:require [gate-util :as u]
            [macos-cli-build :as build]
            [macos-native-lib :as mac])
  (:import operator pathlib shutil subprocess sys))

(def schema "768859620bef185169b794b3ca1dbabb0de8e96186c61e698e61418afd27a034")
(def profile "amu-program-llm-v1")
(def fixture (.joinpath u/root "seed/tests/llm-v1-darwin-broker.kotoba"))

(defn- digest [path] (u/geti (mac/pin path) "sha256"))

(defn- grant-text [image seconds tokens]
  (str "KLG1\nartifact=" (digest image) "\nwire=11\nschema=" schema
       "\nprofile=" profile "\nprovider=synthetic-v1\nendpoint=local:wire11-fixture"
       "\nmodel=:synthetic/model\nseconds=" seconds "\ntokens=" tokens "\n"))

(defn- replace-once [text anchor replacement]
  (u/chk (= 1 (.count text anchor)) "broker test lost its unique fixture anchor")
  (.replace text anchor replacement))

(defn- native [out cli & args]
  (mac/process (into [cli] args) :cwd out :timeout 40
    :env (python/dict {"PATH" "/usr/bin:/bin" "LANG" "C"})))

(defn- guest [out cli name source]
  (let [path (.joinpath out (str name ".kotoba"))
        image (.joinpath out (str name ".macho"))
        _ (.write_text path source)
        result (native out cli "compile" path "--runtime-profile" profile "-o" image)]
    (u/chk (zero? (.-returncode result))
           (str name " native compile failed: " (.decode (.-stderr result) "utf-8" "replace")))
    (mac/verify-macho image)
    image))

(defn- check-case [report name result exit stdout calls diagnostic]
  (let [actual (.-returncode result)
        out (.decode (.-stdout result) "utf-8" "replace")
        err (.decode (.-stderr result) "utf-8" "replace")
        marker (if (nil? calls) "" (str "amu: wire11 provider-calls=" calls "\n"))]
    (u/chk (and (= actual exit) (= out stdout)
                (= (.count err "amu: wire11 provider-calls=") (if (nil? calls) 0 1))
                (or (nil? calls) (.__contains__ err marker))
                (.__contains__ err diagnostic))
           (str name " expected exit " exit ", stdout " (pr-str stdout) ", calls " calls
                ", got exit " actual ", stdout " (pr-str out) ", stderr " (pr-str err)))
    (.append report (u/pydict "case" name "exit" actual "stdout" out "providerCalls" calls))
    (println "PASS" name)
    (.flush sys/stdout)))

(defn- execute [report out cli name image grant exit stdout calls diagnostic]
  (let [path (.joinpath out (str name ".grant"))]
    (when (some? grant) (.write_text path grant))
    (check-case report name (native out cli "run-llm" image "--grant" path) exit stdout calls diagnostic)))

;; These built negative controls tamper only with the private channel. Each
;; uses a freshly checked source, native Mach-O and its own exact grant.
(defn- mutant-cli [out original name anchor replacement]
  (let [source (replace-once (.read_text mac/packager-source) anchor replacement)
        dir (.joinpath out name)
        sibling (.-parent original)
        compiler (.joinpath dir "amu-full-root.macho")
        bootstrap (.joinpath sibling "kotoba-packager-root.macho")]
    (.mkdir dir ** :mode 0700)
    (shutil/copyfile (.joinpath sibling "amu-full-root.macho") compiler)
    (.chmod compiler 0755)
    (let [packager (build/native-image compiler bootstrap dir "kotoba-packager-root" "fs2-cli-stdio-general"
                     (.encode source))
          stage (build/cli-unity-bytes u/root (build/cli-core-names)
                  (build/cli-pins (digest compiler) (digest packager)))]
      (build/native-image compiler packager dir "amu-cli" "amu-cli-host" stage))))

(defn- project-lock [entry module logical?]
  (let [path (fn [file] (if logical? (str "/" (.-name file)) (str file)))]
    (str "KSL2\nentry " (path entry) "\nmodule llm.broker-fixture " (path entry)
         "\nmodule llm.provider-fixture " (path module)
         "\nfile " (digest entry) " " (path entry) "\nfile " (digest module) " " (path module) "\n")))

(defn- locked-project [out name entry-source module-source]
  (let [dir (.joinpath out (str "ksl2-" name))
        entry (.joinpath dir "entry.kotoba")
        module (.joinpath dir "provider.kotoba")
        lock (.joinpath dir "project.ksl")]
    (.mkdir dir ** :mode 0700)
    (.write_text entry entry-source)
    (.write_text module module-source)
    (.write_text lock (project-lock entry module false))
    [dir entry module lock]))

(defn- locked-compile [cli [dir entry _module lock] image profile]
  (apply native dir cli "compile" entry "--source-lock" lock
    (if (nil? profile) ["-o" image] ["--runtime-profile" profile "-o" image])))

(defn- project-image [cli [_dir entry module _lock :as project] image artifacts name profile]
  (let [r (locked-compile cli project image profile)]
    (u/chk (zero? (.-returncode r)) (str name " locked compile: " (.decode (.-stderr r) "utf-8" "replace")))
    (mac/verify-macho image)
    (let [note (str "AMU-LLM-REQUIREMENT-V1\nwire 11 :llm/generate\nrequest :kotoba.llm/generate-request\n"
                    "result :kotoba.llm/result\nschema-sha256 " schema "\n")]
      (u/chk (= 1 (.count (.read_bytes image) (operator/add (u/bytes-of 0) (.encode note))))
             "linked image needs exactly one canonical wire-11 requirement"))
    (.append artifacts (u/pydict "name" name "macho" (mac/pin image) "entry" (mac/pin entry) "module" (mac/pin module)))
    image))

(defn- project-target-refusals [rows cli [dir entry module _lock]]
  (let [compiler (.joinpath (.-parent cli) "amu-full-root.macho")
        lock (.joinpath dir "logical.ksl")
        out (.joinpath dir "unsupported.out")]
    (.write_text lock (project-lock entry module true))
    (doseq [[name target extra code diagnostic]
            [["ksl2-x86-lowering" "x86_64-linux" ["--format" "kx64-v1"] 1 "E3004"]
             ["ksl2-x86-scoped-profile" "x86_64-linux" ["--format" "kx64-v1" "--runtime-profile" profile] 2 "E1"]
             ["ksl2-wasm-scoped-profile" "wasm32-browser" ["--runtime-profile" profile] 2 "E1"]]]
      (let [args (into ["compile" "/entry.kotoba" "--target" target "--output" (.-name out)
                        "--source-lock" (.-name lock) "--source-lock-sha256" (digest lock)] extra)]
        (check-case rows name (mac/native-run compiler dir args :expected code) code "" nil diagnostic)
        (u/chk (not (.exists out)) "unsupported target produced an artifact")))))

(defn- check-project [rows artifacts out cli src]
  (let [wrapper (str "(ns llm.broker-fixture (:require [llm.provider-fixture :as provider]) (:export [main]))\n"
                     "(defn main [] :i64 (provider/main))\n")
        implementation (replace-once src "ns llm.broker-fixture" "ns llm.provider-fixture")
        project (locked-project out "completion" wrapper implementation)
        [dir entry module lock] project
        artifact (project-image cli project (.joinpath dir "guest.macho") artifacts "ksl2-completion" profile)
        granted (grant-text artifact 5 42)
        repeat-project (locked-project out "repeat" wrapper implementation)
        again (project-image cli repeat-project (.joinpath (first repeat-project) "guest.macho") artifacts "ksl2-repeat" profile)]
    (u/chk (= (digest artifact) (digest again)) "signed project depends on its source location")
    (check-case rows "ksl2-check" (native dir cli "check" entry "--source-lock" lock) 0 "ok\n" nil "")
    (execute rows out cli "ksl2-completion" artifact granted 0 "101\n" 1 "")
    (execute rows out cli "ksl2-missing-grant" artifact nil 69 "" 0 "ELLMGRANT")
    (execute rows out cli "ksl2-artifact-mismatch" artifact
      (replace-once granted (digest artifact) (apply str (repeat 64 "0"))) 69 "" 0 "ELLMGRANT")
    (execute rows out cli "ksl2-wrong-schema" artifact
      (replace-once granted schema (apply str (repeat 64 "0"))) 69 "" 0 "ELLMGRANT")
    (execute rows out cli "ksl2-exhausted-tokens" artifact (grant-text artifact 5 41) 69 "" 0 "ELLMBROKER")
    (check-case rows "ksl2-ordinary-artifact" (native dir cli "run" artifact) 1 "" nil "EARTIFACT")
    (check-case rows "ksl2-ordinary-source" (native dir cli "run" entry "--source-lock" lock) 133 "" nil "")
    (check-case rows "ksl2-no-broker" (native dir artifact) 69 "" nil "")
    (let [entry-source (replace-once src "(:export [main])" "(:require [llm.provider-fixture :as provider]) (:export [main])")
          error-source (replace-once entry-source "\"ok\" 42" "\"error\" (provider/budget)")
          pure-module "(ns llm.provider-fixture (:export [budget]))\n(defn budget [] :i64 42)\n"
          error-project (locked-project out "error" error-source pure-module)
          image (project-image cli error-project (.joinpath (first error-project) "guest.macho") artifacts "ksl2-error" profile)]
      (execute rows out cli "ksl2-retryable-error" image (grant-text image 5 42) 0 "202\n" 1 "")
      (project-target-refusals rows cli error-project))
    (doseq [[name anchor replacement calls diagnostic]
            [["ksl2-wrong-model" ":synthetic/model" ":synthetic/other" 0 "ELLMBROKER"]
             ["ksl2-invalid-request" "\"ok\" 42" "\"ok\" 0" 0 "ELLMBROKER"]
             ["ksl2-invalid-response" "\"ok\" 42" "\"malformed-response\" 42" 1 "malformed"]]]
      (let [project (locked-project out name wrapper (replace-once implementation anchor replacement))
            image (project-image cli project (.joinpath (first project) "guest.macho") artifacts name profile)]
        (execute rows out cli name image (grant-text image 5 42) 69 "" calls diagnostic)))
    (let [bad-abi (replace-once wrapper "main []" "main [x :i64]")
          project (locked-project out "bad-abi" bad-abi implementation)
          dst (.joinpath (first project) "scoped.macho")]
      (check-case rows "ksl2-bad-main-abi" (locked-compile cli project dst profile) 1 "" nil "EABI")
      (u/chk (not (.exists dst)) "bad main ABI produced a scoped artifact")
      (let [plain (project-image cli project (.joinpath (first project) "plain.macho") artifacts "ksl2-ordinary-bad-abi" nil)]
        (execute rows out cli "ksl2-run-bad-main-abi" plain (grant-text plain 5 42) 1 "" 0 "EABI")))
    (let [bad-shape (replace-once implementation "[:temperature-milli :i64]" "[:temperature :i64]")
          project (locked-project out "bad-shape" wrapper bad-shape)
          dst (.joinpath (first project) "scoped.macho")]
      (check-case rows "ksl2-bad-nominal-shape" (locked-compile cli project dst profile) 1 "" nil "E2115")
      (u/chk (not (.exists dst)) "wrong nominal request produced an artifact"))
    (let [bad (.joinpath dir "tampered.macho")
          bytes (.read_bytes artifact)
          bundle (.index bytes (.encode "AMU-PROJECT-SOURCE-V1\n"))
          at (.index bytes (.encode "fixture system") bundle)]
      (.write_bytes bad (.join (u/bytes-of)
        (python/list [(operator/getitem bytes (python/slice 0 at)) (.encode "F")
                      (operator/getitem bytes (python/slice (inc at) nil))])))
      (execute rows out cli "ksl2-invalid-bundle" bad (grant-text bad 5 42) 69 "" 0 "EARTIFACT embedded project sources")
      (.write_bytes bad (operator/add bytes (u/bytes-of 0)))
      (execute rows out cli "ksl2-grant-for-tampered-image" bad (grant-text bad 5 42) 69 "" 0 "EARTIFACT signed guest differs"))
    (.write_text module (str implementation "\n;; stale lock fixture\n"))
    (check-case rows "ksl2-check-source-drift" (native dir cli "check" entry "--source-lock" lock) 1 "" nil "EINPUT")
    (let [dst (.joinpath dir "stale.macho")]
      (check-case rows "ksl2-compile-source-drift" (locked-compile cli project dst profile) 1 "" nil "EINPUT")
      (u/chk (not (.exists dst)) "stale lock produced an artifact"))
    (execute rows out cli "ksl2-signed-snapshot-after-source-drift" artifact granted 0 "101\n" 1 "")))

(defn- main [cli out]
  (u/chk (mac/available?) "Darwin arm64 required")
  (mac/verify-macho cli)
  (.mkdir out ** :mode 0700 :exist_ok false)
  (let [src (.read_text fixture)
        rows (python/list)
        artifacts (python/list)
        make (fn [launcher name text]
               (let [image (guest out launcher name text)]
                 (.append artifacts (u/pydict "name" name "macho" (mac/pin image) "source"
                                     (mac/pin (.joinpath out (str name ".kotoba")))))
                 image))
        ok (make cli "ok" src)
        again (make cli "repeat" src)
        granted (grant-text ok 5 42)]
    (u/chk (= (digest ok) (digest again)) "signed fixture did not reproduce")
    (execute rows out cli "completion" ok granted 0 "101\n" 1 "")
    (let [error (make cli "error" (replace-once src "\"ok\" 42" "\"error\" 42"))]
      (execute rows out cli "retryable-error" error (grant-text error 5 42) 0 "202\n" 1 ""))
    (execute rows out cli "missing-grant" ok nil 69 "" 0 "ELLMGRANT")
    (check-case rows "missing-grant-option" (native out cli "run-llm" ok) 2 "" 0 "usage:")
    (doseq [[name before after]
            [["artifact-mismatch" (digest ok) (apply str (repeat 64 "0"))]
             ["wrong-wire" "wire=11" "wire=12"]
             ["wrong-schema" schema (apply str (repeat 64 "0"))]
             ["wrong-profile" profile "amu-program"]
             ["missing-provider" "synthetic-v1" "unavailable-v1"]
             ["wrong-endpoint" "local:wire11-fixture" "local:other"]
             ["wrong-grant-model" ":synthetic/model" ":synthetic/other"]
             ["wrong-deadline" "seconds=5" "seconds=6"]
             ["trailing-grant" "tokens=42\n" "tokens=42\nextra\n"]]]
      (execute rows out cli name ok (replace-once granted before after) 69 "" 0 "ELLMGRANT"))
    (execute rows out cli "exhausted-tokens" ok (grant-text ok 5 41) 69 "" 0 "ELLMBROKER")
    (execute rows out cli "zero-tokens" ok (grant-text ok 5 0) 69 "" 0 "ELLMBROKER")
    (let [wrong (make cli "wrong-model" (replace-once src ":synthetic/model" ":synthetic/other"))
          malformed (make cli "malformed-request" (replace-once src "\"ok\" 42" "\"ok\" 0"))
          bad-result (make cli "bad-provider" (replace-once src "\"ok\" 42" "\"malformed-response\" 42"))
          late-src (replace-once src "(defn main"
                     "(defn- wait-forever [] :i64 (loop [i 0] (if (< i 0) i (recur (+ i 1)))))\n(defn main")
          late (make cli "deadline" (replace-once late-src "42 125)" "42 (wait-forever))"))]
      (execute rows out cli "request-model" wrong (grant-text wrong 5 42) 69 "" 0 "ELLMBROKER")
      (execute rows out cli "invalid-request" malformed (grant-text malformed 5 42) 69 "" 0 "ELLMBROKER")
      (execute rows out cli "invalid-response" bad-result (grant-text bad-result 5 42) 69 "" 1 "malformed")
      (execute rows out cli "timeout" late (grant-text late 1 42) 124 "" 0 "ETIME"))
    (let [changed (.joinpath out "tampered.macho")]
      (.write_bytes changed (operator/add (.read_bytes ok) (u/bytes-of 0)))
      (execute rows out cli "grant-for-tampered-image" changed (grant-text changed 5 42) 69 "" 0 "EARTIFACT"))
    (check-case rows "ordinary-run" (native out cli "run" ok) 1 "" nil "EARTIFACT")
    (check-case rows "no-broker" (native out ok) 69 "" nil "")
    (doseq [[name anchor replacement diagnostic]
            [["bad-transport-magic"
              "(mh-label 3) (mh-imm 0 3) (mh-mov 1 23)"
              "(mh-label 3) (mh-sb 31 24 0) (mh-imm 0 3) (mh-mov 1 23)"
              "ELLMBROKER"]
             ["bad-running-cdhash"
              "(mh-add 25 26 21) (mh-b 0x14000000 95)"
              "(mh-lb 8 22 1) (mh-imm 9 255) (mh-i 0xca090108) (mh-sb 8 22 1) (mh-add 25 26 21) (mh-b 0x14000000 95)"
              "ELLMBROKER"]]]
      (let [mutant (mutant-cli out cli name anchor replacement)
            image (make mutant (str name "-guest") src)]
        (execute rows out mutant name image (grant-text image 5 42) 69 "" 0 diagnostic)))
    (execute rows out cli "after-timeout" ok granted 0 "101\n" 1 "")
    (check-project rows artifacts out cli src)
    (.write_text (.joinpath out "receipt.json")
      (u/json-dump (u/pydict "schema" "amu.macos-wire11-broker.v1" "wire" 11
                     "sourceRevision" (.strip (.decode (subprocess/check_output
                       (python/list ["git" "rev-parse" "HEAD"]) ** :cwd u/root)))
                     "schemaSha256" schema "cli" (mac/pin cli)
                     "compiler" (mac/pin (.joinpath (.-parent cli) "amu-full-root.macho"))
                     "packager" (mac/pin (.joinpath (.-parent cli) "kotoba-packager-root.macho"))
                     "artifacts" artifacts "checks" rows "provider" "synthetic-v1")))
    (println "PASS_NATIVE_DARWIN_LLM_BROKER")
    (.flush sys/stdout)))

(defn -main [& args]
  (let [out (or (u/opt args "--output") (sys/exit "--output is required"))
        descriptor (u/read-json (.joinpath u/root "seed/bootstrap/aarch64-macos/cli.json"))
        cli (or (u/opt args "--cli") (.joinpath u/root (u/geti (u/geti descriptor "image") "path")))]
    (main (.resolve (pathlib/Path cli) ** :strict true) (.resolve (pathlib/Path out)))))

(when (some #(.endswith % "check-macos-llm-broker.cljc") sys/argv)
  (apply -main *command-line-args*))
