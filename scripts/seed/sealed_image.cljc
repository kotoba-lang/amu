;; Bind a Linux process launch to immutable executable bytes.
;;
;; The expected digest must come from a separately trusted source. This helper
;; does not authenticate the origin of that digest or qualify compiler inputs.
;; Ported from sealed_image.py (Basilisp). Linux only: memfd_create and file seals.
;; Python's context managers become callbacks: (with-sealed-image path digest (fn [fd digest] ...)).
(ns sealed-image
  (:import fcntl hashlib hmac operator os re stat pathlib))

(def max-image-bytes (* 128 1024 1024))
(def seals (bit-or fcntl/F_SEAL_WRITE fcntl/F_SEAL_GROW fcntl/F_SEAL_SHRINK fcntl/F_SEAL_SEAL))

(defn- value-error [message] (python/ValueError message))

(defn- read-all-into
  "Copy fd `source` into fd `fd`, bounded by max-image-bytes."
  [source fd]
  (loop [length 0]
    (let [chunk (os/read source (* 1024 1024))]
      (when (seq chunk)
        (let [length (+ length (count chunk))
              _ (when (> length max-image-bytes) (throw (value-error "image exceeds size limit")))
              view (python/memoryview chunk)]
          (loop [offset 0]
            (when (< offset (count chunk))
              (let [written (os/write fd (operator/getitem view (python/slice offset nil)))]
                (when (<= written 0) (throw (python/OSError "short image write")))
                (recur (+ offset written)))))
          (recur length))))))

(defn- digest-fd [fd]
  (let [digest (hashlib/sha256)]
    (loop []
      (let [chunk (os/read fd (* 1024 1024))]
        (when (seq chunk)
          (.update digest chunk)
          (recur))))
    (.hexdigest digest)))

(defn with-sealed-blob
  "Calls (f fd digest) with immutable bytes and their digest; this does not authenticate them.
  The fds are closed when f returns or throws."
  [path f]
  (let [flags (bit-or os/O_RDONLY os/O_CLOEXEC os/O_NOFOLLOW os/O_NONBLOCK)
        source (os/open (pathlib/Path path) flags)
        fd (atom -1)]
    (try
      (when-not (stat/S_ISREG (.-st_mode (os/fstat source)))
        (throw (value-error "image must be a regular file")))
      (reset! fd (os/memfd_create "kotoba-verified-image" (bit-or os/MFD_CLOEXEC os/MFD_ALLOW_SEALING)))
      (read-all-into source @fd)
      (os/fchmod @fd 0500)
      (fcntl/fcntl @fd fcntl/F_ADD_SEALS seals)
      (when (not= seals (bit-and (fcntl/fcntl @fd fcntl/F_GET_SEALS) seals))
        (throw (python/OSError "image sealing failed")))
      ;; Hash after sealing so the digest identifies the exact immutable
      ;; bytes that exec will see, even if the source changed during copying.
      (os/lseek @fd 0 os/SEEK_SET)
      (f @fd (digest-fd @fd))
      (finally
        (os/close source)
        (when (>= @fd 0) (os/close @fd))))))

(defn with-sealed-image
  "Calls (f fd digest) for the verified, sealed bytes; the caller must pass fd.

  Execute /proc/self/fd/<fd> with pass_fds=(fd,) while inside f.
  A cache record or a caller-selected digest is not a trusted authority."
  [path expected-sha256 f]
  (when-not (re/fullmatch "[0-9a-f]{64}" expected-sha256)
    (throw (value-error "invalid trusted image digest")))
  (with-sealed-blob path
    (fn [fd actual]
      (when-not (hmac/compare_digest actual expected-sha256)
        (throw (value-error "image digest mismatch")))
      (f fd actual))))
