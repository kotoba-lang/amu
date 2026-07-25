(ns kotoba.compiler.component
  "The intentionally small, JVM-only bridge from Kotoba core Wasm to the
   standard Component binary format.  `wasm-tools` is used as the reference
   encoder until the compiler owns the Component encoder itself."
  (:require [clojure.java.io :as io]
            [clojure.java.shell :as shell])
  (:import [java.nio.file Files Path]
           [java.nio.charset StandardCharsets]))

(def world-id "kotoba:app/kotoba-app@0.1.0")

(def capability-import-names
  {1 "aiueos-identity-sign"
   2 "aiueos-identity-verify"
   3 "aiueos-hash-sha256"
   4 "aiueos-http-post"
   5 "aiueos-log-read"
   6 "aiueos-log-append"
   7 "aiueos-clock-now"})

(defn capability-import-name [id]
  (or (get capability-import-names id)
      (throw (ex-info "Component capability has no named WIT interface"
                      {:phase :component-abi :capability-id id}))))

(defn world-wit [capability-ids]
  (str "package kotoba:app@0.1.0;\n\nworld kotoba-app {\n"
       ;; Every authority is a separately declared WIT import.  There is no
       ;; `wasi:*` umbrella and no generic dispatcher in the Component ABI.
       (apply str (map #(str "  import " (capability-import-name %) ": func(value: s64) -> s64;\n")
                       (sort capability-ids)))
       "  export main: func() -> s64;\n}\n"))

(defn- command! [& args]
  (let [{:keys [exit out err]} (apply shell/sh args)]
    (when-not (zero? exit)
      (throw (ex-info "wasm-tools Component encoding failed"
                      {:phase :component-encode :command args :exit exit :stderr err})))
    out))

(defn encode!
  "Returns a validated standard Component.  No stdout/stderr is inherited, so
   compiler output remains deterministic and failures carry structured data."
  ([core-bytes] (encode! core-bytes #{}))
  ([core-bytes capability-ids]
  (let [dir (Files/createTempDirectory "kotoba-component-" (make-array java.nio.file.attribute.FileAttribute 0))
        wit (.resolve dir "kotoba-app.wit")
        core (.resolve dir "core.wasm")
        embedded (.resolve dir "embedded.wasm")
        component (.resolve dir "app.component.wasm")]
    (try
      (Files/writeString wit (world-wit capability-ids) StandardCharsets/UTF_8 (make-array java.nio.file.OpenOption 0))
      (Files/write core core-bytes (make-array java.nio.file.OpenOption 0))
      (command! "wasm-tools" "component" "embed" (.toString wit) (.toString core)
                "--world" "kotoba-app" "--output" (.toString embedded))
      (command! "wasm-tools" "component" "new" (.toString embedded)
                "--reject-legacy-names" "--output" (.toString component))
      (Files/readAllBytes component)
      (finally
        ;; All paths are exact children of a directory created above; never
        ;; recursively delete a caller path.
        (doseq [^Path path [component embedded core wit dir]]
          (Files/deleteIfExists path)))))))
