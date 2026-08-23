(ns scripts.wasmtime-tool
  (:require [scripts.lib :as lib]
            ["node:child_process" :as child]
            ["node:crypto" :as crypto]
            ["node:fs" :as fs]
            ["node:path" :as path]))

;; 43, not 42, because kotoba-component's component-model-v1.edn declares
;; :minimum-wasmtime-major 43 for WASI 0.3 and the clock kit's qualification
;; suite reads that number rather than hard-coding one. Pinned at 42 the
;; suite could not pass anywhere -- not locally and not in CI, which
;; provisions through this same table -- so the gate would have been
;; permanently red rather than discriminating. v43.0.2 is the lowest patch
;; of the lowest major that satisfies the declared baseline; the four
;; digests below were taken with shasum -a 256 over the downloaded archives.
(def version "43.0.2")
(def releases
  {"linux-x64" {:archive "wasmtime-v43.0.2-x86_64-linux.tar.xz"
                 :sha256 "06a0b36fd70b6fe4efc3a52325907cbfbb7513c9e1faced9b12e1113d3b89980"}
   "linux-arm64" {:archive "wasmtime-v43.0.2-aarch64-linux.tar.xz"
                   :sha256 "2febb5cdbe18992e5a87598e4f58afddb4509b4ae9a1b0ebe7af4e56e14039e8"}
   "darwin-arm64" {:archive "wasmtime-v43.0.2-aarch64-macos.tar.xz"
                    :sha256 "cbe9eeb255f128d0f7eca1b05c081b5fb825ecbcba9dfd2d8c53faa668ada85b"}
   "darwin-x64" {:archive "wasmtime-v43.0.2-x86_64-macos.tar.xz"
                  :sha256 "34e3ad503a5cf2578489d5aa998ef1038bfb862aebc593a4411daf9f2851c34d"}})

(def root (.join path lib/root ".tools" "wasmtime"))
(def executable (.join path root "wasmtime"))

(defn- verify-tool! []
  (when (.existsSync fs executable)
    (let [result (.spawnSync child executable #js ["--version"]
                             #js {:encoding "utf8" :maxBuffer 65536})]
      (when (and (zero? (or (.-status result) 70))
                 (.startsWith (or (.-stdout result) "") (str "wasmtime " version " ")))
        executable))))

(defn ensure! []
  (if-let [installed (verify-tool!)]
    (js/Promise.resolve installed)
    (let [key (str (.-platform js/process) "-" (.-arch js/process))
          {:keys [archive sha256]} (get releases key)]
      (when-not archive
        (throw (js/Error. (str "unsupported Wasmtime tool platform: " key))))
      (let [url (str "https://github.com/bytecodealliance/wasmtime/releases/download/v"
                     version "/" archive)
            staging (str root ".tmp")
            archive-path (.join path staging archive)]
        (-> (js/fetch url #js {:redirect "follow"})
            (.then (fn [response]
                     (when-not (.-ok response)
                       (throw (js/Error. (str "Wasmtime download failed: " (.-status response)))))
                     (.arrayBuffer response)))
            (.then (fn [array-buffer]
                     (let [bytes (.from js/Buffer array-buffer)
                           actual (-> (.createHash crypto "sha256") (.update bytes) (.digest "hex"))]
                       (when-not (= sha256 actual)
                         (throw (js/Error. "Wasmtime archive digest mismatch")))
                       (.rmSync fs staging #js {:recursive true :force true})
                       (.mkdirSync fs staging #js {:recursive true})
                       (.writeFileSync fs archive-path bytes)
                       (let [result (.spawnSync child "tar" #js ["-xJf" archive-path "-C" staging]
                                                #js {:encoding "utf8" :maxBuffer 1048576})]
                         (when-not (zero? (or (.-status result) 70))
                           (throw (js/Error. (str "Wasmtime extraction failed: " (.-stderr result)))))
                         (let [directory (first (filter #(and (not= % archive)
                                                              (.isDirectory (.statSync fs (.join path staging %))))
                                                        (.readdirSync fs staging)))
                               source (.join path staging directory "wasmtime")]
                           (when-not (and directory (.isFile (.statSync fs source)))
                             (throw (js/Error. "Wasmtime archive layout rejected")))
                           (.rmSync fs root #js {:recursive true :force true})
                           (.mkdirSync fs (.dirname path root) #js {:recursive true})
                           (.renameSync fs (.join path staging directory) root)
                           (.rmSync fs staging #js {:recursive true :force true})
                           (or (verify-tool!)
                               (throw (js/Error. "installed Wasmtime identity mismatch")))))))))))))
