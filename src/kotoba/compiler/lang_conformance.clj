(ns kotoba.compiler.lang-conformance
  "T1.3: dual-backend runner for language pure-product conformance.

  Required backends (from kotoba-lang T1.2 matrix): `:kir` + `:wasm32-kotoba-v1`.
  Pilot fixtures ship under `resources/kotoba/lang-conformance/`. Full matrix
  expansion is progressive as compiler admission covers more fixtures."
  (:require [clojure.edn :as edn]
            [clojure.java.io :as io]
            [clojure.java.shell :as shell]
            [clojure.string :as str]
            [kotoba.compiler.core :as compiler]
            [kotoba.kir :as ir]))

(def pilot-manifest-resource "kotoba/lang-conformance/pilot-manifest.edn")
(def pilot-root-resource "kotoba/lang-conformance/")
(def pure-product-required #{:kir :wasm32-kotoba-v1})

(defn load-manifest
  "Load pilot or caller-supplied manifest EDN text/map."
  ([]
   (if-let [url (io/resource pilot-manifest-resource)]
     (load-manifest (slurp url))
     (throw (ex-info "pilot conformance manifest missing"
                     {:resource pilot-manifest-resource}))))
  ([edn-or-map]
   (if (map? edn-or-map)
     edn-or-map
     (edn/read-string edn-or-map))))

(defn pure-product-cases
  [manifest]
  (filterv #(and (= :run (:kind %))
                 (or (= :pure-product-run (:class %))
                     (= pure-product-required (:required-backends %))))
           (:cases manifest)))

(defn- resolve-source
  "Load case source from classpath under pilot root, or absolute path."
  [entry]
  (let [rel (str pilot-root-resource entry)]
    (if-let [url (io/resource rel)]
      (slurp url)
      (let [f (io/file entry)]
        (when (.isFile f)
          (slurp f))))))

(defn- symbolize-function [function]
  (cond
    (symbol? function) function
    (string? function) (symbol function)
    (keyword? function) (symbol (name function))
    :else 'main))

(defn run-kir
  "Compile source → wasm32 path (produces KIR) and execute on KIR oracle."
  [source function args]
  (let [compiled (compiler/compile-source source :wasm32-kotoba-v1)
        fn-sym (symbolize-function function)
        result (ir/execute (:kir compiled) fn-sym (vec (or args [])))]
    {:backend :kir
     :ok? true
     :result result
     :wasm-bytes (:bytes compiled)}))

(defn- project-root
  "Best-effort compiler repo root (dir containing runtime/browser-host.mjs)."
  []
  (loop [dir (.getAbsoluteFile (io/file "."))]
    (cond
      (.isFile (io/file dir "runtime/browser-host.mjs")) dir
      (nil? (.getParentFile dir)) (io/file ".")
      :else (recur (.getParentFile dir)))))

(defn run-wasm32
  "Compile to wasm32-kotoba-v1 and execute `main` via Node browser-host runtime.
  Returns {:backend :wasm32-kotoba-v1 :ok? bool :result long-or-nil :error ...}."
  [source]
  (let [compiled (compiler/compile-source source :wasm32-kotoba-v1)
        bytes (:bytes compiled)]
    (when-not (bytes? bytes)
      (throw (ex-info "wasm compile produced no bytes" {:phase :lang-conformance})))
    (let [encoded (.encodeToString (java.util.Base64/getEncoder) ^bytes bytes)
          root (project-root)
          ;; Same pattern as typed_value_conformance_test (relative import).
          probe (str "import('./runtime/browser-host.mjs').then(async m=>{"
                     "const h=await m.instantiateKotoba(Buffer.from(process.argv[1],'base64'));"
                     "const value=h.instance.exports.main();"
                     "if(typeof value!=='bigint' && typeof value!=='number')process.exit(2);"
                     "console.log(String(value))})")
          res (shell/sh "node" "--input-type=module" "-e" probe encoded
                        :dir (.getAbsolutePath root))]
      (if (zero? (:exit res))
        (let [out (str/trim (:out res))
              parsed (try (Long/parseLong out) (catch Exception _ out))]
          {:backend :wasm32-kotoba-v1
           :ok? true
           :result parsed
           :raw-out out})
        {:backend :wasm32-kotoba-v1
         :ok? false
         :error (str "wasm exit " (:exit res) ": " (:err res) (:out res))}))))

(defn run-case
  "Run one pure-product case on required backends. Returns result map."
  [case]
  (let [id (:id case)
        entry (:entry case)
        expect (get-in case [:expect :kotoba])
        source (resolve-source entry)
        required (or (:required-backends case) pure-product-required)]
    (if-not source
      {:id id :ok? false :status :missing-source :entry entry}
      (try
        (let [kir (when (contains? required :kir)
                    (run-kir source (:function case) (:args case)))
              wasm (when (contains? required :wasm32-kotoba-v1)
                     (run-wasm32 source))
              kir-ok? (or (nil? kir) (and (:ok? kir) (= expect (:result kir))))
              wasm-ok? (or (nil? wasm) (and (:ok? wasm) (= expect (:result wasm))))
              ok? (and kir-ok? wasm-ok?)]
          {:id id
           :ok? ok?
           :status (if ok? :passed :failed)
           :expect expect
           :kir kir
           :wasm32-kotoba-v1 wasm
           :kir-ok? kir-ok?
           :wasm-ok? wasm-ok?})
        (catch Exception e
          {:id id
           :ok? false
           :status :error
           :error (.getMessage e)
           :ex-data (ex-data e)})))))

(defn run-suite
  "Run all pure-product cases in manifest. Returns aggregate report."
  ([] (run-suite (load-manifest)))
  ([manifest]
   (let [cases (pure-product-cases manifest)
         results (mapv run-case cases)
         passed (count (filter :ok? results))
         failed (filterv (complement :ok?) results)]
     {:ok? (empty? failed)
      :total (count results)
      :passed passed
      :failed-count (count failed)
      :failed failed
      :results results
      :required-backends pure-product-required
      :wbs "T1.3"})))

(defn -main
  "CLI: clojure -M -m kotoba.compiler.lang-conformance"
  [& _args]
  (let [report (run-suite)]
    (println "lang-conformance T1.3 dual-backend:"
             (:passed report) "/" (:total report) "passed")
    (doseq [f (:failed report)]
      (println " FAIL" (:id f) (:status f) (or (:error f) "")))
    (System/exit (if (:ok? report) 0 1))))
