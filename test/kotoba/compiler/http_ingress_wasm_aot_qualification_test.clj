(ns kotoba.compiler.http-ingress-wasm-aot-qualification-test
  "Binds http-ingress-v1 :wasm-aot to host inject → accept.

  Empty queue stays option none (existing accept drivers). A host injects
  through http-ingress-host.inject; accept must return that request, not none."
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

(defn- http-ingress-descriptors []
  (let [kit (edn/read-string
             (slurp (io/resource "kotoba/lang/capability-kits/http-ingress-v1.edn")))
        accept (first (filter #(= :http/accept (:name %)) (:capabilities kit)))
        reply (first (filter #(= :http/reply (:name %)) (:capabilities kit)))
        accept-req (ref-ify (:request accept))
        incoming (ref-ify (second (:result accept)))
        reply-req (ref-ify (:request reply))]
    {:accept-req (:descriptor accept-req)
     :accept-res [:option (:descriptor incoming)]
     :reply-req (:descriptor reply-req)
     :reply-res :bool
     :schemas (merge (:schemas accept-req) (:schemas incoming)
                     (:schemas reply-req))}))

(defn- inject-driver-wit []
  (str
   "package kotoba:application@1.0.0;\n\n"
   "interface types {\n"
   "  record kotoba-http-accept-request { slot: s64, }\n"
   "  record kotoba-http-header { name: string, value: string, }\n"
   "  record kotoba-http-incoming-request {\n"
   "    method: string, path: string,\n"
   "    headers: list<kotoba-http-header>, body: string,\n"
   "  }\n"
   "}\n\n"
   "interface http-ingress {\n"
   "  use types.{kotoba-http-accept-request, kotoba-http-incoming-request};\n"
   "  accept: func(request: kotoba-http-accept-request) -> option<kotoba-http-incoming-request>;\n"
   "}\n\n"
   "interface http-ingress-host {\n"
   "  use types.{kotoba-http-incoming-request};\n"
   "  inject: func(request: kotoba-http-incoming-request);\n"
   "}\n\n"
   "world driver { import http-ingress; import http-ingress-host; export run: func() -> s64; }\n"))

(defn- inject-driver-wat []
  (let [ingress "cm32p2|kotoba:application/http-ingress@1"
        host "cm32p2|kotoba:application/http-ingress-host@1"
        method-bytes (vec (.getBytes "GET" "UTF-8"))
        path-bytes (vec (.getBytes "/x" "UTF-8"))
        mptr 8
        pptr (+ mptr (count method-bytes))
        accept-ret 64]
    (str
     "(module\n"
     "  (import \"" ingress "\" \"accept\" (func $accept (param i64 i32)))\n"
     "  (import \"" host "\" \"inject\""
     " (func $inject (param i32 i32 i32 i32 i32 i32 i32 i32)))\n"
     "  (memory (export \"cm32p2_memory\") 1 1)\n"
     "  (func (export \"cm32p2_realloc\")\n"
     "    (param $old i32) (param $old-size i32) (param $align i32) (param $new-size i32)\n"
     "    (result i32)\n"
     "    local.get $old i32.eqz if (result i32) i32.const 256 else local.get $old end)\n"
     "  (func (export \"cm32p2||run\") (result i64)\n"
     "    (local $disc i32)\n"
     "    i32.const " mptr " i32.const " (count method-bytes) "\n"
     "    i32.const " pptr " i32.const " (count path-bytes) "\n"
     "    i32.const 0 i32.const 0\n"
     "    i32.const 0 i32.const 0\n"
     "    call $inject\n"
     "    i64.const 0 i32.const " accept-ret " call $accept\n"
     "    i32.const " accept-ret " i32.load8_u offset=0 local.set $disc\n"
     "    local.get $disc i32.eqz if (result i64) i64.const 0\n"
     "    else i32.const " accept-ret " i32.load offset=16 i64.extend_i32_u end)\n"
     "  (func (export \"cm32p2||run_post\") (param i64))\n"
     "  (func (export \"cm32p2_initialize\"))\n"
     "  (data (i32.const " mptr ") \"" (wat-data method-bytes) "\")\n"
     "  (data (i32.const " pptr ") \"" (wat-data path-bytes) "\")\n"
     ")\n")))

(defn- package-driver []
  (let [dir (Files/createTempDirectory "amu-http-ingress-wasm-aot-driver-"
                                       (make-array FileAttribute 0))
        world (.resolve dir "driver.wit")
        core (.resolve dir "driver.wasm")
        embedded (.resolve dir "embedded.wasm")
        component (.resolve dir "driver.component.wasm")]
    (try
      (Files/writeString world (inject-driver-wit) (make-array java.nio.file.OpenOption 0))
      (Files/write core (wasm-tools/parse-wat (inject-driver-wat))
                   (make-array java.nio.file.OpenOption 0))
      (wasm-tools/run-command! ["wasm-tools" "component" "embed" (str world) (str core)
                                "--encoding" "utf8" "-o" (str embedded)])
      (wasm-tools/run-command! ["wasm-tools" "component" "new" (str embedded)
                                "--reject-legacy-names" "-o" (str component)])
      {:format :wasm-component/v1 :imports [:http/accept :http-ingress-host/inject]
       :bytes (Files/readAllBytes component)}
      (finally
        (doseq [p [component embedded core world]] (Files/deleteIfExists p))
        (Files/deleteIfExists dir)))))

(deftest http-ingress-kit-flag-is-bound-to-this-evidence
  (let [kit (edn/read-string
             (slurp (io/resource "kotoba/lang/capability-kits/http-ingress-v1.edn")))]
    (is (= :implemented (get-in kit [:qualification :wasm-aot])))
    (is (= :pending (get-in kit [:qualification :native-aot])))
    (is (= :pending (get-in kit [:qualification :jit])))))

(deftest wasmtime-http-ingress-kit-returns-host-injected-path-length
  (let [d (http-ingress-descriptors)
        provider (composition/package-http-ingress-provider
                  (:accept-req d) (:accept-res d)
                  (:reply-req d) (:reply-res d)
                  (:schemas d))
        closed (composition/compose-closed (package-driver) [provider])
        path (Files/createTempFile "amu-http-ingress-wasm-aot-" ".wasm"
                                   (make-array FileAttribute 0))]
    (try
      (Files/write path ^bytes (:bytes closed)
                   (make-array java.nio.file.OpenOption 0))
      (let [run (shell/sh wasmtime-binary "run" "--invoke" "run()" (str path))]
        (is (zero? (:exit run)) (str "wasmtime err: " (:err run)))
        (is (= "2" (str/trim (:out run)))))
      (finally
        (Files/deleteIfExists path)))))
