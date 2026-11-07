;; Selection, hostile ZIP and native cached-object round-trip controls.
;; Ported from test_fetch_bounded_cache.py. Native cases need AMU_BOUNDED_FIXTURE as before.
(ns test-fetch-bounded-cache
  (:require [basilisp.test :refer [deftest is]]
            [basilisp.string :as str]
            [bounded-cache-bundle :as b]
            [check-bounded-producer-attestation :as producer]
            [fetch-bounded-cache :as f]
            [sealed-image :as sealed]
            [verified-attestation :as attest])
  (:import hashlib os pathlib tempfile zipfile unittest.mock))

(def sha (apply str (repeat 40 "a")))
(def repo-id 1297097065)

(defn sha256 [data] (.hexdigest (hashlib/sha256 data)))

(defn fixture []
  (let [v (.get os/environ "AMU_BOUNDED_FIXTURE")]
    (when-not v (throw (python/RuntimeError "AMU_BOUNDED_FIXTURE is required for the native cases")))
    (.resolve (pathlib/Path v))))

(defn with-root [dir g]
  (with-open [tmp (tempfile/TemporaryDirectory ** :prefix "fetch-test-" :dir dir)]
    (g (pathlib/Path tmp))))

(deftest requires-exact-successful-main-run-and-repository
  (let [run {"id" 42 "event" "push" "status" "completed" "conclusion" "success" "head_branch" "main" "head_sha" sha
             "path" ".github/workflows/bounded-cache-producer.yml" "repository" {"id" repo-id}
             "head_repository" {"id" repo-id}}]
    (is (f/run-matches? run sha))
    (doseq [[field value] [["event" "pull_request"] ["conclusion" "failure"] ["head_branch" "other"]
                           ["head_sha" (apply str (repeat 40 "b"))] ["path" ".github/workflows/other.yml"]
                           ["repository" {"id" 1}] ["head_repository" {"id" 1}] ["id" true]]]
      (is (not (f/run-matches? (assoc run field value) sha)) field))))

(deftest requires-exact-artifact-and-run
  (let [run {"id" 42 "repository_id" repo-id "head_repository_id" repo-id "head_branch" "main" "head_sha" sha}
        artifact {"id" 3 "name" (str "experimental-bounded-kir-producer-" sha) "expired" false
                  "size_in_bytes" 1024 "digest" (str "sha256:" (apply str (repeat 64 "c"))) "workflow_run" run}]
    (is (f/artifact-matches? artifact 42 sha))
    (doseq [[field value] [["name" "other"] ["expired" true] ["size_in_bytes" 0] ["digest" "self-reported"] ["id" true]
                           ["workflow_run" (assoc run "id" 43)]
                           ["workflow_run" (assoc run "head_sha" (apply str (repeat 40 "b")))]
                           ["workflow_run" (assoc run "repository_id" 1)]]]
      (is (not (f/artifact-matches? (assoc artifact field value) 42 sha)) (str field value)))
    (is (nil? (f/select-artifact [] 42 sha)))
    (is (nil? (f/select-artifact [(assoc artifact "expired" true)] 42 sha)))
    (is (thrown? python/ValueError (f/select-artifact [artifact artifact] 42 sha)))
    (is (thrown? python/ValueError (f/select-artifact [(assoc artifact "digest" "forged")] 42 sha)))
    (is (thrown? python/ValueError (f/fetch-verified "main" "/nonexistent" (apply str (repeat 64 "0")) "/nonexistent/out")))))

(deftest preview-policy-is-explicit-and-never-matches-main-defaults
  (let [branch "codex/task-branch"
        workflow ".github/workflows/bounded-cache-preview.yml"
        run {"id" 42 "event" "push" "status" "completed" "conclusion" "success" "head_branch" branch "head_sha" sha
             "path" workflow "repository" {"id" repo-id} "head_repository" {"id" repo-id}}
        ref {"id" 42 "repository_id" repo-id "head_repository_id" repo-id "head_branch" branch "head_sha" sha}
        artifact {"id" 3 "name" (str "experimental-preview-" sha) "expired" false "size_in_bytes" 1024
                  "digest" (str "sha256:" (apply str (repeat 64 "c"))) "workflow_run" ref}]
    (is (not (f/run-matches? run sha)))
    (is (not (f/artifact-matches? artifact 42 sha)))
    (is (f/run-matches? run sha branch workflow))
    (is (f/artifact-matches? artifact 42 sha branch "experimental-preview-"))
    (let [policy (attest/attestation-policy "other/repo" "1" workflow (str "refs/heads/" branch) sha sha "push")]
      (is (thrown? python/ValueError (f/fetch-with-policy policy "experimental-preview-" "/nonexistent"
                                                          (apply str (repeat 64 "0")) "/nonexistent/out"))))))

(deftest zip-round-trip-keeps-fresh-native-admission
  (let [fx (fixture)]
    (with-root (.-parent fx)
      (fn [root]
        (let [bundle (.joinpath root "source.tar") archive (.joinpath root "artifact.zip") unpacked (.joinpath root "received.tar")]
          (b/pack (.joinpath fx "producer.elf") (.joinpath fx "cache") bundle)
          (with-open [z (zipfile/ZipFile archive "w" zipfile/ZIP_DEFLATED)]
            (.write z bundle "bounded-cache.tar"))
          (f/unzip-exact archive unpacked)
          (let [[image objects digest] (sealed/with-sealed-blob unpacked (fn [fd _] (b/extract-sealed fd (.joinpath root "bundle"))))]
            (producer/exercise image objects digest root)))))))

(deftest hostile-zip-is-never-extracted
  (with-root nil
    (fn [root]
      (doseq [kind ["traversal" "symlink" "extra"]]
        (let [archive (.joinpath root (str kind ".zip")) output (.joinpath root (str kind ".tar"))]
          (with-open [z (zipfile/ZipFile archive "w")]
            (let [name (if (= kind "traversal") "../escape" "bounded-cache.tar")
                  entry (zipfile/ZipInfo name)]
              (when (= kind "symlink")
                (set! (.-create_system entry) 3)
                (set! (.-external_attr entry) (bit-shift-left 0120777 16)))
              (.writestr z entry (.encode "x"))
              (when (= kind "extra") (.writestr z "stdout" (.encode "old result")))))
          (is (thrown? python/ValueError (f/unzip-exact archive output)) kind)
          (is (not (.exists output)) kind)
          (is (not (.exists (.joinpath root "escape"))) kind))))))

(defn- stub-pin! [stub body]
  (.write_text stub (str "#!/usr/bin/python3\n" body "\n"))
  (.chmod stub 0500)
  (sha256 (.read_bytes stub)))

(def stub-env (python/dict {"PATH" "/usr/bin:/bin"}))

(deftest metadata-stream-is-bounded-and-process-failure-is-refused
  ;; A pinned transport stub, never an attestation verifier.
  (with-root nil
    (fn [root]
      (let [stub (.joinpath root "metadata-stub")
            run-stub (fn [body g]
                       (when (.exists stub) (.chmod stub 0700))
                       (let [pin (stub-pin! stub body)]
                         (sealed/with-sealed-image stub pin g)))]
        (run-stub "import os; os.write(1, b'{\"ok\":true}')"
                  (fn [fd _] (is (= {"ok" true} (f/call fd stub-env "fixture")))))
        (run-stub "import os; b=b'x'*65536\nfor _ in range(65): os.write(1,b)"
                  (fn [fd _] (is (thrown-with-msg? python/ValueError #"size limit" (f/call fd stub-env "fixture")))))
        (run-stub "import os; os.write(1,b'{}'); raise SystemExit(7)"
                  (fn [fd _] (is (thrown-with-msg? python/ValueError #"request failed" (f/call fd stub-env "fixture")))))
        (run-stub "import os; os.write(1,b'not-json')"
                  (fn [fd _] (is (thrown? python/ValueError (f/call fd stub-env "fixture")))))
        (run-stub "import time; time.sleep(30)"
                  (fn [fd _]
                    (with-open [_ (unittest.mock/patch "select.select" ** :return_value (python/tuple [[] [] []]))]
                      (is (thrown-with-msg? python/TimeoutError #"timed out" (f/call fd stub-env "fixture"))))))))))

(deftest download-stream-size-digest-and-process-failure
  ;; A transport stub, not a provenance verifier or a compiler fallback.
  (with-root nil
    (fn [root]
      (let [stub (.joinpath root "stub")
            pin (stub-pin! stub "import os\nos.write(1, b'probe')")
            expected {"id" 1 "size_in_bytes" 5 "digest" (str "sha256:" (sha256 (.encode "probe")))}]
        (sealed/with-sealed-image stub pin
          (fn [fd _]
            (let [good (.joinpath root "good.zip")]
              (f/download fd stub-env expected good)
              (is (= (.encode "probe") (.read_bytes good)))
              (doseq [[name changed] [["size" (assoc expected "size_in_bytes" 4)]
                                      ["digest" (assoc expected "digest" (str "sha256:" (apply str (repeat 64 "0"))))]]]
                (is (thrown? python/ValueError (f/download fd stub-env changed (.joinpath root (str name ".zip")))) name)))))
        (.chmod stub 0700)
        (let [pin (stub-pin! stub "raise SystemExit(7)")]
          (sealed/with-sealed-image stub pin
            (fn [fd _]
              (is (thrown? python/ValueError (f/download fd stub-env expected (.joinpath root "failed.zip")))))))))))
