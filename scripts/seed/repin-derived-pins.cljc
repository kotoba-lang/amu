;; Regenerate every derived seed pin for the current tree in one command.
;;
;; JUN-631 / ADR 0388. Derived pins (compiler images, descriptors, the public Mac CLI) are outputs of the seed
;; sources. A seed PR that is behind main must never hand-resolve them: merge main, take main's side of each pin
;; file (--take-pins-from FETCH_HEAD), then run this to rebuild all of them on the merged source with the
;; repository's own two-phase writer. Mac arm64 only; the native compiler does the work, this stages and hashes.
;; Ported from repin-derived-pins.py (Basilisp, JUN-974); every sub-gate it launches is the Basilisp port.
;; Run (repo root): basilisp run -p scripts/seed scripts/seed/repin-derived-pins.cljc -- [--take-pins-from REF] [--work DIR]
(ns repin-derived-pins
  (:require [basilisp.string :as str]
            [gate-util :as u]
            [macos-scope-build :as scope])
  (:import hashlib json operator pathlib platform shutil subprocess sys tempfile))

(def root u/root)
(def seed (pathlib/Path root "scripts/seed"))
(def pins
  ["bin/amu-linux-x86_64" "bin/x86_64-linux/amu" "examples/foundation-starter/MACOS-ARM64.md"
   "examples/foundation-starter/candidate.json" "native-product.json" "seed/bootstrap/aarch64-linux-static-root.elf"
   "seed/bootstrap/aarch64-linux-static-root.json" "seed/bootstrap/aarch64-macos/amu-cli.macho"
   "seed/bootstrap/aarch64-macos/amu-full-root.macho" "seed/bootstrap/aarch64-macos/kotoba-packager-root.macho"
   "seed/bootstrap/aarch64-macos/cli.json" "seed/bootstrap/aarch64-macos/root.json"])

(defn rp [rel] (pathlib/Path root rel))
(defn g [m & ks] (reduce (fn [a k] (operator/getitem a k)) m ks))
(defn die [m] (sys/exit m))
(defn sha [path] (u/sha256-hex (.read_bytes (pathlib/Path path))))
(defn pin [path] (u/pydict "bytes" (.-st_size (.stat (pathlib/Path path))) "sha256" (sha path)))
(defn read-json [p] (json/loads (.read_text p)))

(defn run [& args]
  (println "+" (str/join " " (map str args)))
  (.flush sys/stdout)
  (subprocess/run (python/list (map str args)) ** :cwd root :check true))

(defn git [& args]
  (.decode (.-stdout (subprocess/run (python/list (concat ["git" "-C" (str root)] args)) ** :check true :stdout subprocess/PIPE))))

(defn bl
  "Run a Basilisp port of a seed script: basilisp run -p SEED SEED/file -- args."
  [file & args]
  (apply run "basilisp" "run" "-p" seed (pathlib/Path seed file) "--" args))

(defn stage-changed-packager
  "Bootstrap a changed packager before the source gate validates it."
  [compiler packager out]
  (let [rt (read-json (rp "seed/bootstrap/aarch64-macos/root.json"))
        source (rp "seed/macos-fs2-runtime-packager.kotoba")]
    (if (u/deq (pin source) (u/pydict-from (for [k ["bytes" "sha256"]] [k (g rt "packagerSource" k)])))
      packager
      (let [folder (pathlib/Path out "packager-stage")]
        (.mkdir folder ** :parents true :exist_ok false)
        (scope/build compiler packager folder "candidate-packager" source)))))

(defn take-pins [ref]
  (doseq [path pins] (git "checkout" ref "--" path))
  (let [left (.split (git "diff" "--name-only" "--diff-filter=U"))]
    (when (pos? (python/len left)) (die (str "unresolved non-pin conflicts: " (str/join " " left))))))

(defn repin-cli [out]
  (let [build (read-json (pathlib/Path out "cli/cli-build.json"))
        cli-path (rp "seed/bootstrap/aarch64-macos/cli.json")
        cli (read-json cli-path)
        rt (read-json (rp "seed/bootstrap/aarch64-macos/root.json"))
        names (loop [ls (filter #(and (seq %) (not (.startswith % "#"))) (.splitlines (.read_text (rp "seed/FULL-MANIFEST")))) acc []]
                (if-let [name (first ls)]
                  (if (= name "seed/90-drv.kotoba") (conj acc name) (recur (rest ls) (conj acc name)))
                  acc))
        names (into names ["seed/macos-cli-api.kotoba" "seed/macos-cli.kotoba"])
        expected (u/pydict-from (for [n names] [n (pin (rp n))]))]
    (when (or (not= (count names) (count (set names))) (not (u/deq (g build "sources") expected)))
      (die "CLI build sources do not match the current manifest and source bytes"))
    (operator/setitem cli "sources" expected)
    (let [old (g cli "image" "sha256")
          image (rp (g cli "image" "path"))]
      (shutil/copyfile (pathlib/Path out "cli/amu-cli.macho") image)
      (.chmod image 0755)
      (.update (g cli "image") (pin image))
      (operator/setitem cli "unsigned" (pin (pathlib/Path out "cli/amu-cli-unsigned.macho")))
      (operator/setitem cli "compiler" (g rt "compiler"))
      (operator/setitem cli "packager" (g rt "packager"))
      (operator/setitem cli "unity" (g build "unity"))
      (.write_text cli-path (u/json-dump cli))
      (let [md (rp "examples/foundation-starter/MACOS-ARM64.md")
            text (.read_text md)]
        (when-not (str/includes? text old) (die "MACOS-ARM64.md does not name the previous CLI digest"))
        (.write_text md (.replace text old (g cli "image" "sha256")))))))

(defn -main [& args]
  (let [take-from (u/opt args "--take-pins-from")
        work (u/opt args "--work")]
    (when-not (and (= (platform/system) "Darwin") (= (platform/machine) "arm64")) (die "derived pins are produced on Mac arm64"))
    (when take-from (take-pins take-from))
    (let [out (if work (pathlib/Path work) (pathlib/Path (tempfile/mkdtemp ** :prefix "amu-repin-")))
          compiler (rp "seed/bootstrap/aarch64-macos/amu-full-root.macho")
          packager (rp "seed/bootstrap/aarch64-macos/kotoba-packager-root.macho")
          source-packager (stage-changed-packager compiler packager out)
          o (fn [n] (pathlib/Path out n))]
      ;; Phase source: the pinned root compiles the new sources.
      (bl "check-aiueos-user-macos-native.cljc" "--compiler-image" compiler "--compiler-sha256" (sha compiler)
          "--packager-image" source-packager "--packager-sha256" (sha source-packager) "--output" (o "mac-root-src"))
      (bl "write-bootstrap-descriptors.cljc" "--mac-build" (o "mac-root-src") "--phase" "source" "--install" "--write")
      ;; Phase final: the new root reproduces itself and the Linux candidates.
      (bl "check-aiueos-user-macos-native.cljc" "--output" (o "mac-root"))
      (bl "check-macos-cross-linux-candidates.cljc" "--mac-build" (o "mac-root") "--output" (o "mac-cross") "--produce-candidates")
      (bl "write-bootstrap-descriptors.cljc" "--mac-build" (o "mac-root") "--cross-build" (o "mac-cross") "--phase" "final" "--install" "--write")
      (bl "build-macos-cli.cljc" "--output" (o "cli"))
      (repin-cli out)
      (bl "check-public-macos-product.cljc" "--output" (o "public"))
      (bl "write-bootstrap-descriptors.cljc" "--mac-build" (o "mac-root") "--cross-build" (o "mac-cross") "--phase" "final" "--check")
      (apply git "add" "--" pins)
      (println "REPINNED" (str out)))))

(when (some #(or (= % "repin-derived-pins.cljc") (str/ends-with? % "/repin-derived-pins.cljc")) sys/argv)
  (apply -main *command-line-args*))
