;; Stage a pinned static gh image from its pinned release archive.
;; Ported from stage_pinned_gh.py (Basilisp). Run:
;;   basilisp run scripts/seed/stage_pinned_gh.cljc -- --archive A --output O
(ns stage-pinned-gh
  (:require [basilisp.string :as str]
            [check-bounded-producer-attestation :as producer]
            [sealed-image :as sealed])
  (:import hashlib os pathlib sys tarfile))

(def ^:redef archive-sha256 "4c806978ffce1cec70853302a56d70ac6da4f19bae7adca4e1a8ab00633dd91d")
(def member "gh_2.103.3_linux_amd64/bin/gh")
(def limit (* 128 1024 1024))

(defn ^:redef gh-sha256 [] producer/gh-sha256)

(defn stage [archive output]
  (let [archive (pathlib/Path archive) output (pathlib/Path output)
        data (sealed/with-sealed-image archive archive-sha256
               (fn [fd _]
                 (when (> (.-st_size (os/fstat fd)) (* 32 1024 1024))
                   (throw (python/ValueError "verifier archive exceeds size limit")))
                 (os/lseek fd 0 os/SEEK_SET)
                 (with-open [source (os/fdopen (os/dup fd) "rb")
                             tar (tarfile/open ** :fileobj source :mode "r:gz")]
                   (let [members (vec (filter #(= member (.-name %)) (python/list tar)))
                         m (first members)]
                     (when (or (not= 1 (count members)) (not (.isfile m)) (not (< 0 (.-size m) (inc limit))))
                       (throw (python/ValueError "invalid verifier member")))
                     (let [stream (.extractfile tar m)]
                       (when (nil? stream) (throw (python/ValueError "missing verifier bytes")))
                       (.read stream (inc limit)))))))]
    (when (not= (.hexdigest (hashlib/sha256 data)) (gh-sha256))
      (throw (python/ValueError "verifier image digest mismatch")))
    (let [fd (os/open output (bit-or os/O_WRONLY os/O_CREAT os/O_EXCL os/O_NOFOLLOW) 0500)]
      (try
        (with-open [out (os/fdopen fd "wb")]
          (.write out data)
          (.flush out)
          (os/fchmod (.fileno out) 0500)
          (os/fsync (.fileno out)))
        (catch python/BaseException e
          (.unlink output ** :missing_ok true)
          (throw e))))))

(defn- opt [args k] (second (drop-while #(not= % k) args)))

(defn -main [& args]
  (stage (or (opt args "--archive") (sys/exit "--archive is required"))
         (or (opt args "--output") (sys/exit "--output is required"))))

(when (some #(or (= % "stage_pinned_gh.cljc") (str/ends-with? % "/stage_pinned_gh.cljc")) sys/argv)
  (apply -main *command-line-args*))
