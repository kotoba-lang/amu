;; BOOTSTRAP REFERENCE (JVM + KIR interpreter), dev feedback only. Runs a guest module's text->text entry like
;; interp-run.cljs, on the JVM-compiled frontend (build-native.sh's work dir), with the project admission ceilings raised
;; (the guest links the whole frontend closure, which the product limits refuse) and the input cut into batches of at most
;; 60000 bytes (a string value is bounded at 65536). The lowered program is cached by the CID of the linked source.
;; env: GUEST (module path), ENTRY (export), KROOTS (colon-separated source roots); stdin = input text, stdout = answer.
(require 'kotoba.sema 'kotoba.kir 'kotoba.compiler.project 'kotoba.compiler.project-files)
(require '[clojure.string :as str] 'clojure.edn)
(doseq [[v n] [['kotoba.compiler.project/max-project-exports 1000000]
               ['kotoba.compiler.project/max-project-functions 1000000]
               ['kotoba.compiler.project/max-definition-closure-count 1000000]
               ['kotoba.compiler.project/max-project-modules 100000]
               ['kotoba.compiler.project/max-project-source-bytes (* 1024 1024 1024)]
               ['kotoba.compiler.project/max-project-dependency-edges 100000]
               ['kotoba.compiler.project/max-project-expression-nodes 100000000]]]
  (when-let [r (resolve v)] (alter-var-root r (constantly n))))
(defn sha256 [^String s]
  (let [d (.digest (java.security.MessageDigest/getInstance "SHA-256") (.getBytes s "UTF-8"))]
    (apply str (map #(format "%02x" (bit-and % 0xff)) d))))
(defn typed-cap-call [id _ _ request]
  (case (long id)
    3 (sha256 request)
    (throw (ex-info "unhandled capability" {:id id}))))
(let [t0 (System/currentTimeMillis)
      roots (vec (str/split (System/getenv "KROOTS") #":"))
      graph (kotoba.compiler.project-files/load-closed-graph (System/getenv "GUEST") roots)
      linked (kotoba.compiler.project/link-source (:sources graph) (:root graph))
      _ (binding [*out* *err*] (println "linked" (count (:source linked)) "bytes in" (- (System/currentTimeMillis) t0) "ms"))
      key (sha256 (:source linked))
      cache (java.io.File. (str (or (System/getenv "ABORT_CACHE") "/tmp") "/lowered-" key ".edn"))
      lowered (if (.exists cache)
                (clojure.edn/read-string {:readers {}} (slurp cache))
                (let [l (kotoba.kir/lower (kotoba.sema/analyze (:source linked) {:admit-linked-synthetics? true}))]
                  (try (binding [*print-length* nil *print-level* nil *print-namespace-maps* false] (spit cache (pr-str l)))
                       (catch Throwable e (binding [*out* *err*] (println "cache write failed" (.getMessage e)))))
                  l))
      _ (binding [*out* *err*] (println "lowered in" (- (System/currentTimeMillis) t0) "ms"))
      lines (vec (remove str/blank? (str/split-lines (slurp *in*))))
      batches (loop [ls lines cur [] sz 0 out []]
                (cond (empty? ls) (if (seq cur) (conj out cur) out)
                      (and (seq cur) (> (+ sz (count (.getBytes ^String (first ls) "UTF-8")) 1) 60000)) (recur ls [] 0 (conj out cur))
                      :else (recur (rest ls) (conj cur (first ls)) (+ sz (count (.getBytes ^String (first ls) "UTF-8")) 1) out)))]
  (doseq [[i b] (map-indexed vector batches)]
    (let [text (str (str/join "\n" b) "\n")
          out (kotoba.kir/execute lowered (symbol (System/getenv "ENTRY")) [text]
                                  {:typed-cap-call typed-cap-call :fuel 100000000000000 :frames 1000000 :cells 1000000000 :bytes 2000000000})]
      (binding [*out* *err*] (println "batch" i "of" (count batches) "done at" (- (System/currentTimeMillis) t0) "ms"))
      (when (map? out) (throw (ex-info "guest trap" {:out (pr-str out)})))
      (print out) (flush))))
