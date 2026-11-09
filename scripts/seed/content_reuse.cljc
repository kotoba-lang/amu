;; Content-addressed reuse for the selfhost orchestration scripts.
;;
;; A stored result may stand in for a call only when its key matches exactly: the sha256 of every existing file the
;; call's argv names (the producing image first, then its inputs), the argv and the full environment (the output
;; directory written as $OUT), the host and the declared outputs. Orchestrates processes and hashes only. Ported
;; from content_reuse.py (Basilisp, JUN-974). A Runs value is a map {:out :calls (atom) :reuse :store}.
(ns content-reuse
  (:require [gate-util :as u])
  (:import hashlib json operator os pathlib platform shutil subprocess sys time))

(def run-path "/usr/bin:/bin")
(def reuse-version 1)   ; bump when the meaning of a reuse record changes
(def scripts ["scripts/seed/content_reuse.py" "scripts/seed/selfhost-bootstrap.py" "scripts/seed/check-x86_64-native.py"])
(def root-image "seed/bootstrap/aarch64-linux-static-root.elf")
(def manifests ["seed/X86_64-LINUX-SELFHOST-MANIFEST" "seed/CORE-STATIC-MANIFEST" "seed/MANIFEST"])

(defn pin [p] (u/pin p))

(defn runs
  "A record stored alongside an artifact cannot authenticate it. Until a separately trusted producer binds output pins
  to the full input closure, never consume a persisted result as a successful call."
  ([out] (runs out nil nil))
  ([out reuse store]
   (let [out (pathlib/Path out)]
     (.mkdir (pathlib/Path out "raw") ** :exist_ok true)
     {:out out :calls (atom []) :reuse reuse :store store})))

(defn calls [r] @(:calls r))

(defn- record! [r call]
  (swap! (:calls r) conj call)
  (.write_text (pathlib/Path (:out r) "calls.json") (str (json/dumps (python/list @(:calls r)) ** :indent 1) "\n")))

(defn run
  "Run argv in the output directory with PATH plus env; returns the CompletedProcess. With success (default) a
  non-zero exit or any stderr is an assertion failure."
  [r name argv env & {:keys [success timeout] :or {success true timeout 3600}}]
  (let [argv (mapv str argv)
        t (time/monotonic)
        full-env (python/dict (merge {"PATH" run-path} env))
        p (subprocess/run (python/list argv) ** :cwd (:out r) :env full-env :capture_output true :timeout timeout)]
    (.write_bytes (pathlib/Path (:out r) "raw" (str name ".stdout")) (.-stdout p))
    (.write_bytes (pathlib/Path (:out r) "raw" (str name ".stderr")) (.-stderr p))
    (record! r (u/pydict "name" name "argv" (python/list argv) "env" (u/to-py env) "exit" (.-returncode p)
                         "seconds" (python/round (- (time/monotonic) t) 1)))
    (when (and success (or (not= (.-returncode p) 0) (pos? (python/len (.-stderr p)))))
      (throw (python/AssertionError (python/tuple [name (.-returncode p) (.decode (.-stderr p) "utf-8" "replace")]))))
    p))

(defn key-material
  "Every input byte of a call: the sha256 of each existing file its argv names (the producing image first), the argv
  and the full environment with the output directory written as $OUT, and the declared outputs."
  [r argv env outputs]
  (let [out-str (str (:out r))
        norm (fn [v] (.replace (str v) out-str "$OUT"))
        files (u/pydict-from (for [a argv
                                   :let [pa (pathlib/Path (str a))]
                                   :when (and (.is_absolute pa) (.is_file pa))]
                               [(norm a) (pin pa)]))]
    (when-not (operator/contains files (norm (first argv)))
      (throw (python/AssertionError "the producing image must be a file")))
    (u/pydict "version" reuse-version "host" (python/list [(platform/system) (platform/machine)])
              "argv" (python/list (map norm argv))
              "env" (u/pydict-from (for [[k v] (sort-by first (merge {"PATH" run-path} env))] [k (norm v)]))
              "inputs" files "outputs" (python/sorted (python/list (map norm outputs))))))

(defn run-cached
  "run(), plus the content-addressed record of the identical call. The key covers every input byte (key-material).
  Do not replay stdout, stderr or a historical success verdict."
  [r name argv env outputs & {:keys [timeout] :or {timeout 3600}}]
  (let [material (key-material r argv env outputs)
        key (u/sha256-hex (.encode (json/dumps material ** :sort_keys true)))]
    (run r name argv env :timeout timeout)
    (let [calls- (:calls r)]
      (swap! calls- (fn [cs] (conj (pop cs) (doto (peek cs) (operator/setitem "key" key))))))
    (when-let [store (:store r)]
      (let [entry (pathlib/Path store key)]
        (.mkdir entry ** :parents true :exist_ok false)
        (doseq [o outputs]
          (shutil/copyfile o (pathlib/Path entry (.-name (pathlib/Path o)))))
        (let [origin (let [m (into {} (for [k ["GITHUB_REPOSITORY" "GITHUB_RUN_ID" "GITHUB_RUN_ATTEMPT" "GITHUB_SHA" "GITHUB_EVENT_NAME"]
                                           :when (operator/contains os/environ k)]
                                       [k (operator/getitem os/environ k)]))]
                       (if (seq m) (u/pydict-from (for [k ["GITHUB_REPOSITORY" "GITHUB_RUN_ID" "GITHUB_RUN_ATTEMPT" "GITHUB_SHA" "GITHUB_EVENT_NAME"] :when (contains? m k)] [k (get m k)])) "local"))
              record (u/pydict "key" key "material" material "from" origin
                               "outputs" (u/pydict-from (for [o outputs] [(.-name (pathlib/Path o)) (pin o)])))]
          (.write_text (pathlib/Path entry "record.json") (str (json/dumps record ** :indent 1) "\n")))))
    nil))

(defn lookup-key
  "A CI cache lookup hint, not the reuse key: the orchestration scripts and every source and image the reusable calls
  derive from. The exact per-call key is still checked by run-cached."
  [root]
  (let [h (hashlib/sha256)
        root (pathlib/Path root)
        file-digest (fn [p] (.digest (hashlib/sha256 (.read_bytes (pathlib/Path root p)))))]
    (doseq [p (concat scripts [root-image])] (.update h (file-digest p)))
    (doseq [manifest manifests]
      (doseq [p (cons manifest (filter #(and (seq %) (not (.startswith % "#"))) (.splitlines (.read_text (pathlib/Path root manifest)))))]
        (.update h (operator/add (operator/add (.encode p) (u/bytes-of 0)) (file-digest p)))))
    (.hexdigest h)))
