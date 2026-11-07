;; Observe all-caller fixed extent contracts through real native linking.
;; Ported from check-aiueos-fixed-extent-native.py (Basilisp). Linux only.
;; Run: basilisp run scripts/seed/check-aiueos-fixed-extent-native.cljc -- (--build DIR | --complete DIR) --output OUT
(ns check-aiueos-fixed-extent-native
  (:require [aiueos-native-proof :as proof]
            [basilisp.string :as str]
            [gate-util :as u])
  (:import operator sys))

;; Both scopes of scoped-entry-src reuse frame slots, but each read must be dominated by its own assignment.
;; The condition is deliberately runtime data, never folded away.
(def entry-src
  "(ns entry (:require [lib.bridge :as b]) (:export [main]))
(defn main [] :i64
 (let [p (kernel-owned-page 0) saved (kernel-load-u64-4k p 4096 0)
       write (kernel-store-u64-4k p 4096 0 42)
       value (b/through p 0)
       restored (kernel-store-u64-4k p 4096 0 saved)]
  (if (and (= write 42) (= value 42) (= restored saved)) 42 0)))\n")

(def bridge-src
  "(ns lib.bridge (:require [lib.memory :as m]) (:export [through]))
(defn through [base :i64 index :i64] :i64 (m/read base index))\n")

(def memory-src
  "(ns lib.memory (:export [read]))
(defn- leaf [base :i64 index :i64] :i64 (kernel-load-u64-4k base 4096 index))
(defn read [base :i64 index :i64] :i64 (leaf base index))\n")

(def recursive-src
  "(ns lib.memory (:export [read]))
(defn- leaf [base :i64 index :i64 remaining :i64] :i64
 (if (= remaining 0) (kernel-load-u64-4k base 4096 index)
  (leaf base index (- remaining 1))))
(defn read [base :i64 index :i64] :i64 (leaf base index 3))\n")

(def scoped-entry-src
  "(ns entry (:require [lib.bridge :as b]) (:export [main]))
(defn main [] :i64
 (if (= (kernel-rdtsc) 0)
  (let [p (kernel-owned-page 0) saved (kernel-load-u64-4k p 4096 0)
        write (kernel-store-u64-4k p 4096 0 42) value (b/through p 0)
        restored (kernel-store-u64-4k p 4096 0 saved)]
   (if (and (= write 42) (= value 42) (= restored saved)) 42 0))
  (let [p (kernel-owned-page 1) saved (kernel-load-u64-4k p 4096 0)
        write (kernel-store-u64-4k p 4096 0 42) value (b/through p 0)
        restored (kernel-store-u64-4k p 4096 0 saved)]
   (if (and (= write 42) (= value 42) (= restored saved)) 42 0))))\n")

(def ready-bridge-src
  "(ns lib.bridge (:require [lib.memory :as m]) (:export [through]))
(defn- resident [base :i64 index :i64 a :i64 b :i64 ready :i64 remaining :i64] :i64
 (if (= remaining 0) (if (= ready 1) (m/read base index) 42)
  (resident base index a b ready (- remaining 1))))
(defn through [base :i64 index :i64] :i64
 (let [ready (if (= index 0) 1 0)] (resident base index 0 0 ready 3)))\n")

(def mutual-src
  "(ns lib.memory (:export [read]))
(defn- leaf [base :i64 index :i64 remaining :i64] :i64
 (if (= remaining 0) (kernel-load-u64-4k base 4096 index)
  (other base index (- remaining 1))))
(defn- other [base :i64 index :i64 remaining :i64] :i64
 (if (= remaining 0) (kernel-load-u64-4k base 4096 index)
  (leaf base index (- remaining 1))))
(defn read [base :i64 index :i64] :i64 (leaf base index 3))\n")

(def length-memory-src
  "(ns lib.memory (:export [read]))
(defn- leaf [base :i64 length :i64 index :i64] :i64
 (kernel-load-u64-4k base length index))
(defn read [base :i64 length :i64 index :i64] :i64 (leaf base length index))\n")

(def length-bridge-src (.replace bridge-src "(m/read base index)" "(m/read base 4096 index)"))
(def diagnostic-memory-src
  (str memory-src "\n(defn- diagnostic [parent :i64 bytes :i64] :i64\n (let [page (kernel-subregion parent bytes 0 4096)] (leaf page 0)))\n"))

(defn main [build out complete]
  (let [[graph producers _] (proof/load-native-producers :build build :complete complete)
        _ (.mkdir out ** :parents true :exist_ok false)
        routes (python/list)]
    (doseq [compiler producers]
      (let [scope (.joinpath out (.-stem compiler))
            _ (.mkdir (.joinpath scope "lib") ** :parents true)
            entry (.joinpath scope "entry.kotoba") bridge (.joinpath scope "lib/bridge.kotoba") memory (.joinpath scope "lib/memory.kotoba")
            lock (.joinpath scope "source.ksl")
            calls (python/list) artifacts (python/dict)
            env (python/dict {"PATH" "/nonexistent" "KEXE_STACK_BYTES" "8388608" "KEXE_CAP_RESOURCES_35" (str scope)})
            compile- (fn [name & {:keys [e b m bad] :or {e entry-src b bridge-src m memory-src bad false}}]
                       (.write_text entry e) (.write_text bridge b) (.write_text memory m)
                       (.write_text lock (str "KSL1\nentry " entry "\nroot " scope "\n"
                                              (apply str (for [p (sort-by str [entry bridge memory])] (str "file " (u/geti (u/pin p) "sha256") " " p "\n")))))
                       (let [image (.joinpath scope (str name ".elf"))
                             r (u/run-process [compiler "compile" entry "--target" "x86_64-aiueos-kernel-v1" "--artifact" "image" "--output" image
                                               "--fuel" "1000000" "--source-path" scope "--source-lock" lock
                                               "--source-lock-sha256" (u/geti (u/pin lock) "sha256")] env 240)]
                         (.append calls (u/pydict "name" name "exit" (.-returncode r) "stderr" (.decode (.-stderr r))
                                                  "sources" (u/pydict-from (for [p [entry bridge memory]] [(str (.relative_to p scope)) (.read_text p)]))))
                         (.write_text (.joinpath scope "calls.json") (u/json-dump calls))
                         (if bad
                           (u/chk (and (= 1 (.-returncode r)) (u/has-bytes? (.encode "E7106") (.-stderr r))
                                       (u/has-bytes? (.encode "kernel function ") (.-stderr r)) (not (.exists image))) (u/geti calls -1))
                           (do (u/chk (and (zero? (.-returncode r)) (not (u/nonempty? (.-stderr r))) (.exists image)) (u/geti calls -1))
                               (let [efi (.joinpath scope (str name ".efi"))
                                     q (u/run-process [compiler "package-aiueos-boot" image "--output" efi] env 180)]
                                 (u/chk (and (zero? (.-returncode q)) (not (u/nonempty? (.-stderr q)))) (.-stderr q))
                                 (operator/setitem artifacts name (u/pydict "kernel" (u/pin image) "efi" (u/pin efi))))))))]
        (compile- "fixed-helper")
        (compile- "identity-recursion" :m recursive-src)
        (compile- "identity-nontail-recursion" :m (.replace recursive-src "(leaf base index (- remaining 1))" "(+ 0 (leaf base index (- remaining 1)))"))
        (compile- "disjoint-local-scopes" :e scoped-entry-src)
        (compile- "separate-ready-six-arguments" :b ready-bridge-src)
        (compile- "rooted-mutual-recursion" :m mutual-src)
        (compile- "rooted-mutual-nontail" :m (.replace mutual-src "(other base index (- remaining 1))" "(+ 0 (other base index (- remaining 1)))"))
        (compile- "fixed-and-paired-length" :b length-bridge-src :m length-memory-src)
        (compile- "uncalled-paired-diagnostic" :m diagnostic-memory-src)
        (compile- "wrong-extent" :m (.replace memory-src "base 4096 index" "base 64 index") :bad true)
        (compile- "literal-caller" :e (.replace entry-src "(b/through p 0)" "(b/through 4096 0)") :bad true)
        (compile- "computed-caller" :e (.replace entry-src "(b/through p 0)" "(b/through (+ p 0) 0)") :bad true)
        (compile- "second-forged-caller" :b (str bridge-src "\n(defn- bad [] :i64 (m/read 4096 0))\n") :bad true)
        (compile- "mixed-extents" :e (.replace entry-src "value (b/through p 0)" "other (b/through (kernel-owned-window 0 8192) 0) value (b/through p 0)") :bad true)
        (compile- "recursive-pointer-change" :m (.replace recursive-src "(leaf base index (- remaining 1))" "(leaf (+ base 8) index (- remaining 1))") :bad true)
        (compile- "unseeded-recursion" :e "(ns entry (:require [lib.bridge :as b]) (:export [main]))\n(defn main [] :i64 42)\n" :m recursive-src :bad true)
        (compile- "forged-disjoint-scope" :e (.replace scoped-entry-src "(kernel-owned-page 1)" "4096") :bad true)
        (compile- "computed-disjoint-scope" :e (.replace scoped-entry-src "(kernel-owned-page 1)" "(+ (kernel-owned-page 1) 0)") :bad true)
        (compile- "branch-result-base" :e (.replace entry-src "(kernel-owned-page 0)" "(if (= (kernel-rdtsc) 0) (kernel-owned-page 0) (kernel-owned-page 1))") :bad true)
        (compile- "inline-ready-branch" :b (.replace ready-bridge-src "(let [ready (if (= index 0) 1 0)] (resident base index 0 0 ready 3))" "(resident base index 0 0 (if (= index 0) 1 0) 3)"))
        (compile- "unseeded-mutual" :e "(ns entry (:require [lib.bridge :as b]) (:export [main]))\n(defn main [] :i64 42)\n" :m mutual-src :bad true)
        (compile- "forged-mutual-caller" :m (str mutual-src "\n(defn- bad [] :i64 (other 4096 0 3))\n") :bad true)
        (compile- "computed-mutual-edge" :m (.replace mutual-src "(other base index (- remaining 1))" "(other (+ base 8) index (- remaining 1))") :bad true)
        (compile- "lying-paired-length" :b (.replace length-bridge-src "(m/read base 4096 index)" "(m/read base 64 index)") :m length-memory-src :bad true)
        (compile- "assigned-parameter-rebase" :m (.replace recursive-src "(leaf base index (- remaining 1))" "(leaf (kernel-subregion base 4096 0 4096) index (- remaining 1))") :bad true)
        (compile- "forged-diagnostic-caller" :m (str diagnostic-memory-src "\n(defn- bad [] :i64 (diagnostic 4096 4096))\n") :bad true)
        (.append routes (u/pydict "compiler" (u/pin compiler) "artifacts" artifacts "refusals" 16))))
    (u/chk (u/deq (u/geti (u/geti routes 0) "artifacts") (u/geti (u/geti routes 1) "artifacts")))
    (let [report (u/pydict "status" "PASS_NATIVE_FIXED_EXTENT_HELPERS" "source" graph "routes" routes
                           "guestExecution" false "fullKernel" false "nativeCDCI" false)]
      (.write_text (.joinpath out "native-fixed-extent.json") (u/json-dump report))
      (println (u/geti report "status") "rooted mutual recursion, scoped dominance, fixed/paired lengths,16 refusals; guest separate"))))

(defn -main [& args]
  (let [[build out complete] (u/parse-build-complete-output args)]
    (main build out complete)))

(when (some #(or (= % "check-aiueos-fixed-extent-native.cljc") (str/ends-with? % "/check-aiueos-fixed-extent-native.cljc")) sys/argv)
  (apply -main *command-line-args*))
