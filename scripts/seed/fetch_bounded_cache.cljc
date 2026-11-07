;; Fetch an exact main-run bounded fixture and verify before using it.
;;
;; The source SHA and verifier pin must be supplied by trusted host configuration,
;; not by the downloaded artifact or a PR-controlled cache record. A missing
;; candidate is distinct from a malformed or unauthenticated one. This is not
;; whole-compiler cache admission.
;; Ported from fetch_bounded_cache.py (Basilisp). Linux only (/proc/self/fd, seals).
;; Run: basilisp run scripts/seed/fetch_bounded_cache.cljc -- --source-sha S --gh G --output O
;; Exit code 75 means CACHE_UNAVAILABLE.
(ns fetch-bounded-cache
  (:require [basilisp.string :as str]
            [bounded-cache-bundle :as bundle]
            [check-bounded-producer-attestation :as producer]
            [sealed-image :as sealed]
            [verified-attestation :as attest])
  (:import hashlib json operator os pathlib re select stat subprocess sys tempfile time urllib.parse zipfile))

(def repo "kotoba-lang/amu")
(def repo-id 1297097065)
(def workflow ".github/workflows/bounded-cache-producer.yml")
(def prefix "experimental-bounded-kir-producer-")

(defn- value-error [message] (python/ValueError message))

(defn cache-unavailable
  "No successful producer exists for this exact source revision."
  [message]
  (ex-info message {::cache-unavailable true}))

(defn cache-unavailable? [e] (boolean (::cache-unavailable (ex-data e))))

(defn- from-py [x]
  (cond (instance? python/dict x) (into {} (map (fn [[k v]] [k (from-py v)])) (.items x))
        (instance? python/list x) (mapv from-py x)
        :else x))

(defn- real-int?
  "A positive JSON integer; Python's True is an int but never an id."
  [x]
  (and (int? x) (not (instance? python/bool x)) (pos? x)))

(defn run-matches?
  ([row sha] (run-matches? row sha "main" workflow))
  ([row sha branch wf]
   (boolean
     (and (= "push" (get row "event")) (= "completed" (get row "status")) (= "success" (get row "conclusion"))
          (= branch (get row "head_branch")) (= sha (get row "head_sha")) (= wf (get row "path"))
          (= repo-id (get-in row ["repository" "id"])) (= repo-id (get-in row ["head_repository" "id"]))
          (real-int? (get row "id"))))))

(defn artifact-matches?
  ([row run-id sha] (artifact-matches? row run-id sha "main" prefix))
  ([row run-id sha branch pfx]
   (let [run (or (get row "workflow_run") {})
         size (get row "size_in_bytes")]
     (boolean
       (and (= (str pfx sha) (get row "name"))
            (false? (get row "expired")) (real-int? (get row "id"))
            (real-int? size) (<= size sealed/max-image-bytes)
            (re/fullmatch "sha256:[0-9a-f]{64}" (or (get row "digest") ""))
            (= run-id (get run "id")) (= repo-id (get run "repository_id"))
            (= repo-id (get run "head_repository_id")) (= branch (get run "head_branch"))
            (= sha (get run "head_sha")))))))

(defn select-artifact
  ([rows run-id sha] (select-artifact rows run-id sha "main" prefix))
  ([rows run-id sha branch pfx]
   (let [candidates (filterv #(= (str pfx sha) (get % "name")) rows)]
     (when (> (count candidates) 1) (throw (value-error "ambiguous producer artifacts")))
     (if (or (empty? candidates) (true? (get (first candidates) "expired")))
       nil
       (do (when-not (artifact-matches? (first candidates) run-id sha branch pfx)
             (throw (value-error "producer artifact metadata mismatch")))
           (first candidates))))))

(defn unzip-exact
  "Extract one regular bounded tar, never paths supplied by a zip."
  [path destination]
  (with-open [archive (zipfile/ZipFile path)]
    (let [entries (python/list (.infolist archive))]
      (when (not= 1 (count entries)) (throw (value-error "unexpected artifact archive entries")))
      (let [info (first entries)
            mode (bit-shift-right (.-external_attr info) 16)]
        (when (or (not= (.-filename info) "bounded-cache.tar") (.is_dir info)
                  (and (not= 0 mode) (not (stat/S_ISREG mode)))
                  (not= 0 (bit-and (.-flag_bits info) 1))
                  (not (contains? #{zipfile/ZIP_STORED zipfile/ZIP_DEFLATED} (.-compress_type info)))
                  (not (< 0 (.-file_size info) (inc sealed/max-image-bytes))))
          (throw (value-error "invalid artifact archive entry")))
        (let [fd (os/open destination (bit-or os/O_WRONLY os/O_CREAT os/O_EXCL os/O_NOFOLLOW) 0600)]
          (try
            (with-open [out (os/fdopen fd "wb")
                        source (.open archive info)]
              (loop [total 0]
                (let [data (.read source (* 1024 1024))]
                  (if (seq data)
                    (let [total (+ total (count data))]
                      (when (or (> total (.-file_size info)) (> total sealed/max-image-bytes))
                        (throw (value-error "artifact entry exceeds its limit")))
                      (.write out data)
                      (recur total))
                    (when (not= total (.-file_size info))
                      (throw (value-error "truncated artifact entry")))))))
            (catch python/BaseException e
              (.unlink (pathlib/Path destination) ** :missing_ok true)
              (throw e))))))))

(defn- stop-process! [proc]
  (.close (.-stdout proc))
  (when (nil? (.poll proc))
    (.kill proc)
    (.wait proc)))

(defn call
  "Bound the stream while reading it: capture_output would allocate all producer-controlled metadata before
  the length check could run."
  [gh-fd env endpoint]
  (let [limit (* 4 1024 1024)
        deadline (+ (time/monotonic) 120)]
    (with-open [errors (tempfile/TemporaryFile)]
      (let [proc (subprocess/Popen (python/list [(str "/proc/self/fd/" gh-fd) "api" endpoint]) ** :env env
                                   :pass_fds (python/tuple [gh-fd]) :stdout subprocess/PIPE :stderr errors)]
        (try
          (let [chunks (loop [chunks [] total 0]
                         (let [remaining (- deadline (time/monotonic))]
                           (when (or (<= remaining 0) (empty? (first (select/select [(.-stdout proc)] [] [] remaining))))
                             (throw (python/TimeoutError "GitHub metadata request timed out")))
                           (let [data (os/read (.fileno (.-stdout proc)) (min (* 1024 1024) (- (inc limit) total)))]
                             (if (empty? data)
                               chunks
                               (let [total (+ total (count data))]
                                 (when (> total limit) (throw (value-error "GitHub metadata exceeds size limit")))
                                 (recur (conj chunks data) total))))))]
            (when (not= 0 (.wait proc ** :timeout (max 0.1 (- deadline (time/monotonic)))))
              (throw (value-error "GitHub metadata request failed")))
            (from-py (json/loads (.join (python/bytes) (python/list chunks)))))
          (finally (stop-process! proc)))))))

(defn download [gh-fd env artifact output]
  (let [endpoint (str "repos/" repo "/actions/artifacts/" (get artifact "id") "/zip")
        digest (hashlib/sha256)]
    (with-open [errors (tempfile/TemporaryFile)
                dest (.open (pathlib/Path output) "xb")]
      (let [proc (subprocess/Popen (python/list [(str "/proc/self/fd/" gh-fd) "api" endpoint]) ** :env env
                                   :pass_fds (python/tuple [gh-fd]) :stdout subprocess/PIPE :stderr errors)
            deadline (+ (time/monotonic) 120)]
        (try
          (let [total (loop [total 0]
                        (let [remaining (- deadline (time/monotonic))]
                          (when (or (<= remaining 0) (empty? (first (select/select [(.-stdout proc)] [] [] remaining))))
                            (throw (python/TimeoutError "artifact download timed out")))
                          (let [data (os/read (.fileno (.-stdout proc)) (* 1024 1024))]
                            (if (empty? data)
                              total
                              (let [total (+ total (count data))]
                                (when (or (> total sealed/max-image-bytes) (> total (get artifact "size_in_bytes")))
                                  (throw (value-error "download exceeds declared size")))
                                (.update digest data)
                                (.write dest data)
                                (recur total))))))]
            (when (or (not= 0 (.wait proc ** :timeout (max 0.1 (- deadline (time/monotonic)))))
                      (not= total (get artifact "size_in_bytes")))
              (throw (value-error "artifact download failed or was truncated"))))
          (finally (stop-process! proc)))
        (when (not= (str "sha256:" (.hexdigest digest)) (get artifact "digest"))
          (throw (value-error "downloaded archive digest mismatch")))))))

(defn- gh-env [temp]
  (let [env (python/dict {"PATH" "/usr/bin:/bin" "GH_HOST" "github.com" "GH_PROMPT_DISABLED" "1"
                          "HOME" temp "GH_CONFIG_DIR" temp})]
    (when (contains? os/environ "GH_TOKEN") (operator/setitem env "GH_TOKEN" (operator/getitem os/environ "GH_TOKEN")))
    env))

(defn fetch-with-policy
  "Private fixture hook: policy and prefix must be chosen by a trusted host."
  [policy pfx gh gh-sha256 destination]
  (attest/validate policy)
  (when (or (not= (:repository policy) repo) (not= (:repository-id policy) (str repo-id)) (not= (:trigger policy) "push")
            (not (re/fullmatch "[a-z0-9-]{1,100}-" pfx)))
    (throw (value-error "untrusted producer policy")))
  (let [source-sha (:source-sha policy)
        branch (subs (:ref policy) (count "refs/heads/"))
        workflow-name (last (.split (:workflow policy) "/"))]
    (with-open [temp (tempfile/TemporaryDirectory ** :prefix "bounded-fetch-")]
      (let [env (gh-env temp)
            zip-path (.joinpath (pathlib/Path temp) "artifact.zip")
            tar-path (.joinpath (pathlib/Path temp) "bounded-cache.tar")]
        (sealed/with-sealed-image gh gh-sha256
          (fn [fd _]
            (let [query (urllib.parse/urlencode (python/dict [["event" "push"] ["branch" branch] ["status" "success"]
                                                              ["head_sha" source-sha] ["per_page" 100]]))
                  endpoint (str "repos/" repo "/actions/workflows/" workflow-name "/runs?" query)
                  rows (get (call fd env endpoint) "workflow_runs" [])
                  _ (when (some #(not (run-matches? % source-sha branch (:workflow policy))) rows)
                      (throw (value-error "producer run metadata mismatch")))
                  runs (sort-by #(get % "id") #(compare %2 %1) rows)
                  selected (some (fn [run]
                                   (let [listing (call fd env (str "repos/" repo "/actions/runs/" (get run "id") "/artifacts?per_page=100"))]
                                     (when (> (get listing "total_count" 0) 100)
                                       (throw (value-error "too many artifacts for an unambiguous producer")))
                                     (select-artifact (get listing "artifacts" []) (get run "id") source-sha branch pfx)))
                                 runs)]
              (when (nil? selected)
                (throw (cache-unavailable "no successful unexpired producer for this exact revision")))
              (download fd env selected zip-path))))
        (unzip-exact zip-path tar-path)
        (bundle/verified-extract tar-path gh gh-sha256 policy destination)))))

(defn fetch-verified
  "Fetch an exact successful main artifact and verify its attested bundle."
  [source-sha gh gh-sha256 destination]
  (when-not (re/fullmatch "[0-9a-f]{40}" source-sha) (throw (value-error "source revision must be an immutable SHA")))
  (fetch-with-policy (attest/attestation-policy repo (str repo-id) workflow "refs/heads/main" source-sha source-sha "push")
                     prefix gh gh-sha256 destination))

(defn- opt [args k] (second (drop-while #(not= % k) args)))

(defn -main [& args]
  (let [source-sha (or (opt args "--source-sha") (sys/exit "--source-sha is required"))
        gh (or (opt args "--gh") (sys/exit "--gh is required"))
        out (pathlib/Path (or (opt args "--output") (sys/exit "--output is required")))]
    (.mkdir out ** :mode 0700)
    (os/chmod out 0700)
    (let [output (.resolve out)
          result (try (fetch-verified source-sha (pathlib/Path gh) producer/gh-sha256 (.joinpath output "bundle"))
                      (catch basilisp.lang.exception/ExceptionInfo e
                        (if (cache-unavailable? e)
                          (do (.write sys/stderr (str "CACHE_UNAVAILABLE: " (ex-message e) "\n")) (sys/exit 75))
                          (throw e))))
          [image objects image-digest bundle-digest] result]
      (producer/exercise image objects image-digest output)
      (println "PASS_FETCHED_BOUNDED_CACHE" source-sha bundle-digest)
      (.flush sys/stdout))))

(when (some #(or (= % "fetch_bounded_cache.cljc") (str/ends-with? % "/fetch_bounded_cache.cljc")) sys/argv)
  (apply -main *command-line-args*))
