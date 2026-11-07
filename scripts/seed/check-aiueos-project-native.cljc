;; Observe locked native project linking; no compiler or CDCI verdict here.
;; Ported from check-aiueos-project-native.py (Basilisp). Linux only.
;; Run: basilisp run scripts/seed/check-aiueos-project-native.cljc -- (--build DIR | --complete DIR) --output OUT
(ns check-aiueos-project-native
  (:require [aiueos-gate :as g]
            [aiueos-native-proof :as proof]
            [basilisp.string :as str]
            [gate-util :as u])
  (:import sys))

(def entry-src "(ns entry (:require [lib.left :as l] [lib.right :as r]) (:export [main]))\n(defn main [] :i64 (+ (l/run 20) (r/run 20)))\n")
(def left-src "(ns lib.left (:require [lib.base :as b]) (:export [run unused]))\n(defn run [x :i64] :i64 (b/plus-one x))\n(defn unused [x :i64] :i64 (- x 1))\n")
(def right-src "(ns lib.right (:require [lib.base :refer [plus-one]]) (:export [run]))\n(defn run [x :i64] :i64 (plus-one x))\n")
(def base-src "(ns lib.base (:export [plus-one]))\n(defn- add [x :i64] :i64 (+ x 1))\n(defn plus-one [x :i64] :i64 (add x))\n")

(defn main [build complete output]
  (let [[source producers _] (proof/load-native-producers :build build :complete complete)
        _ (.mkdir output ** :parents true :exist_ok false)
        verify (g/load-source-var "check-aiueos-image-native.cljc" 'check-aiueos-image-native/verify)
        routes (python/list)]
    (doseq [producer producers]
      (let [out (.joinpath output (.-stem producer))
            _ (.mkdir out)
            root (.joinpath out "src")
            _ (.mkdir (.joinpath root "lib") ** :parents true)
            entry (.joinpath root "entry.kotoba")
            left (.joinpath root "lib/left.kotoba") right (.joinpath root "lib/right.kotoba") base (.joinpath root "lib/base.kotoba")
            sources [[entry entry-src] [left left-src] [right right-src] [base base-src]]
            _ (doseq [[p text] sources] (.write_text p text))
            source-paths (mapv first sources)
            lock (.joinpath out "project.ksl")
            write-lock (fn [& {:keys [files roots] :or {files source-paths roots [root]}}]
                         (.write_text lock (str "KSL1\nentry " entry "\n"
                                                (apply str (for [p roots] (str "root " p "\n")))
                                                (apply str (for [p (sort-by str files)] (str "file " (u/geti (u/pin p) "sha256") " " p "\n"))))))
            _ (write-lock)
            good-lock (.read_bytes lock)
            env (python/dict {"PATH" "/nonexistent" "KEXE_STACK_BYTES" "8388608" "KEXE_CAP_RESOURCES_35" (str out)})
            calls (python/list)
            compile- (fn [name & {:keys [extra lock-args sentinel digest] :or {extra [] lock-args true}}]
                       (let [dst (.joinpath out (str name ".elf"))]
                         (when sentinel (.write_bytes dst sentinel))
                         (let [argv (concat [producer "compile" entry "--target" "x86_64-aiueos-kernel-v1" "--artifact" "image" "--output" dst
                                             "--fuel" "1000000" "--source-path" root]
                                            (when lock-args ["--source-lock" lock "--source-lock-sha256" (or digest (u/geti (u/pin lock) "sha256"))])
                                            extra)
                               r (u/run-process argv env 180)]
                           (.append calls (u/pydict "name" name "exit" (.-returncode r) "stderr" (.decode (.-stderr r))
                                                    "stdout" (.decode (.-stdout r)) "lock" (u/pin lock)))
                           (.write_text (.joinpath out "commands.json") (u/json-dump calls))
                           [dst r])))
            [image r0] (compile- "diamond")
            _ (u/chk (and (zero? (.-returncode r0)) (not (u/nonempty? (.-stderr r0)))) ["diamond" (.-returncode r0) (.-stderr r0)])
            image-pin (u/pin image)
            ;; Reuse the independent ABI observer, not a hosted compiler oracle.
            _ (verify (.read_bytes image) 1000000 true)
            refusals (python/list)
            refused (fn [name & opts]
                      (let [[dst r] (apply compile- name opts)]
                        (u/chk (and (not (zero? (.-returncode r))) (not (u/has-bytes? (.encode "KEXE_TRAP") (.-stderr r)))) [name (.-returncode r) (.-stderr r)])
                        (u/chk (not (.exists dst)) name)
                        (.append refusals name)))]
        (refused "missing-lock" :lock-args false)
        (refused "unpinned" :extra ["--unpinned"])
        (refused "forbidden-format" :extra ["--format" "static"])
        (refused "unexpected-positional" :extra ["ignored"])
        (refused "emit-module" :extra ["--emit-module"])
        (refused "wrong-lock-digest" :digest (apply str (repeat 64 "0")))
        (write-lock :files (remove #(= "base.kotoba" (.-name %)) source-paths))
        (refused "missing-transitive-source")
        (let [extra-file (.joinpath root "unused.kotoba")]
          (.write_text extra-file "(ns unused (:export [f]))\n(defn f [] :i64 0)\n")
          (write-lock :files (conj source-paths extra-file)))
        (refused "unused-lock-source")
        (.write_bytes lock good-lock)
        (let [original (.read_text base)]
          (.write_text base (.replace original "(+ x 1)" "(+ x 2)"))
          (refused "transitive-hash-drift")
          (.write_text base original))
        (let [original-left (.read_text left)]
          (.write_text left (str original-left "(defn- unreachable [] :string \"must refuse\")\n"))
          (write-lock)
          (refused "unused-unsupported-function")
          (.write_text left original-left))
        (let [original-entry (.read_text entry)]
          (.write_text entry (.replace original-entry "(l/run 20)" "(l/hidden 20)"))
          (write-lock)
          (refused "nonexported-import")
          (.write_text entry (str (.replace original-entry "[main]" "[main aiueos-isr-6]") "(defn aiueos-isr-6 [v :i64 r :i64 c :i64] :i64 0)\n"))
          (write-lock)
          (refused "invalid-isr-arity")
          (.write_text entry original-entry))
        (write-lock)
        (let [[dst r] (compile- "existing" :sentinel (.encode "preserve"))]
          (u/chk (and (not (zero? (.-returncode r))) (= (.encode "preserve") (.read_bytes dst))))
          (.append refusals "existing-output"))
        (let [[again r] (compile- "diamond-again")]
          (u/chk (and (zero? (.-returncode r)) (not (u/nonempty? (.-stderr r))) (u/deq (u/pin again) image-pin))))
        (.append routes (u/pydict "producer" (u/pin producer) "image" image-pin "modules" (count sources)
                                  "sourceFiles" (u/pydict-from (for [p source-paths] [(str (.relative_to p root)) (u/pin p)]))
                                  "refusals" refusals "compiledUnreachableDeclarations" true))))
    (u/chk (u/deq (u/geti (u/geti routes 0) "image") (u/geti (u/geti routes 1) "image")))
    (let [report (u/pydict "status" "PASS_NATIVE_AIUEOS_LOCKED_SCALAR_PROJECT" "sources" source "routes" routes
                           "nativeCDCI" false "fullKernel" false "ISR" false "liveRuntime" false "qemuBoot" false)]
      (.write_text (.joinpath output "native-project.json") (u/json-dump report))
      (println (u/geti report "status") "diamond/refer/private interface linking and refusal controls"))))

(defn -main [& args]
  (let [[build out complete] (u/parse-build-complete-output args)]
    (main build complete out)))

(when (some #(or (= % "check-aiueos-project-native.cljc") (str/ends-with? % "/check-aiueos-project-native.cljc")) sys/argv)
  (apply -main *command-line-args*))
