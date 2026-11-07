;; Shared helpers for the Basilisp ports of the native gate scripts (JUN-974).
;; Gate reports are Python dicts (insertion-ordered, JSON byte layout identical to the Python originals);
;; comparisons of such values go through operator/eq.
(ns gate-util
  (:import hashlib json operator os pathlib subprocess))

(def root
  "Repository root. Basilisp exposes no script path, so this is the working directory (gates run from the
  repo root); AMU_ROOT overrides."
  (.resolve (pathlib/Path (or (.get os/environ "AMU_ROOT") "."))))

(defn path [& parts] (apply pathlib/Path parts))

(defn pydict
  "Insertion-ordered Python dict from alternating keys and values."
  [& kvs]
  (python/dict (python/list (map python/tuple (partition 2 kvs)))))

(defn pylist [coll] (python/list coll))

(defn pydict-from
  "Insertion-ordered Python dict from [k v] pairs."
  [pairs]
  (python/dict (python/list (map python/tuple pairs))))

(defn concat-bytes [a b] (operator/add a b))

(defn to-py
  "Recursively convert Clojure maps/sequences to Python dicts/lists."
  [x]
  (cond (map? x) (python/dict (python/list (for [[k v] x] (python/tuple [k (to-py v)]))))
        (or (vector? x) (sequential? x)) (python/list (map to-py x))
        :else x))

(defn chk
  "Python `assert`: throws AssertionError when ok is falsey."
  ([ok] (chk ok "assertion failed"))
  ([ok message] (when-not ok (throw (python/AssertionError (str message))))))

(defn deq [a b] (operator/eq a b))
(defn geti [m k] (operator/getitem m k))
(defn has-bytes? [needle haystack] (operator/contains haystack needle))
(defn nonempty? [b] (pos? (python/len b)))
(defn bslice [data a b] (operator/getitem data (python/slice a b)))
(defn bytes-of [& ns] (python/bytes (python/list (or ns []))))
(defn bytes-of-n [n b] (python/bytes (python/list (repeat n b))))
(defn hex->bytes [s] (.fromhex python/bytes s))

(defn sha256-hex [data] (.hexdigest (hashlib/sha256 data)))

(defn pin
  "{bytes, sha256} of a file, as a Python dict."
  [p]
  (let [raw (.read_bytes (pathlib/Path p))]
    (pydict "bytes" (python/len raw) "sha256" (sha256-hex raw))))

(defn json-dump
  "json.dumps(value, indent=2) + newline, as every gate report is written."
  [value]
  (str (json/dumps value ** :indent 2) "\n"))

(defn read-json [p] (json/loads (.read_text (pathlib/Path p))))

(defn manifest-paths
  "Non-comment, non-empty lines of a manifest file."
  [p]
  (vec (filter #(and (seq %) (not (.startswith % "#"))) (.splitlines (.read_text (pathlib/Path p))))))

(defn opt
  "Value following flag k in args, or nil."
  [args k]
  (second (drop-while #(not= % k) args)))

(defn ksl-text
  "The source-lock file text the AIUEOS gates write next to each source."
  [source scope]
  (str "KSL1\nentry " source "\nroot " scope "\nfile " (geti (pin source) "sha256") " " source "\n"))

(defn run-process
  "subprocess.run(argv, env, capture_output, timeout) with every arg stringified."
  [argv env timeout & {:keys [pass-fds cwd]}]
  (let [args (python/list (map str argv))
        fds (python/tuple (or pass-fds []))]
    (if cwd
      (subprocess/run args ** :env env :capture_output true :timeout timeout :pass_fds fds :cwd cwd)
      (subprocess/run args ** :env env :capture_output true :timeout timeout :pass_fds fds))))

(defn parse-build-complete-output
  "The shared CLI of the AIUEOS gates: exactly one of --build/--complete, plus --output.
  Returns [build output complete] as resolved pathlib.Path (nil when absent)."
  [args]
  (let [build (opt args "--build") complete (opt args "--complete") out (opt args "--output")]
    (when (nil? out) (throw (python/SystemExit "--output is required")))
    (when (= (nil? build) (nil? complete)) (throw (python/SystemExit "exactly one of --build/--complete is required")))
    [(when build (.resolve (pathlib/Path build))) (.resolve (pathlib/Path out)) (when complete (.resolve (pathlib/Path complete)))]))
