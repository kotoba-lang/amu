(ns kotoba.compiler.lang-native-conformance
  "T1.4: pure-native-v1 pilot — host ISA kexe execute for pure i64/string subset.

  Requires tender-native (test / :native-run alias). Soft-skips if unavailable."
  (:require [clojure.edn :as edn]
            [clojure.java.io :as io]
            [clojure.string :as str]
            [kotoba.compiler.core :as compiler]
            [kotoba.compiler.atomic-output :as atomic-output]
            [kotoba.artifact.runtime-identity :as runtime-identity]
            [kotoba.verifier.signing :as signing]))

(def manifest-resource "kotoba/lang-conformance/native-pilot-manifest.edn")
(def pilot-root "kotoba/lang-conformance/")

(defn host-native-target
  []
  (if (contains? #{"aarch64" "arm64"}
                 (str/lower-case (System/getProperty "os.arch")))
    :aarch64-kotoba-v1
    :x86_64-kotoba-v1))

(defn tender-native-available?
  []
  (try
    (requiring-resolve 'kototama.native.executor/execute)
    true
    (catch Exception _ false)))

(defn load-manifest
  ([]
   (if-let [url (io/resource manifest-resource)]
     (edn/read-string (slurp url))
     (throw (ex-info "native pilot manifest missing" {:resource manifest-resource}))))
  ([edn-or-map]
   (if (map? edn-or-map) edn-or-map (edn/read-string edn-or-map))))

(defn- resolve-source [entry]
  (let [rel (str pilot-root entry)]
    (if-let [url (io/resource rel)]
      (slurp url)
      (let [f (io/file entry)]
        (when (.isFile f) (slurp f))))))

(defonce ^:private measured-runtime
  (delay
    (when (tender-native-available?)
      (let [measure (requiring-resolve 'kototama.native.executor/measure-runtime)
            {:keys [runtime loader-bytes]} (measure)
            loader (doto (java.io.File/createTempFile "kotoba-native-pilot-" "")
                     (.deleteOnExit))]
        (atomic-output/write-bytes! (.getPath loader) loader-bytes {:executable? true})
        {:runtime runtime :loader-path (.getPath loader)}))))

(defn run-native-case
  "Compile + sign + kexe-execute one pure-native case."
  [case]
  (let [id (:id case)
        expect (get-in case [:expect :kotoba])
        source (resolve-source (:entry case))
        target (host-native-target)]
    (cond
      (not (tender-native-available?))
      {:id id :ok? false :status :skipped :reason :tender-native-missing}

      (nil? source)
      {:id id :ok? false :status :missing-source :entry (:entry case)}

      :else
      (try
        (let [execute (requiring-resolve 'kototama.native.executor/execute)
              artifact (:artifact (compiler/compile-source source target {:allow #{}}))
              key (signing/generate-keypair)
              envelope (signing/sign artifact key {:not-before 1000 :expires 2000})
              base-trust {:format :kotoba.trust/v1
                          :trusted-signers #{(:signer key)}
                          :revoked-signers #{}
                          :revoked-artifacts #{}}
              {:keys [runtime loader-path]} @measured-runtime
              trust (assoc base-trust :trusted-runtime-sha256
                           #{(runtime-identity/identity-sha256 runtime)})
              result (execute envelope trust {:allow #{}}
                              {:args (vec (or (:args case) []))}
                              {:now 1500
                               :entry (symbol (or (:function case) "main"))
                               :runtime runtime
                               :loader-path loader-path})
              got (get-in result [:evidence :result])
              status (get-in result [:evidence :status])
              ok? (and (= :ok status) (= expect got))]
          {:id id
           :ok? ok?
           :status (if ok? :passed :failed)
           :target target
           :expect expect
           :result got
           :evidence-status status})
        (catch Exception e
          {:id id
           :ok? false
           :status :error
           :error (.getMessage e)
           :ex-data (ex-data e)})))))

(defn run-suite
  ([] (run-suite (load-manifest)))
  ([manifest]
   (let [cases (:cases manifest)
         results (mapv run-native-case cases)
         skipped (filterv #(= :skipped (:status %)) results)
         failed (filterv #(and (not (:ok? %))
                               (not= :skipped (:status %)))
                         results)
         passed (count (filter :ok? results))]
     {:ok? (and (empty? failed)
                (or (seq skipped) ; skip-all is soft ok when dep missing
                    (= passed (count cases))))
      :skipped? (boolean (seq skipped))
      :total (count results)
      :passed passed
      :failed-count (count failed)
      :failed failed
      :skipped skipped
      :results results
      :wbs "T1.4"
      :target (when (tender-native-available?) (host-native-target))})))

(defn -main
  "CLI: clojure -M:test -m kotoba.compiler.lang-native-conformance
   (needs tender-native on classpath — use :test or :native-run alias)"
  [& _]
  (let [report (run-suite)]
    (println "lang-conformance T1.4 pure-native:"
             (:passed report) "/" (:total report)
             (if (:skipped? report) "(skipped tender-native)" "passed")
             "target" (:target report))
    (doseq [f (:failed report)]
      (println " FAIL" (pr-str f)))
    (System/exit (if (:ok? report) 0 1))))
