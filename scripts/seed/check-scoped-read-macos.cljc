;; Exercise KFR1 with a candidate native Darwin packager and FD3 scope.
;; Ported from check-scoped-read-macos.py (Basilisp, JUN-974). Apple Silicon macOS only.
;; Run: basilisp run -p scripts/seed scripts/seed/check-scoped-read-macos.cljc -- --compiler C --packager P --output DIR
(ns check-scoped-read-macos
  (:require [basilisp.string :as str]
            [gate-util :as u]
            [macos-native-lib :as mac]
            [macos-scope-build :as sb])
  (:import json pathlib sys))

(def source (.joinpath u/root "seed/tests/scoped-read/probe.kotoba"))
(def fs2-control
  (str "(ns fs2-control (:export [main]))\n"
       "(defn main [] :i64\n"
       "  (let [nul (string-from-utf8 (bytes-from-vector-i64 (vector-alloc 1)))\n"
       "        reply (typed-cap-call 35 :string :string (str nul \"FS2\" nul \"Ahello\" nul))]\n"
       "    (if (= reply (str nul \"FS2\" nul \"hello\\n\")) 0 1)))\n"))
(defn b [s] (.encode s))
(def hello-out (b "1 7 hello\n\n"))
(def refused-out (b "0 1 \n"))

(defn main [compiler packager out]
  (.mkdir out ** :parents false :exist_ok false)
  (let [compiler (.resolve compiler ** :strict true)
        packager (.resolve packager ** :strict true)
        p (fn [n] (.joinpath out n))
        image (sb/build compiler packager out "probe" source)]
    (.write_bytes (p "empty") (u/bytes-of))
    (.write_text (p "hello") "hello\n")
    (.write_bytes (p "big") (u/bytes-of-n (inc 1048576) 0x78))
    (.symlink_to (p "link") "hello")
    (.mkdir (p "folder"))
    (.write_text (.joinpath out "folder" "hello") "hello\n")
    (.symlink_to (p "parent-link") "folder" ** :target_is_directory true)
    (let [outside (.joinpath (.-parent out) (str (.-name out) "-outside"))
          cases (python/list)]
      (.write_text outside "protected-outside")
      (.symlink_to (p "outside-link") outside)
      (doseq [[name path expected output] [["regular" "hello" 0 hello-out] ["empty" "empty" 0 (b "1 1 \n")]
                                           ["missing" "missing" 2 refused-out] ["directory" "." 2 refused-out]
                                           ["too-large" "big" 2 refused-out] ["symlink" "link" 2 refused-out]
                                           ["outside" "../outside" 2 refused-out] ["nested" "folder/hello" 0 hello-out]
                                           ["virtual-root" "/folder/hello" 0 hello-out]
                                           ["parent-symlink" "parent-link/hello" 2 refused-out]
                                           ["outside-file" (str "../" (.-name outside)) 2 refused-out]
                                           ["outside-virtual-root" (str "/../" (.-name outside)) 2 refused-out]
                                           ["outside-link" "outside-link" 2 refused-out]
                                           ["nested-escape" (str "folder/../../" (.-name outside)) 2 refused-out]
                                           ["double-root" "//etc/passwd" 2 refused-out]
                                           ["empty-path" "" 2 refused-out]]]
        (println "checking" name)
        (.flush sys/stdout)
        (let [result (mac/native-run image out [path] :expected expected :timeout 30)]
          (when (or (not (u/deq (.-stdout result) output)) (u/nonempty? (.-stderr result)))
            (mac/fail (str [name (.-returncode result) (.-stdout result) (.-stderr result)])))
          (.append cases name)))
      (when (not= (.read_text outside) "protected-outside") (mac/fail "outside sentinel changed"))
      (let [src-text (.read_text source)
            ksl (.replace src-text "KFR1" "KSL1")
            _ (when (= ksl src-text) (mac/fail "source-lock control not constructed"))
            ksl-image (sb/build compiler packager out "ksl" ksl)
            ksl-result (mac/native-run ksl-image out ["hello"] :expected 0 :timeout 30)]
        (when (or (not (u/deq (.-stdout ksl-result) hello-out)) (u/nonempty? (.-stderr ksl-result)))
          (mac/fail (str ["source-lock regression" (.-stdout ksl-result) (.-stderr ksl-result)])))
        (.append cases "source-lock-existing-prefix"))
      (let [fs2-image (sb/build compiler packager out "fs2-control" fs2-control)
            fs2-result (mac/native-run fs2-image out [] :expected 0 :timeout 30)]
        (when (or (u/nonempty? (.-stdout fs2-result)) (u/nonempty? (.-stderr fs2-result)))
          (mac/fail (str ["existing FS2 regression" (.-stdout fs2-result) (.-stderr fs2-result)])))
        (.append cases "existing-fs2-read"))
      (.write_bytes (p "binary") (u/hex->bytes "00ff80"))
      (let [binary (sb/build compiler packager out "binary-control" (.joinpath u/root "seed/tests/scoped-read/binary.kotoba"))
            binary-result (mac/native-run binary out ["binary"] :expected 0 :timeout 30)]
        (when (or (u/nonempty? (.-stdout binary-result)) (u/nonempty? (.-stderr binary-result)))
          (mac/fail (str ["exact binary regression" (.-stdout binary-result) (.-stderr binary-result)])))
        (.append cases "exact-binary"))
      (let [sha (fn [path] (u/sha256-hex (.read_bytes path)))
            receipt (u/pydict "status" "PASS" "cases" cases "compilerSha256" (sha compiler) "packagerSha256" (sha packager)
                              "imageSha256" (sha image) "sourceSha256" (sha source)
                              "scope" "Mac arm64, synthetic FD3 scope; fleet integration unqualified")]
        (.write_text (p "receipt.json") (u/json-dump receipt))
        (println "PASS_SCOPED_READ_MACOS_ARM64")
        (.flush sys/stdout)))))

(defn -main [& args]
  (main (pathlib/Path (or (u/opt args "--compiler") (sys/exit "--compiler is required")))
        (pathlib/Path (or (u/opt args "--packager") (sys/exit "--packager is required")))
        (.resolve (pathlib/Path (or (u/opt args "--output") (sys/exit "--output is required"))))))

(when (some #(or (= % "check-scoped-read-macos.cljc") (str/ends-with? % "/check-scoped-read-macos.cljc")) sys/argv)
  (apply -main *command-line-args*))
