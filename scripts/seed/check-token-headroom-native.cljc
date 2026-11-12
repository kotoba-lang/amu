;; Compiler table headroom of the largest static builds (JUN-737). Ported from check-token-headroom-native.py
;; (Basilisp, JUN-974); the Python docstring has the full measurement/bisection/negative-control contract.
;;
;; The static profile's tables (seed/00-ns-static.kotoba, set by the seed/MEMORY-MAP static overrides) bound every
;; source the native compiler reads. This gate measures, with the native compiler itself, how many more entries the
;; largest static builds in CI can take in the TOK, NODE and FN tables, and fails when any is below its floor.
;; Stages sources and observes processes; every lex, read and name pass is the native compiler's.
;; Run: basilisp run -p scripts/seed scripts/seed/check-token-headroom-native.cljc -- --compiler F --output DIR
;;      [--floor TABLE=N]... [--mac-target aarch64-linux|x86_64-linux] [--tables TOK,NODE,FN]
(ns check-token-headroom-native
  (:require [basilisp.string :as str]
            [gate-util :as u])
  (:import json operator os pathlib platform re subprocess sys))

(def root u/root)
(defn rp [rel] (pathlib/Path root rel))
(defn g [m & ks] (reduce (fn [a k] (operator/getitem a k)) m ks))
(defn pin [p] (let [d (.read_bytes (pathlib/Path p))] (u/pydict "bytes" (python/len d) "sha256" (u/sha256-hex d))))
(defn chk [c m] (u/chk c (str m)))
(defn b [x] (.encode x "utf-8"))
(defn pyenv [& kvs] (apply u/pydict kvs))

(def full-marker (b "E101 compiler table full: region "))
(def entry "seed/78-full-entry.kotoba")
(def main-form (b "(defn- seed-main [] :i64"))
;; table -> [E101 region, capacity constant, default floor]
(def tables [["TOK" 1 "MM-TOK-CAP" 65536] ["NODE" 4 "MM-NODE-CAP" 65536] ["FN" 6 "MM-FN-CAP" 256]])
(def table-names (mapv first tables))
(defn table-region [t] (second (first (filter #(= (first %) t) tables))))
(def regions {1 "TOK" 4 "NODE" 6 "FN"})
(def lex (re/compile (b ";[^\\n]*|\"(?:\\\\.|[^\"\\\\])*\"|#\\{|[()\\[\\]{}]|[^\\s()\\[\\]{}\",;]+")))

(defn lines-of [m] (vec (filter #(and (seq %) (not (.startswith % "#"))) (.splitlines (.read_text (rp m))))))
(defn bjoin [sep items] (.join sep (python/list items)))

(defn renamed-entry [data name]
  (chk (= (.count data main-form) 1) "entry anchor")
  (.replace data main-form (operator/add (operator/add (b "(defn- ") name) (b " [] :i64"))))

(defn builds
  "The largest static sources CI compiles, composed as their gates compose them."
  []
  (let [paths (lines-of "seed/FULL-MANIFEST")
        rd (fn [p] (.read_bytes (rp p)))
        kir (map (fn [p] (if (= p entry) (renamed-entry (rd p) (b "dsx-original-main")) (rd p))) paths)
        kernel "seed/05-definition-graph.kotoba"
        graph (map (fn [p] (if (= p entry) (renamed-entry (rd p) (b "dgg-original-main")) (rd p))) (filter #(not= % kernel) paths))
        whole-entry (b "\n(defn- seed-main [] :i64 (if (= (io-argc) 1) (dgsr-run (drv-read (io-arg 0))) 2))\n")
        cat (fn [& parts] (reduce operator/add parts))]
    [["kir-execution-compiler" (cat (bjoin (b "\n") kir) (b "\n") (rd "seed/tests/native-source-loop-execution.kotoba"))]
     ["definition-graph-whole-producer" (cat (bjoin (b "\n") graph) (b "\n") (rd kernel) (b "\n")
                                             (rd "seed/tests/native-definition-graph-sir.kotoba") whole-entry)]]))

(defn capacity [name]
  (let [caps (re/findall (str "\\(def " name " (\\d+)\\)") (.read_text (rp "seed/00-ns-static.kotoba")))]
    (chk (= (python/len caps) 1) name)
    (python/int (operator/getitem caps 0))))

(defn estimate
  "Approximate count, only to centre a search window (the native compiler decides)."
  [source table]
  (let [items (python/list (filter (fn [m] (not (.startswith m (b ";")))) (re/findall lex source)))
        n (python/len items)]
    (case table
      "TOK" n
      "NODE" (count (filter (fn [m] (not (contains? #{")" "]" "}"} (.decode m "utf-8")))) items))
      (loop [i 0 c 0]
        (if (>= (inc i) n)
          c
          (recur (inc i) (if (and (u/deq (operator/getitem items i) (b "(")) (let [x (operator/getitem items (inc i))] (or (u/deq x (b "defn")) (u/deq x (b "defn-"))))) (inc c) c)))))))

(defn filler
  "Exactly n stray tokens / read nodes as lists of 100 tokens (99 nodes), or n trivial functions and a stray `0`."
  [n table]
  (if (= table "FN")
    (operator/add (bjoin (u/bytes-of) (map (fn [i] (b (str "(defn- zz-fn-headroom" i " [] :i64 0)\n"))) (range n))) (b "0\n"))
    (let [unit (if (= table "TOK") 100 99)
          chunk (operator/add (operator/add (b "(") (operator/mul (b "0 ") 98)) (b ")"))
          rest- (mod n unit)
          chunks (python/list (repeat (quot n unit) chunk))]
      (cond (= rest- 1) (.append chunks (b "0"))
            (pos? rest-) (.append chunks (operator/add (operator/add (b "(") (operator/mul (b "0 ") (- rest- (if (= table "TOK") 2 1)))) (b ")"))))
      (bjoin (b "\n") chunks))))

(defn padding
  "Never-called module-local functions adding exactly n tokens / read nodes / functions."
  [n table]
  (if (= table "FN")
    (operator/add (bjoin (u/bytes-of) (map (fn [i] (b (str "\n(defn- zz-table-headroom-fn" i " [] :i64 0)"))) (range n))) (b "\n"))
    (let [fixed (if (= table "TOK") 11 8)
          _ (chk (>= n fixed) "padding size")
          sizes (let [s (python/list (repeat (quot n 1000) 1000))]
                  (if (or (>= (mod n 1000) fixed) (zero? (python/len s)))
                    (.append s (mod n 1000))
                    (operator/setitem s -1 (+ (operator/getitem s -1) (mod n 1000))))
                  s)]
      (operator/add (bjoin (u/bytes-of) (map-indexed (fn [i k] (operator/add (operator/add (b (str "\n(defn- zz-table-headroom-pad" i " [] :i64 (do ")) (operator/mul (b "1 ") (- k fixed))) (b "0))")))
                                                     sizes))
                    (b "\n")))))

(defn make-probe [compiler out target]
  (let [macho? (u/deq (u/bslice (.read_bytes compiler) 0 4) (u/bytes-of 0xcf 0xfa 0xed 0xfe))
        env (pyenv "PATH" "/nonexistent" "KEXE_ALLOW" "35,37,38,39" "KEXE_CAP_RESOURCES_35" (str out) "KEXE_STACK_BYTES" "8388608" "KEXE_FUEL" "10000000000")
        calls (python/list [])
        last- (atom nil)
        full? (fn [name source extra table]
                (let [src (pathlib/Path out "probe.kotoba") img (pathlib/Path out "probe.elf")
                      _ (.write_bytes src (operator/add (operator/add source (b "\n")) (filler extra table)))
                      p (if macho?
                          ;; local Apple Silicon run: the Mach-O compiler reads through FD3
                          (subprocess/run (python/list ["/bin/sh" "-c" "\"$0\" compile probe.kotoba --target \"$1\" --output probe.elf --format static 3<." (str compiler) target])
                                          ** :cwd out :capture_output true :timeout 600)
                          (subprocess/run (python/list [(str compiler) "compile" (str src) "--target" target "--output" (str img) "--format" "static"])
                                          ** :cwd out :env env :capture_output true :timeout 600))
                      _ (.unlink img ** :missing_ok true)
                      text (operator/add (operator/add (.-stdout p) (.-stderr p)) (b "\n"))
                      filled (vec (filter #(u/has-bytes? (operator/add full-marker (b (str % "\n"))) text) (range 1 10)))
                      region (table-region table)
                      hit (or (some #{region} filled) (and (= table "NODE") (some #{1} filled)))
                      ;; Anything else (a crash, an unrelated table, no stray-form refusal) is not a measurement of this table.
                      valid (or hit (and (empty? filled) (u/has-bytes? (b "E2003") text)) (and (= table "TOK") (= filled [4])))]
                  (chk (and (= (.-returncode p) 1) valid) [name table extra (.-returncode p) (.decode (u/bslice text (max 0 (- (python/len text) 300)) (python/len text)) "utf-8" "replace")])
                  (.append calls (pyenv "build" name "table" table "extra" extra "exit" (.-returncode p) "filledRegions" (python/list filled)))
                  (when hit (reset! last- (first filled)))
                  (boolean hit)))]
    {:calls calls :last last- :full? full?}))

(defn headroom
  "Largest n such that source + n stray entries still fit; observed at n and n + 1."
  [probe name source table guess]
  (let [full? (:full? probe)
        step (if (not= table "FN") 256 16)
        ;; The least probe still needs a stray form: FN filler always ends in a stray `0`; TOK/NODE need one entry.
        least (if (= table "FN") 0 1)
        [lo hi]
        (if (nil? guess)
          (let [lo least hi (* 64 step)]
            (chk (not (full? name source lo table)) [name table "already full"])
            (loop [lo lo hi hi]
              (if (full? name source hi table) [lo hi] (recur hi (* hi 2)))))
          (let [[lo hi width] (loop [lo (max least (- guess step)) hi nil width step]
                                (if (and (> lo least) (full? name source lo table))
                                  (recur (max least (- lo width)) lo (* width 2))
                                  [lo hi width]))
                _ (chk (or (> lo least) (not (full? name source lo table))) [name table "already full"])]
            (if (nil? hi)
              (loop [lo lo hi (+ guess step) width step]
                (if (full? name source hi table) [lo hi] (recur hi (+ hi width) (* width 2))))
              [lo hi])))]
    (loop [lo lo hi hi]
      (if (> (- hi lo) 1)
        (let [mid (quot (+ lo hi) 2)]
          (if (full? name source mid table) (recur lo mid) (recur mid hi)))
        lo))))

(defn verdict [h floor] (if (>= h floor) "PASS" "BELOW_FLOOR"))

(defn run-main [compiler out floors mac-target only]
  (let [active (vec (filter #(or (nil? only) (some #{%} only)) table-names))
        _ (.mkdir out ** :mode 0700 :parents true :exist_ok false)
        data (.read_bytes compiler)
        target (if (u/deq (u/bslice data 0 4) (u/bytes-of 0x7f 0x45 0x4c 0x46))
                 (get {183 "aarch64-linux" 62 "x86_64-linux"} (.from_bytes python/int (u/bslice data 18 20) "little"))
                 (do (chk (and (u/deq (u/bslice data 0 4) (u/bytes-of 0xcf 0xfa 0xed 0xfe)) (= (platform/system) "Darwin")) "an ELF or a local Mach-O compiler")
                     (or mac-target "aarch64-linux")))
        probe (make-probe compiler out target)
        report (pyenv "schema" "amu.native-table-headroom.v1" "status" "running" "compiler" (pin compiler)
                      "observer" (pin (rp "scripts/seed/check-token-headroom-native.cljc")) "target" target
                      "floors" (u/pydict-from (for [t table-names] [t (get floors t)])) "tables" (python/list active)
                      "capacities" (u/pydict-from (for [[t _ c _] tables] [t (capacity c)])) "builds" (python/dict) "negativeControls" (python/dict)
                      "calls" (:calls probe))
        save! (fn [] (.write_text (pathlib/Path out "token-headroom.json") (u/json-dump report)))
        sources (builds)
        src-of (fn [name] (second (first (filter #(= (first %) name) sources))))
        first- (atom {})]
    (doseq [[name source] sources]
      (let [row (u/pydict "source" (u/pydict "bytes" (python/len source) "sha256" (u/sha256-hex source)))]
        (operator/setitem (g report "builds") name row)
        (doseq [table active]
          (let [guess (when-let [[base measured] (get @first- table)]
                        (max 0 (- (+ measured (estimate (src-of base) table)) (estimate source table))))
                n (headroom probe name source table guess)
                _ (when-not (contains? @first- table) (swap! first- assoc table [name n]))
                limited (get regions @(:last probe))]
            (operator/setitem row table (u/pydict "headroom" n "limitedBy" limited "verdict" (verdict n (get floors table))))
            (println (str name " " target ": " table " headroom " n " (full next: " limited "; floor " (get floors table) ")"))
            (.flush sys/stdout)
            (save!)))))
    (doseq [table active]
      (let [floor (get floors table)
            builds-row (g report "builds")
            name (first (sort-by (fn [bn] (g builds-row bn table "headroom")) (python/list (.keys builds-row))))
            measured (g builds-row name table "headroom")]
        (if (or (< measured floor) (not= (g builds-row name table "limitedBy") table))
          (operator/setitem (g report "negativeControls") table (u/pydict "build" name "skipped" "below the floor, or bounded by another table"))
          (let [added (inc (- measured floor))
                grown (operator/add (src-of name) (padding added table))
                fits (not ((:full? probe) (str name "+pad") grown (dec floor) table))
                fills ((:full? probe) (str name "+pad") grown floor table)]
            (chk (and fits fills) ["padding control" table fits fills])
            (chk (= (verdict (dec floor) floor) "BELOW_FLOOR") "verdict")
            (operator/setitem (g report "negativeControls") table (u/pydict "build" name "added" added "headroom" (dec floor) "verdict" "BELOW_FLOOR" "refused" true))
            (println (str "negative control " table ": " name " + " added " -> " (dec floor) " left, refused"))
            (.flush sys/stdout)
            (save!)))))
    (let [low (u/pydict-from (for [[bn r] (.items (g report "builds")) t active :when (not= (g r t "verdict") "PASS")] [(str bn "/" t) (g r t "headroom")]))]
      (operator/setitem report "status" (if (zero? (python/len low)) "PASS_NATIVE_TABLE_HEADROOM" "FAIL_TABLE_HEADROOM_BELOW_FLOOR"))
      (save!)
      (println (g report "status") (if (zero? (python/len low)) "" (json/dumps low)))
      (.flush sys/stdout)
      (when (pos? (python/len low))
        (sys/exit (str "compiler table headroom below its floor: " (python/dict low) "; raise the static capacity (seed/MEMORY-MAP overrides) or shrink the build"))))))

(defn -main [& args]
  (let [floors (reduce (fn [m [k v]] (assoc m k v)) (into {} (for [[t _ _ f] tables] [t f]))
                       (for [[a v] (partition 2 1 args) :when (= a "--floor")
                             :let [[t n] (.split v "=")]]
                         (do (chk (some #{t} table-names) t) [t (python/int n)])))
        tables-arg (u/opt args "--tables")
        only (when tables-arg (vec (.split tables-arg ",")))
        mac-target (u/opt args "--mac-target")]
    (chk (or (nil? only) (and (seq only) (every? #(some #{%} table-names) only))) "--tables names TOK, NODE or FN")
    (run-main (.resolve (pathlib/Path (or (u/opt args "--compiler") (sys/exit "--compiler is required"))))
              (.resolve (pathlib/Path (or (u/opt args "--output") (sys/exit "--output is required"))))
              floors mac-target only)))

(when (some #(or (= % "check-token-headroom-native.cljc") (str/ends-with? % "/check-token-headroom-native.cljc")) sys/argv)
  (apply -main *command-line-args*))
