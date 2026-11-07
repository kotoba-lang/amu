;; Transport a bounded native object fixture; never transport gate verdicts.
;; Ported from bounded_cache_bundle.py (Basilisp). Linux only (file seals).
;; Run: basilisp run scripts/seed/bounded_cache_bundle.cljc -- --producer P --cache C --output O
(ns bounded-cache-bundle
  (:require [basilisp.string :as str]
            [sealed-image :as sealed]
            [verified-attestation :as attest])
  (:import fcntl hashlib os pathlib re shutil stat sys tarfile))

(def object-re "objects/[0-9a-f]{64}\\.kdo")
(def max-objects 512)
(def max-object-bytes (* 4 1024 1024))

(defn- value-error [message] (python/ValueError message))

(defn- private!
  [path directory?]
  (let [info (os/lstat path)]
    (when (or (not= (.-st_uid info) (os/geteuid))
              (not (if directory? (stat/S_ISDIR (.-st_mode info)) (stat/S_ISREG (.-st_mode info))))
              (not= (stat/S_IMODE (.-st_mode info)) (if directory? 0700 0400)))
      (throw (value-error "object store must be private and compiler-owned")))))

(defn pack
  "Pack only a producer image and private .kdo files; never a receipt."
  [producer cache destination]
  (let [producer (pathlib/Path producer) cache (pathlib/Path cache) destination (pathlib/Path destination)
        _ (private! cache true)
        objects (vec (sort-by #(.-name %) (python/list (.iterdir cache))))
        _ (when (or (empty? objects) (> (count objects) max-objects)) (throw (value-error "invalid object count")))
        entries (into [[producer "producer.elf" sealed/max-image-bytes 0500]]
                      (for [path objects]
                        (do (when-not (re/fullmatch object-re (str "objects/" (.-name path)))
                              (throw (value-error "unexpected cache entry")))
                            (private! path false)
                            [path (str "objects/" (.-name path)) max-object-bytes 0400])))
        created (atom false)]
    (try
      (with-open [out (.open destination "xb")]
        (reset! created true)
        (os/fchmod (.fileno out) 0600)
        (let [total (atom 0)]
          (with-open [tar (tarfile/open ** :fileobj out :mode "w" :format tarfile/USTAR_FORMAT)]
            (doseq [[path name limit mode] entries]
              (let [fd (os/open path (bit-or os/O_RDONLY os/O_NOFOLLOW os/O_NONBLOCK os/O_CLOEXEC))]
                (with-open [source (os/fdopen fd "rb")]
                  (let [info (os/fstat fd)]
                    (when (or (not (stat/S_ISREG (.-st_mode info))) (<= (.-st_size info) 0) (> (.-st_size info) limit))
                      (throw (value-error "invalid artifact file")))
                    (swap! total + (.-st_size info))
                    (when (> @total sealed/max-image-bytes) (throw (value-error "bundle contents exceed size limit")))
                    (when (and (= mode 0400) (or (not= (.-st_uid info) (os/geteuid)) (not= (stat/S_IMODE (.-st_mode info)) 0400)))
                      (throw (value-error "object changed while opening")))
                    (let [row (tarfile/TarInfo name)]
                      (set! (.-size row) (.-st_size info))
                      (set! (.-mode row) mode)
                      (set! (.-mtime row) 0)
                      (set! (.-uid row) 0)
                      (set! (.-gid row) 0)
                      (.addfile tar row source)))))))
          (.flush out)
          (os/fsync (.fileno out))))
      (catch python/BaseException e
        (when @created (.unlink destination ** :missing_ok true))
        (throw e)))
    (when (> (.-st_size (.stat destination)) sealed/max-image-bytes)
      (.unlink destination)
      (throw (value-error "bundle exceeds size limit")))))

(defn extract-sealed
  "Extract an already authenticated, sealed fd into a new private path. Returns [image objects image-digest]."
  [fd destination]
  (when (not= sealed/seals (bit-and (fcntl/fcntl fd fcntl/F_GET_SEALS) sealed/seals))
    (throw (value-error "bundle is not sealed")))
  (let [destination (pathlib/Path destination)
        objects (.joinpath destination "objects")
        seen (atom #{})
        total (atom 0)
        image-digest (atom nil)]
    (.mkdir destination ** :mode 0700)
    (os/chmod destination 0700)
    (try
      (.mkdir objects ** :mode 0700)
      (os/chmod objects 0700)
      (os/lseek fd 0 os/SEEK_SET)
      (with-open [source (os/fdopen (os/dup fd) "rb")
                  tar (tarfile/open ** :fileobj source :mode "r|")]
        (let [it (python/iter tar)]
          (loop []
            (when-let [row (python/next it nil)]
              (let [name (.-name row)
                    image? (= name "producer.elf")]
                (when (or (not (.isfile row))
                          (and (not image?) (not (re/fullmatch object-re name)))
                          (contains? @seen name)
                          (<= (.-size row) 0)
                          (> (.-size row) (if image? sealed/max-image-bytes max-object-bytes)))
                  (throw (value-error "invalid bundle entry")))
                (swap! seen conj name)
                (when (> (count @seen) (inc max-objects)) (throw (value-error "too many bundle entries")))
                (swap! total + (.-size row))
                (when (> @total sealed/max-image-bytes) (throw (value-error "bundle contents exceed size limit")))
                (let [target (.joinpath destination name)
                      handle (os/open target (bit-or os/O_WRONLY os/O_CREAT os/O_EXCL os/O_NOFOLLOW) 0600)]
                  (with-open [out (os/fdopen handle "wb")]
                    (let [data (.extractfile tar row)]
                      (when (nil? data) (throw (value-error "missing bundle bytes")))
                      (let [hasher (hashlib/sha256)]
                        (loop []
                          (let [chunk (.read data (* 1024 1024))]
                            (when (seq chunk)
                              (.update hasher chunk)
                              (.write out chunk)
                              (recur))))
                        (when image? (reset! image-digest (.hexdigest hasher))))))
                  (os/chmod target (if image? 0500 0400)))
                (recur))))))
      (when (or (not (contains? @seen "producer.elf")) (< (count @seen) 2))
        (throw (value-error "bundle must contain a producer and objects")))
      (catch python/BaseException e
        (shutil/rmtree destination)
        (throw e)))
    [(.joinpath destination "producer.elf") objects @image-digest]))

(defn verified-extract
  "Authenticate the sealed archive before touching its member paths. Returns [image objects image-digest digest]."
  [bundle gh gh-sha256 policy destination]
  (attest/with-verified-artifact bundle gh gh-sha256 policy
    (fn [fd digest]
      (let [[image objects image-digest] (extract-sealed fd destination)]
        [image objects image-digest digest]))))

(defn- opt [args k] (second (drop-while #(not= % k) args)))

(defn -main [& args]
  (let [need (fn [k] (or (opt args k) (sys/exit (str k " is required"))))]
    (pack (need "--producer") (need "--cache") (need "--output"))))

(when (some #(or (= % "bounded_cache_bundle.cljc") (str/ends-with? % "/bounded_cache_bundle.cljc")) sys/argv)
  (apply -main *command-line-args*))
