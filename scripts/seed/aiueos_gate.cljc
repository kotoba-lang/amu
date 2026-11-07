;; The compile/refuse skeleton shared by the AIUEOS native gates (JUN-974 port of the repeated `compile_`
;; closure of the Python originals): write a source and its source lock, run the admitted native compiler for
;; x86_64-aiueos-kernel-v1, record the call in calls.json, and assert the expected outcome.
(ns aiueos-gate
  (:require [gate-util :as u])
  (:import operator pathlib struct))

(defn- operator-setitem [d k v] (operator/setitem d k v))

(defn start-scope
  "Create `dir` and the per-compiler state: source, lock, calls and the compiler environment."
  [compiler dir]
  (.mkdir dir)
  {:compiler compiler :dir dir
   :source (.joinpath dir "entry.kotoba") :lock (.joinpath dir "source.ksl")
   :calls (python/list)
   :env (python/dict {"PATH" "/nonexistent" "KEXE_STACK_BYTES" "8388608" "KEXE_CAP_RESOURCES_35" (str dir)})})

(defn compile!
  "Compile `text`; returns [r image]. opts: :pin-source adds the source pin to the call row, :source-text adds the
  text. The call is appended to calls.json before any assertion."
  [{:keys [compiler dir source lock calls env]} name text & {:keys [pin-source source-text fuel] :or {fuel "1000000"}}]
  (.write_text source text)
  (.write_text lock (u/ksl-text source dir))
  (let [image (.joinpath dir (str name ".elf"))
        r (u/run-process [compiler "compile" source "--target" "x86_64-aiueos-kernel-v1" "--artifact" "image" "--output" image
                          "--fuel" fuel "--source-path" dir "--source-lock" lock
                          "--source-lock-sha256" (u/geti (u/pin lock) "sha256")]
                         env 240)
        row (u/pydict "name" name "exit" (.-returncode r) "stderr" (.decode (.-stderr r)))]
    (when pin-source (operator-setitem row "source" (u/pin source)))
    (when source-text (operator-setitem row "sourceText" text))
    (.append calls row)
    (.write_text (.joinpath dir "calls.json") (u/json-dump calls))
    [r image]))

(defn last-call [scope] (u/geti (:calls scope) -1))

(defn refusal!
  "Compile `text` and assert the compiler refuses it with `code` and writes no image."
  [scope name text code & opts]
  (let [[r image] (apply compile! scope name text opts)]
    (u/chk (and (= 1 (.-returncode r)) (u/has-bytes? (.encode code) (.-stderr r)) (not (.exists image))) (last-call scope))
    nil))

(defn success!
  "Compile `text` and assert it succeeds silently; returns the image path."
  [scope name text & opts]
  (let [[r image] (apply compile! scope name text opts)]
    (u/chk (and (zero? (.-returncode r)) (not (u/nonempty? (.-stderr r))) (.exists image)) (last-call scope))
    image))

(defn package-efi!
  "Run package-aiueos-boot on `image`; returns the efi path after asserting a silent success."
  [{:keys [compiler dir env]} name image & {:keys [pci] :or {pci true}}]
  (let [efi (.joinpath dir (str name ".efi"))
        q (u/run-process (concat [compiler "package-aiueos-boot" image "--output" efi] (when pci ["--pci-resources" "v1"])) env 180)]
    (u/chk (and (zero? (.-returncode q)) (not (u/nonempty? (.-stderr q)))) (.-stderr q))
    efi))

(defn case!
  "One named case: with :refuse CODE the compiler must refuse; otherwise it must succeed, the image is packaged
  (with --pci-resources v1 only when :pci) and {kernel, efi} pins are recorded in `artifacts` under `name`."
  [scope artifacts name text & {:keys [refuse pci] :as opts}]
  (let [copts (mapcat identity (select-keys opts [:pin-source :source-text]))]
    (if refuse
      (apply refusal! scope name text refuse copts)
      (let [image (apply success! scope name text copts)
            efi (package-efi! scope name image :pci (boolean pci))]
        (operator/setitem artifacts name (u/pydict "kernel" (u/pin image) "efi" (u/pin efi)))))))

(defn unpack [fmt b off] (struct/unpack_from fmt b off))
(defn u64-at [b off] (u/geti (unpack "<Q" b off) 0))
(defn ph-rx [b] (unpack "<IIQQQQQQ" b 64))
(defn ph-rw [b] (unpack "<IIQQQQQQ" b 120))

(defn finish!
  "Write `report` (a Python dict) as out/file and print its status."
  [out file report]
  (.write_text (.joinpath out file) (u/json-dump report))
  (println (u/geti report "status")))

(defn load-source-var
  "Load a hyphenated sibling gate file (as the Python originals did with runpy) and return the value of `sym`
  in its namespace (a qualified symbol like 'check-aiueos-value-call-native/source)."
  [file sym]
  (load-file (str (.joinpath u/root (str "scripts/seed/" file))))
  @(resolve sym))
