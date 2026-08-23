(ns kotoba.compiler.log-wasm-aot-qualification-test
  "Binds log-v1 :wasm-aot to live wasmtime ring-buffer vectors.

  The in-component ring is the production source of truth (no stdout
  sink). Sequence advance plus oldest-drop on overflow are the
  discriminating claims — a canned append result would not drop seq 1."
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

(defn- ref-ify-record [descriptor]
  (let [schemas (atom {})]
    (letfn [(walk [d]
              (cond
                (and (vector? d) (= :record (first d)))
                (let [[_ name fields] d
                      walked (mapv (fn [[f t]] [f (walk t)]) fields)
                      rec [:record name walked]]
                  (swap! schemas assoc name rec)
                  [:ref name])
                (and (vector? d) (#{:set :list} (first d)))
                [(first d) (walk (second d))]
                :else d))]
      (let [root (walk descriptor)]
        {:descriptor root :schemas @schemas}))))

(defn- log-v1-descriptors []
  (let [kit (edn/read-string
             (slurp (io/resource "kotoba/lang/capability-kits/log-v1.edn")))
        append-req (ref-ify-record (get-in kit [:append :request]))
        append-res (ref-ify-record (get-in kit [:append :result]))
        read-req (ref-ify-record (get-in kit [:read :request]))
        read-res (ref-ify-record (get-in kit [:read :result]))]
    {:append-req (:descriptor append-req)
     :append-res (:descriptor append-res)
     :read-req (:descriptor read-req)
     :read-res (:descriptor read-res)
     :schemas (merge (:schemas append-req) (:schemas append-res)
                     (:schemas read-req) (:schemas read-res))}))

(defn- package-component [prefix wit wat imports]
  (let [dir (Files/createTempDirectory prefix (make-array FileAttribute 0))
        world (.resolve dir "driver.wit")
        core (.resolve dir "driver.wasm")
        embedded (.resolve dir "embedded.wasm")
        component (.resolve dir "driver.component.wasm")]
    (try
      (Files/writeString world wit (make-array java.nio.file.OpenOption 0))
      (Files/write core (wasm-tools/parse-wat wat)
                   (make-array java.nio.file.OpenOption 0))
      (wasm-tools/run-command! ["wasm-tools" "component" "embed" (str world) (str core)
                                "--encoding" "utf8" "-o" (str embedded)])
      (wasm-tools/run-command! ["wasm-tools" "component" "new" (str embedded)
                                "--reject-legacy-names" "-o" (str component)])
      {:format :wasm-component/v1 :imports imports
       :bytes (Files/readAllBytes component)}
      (finally
        (doseq [p [component embedded core world]] (Files/deleteIfExists p))
        (Files/deleteIfExists dir)))))

(defn- append-only-wit []
  (str
   "package kotoba:application@1.0.0;\n\n"
   "interface types {\n"
   "  record kotoba-log-field { key: string, value: string, }\n"
   "  record kotoba-log-append-request {\n"
   "    level: string, event: string, message: string,\n"
   "    fields: list<kotoba-log-field>,\n"
   "  }\n"
   "  record kotoba-log-append-result { sequence: s64, }\n"
   "}\n\n"
   "interface log {\n"
   "  use types.{kotoba-log-append-request, kotoba-log-append-result};\n"
   "  append: func(request: kotoba-log-append-request) -> kotoba-log-append-result;\n"
   "}\n\n"
   "world driver { import log; export run: func() -> s64; }\n"))

(defn- append-sequence-wat []
  (let [mod "cm32p2|kotoba:application/log@1"
        level-bytes (vec (.getBytes "info" "UTF-8"))
        event-bytes (vec (.getBytes "boot" "UTF-8"))
        msg1-bytes (vec (.getBytes "one" "UTF-8"))
        msg2-bytes (vec (.getBytes "two" "UTF-8"))
        level-ptr 8
        event-ptr (+ level-ptr (count level-bytes))
        msg1-ptr (+ event-ptr (count event-bytes))
        msg2-ptr (+ msg1-ptr (count msg1-bytes))
        push (fn [msg-ptr msg-len]
               (str "    i32.const " level-ptr "\n"
                    "    i32.const " (count level-bytes) "\n"
                    "    i32.const " event-ptr "\n"
                    "    i32.const " (count event-bytes) "\n"
                    "    i32.const " msg-ptr "\n"
                    "    i32.const " msg-len "\n"
                    "    i32.const 0\n    i32.const 0\n"
                    "    call $append\n"))]
    (str
     "(module\n"
     "  (import \"" mod "\" \"append\""
     " (func $append (param i32 i32 i32 i32 i32 i32 i32 i32) (result i64)))\n"
     "  (memory (export \"cm32p2_memory\") 1 1)\n"
     "  (func (export \"cm32p2_realloc\")\n"
     "    (param $old i32) (param $old-size i32) (param $align i32) (param $new-size i32)\n"
     "    (result i32)\n"
     "    local.get $old i32.eqz if (result i32) i32.const 256 else local.get $old end)\n"
     "  (func (export \"cm32p2||run\") (result i64)\n"
     "    (local $s1 i64) (local $s2 i64)\n"
     (push msg1-ptr (count msg1-bytes))
     "    local.set $s1\n"
     (push msg2-ptr (count msg2-bytes))
     "    local.set $s2\n"
     "    local.get $s2 local.get $s1 i64.sub)\n"
     "  (func (export \"cm32p2||run_post\") (param i64))\n"
     "  (func (export \"cm32p2_initialize\"))\n"
     "  (data (i32.const " level-ptr ") \"" (wat-data level-bytes) "\")\n"
     "  (data (i32.const " event-ptr ") \"" (wat-data event-bytes) "\")\n"
     "  (data (i32.const " msg1-ptr ") \"" (wat-data msg1-bytes) "\")\n"
     "  (data (i32.const " msg2-ptr ") \"" (wat-data msg2-bytes) "\")\n"
     ")\n")))

(defn- dual-log-wit []
  (str
   "package kotoba:application@1.0.0;\n\n"
   "interface types {\n"
   "  record kotoba-log-field { key: string, value: string, }\n"
   "  record kotoba-log-append-request {\n"
   "    level: string, event: string, message: string,\n"
   "    fields: list<kotoba-log-field>,\n"
   "  }\n"
   "  record kotoba-log-append-result { sequence: s64, }\n"
   "  record kotoba-log-read-request { after-sequence: s64, limit: s64, }\n"
   "  record kotoba-log-entry {\n"
   "    sequence: s64, level: string, event: string, message: string,\n"
   "    fields: list<kotoba-log-field>,\n"
   "  }\n"
   "  record kotoba-log-read-result {\n"
   "    oldest-sequence: s64, latest-sequence: s64, truncated: bool,\n"
   "    entries: list<kotoba-log-entry>,\n"
   "  }\n"
   "}\n\n"
   "interface log {\n"
   "  use types.{kotoba-log-append-request, kotoba-log-append-result,\n"
   "             kotoba-log-read-request, kotoba-log-read-result};\n"
   "  append: func(request: kotoba-log-append-request) -> kotoba-log-append-result;\n"
   "  read: func(request: kotoba-log-read-request) -> kotoba-log-read-result;\n"
   "}\n\n"
   "world driver { import log; export run: func() -> s64; }\n"))

(defn- ring-overflow-wat []
  (let [mod "cm32p2|kotoba:application/log@1"
        level-bytes (vec (.getBytes "info" "UTF-8"))
        event-bytes (vec (.getBytes "boot" "UTF-8"))
        msg-bytes (vec (.getBytes "hi" "UTF-8"))
        level-ptr 8
        event-ptr (+ level-ptr (count level-bytes))
        msg-ptr (+ event-ptr (count event-bytes))
        read-ret 256
        push (str
              "    i32.const " level-ptr "\n"
              "    i32.const " (count level-bytes) "\n"
              "    i32.const " event-ptr "\n"
              "    i32.const " (count event-bytes) "\n"
              "    i32.const " msg-ptr "\n"
              "    i32.const " (count msg-bytes) "\n"
              "    i32.const 0\n    i32.const 0\n"
              "    call $append\n    drop\n")]
    (str
     "(module\n"
     "  (import \"" mod "\" \"append\""
     " (func $append (param i32 i32 i32 i32 i32 i32 i32 i32) (result i64)))\n"
     "  (import \"" mod "\" \"read\" (func $read (param i64 i64 i32)))\n"
     "  (memory (export \"cm32p2_memory\") 1 1)\n"
     "  (func (export \"cm32p2_realloc\")\n"
     "    (param $old i32) (param $old-size i32) (param $align i32) (param $new-size i32)\n"
     "    (result i32)\n"
     "    local.get $old i32.eqz if (result i32) i32.const 512 else local.get $old end)\n"
     "  (func (export \"cm32p2||run\") (result i64)\n"
     push push push
     "    i64.const 0\n    i64.const 8\n    i32.const " read-ret "\n"
     "    call $read\n"
     "    i32.const " read-ret " i64.load offset=0)\n"
     "  (func (export \"cm32p2||run_post\") (param i64))\n"
     "  (func (export \"cm32p2_initialize\"))\n"
     "  (data (i32.const " level-ptr ") \"" (wat-data level-bytes) "\")\n"
     "  (data (i32.const " event-ptr ") \"" (wat-data event-bytes) "\")\n"
     "  (data (i32.const " msg-ptr ") \"" (wat-data msg-bytes) "\")\n"
     ")\n")))

(defn- run-closed [closed]
  (let [path (Files/createTempFile "amu-log-wasm-aot-" ".wasm"
                                   (make-array FileAttribute 0))]
    (try
      (Files/write path ^bytes (:bytes closed)
                   (make-array java.nio.file.OpenOption 0))
      (shell/sh wasmtime-binary "run" "--invoke" "run()" (str path))
      (finally
        (Files/deleteIfExists path)))))

(deftest log-kit-flag-is-bound-to-this-evidence
  (let [kit (edn/read-string
             (slurp (io/resource "kotoba/lang/capability-kits/log-v1.edn")))]
    (is (= :implemented (get-in kit [:qualification :wasm-aot])))
    (is (= :pending (get-in kit [:qualification :wasm32-kotoba-v1])))
    (is (= :pending (get-in kit [:qualification :native-aot])))
    (is (= :implemented (get-in kit [:qualification :jit]))
        "kotoba-script :js-kotoba-v1 under V8; measured on the default
         branch by the jit round-trip deftest for this kit")))

(deftest wasmtime-log-kit-advances-sequence-across-appends
  (let [d (log-v1-descriptors)
        provider (composition/package-log-provider
                  (:append-req d) (:append-res d)
                  (:read-req d) (:read-res d)
                  (:schemas d))
        driver (package-component "amu-log-append-driver-"
                                  (append-only-wit) (append-sequence-wat)
                                  [:log/append])
        closed (composition/compose-closed driver [provider])
        run (run-closed closed)]
    (is (zero? (:exit run)) (str "wasmtime err: " (:err run)))
    (is (= "1" (str/trim (:out run))))))

(deftest wasmtime-log-kit-drops-oldest-on-ring-overflow
  (let [d (log-v1-descriptors)
        provider (composition/package-log-provider
                  (:append-req d) (:append-res d)
                  (:read-req d) (:read-res d)
                  (:schemas d)
                  2)
        driver (package-component "amu-log-overflow-driver-"
                                  (dual-log-wit) (ring-overflow-wat)
                                  [:log/append :log/read])
        closed (composition/compose-closed driver [provider])
        run (run-closed closed)]
    (is (zero? (:exit run)) (str "wasmtime err: " (:err run)))
    (is (= "2" (str/trim (:out run)))
        "capacity-2 ring after 3 appends must drop seq 1 (oldest=2)")))
