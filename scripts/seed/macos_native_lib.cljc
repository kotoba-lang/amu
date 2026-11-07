;; Shared helpers of the Mac gates: pinned inputs, Mach-O verification, native runs with an FD3 file root,
;; ad-hoc signing. Ported from the helper half of check-aiueos-user-macos-native.py (Basilisp, JUN-974); the
;; Python module stays until its last Python importer is ported. Apple Silicon macOS only.
(ns macos-native-lib
  (:require [gate-util :as u])
  (:import json operator os pathlib platform re shutil struct subprocess sys))

(def manifest (.joinpath u/root "seed/FULL-MANIFEST"))
(def root-descriptor (.joinpath u/root "seed/bootstrap/aarch64-macos/root.json"))
(def packager-source (.joinpath u/root "seed/macos-fs2-runtime-packager.kotoba"))

(defn fail [message] (throw (python/ValueError message)))

(defn pin [path] (u/pin path))

(defn require-regular
  ([path] (require-regular path nil))
  ([path digest]
   (let [path (pathlib/Path path)]
     (when (or (.is_symlink path) (not (.is_file path)))
       (fail (str "regular non-symlink input required: " path)))
     (let [identity (pin path)]
       (when (and digest (not= (u/geti identity "sha256") digest))
         (fail (str "input digest mismatch: " (.-name path))))
       identity))))

(defn process
  "subprocess.run(argv, cwd, env, pass_fds, capture_output, timeout) with every arg stringified."
  [argv & {:keys [cwd env pass-fds timeout] :or {pass-fds [] timeout 1200}}]
  (subprocess/run (python/list (map str argv)) ** :cwd cwd :env env :pass_fds (python/tuple pass-fds)
                  :capture_output true :timeout timeout :check false))

(defn- unpack [fmt raw offset] (vec (struct/unpack_from fmt raw offset)))

(defn verify-macho [path]
  (let [path (pathlib/Path path)
        raw (.read_bytes path)
        n (python/len raw)
        name (.-name path)]
    (when (or (< n 32) (not= (unpack "<IiiI" raw 0) [0xfeedfacf 0x100000c 0 2]))
      (fail (str "expected arm64 Mach-O executable: " name)))
    (let [[commands size] (unpack "<II" raw 16)]
      (when (or (< commands 2) (> commands 32) (> size 992) (> (+ 32 size) n))
        (fail (str "invalid Mac load-command extent: " name)))
      (let [seen (atom {2 0 11 0})
            offset (loop [i 0 offset 32]
                     (if (< i commands)
                       (do
                         (when (> (+ offset 8) (+ 32 size)) (fail (str "truncated Mac load command: " name)))
                         (let [[kind length] (unpack "<II" raw offset)]
                           (when (or (< length 8) (pos? (mod length 8)) (> (+ offset length) (+ 32 size)))
                             (fail (str "invalid Mac load command: " name)))
                           (when (contains? @seen kind)
                             (when (or (not= length ({2 24 11 80} kind))
                                       (python/any (u/bslice raw (+ offset 8) (+ offset length))))
                               (fail (str "nonempty Mac symbol/relocation table: " name)))
                             (swap! seen update kind inc))
                           (recur (inc i) (+ offset length))))
                       offset))]
        (when (or (not= offset (+ 32 size)) (not= @seen {2 1 11 1}))
          (fail (str "Mac symbol/relocation commands missing: " name)))))
    (let [signed (process ["/usr/bin/codesign" "--verify" "--strict" path] :timeout 30)]
      (when-not (zero? (.-returncode signed)) (fail (str "code signature verification failed: " name))))
    (let [linked (process ["/usr/bin/otool" "-L" path] :timeout 30)]
      (when (or (not (zero? (.-returncode linked)))
                (not= (vec (.splitlines (.-stdout linked))) [(.encode (str path ":"))]))
        (fail (str "undeclared dylib dependency: " name))))
    (pin path)))

(defn native-run
  "Give the native program only the output-owned FD3 file root."
  [image directory args & {:keys [expected timeout] :or {expected 0 timeout 1200}}]
  (let [directory (pathlib/Path directory)
        image (pathlib/Path image)
        fd (os/open directory (bit-or os/O_RDONLY os/O_DIRECTORY))
        relocated (not= fd 3)
        saved (atom nil)]
    (try
      (when relocated
        (try (reset! saved (os/dup 3)) (catch python/OSError _ nil))
        (os/dup2 fd 3))
      (let [d (str directory)
            env (python/dict {"PATH" "/usr/bin:/bin" "LANG" "C" "TMPDIR" d "TMP" d "TEMP" d})
            result (process (concat [image] args) :cwd directory :env env :pass-fds [3] :timeout timeout)]
        (when (not= (.-returncode result) expected)
          (fail (str (.-name image) " returned " (.-returncode result) ", expected " expected ": "
                     (let [e (.decode (.-stderr result) "utf-8" "replace")] (subs e (max 0 (- (count e) 800)))))))
        (when (and (zero? expected) (u/nonempty? (.-stderr result)))
          (fail (str (.-name image) " wrote unexpected stderr: "
                     (let [e (.decode (.-stderr result) "utf-8" "replace")] (subs e (max 0 (- (count e) 800)))))))
        result)
      (finally
        (when relocated
          (if (nil? @saved)
            (os/close 3)
            (do (os/dup2 @saved 3) (os/close @saved))))
        (os/close fd)))))

(defn sign [unsigned signed]
  (let [signed (pathlib/Path signed)]
    (shutil/copyfile unsigned signed)
    (.chmod signed 0755)
    (let [result (process ["/usr/bin/codesign" "--force" "--sign" "-" signed] :timeout 30)]
      (when-not (zero? (.-returncode result)) (fail (str "could not sign native Mach-O: " (.-name signed)))))
    (verify-macho signed)))

(defn available? []
  (and (= "Darwin" (platform/system)) (contains? #{"arm64" "aarch64"} (platform/machine))))

(defn stage-unity
  "Write directory/full-unity.kotoba from FULL-MANIFEST; returns [sources unity-pin]."
  [directory]
  (let [directory (pathlib/Path directory)
        names (vec (filter #(and (seq %) (not (.startswith % "#"))) (.splitlines (.read_text manifest))))]
    (when (or (not= 61 (count names)) (not= 61 (count (set names))))
      (fail "FULL-MANIFEST must contain 61 unique modules"))
    (let [unity (.joinpath directory "full-unity.kotoba")
          stream (.open unity "wb")
          sources (try
                    (vec (for [name names]
                           (let [part (pathlib/Path name)]
                             (when (or (.is_absolute part) (.__contains__ (.-parts part) "..") (not= "seed" (first (.-parts part))))
                               (fail "invalid source path in FULL-MANIFEST"))
                             (let [path (.joinpath u/root part)
                                   row (python/dict (.items (python/dict (concat [["name" name]] (.items (require-regular path))))))]
                               (.write stream (operator/add (.read_bytes path) (.encode "\n")))
                               row))))
                    (finally (.close stream)))]
      [sources (pin unity)])))

(defn generation
  "One bootstrap generation: compile the unity, extract main, package, sign. Returns [signed row]."
  [number producer packager directory]
  (let [directory (pathlib/Path directory)
        container (.joinpath directory (str "F" number ".kseed"))
        raw (.joinpath directory (str "F" number ".raw"))
        unsigned (.joinpath directory (str "F" number "-unsigned.macho"))
        signed (.joinpath directory (str "F" number "-signed.macho"))]
    (native-run producer directory ["compile" "full-unity.kotoba" "--target" "aarch64-macos" "--output" (.-name container)])
    (let [extracted (native-run producer directory ["extract-native" (.-name container) "--symbol" "main" "--output" (.-name raw)])
          m (re/search (.encode ":offset (\\d+), :length (\\d+), :arity 0}") (.-stdout extracted))]
      (when (or (nil? m) (not= (python/int (.group m 2)) (.-st_size (.stat raw))))
        (fail "native main extraction did not match raw bytes"))
      (let [entry (python/int (.group m 1))]
        (native-run packager directory [(.-name unsigned) (.-name raw) "fs2-cli-stdio-general" (str entry)])
        (let [signed-pin (sign unsigned signed)
              row (u/pydict "number" number "producer" (pin producer) "container" (pin container) "raw" (pin raw)
                            "entry" entry "unsigned" (pin unsigned) "signed" signed-pin)]
          (println (str "F" number " container " (u/geti (u/geti row "container") "sha256")))
          (.flush sys/stdout)
          [signed row])))))
