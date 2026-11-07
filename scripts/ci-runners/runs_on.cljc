;; Render and check the variable-driven `runs-on` lines of the amu workflows (ADR 0407).
;;
;; Every covered job keeps its GitHub-hosted label as the default.  The repo
;; variable AMU_RUNNER_PROFILE selects self-hosted labels:
;;
;;   (unset) | hosted   all jobs on GitHub-hosted runners (current behaviour)
;;   selfhosted-arm     linux-arm64 and macos-arm64 jobs on amu-* runners
;;   selfhosted         additionally linux-x86_64 jobs on amu-linux-x86_64
;;
;; A self-hosted label is selected only when the event is not a pull request or
;; the pull request head is this repository.  Fork pull requests always get the
;; hosted label.  Jobs that hold secrets are never covered.
;;
;;   runs_on.cljc --write   rewrite the covered workflow lines
;;   runs_on.cljc --check   fail if any covered line differs from the template
;; Ported from runs_on.py (Basilisp). Run from the repo root: basilisp run scripts/ci-runners/runs_on.cljc -- --check
(ns runs-on
  (:require [basilisp.string :as str])
  (:import os pathlib re sys))

(def root (.resolve (pathlib/Path (or (.get os/environ "AMU_ROOT") "."))))
(def workflows (.joinpath root ".github/workflows"))

;; file -> hosted labels that are covered (others stay literal).
(def covered-labels
  {"selfhost-native.yml" #{"ubuntu-24.04-arm" "ubuntu-24.04" "${{ matrix.runner }}"}
   "native-definition-graph.yml" #{"ubuntu-24.04-arm" "ubuntu-24.04" "${{ matrix.runner }}"}
   "native-definition-build.yml" #{"${{ matrix.runner }}"}
   "native-definition-cid.yml" #{"${{ matrix.runner }}"}
   "native-definition-cids.yml" #{"${{ matrix.runner }}"}
   "native-checked-definition.yml" #{"${{ matrix.runner }}"}
   "native-checked-source.yml" #{"${{ matrix.runner }}"}
   "native-capability-names.yml" #{"ubuntu-24.04-arm"}
   "mac-selfhost-aiueos.yml" #{"ubuntu-24.04-arm" "ubuntu-24.04" "macos-15"}})

;; (file, job) that stay hosted: they need Docker-in-job or Chrome, which the runner image does not provide.
(def hosted-only #{["selfhost-native.yml" "qualify-arm64-runtime"] ["selfhost-native.yml" "wasm32-browser-chrome"]})
;; Never covered, whatever the file: jobs with secrets or write tokens.
(def never #{"post-merge-repin.yml"})

(def arm-profiles "[\"selfhosted\",\"selfhosted-arm\"]")
(def guard (str "(github.event_name != 'pull_request' || "
                "github.event.pull_request.head.repo.full_name == github.repository)"))
(def arm (str "contains(fromJSON('" arm-profiles "'), vars.AMU_RUNNER_PROFILE) && " guard))
(def x86 (str "vars.AMU_RUNNER_PROFILE == 'selfhosted' && " guard))

(def expr
  {"ubuntu-24.04-arm" (str "${{ " arm " && 'amu-linux-arm64' || 'ubuntu-24.04-arm' }}")
   "ubuntu-24.04"     (str "${{ " x86 " && 'amu-linux-x86_64' || 'ubuntu-24.04' }}")
   "macos-15"         (str "${{ " arm " && 'amu-macos-arm64' || 'macos-15' }}")
   "${{ matrix.runner }}"
   (str "${{ matrix.runner == 'ubuntu-24.04-arm' && (" arm " && 'amu-linux-arm64' || matrix.runner)"
        " || (" x86 " && 'amu-linux-x86_64' || matrix.runner) }}")})

(def line-re (re/compile "^(\\s*)runs-on: (.*?)(\\s+# amu-runner: (.+))?$"))
(def job-re (re/compile "^  ([A-Za-z0-9_-]+):\\s*$"))

(defn transform
  "Returns [new-text problems]; problems is a vector of [line-no message]."
  [text covered write fname]
  (loop [lines (map-indexed vector (.split text "\n")) ; Python split keeps the trailing empty element
         job "" out [] problems []]
    (if-let [[[i line] & more] (seq lines)]
      (let [n (inc i)
            jm (.match job-re line)
            job (if jm (.group jm 1) job)
            m (.match line-re line)]
        (if-not m
          (recur more job (conj out line) problems)
          (let [indent (.group m 1) value (.group m 2) tag (.group m 4)]
            (cond
              (contains? hosted-only [fname job])
              (recur more job (conj out line)
                     (if (or tag (str/includes? value "amu-"))
                       (conj problems [n "hosted-only job carries a self-hosted label"])
                       problems))

              tag
              (recur more job (conj out line)
                     (if (not= value (get expr tag))
                       (conj problems [n (str "differs from template for " tag)])
                       problems))

              (contains? covered value)
              (if write
                (recur more job (conj out (str indent "runs-on: " (get expr value) "  # amu-runner: " value)) problems)
                (recur more job (conj out line)
                       (conj problems [n (str "hosted literal " (python/repr value) " not rendered")])))

              (or (str/includes? value "amu-linux") (str/includes? value "amu-macos"))
              (recur more job (conj out line) (conj problems [n "self-hosted label outside the template"]))

              :else (recur more job (conj out line) problems)))))
      [(str/join "\n" out) problems])))

(defn -main [& argv]
  (let [write (some #{"--write"} argv)
        files (sort-by #(.-name %) (python/list (.glob workflows "*.yml")))
        bad (reduce
              (fn [bad p]
                (let [text (.read-text p)
                      nm (.-name p)
                      cov (if (contains? never nm) #{} (get covered-labels nm #{}))
                      [new problems] (transform text cov write nm)
                      problems (if (and (contains? never nm) (re/search "amu-(linux|macos)" text))
                                 (conj problems [0 "self-hosted label in a secret-bearing workflow"])
                                 problems)]
                  (when (and write (not= new text)) (.write-text p new))
                  (doseq [[n why] problems] (println (str nm ":" n ": " why)))
                  (+ bad (count problems))))
              0 files)]
    (when (and (not write) (pos? bad)) (sys/exit 1))
    (println (if (zero? bad) "ok" (str bad " problem(s)")))))

(when (some #(or (= % "runs_on.cljc") (str/ends-with? % "/runs_on.cljc")) sys/argv)
  (apply -main *command-line-args*))
