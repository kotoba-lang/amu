;; Compile, package and sign one program for the Mac diagnostic runtime (shared by the Mac runtime-feature gates:
;; arena-scope and the ones that borrow its build step). Ported from `build` of check-macos-arena-scope.py
;; (Basilisp, JUN-974). The compiler and packager are native Mac images; this stages and observes.
(ns macos-scope-build
  (:require [gate-util :as u]
            [macos-native-lib :as mac])
  (:import pathlib re))

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
