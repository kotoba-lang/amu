;; BOOTSTRAP REFERENCE (JVM + KIR interpreter): runs the infer guest over a cases file, batch by batch, in one process.
;; env GUEST CASES OUT KROOTS [BATCH] [FROM] [TO]
(require '[clojure.string :as str]
         '[kotoba.sema :as sema] '[kotoba.kir :as kir]
         '[kotoba.compiler.project :as project] '[kotoba.compiler.project-files :as pf])
(def env (System/getenv))
(def roots (vec (str/split (get env "KROOTS") #":")))
(defn typed-cap-call [id _ _ request]
  (case (long id)
    3 (let [md (java.security.MessageDigest/getInstance "SHA-256")]
        (apply str (map #(format "%02x" %) (.digest md (.getBytes (str request) "UTF-8")))))
    (throw (ex-info "unhandled capability" {:id id}))))
(def t0 (System/currentTimeMillis))
(defn log [& xs] (println (str "[" (quot (- (System/currentTimeMillis) t0) 1000) "s]") (apply str xs)) (flush))
(def graph (pf/load-closed-graph (get env "GUEST") roots))
(log "graph loaded")
(def linked (project/link-source (:sources graph) (:root graph)))
(log "linked")
(def lowered (kir/lower (sema/analyze (:source linked) {:admit-linked-synthetics? true})))
(log "lowered")
(def batch-bytes (Long/parseLong (or (get env "BATCH") "58000")))
(def lines (vec (remove str/blank? (str/split-lines (slurp (get env "CASES"))))))
(def from (Long/parseLong (or (get env "FROM") "0")))
(def to (Long/parseLong (or (get env "TO") (str (count lines)))))
(defn run [ls]
  (let [out (kir/execute lowered 'ie-diff-run [(str (str/join "\n" ls) "\n")]
                         {:typed-cap-call typed-cap-call :fuel 100000000000 :frames 100000 :cells 1000000000 :bytes 1000000000})]
    (if (map? out) (throw (ex-info "guest trap" {:out (pr-str out)})) (vec (butlast (str/split out #"\n" -1))))))
(defn run-safe [ls]
  (try (run ls)
       (catch Throwable e
         (if (= 1 (count ls))
           [(str "TRAP " (subs (str (ex-message e)) 0 (min 200 (count (str (ex-message e))))))]
           (vec (mapcat #(run-safe [%]) ls))))))
(spit (get env "OUT") "")
(loop [i from]
  (when (< i to)
    (let [[batch n] (loop [j i size 0 acc []]
                      (if (and (< j to) (or (empty? acc) (<= (+ size (count (nth lines j)) 1) batch-bytes)))
                        (recur (inc j) (+ size (count (nth lines j)) 1) (conj acc (nth lines j)))
                        [acc j]))
          t (System/currentTimeMillis)
          answers (run-safe batch)]
      (spit (get env "OUT") (str (str/join "\n" answers) "\n") :append true)
      (log "cases " i ".." n " done in " (- (System/currentTimeMillis) t) " ms")
      (recur n))))
(log "finished")
(System/exit 0)
