(ns kotoba.compiler.component
  "The intentionally small, JVM-only bridge from Kotoba core Wasm to the
   standard Component binary format.  `wasm-tools` is used as the reference
   encoder until the compiler owns the Component encoder itself."
  (:require [clojure.java.io :as io]
            [clojure.java.shell :as shell]
            [kotoba.abi.contract :as abi])
  (:import [java.nio.file Files Path]
           [java.nio.charset StandardCharsets]))

(def world-id abi/component-world)
(def world-id-v2 abi/component-world-v2)
(def typed-world-id-v3 abi/typed-capability-world-v3)

(defn typed-world-wit-v3 []
  (abi/typed-capability-wit-v3))

(defn world-id-for [target]
  (case target
    :wasm-component-kotoba-v1 world-id
    :wasm-component-kotoba-v2 world-id-v2
    (throw (ex-info "unsupported Component world target" {:target target}))))

(def capability-import-names abi/capability-import-names)

(defn capability-import-name [id]
  (abi/capability-import-name id))

(defn world-wit
  ([capability-ids] (abi/world-wit capability-ids))
  ([target capability-ids]
   (case target
     :wasm-component-kotoba-v1 (abi/world-wit capability-ids)
     :wasm-component-kotoba-v2 (abi/world-wit-v2 capability-ids)
     (throw (ex-info "unsupported Component world target" {:target target})))))

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
   (encode! core-bytes capability-ids :wasm-component-kotoba-v1))
  ([core-bytes capability-ids target]
  (let [typed-effect? (and (= target :wasm-component-kotoba-v2) (seq capability-ids))
        dir (Files/createTempDirectory "kotoba-component-" (make-array java.nio.file.attribute.FileAttribute 0))
        wit (.resolve dir "kotoba-app.wit")
        core (.resolve dir "core.wasm")
        embedded (.resolve dir "embedded.wasm")
        component (.resolve dir "app.component.wasm")]
    (try
      (Files/writeString wit (if typed-effect? (typed-world-wit-v3)
                                 (world-wit target capability-ids))
                         StandardCharsets/UTF_8 (make-array java.nio.file.OpenOption 0))
      (Files/write core core-bytes (make-array java.nio.file.OpenOption 0))
      (command! "wasm-tools" "component" "embed" (.toString wit) (.toString core)
                "--world" (if typed-effect? "application" "kotoba-app")
                "--output" (.toString embedded))
      (command! "wasm-tools" "component" "new" (.toString embedded)
                "--reject-legacy-names" "--output" (.toString component))
      (Files/readAllBytes component)
      (finally
        ;; All paths are exact children of a directory created above; never
        ;; recursively delete a caller path.
        (doseq [^Path path [component embedded core wit dir]]
          (Files/deleteIfExists path)))))))
