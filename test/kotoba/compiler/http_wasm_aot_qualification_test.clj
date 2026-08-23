(ns kotoba.compiler.http-wasm-aot-qualification-test
  "Binds http-v1 :wasm-aot to a sync kit-shaped host boundary.

  WASI `wasi:http/client@0.3.0` is async func + streams; standard32 has no
  future/stream surface, so wasm-aot cannot import it. The kit is
  `:synchronous-reference`. The provider validates kit bounds then forwards
  to imported `http-host.post`. Tests plug an echo stub (status 200, body =
  request body). That is not ambient network and not the cljs transport
  (ADR 0066). It is the host seam a production embedder fills.

  hello(5)+xy(2)=7. Fixed `\"ok\"` cannot produce 7. Withholding the stub
  fails to link on `http-host`."
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
                (and (vector? d) (#{:set :list} (first d)))
                [(first d) (walk (second d))]
                :else d))]
      (let [root (walk descriptor)]
        {:descriptor root :schemas @schemas}))))

(defn- http-v1-descriptors []
  (let [kit (edn/read-string
             (slurp (io/resource "kotoba/lang/capability-kits/http-v1.edn")))
        req (ref-ify (:request kit))
        res (ref-ify (:result kit))]
    {:request (:descriptor req)
     :result (:descriptor res)
     :schemas (merge (:schemas req) (:schemas res))}))

(defn- echo-driver-wit []
  (str
   "package kotoba:application@1.0.0;\n\n"
   "interface types {\n"
   "  record kotoba-http-header { name: string, value: string, }\n"
   "  record kotoba-http-post-request {\n"
   "    url: string, headers: list<kotoba-http-header>, body: string, timeout-ms: s64,\n"
   "  }\n"
   "  record kotoba-http-response {\n"
   "    status: s64, headers: list<kotoba-http-header>, body: string,\n"
   "  }\n"
   "  record kotoba-http-error { code: string, message: string, retryable: bool, }\n"
   "  variant kotoba-http-result { ok(kotoba-http-response), error(kotoba-http-error), }\n"
   "}\n\n"
   "interface http-post {\n"
   "  use types.{kotoba-http-post-request, kotoba-http-result};\n"
   "  post: func(request: kotoba-http-post-request) -> kotoba-http-result;\n"
   "}\n\n"
   "world driver {\n  import http-post;\n  export run: func() -> s64;\n}\n"))

(defn- echo-driver-wat []
  (let [mod "cm32p2|kotoba:application/http-post@1"
        url-bytes (vec (.getBytes "https://x" "UTF-8"))
        b1 (vec (.getBytes "hello" "UTF-8"))
        b2 (vec (.getBytes "xy" "UTF-8"))
        url-ptr 8
        b1-ptr 24
        b2-ptr 32
        r1 64
        r2 160
        body-len-offset 28
        push (fn [ret body-ptr body-len]
               (str
                "    i32.const " url-ptr " i32.const " (count url-bytes) "\n"
                "    i32.const 0 i32.const 0\n"
                "    i32.const " body-ptr " i32.const " body-len "\n"
                "    i64.const 1000 i32.const " ret " call $post\n"))]
    (str
     "(module\n"
     "  (import \"" mod "\" \"post\" (func $post (param i32 i32 i32 i32 i32 i32 i64 i32)))\n"
     "  (memory (export \"cm32p2_memory\") 1 1)\n"
     "  (func (export \"cm32p2_realloc\")\n"
     "    (param $old i32) (param $old-size i32) (param $align i32) (param $new-size i32)\n"
     "    (result i32)\n"
     "    local.get $old i32.eqz if (result i32) i32.const 256 else local.get $old end)\n"
     "  (func (export \"cm32p2||run\") (result i64)\n"
     "    (local $l1 i32) (local $l2 i32)\n"
     (push r1 b1-ptr (count b1))
     "    i32.const " r1 " i32.load offset=" body-len-offset " local.set $l1\n"
     (push r2 b2-ptr (count b2))
     "    i32.const " r2 " i32.load offset=" body-len-offset " local.set $l2\n"
     "    local.get $l1 local.get $l2 i32.add i64.extend_i32_u)\n"
     "  (func (export \"cm32p2||run_post\") (param i64))\n"
     "  (func (export \"cm32p2_initialize\"))\n"
     "  (data (i32.const " url-ptr ") \"" (wat-data url-bytes) "\")\n"
     "  (data (i32.const " b1-ptr ") \"" (wat-data b1) "\")\n"
     "  (data (i32.const " b2-ptr ") \"" (wat-data b2) "\")\n"
     ")\n")))

(defn- package-driver []
  (let [dir (Files/createTempDirectory "amu-http-wasm-aot-driver-"
                                       (make-array FileAttribute 0))
        world (.resolve dir "driver.wit")
        core (.resolve dir "driver.wasm")
        embedded (.resolve dir "embedded.wasm")
        component (.resolve dir "driver.component.wasm")]
    (try
      (Files/writeString world (echo-driver-wit)
                         (make-array java.nio.file.OpenOption 0))
      (Files/write core (wasm-tools/parse-wat (echo-driver-wat))
                   (make-array java.nio.file.OpenOption 0))
      (wasm-tools/run-command! ["wasm-tools" "component" "embed" (str world) (str core)
                                "--encoding" "utf8" "-o" (str embedded)])
      (wasm-tools/run-command! ["wasm-tools" "component" "new" (str embedded)
                                "--reject-legacy-names" "-o" (str component)])
      {:format :wasm-component/v1 :imports [:http/post]
       :bytes (Files/readAllBytes component)}
      (finally
        (doseq [p [component embedded core world]] (Files/deleteIfExists p))
        (Files/deleteIfExists dir)))))

(deftest http-kit-flag-is-bound-to-this-evidence
  (let [kit (edn/read-string
             (slurp (io/resource "kotoba/lang/capability-kits/http-v1.edn")))]
    (is (= :implemented (get-in kit [:qualification :wasm-aot]))
        "do not claim :wasm-aot without the echo-host tests in this ns")
    (is (= :pending (get-in kit [:qualification :wasm32-kotoba-v1])))
    (is (= :pending (get-in kit [:qualification :native-aot])))
    (is (= :implemented (get-in kit [:qualification :jit]))
        "kotoba-script :js-kotoba-v1 under V8; measured on the default
         branch by the jit round-trip deftest for this kit")))

(deftest wasmtime-http-kit-echo-body-length-sum-is-7
  (let [d (http-v1-descriptors)
        provider (composition/package-http-echo-provider
                  (:request d) (:result d) (:schemas d))
        closed (composition/compose-closed (package-driver) [provider])
        path (Files/createTempFile "amu-http-wasm-aot-" ".wasm"
                                   (make-array FileAttribute 0))]
    (try
      (Files/write path ^bytes (:bytes closed)
                   (make-array java.nio.file.OpenOption 0))
      (let [run (shell/sh wasmtime-binary "run" "--invoke" "run()" (str path))]
        (is (zero? (:exit run)) (str "wasmtime err: " (:err run)))
        (is (= "7" (str/trim (:out run)))))
      (finally
        (Files/deleteIfExists path)))))

(deftest wasmtime-denies-http-kit-when-host-is-withheld
  (let [d (http-v1-descriptors)
        provider (composition/package-http-host-provider
                  (:request d) (:result d) (:schemas d))
        closed (composition/compose-closed (package-driver) [provider])
        path (Files/createTempFile "amu-http-wasm-aot-deny-" ".wasm"
                                   (make-array FileAttribute 0))]
    (try
      (Files/write path ^bytes (:bytes closed)
                   (make-array java.nio.file.OpenOption 0))
      (let [denied (shell/sh wasmtime-binary "run" "--invoke" "run()" (str path))]
        (is (not (zero? (:exit denied)))
            "withholding http-host must not still produce a body length")
        (is (re-find #"(?i)http-host" (str (:err denied) (:out denied)))))
      (finally
        (Files/deleteIfExists path)))))
