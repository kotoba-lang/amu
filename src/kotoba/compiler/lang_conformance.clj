(ns kotoba.compiler.lang-conformance
  "T1.3: dual-backend runner for language pure-product conformance.

  Required backends (from kotoba-lang T1.2 matrix): `:kir` + `:wasm32-kotoba-v1`.
  Pilot fixtures ship under `resources/kotoba/lang-conformance/`. Full matrix
  expansion is progressive as compiler admission covers more fixtures."
  (:require [clojure.edn :as edn]
            [clojure.java.io :as io]
            [clojure.java.shell :as shell]
            [clojure.string :as str]
            [kotoba.artifact.core :as artifact]
            [kotoba.compiler.core :as compiler]
            [kotoba.kir :as ir]
            [clojure.pprint]
            [clojure.walk])
  (:import [java.security MessageDigest]
           [java.nio.charset StandardCharsets]))

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


;; --- T1.5 golden digests -------------------------------------------------

(def golden-resource "kotoba/lang-conformance/pilot-golden.edn")

(defn- bytes-sha256-hex
  "SHA-256 of raw bytes as lowercase hex (wasm artifact fingerprint)."
  [^bytes b]
  (let [digest (.digest (MessageDigest/getInstance "SHA-256") b)]
    (apply str (map #(format "%02x" (bit-and (int %) 0xff)) digest))))

(defn- gensym-like?
  "True for compiler gensyms like foo__12345 (digits after __)."
  [x]
  (and (symbol? x)
       (nil? (namespace x))
       (boolean (re-matches #".+__\d+" (name x)))))

(defn- normalize-gensyms
  "Rewrite gensym-like symbols to stable foo__G0, foo__G1 … by first-seen order
  so KIR digests are deterministic across process runs."
  [form]
  (let [table (atom {})
        counter (atom 0)
        ren (fn [sym]
              (or (get @table sym)
                  (let [n (name sym)
                        base (second (re-matches #"(.+)__\d+" n))
                        fresh (symbol (str base "__G" @counter))]
                    (swap! counter inc)
                    (swap! table assoc sym fresh)
                    fresh)))]
    (clojure.walk/prewalk
     (fn [x]
       (if (gensym-like? x) (ren x) x))
     form)))

(defn- kir-digest-body
  "Stable KIR projection for hashing — gensym-normalized + select-keys;
  artifact/sha256 canonicalizes map key order."
  [kir]
  (-> kir
      (select-keys [:format :signature :functions :exports :effects
                    :schemas :schema-identities :blocks :entry :oracle-value])
      normalize-gensyms))

(defn digest-case
  "Compile case once; return {:id :kir-sha256 :wasm-sha256 :expect :result}."
  [case]
  (let [source (resolve-source (:entry case))
        expect (get-in case [:expect :kotoba])]
    (when-not source
      (throw (ex-info "missing source for golden digest" {:id (:id case)
                                                          :entry (:entry case)})))
    (let [compiled (compiler/compile-source source :wasm32-kotoba-v1)
          kir (:kir compiled)
          bytes (:bytes compiled)
          result (ir/execute kir (symbolize-function (:function case))
                             (vec (or (:args case) [])))]
      {:id (:id case)
       :entry (:entry case)
       :expect expect
       :result result
       :result-ok? (= expect result)
       :kir-sha256 (artifact/sha256 (kir-digest-body kir))
       :wasm-sha256 (bytes-sha256-hex bytes)
       :wasm-byte-count (alength ^bytes bytes)})))

(defn collect-goldens
  "Digest all pure-product pilot cases."
  ([] (collect-goldens (load-manifest)))
  ([manifest]
   (mapv digest-case (pure-product-cases manifest))))

(defn golden-document
  "EDN map written to pilot-golden.edn."
  [rows]
  {:kotoba.lang.conformance.golden/version 1
   :kotoba.lang.conformance.golden/wbs "T1.5"
   :kotoba.lang.conformance.golden/note
   "KIR + wasm32-kotoba-v1 digests for T1.3 pure-product pilot. CI fails on drift."
   :algorithm {:kir "artifact.core/sha256 of select-keys KIR body"
               :wasm "SHA-256 hex of raw wasm bytes"}
   :cases (mapv #(select-keys % [:id :entry :expect :kir-sha256 :wasm-sha256
                                 :wasm-byte-count])
                rows)})

(defn load-goldens
  ([]
   (if-let [url (io/resource golden-resource)]
     (edn/read-string (slurp url))
     (throw (ex-info "pilot golden missing" {:resource golden-resource}))))
  ([edn-or-map]
   (if (map? edn-or-map) edn-or-map (edn/read-string edn-or-map))))

(defn check-goldens
  "Compare live digests to golden file. Returns {:ok? :mismatches :missing :extra}."
  ([] (check-goldens (load-goldens) (collect-goldens)))
  ([golden live-rows]
   (let [g-by-id (into {} (map (juxt :id identity) (:cases golden)))
         l-by-id (into {} (map (juxt :id identity) live-rows))
         ids (set (concat (keys g-by-id) (keys l-by-id)))
         mismatches (vec
                     (keep
                      (fn [id]
                        (let [g (g-by-id id)
                              l (l-by-id id)]
                          (cond
                            (nil? g) {:id id :type :extra-live}
                            (nil? l) {:id id :type :missing-live}
                            (not (:result-ok? l))
                            {:id id :type :result-mismatch
                             :expect (:expect g) :got (:result l)}
                            (or (not= (:kir-sha256 g) (:kir-sha256 l))
                                (not= (:wasm-sha256 g) (:wasm-sha256 l)))
                            {:id id :type :digest-drift
                             :golden (select-keys g [:kir-sha256 :wasm-sha256])
                             :live (select-keys l [:kir-sha256 :wasm-sha256])}
                            :else nil)))
                      (sort ids)))]
     {:ok? (empty? mismatches)
      :case-count (count live-rows)
      :mismatches mismatches
      :wbs "T1.5"})))

(defn write-goldens!
  "Write resources/…/pilot-golden.edn from live digests. Returns path."
  ([]
   (let [rows (collect-goldens)
         doc (golden-document rows)
         ;; Prefer repo resources path when running from compiler root.
         f (io/file "resources/kotoba/lang-conformance/pilot-golden.edn")]
     (io/make-parents f)
     (spit f (with-out-str (clojure.pprint/pprint doc)))
     (.getPath f))))

(defn -main
  "CLI: clojure -M:conformance
         clojure -M:conformance --write-golden
         clojure -M:conformance --check-golden"
  [& args]
  (cond
    (some #{"--write-golden"} args)
    (let [path (write-goldens!)]
      (println "wrote" path)
      (System/exit 0))

    (some #{"--check-golden"} args)
    (let [report (check-goldens)]
      (println "lang-conformance T1.5 golden:"
               (:case-count report) "cases"
               (if (:ok? report) "ok" "DRIFT"))
      (doseq [m (:mismatches report)]
        (println " FAIL" (pr-str m)))
      (System/exit (if (:ok? report) 0 1)))

    :else
    (let [report (run-suite)]
      (println "lang-conformance T1.3 dual-backend:"
               (:passed report) "/" (:total report) "passed")
      (doseq [f (:failed report)]
        (println " FAIL" (:id f) (:status f) (or (:error f) "")))
      (System/exit (if (:ok? report) 0 1)))))
