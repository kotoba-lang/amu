(ns kotoba.compiler.storage-wasm-aot-qualification-test
  "Binds storage-v1 :wasm-aot to a live in-component KV.

  Empty get stays missing. put/get/conflict/delete is mask 63 — always-missing
  cannot set the written/found/conflict/deleted bits. This is not ADR 0071's
  HTTP endpoint and not a filesystem."
  (:require [clojure.edn :as edn]
            [clojure.java.io :as io]
            [clojure.java.shell :as shell]
            [clojure.string :as str]
            [clojure.test :refer [deftest is]]
            [kotoba.component.composition :as composition]
            [kotoba.wasm.tools :as wasm-tools])
  (:import [java.nio.file Files]
           [java.nio.file.attribute FileAttribute]))

(def ^:private wasmtime-binary
  (let [pinned (io/file ".tools" "wasmtime" "wasmtime")]
    (if (.canExecute pinned) (.getPath pinned) "wasmtime")))

(defn- wat-data [bytes]
  (apply str (map #(format "\\%02x" (bit-and (int %) 0xff)) bytes)))

(defn- ref-ify [descriptor]
  (let [schemas (atom {})]
    (letfn [(walk [d]
              (cond
                (and (vector? d) (= :record (first d)))
                (let [[_ name fields] d
                      walked (mapv (fn [[f t]] [f (walk t)]) fields)
                      rec [:record name walked]]
                  (swap! schemas assoc name rec)
                  [:ref name])
                (and (vector? d) (= :variant (first d)))
                (let [[_ name cases] d
                      walked (mapv (fn [[tag p]] [tag (walk p)]) cases)
                      var [:variant name walked]]
                  (swap! schemas assoc name var)
                  [:ref name])
                (and (vector? d) (#{:set :list :option} (first d)))
                (into [(first d)] (map walk (rest d)))
                :else d))]
      (let [root (walk descriptor)]
        {:descriptor root :schemas @schemas}))))

(defn- storage-v1-descriptors []
  (let [kit (edn/read-string
             (slurp (io/resource "kotoba/lang/capability-kits/storage-v1.edn")))
        req (ref-ify (:request kit))
        res (ref-ify (:result kit))]
    {:request (:descriptor req)
     :result (:descriptor res)
     :schemas (merge (:schemas req) (:schemas res))}))

(defn- storage-wit []
  (str
   "package kotoba:application@1.0.0;\n\n"
   "interface types {\n"
   "  record kotoba-storage-get { key: string, }\n"
   "  record kotoba-storage-put {\n"
   "    key: string, value: string, expected-version: option<s64>,\n"
   "  }\n"
   "  record kotoba-storage-delete {\n"
   "    key: string, expected-version: option<s64>,\n"
   "  }\n"
   "  variant kotoba-storage-request {\n"
   "    get(kotoba-storage-get), put(kotoba-storage-put), delete(kotoba-storage-delete),\n"
   "  }\n"
   "  record kotoba-storage-entry { key: string, value: string, version: s64, }\n"
   "  record kotoba-storage-conflict { key: string, current-version: option<s64>, }\n"
   "  record kotoba-storage-error { code: string, message: string, retryable: bool, }\n"
   "  variant kotoba-storage-result {\n"
   "    found(kotoba-storage-entry), missing(bool), written(kotoba-storage-entry),\n"
   "    deleted(bool), conflict(kotoba-storage-conflict), error(kotoba-storage-error),\n"
   "  }\n"
   "}\n\n"
   "interface storage {\n"
   "  use types.{kotoba-storage-request, kotoba-storage-result};\n"
   "  transact: func(request: kotoba-storage-request) -> kotoba-storage-result;\n"
   "}\n\n"
   "world driver { import storage; export run: func() -> s64; }\n"))

(defn- storage-kv-vector-driver-wat []
  (let [mod "cm32p2|kotoba:application/storage@1"
        key-bytes (vec (.getBytes "k" "UTF-8"))
        val-bytes (vec (.getBytes "v" "UTF-8"))
        key-ptr 8
        val-ptr 16
        rets [64 128 192 256 320 384]
        transact-get
        (fn [ret]
          (str
           "    i32.const 0\n"
           "    i32.const " key-ptr " i32.const " (count key-bytes) "\n"
           "    i32.const 0 i64.const 0 i32.const 0 i64.const 0\n"
           "    i32.const " ret " call $transact\n"))
        transact-put
        (fn [ret expected-disc expected-val]
          (str
           "    i32.const 1\n"
           "    i32.const " key-ptr " i32.const " (count key-bytes) "\n"
           "    i32.const " val-ptr " i64.const " (count val-bytes) "\n"
           "    i32.const " expected-disc " i64.const " expected-val "\n"
           "    i32.const " ret " call $transact\n"))
        transact-delete
        (fn [ret]
          (str
           "    i32.const 2\n"
           "    i32.const " key-ptr " i32.const " (count key-bytes) "\n"
           "    i32.const 0 i64.const 0 i32.const 0 i64.const 0\n"
           "    i32.const " ret " call $transact\n"))]
    (str
     "(module\n"
     "  (import \"" mod "\" \"transact\""
     " (func $transact (param i32 i32 i32 i32 i64 i32 i64 i32)))\n"
     "  (memory (export \"cm32p2_memory\") 1 1)\n"
     "  (func (export \"cm32p2_realloc\")\n"
     "    (param $old i32) (param $old-size i32) (param $align i32) (param $new-size i32)\n"
     "    (result i32)\n"
     "    local.get $old i32.eqz if (result i32) i32.const 512 else local.get $old end)\n"
     "  (func (export \"cm32p2||run\") (result i64)\n"
     "    (local $d0 i32) (local $d1 i32) (local $d2 i32)"
     " (local $d3 i32) (local $d4 i32) (local $d5 i32)"
     " (local $ver i64) (local $mask i32)\n"
     (transact-get (nth rets 0))
     "    i32.const " (nth rets 0) " i32.load8_u offset=0 local.set $d0\n"
     (transact-put (nth rets 1) 0 0)
     "    i32.const " (nth rets 1) " i32.load8_u offset=0 local.set $d1\n"
     (transact-get (nth rets 2))
     "    i32.const " (nth rets 2) " i32.load8_u offset=0 local.set $d2\n"
     "    i32.const " (nth rets 2) " i64.load offset=24 local.set $ver\n"
     (transact-put (nth rets 3) 1 99)
     "    i32.const " (nth rets 3) " i32.load8_u offset=0 local.set $d3\n"
     (transact-delete (nth rets 4))
     "    i32.const " (nth rets 4) " i32.load8_u offset=0 local.set $d4\n"
     (transact-get (nth rets 5))
     "    i32.const " (nth rets 5) " i32.load8_u offset=0 local.set $d5\n"
     "    i32.const 0 local.set $mask\n"
     "    local.get $d0 i32.const 1 i32.eq if local.get $mask i32.const 1 i32.or local.set $mask end\n"
     "    local.get $d1 i32.const 2 i32.eq if local.get $mask i32.const 2 i32.or local.set $mask end\n"
     "    local.get $d2 i32.eqz local.get $ver i64.const 1 i64.eq i32.and\n"
     "    if local.get $mask i32.const 4 i32.or local.set $mask end\n"
     "    local.get $d3 i32.const 4 i32.eq if local.get $mask i32.const 8 i32.or local.set $mask end\n"
     "    local.get $d4 i32.const 3 i32.eq if local.get $mask i32.const 16 i32.or local.set $mask end\n"
     "    local.get $d5 i32.const 1 i32.eq if local.get $mask i32.const 32 i32.or local.set $mask end\n"
     "    local.get $mask i64.extend_i32_u)\n"
     "  (func (export \"cm32p2||run_post\") (param i64))\n"
     "  (func (export \"cm32p2_initialize\"))\n"
     "  (data (i32.const " key-ptr ") \"" (wat-data key-bytes) "\")\n"
     "  (data (i32.const " val-ptr ") \"" (wat-data val-bytes) "\")\n"
     ")\n")))

(defn- package-driver []
  (let [dir (Files/createTempDirectory "amu-storage-wasm-aot-driver-"
                                       (make-array FileAttribute 0))
        world (.resolve dir "driver.wit")
        core (.resolve dir "driver.wasm")
        embedded (.resolve dir "embedded.wasm")
        component (.resolve dir "driver.component.wasm")]
    (try
      (Files/writeString world (storage-wit) (make-array java.nio.file.OpenOption 0))
      (Files/write core (wasm-tools/parse-wat (storage-kv-vector-driver-wat))
                   (make-array java.nio.file.OpenOption 0))
      (wasm-tools/run-command! ["wasm-tools" "component" "embed" (str world) (str core)
                                "--encoding" "utf8" "-o" (str embedded)])
      (wasm-tools/run-command! ["wasm-tools" "component" "new" (str embedded)
                                "--reject-legacy-names" "-o" (str component)])
      {:format :wasm-component/v1 :imports [:storage/transact]
       :bytes (Files/readAllBytes component)}
      (finally
        (doseq [p [component embedded core world]] (Files/deleteIfExists p))
        (Files/deleteIfExists dir)))))

(deftest storage-kit-flag-is-bound-to-this-evidence
  (let [kit (edn/read-string
             (slurp (io/resource "kotoba/lang/capability-kits/storage-v1.edn")))]
    (is (= :implemented (get-in kit [:qualification :wasm-aot])))
    (is (= :pending (get-in kit [:qualification :wasm32-kotoba-v1])))
    (is (= :pending (get-in kit [:qualification :native-aot])))
    (is (= :pending (get-in kit [:qualification :jit])))))

(deftest wasmtime-storage-kit-kv-vector-is-mask-63
  (let [d (storage-v1-descriptors)
        provider (composition/package-storage-provider
                  (:request d) (:result d) (:schemas d) 4)
        closed (composition/compose-closed (package-driver) [provider])
        path (Files/createTempFile "amu-storage-wasm-aot-" ".wasm"
                                   (make-array FileAttribute 0))]
    (try
      (Files/write path ^bytes (:bytes closed)
                   (make-array java.nio.file.OpenOption 0))
      (let [run (shell/sh wasmtime-binary "run" "--invoke" "run()" (str path))]
        (is (zero? (:exit run)) (str "wasmtime err: " (:err run)))
        (is (= "63" (str/trim (:out run)))))
      (finally
        (Files/deleteIfExists path)))))
