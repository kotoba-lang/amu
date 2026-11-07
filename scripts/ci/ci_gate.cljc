;; Input-hash gate for the native CI jobs (JUN-759). Scheduling only, no verdict.
;;
;; A job asks this script two questions before its heavy steps:
;;
;; * docs_only: does the pull request / merge-group entry change only inert files
;;   (documentation)? Then the native verdict of its base applies
;;   unchanged and the job reports success without running its steps. The required
;;   check still runs and reports under its own name.
;; * key / restore_keys: the cache key for a marker or a derived-artifact cache,
;;   made of a content hash of the job's inputs (every tracked file except the
;;   inert ones) plus the runner arch and the tier. Pushes to main, the schedule
;;   and manual dispatch never skip: they run the full suite as the safety net and
;;   only write markers/caches. The caller saves a marker only after a job passed.
;;
;; Two kinds:
;;   marker  key over the whole tree (minus inert files); a hit means this exact
;;           tree already passed this job on main/schedule (or earlier in the
;;           same ref), so the job may skip.
;;   derive  key over the derivation inputs only: the tree minus inert files minus
;;           the gate-only scripts (scripts/seed/check-*.py|cljc, test_*.py|cljc) that the
;;           derivation scripts do not reference. A hit restores the exact
;;           derived compiler artifacts instead of re-deriving them. Gate scripts
;;           that run on the restored artifacts are never cached.
;; Ported from ci_gate.py (Basilisp). The script set under scripts/seed is mixed .py and .cljc during the
;; migration (JUN-974); both extensions are gate scripts / derivation inputs.
;; Run: basilisp run scripts/ci/ci_gate.cljc -- --job J [--kind marker|derive] [--roots a.py,b.cljc] [--root DIR]
(ns ci-gate
  (:require [basilisp.string :as str])
  (:import hashlib json os re subprocess sys urllib.request))

(def version "v1")
;; Files whose content no native job reads. docs/evidence is read by gates and is NOT inert; seed/README.md etc. are
;; under seed/ and are NOT inert; top-level Markdown is read by no script.
(def inert
  [(re/compile "^[^/]*\\.md$")
   (re/compile "^LICENSE$")
   (re/compile "^docs/(?!evidence/).*\\.md$")
   (re/compile "(^|/)\\.DS_Store$")
   (re/compile "^\\.github/dependabot\\.yml$")
   ;; JUN-818: repository tooling no native job reads (PR batching helper, post-merge repin allowlist and its
   ;; disabled bot workflow, which only runs on main/dispatch). Named one by one: a new file is never inert.
   (re/compile "^scripts/ci/(pr_batch|test_pr_batch)\\.cljc$")])
(def tiers ["pr" "main" "full"])
(def seed "scripts/seed/")
(def script-ext-re "(?:py|cljc)")

(defn inert? [path] (boolean (some #(re/search % path) inert)))

(defn tracked
  ([] (tracked "."))
  ([root]
   (let [raw (subprocess/check_output ["git" "-C" root "ls-files" "-s" "-z"])]
     (vec (for [item (.split raw (python/bytes [0]))
                :when (seq item)
                :let [[meta path] (.split item (python/bytes [9]) 1)
                      [mode blob _stage] (.split (.decode meta))]]
            [mode blob (.decode path)])))))

(defn- stem-of [file] (str/replace (re/sub (str "\\." script-ext-re "$") "" file) "-" "_"))

(defn local-refs
  "Script file names mentioned by name or imported/required from text. A superset of the real imports."
  [text files stems own]
  (let [by-name (for [m (python/list (re/finditer (str "[A-Za-z0-9_\\-]+\\." script-ext-re) text))
                      :let [n (.group m 0)]
                      :when (and (contains? files n) (not= n own))]
                  n)
        py-imports (for [m (python/list (re/finditer "^\\s*(?:from|import)\\s+([A-Za-z_][A-Za-z0-9_]*)" text re/M))
                         :let [n (get stems (.group m 1))]
                         :when (and n (not= n own))]
                     n)
        ;; (:require [some-ns :as x]) / (:require [some-ns :refer [..]]) -> some_ns.cljc
        cljc-requires (for [m (python/list (re/finditer "\\[([A-Za-z][A-Za-z0-9._-]*)\\s+:(?:as|refer)" text))
                            :let [n (get stems (str/replace (.group m 1) "-" "_"))]
                            :when (and n (not= n own))]
                        n)]
    (set (concat by-name py-imports cljc-requires))))

(defn closure
  "The scripts/seed script files (.py/.cljc) transitively mentioned by name from the roots."
  ([roots] (closure roots "."))
  ([roots root]
   (let [directory (os.path/join root seed)
         files (set (filter #(re/search (str "\\." script-ext-re "$") %) (os/listdir directory)))
         stems (into {} (map (juxt stem-of identity)) (sort files))]
     (loop [seen #{} pending (vec (filter seq roots))]
       (if (empty? pending)
         seen
         (let [name (peek pending) pending (pop pending)]
           (if (contains? seen name)
             (recur seen pending)
             (do
               (when-not (contains? files name)
                 (sys/exit (str "unknown derivation root script: " name)))
               (let [text (with-open [stream (python/open (os.path/join directory name) ** :encoding "utf-8" :errors "replace")]
                            (.read stream))]
                 (recur (conj seen name) (into pending (sort (local-refs text files stems name)))))))))))))

(defn gate-only? [path keep]
  (and (str/starts-with? path seed)
       (not (str/includes? (subs path (count seed)) "/"))
       (let [name (subs path (count seed))]
         (and (or (str/starts-with? name "check-") (str/starts-with? name "test_"))
              (boolean (re/search (str "\\." script-ext-re "$") name))
              (not (contains? keep name))))))

(defn tree-hash
  ([rows kind] (tree-hash rows kind #{}))
  ([rows kind keep]
   (let [digest (hashlib/sha256)]
     (.update digest (.encode (str version "\n" kind "\n")))
     (let [count (reduce
                   (fn [n [mode blob path]]
                     (if (or (inert? path) (and (= kind "derive") (gate-only? path keep)))
                       n
                       (do (.update digest (.encode (str mode " " blob " " path "\n")))
                           (inc n))))
                   0 (sort-by #(nth % 2) rows))]
       [(.hexdigest digest) count]))))

(defn tier-of [event]
  (get {"pull_request" "pr" "merge_group" "pr" "push" "main"} event "full"))

(defn accepted
  "A result from this tier or a stronger one may stand in for the requested tier."
  [tier]
  (if (not= tier "pr") (vec (drop (.index (python/list tiers) tier) tiers)) tiers))

(defn- strip-dashes [s] (.strip s "-"))

(defn keys-for
  "[exact others] cache keys."
  [kind job arch tier digest]
  (let [base (str "amu-ci-" kind "-" version "-" (strip-dashes (re/sub "[^A-Za-z0-9_.-]+" "-" job)) "-"
                  (strip-dashes (re/sub "[^A-Za-z0-9_.-]+" "-" arch)))
        exact (str base "-" tier "-" digest)
        others (vec (for [t (accepted tier) :when (not= t tier)] (str base "-" t "-" digest)))]
    [exact others]))

(defn default-opener [request timeout]
  (urllib.request/urlopen request ** :timeout timeout))

(defn changed-files
  "Files changed by head relative to base, or nil when unknown (then nothing is skipped)."
  [repo base head token opener]
  (loop [page 1 names []]
    (if (> page 3)
      nil
      (let [url (str "https://api.github.com/repos/" repo "/compare/" base "..." head "?per_page=100&page=" page)
            request (urllib.request/Request url ** :headers {"Accept" "application/vnd.github+json"
                                                              "Authorization" (str "Bearer " token)
                                                              "X-GitHub-Api-Version" "2022-11-28"})
            body (try
                   (with-open [response (opener request 30)]
                     (json/load response))
                   (catch python/Exception error ; an unknown answer never skips
                     (.write sys/stderr (str "compare unavailable: " error "\n"))
                     ::unknown))]
        (if (= body ::unknown)
          nil
          (let [files (or (get body "files") [])
                names (reduce (fn [names row]
                                (cond-> (conj names (get row "filename"))
                                  (get row "previous_filename") (conj (get row "previous_filename"))))
                              names files)]
            (if (< (count files) 100)
              (if (> (get body "total_commits" 1) 0) names nil)
              (recur (inc page) names))))))))

(defn docs-only?
  ([event env] (docs-only? event env default-opener))
  ([event env opener]
   (let [[base head] (case event
                       "pull_request" [(get env "PR_BASE_SHA") (get env "PR_HEAD_SHA")]
                       "merge_group" [(get env "MG_BASE_SHA") (get env "MG_HEAD_SHA")]
                       nil)]
     (if-not (and base head (seq base) (seq head) (seq (get env "GITHUB_REPOSITORY")) (seq (get env "GITHUB_TOKEN")))
       false
       (let [names (changed-files (get env "GITHUB_REPOSITORY") base head (get env "GITHUB_TOKEN") opener)]
         (boolean (and (seq names) (every? inert? names))))))))

(defn emit [values path]
  (let [lines (apply str (for [[k v] values] (str (name k) "=" v "\n")))]
    (.write sys/stdout lines)
    (when path
      (with-open [stream (python/open path "a" ** :encoding "utf-8")]
        (.write stream lines)))))

(defn- parse-args [args]
  (loop [m {:kind "marker" :roots "" :root "." :job nil} [a v & more :as xs] (seq args)]
    (cond
      (empty? xs) (do (when-not (:job m) (sys/exit "--job is required"))
                      (when-not (contains? #{"marker" "derive"} (:kind m)) (sys/exit "--kind must be marker or derive"))
                      m)
      (= a "--job") (recur (assoc m :job v) more)
      (= a "--kind") (recur (assoc m :kind v) more)
      (= a "--roots") (recur (assoc m :roots v) more)
      (= a "--root") (recur (assoc m :root v) more)
      :else (sys/exit (str "unknown argument " a)))))

(defn main
  ([argv] (main argv (into {} (map (fn [[k v]] [k v])) (.items os/environ))))
  ([argv env]
   (let [{:keys [job kind roots root]} (parse-args argv)
         event (get env "GITHUB_EVENT_NAME" "")
         tier (tier-of event)
         keep (if (= kind "derive") (closure (mapv str/trim (.split roots ",")) root) #{})
         [digest n] (tree-hash (tracked root) kind keep)
         arch (str (get env "RUNNER_OS" "Linux") "-" (get env "RUNNER_ARCH" "X64"))
         [exact others] (keys-for kind job arch tier digest)
         inert-only (docs-only? event env)
         always (not= tier "pr")
         path (get env "GITHUB_OUTPUT")]
     (emit [[:docs_only (if inert-only "true" "false")] [:always_run (if always "true" "false")] [:tier tier]
            [:inputs n] [:digest digest] [:key exact]
            [:restore (if (or inert-only always) "false" "true")]]
           path)
     ;; restore-keys is multi-line: write it as a delimited block
     (when path
       (with-open [stream (python/open path "a" ** :encoding "utf-8")]
         (.write stream (str "restore_keys<<EOF_KEYS\n" (str/join "\n" others) "\nEOF_KEYS\n"))))
     (println (str "restore_keys: " (python/repr (python/list others)))))))

(when (some #(or (= % "ci_gate.cljc") (str/ends-with? % "/ci_gate.cljc")) sys/argv)
  (main *command-line-args*))
