;; Build and run one Amu program as a signed macOS arm64 image (JUN-586).
;;
;; Shared by the native definition gates when they run on Apple Silicon. The Mac root compiler emits a KSEED
;; container, extracts the native `main`, and the Mac packager wraps it in the fs2-cli-stdio-general runtime. This
;; only stages bytes, launches the native programs and signs a copy with the system codesign. File access goes
;; through FD 3 (the output directory) and file names are basenames, as the Mac runtime requires (KOTOBA-169).
;; Ported from macos_native_image.py (Basilisp, JUN-974).
(ns macos-image
  (:require [gate-util :as u]
            [macos-native-lib :as mac])
  (:import json os pathlib platform re subprocess))

(defn available? []
  (and (= "Darwin" (platform/system)) (contains? #{"arm64" "aarch64"} (platform/machine))))

(defn root-images
  "The descriptor's compiler and packager, verified against their pins: [compiler packager]."
  []
  (let [d (u/read-json mac/root-descriptor)]
    (vec (for [role ["compiler" "packager"]]
           (let [image (.joinpath u/root (u/geti (u/geti d role) "path"))]
             (u/chk (u/deq (mac/verify-macho image)
                           (u/pydict-from (for [k ["bytes" "sha256"]] [k (u/geti (u/geti d role) k)])))
                    role)
             image)))))

(defn build
  "Compile out/source-name and return [signed-image unsigned-image]."
  [compiler packager out source-name stem]
  (let [out (pathlib/Path out)]
    (mac/native-run compiler out ["compile" source-name "--target" "aarch64-macos" "--output" (str stem ".kseed")])
    (let [r (mac/native-run compiler out ["extract-native" (str stem ".kseed") "--symbol" "main" "--output" (str stem ".raw")])
          m (re/search (.encode ":offset (\\d+), :length (\\d+), :arity 0}") (.-stdout r))]
      (u/chk (and m (= (python/int (.group m 2)) (.-st_size (.stat (.joinpath out (str stem ".raw")))))) (.-stdout r))
      (mac/native-run packager out [(str stem "-unsigned.macho") (str stem ".raw") "fs2-cli-stdio-general" (.decode (.group m 1))]))
    (let [image (.joinpath out (str stem ".macho"))]
      (mac/sign (.joinpath out (str stem "-unsigned.macho")) image)
      (mac/verify-macho image)
      [image (.joinpath out (str stem "-unsigned.macho"))])))

(defn run
  "Run a packaged image with FD 3 = out, cwd = out; arguments must be basenames."
  [image out args & {:keys [timeout] :or {timeout 900}}]
  (doseq [a args] (u/chk (not (.__contains__ (str a) "/")) (str "the Mac runtime takes basenames only " a)))
  (let [fd (os/open out (bit-or os/O_RDONLY os/O_DIRECTORY))]
    (try
      (subprocess/run (python/list (map str (cons image args))) ** :cwd out
                      :env (python/dict {"PATH" "/usr/bin:/bin" "LANG" "C"})
                      :capture_output true :timeout timeout :pass_fds (python/tuple [3])
                      :preexec_fn (fn [] (os/dup2 fd 3)))
      (finally (os/close fd)))))
