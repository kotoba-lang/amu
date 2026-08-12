(ns kotoba.compiler.nbb.io
  "Minimal Node-`fs`-based file I/O for the nbb-native compile/check path
  (`bin/amu`'s Wasm and ordinary-native fast paths). This is a primary compiler
  boundary, so publication follows the same durable shape as the JVM path:
  an OS-created private temporary location, exclusive/no-follow file creation,
  complete write, file `fsync`, close, then same-filesystem atomic rename.
  Hardened EDN parsing remains in `kotoba.compiler.nbb.cli-support`; Windows
  owner-only ACL provisioning remains a JVM-only requirement because this path
  emits no private keys."
  (:require ["node:fs" :as fs]
            ["node:path" :as path]))

;; Matches `kotoba.compiler.bounded-edn/max-source-bytes` exactly (the
;; stricter of its two limits -- `.kotoba` source and `--policy` EDN both
;; go through this same function, so both get the tighter cap). Checked
;; against the RAW byte count before UTF-8 decoding, same order the JVM
;; path's `read-bytes` uses -- confirmed live: without this, a >1MiB
;; `.kotoba` source silently reached `sema/analyze`'s own (differently
;; worded) size check instead of failing here with the exact message
;; `scripts/conformance.cljs` asserts on.
(def ^:private max-bytes (* 1024 1024))

(defn read-text-file [p]
  (when-not (and (string? p) (seq p))
    (throw (ex-info "input path is required" {:phase :decode})))
  (let [buf (try
              (.readFileSync fs p)
              (catch :default error
                (throw (ex-info "input could not be read" {:phase :decode :path p} error))))]
    (when (> (.-length buf) max-bytes)
      (throw (ex-info "input exceeds byte limit" {:phase :decode :path p})))
    (let [decoder (js/TextDecoder. "utf-8" #js {:fatal true})]
      (try
        (.decode decoder buf)
        (catch :default error
          (throw (ex-info "input is not valid UTF-8" {:phase :decode :path p} error)))))))

(defn- open-output! [temporary]
  (let [constants (.-constants fs)
        no-follow (or (.-O_NOFOLLOW constants) 0)
        flags (bit-or (.-O_CREAT constants)
                      (.-O_EXCL constants)
                      (.-O_WRONLY constants)
                      no-follow)]
    ;; 0600 is also the JVM temporary-file posture on POSIX. The NBB path does
    ;; not emit keys, but private creation prevents another local user from
    ;; observing an artifact before publication.
    (.openSync fs temporary flags 384)))

(defn- write-atomic! [output-path write-fd!]
  (when-not (and (string? output-path) (seq output-path))
    (throw (ex-info "output path is required" {:phase :output})))
  (let [target (.resolve path output-path)
        dir (.dirname path target)]
    (when-not (try (.isDirectory (.statSync fs dir)) (catch :default _ false))
      (throw (ex-info "output parent must be a directory" {:phase :output :path output-path})))
    ;; mkdtemp is an OS-exclusive allocation. The previous Math.random name
    ;; could already exist as an attacker-controlled symlink; writeFileSync
    ;; would then follow it before rename ever protected TARGET.
    (let [temporary-dir (.mkdtempSync fs (.join path dir ".kotoba-output-"))
          temporary (.join path temporary-dir "artifact.tmp")
          descriptor (volatile! nil)
          operation (volatile! :open)]
      (try
        (let [fd (open-output! temporary)]
          (vreset! descriptor fd)
          (vreset! operation :write)
          (write-fd! fd)
          (vreset! operation :fsync)
          (.fsyncSync fs fd)
          (.closeSync fs fd)
          (vreset! descriptor nil))
        (vreset! operation :rename)
        ;; rename replaces a destination symlink itself on POSIX; it never
        ;; opens the symlink's referent.
        (.renameSync fs temporary target)
        output-path
        (catch :default error
          (throw (ex-info "atomic output failed"
                          {:phase :output :path output-path :reason @operation}
                          error)))
        (finally
          (when-some [fd @descriptor]
            (try (.closeSync fs fd) (catch :default _ nil)))
          (try (.rmSync fs temporary-dir #js {:recursive true :force true})
               (catch :default _ nil)))))))

(defn write-bytes! [output-path ^js bytes]
  (write-atomic! output-path #(.writeFileSync fs % bytes)))

;; Same fsync-before-rename boundary as `write-bytes!`, for the native compile
;; path's `.kexe`/`.provenance.edn` output.
(defn write-text! [output-path ^string text]
  (write-atomic! output-path #(.writeFileSync fs % text "utf8")))
