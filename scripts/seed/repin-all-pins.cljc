;; Regenerate and verify every derived pin a seed PR can make stale (JUN-759).
;;
;; repin-derived-pins covers the bootstrap roots, Linux images, product descriptors and the Mac CLI. This command
;; adds the two pin kinds it does not: core adoption (seed/<adoption receipt> and seed/compiler-core.json, computed
;; by the Mac fixed point) and native CDCI (seed/cdci/policy.json, the controller pin rows, the 24 case image rows
;; of seed/cdci/kotoba-gate.kotoba and the two role source hashes in seed/79-native-cdci.kotoba).
;; Write mode (default, Mac arm64, ~8 minutes): --merge origin/main merges, resolves pin/derived conflicts
;; mechanically (anything else is owner work, exit 12), then repeats repin-derived-pins + this sync until a fixed
;; point. Check mode (--check) never writes the tree. Exit codes: 0 current, 10 CDCI pins stale, 11 core adoption
;; stale, 12 owner-authored content needed, 2 environment/usage. Native only. Ported from repin-all-pins.py
;; (Basilisp, JUN-974); the Python docstring has the full contract. Run from the repository root:
;; basilisp run -p scripts/seed scripts/seed/repin-all-pins.cljc -- [--root DIR] [--check] [--merge REF]
;;   [--mac-build DIR] [--work DIR] [--report-receipts] [--rounds N]
(ns repin-all-pins
  (:require [basilisp.string :as str]
            [gate-util :as u]
            [macos-native-lib :as mac])
  (:import hashlib json operator os pathlib platform re shutil subprocess sys tempfile))

(def seed (pathlib/Path u/root "scripts/seed"))
(def exit-cdci 10) (def exit-core 11) (def exit-owner 12) (def exit-env 2)

(def pin-files
  ["bin/amu-linux-x86_64" "bin/x86_64-linux/amu"
   "examples/foundation-starter/MACOS-ARM64.md" "examples/foundation-starter/candidate.json"
   "native-product.json" "seed/bootstrap/aarch64-linux-static-root.elf"
   "seed/bootstrap/aarch64-linux-static-root.json" "seed/bootstrap/aarch64-macos/amu-cli.macho"
   "seed/bootstrap/aarch64-macos/amu-full-root.macho" "seed/bootstrap/aarch64-macos/cli.json"
   "seed/bootstrap/aarch64-macos/root.json" "seed/bootstrap/aarch64-macos/kotoba-packager-root.macho"])
(def derived-files ["seed/cdci/policy.json" "seed/cdci/controller.kotoba" "seed/cdci/kotoba-gate.kotoba" "seed/compiler-core.json"])
(def role-line (re/compile "^.*\\(string=\\? role \"[a-z-]+\"\\) \"[0-9a-f]{64}\".*$" re/M))

(defn g [m & ks] (reduce (fn [a k] (operator/getitem a k)) m ks))
(defn p [& parts] (apply pathlib/Path parts))
(defn sha [data] (u/sha256-hex data))
(defn owner [m] (throw (ex-info m {:owner true})))
(defn read-json [path] (json/loads (.read_text path)))
(defn word
  "Eight hex characters as the little-endian 64-bit literal the rows use."
  [h8]
  (str "0x" (.hex (operator/getitem (.encode h8) (python/slice nil nil -1)))))
(defn sub-fn [pattern f s & {:keys [count flags] :or {count 0}}] (.sub (re/compile pattern) f s ** :count count))

(defn git [root args & {:keys [check] :or {check true}}]
  (let [r (subprocess/run (python/list (concat ["git" "-C" (str root)] args)) ** :capture_output true :text true)]
    (when (and check (not= (.-returncode r) 0))
      (throw (python/RuntimeError (str "git " (str/join " " args) ": " (.strip (.-stderr r))))))
    r))

;; ---- Sync: {:root :write :stale (atom) :producer :tmp :roles-built (atom) :core-drift (atom)}
(defn make-sync [root mac-build write?]
  (let [root (.resolve (pathlib/Path root))
        report (read-json (p mac-build "mac-aiueos-user-target.json"))
        n (g (operator/getitem (g report "generations") -1) "number")
        producer (p mac-build (str "F" n "-signed.macho"))]
    (when-not (.is_file producer) (owner (str "no Mac fixed point image " producer)))
    (let [tmp (p (tempfile/mkdtemp ** :prefix "repin-all-" :dir (str (.-parent (pathlib/Path mac-build)))))]
      (.chmod tmp 0700)
      {:root root :write write? :stale (atom []) :producer producer :tmp tmp :roles-built (atom true) :core-drift (atom false)})))

(defn spath [s rel] (p (:root s) rel))
(defn modules [s manifest]
  (vec (filter #(and (seq %) (not (.startswith % "#"))) (.splitlines (.read_text (spath s manifest))))))
(defn unity [s manifest]
  (.join (u/bytes-of) (python/list (map #(operator/add (.read_bytes (spath s %)) (u/bytes-of 10)) (modules s manifest)))))
(defn native [s & args] (mac/native-run (:producer s) (:tmp s) (vec args)))
(defn stage [s name data] (.write_bytes (p (:tmp s) name) data))
(defn put [s rel text why]
  (let [path (spath s rel)]
    (when (not= (.read_text path) text)
      (swap! (:stale s) conj [rel why])
      (when (:write s) (.write_text path text)))))
(defn dump [x] (u/json-dump x))

;; ---- core adoption
(defn core [s]
  (let [core-path "seed/compiler-core.json"
        core- (read-json (spath s core-path))
        adoption-rel (g core- "adoptionReceipt")
        adoption (read-json (spath s adoption-rel))
        names (modules s (g adoption "sourceManifest"))]
    (when (not= (count names) (count (set names))) (owner "seed/MANIFEST lists a module twice"))
    (let [sources (python/list
                   (for [name names]
                     (let [pp (pathlib/Path name)]
                       (when (or (.is_absolute pp) (some #{".."} (.-parts pp)) (not= (first (.-parts pp)) "seed"))
                         (owner (str "invalid core source path " name)))
                       (let [d (u/pydict "path" name)] (.update d (mac/require-regular (spath s name))) d))))
          un (unity s (g adoption "sourceManifest"))
          want (u/pydict "bytes" (python/len un) "sha256" (sha un))
          cur (u/pydict "bytes" (g adoption "sourceUnityBytes") "sha256" (g adoption "sourceUnitySHA256"))]
      (if (and (u/deq sources (g adoption "sources")) (u/deq (g adoption "sources") (g core- "sources"))
               (u/deq want cur) (u/deq cur (u/pydict "bytes" (g core- "sourceUnityBytes") "sha256" (g core- "sourceUnitySHA256"))))
        adoption-rel
        (do
          (swap! (:stale s) conj [adoption-rel "core source drift (seed/MANIFEST modules changed): adoption round required"])
          (reset! (:core-drift s) true)
          (if-not (:write s)
            adoption-rel
            (let [desc (read-json (spath s "seed/bootstrap/aarch64-macos/root.json"))
                  packager (spath s (g desc "packager" "path"))
                  tmp (:tmp s)
                  _ (stage s "adopted-unity.kotoba" un)
                  generations (python/list [])]
              (loop [current (:producer s) numbers [1 2 3]]
                (when (seq numbers)
                  (let [number (first numbers)
                        container (str "G" number ".kseed") raw (str "G" number ".bin")
                        unsigned (p tmp (str "G" number "-unsigned.macho")) signed (p tmp (str "G" number "-signed.macho"))]
                    (mac/native-run current tmp ["compile" "adopted-unity.kotoba" "--target" "aarch64-macos" "--output" container])
                    (let [out (mac/native-run current tmp ["extract-native" container "--symbol" "main" "--output" raw])
                          m (re/search (.encode ":offset (\\d+), :length (\\d+), :arity 0}") (.-stdout out))]
                      (when (or (nil? m) (not= (python/int (.group m 2)) (.-st_size (.stat (p tmp raw)))))
                        (owner "core main extraction mismatch"))
                      (mac/native-run packager tmp [(.-name unsigned) raw "fs2-cli-stdio-general" (.decode (.group m 1))])
                      (mac/sign unsigned signed)
                      (.append generations (u/pydict "name" (str "G" number) "native" (mac/pin (p tmp raw)) "container" (mac/pin (p tmp container))))
                      (recur signed (rest numbers))))))
              (let [g0 (operator/getitem generations 0)]
                (when-not (every? (fn [gg] (and (u/deq (g gg "native") (g g0 "native")) (u/deq (g gg "container") (g g0 "container")))) generations)
                  (owner "core source fixed point G1=G2=G3 is absent: the PR's core change does not self-reproduce; fix the source"))
                (.update adoption (u/pydict "sourceUnityBytes" (g want "bytes") "sourceUnitySHA256" (g want "sha256") "sources" sources
                                           "nativeImageBytes" (g g0 "native" "bytes") "nativeImageSHA256" (g g0 "native" "sha256")
                                           "container" (g g0 "container") "generations" generations))
                (.update core- (u/pydict "sourceUnityBytes" (g want "bytes") "sourceUnitySHA256" (g want "sha256") "sources" sources))
                (.write_text (spath s adoption-rel) (dump adoption))
                (.write_text (spath s core-path) (dump core-))
                adoption-rel))))))))

;; ---- native CDCI
(defn cdci [s adoption-rel]
  (let [adoption (read-json (spath s adoption-rel))
        policy-rel "seed/cdci/policy.json"
        policy (read-json (spath s policy-rel))
        new (python/dict policy)
        tmp (:tmp s)
        core-unity (unity s "seed/MANIFEST")]
    (operator/setitem new "coreSourceSHA256" (sha core-unity))
    (operator/setitem new "coreContainerSHA256" (g adoption "container" "sha256"))
    (stage s "core-static.kotoba" (unity s "seed/CORE-STATIC-MANIFEST"))
    (native s "compile" "core-static.kotoba" "--target" "x86_64-linux" "--output" "amu-selfhost.elf" "--format" "static")
    (operator/setitem new "amuSelfhostGateSHA256" (sha (.read_bytes (p tmp "amu-selfhost.elf"))))
    (let [cases (g (read-json (spath s "seed/static-cases.json")) "cases")]
      (when (not= (python/len cases) (g policy "caseCount"))
        (owner "seed/static-cases.json case count differs from policy.caseCount: new cases need owner-authored gate rows"))
      (let [gate-rel "seed/cdci/kotoba-gate.kotoba"
            gtxt (atom (.read_text (spath s gate-rel)))]
        (doseq [[i case] (map-indexed vector cases)]
          (stage s (str "case-" i ".kotoba") (.encode (g case "source")))
          (native s "compile" (str "case-" i ".kotoba") "--target" "x86_64-linux" "--output" (str "case-" i ".elf") "--format" "static")
          (let [vals [["h0" (sha (.encode (g case "source")))] ["h1" (sha (.read_bytes (p tmp (str "case-" i ".elf"))))]]
                m (re/search (str "\\(defn- kg-vector-" i " \\[\\] :i64\\n(.*?)\\n        v0 ") @gtxt re/S)]
            (when-not m (owner (str "kotoba-gate.kotoba has no vector for case " i)))
            (let [block (atom (.group m 1))]
              (doseq [[tag v] vals k (range 8)]
                (let [pat (re/compile (str "(" tag "_" (* k 8) " \\(kc-word \\(\\+ p \\d+\\) )0x[0-9a-f]+( 8\\))"))]
                  (when-not (.search pat @block) (owner (str "kotoba-gate.kotoba vector " i " lacks row " tag "_" (* k 8))))
                  (reset! block (.sub pat (fn [mm] (str (.group mm 1) (word (subs v (* k 8) (* (inc k) 8))) (.group mm 2))) @block ** :count 1))))
              (reset! gtxt (str (subs @gtxt 0 (.start m 1)) @block (subs @gtxt (.end m 1)))))))
        (put s gate-rel @gtxt "case image rows")
        (let [entry (.read_bytes (spath s "seed/cdci/entry.kotoba"))
              runtime (.read_bytes (spath s "seed/cdci/runtime.kotoba"))
              gtxt @gtxt]
          (operator/setitem new "kotobaGateSourceSHA256" (sha (operator/add (operator/add entry runtime) (.encode gtxt))))
          (let [p79-rel "seed/79-native-cdci.kotoba"
                t79 (atom (.read_text (spath s p79-rel)))]
            (reset! t79 (.sub (re/compile "(string=\\? role \"kotoba-native\"\\) \")[0-9a-f]{64}") (fn [m] (str (.group m 1) (sha (.encode gtxt)))) @t79))
            (doseq [[var rel] [["host" "seed/bench/host-arm.kotoba"] ["registry" "seed/bench/registry-arm.kotoba"]]]
              (reset! t79 (.sub (re/compile (str "(string=\\? \\(sh-text " var "\\) \")[0-9a-f]{64}"))
                                (fn [m] (str (.group m 1) (sha (.read_bytes (spath s rel))))) @t79)))
            (stage s "entry.kotoba" entry)
            (stage s "runtime.kotoba" runtime)
            (stage s "kotoba-gate.kotoba" (.encode gtxt))
            (reset! (:roles-built s) true)
            (try
              (native s "cdci-build" "kotoba-native" "entry.kotoba" "runtime.kotoba" "kotoba-gate.kotoba" "kotoba-native.elf")
              (operator/setitem new "kotobaNativeGateSHA256" (sha (.read_bytes (p tmp "kotoba-native.elf"))))
              (catch python/Exception e
                (reset! (:roles-built s) false)
                (swap! (:stale s) conj [p79-rel (str "producer does not yet pin the current role hash (rebuild after sync): " (let [t (str e)] (subs t 0 (min 80 (count t)))))])))
            (let [ctl-rel "seed/cdci/controller.kotoba"
                  ctl (atom (.read_text (spath s ctl-rel)))]
              (doseq [[idx f] (map-indexed vector ["coreSourceSHA256" "coreContainerSHA256" "amuSelfhostGateSHA256" "kotobaNativeGateSHA256" "kotobaGateSourceSHA256"])
                      k (range 8)]
                (let [pat (re/compile (str "(\\bh" idx "_" (* k 8) " \\(kc-word \\(\\+ \\(kc-g\\) " (+ 20100000 (* idx 64) (* k 8)) "\\) )0x[0-9a-f]+( 8\\))"))]
                  (when-not (.search pat @ctl) (owner (str "controller.kotoba lacks pin row h" idx "_" (* k 8))))
                  (reset! ctl (.sub pat (fn [mm] (str (.group mm 1) (word (subs (operator/getitem new f) (* k 8) (* (inc k) 8))) (.group mm 2))) @ctl ** :count 1))))
              (put s ctl-rel @ctl "controller pin rows")
              (reset! t79 (.sub (re/compile "(string=\\? role \"controller\"\\) \")[0-9a-f]{64}") (fn [m] (str (.group m 1) (sha (.encode @ctl)))) @t79))
              (put s p79-rel @t79 "role source hashes")
              (put s policy-rel (dump new) "policy pins")
              (when @(:roles-built s)
                (stage s "controller.kotoba" (.encode @ctl))
                (try
                  (native s "cdci-build" "controller" "entry.kotoba" "runtime.kotoba" "controller.kotoba" "controller.elf")
                  (catch python/Exception e
                    (reset! (:roles-built s) false)
                    (swap! (:stale s) conj [p79-rel (str "controller role is not pinned in the producer: " (let [t (str e)] (subs t 0 (min 80 (count t)))))])))))))))))

(defn run-sync [s]
  (reset! (:core-drift s) false)
  (let [adoption-rel (core s)]
    (cdci s adoption-rel)
    (shutil/rmtree (:tmp s) ** :ignore_errors true)
    [@(:stale s) @(:roles-built s)]))

(defn build-mac-fixed-point [root out]
  (subprocess/run (python/list [(str (p "basilisp")) "run" "-p" (str seed) (str (p seed "check-aiueos-user-macos-native.cljc")) "--" "--output" (str (p out "mac-root"))])
                  ** :cwd root :check true)
  (p out "mac-root"))

(defn merge- [root ref]
  (let [r (git root ["merge" "--no-edit" ref] :check false)]
    (when-not (= (.-returncode r) 0)
      (let [left (atom [])]
        (doseq [f (.split (.-stdout (git root ["diff" "--name-only" "--diff-filter=U"])))]
          (cond
            (or (some #{f} pin-files) (some #{f} derived-files) (re/fullmatch "seed/adoption-[^/]+\\.json" f))
            (git root ["checkout" ref "--" f])
            (= f "seed/79-native-cdci.kotoba")
            (let [base (.strip (.-stdout (git root ["merge-base" "HEAD" ref])))
                  parts (for [r- ["HEAD" base ref]] (.sub role-line "ROLE-HASH-LINE" (.-stdout (git root ["show" (str r- ":" f)]))))]
              (let [d (tempfile/TemporaryDirectory)
                    dname (.__enter__ d)]
                (try
                  (let [files (vec (for [[name text] (map vector ["ours" "base" "theirs"] parts)]
                                     (do (.write_text (p dname name) text) (str (p dname name)))))
                        m (subprocess/run (python/list (concat ["git" "merge-file" "-p"] files)) ** :capture_output true :text true)]
                    (if (not= (.-returncode m) 0)
                      (swap! left conj f)
                      (.write_text (p root f) (.-stdout m))))
                  (finally (.__exit__ d nil nil nil)))))
            :else (swap! left conj f)))
        (when (seq @left)
          (owner (str "merge conflicts outside the mechanical set (pin files, derived CDCI/adoption files, seed/79 hash lines): " (str/join " " @left))))
        (let [p79 (p root "seed/79-native-cdci.kotoba")]
          (when (str/includes? (.read_text p79) "ROLE-HASH-LINE")
            (let [canon (.-stdout (git root ["show" (str ref ":seed/79-native-cdci.kotoba")]))
                  lines (re/findall (re/compile "^.*\\(string=\\? role \"[a-z-]+\"\\) \"[0-9a-f]{64}\".*$" re/M) canon)]
              (.write_text p79 (reduce (fn [text line] (.replace text "ROLE-HASH-LINE" line 1)) (.read_text p79) lines)))))
        (git root ["add" "-A"])
        (git root ["-c" "core.editor=true" "commit" "--no-edit"])))))

(defn report-receipts [root]
  (let [found (atom 0)]
    (doseq [f (.split (.-stdout (git root ["ls-files" "docs"])))
            :when (.endswith f ".json")]
      (when-let [data (try (read-json (p root f)) (catch python/Exception _ nil))]
        (loop [stack [data]]
          (when (seq stack)
            (let [x (peek stack) stack (pop stack)]
              (cond
                (instance? python/dict x)
                (let [pp (.get x "path") h (.get x "sha256")]
                  (when (and (string? pp) (string? h) (.is_file (p root pp)) (not= (sha (.read_bytes (p root pp))) h))
                    (println "drifted receipt pin:" f pp)
                    (swap! found inc))
                  (recur (into stack (python/list (.values x)))))
                (instance? python/list x) (recur (into stack x))
                :else (recur stack)))))))
    (println (str @found " historical receipt pins differ from the current tree (not regenerated; see AGENTS.md)"))))

(defn report [stale check?]
  (doseq [[rel why] stale] (println (str (if check? "STALE " "REGENERATED ") rel ": " why))))

(defn run [args]
  (let [root (.resolve (p (or (u/opt args "--root") (str u/root))))
        check? (boolean (some #{"--check"} args))
        merge-ref (u/opt args "--merge")
        mac-build (u/opt args "--mac-build")
        work-arg (u/opt args "--work")
        rounds (python/int (or (u/opt args "--rounds") "5"))]
    (if-not (and (= (platform/system) "Darwin") (= (platform/machine) "arm64"))
      (do (.write sys/stderr "derived pins are produced on Mac arm64\n") exit-env)
      (if (some #{"--report-receipts"} args)
        (do (report-receipts root) 0)
        (let [work (if work-arg (p work-arg) (p (tempfile/mkdtemp ** :prefix "repin-all-")))]
          (.mkdir work ** :parents true :exist_ok true)
          (try
            (if check?
              (let [mac- (if mac-build (p mac-build) (build-mac-fixed-point root work))
                    [stale roles] (run-sync (make-sync root (.resolve mac-) false))]
                (report stale true)
                (if (and (empty? stale) roles)
                  (do (println "PASS_ALL_PINS_CURRENT") 0)
                  (let [core? (boolean (some (fn [[_ why]] (str/includes? why "core source drift")) stale))]
                    (.write sys/stderr "FAIL_STALE_PINS: run scripts/seed/repin-all-pins.py --merge origin/main\n")
                    (if core? exit-core exit-cdci))))
              (do
                (when merge-ref (merge- root merge-ref))
                (loop [i 1]
                  (if (> i rounds)
                    (do (.write sys/stderr "FAIL_NO_FIXED_POINT: pins did not converge; owner review needed\n") exit-owner)
                    (let [w (p work (str "round-" i))
                          cmd (concat [(str "basilisp") "run" "-p" (str seed) (str (p seed "repin-derived-pins.cljc")) "--" "--work" (str w)]
                                      (when (and (= i 1) merge-ref) ["--take-pins-from" merge-ref]))]
                      (subprocess/run (python/list cmd) ** :cwd root :check true)
                      (let [[stale roles] (run-sync (make-sync root (p w "mac-root") true))]
                        (report stale false)
                        (if (and (empty? stale) roles)
                          (do (git root (concat ["add" "-A" "--"] pin-files ["seed/cdci" "seed/79-native-cdci.kotoba" "seed/compiler-core.json" "seed/adoption-*.json"]) :check false)
                              (println (str "PASS_ALL_PINS_FIXED_POINT after " i " round(s); review `git status` and commit"))
                              0)
                          (recur (inc i)))))))))
            (catch python/Exception e
              (if (and (ex-data e) (:owner (ex-data e)))
                (do (.write sys/stderr (str "OWNER_AUTHORED_CONTENT_NEEDED: " (ex-message e) "\n")) exit-owner)
                (throw e)))))))))

(defn -main [& args] (sys/exit (run args)))

(when (some #(or (= % "repin-all-pins.cljc") (str/ends-with? % "/repin-all-pins.cljc")) sys/argv)
  (apply -main *command-line-args*))
