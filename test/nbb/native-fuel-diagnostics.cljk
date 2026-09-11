(ns test.nbb.native-fuel-diagnostics
  "The JDK-free native driver, on the two seams the JVM route fixed the same
  day (amu-h6, amu-h10):

  - `--fuel N` together with a policy `{:budgets {:fuel M}}`, N != M, is
    refused as `{:phase :usage :reason :fuel-declared-twice :flag N :policy M}`
    instead of the flag silently winning; N = M compiles and seals N.
  - A refusal raised while compiling a linked project names the module and
    line that wrote the form (`:source-module`, `:span {:line}`, and the
    module's file when the graph came from `--source-path`), not the root
    file at a position inside the linker's synthetic unit.

  Runs `kotoba.compiler.nbb.cli/run!` in-process the way `x86_64_cli.cljs`
  does, once through `support/invoke` for the envelope and once bare for the
  ex-data, so the assertions do not depend on what the envelope redacts."
  (:require [cljs.reader :as reader]
            [kotoba.lang.text :as str]
            [kotoba.compiler.nbb.cli :as native-cli]
            [kotoba.compiler.nbb.cli-support :as support]
            [kotoba.compiler.nbb.native-package :as native-package]
            [kotoba.native.x86-64 :as x86-64]
            ["node:fs" :as fs]
            ["node:os" :as os]
            ["node:path" :as path]))

(def ^:private failures (atom 0))

(defn- check! [label ok? detail]
  (if ok?
    (println (str "ok   " label))
    (do (swap! failures inc)
        (println (str "FAIL " label " -- " (pr-str detail))))))

(defn- run! [args]
  (native-cli/run! (vec args) :x86_64-kotoba-v1 x86-64/emit-program
                   native-package/package nil))

(defn- invoke [& args] (support/invoke run! args))

(defn- thrown-data [& args]
  (try (run! args) nil
       (catch :default error (ex-data error))))

(defn- tmpdir [] (.mkdtempSync fs (.join path (.tmpdir os) "amu-nbb-fuel-diag-")))
(defn- spit! [dir name text]
  (let [file (.join path dir name)]
    (.mkdirSync fs (.dirname path file) #js {:recursive true})
    (.writeFileSync fs file text "utf8")
    file))

;; ---------------------------------------------------------------------------
;; amu-h6

(let [dir (tmpdir)
      source (spit! dir "main.kotoba" "(defn main [] :i64 42)")
      disagreeing (spit! dir "p4096.edn" "{:budgets {:fuel 4096}}")
      agreeing (spit! dir "p8192.edn" "{:budgets {:fuel 8192}}")
      out (.join path dir "main.kexe")]
  (let [data (thrown-data "compile" source "--target" "x86_64" "--output" out
                          "--fuel" "8192" "--policy" disagreeing)]
    (check! "h6: --fuel 8192 with policy 4096 is refused as :fuel-declared-twice"
            (and (= :usage (:phase data))
                 (= :fuel-declared-twice (:reason data))
                 (= "8192" (str (:flag data)))
                 (= "4096" (str (:policy data))))
            data))
  (let [{:keys [status stderr]} (invoke "compile" source "--target" "x86_64" "--output" out
                                        "--fuel" "8192" "--policy" disagreeing)
        report (when (seq stderr) (reader/read-string stderr))]
    (check! "h6: the envelope exits 64 with :error :usage"
            (and (= 64 status) (= :usage (:error report)))
            {:status status :report report}))
  (let [{:keys [status stderr]} (invoke "compile" source "--target" "x86_64" "--output" out
                                        "--fuel" "8192" "--policy" agreeing)
        artifact (when (zero? status) (reader/read-string (.readFileSync fs out "utf8")))]
    (check! "h6: --fuel 8192 with policy 8192 compiles and seals 8192"
            (and (zero? status) (= "8192" (str (get-in artifact [:limits :fuel]))))
            {:status status :stderr stderr :limits (:limits artifact)})))

;; ---------------------------------------------------------------------------
;; amu-h10

(let [dir (tmpdir)
      root (spit! dir "main.kotoba"
                  (str "(ns example.a (:require [example.b :as b]) (:export [main]))\n"
                       "(defn main [] :i64 (b/wide 1 2 3 4 5 6))\n"))
      _ (spit! dir "src/example/b.kotoba"
               (str "(ns example.b (:export [wide]))\n"
                    "(defn- helper [x :i64] :i64 (+ x 1))\n"
                    "(defn wide [a :i64 b :i64 c :i64 d :i64 e :i64 f :i64] :i64\n"
                    "  (+ a (+ b (+ c (+ d (+ e f))))))\n"))
      src (.join path dir "src")
      out (.join path dir "main.kexe")
      args ["compile" root "--source-path" src "--target" "x86_64" "--output" out "--unpinned"]
      data (apply thrown-data args)]
  (check! "h10: the refusal itself is unchanged"
          (= :kotoba.error/max-parameters (:kotoba.error/code data)) data)
  (check! "h10: attributed to example.b at its defn line, no column"
          (and (= 'example.b (:source-module data))
               (= {:line 3} (:span data)))
          (select-keys data [:source-module :span]))
  (check! "h10: the module's file is named when the graph came from --source-path"
          (and (string? (:source-file data)) (str/ends-with? (:source-file data) "b.kotoba"))
          (:source-file data))
  (let [{:keys [status stderr]} (apply invoke args)
        report (when (seq stderr) (reader/read-string stderr))
        diagnostic (:diagnostic report)]
    (check! "h10: the envelope names b.kotoba:3"
            (and (= 65 status)
                 (= "b.kotoba" (:source diagnostic))
                 (= {:line 3} (:span diagnostic)))
            {:status status :diagnostic diagnostic})))

(when (pos? @failures)
  (println (str @failures " failure(s)"))
  (.exit js/process 1))
(println "native-fuel-diagnostics: all checks passed")
