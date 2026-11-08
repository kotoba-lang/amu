;; Compile, package and sign one program for the Mac diagnostic runtime (shared by the Mac runtime-feature gates:
;; arena-scope and the ones that borrow its build step). Ported from `build` of check-macos-arena-scope.py
;; (Basilisp, JUN-974). The compiler and packager are native Mac images; this stages and observes.
(ns macos-scope-build
  (:require [gate-util :as u]
            [macos-native-lib :as mac])
  (:import os pathlib re))

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

(defn run-source
  "Run `compiler <command> name.kotoba` with directory as the FD3 root. Returns [exit stdout stderr] (strings)."
  [compiler directory command name source]
  (let [directory (pathlib/Path directory)]
    (.write_text (.joinpath directory (str name ".kotoba")) source)
    (let [fd (os/open directory (bit-or os/O_RDONLY os/O_DIRECTORY))
          saved (atom nil)]
      (try
        (try (reset! saved (os/dup 3)) (catch python/OSError _ nil))
        (os/dup2 fd 3)
        (let [result (mac/process [compiler command (str name ".kotoba")] :cwd directory :pass-fds [3]
                                  :env (python/dict {"PATH" "/usr/bin:/bin" "LANG" "C"}) :timeout 600)]
          [(.-returncode result) (.decode (.-stdout result) "utf-8" "replace") (.decode (.-stderr result) "utf-8" "replace")])
        (finally
          (if (nil? @saved)
            (os/close 3)
            (do (os/dup2 @saved 3) (os/close @saved)))
          (os/close fd))))))

(defn check-source
  "Run `compiler check name.kotoba` with directory as the FD3 root. Returns [exit-code combined-output-string]."
  [compiler directory name source]
  (let [[rc out err] (run-source compiler directory "check" name source)]
    [rc (str out err)]))

(defn mutant-compiler
  "Build a mutant full compiler from FULL-MANIFEST with `path`'s text edited by [[old new] ...] (each `old` must occur
  exactly once), using `compiler`/`packager`. Returns the mutant compiler Path; fails if it equals the compiler."
  [compiler packager output label path edits]
  (let [names (vec (filter #(and (seq %) (not (.startswith % "#"))) (.splitlines (.read_text mac/manifest))))
        _ (when-not (contains? (set names) path) (mac/fail (str "FULL-MANIFEST no longer lists " path)))
        text (reduce (fn [text [old new]]
                       (when (not= 1 (.count text old)) (mac/fail (str "cannot construct the " label " negative control")))
                       (.replace text old new))
                     (.read_text (.joinpath u/root path)) edits)
        mutant (.joinpath (pathlib/Path output) label)
        _ (.mkdir mutant ** :mode 0700)
        _ (.write_text (.joinpath mutant "full-unity.kotoba")
                       (apply str (for [name names] (str (if (= name path) text (.read_text (.joinpath u/root name))) "\n"))))
        built (build compiler packager mutant "full-unity" (.read_text (.joinpath mutant "full-unity.kotoba")))]
    (when (u/deq (mac/pin built) (mac/pin compiler))
      (mac/fail (str "mutant compiler is identical to the compiler under test: " label)))
    built))

(defn build-run
  "Write directory/name.kotoba, build it with `build`, run the image; returns its exit code (60 s timeout)."
  [compiler packager directory name source]
  (let [directory (pathlib/Path directory)
        path (.joinpath directory (str name ".kotoba"))]
    (.write_text path source)
    (let [image (build compiler packager directory name path)]
      (.-returncode (mac/process [image] :cwd directory :env (python/dict {"PATH" "/usr/bin:/bin" "LANG" "C"}) :timeout 60)))))

(defn cids
  "stdout of `compiler definition-cids name.kotoba` (FD3 root = directory); fails on a non-zero exit."
  [compiler directory name source]
  (let [[status out err] (run-source compiler directory "definition-cids" name source)]
    (when (not= status 0)
      (mac/fail (str "definition-cids " name ": exit " status ": " (pr-str (let [s (str out err)] (subs s (max 0 (- (count s) 300))))))))
    out))

(defn cids-report
  "\"exit N\\n\" + stdout + stderr of `compiler definition-cids name.kotoba` (never fails on a non-zero exit)."
  [compiler directory name source]
  (let [[status out err] (run-source compiler directory "definition-cids" name source)]
    (str "exit " status "\n" out err)))
