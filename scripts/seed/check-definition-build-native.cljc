;; Observe the bounded native KIR persistent object/relink candidate.
;;
;; Basilisp stages fixed sources/fixtures and observes native processes. Checking,
;; CID/SCC production, object encoding/store validation, emission and relinking
;; execute in Amu native images. Its modules (04-09) are in FULL-MANIFEST since JUN-584, but
;; this harness is not a whole Seed compiler cache, a trusted image-binding host, or a CI speedup claim.
;; Ported from check-definition-build-native.py (Basilisp). Linux only.
;; Run from the repo root (or AMU_ROOT):
;;   basilisp run scripts/seed/check-definition-build-native.cljc -- --compiler C --output O [--no-mutations]
(ns check-definition-build-native
  (:require [basilisp.string :as str]
            [sealed-image :as sealed])
  (:import hashlib json operator os pathlib platform shutil signal subprocess sys time))

(def root (.resolve (pathlib/Path (or (.get os/environ "AMU_ROOT") "."))))
(def extra ["seed/04-definition-cid.kotoba" "seed/05-definition-graph.kotoba" "seed/05-checked-definition.kotoba"
            "seed/06-definition-groups.kotoba" "seed/07-definition-objects.kotoba"
            "seed/08-definition-object-emitter.kotoba" "seed/09-definition-build.kotoba"
            "seed/tests/native-definition-object-checks.kotoba" "seed/tests/native-definition-build.kotoba"])

(defn- pydict
  "Insertion-ordered Python dict from alternating keys and values."
  [& kvs]
  (python/dict (python/list (map python/tuple (partition 2 kvs)))))

(defn- to-py [x]
  (cond (map? x) (python/dict (python/list (for [[k v] x] (python/tuple [k (to-py v)]))))
        (or (vector? x) (sequential? x)) (python/list (map to-py x))
        :else x))

(defn- chk
  ([ok] (chk ok "assertion failed"))
  ([ok message] (when-not ok (throw (python/AssertionError (str message))))))

(defn- deq [a b] (operator/eq a b))
(defn- has-bytes? [needle haystack] (operator/contains haystack needle))
(defn- nonempty? [b] (pos? (python/len b)))
(defn- bslice [data a b] (operator/getitem data (python/slice a b)))

(defn pin [path]
  (let [data (.read_bytes (pathlib/Path path))]
    (pydict "bytes" (python/len data) "sha256" (.hexdigest (hashlib/sha256 data)))))

(defn function
  ([name body] (function name body "x"))
  ([name body params]
   (str "{:name " name " :params [" params "] :param-types [" (if (seq params) ":i64" "") "] :result :i64 :effects #{} :body " body "}")))

(defn module [functions]
  (str "{:format :kotoba.kir/v4 :entry main :exports [main] :effects #{} :functions [" (str/join " " functions) "]}\n"))

(defn- hits-text [hits] (.encode (str "reused=" (first hits) " rebuilt=" (second hits) "\n")))
(defn- le64 [n] (.to_bytes n 8 "little" ** :signed true))

(defn main [compiler out & {:keys [mutations] :or {mutations true}}]
  (let [machine (platform/machine)
        _ (chk (and (= "Linux" (platform/system)) (contains? #{"aarch64" "x86_64"} machine)))
        compiler (.resolve compiler)
        product (json/loads (.read_text (.joinpath root "native-product.json")))
        compiler-pin (operator/getitem product (if (= machine "aarch64") "rootImage" "image"))
        _ (chk (deq (pin compiler) compiler-pin) "compiler differs from the source descriptor")
        _ (.mkdir out ** :parents true :exist_ok false)
        out (.resolve out)
        paths0 (vec (filter #(and (seq %) (not (str/starts-with? % "#")))
                            (.splitlines (.read_text (.joinpath root "seed/FULL-MANIFEST")))))
        _ (chk (= "seed/78-full-entry.kotoba" (last paths0)))
        ;; JUN-584: 04-09 are in FULL-MANIFEST now; add only the test fixtures it does not already carry.
        paths (into (vec (butlast paths0)) (remove (set paths0) extra))
        source (.decode (.join (.encode "\n") (python/list (map #(.read_bytes (.joinpath root %)) paths))))
        env (python/dict {"PATH" "/nonexistent" "KEXE_ALLOW" "35,37,38,39" "KEXE_CAP_RESOURCES_35" (str out)
                          "KEXE_STACK_BYTES" "8388608" "KEXE_FUEL" "10000000000"})
        report (pydict "schema" "amu.native-definition-build.v1" "host" (python/list [(platform/system) machine])
                       "nativeVerdictAuthority" false "productionCompilerClosureChanged" false
                       "productionImageSealBound" false "wholeSeedFrontendQualified" false
                       "wholeCompilerCacheQualified" false "ciPerformanceClaim" false "emulation" false
                       "scope" "pure scalar KIR v3/v4, payload-v2 profile6/desugar2, SCC<=8, x86 ELF"
                       "compiler" (pin compiler)
                       "modules" (python/dict (python/list (for [p paths] (python/tuple [p (pin (.joinpath root p))]))))
                       "calls" (python/list) "parity" (python/list) "mutations" (python/list))
        report-set (fn [k v] (operator/setitem report k v))
        report-add (fn [k row] (.append (operator/getitem report k) row))
        save (fn [] (.write_text (.joinpath out "observations.json") (str (json/dumps report ** :indent 2) "\n")))

        call (fn call
               [name argv & {:keys [code environment exact pass-fds] :or {code 0 environment env exact true pass-fds []}}]
               (let [start (time/monotonic)
                     p (subprocess/run (python/list (map str argv)) ** :cwd out :env environment :capture_output true
                                       :timeout 900 :pass_fds (python/tuple pass-fds))]
                 (.write_bytes (.joinpath out (str name ".stdout")) (.-stdout p))
                 (.write_bytes (.joinpath out (str name ".stderr")) (.-stderr p))
                 (let [row (pydict "name" name "exit" (.-returncode p) "seconds" (- (time/monotonic) start)
                                   "stdoutSHA256" (.hexdigest (hashlib/sha256 (.-stdout p)))
                                   "stderrSHA256" (.hexdigest (hashlib/sha256 (.-stderr p))))]
                   (report-add "calls" row)
                   (save)
                   (println (json/dumps row))
                   (.flush sys/stdout)
                   (when exact
                     (chk (= code (.-returncode p))
                          (str [name code (.-returncode p) (bslice (.-stdout p) -500 nil) (bslice (.-stderr p) -500 nil)])))
                   p)))

        target (if (= machine "aarch64") "aarch64-linux" "x86_64-linux")
        build (fn [name text]
                (let [src (.joinpath out (str name ".kotoba"))
                      image (.joinpath out (str name ".elf"))]
                  (.write_text src text)
                  (sealed/with-sealed-image compiler (operator/getitem compiler-pin "sha256")
                    (fn [fd _]
                      (call (str "build-" name) [(str "/proc/self/fd/" fd) "compile" src "--target" target
                                                 "--output" image "--format" "static"]
                            :pass-fds [fd])))
                  (.chmod image 0755)
                  image))

        producer (build "producer" source)
        seal (operator/getitem (pin producer) "sha256") ; Observer context only; no trusted production binding claim.
        _ (do (report-set "producer" (pin producer)) (save))

        directory (fn [name]
                    (let [path (.joinpath out name)] (.mkdir path ** :mode 0700) path))

        bound-invoke
        (fn [name image expected text cache hits & {:keys [replace-after-open]}]
          (let [src (.joinpath out (str name ".kir")) artifact (.joinpath out (str name ".elf"))]
            (.write_text src text)
            (let [p (sealed/with-sealed-image image expected
                      (fn [fd digest]
                        ;; An owner who can replace the path cannot replace the sealed fd.
                        (when replace-after-open
                          (.unlink image)
                          (.write_bytes image (.encode "not an executable")))
                        (try (os/write fd (.encode "x"))
                             (throw (python/AssertionError "sealed image accepted a write"))
                             (catch python/PermissionError _ nil))
                        (try (os/ftruncate fd 0)
                             (throw (python/AssertionError "sealed image accepted truncation"))
                             (catch python/PermissionError _ nil))
                        (call name [(str "/proc/self/fd/" fd) "cached" src cache digest artifact "1000000"] :pass-fds [fd])))]
              (chk (and (.exists artifact) (not (nonempty? (.-stderr p)))))
              (chk (has-bytes? (hits-text hits) (.-stdout p)))
              artifact)))

        invoke
        (fn [name text cache & {:keys [mode hits code context fuel image] :or {mode "cached" code 0 context seal fuel "1000000" image producer}}]
          (let [src (.joinpath out (str name ".kir")) artifact (.joinpath out (str name ".elf"))]
            (.write_text src text)
            (let [p (call name [image mode src cache context artifact fuel] :code code)]
              (if (or (not= code 0) (= mode "controls"))
                (do (chk (not (.exists artifact)) name) p)
                (do (chk (and (.exists artifact) (not (nonempty? (.-stderr p)))) [name (.-stderr p)])
                    (when hits (chk (has-bytes? (hits-text hits) (.-stdout p)) [name (.-stdout p)]))
                    artifact)))))

        execute
        (fn [name artifact expected]
          (when (= machine "x86_64") ; ARM emits x86 bytes; it does not emulate their execution.
            (.chmod artifact 0755)
            (let [p (call (str name "-execute") [artifact] :environment (python/dict {"PATH" "/nonexistent"}))]
              (chk (and (not (nonempty? (.-stderr p))) (= (le64 expected) (.-stdout p))) [name (.-stdout p)]))))

        pair
        (fn [name text cache hits expected]
          (let [reference (invoke (str name "-reference") text cache :mode "reference")
                candidate (invoke name text cache :hits hits)]
            (chk (= (.read_bytes reference) (.read_bytes candidate)) name)
            (execute name candidate expected)
            (report-add "parity" (pydict "name" name "image" (pin candidate) "reused" (first hits) "rebuilt" (second hits)
                                         "nativeExecution" (= machine "x86_64") "expectedI64" expected))
            (save)
            candidate))

        helper (function "helper" "(if (< x 0) 0 (+ x 2))")
        entry (function "main" "(helper 40)" "")
        base (module [helper entry])
        bound-cache (directory "bound-cache")
        trusted-copy (.joinpath out "bound-producer.elf")
        _ (do (shutil/copyfile producer trusted-copy) (.chmod trusted-copy 0500))
        bound-cold (bound-invoke "bound-cold" trusted-copy seal base bound-cache [0 2])
        bound-warm (bound-invoke "bound-warm" trusted-copy seal base bound-cache [2 0])
        _ (chk (= (.read_bytes bound-cold) (.read_bytes bound-warm)))
        replaced (bound-invoke "bound-replaced-path" trusted-copy seal base bound-cache [2 0] :replace-after-open true)
        _ (chk (= (.read_bytes replaced) (.read_bytes bound-cold)))
        _ (execute "bound-replaced-path" replaced 42)
        _ (try (sealed/with-sealed-image trusted-copy seal (fn [_ _] (throw (python/AssertionError "modified producer accepted"))))
               (catch python/ValueError error (chk (= "image digest mismatch" (str error)))))
        _ (do (report-set "boundFixture" (pydict "image" (pin producer) "cold" (pin bound-cold) "warm" (pin bound-warm)
                                                 "pathReplacementDidNotChangeExecution" true "sealedWritesRejected" true
                                                 "independentlyAuthenticatedProducer" false "productionQualified" false))
              (save))
        cache (directory "cache")
        _ (pair "base-fill" base cache [0 2] 42)
        _ (pair "base-warm" base cache [2 0] 42)
        ;; Source-to-KIR conversion may erase a checker-injected vector-new call and change fuel behavior. This
        ;; bounded producer accepts checked scalar KIR only: neither raw source nor these vector KIRs may enter
        ;; its object store.
        vector-cache cache ; Keep populated, verified scalar objects in the store.
        listing (fn [d] (python/dict (python/list (for [p (python/list (.iterdir d))] (python/tuple [(.-name p) (pin p)])))))
        vector-before (listing vector-cache)
        _ (chk (= 2 (python/len vector-before)))
        _ (doseq [[name body] [["empty" "(vector-count (vector-new))"]
                               ["conj" "(let [v (vector-new) w (vector-conj v 42)] (if (= (vector-count v) 0) (vector-at w 0) 7))"]]]
            (let [input-source (str "(ns vector-runtime (:export [main])) (defn main [] :i64 " body ")\n")
                  kir (module [(function "main" body "")])]
              (doseq [mode ["cold" "cached" "reference"]]
                (let [refused-source (invoke (str "vector-" name "-source-" mode) input-source vector-cache :mode mode :code 1)]
                  (chk (not (nonempty? (.-stdout refused-source)))))
                (let [refused-kir (invoke (str "vector-" name "-kir-" mode) kir vector-cache :mode mode :code 1)]
                  (chk (and (not (nonempty? (.-stdout refused-kir))) (has-bytes? (.encode "E7101") (.-stderr refused-kir)))))
                (chk (deq (listing vector-cache) vector-before)))))
        ;; Record-schema identity is supported by the checked KIR producer, but the current object backend is still
        ;; the scalar profile. Neither a reference nor a cached build may manufacture an object for this input.
        schema-cache (directory "schema-refusal-cache")
        schema-kir (str "{:format :kotoba.kir/v4 :entry main :exports [main] :effects #{} "
                        ":schemas {:s/r [:record :s/r [[:a :i64]]]} :functions ["
                        "{:name f :params [x] :param-types [[:ref :s/r]] :result :i64 :effects #{} :body 42} "
                        (function "main" "42" "") "]}\n")
        _ (doseq [mode ["reference" "cached"]]
            (let [rejected (invoke (str "schema-refusal-" mode) schema-kir schema-cache :mode mode :code 1)]
              (chk (and (not (nonempty? (.-stdout rejected))) (has-bytes? (.encode "E7102") (.-stderr rejected))))
              (chk (empty? (python/list (.iterdir schema-cache))))))
        _ (invoke "native-controls" base cache :mode "controls")
        _ (pair "rename" (module [(function "renamed" "(if (< x 0) 0 (+ x 2))") (function "main" "(renamed 40)" "")]) cache [2 0] 42)
        _ (pair "reorder" (module [entry helper]) cache [2 0] 42)
        _ (pair "unrelated" (module [(function "unrelated" "(+ x 900)") entry helper]) cache [2 1] 42)
        _ (pair "leaf-edit" (module [(function "helper" "(if (< x 0) 0 (+ x 3))") entry]) cache [0 2] 43)
        _ (pair "caller-edit" (module [helper (function "main" "(helper 41)" "")]) cache [1 1] 43)
        alternate (if (not= seal (apply str (repeat 64 "0"))) (apply str (repeat 64 "0")) (apply str (repeat 64 "1")))
        original (invoke "context-reference" base cache :mode "reference" :context alternate)
        changed (invoke "context-change" base cache :hits [0 2] :context alternate)
        _ (chk (= (.read_bytes original) (.read_bytes changed)))
        _ (execute "context-change" changed 42)

        dup (directory "duplicates")
        a (function "a" "(+ x 2)") b (function "b" "(+ x 2)")
        duplicate-b (module [a b (function "main" "(b 40)" "")])
        _ (pair "duplicate-fill" duplicate-b dup [0 3] 42)
        _ (pair "duplicate-warm" duplicate-b dup [3 0] 42)
        _ (pair "duplicate-call-edit" (module [a b (function "main" "(a 40)" "")]) dup [2 1] 42)
        _ (pair "duplicate-reorder" (module [b a (function "main" "(a 40)" "")]) dup [3 0] 42)

        cyc (directory "cycle")
        ca (function "a" "(if (= x 0) 40 (b (- x 1)))") cb (function "b" "(if (= x 0) 41 (a (- x 1)))")
        cm (function "main" "(a 3)" "") unused (function "unused" "(+ x 9)")
        cycle (module [ca cb cm unused])
        _ (pair "cycle-fill" cycle cyc [0 3] 41)
        _ (pair "cycle-warm" cycle cyc [3 0] 41)
        _ (pair "cycle-reorder" (module [unused cm cb ca]) cyc [3 0] 41)
        _ (pair "cycle-rename" (module [(function "north" "(if (= x 0) 40 (south (- x 1)))")
                                        (function "south" "(if (= x 0) 41 (north (- x 1)))")
                                        (function "main" "(north 3)" "") unused]) cyc [3 0] 41)
        _ (pair "cycle-edit" (module [ca (function "b" "(if (= x 0) 42 (a (- x 1)))") cm unused]) cyc [1 2] 42)
        large (directory "scc8")
        ring (vec (for [i (range 8)]
                    (function (str "f" i) (str "(if (= x 0) " (- 8 i) " (f" (mod (dec i) 8) " (- x 1)))"))))
        ringmain (function "main" "(f0 4)" "")
        _ (pair "scc8-fill" (module (conj (conj ring ringmain) unused)) large [0 3] 4)
        _ (pair "scc8-warm" (module (conj (conj ring ringmain) unused)) large [3 0] 4)
        ring (assoc ring 4 (function "f4" "(if (= x 0) 99 (f3 (- x 1)))"))
        _ (pair "scc8-edit" (module (conj (conj ring ringmain) unused)) large [1 2] 99)

        contents (fn [d] (python/dict (python/list (for [p (python/list (.iterdir d))] (python/tuple [(.-name p) (.read_bytes p)])))))
        snapshot (contents cache)
        _ (invoke "wrong-type" (module [helper (function "main" "true" "")]) cache :code 1)
        _ (invoke "effects" (.replace base ":effects #{}" ":effects #{:fs/app-data}" 1) cache :code 1)
        _ (invoke "forged-checked" (str (bslice base 0 -2) " :checked true}\n") cache :code 1)
        six (str "{:name six :params [a b c d e f] :param-types [:i64 :i64 :i64 :i64 :i64 :i64] "
                 ":result :i64 :effects #{} :body (+ a f)}")
        _ (invoke "fresh-target-refusal" (module [six (function "main" "(six 1 2 3 4 5 6)" "")]) cache :code 1)
        _ (invoke "fuel-zero" base cache :code 2 :fuel "0")
        _ (chk (deq snapshot (contents cache)))
        exhausted (invoke "fuel-exhaustion" cycle cyc :hits [3 0] :fuel "1")
        _ (when (= machine "x86_64")
            (.chmod exhausted 0755)
            (let [p (call "fuel-exhaustion-execute" [exhausted] :code (- (python/int signal/SIGILL))
                          :environment (python/dict {"PATH" "/nonexistent"}))]
              (chk (and (not (nonempty? (.-stdout p))) (not (nonempty? (.-stderr p)))))))
        ;; Reusing the same object bodies must never reuse an earlier invocation's fuel budget. Compare fresh
        ;; reference/link bytes for several budgets, including exhaustion, with the same already-populated SCC cache.
        cycle-before (listing cyc)
        fuel-images (python/dict)
        _ (doseq [budget ["1" "2" "3" "1000000"]]
            (let [reference (invoke (str "fuel-" budget "-reference") cycle cyc :mode "reference" :fuel budget)
                  candidate (invoke (str "fuel-" budget "-cached") cycle cyc :hits [3 0] :fuel budget)]
              (chk (= (.read_bytes reference) (.read_bytes candidate)) budget)
              (operator/setitem fuel-images budget (pin candidate))
              (chk (deq (listing cyc) cycle-before))
              (when (= machine "x86_64")
                (let [outcomes (vec (for [[lane image] [["reference" reference] ["cached" candidate]]]
                                      (do (.chmod image 0755)
                                          (let [observed (call (str "fuel-" budget "-" lane "-execute") [image]
                                                               :environment (python/dict {"PATH" "/nonexistent"}) :exact false)]
                                            [(.-returncode observed) (.-stdout observed) (.-stderr observed)]))))]
                  (chk (= (first outcomes) (second outcomes)) budget)
                  (when (= budget "1")
                    (chk (= [(- (python/int signal/SIGILL)) (.encode "") (.encode "")] (first outcomes))))
                  (when (= budget "1000000")
                    (chk (= [0 (le64 41) (.encode "")] (first outcomes))))))))
        _ (chk (= (python/len fuel-images)
                  (python/len (python/set (for [v (.values fuel-images)] (operator/getitem v "sha256"))))))
        _ (do (report-set "freshFuelLinkParity" fuel-images) (save))
        missing (directory "missing")
        _ (pair "missing-fill" base missing [0 2] 42)
        _ (.unlink (python/next (python/iter (.glob missing "*.kdo"))))
        _ (pair "missing-rebuild" base missing [1 1] 42)
        damaged (atom {})
        _ (doseq [[name kind] [["corrupt" "body"] ["checksum" "checksum"] ["permissions" "mode"] ["symlink" "symlink"]]]
            (let [d (directory name)]
              (pair (str name "-fill") base d [0 2] 42)
              (let [target (python/next (python/iter (.glob d "*.kdo")))]
                (.chmod target 0600)
                (let [data (.read_bytes target)]
                  (cond
                    (contains? #{"body" "checksum"} kind)
                    (let [pos (if (= kind "body") (dec (python/len data)) 70)]
                      (.write_bytes target (operator/add (operator/add (bslice data 0 pos)
                                                                       (if (not= (bslice data pos (inc pos)) (.encode "0")) (.encode "0") (.encode "1")))
                                                         (bslice data (inc pos) nil)))
                      (.chmod target 0400))
                    (= kind "symlink")
                    (let [real (.joinpath out "symlink-real.kdo")]
                      (.write_bytes real data)
                      (.chmod real 0400)
                      (.unlink target)
                      (.symlink_to target real)))
                  (let [before (.read_bytes target)]
                    (invoke (str name "-refusal") base d :code 1)
                    (chk (= before (.read_bytes target)))
                    (swap! damaged assoc name d))))))
        public (directory "public-directory")
        _ (.chmod public 0755)
        _ (invoke "public-directory-refusal" base public :code 1)
        _ (chk (empty? (python/list (.iterdir public))))]

    (when mutations
      (doseq [[name old new scenario]
              [["checksum" "(= (sh-text body) (string-substring record 70 134))" "true" "checksum"]
               ["permissions" "(= (dco-field metadata 0) (if directory \"448\" \"256\"))" "true" "permissions"]
               ["placeholder" "(dco-zero? code offset width)" "true" "controls"]
               ["binding" "(= (dcn-binding A R f) binding)"
                "(= (string-substring (dcn-binding A R f) 0 59) (string-substring binding 0 59))" "binding"]]]
        (chk (= 1 (.count source old)) name)
        (let [mutant (build (str "mutant-" name) (.replace source old new))]
          (when (= name "checksum")
            ;; A different executing image must not reuse the first image's objects.
            (let [changed-image (bound-invoke "bound-other-image" mutant (operator/getitem (pin mutant) "sha256") base bound-cache [0 2])]
              (chk (= (.read_bytes changed-image) (.read_bytes bound-cold)))
              (execute "bound-other-image" changed-image 42)
              (try (sealed/with-sealed-image mutant seal (fn [_ _] (throw (python/AssertionError "different image accepted original pin"))))
                   (catch python/ValueError error (chk (= "image digest mismatch" (str error)))))))
          ;; Explicitly reuse fixture context to reach the internal guard.
          ;; Production image binding remains an OPEN gate for this prototype.
          (let [src (.joinpath out (str "mutant-" name ".kir"))
                _ (.write_text src (if (= scenario "binding") duplicate-b base))
                artifact (.joinpath out (str "mutant-" name "-output.elf"))
                d (if (= scenario "binding") dup (get @damaged scenario cache))
                mode (if (= scenario "controls") "controls" "cached")
                p (call (str "detect-" name) [mutant mode src d seal artifact "1000000"] :exact false)
                detected (if (= scenario "controls")
                           (and (= 1 (.-returncode p)) (not (.exists artifact)))
                           (do (chk (and (= 0 (.-returncode p)) (.exists artifact)) [name (.-stderr p)])
                               (if (= scenario "binding")
                                 (not= (.read_bytes artifact) (.read_bytes (.joinpath out "duplicate-fill-reference.elf")))
                                 (has-bytes? (.encode "reused=2 rebuilt=0") (.-stdout p)))))]
            (report-add "mutations" (pydict "name" name "built" true "executed" true "detected" (boolean detected) "image" (pin mutant)))
            (save)
            (chk detected name)))))
    (chk (empty? (python/list (.glob out "*/kotoba-output-*"))) "managed staging leak")
    (doseq [d [cache dup cyc large missing]]
      (chk (every? #(= 0400 (bit-and (.-st_mode (.stat %)) 0777)) (python/list (.glob d "*.kdo")))))
    (report-set "status" "PASS_NATIVE_DEFINITION_OBJECT_BUILD")
    (report-set "nativeEmittedExecution" (= machine "x86_64"))
    (save)
    (println (operator/getitem report "status"))
    (.flush sys/stdout)))

(defn- opt [args k] (second (drop-while #(not= % k) args)))

(defn -main [& args]
  (main (pathlib/Path (or (opt args "--compiler") (sys/exit "--compiler is required")))
        (pathlib/Path (or (opt args "--output") (sys/exit "--output is required")))
        :mutations (not (some #{"--no-mutations"} args))))

(when (some #(or (= % "check-definition-build-native.cljc") (str/ends-with? % "/check-definition-build-native.cljc")) sys/argv)
  (apply -main *command-line-args*))
