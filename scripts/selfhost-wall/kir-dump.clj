;; BOOTSTRAP REFERENCE (JVM-built compiler classes, build/native-image/work): write the closed native KIR program of a
;; project-route module, the bytes a kexe's :program would hold, WITHOUT the native backend's admission.
;;
;;   GUEST=<module.cljk> OUT=<file.kir> KROOTS=<src:src:..> java -Xss1g -cp <work/classes:classpath> clojure.main kir-dump.clj
;;
;; Why: stage-0's native image has no --emit-kir, and its aarch64 admission (`ir/only-native-word-typed-features?`) refuses
;; the frontend guests (typed sets of keywords, ...) BEFORE the KIR is written, so `kir_extract.py` has nothing to cut. The
;; seed's `compile-kir` is a different backend with its own refusals; this hands it the same `ir/native-program` value the
;; native CLI would seal (cli.cljk: `program (ir/native-program kir)`, kir = `ir/lower hir`), printed with pr-str.
;; Agent FRONT, 2026-10-03 (H-F1).
(require '[clojure.string :as str]
         '[kotoba.sema :as sema] '[kotoba.kir :as kir]
         '[kotoba.compiler.project :as project] '[kotoba.compiler.project-files :as pf])
(def env (System/getenv))
;; RAISE=1: the project admission ceilings raised as abort-run-jvm.clj raises them (a guest that links the whole frontend
;; closure is over the product limits; the seed backend has its own table limits, which then decide)
(when (= "1" (get env "RAISE"))
  (doseq [[v n] [['kotoba.compiler.project/max-project-exports 1000000]
                 ['kotoba.compiler.project/max-project-functions 1000000]
                 ['kotoba.compiler.project/max-definition-closure-count 1000000]
                 ['kotoba.compiler.project/max-project-modules 100000]
                 ['kotoba.compiler.project/max-project-source-bytes (* 1024 1024 1024)]
                 ['kotoba.compiler.project/max-project-dependency-edges 100000]
                 ['kotoba.compiler.project/max-project-expression-nodes 100000000]]]
    (when-let [r (resolve v)] (alter-var-root r (constantly n)))))
(def roots (vec (str/split (get env "KROOTS") #":")))
(def t0 (System/currentTimeMillis))
(defn log [& xs] (binding [*out* *err*] (println (str "[" (- (System/currentTimeMillis) t0) " ms]") (apply str xs)) (flush)))
(def graph (pf/load-closed-graph (get env "GUEST") roots))
(log "graph loaded: " (count (:sources graph)) " modules")
(def linked (project/link-source (:sources graph) (:root graph)))
(log "linked")
(def hir (sema/analyze (:source linked) {:admit-linked-synthetics? true}))
(log "analyzed: " (count (:functions hir)) " functions")
(def lowered (kir/lower hir {:oracle-fuel 1000}))
(log "lowered: " (count (:functions lowered)) " functions, format " (:format lowered))
(def program (kir/native-program lowered))
(spit (get env "OUT") (str (pr-str program) "\n"))
(log "written " (get env "OUT") " native-word-typed-only? " (try (kir/only-native-word-typed-features? lowered) (catch Throwable e (str "n/a " (ex-message e)))))
(System/exit 0)
