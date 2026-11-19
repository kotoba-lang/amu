;; Derive the bootstrap descriptors' digests from the Mac gate and cross receipts (JUN-545).
;;
;; Inputs are the two receipts and the artifacts they name; no digest is passed by hand. The writer re-hashes every
;; artifact it reads, checks the receipts against each other, and refuses on any mismatch. It does not build or run
;; a compiler. Phases: --phase source (root.json takes the new fullSource/packagerSource/expected fixed point; the
;; compiler pin stays the previous root) and --phase final (default; everything: root.json, the aarch64 Linux root,
;; native-product.json and examples/foundation-starter/candidate.json). Modes: --check (default) reports which
;; fields differ and exits 1 if any; --write rewrites the files; --install (with --write) also copies the verified
;; artifacts to the paths the descriptors name. Ported from write-bootstrap-descriptors.py (Basilisp, JUN-974); the
;; full contract is documented there.
;; Run: basilisp run -p scripts/seed scripts/seed/write-bootstrap-descriptors.cljc -- --mac-build DIR
;;      [--cross-build DIR] [--phase source|final] [--repo DIR] [--install] [--check|--write]
(ns write-bootstrap-descriptors
  (:require [basilisp.string :as str]
            [gate-util :as u])
  (:import hashlib json operator os pathlib sys))

(def mac-receipt "mac-aiueos-user-target.json")
(def cross-receipt "cross.json")

(defn refuse [m] (throw (ex-info m {:refused true})))
(defn need [c m] (when-not c (refuse m)))

(defn g [m & ks] (reduce (fn [a k] (operator/getitem a k)) m ks))
(defn has? [m k] (operator/contains m k))
(defn put! [m k v] (operator/setitem m k v) m)
(defn p [& parts] (apply pathlib/Path parts))
(defn neq [a b] (not (u/deq a b)))

(defn sha
  "[hex size] of a file, read in 1 MiB blocks."
  [path]
  (let [h (hashlib/sha256)]
    (with-open [stream (.open path "rb")]
      (loop []
        (let [block (.read stream 1048576)]
          (when (pos? (python/len block)) (.update h block) (recur)))))
    [(.hexdigest h) (.-st_size (.stat path))]))

(defn load-json [path]
  (try (json/loads (.read_text path ** :encoding "utf-8"))
       (catch python/Exception e (refuse (str "cannot read " path ": " e)))))

(defn pin
  "The file at path must have exactly the receipt's digest and size."
  [path expected what]
  (need (.is_file path) (str what ": " (.-name path) " is missing"))
  (let [[digest size] (sha path)]
    (need (and (= digest (g expected "sha256")) (= size (g expected "bytes")))
          (str what ": " (.-name path) " is " (subs digest 0 12) "/" size ", the receipt says "
               (subs (g expected "sha256") 0 12) "/" (g expected "bytes")))
    (u/pydict "bytes" size "sha256" digest)))

(defn pk-pin [mac-dir]
  (let [[d s] (sha (p mac-dir "P1-signed.macho"))] (u/pydict "bytes" s "sha256" d)))

(defn fixed-point [mac]
  (let [gens (g mac "generations")
        fp (g mac "fixedPointGeneration")]
    (need (and (int? fp) (<= 2 fp (python/len gens))) "fixedPointGeneration")
    (let [last- (operator/getitem gens (dec fp)) prev (operator/getitem gens (- fp 2))]
      (doseq [k ["container" "raw" "unsigned"]]
        (need (u/deq (g last- k) (g prev k)) (str "F" (dec fp) " and F" fp " differ in " k ": not a fixed point")))
      [fp last-])))

(defn derive-source [mac-dir]
  (let [mac (load-json (p mac-dir mac-receipt))]
    (need (= (.get mac "schema") "amu.mac-aiueos-user-target.v3") "mac receipt schema")
    (need (= (.get mac "status") "PASS_MAC_NATIVE_USER_TARGET_SELFHOST") "mac gate did not pass")
    (let [[fp last-] (fixed-point mac)
          ps (g mac "packagerSelfRebuild")]
      (need (u/deq (g ps "unsigned") (g ps "repackagedUnsigned")) "packager did not repackage itself byte for byte")
      (pin (p mac-dir (str "F" fp "-signed.macho")) (g last- "signed") (str "F" fp " signed compiler"))
      (pin (p mac-dir (str "F" fp "-unsigned.macho")) (g last- "unsigned") (str "F" fp " unsigned compiler"))
      (pin (p mac-dir "P1-unsigned.macho") (g ps "unsigned") "packager unsigned")
      (let [pk (pk-pin mac-dir)]
        {:install [[(p mac-dir "P1-signed.macho") "seed/bootstrap/aarch64-macos/kotoba-packager-root.macho" pk]]
         :root (u/pydict "fullSource" (python/dict (g mac "source")) "packagerSource" (python/dict (g ps "source"))
                         "packager" pk "container" (g last- "container" "sha256")
                         "packagerUnsigned" (g ps "unsigned" "sha256"))}))))

(defn derive [mac-dir cross-dir]
  (let [mac (load-json (p mac-dir mac-receipt))
        cross (load-json (p cross-dir cross-receipt))]
    (need (= (.get mac "schema") "amu.mac-aiueos-user-target.v3") "mac receipt schema")
    (need (= (.get mac "status") "PASS_MAC_NATIVE_USER_TARGET_SELFHOST") "mac gate did not pass")
    (need (= (.get cross "schema") "amu.mac-cross-linux-candidates.v1") "cross receipt schema")
    (need (#{"MAC_NATIVE_CROSS_ARTIFACTS_UNEXECUTED" "MAC_NATIVE_CROSS_CANDIDATES_UNADOPTED"} (.get cross "status")) "cross gate status")
    (need (false? (.get cross "linuxProcessInThisGate")) "cross receipt records a Linux process")
    (pin (p mac-dir mac-receipt) (g cross "macSelfhostReport") "cross receipt names the mac receipt")
    (let [[fp last-] (fixed-point mac)]
      (need (u/deq (g cross "container") (g last- "container")) "cross container is not the fixed-point container")
      (need (u/deq (g cross "producer") (g last- "signed")) "cross producer is not the mac gate's fixed-point compiler")
      (need (u/deq (g cross "fullSource" "unity") (g mac "source")) "cross and mac gates saw different sources")
      (need (u/deq (g cross "fullSource" "manifest") (g mac "manifest")) "cross and mac gates saw different manifests")
      (let [ps (g mac "packagerSelfRebuild")]
        (need (u/deq (g ps "unsigned") (g ps "repackagedUnsigned")) "packager did not repackage itself byte for byte")
        (let [compiler (pin (p mac-dir (str "F" fp "-signed.macho")) (g last- "signed") (str "F" fp " signed compiler"))
              _ (pin (p mac-dir (str "F" fp "-unsigned.macho")) (g last- "unsigned") (str "F" fp " unsigned compiler"))
              _ (pin (p mac-dir "P1-unsigned.macho") (g ps "unsigned") "packager unsigned")
              pk (pk-pin mac-dir)
              arm (pin (p cross-dir "F-aarch64.elf") (g cross "aarch64Root") "aarch64 root")
              x86 (pin (p cross-dir "F-x86_64.elf") (g cross "x86FullCompiler") "x86_64 full compiler")
              host (pin (p cross-dir "H-x86_64.elf") (g cross "x86HostEntry") "x86_64 host entry")]
          (need (neq host x86) "the x86_64 host entry is the root image")
          {:install [[(p mac-dir (str "F" fp "-signed.macho")) "seed/bootstrap/aarch64-macos/amu-full-root.macho" compiler]
                     [(p mac-dir "P1-signed.macho") "seed/bootstrap/aarch64-macos/kotoba-packager-root.macho" pk]
                     [(p cross-dir "F-aarch64.elf") "seed/bootstrap/aarch64-linux-static-root.elf" arm]
                     [(p cross-dir "F-x86_64.elf") "bin/amu-linux-x86_64" x86]
                     [(p cross-dir "H-x86_64.elf") "bin/x86_64-linux/amu" host]]
           :root (u/pydict "compiler" compiler "packager" pk "fullSource" (python/dict (g mac "source"))
                           "packagerSource" (python/dict (g ps "source")) "container" (g last- "container" "sha256")
                           "packagerUnsigned" (g ps "unsigned" "sha256"))
           :linux (u/pydict "image" arm "sourceUnity" (python/dict (g cross "fullSource" "unity"))
                            "macContainer" (python/dict (g cross "container")))
           :product (u/pydict "image" x86 "hostImage" host "rootImage" arm
                              "sourceUnity" (python/dict (g cross "fullSource" "unity"))
                              "sourceModuleCount" (g cross "fullSource" "modules"))})))))

(defn updated [old new which phase]
  (let [doc (json/loads (json/dumps old))]
    (cond
      (and (= which :root) (= phase "source"))
      (do (when (not= (g doc "packagerSource" "sha256") (g new "packagerSource" "sha256"))
            (.update (g doc "packager") (g new "packager")))
          (.update (g doc "fullSource") (g new "fullSource"))
          (.update (g doc "packagerSource") (g new "packagerSource"))
          (put! (g doc "expectedFixedPoint") "compilerContainerSha256" (g new "container"))
          (put! (g doc "expectedFixedPoint") "packagerUnsignedSha256" (g new "packagerUnsigned")))

      (= which :root)
      (do (.update (g doc "compiler") (g new "compiler"))
          (.update (g doc "packager") (g new "packager"))
          (.update (g doc "fullSource") (g new "fullSource"))
          (.update (g doc "packagerSource") (g new "packagerSource"))
          (put! (g doc "expectedFixedPoint") "compilerContainerSha256" (g new "container"))
          (put! (g doc "expectedFixedPoint") "packagerUnsignedSha256" (g new "packagerUnsigned"))
          (put! (g doc "qualification") "sourceFixedPointOnMac" true)
          (put! (g doc "qualification") "packagerFixedPointOnMac" true))

      (= which :linux)
      (do (.update (g doc "image") (g new "image"))
          (.update (g doc "sourceUnity") (g new "sourceUnity"))
          (.update (g doc "producedBy" "macFixedPointContainer") (g new "macContainer")))

      (= which :product)
      (let [changed (or (neq (g doc "image") (g new "image"))
                        (neq (g doc "hostEntry" "image") (g new "hostImage"))
                        (neq (g doc "sourceUnity") (g new "sourceUnity")))]
        (.update (g doc "image") (g new "image"))
        (.update (g doc "hostEntry" "image") (g new "hostImage"))
        (.update (g doc "rootImage") (g new "rootImage"))
        (.update (g doc "sourceUnity") (g new "sourceUnity"))
        (put! doc "sourceModuleCount" (g new "sourceModuleCount"))
        (when changed
          (put! doc "sourceRevision" nil)
          (put! doc "compilerGenerations" (python/list))
          (doseq [f ["nativePinnedCheckAndCompile" "controllerQualified" "currentCompilerLinkVerified" "broaderPublicCompatibilityQualified"]]
            (put! doc f false))
          (put! doc "qualificationState" "Changed compiler/source candidate: source revision binding and current native qualification pending.")))

      (= which :starter)
      (let [changed (or (neq (g doc "compilerImage") (g new "image"))
                        (neq (g doc "compilerSourceUnity") (g new "sourceUnity")))]
        (put! doc "compilerImage" (python/dict (g new "image")))
        (put! doc "compilerSourceUnity" (python/dict (g new "sourceUnity")))
        (when changed
          (put! doc "upstreamRevision" nil)
          (put! doc "publicReleaseReady" false)
          (let [evidence (.get doc "compilerEvidence")]
            (when (some? evidence)
              (put! evidence "sameCompilerBytesAndSourceUnity" false)
              (put! evidence "descriptorQualificationFlagsStillFalse" true)
              (put! evidence "scope" "Historical compiler; new candidate requires source binding and native qualification")))))
      :else nil)
    doc))

(defn flat
  "[path value] leaves of a JSON document, in document order."
  [o prefix]
  (if (instance? python/dict o)
    (mapcat (fn [[k v]] (flat v (str prefix "." k))) (.items o))
    [[prefix o]]))

(defn pystr [x]
  (cond (nil? x) "None" (true? x) "True" (false? x) "False" :else (python/str x)))

(defn run [args]
  (let [mac-build (u/opt args "--mac-build")
        cross-build (u/opt args "--cross-build")
        phase (or (u/opt args "--phase") "final")
        repo (p (or (u/opt args "--repo") (str u/root)))
        install? (boolean (some #{"--install"} args))
        write? (boolean (some #{"--write"} args))
        files (atom {:root (p repo "seed/bootstrap/aarch64-macos/root.json")
                     :linux (p repo "seed/bootstrap/aarch64-linux-static-root.json")
                     :product (p repo "native-product.json")})]
    (when-not mac-build (sys/exit "--mac-build is required"))
    (when-not (#{"source" "final"} phase) (sys/exit "--phase must be source or final"))
    (when (and write? (some #{"--check"} args)) (sys/exit "--check and --write are mutually exclusive"))
    (let [new (try
                (if (= phase "source")
                  (let [n (derive-source (p mac-build))]
                    (swap! files select-keys [:root])
                    n)
                  (do (need (some? cross-build) "--cross-build is required in the final phase")
                      (let [n (derive (p mac-build) (p cross-build))
                            starter (p repo "examples/foundation-starter/candidate.json")]
                        (if (.is_file starter)
                          (do (swap! files assoc :starter starter) (assoc n :starter (:product n)))
                          n))))
                (catch python/Exception e
                  (when-not (and (ex-data e) (:refused (ex-data e))) (throw e))
                  (.write sys/stderr (str "REFUSED: " (ex-message e) "\n"))
                  nil))]
      (cond
        (nil? new) 2
        (and install? (not write?)) (do (.write sys/stderr "REFUSED: --install needs --write\n") 2)
        :else
        (let [packager-changed (and (= phase "source")
                                    (not= (g (load-json (:root @files)) "packagerSource" "sha256")
                                          (g (:root new) "packagerSource" "sha256")))
              differs (atom 0)]
          (doseq [which [:root :linux :product :starter] :when (contains? @files which)]
            (let [path (get @files which)
                  old (load-json path)
                  doc (updated old (get new which) which phase)
                  changes (filter (fn [[[_ a] [k b]]] (neq a b)) (map vector (flat old "") (flat doc "")))]
              (doseq [[[_ a] [k b]] changes]
                (println (str (.-name path) k ": " (subs (pystr a) 0 (min 16 (count (pystr a)))) " -> "
                              (subs (pystr b) 0 (min 16 (count (pystr b)))))))
              (swap! differs + (count changes))
              (when (and write? (seq changes))
                (.write_text path (str (json/dumps doc ** :indent 2 :ensure_ascii false) "\n") ** :encoding "utf-8"))))
          (when install?
            (loop [items (:install new)]
              (when (and (seq items) (not (and (= phase "source") (not packager-changed))))
                (let [[src rel expected] (first items)
                      [digest size] (sha src)]
                  (need (and (= digest (g expected "sha256")) (= size (g expected "bytes"))) (str (.-name src) " changed before install"))
                  (let [dst (p repo rel)]
                    (when-not (and (.is_file dst) (= (first (sha dst)) digest))
                      (.mkdir (.-parent dst) ** :parents true :exist_ok true)
                      (let [tmp (.with_name dst (str (.-name dst) ".installing"))]
                        (.write_bytes tmp (.read_bytes src))
                        (.chmod tmp 0755)
                        (.replace tmp dst)
                        (println (str "installed " rel)))))
                  (recur (rest items))))))
          (println (cond (zero? @differs) "DESCRIPTORS_CURRENT" write? "DESCRIPTORS_WRITTEN" :else (str "DESCRIPTORS_DIFFER " @differs)))
          (if (or (zero? @differs) write?) 0 1))))))

(defn -main [& args]
  (try
    (sys/exit (run args))
    (catch python/Exception e
      (if (and (ex-data e) (:refused (ex-data e)))
        (do (.write sys/stderr (str "Refused: " (ex-message e) "\n")) (sys/exit 1))
        (throw e)))))

(when (some #(or (= % "write-bootstrap-descriptors.cljc") (str/ends-with? % "/write-bootstrap-descriptors.cljc")) sys/argv)
  (apply -main *command-line-args*))
