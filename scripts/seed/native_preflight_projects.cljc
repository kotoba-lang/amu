;; Stage the ordered local-project -> FS35 candidate preflight.
;;
;; No native verdict or source semantics are implemented here. The existing
;; observers retain their exact native compiler, fixtures, refusals and flags.
;; Ported from native_preflight_projects.py (Basilisp, .cljc).
;; Run: basilisp run scripts/seed/native_preflight_projects.cljc -- --compiler C --temporary T
(ns native-preflight-projects
  (:require [basilisp.string :as str])
  (:import json os pathlib subprocess sys))

(defn path [& parts] (apply pathlib/Path parts))

(def root
  "Repository root. Basilisp exposes no script path, so this is the working
  directory (the gate plan runs every argv from the repo root); AMU_ROOT overrides."
  (.resolve (path (or (.get os/environ "AMU_ROOT") "."))))

(def python "python3")

(defn root-file [rel] (str (.joinpath root rel)))

(defn ^:redef run-process
  "Run argv, raising subprocess.CalledProcessError on non-zero exit."
  [argv]
  (subprocess/run (python/list argv) ** :check true))

(defn main
  [compiler temporary]
  (let [compiler  (str compiler)
        temporary (path temporary)
        project   (str (.joinpath temporary "local-native-project"))]
    (run-process ["basilisp" "run" "-p" (root-file "scripts/seed") (root-file "scripts/seed/check-x86-project-native.cljc") "--"
                  "--compiler" compiler
                  "--output" project])
    (let [image (-> (path (root-file "native-product.json")) .read-text json/loads (get "image") (get "sha256"))]
      (run-process [python (root-file "scripts/seed/check-x86-project-fs-native.py")
                    "--compiler" compiler "--compiler-sha256" image
                    "--runner" (str (.joinpath temporary "local-native-project/runner.elf"))
                    "--output" (str (.joinpath temporary "project-fs-candidate")) "--derive"]))))

(defn- parse-args [args]
  (loop [m {} [k v & more :as xs] (seq args)]
    (cond
      (empty? xs) m
      (= k "--compiler")  (recur (assoc m :compiler v) more)
      (= k "--temporary") (recur (assoc m :temporary v) more)
      :else (throw (ex-info (str "unknown argument " k) {:arg k})))))

(defn -main [& args]
  (let [{:keys [compiler temporary]} (parse-args args)]
    (when-not (and compiler temporary)
      (throw (ex-info "--compiler and --temporary are required" {})))
    (main (.resolve (path compiler)) (.resolve (path temporary)))))

(when (some #(or (= % "native_preflight_projects.cljc")
                 (str/ends-with? % "/native_preflight_projects.cljc"))
            sys/argv)
  (apply -main *command-line-args*))
