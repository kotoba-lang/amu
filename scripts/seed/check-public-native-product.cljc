;; Read back the published native product bytes and exercise each public alias. Packaging/process observations
;; only; no hosted compiler or fallback. Ported from check-public-native-product.py (Basilisp, JUN-974). Needs
;; native x86_64 Linux and the output of check-complete-x86 (--complete). Library: source_lock_checks.cljc (named here so
;; the CI derivation closure covers it rather than the Python module of the same stem).
;; Run: basilisp run -p scripts/seed scripts/seed/check-public-native-product.cljc -- --product DIR --output DIR
;;      --complete DIR
(ns check-public-native-product
  (:require [basilisp.string :as str]
            [gate-util :as u]
            [source-lock-checks :as slc])
  (:import json operator os pathlib platform re subprocess sys))

(def root u/root)
(defn g [m & ks] (reduce (fn [a k] (operator/getitem a k)) m ks))
(defn read-json [p] (json/loads (.read_text p)))
(defn sha [p] (u/sha256-hex (.read_bytes (pathlib/Path p))))
(defn size [p] (.-st_size (.stat (pathlib/Path p))))
(defn chk [c m] (u/chk c (str m)))

(defn run-main [product out complete]
  (chk (and (= (platform/system) "Linux") (= (platform/machine) "x86_64")) "native x86_64 Linux required")
  (let [descriptor (read-json (pathlib/Path product "native-product.json"))
        entry (pathlib/Path product (g descriptor "entry"))
        _ (chk (= (sha entry) (g descriptor "image" "sha256")) "entry digest")
        _ (chk (= (size entry) (g descriptor "image" "bytes")) "entry size")
        proof-path (pathlib/Path complete "complete-x86.json")
        proof (read-json proof-path)]
    (chk (= (g proof "status") "PASS_COMPLETE_NATIVE_X86_COMPILER_BUILD") "complete proof status")
    (chk (= (python/len (g proof "generations")) 3) "three generations")
    (doseq [[i generation] (map-indexed (fn [i x] [(inc i) x]) (g proof "generations"))]
      (let [actual (pathlib/Path complete (str "F" i ".elf"))]
        (chk (and (= (sha actual) (g generation "sha256")) (= (g generation "sha256") (sha entry))) "public image differs from current native compiler")
        (chk (and (= (size actual) (g generation "bytes")) (= (g generation "bytes") (g descriptor "image" "bytes"))) "generation size")))
    (let [paths (vec (filter #(and (seq %) (not (.startswith % "#"))) (.splitlines (.read_text (pathlib/Path root (g descriptor "sourceManifest"))))))
          _ (chk (= (count paths) (g descriptor "sourceModuleCount")) "module count")
          unity (.join (u/bytes-of) (python/list (map #(operator/add (.read_bytes (pathlib/Path root %)) (u/bytes-of 10)) paths)))
          _ (chk (u/deq (u/pydict "bytes" (python/len unity) "sha256" (u/sha256-hex unity)) (g proof "sourceUnity")) "current full source differs")
          aliases (vec (cons entry (map #(pathlib/Path product %) (g descriptor "aliases"))))]
      (doseq [p (rest aliases)]
        (chk (and (.is_symlink p) (= (os/readlink p) (.-name entry))) (str p))
        (chk (= (sha p) (sha entry)) (str p)))
      (.mkdir out ** :mode 0700 :parents true :exist_ok false)
      (let [src (pathlib/Path out "public-good.kotoba")
            _ (.write_text src "(ns public-good (:export [main]))\n(defn main [] :i64 42)\n")
            lock (pathlib/Path out "public-good.ksl")
            _ (.write_text lock (str "KSL1\nentry " src "\nfile " (sha src) " " src "\n"))
            env (u/pydict "PATH" "/nonexistent" "KEXE_ALLOW" "35,37,38,39" "KEXE_CAP_RESOURCES_35" (str out) "KEXE_STACK_BYTES" "8388608")
            calls (python/list [])
            run (fn [name argv expected & {:keys [custom diagnostic]}]
                  (let [r (subprocess/run (python/list (map str argv)) ** :env (or custom env) :cwd out :capture_output true :timeout 120)]
                    (.write_bytes (pathlib/Path out (str name ".stdout")) (.-stdout r))
                    (.write_bytes (pathlib/Path out (str name ".stderr")) (.-stderr r))
                    (chk (= (.-returncode r) expected) [name (.-returncode r) (.-stderr r)])
                    (if diagnostic
                      (chk (and (u/has-bytes? (.encode diagnostic) (.-stderr r)) (not (u/has-bytes? (.encode "KEXE_TRAP") (.-stderr r)))) [name (.-stderr r)])
                      (chk (zero? (python/len (.-stderr r))) [name (.-stderr r)]))
                    (.append calls (u/pydict "name" name "exit" (.-returncode r) "stdoutSHA256" (u/sha256-hex (.-stdout r)) "stderrSHA256" (u/sha256-hex (.-stderr r))))
                    r))]
        (doseq [[i alias] (map-indexed vector aliases)]
          (run (str "alias-" i "-check") [alias "check" src "--source-lock" lock "--source-lock-sha256" (sha lock)] 0))
        (let [container (pathlib/Path out "public-good.kseed")]
          (run "compile-pinned" [entry "compile" src "--target" "aarch64-macos" "--output" container "--source-lock" lock "--source-lock-sha256" (sha lock)] 0)
          (chk (= (sha container) "d9d93e2896184a1eff34a88f79cdfd9d51d96afd2af1f6d1b2020010ebc920bc") "pinned container digest"))
        (let [native (pathlib/Path out "hello.elf")]
          (run "compile-native" [(nth aliases 1) "compile" src "--target" "x86_64-linux" "--output" native "--format" "static"] 0)
          (.chmod native 0700)
          ;; A literal return emits no OP-FUEL. The fixed24 operation-bearing corpus has its own unchanged expectations.
          (let [r (run "run-native" [native] 0 :custom (u/pydict "PATH" "/nonexistent" "KEXE_ALLOW" "-" "KEXE_FUEL" "1000000" "KEXE_STRUCTURED_REPORT" "1"))]
            (chk (and (re/search (.encode ":result 42\\b") (.-stdout r)) (re/search (.encode ":remaining 1000000\\b") (.-stdout r))) (.-stdout r))))
        (run "refuse-digest" [entry "check" src "--source-lock" lock "--source-lock-sha256" (apply str (repeat 64 "0"))] 1 :diagnostic "E6015")
        (run "refuse-c-linked" [entry "compile" src "--target" "x86_64-linux" "--output" (pathlib/Path out "c-linked.elf") "--format" "platform-linked"] 1 :diagnostic "E2")
        (chk (not (.exists (pathlib/Path out "c-linked.elf"))) "c-linked output")
        (run "refuse-default" [entry "compile" src "--output" (pathlib/Path out "refused.kseed")] 1 :diagnostic "E2")
        (run "refuse-worker" [(nth aliases 2) "worker"] 2 :diagnostic "E1")
        (chk (not (.exists (pathlib/Path out "refused.kseed"))) "refused output")
        (let [lock-boundary (slc/check-source-locks aliases (pathlib/Path out "source-lock-boundary"))
              ;; The descriptor's sourceRevision is a claim, not a verified binding to this source unity. Keep the
              ;; old key as null until that binding is proven.
              report (u/pydict "status" "PASS_PUBLIC_NATIVE_PRODUCT" "image" (g descriptor "image")
                               "sourceRevision" nil
                               "publicDescriptorSourceRevision" (g descriptor "sourceRevision")
                               "aliases" (count aliases)
                               "nativeResult" 42 "remainingFuel" 1000000 "calls" calls
                               "completeReceiptSHA256" (sha proof-path)
                               "currentSourceUnity" (g proof "sourceUnity")
                               "sameAsCurrentNativeGenerations" true
                               "sourceLockBoundary" lock-boundary
                               "observerSourceSHA256" (sha (pathlib/Path root "scripts/seed/check-public-native-product.cljc"))
                               "host" (python/list [(platform/system) (platform/machine) (platform/release)])
                               "legacyRuntimeFallback" false)]
          (.write_text (pathlib/Path out "public-product.json") (u/json-dump report))
          (println (g report "status") "3 aliases, pinned check/compile, native execution and named refusals")
          (.flush sys/stdout))))))

(defn -main [& args]
  (run-main (.resolve (pathlib/Path (or (u/opt args "--product") (sys/exit "--product is required"))))
            (.resolve (pathlib/Path (or (u/opt args "--output") (sys/exit "--output is required"))))
            (.resolve (pathlib/Path (or (u/opt args "--complete") (sys/exit "--complete is required"))))))

(when (some #(or (= % "check-public-native-product.cljc") (str/ends-with? % "/check-public-native-product.cljc")) sys/argv)
  (apply -main *command-line-args*))
