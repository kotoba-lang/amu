;; Compile, package and sign one program for the Mac diagnostic runtime (shared by the Mac runtime-feature gates:
;; arena-scope and the ones that borrow its build step). Ported from `build` of check-macos-arena-scope.py
;; (Basilisp, JUN-974). The compiler and packager are native Mac images; this stages and observes.
(ns macos-scope-build
  (:require [gate-util :as u]
            [macos-native-lib :as mac])
  (:import operator os pathlib re))

(defn build
  "Compile `source` (a string or a Path), extract `symbol`, package with the packager, sign. Returns the .macho Path."
  ([compiler packager output name source] (build compiler packager output name source "main"))
  ([compiler packager output name source symbol]
   (let [output (pathlib/Path output)]
     (.write_text (.joinpath output (str name ".kotoba")) (if (string? source) source (.read_text source)))
     (mac/native-run compiler output ["compile" (str name ".kotoba") "--target" "aarch64-macos" "--output" (str name ".kseed")])
     (let [extracted (mac/native-run compiler output ["extract-native" (str name ".kseed") "--symbol" symbol "--output" (str name ".raw")])
           m (re/search (.encode ":offset (\\d+), :length (\\d+), :arity 0}") (.-stdout extracted))]
       (when (or (nil? m) (not= (python/int (.group m 2)) (.-st_size (.stat (.joinpath output (str name ".raw"))))))
         (mac/fail (str "native extraction did not match raw bytes: " name)))
       (mac/native-run packager output [(str name "-unsigned.macho") (str name ".raw") "fs2-cli-stdio-general" (.decode (.group m 1))])
       (mac/sign (.joinpath output (str name "-unsigned.macho")) (.joinpath output (str name ".macho")))
       (.joinpath output (str name ".macho"))))))

(defn check-source
  "Run `compiler check name.kotoba` with directory as the FD3 root. Returns [exit-code combined-output-string]."
  [compiler directory name source]
  (let [directory (pathlib/Path directory)]
    (.write_text (.joinpath directory (str name ".kotoba")) source)
    (let [fd (os/open directory (bit-or os/O_RDONLY os/O_DIRECTORY))
          saved (atom nil)]
      (try
        (try (reset! saved (os/dup 3)) (catch python/OSError _ nil))
        (os/dup2 fd 3)
        (let [result (mac/process [compiler "check" (str name ".kotoba")] :cwd directory :pass-fds [3]
                                  :env (python/dict {"PATH" "/usr/bin:/bin" "LANG" "C"}) :timeout 600)]
          [(.-returncode result) (.decode (operator/add (.-stdout result) (.-stderr result)) "utf-8" "replace")])
        (finally
          (if (nil? @saved)
            (os/close 3)
            (do (os/dup2 @saved 3) (os/close @saved)))
          (os/close fd))))))
