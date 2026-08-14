(ns kotoba.compiler.ui-wasm-aot-qualification-test
  "Binds ui-v1 :wasm-aot to host enqueue → next-event.

  Empty queue stays option none (existing commit drivers). A host injects
  through ui-host.enqueue; next-event must return that event, not none."
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
                (and (vector? d) (#{:set :list :option} (first d)))
                [(first d) (walk (second d))]
                :else d))]
      (let [root (walk descriptor)]
        {:descriptor root :schemas @schemas}))))

(defn- ui-v1-descriptors []
  (let [kit (edn/read-string
             (slurp (io/resource "kotoba/lang/capability-kits/ui-v1.edn")))
        commit-req (ref-ify-record (get-in kit [:commit :request]))
        commit-res (ref-ify-record (get-in kit [:commit :result]))
        event-req (ref-ify-record (get-in kit [:event :request]))
        event (ref-ify-record (second (get-in kit [:event :result])))]
    {:commit-req (:descriptor commit-req)
     :commit-res (:descriptor commit-res)
     :event-req (:descriptor event-req)
     :event-res [:option (:descriptor event)]
     :schemas (merge (:schemas commit-req) (:schemas commit-res)
                     (:schemas event-req) (:schemas event))}))

(defn- enqueue-driver-wit []
  (str
   "package kotoba:application@1.0.0;\n\n"
   "interface types {\n"
   "  record kotoba-ui-node { id: string, parent: option<string>, kind: string, text: string, }\n"
   "  record kotoba-ui-commit-request { base-revision: s64, nodes: list<kotoba-ui-node>, }\n"
   "  record kotoba-ui-commit-result { revision: s64, node-count: s64, }\n"
   "  record kotoba-ui-event-request { after-revision: s64, }\n"
   "  record kotoba-ui-event { revision: s64, target: string, kind: string, value: string, }\n"
   "}\n\n"
   "interface ui {\n"
   "  use types.{kotoba-ui-commit-request, kotoba-ui-commit-result,\n"
   "             kotoba-ui-event-request, kotoba-ui-event};\n"
   "  commit: func(request: kotoba-ui-commit-request) -> kotoba-ui-commit-result;\n"
   "  next-event: func(request: kotoba-ui-event-request) -> option<kotoba-ui-event>;\n"
   "}\n\n"
   "interface ui-host {\n"
   "  use types.{kotoba-ui-event};\n"
   "  enqueue: func(event: kotoba-ui-event);\n"
   "}\n\n"
   "world driver { import ui; import ui-host; export run: func() -> s64; }\n"))

(defn- enqueue-driver-wat []
  (let [ui "cm32p2|kotoba:application/ui@1"
        host "cm32p2|kotoba:application/ui-host@1"
        target-bytes (vec (.getBytes "btn" "UTF-8"))
        kind-bytes (vec (.getBytes "click" "UTF-8"))
        value-bytes (vec (.getBytes "x" "UTF-8"))
        tptr 8
        kptr (+ tptr (count target-bytes))
        vptr (+ kptr (count kind-bytes))
        event-ret 128]
    (str
     "(module\n"
     "  (import \"" ui "\" \"next-event\" (func $next-event (param i64 i32)))\n"
     "  (import \"" host "\" \"enqueue\""
     " (func $enqueue (param i64 i32 i32 i32 i32 i32 i32)))\n"
     "  (memory (export \"cm32p2_memory\") 1 1)\n"
     "  (func (export \"cm32p2_realloc\")\n"
     "    (param $old i32) (param $old-size i32) (param $align i32) (param $new-size i32)\n"
     "    (result i32)\n"
     "    local.get $old i32.eqz if (result i32) i32.const 256 else local.get $old end)\n"
     "  (func (export \"cm32p2||run\") (result i64)\n"
     "    (local $disc i32)\n"
     "    i64.const 7\n"
     "    i32.const " tptr " i32.const " (count target-bytes) "\n"
     "    i32.const " kptr " i32.const " (count kind-bytes) "\n"
     "    i32.const " vptr " i32.const " (count value-bytes) "\n"
     "    call $enqueue\n"
     "    i64.const 0 i32.const " event-ret " call $next-event\n"
     "    i32.const " event-ret " i32.load8_u offset=0 local.set $disc\n"
     "    local.get $disc i32.eqz if (result i64) i64.const 0\n"
     "    else i32.const " event-ret " i64.load offset=8 end)\n"
     "  (func (export \"cm32p2||run_post\") (param i64))\n"
     "  (func (export \"cm32p2_initialize\"))\n"
     "  (data (i32.const " tptr ") \"" (wat-data target-bytes) "\")\n"
     "  (data (i32.const " kptr ") \"" (wat-data kind-bytes) "\")\n"
     "  (data (i32.const " vptr ") \"" (wat-data value-bytes) "\")\n"
     ")\n")))

(defn- package-driver []
  (let [dir (Files/createTempDirectory "amu-ui-wasm-aot-driver-"
                                       (make-array FileAttribute 0))
        world (.resolve dir "driver.wit")
        core (.resolve dir "driver.wasm")
        embedded (.resolve dir "embedded.wasm")
        component (.resolve dir "driver.component.wasm")]
    (try
      (Files/writeString world (enqueue-driver-wit) (make-array java.nio.file.OpenOption 0))
      (Files/write core (wasm-tools/parse-wat (enqueue-driver-wat))
                   (make-array java.nio.file.OpenOption 0))
      (wasm-tools/run-command! ["wasm-tools" "component" "embed" (str world) (str core)
                                "--encoding" "utf8" "-o" (str embedded)])
      (wasm-tools/run-command! ["wasm-tools" "component" "new" (str embedded)
                                "--reject-legacy-names" "-o" (str component)])
      {:format :wasm-component/v1 :imports [:ui/next-event :ui-host/enqueue]
       :bytes (Files/readAllBytes component)}
      (finally
        (doseq [p [component embedded core world]] (Files/deleteIfExists p))
        (Files/deleteIfExists dir)))))

(deftest ui-kit-flag-is-bound-to-this-evidence
  (let [kit (edn/read-string
             (slurp (io/resource "kotoba/lang/capability-kits/ui-v1.edn")))]
    (is (= :implemented (get-in kit [:qualification :wasm-aot])))
    (is (= :pending (get-in kit [:qualification :native-aot])))
    (is (= :pending (get-in kit [:qualification :jit])))))

(deftest wasmtime-ui-kit-returns-host-enqueued-revision
  (let [d (ui-v1-descriptors)
        provider (composition/package-ui-provider
                  (:commit-req d) (:commit-res d)
                  (:event-req d) (:event-res d)
                  (:schemas d))
        closed (composition/compose-closed (package-driver) [provider])
        path (Files/createTempFile "amu-ui-wasm-aot-" ".wasm"
                                   (make-array FileAttribute 0))]
    (try
      (Files/write path ^bytes (:bytes closed)
                   (make-array java.nio.file.OpenOption 0))
      (let [run (shell/sh wasmtime-binary "run" "--invoke" "run()" (str path))]
        (is (zero? (:exit run)) (str "wasmtime err: " (:err run)))
        (is (= "7" (str/trim (:out run)))))
      (finally
        (Files/deleteIfExists path)))))
