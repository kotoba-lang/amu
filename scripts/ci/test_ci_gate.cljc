;; Negative controls for scripts/ci/ci_gate.cljc (JUN-759): what may be skipped, what must change a key and which
;; steps must stop when the gate skips. Ported from test_ci_gate.py.
;; Run from the repo root:
;;   PYTHONPATH=scripts/ci basilisp test -p no:cacheprovider --rootdir scripts/ci scripts/ci/test_ci_gate.cljc
(ns test-ci-gate
  (:require [basilisp.test :refer [deftest is testing]]
            [basilisp.string :as str]
            [ci-gate :as G])
  (:import io json os pathlib re subprocess tempfile))

(defn ->py [x]
  (cond (map? x) (python/dict (python/list (for [[k v] x] (python/tuple [k (->py v)]))))
        (sequential? x) (python/list (map ->py x))
        :else x))

(defn opener
  ([files] (opener files 1))
  ([files total]
   (fn [request _timeout]
     (let [url (.-full_url request)
           page (python/int (last (.rsplit url "page=" 1)))
           rows (mapv (fn [n] {"filename" n}) (take 100 (drop (* (dec page) 100) files)))]
       (io/BytesIO (.encode (json/dumps (->py {"files" rows "total_commits" total}))))))))

(deftest inert-paths
  (doseq [path ["README.md" "CHANGELOG.md" "docs/notes/a.md" "LICENSE" "bench/.DS_Store"
                ".github/dependabot.yml" "scripts/ci/pr_batch.cljc" "scripts/ci/test_pr_batch.cljc"]]
    (is (G/inert? path) path)))

(deftest everything-a-gate-can-read-is-not-inert
  (doseq [path ["docs/evidence/x/README.md" "docs/language-ladder.edn" "seed/README.md" "seed/00-core.kotoba"
                "scripts/seed/check-io-read.py" "scripts/seed/check-io-read.cljc" "scripts/ci/ci_gate.cljc"
                "scripts/ci/new_tool.cljc" "scripts/ci/pr_batch.cljc.bak" "scripts/ci/pr_batch.py" "bin/amu-linux-x86_64"
                "native-product.json" ".github/workflows/selfhost-native.yml" ".github/workflows/merge-guard.yml"
                ".github/actions/ci-gate/action.yml" "examples/foundation-starter/MACOS-ARM64.md"
                "tools/c/sm70/README.md" "src/a.kotoba"]]
    (is (not (G/inert? path)) path)))

(def rows [["100644" (apply str (repeat 40 "a")) "README.md"]
           ["100644" (apply str (repeat 40 "b")) "seed/x.kotoba"]
           ["100644" (apply str (repeat 40 "c")) "scripts/seed/check-gate.py"]
           ["100644" (apply str (repeat 40 "d")) "scripts/seed/selfhost-bootstrap.py"]
           ["100644" (apply str (repeat 40 "e")) "scripts/seed/test_gate.py"]
           ["100644" (apply str (repeat 40 "f")) "scripts/seed/check-gate2.cljc"]])

(def zeros (apply str (repeat 40 "0")))
(defn hash-of ([rs] (hash-of rs "marker" #{})) ([rs kind] (hash-of rs kind #{})) ([rs kind keep] (first (G/tree-hash rs kind keep))))
(defn with-blob [rs i blob] (assoc rs i (assoc (nth rs i) 1 blob)))

(deftest docs-do-not-change-either-key
  (let [changed (assoc rows 0 ["100644" (apply str (repeat 40 "f")) "README.md"])]
    (doseq [kind ["marker" "derive"]]
      (is (= (hash-of rows kind) (hash-of changed kind))))))

(deftest any-other-change-changes-the-marker
  (doseq [i (range 1 (count rows))]
    (is (not= (hash-of rows) (hash-of (with-blob rows i zeros))) (nth (nth rows i) 2))))

(deftest gate-scripts-change-only-the-marker-unless-the-derivation-references-them
  (doseq [[i name] [[2 "check-gate.py"] [5 "check-gate2.cljc"] [4 "test_gate.py"]]]
    (let [changed (with-blob rows i zeros)]
      (is (not= (hash-of rows) (hash-of changed)))
      (is (= (hash-of rows "derive") (hash-of changed "derive")) name)
      (is (not= (hash-of rows "derive" #{name}) (hash-of changed "derive" #{name})) name))))

(deftest derivation-inputs-always-change-the-derive-key
  (doseq [i [1 3]]
    (is (not= (hash-of rows "derive") (hash-of (with-blob rows i zeros) "derive")))))

(deftest kinds-and-mode-are-part-of-the-key
  (is (not= (hash-of rows "marker") (hash-of rows "derive")))
  (is (not= (hash-of (subvec rows 1 2)) (hash-of [["100755" (nth (nth rows 1) 1) (nth (nth rows 1) 2)]]))))

(deftest tiers
  (is (= ["pr" "pr" "main" "full" "full"] (mapv G/tier-of ["pull_request" "merge_group" "push" "schedule" "workflow_dispatch"])))
  (let [[exact others] (G/keys-for "marker" "j (1)" "Linux-X64" "pr" "h")]
    (is (and (str/ends-with? exact "-pr-h") (not (str/includes? exact " ")) (not (str/includes? exact "("))))
    (is (= ["main" "full"] (mapv #(second (reverse (.rsplit % "-" 2))) others))))
  (is (= ["full"] (mapv #(second (reverse (.rsplit % "-" 2))) (second (G/keys-for "marker" "j" "a" "main" "h")))))
  (is (= [] (second (G/keys-for "marker" "j" "a" "full" "h")))))

(deftest arch-is-part-of-the-key
  (is (not= (first (G/keys-for "marker" "j" "Linux-ARM64" "pr" "h")) (first (G/keys-for "marker" "j" "Linux-X64" "pr" "h")))))

(def env {"GITHUB_REPOSITORY" "o/r" "GITHUB_TOKEN" "t" "PR_BASE_SHA" "b" "PR_HEAD_SHA" "h" "MG_BASE_SHA" "b" "MG_HEAD_SHA" "h"})
(defn check-docs ([event files] (check-docs event files 1)) ([event files total] (G/docs-only? event env (opener files total))))

(deftest only-inert-files-skip
  (doseq [event ["pull_request" "merge_group"]]
    (is (check-docs event ["README.md" "docs/a.md"]))
    (is (not (check-docs event ["README.md" "seed/00-core.kotoba"])))
    (is (not (check-docs event ["README.md" "docs/evidence/a/README.md"])))
    (is (not (check-docs event [])))))

(deftest unknown-or-large-answers-never-skip
  (is (not (check-docs "pull_request" (vec (repeat 301 "README.md")))))
  (is (not (check-docs "pull_request" ["README.md"] 0)))
  (is (not (G/docs-only? "pull_request" (dissoc env "GITHUB_TOKEN") (opener ["README.md"]))))
  (is (not (G/docs-only? "pull_request" env (fn [_ _] (throw (python/OSError "offline")))))))

(deftest push-schedule-and-dispatch-never-skip
  (doseq [event ["push" "schedule" "workflow_dispatch" ""]]
    (is (not (G/docs-only? event env (opener ["README.md"]))))))

(deftest rename-out-of-a-real-path-is-not-docs-only
  (is (not (G/docs-only? "pull_request" env
                         (fn [_ _] (io/BytesIO (.encode (json/dumps (->py {"files" [{"filename" "docs/a.md" "previous_filename" "seed/a.kotoba"}]
                                                                    "total_commits" 1})))))))))

(deftest closure-follows-names-and-imports
  (with-open [tmp (tempfile/TemporaryDirectory)]
    (let [d (.joinpath (pathlib/Path tmp) "scripts/seed")]
      (.mkdir d ** :parents true)
      (.write_text (.joinpath d "a.py") "import helper\nx = 'check-b.py'\n")
      (.write_text (.joinpath d "helper.py") "")
      (.write_text (.joinpath d "check-b.py") "")
      (.write_text (.joinpath d "check-unrelated.py") "")
      (is (= #{"a.py" "helper.py" "check-b.py"} (G/closure ["a.py"] tmp)))
      ;; a Basilisp script is followed through :require and through a literal file name
      (.write_text (.joinpath d "run_it.cljc") "(ns run-it (:require [some-helper :as h]))\n;; see check-c.cljc\n")
      (.write_text (.joinpath d "some_helper.cljc") "")
      (.write_text (.joinpath d "check-c.cljc") "")
      (is (= #{"run_it.cljc" "some_helper.cljc" "check-c.cljc"} (G/closure ["run_it.cljc"] tmp)))
      (is (thrown? python/SystemExit (G/closure ["missing.py"] tmp))))))

(deftest tracked-and-main
  (with-open [tmp (tempfile/TemporaryDirectory)]
    (let [run (fn [& a] (subprocess/check_call (python/list (concat ["git" "-C" tmp] a)) ** :stdout subprocess/DEVNULL))
          p (pathlib/Path tmp)]
      (run "init" "-q")
      (.mkdir (.joinpath p "seed"))
      (.write_text (.joinpath p "seed/a.kotoba") "x")
      (.write_text (.joinpath p "README.md") "doc")
      (run "add" ".")
      (is (= ["README.md" "seed/a.kotoba"] (vec (sort (map #(nth % 2) (G/tracked tmp))))))
      (let [out (.joinpath p "out")]
        (G/main ["--job" "j" "--root" tmp]
                {"GITHUB_EVENT_NAME" "push" "GITHUB_OUTPUT" (str out) "RUNNER_OS" "Linux" "RUNNER_ARCH" "ARM64"})
        (let [text (.read_text out)]
          (is (str/includes? text "always_run=true"))
          (is (str/includes? text "restore=false"))
          (is (str/includes? text "docs_only=false"))
          (is (str/includes? text "amu-ci-marker-v1-j-Linux-ARM64-main-")))))))

(def gate "./.github/actions/ci-gate")
(def guard "steps.gate.outputs.skip != 'true'")
;; Reads only `needs` results, so it runs on a skip too: a skipped job must not hide a failed shard.
(def may-run-when-skipped
  #{["selfhost-native.yml" "qualify-x86_64"
     "Require the shards and the runtime checks even when the gate skipped the steps (JUN-759)"]})

(defn steps-by-job
  "Job id to its steps' keys, read by line: the runners have no YAML module, and these workflows keep jobs at
  indent 2, `steps:` at 4, steps at 6 and step keys at 8. every-gate-is-seen fails if that stops holding.
  Returns an ordered vector of [job steps]."
  [text]
  (let [body (second (.split text "\njobs:\n" 1))]
    (loop [lines (.splitlines body) job nil steps nil jobs [] ] ; steps: index into jobs entry or nil
      (if-let [[line & more] (seq lines)]
        (let [id-line (re/match "^  ([A-Za-z0-9_-]+):\\s*$" line)]
          (cond
            id-line (recur more (.group id-line 1) nil jobs)
            (re/match "^    steps:\\s*$" line)
            (let [idx (first (keep-indexed (fn [i [j _]] (when (= j job) i)) jobs))
                  jobs (if idx jobs (conj jobs [job []]))
                  idx (or idx (dec (count jobs)))]
              (recur more job idx jobs))
            (re/match "^    [^\\s#]" line) (recur more job nil jobs)
            (some? steps)
            (let [new-step (str/starts-with? line "      - ")
                  line (if new-step (str "        " (subs line (count "      - "))) line)
                  jobs (if new-step (update-in jobs [steps 1] conj {}) jobs)
                  key (re/match "^        ([a-z-]+):\\s*(.*)$" line)]
              (recur more job steps
                     (if key
                       (let [last-i (dec (count (get-in jobs [steps 1])))
                             cur (get-in jobs [steps 1 last-i])]
                         (if (contains? cur (.group key 1))
                           jobs
                           (assoc-in jobs [steps 1 last-i (.group key 1)] (.group key 2))))
                       jobs)))
            :else (recur more job steps jobs)))
        jobs))))

(defn gated-jobs [text]
  (vec (for [[job steps] (steps-by-job text) :when (some #(= gate (get % "uses")) steps)] job)))

(defn unguarded
  "[job step] of each step after a job's gate that would still run when the gate skips."
  [text]
  (vec (for [[job steps] (steps-by-job text)
             :let [idx (first (keep-indexed (fn [i s] (when (= gate (get s "uses")) i)) steps))]
             :when idx
             s (drop (inc idx) steps)
             :when (not (str/includes? (get s "if" "") guard))]
         [job (get s "name" (get s "uses"))])))

(def head (str "on:\n  pull_request:\n    paths:\n      - 'seed/**'\njobs:\n  plain:\n    steps:\n      - name: no gate\n"
               "        run: a\n  gated:\n    needs:\n      - plain\n    steps:\n      - name: before\n        run: b\n"
               "      - id: gate\n        uses: " gate "\n        with:\n          job: gated\n"))

(deftest guarded-steps-pass-in-every-form
  (doseq [step [(str "      - name: s\n        if: " guard "\n        run: c\n")
                (str "      - name: s\n        if: always() && " guard " && (matrix.shard == 'core')\n        run: c\n")
                (str "      - if: success() && " guard "\n        uses: ./.github/actions/ci-save\n")
                (str "      - uses: actions/upload-artifact@x\n        if: " guard "\n        with:\n          name: n\n")]]
    (is (= [] (unguarded (str head step))) step)))

(deftest a-step-the-gate-would-not-stop-is-found
  (doseq [condition ["" "        if: matrix.target == 'x86_64'\n" "        if: always()\n"
                     "        if: steps.gate.outputs.hit != 'true'\n" "        if: steps.gate.outputs.skip == 'true'\n"]]
    (is (= [["gated" "s"]] (unguarded (str head "      - name: s\n" condition "        run: c\n"))) condition)))

(deftest one-missing-guard-among-guarded-steps-is-found
  (let [steps (str "      - name: a\n        if: " guard "\n        run: c\n      - name: b\n        run: |\n          d\n"
                   "      - name: e\n        if: " guard "\n        run: f\n")]
    (is (= [["gated" "b"]] (unguarded (str head steps))))))

(deftest only-steps-after-a-gate-count
  (is (= [] (unguarded head)))
  (is (= ["gated"] (gated-jobs head)))
  (is (= [] (unguarded (str head "  later:\n    steps:\n      - name: other job\n        run: g\n")))))

(deftest text-inside-a-run-block-is-not-a-step
  (let [step (str "      - name: s\n        if: " guard "\n        run: |\n          cat <<EOF\n          - name: x\n          EOF\n")]
    (is (= [] (unguarded (str head step))))))

(deftest job-keys-after-the-steps-end-them
  (let [step (str "      - name: s\n        if: " guard "\n        run: c\n    outputs:\n      - not-a-step: 1\n")]
    (is (= [] (unguarded (str head step))))))

(def workflows
  (let [root (.resolve (pathlib/Path (or (.get os/environ "AMU_ROOT") ".")))]
    (vec (sort-by #(.-name %) (python/list (.glob (.joinpath root ".github/workflows") "*.y*ml"))))))

(deftest every-gate-is-seen
  (let [total (reduce
                (fn [total path]
                  (let [text (.read_text path)
                        gates (count (python/list (re/finditer (str "^\\s+(?:- )?uses: " (re/escape gate) "\\s*$") text re/M)))]
                    (when (pos? gates)
                      (is (= gates (count (gated-jobs text))) (.-name path)))
                    (+ total gates)))
                0 workflows)]
    (is (pos? total))))

(deftest every-later-step-stops-when-the-gate-skips
  (let [found (set (for [path workflows
                         :let [text (.read_text path)]
                         :when (str/includes? text gate)
                         row (unguarded text)]
                     (into [(.-name path)] row)))]
    (is (= may-run-when-skipped found))))
