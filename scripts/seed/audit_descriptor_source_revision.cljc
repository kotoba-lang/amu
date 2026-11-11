;; Compare descriptor source unity with bytes at a specified Git commit. Ported from
;; audit-descriptor-source-revision.py (Basilisp, JUN-974).
;;
;; This audits locally available tree content only. Missing objects are refused; Git must support --no-lazy-fetch.
;; Replacement refs are not used. A match does not establish compiler build provenance, qualification, or release
;; readiness. A null sourceRevision is the regenerated-descriptor state (JUN-631): the descriptor's own commit is
;; then the source tree audited, so no follow-up commit has to name a squash commit after merge.
;; Run (repo root): basilisp run -p scripts/seed scripts/seed/audit_descriptor_source_revision.cljc --
;;   --descriptor-revision SHA [--source-revision SHA]
;; Exit: 0 MATCH, 1 MISMATCH, 2 REFUSED.
(ns audit-descriptor-source-revision
  (:require [basilisp.string :as str]
            [gate-util :as u])
  (:import hashlib json operator pathlib re subprocess sys))

(def root (atom u/root))   ; tests point this at a scratch repository
(def sha-re (re/compile "[0-9a-f]{40}\\Z"))
(def path-re (re/compile "seed/[A-Za-z0-9_.-]+\\.kotoba\\Z"))

(defn g [m & ks] (reduce (fn [a k] (operator/getitem a k)) m ks))

(defn git [& args]
  (.-stdout (subprocess/run (python/list (concat ["git" "--no-lazy-fetch" "--no-replace-objects" "-C" (str @root)] args))
                            ** :check true :stdout subprocess/PIPE :stderr subprocess/PIPE)))

(defn commit [value]
  (when-not (and (string? value) (.fullmatch sha-re value))
    (throw (python/ValueError "revision must be a full lowercase 40-character commit")))
  (let [resolved (.strip (.decode (git "rev-parse" "--verify" (str value "^{commit}"))))]
    (when (not= resolved value) (throw (python/ValueError "revision did not resolve to itself")))
    value))

(defn blob [revision path] (git "show" (str revision ":" path)))

(defn audit [descriptor-revision source-override]
  (let [descriptor-revision (commit descriptor-revision)
        d (json/loads (blob descriptor-revision "native-product.json"))
        declared (g d "sourceRevision")
        source-revision (cond (some? source-override) (commit source-override)
                              (nil? declared) descriptor-revision
                              :else (commit declared))]
    (when (not= (g d "sourceManifest") "seed/FULL-MANIFEST") (throw (python/ValueError "unexpected manifest path")))
    (let [lines (.splitlines (.decode (blob descriptor-revision (g d "sourceManifest")) "utf-8"))
          paths (vec (filter #(and (seq %) (not (.startswith % "#"))) lines))]
      (when (or (empty? paths) (not= (count paths) (g d "sourceModuleCount")) (not= (count paths) (count (set paths)))
                (some #(not (.fullmatch path-re %)) paths))
        (throw (python/ValueError "manifest paths, duplicates or module count invalid")))
      (let [digest (hashlib/sha256)
            size (atom 0)]
        (doseq [path paths]
          (let [data (operator/add (blob source-revision path) (u/bytes-of 10))]
            (.update digest data)
            (swap! size + (python/len data))))
        (let [actual (u/pydict "bytes" @size "sha256" (.hexdigest digest))
              expected (g d "sourceUnity")
              matched (u/deq actual expected)]
          (u/pydict "status" (if matched "MATCH" "MISMATCH") "descriptorRevision" descriptor-revision
                    "descriptorSourceRevision" declared "sourceRevisionTested" source-revision
                    "comparedDeclaredSourceRevision" (= source-revision (or declared descriptor-revision))
                    "sourceRevisionImplicit" (nil? declared)
                    "modules" (count paths) "expectedUnity" expected "actualUnity" actual
                    "compilerBuildProvenanceVerified" false "publicReleaseQualified" false))))))

(defn run [args]
  (let [descriptor (or (u/opt args "--descriptor-revision") (sys/exit "--descriptor-revision is required"))
        source (u/opt args "--source-revision")]
    (try
      (let [result (audit descriptor source)]
        (println (json/dumps result ** :indent 2))
        (if (= (g result "status") "MATCH") 0 1))
      (catch python/Exception e
        (if (or (instance? python/KeyError e) (instance? python/ValueError e) (instance? python/OSError e)
                (instance? subprocess/CalledProcessError e))
          (do (println (json/dumps (u/pydict "status" "REFUSED" "reason" (str e)))) 2)
          (throw e))))))

(defn -main [& args] (sys/exit (run args)))

(when (some #(or (= % "audit_descriptor_source_revision.cljc") (str/ends-with? % "/audit_descriptor_source_revision.cljc")) sys/argv)
  (apply -main *command-line-args*))
