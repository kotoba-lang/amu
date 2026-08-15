(ns kotoba.compiler.clock-wasm-aot-qualification-test
  "Binds clock-v1 :wasm-aot to WASI 0.3 host-time execution.

  :wasm-aot is the kit variant/record schema on a wasm component whose
  time comes from wasi:clocks/{system,monotonic}-clock@0.3.0 — not the
  i64 (clock/now seed) surface named :wasm32-kotoba-v1 (ADR 0257).

  The driver is the same wall-reading WAT as kotoba-component W6
  (`run() -> s64` of unix-millis). It lives here so flipping
  clock-v1.edn cannot stay green without this suite going red."
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

(def ^:private minimum-wasmtime-major
  (-> (io/resource "kotoba/lang/component-model-v1.edn")
      slurp edn/read-string
      (get-in [:spec-baseline :wasi :minimum-wasmtime-major])))

(defn- wasmtime-major []
  (let [{:keys [exit out]} (shell/sh wasmtime-binary "--version")]
    (when (zero? exit)
      (some-> (re-find #"wasmtime (\d+)\." out) second parse-long))))

(defn- require-qualifying-wasmtime!
  "Fail, do not skip. A quiet pass on wasmtime < 43 would leave WASI 0.3
   unproven while the kit claims :wasm-aot."
  []
  (let [major (wasmtime-major)]
    (is (some? major)
        (str "wasmtime not runnable as " wasmtime-binary))
    (is (and major (>= major minimum-wasmtime-major))
        (str "WASI 0.3 qualification needs wasmtime >= " minimum-wasmtime-major
             ", found " major))
    (and major (>= major minimum-wasmtime-major))))

(defn- ref-ify [variant-descriptor]
  (let [[_ variant-name cases] variant-descriptor
        schemas (atom {})
        ref-cases (mapv (fn [[tag payload]]
                          (if (and (vector? payload) (= :record (first payload)))
                            (let [[_ record-name _fields] payload]
                              (swap! schemas assoc record-name payload)
                              [tag [:ref record-name]])
                            [tag payload]))
                        cases)]
    (swap! schemas assoc variant-name [:variant variant-name ref-cases])
    {:descriptor [:ref variant-name] :schemas @schemas}))

(defn- clock-v1-descriptors []
  (let [kit (edn/read-string
             (slurp (io/resource "kotoba/lang/capability-kits/clock-v1.edn")))
        request (ref-ify (:request kit))
        result (ref-ify (:result kit))]
    {:descriptor (:descriptor request)
     :result-descriptor (:descriptor result)
     :schemas (merge (:schemas request) (:schemas result))}))

(defn- driver-wit []
  (str
   "package kotoba:application@1.0.0;\n\n"
   "interface types {\n"
   "  record kotoba-clock-wall {\n    unix-millis: s64,\n    observation-sequence: s64,\n  }\n"
   "  record kotoba-clock-monotonic {\n    nanos: s64,\n    observation-sequence: s64,\n  }\n"
   "  record kotoba-clock-error {\n    code: string,\n    message: string,\n  }\n"
   "  variant kotoba-clock-request {\n    wall(bool),\n    monotonic(bool),\n  }\n"
   "  variant kotoba-clock-result {\n"
   "    wall(kotoba-clock-wall),\n    monotonic(kotoba-clock-monotonic),\n"
   "    error(kotoba-clock-error),\n  }\n"
   "}\n\n"
   "interface clock {\n"
   "  use types.{kotoba-clock-request, kotoba-clock-result};\n"
   "  now: func(request: kotoba-clock-request) -> kotoba-clock-result;\n"
   "}\n\n"
   "world driver {\n  import clock;\n  export run: func() -> s64;\n}\n"))

(defn- driver-wat []
  (let [mod "cm32p2|kotoba:application/clock@1"
        ret-base 64]
    (str
     "(module\n"
     "  (import \"" mod "\" \"now\" (func $now (param i32 i32 i32)))\n"
     "  (memory (export \"cm32p2_memory\") 1 1)\n"
     "  (func (export \"cm32p2_realloc\")\n"
     "    (param $old i32) (param $old-size i32) (param $align i32) (param $new-size i32)\n"
     "    (result i32)\n"
     "    local.get $old i32.eqz if (result i32) i32.const 256 else local.get $old end)\n"
     "  (func (export \"cm32p2||run\") (result i64)\n"
     "    i32.const 0 i32.const 0 i32.const " ret-base " call $now\n"
     "    i32.const " ret-base " i64.load offset=8)\n"
     "  (func (export \"cm32p2||run_post\") (param i64))\n"
     "  (func (export \"cm32p2_initialize\"))\n"
     ")\n")))

(defn- package-driver []
  (let [dir (Files/createTempDirectory "amu-clock-wasm-aot-driver-"
                                       (make-array FileAttribute 0))
        world (.resolve dir "driver.wit")
        core (.resolve dir "driver.wasm")
        embedded (.resolve dir "embedded.wasm")
        component (.resolve dir "driver.component.wasm")]
    (try
      (Files/writeString world (driver-wit) (make-array java.nio.file.OpenOption 0))
      (Files/write core (wasm-tools/parse-wat (driver-wat))
                   (make-array java.nio.file.OpenOption 0))
      (wasm-tools/run-command! ["wasm-tools" "component" "embed" (str world) (str core)
                                "--encoding" "utf8" "-o" (str embedded)])
      (wasm-tools/run-command! ["wasm-tools" "component" "new" (str embedded)
                                "--reject-legacy-names" "-o" (str component)])
      {:format :wasm-component/v1 :imports [:clock/now]
       :bytes (Files/readAllBytes component)}
      (finally
        (doseq [p [component embedded core world]] (Files/deleteIfExists p))
        (Files/deleteIfExists dir)))))

(defn- composed-artifact []
  (let [{:keys [descriptor result-descriptor schemas]} (clock-v1-descriptors)
        provider (composition/package-clock-wasi-provider
                  :clock/now descriptor result-descriptor schemas)]
    (composition/compose-with-declared-wasi
     (package-driver) [provider] composition/clock-wasi-imports)))

(defn- run-composed [path flags]
  (apply shell/sh (concat [wasmtime-binary "run"] flags
                          ["--invoke" "run()" (str path)])))

(deftest clock-kit-flag-is-bound-to-this-evidence
  (let [kit (edn/read-string
             (slurp (io/resource "kotoba/lang/capability-kits/clock-v1.edn")))]
    (is (= :implemented (get-in kit [:qualification :wasm-aot]))
        "do not claim :wasm-aot without the WASI host-time tests in this ns")
    (is (= :pending (get-in kit [:qualification :native-aot]))
        "native remains the C-free aiueos syscall gap")
    (is (= :pending (get-in kit [:qualification :jit])))))

(deftest clock-wasi-composition-keeps-only-declared-clocks
  (let [composed (composed-artifact)
        imports (set (composition/composed-world-imports (:bytes composed)))]
    (is (= :wasm-component-wasi-composed/v1 (:format composed)))
    (is (= (vec (sort composition/clock-wasi-imports)) (:wasi-imports composed)))
    (is (not (contains? imports "kotoba:application/clock@1.0.0")))))

(deftest wasmtime-wasi-clock-kit-returns-real-host-time
  (when (require-qualifying-wasmtime!)
    (let [composed (composed-artifact)
          path (Files/createTempFile "amu-clock-wasm-aot-" ".wasm"
                                     (make-array FileAttribute 0))]
      (try
        (Files/write path ^bytes (:bytes composed)
                     (make-array java.nio.file.OpenOption 0))
        (let [before (System/currentTimeMillis)
              granted (run-composed path ["-S" "p3"])
              after (System/currentTimeMillis)]
          (is (zero? (:exit granted)) (str "wasmtime err: " (:err granted)))
          (let [millis (parse-long (str/trim (:out granted)))]
            (is (some? millis) (str "no reading in: " (pr-str (:out granted))))
            (is (and millis (<= (- before 1000) millis (+ after 1000)))
                (str "component time " millis " outside host window ["
                     before ", " after "]"))))
        (finally
          (Files/deleteIfExists path))))))

(deftest wasmtime-denies-clock-kit-when-wasi-is-withheld
  (when (require-qualifying-wasmtime!)
    (let [composed (composed-artifact)
          path (Files/createTempFile "amu-clock-wasm-aot-deny-" ".wasm"
                                     (make-array FileAttribute 0))]
      (try
        (Files/write path ^bytes (:bytes composed)
                     (make-array java.nio.file.OpenOption 0))
        (let [denied (run-composed path ["-S" "cli=n" "-S" "p3=n"])]
          (is (not (zero? (:exit denied)))
              "withholding the clocks must not still produce a time")
          (is (str/includes? (:err denied) "wasi:clocks/")
              (str "unexpected denial message: " (:err denied)))
          (is (str/includes? (:err denied) "not found in the linker")
              (str "unexpected denial message: " (:err denied))))
        (finally
          (Files/deleteIfExists path))))))
