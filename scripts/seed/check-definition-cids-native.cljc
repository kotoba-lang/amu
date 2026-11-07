;; Observe native `definition-cids` in the full compiler and its candidate harness (JUN-583/JUN-584).
;;
;; Every parse, check, alpha normalization, SCC search, DAG-CBOR encoding and hash runs in Amu native images. This
;; script only stages bytes, launches processes and compares observations. The expected CIDs come from an
;; independently hand-authored oracle image (seed/tests/native-checked-definition-oracle.kotoba, through seed/04's
;; codec), never from the producer. A mutant that changes a seed/05 canonical payload field must be refused.
;;
;; Since JUN-584 the definition layer (04-09) is in FULL-MANIFEST, so the compiler under test (--compiler, the
;; shipped full compiler) answers `definition-cids` itself. Every report case runs on both the compiler and the
;; smaller DEFINITION-CIDS-MANIFEST harness image, and the two must agree byte for byte; mutants are built from
;; the harness. Per-definition refusal (ADR 0300 / the reference `definitions` loop): a definition that cannot be
;; identified is a `name<TAB>REFUSED:<marker>` row, its callers are `dependency-unavailable`, kept CIDs are the
;; CIDs of the same definitions in a module without the refused ones, and `SCANNED` is `<identified>/<total>`.
;; The gate grants nothing. Ported from check-definition-cids-native.py (Basilisp, JUN-974).
;; Run: basilisp run -p scripts/seed scripts/seed/check-definition-cids-native.cljc -- --compiler C --output DIR
(ns check-definition-cids-native
  (:require [basilisp.string :as str]
            [gate-util :as u]
            [macos-image :as macos])
  (:import json operator pathlib platform subprocess sys))

(def oracle-modules ["seed/00-ns-static.kotoba" "seed/01-mem.kotoba" "seed/02-io.kotoba"
                     "seed/03-source-sha256.kotoba" "seed/04-definition-cid.kotoba"
                     "seed/tests/native-checked-definition-oracle.kotoba"])

(defn dfn [name params body]
  (str "(defn " name " [" (str/join " " (map #(str % " :i64") params)) "] :i64 " body ")"))

(defn cycle* [n]
  (vec (for [i (range n)]
         (dfn (python/chr (+ 97 i)) ["x"]
              (str "(if (= x 0) " (- n i) " (" (python/chr (+ 97 (mod (dec i) n))) " (- x 1)))")))))

(def mixed-source
  [(dfn "bad" ["n"] "((fn [x] (+ x 1)) n)") (dfn "f" ["x"] "(+ x 1)")
   (dfn "main" ["x"] "(bad x)") (dfn "caller" ["x"] "(f x)")
   (dfn "s" ["n"] "(loop [i 0 a 0] (if (< i n) (recur (+ i 1) (+ a (bad i))) a))")
   (dfn "t" ["n"] "(loop [i 0 a 0] (if (< i n) (recur (+ i 1) (+ a i)) a))")])

(defn lines-of [s] (vec (.splitlines s)))
(defn row-split [r] (vec (.split r "\t")))
(defn cid-of [d k] (u/geti (u/geti d k) 0))
(defn keys-of [d] (vec (python/list d)))

(defn main [compiler out]
  (let [darwin (macos/available?)
        _ (u/chk (or darwin (and (= "Linux" (platform/system)) (contains? #{"aarch64" "x86_64"} (platform/machine)))))
        target (cond darwin "aarch64-macos" (= "aarch64" (platform/machine)) "aarch64-linux" :else "x86_64-linux")
        root u/root
        _ (.mkdir out ** :parents false :mode 0700 :exist_ok false)
        packager (when darwin (second (macos/root-images)))
        paths (vec (filter #(and (seq %) (not (.startswith % "#")))
                           (.splitlines (.read_text (.joinpath root "seed/DEFINITION-CIDS-MANIFEST")))))
        _ (u/chk (= "seed/99-definition-cids-entry.kotoba" (last paths)))
        _ (u/chk (not (contains? (set paths) "seed/99-entry.kotoba")))
        env (python/dict {"PATH" "/nonexistent" "KEXE_STACK_BYTES" "8388608" "KEXE_FUEL" "10000000000"
                          "KEXE_ALLOW" "35,37,38,39" "KEXE_CAP_RESOURCES_35" (str out)})
        report (u/pydict "schema" "amu.native-definition-cids.v1" "nativeVerdictAuthority" false
                         "host" (python/list [(platform/system) (platform/machine)]) "compiler" (u/pin compiler) "target" target
                         "modules" (u/pydict-from (for [p paths] [p (u/pin (.joinpath root p))])) "calls" (python/list)
                         "scope" "pure checked-source bridge, payload-v2 profile6/desugar2, SCC<=8; no admission"
                         "macosQualified" darwin "compilerHasCommand" true "productionCompilerClosureChanged" true)
        save (fn [] (.write_text (.joinpath out "observations.json") (u/json-dump report)))
        run (fn run
              ([name argv] (run name argv 0))
              ([name argv code]
               (let [p (if darwin
                         ;; FD 3 is the file root; the Mac runtime takes basenames only (KOTOBA-169).
                         (macos/run (first argv) out (for [a (rest argv)] (if (instance? pathlib/Path a) (.-name a) a)))
                         (subprocess/run (python/list (map str argv)) ** :cwd out :env env :capture_output true :timeout 900))]
                 (.append (u/geti report "calls")
                          (u/pydict "name" name "exit" (.-returncode p) "stdoutSHA256" (u/sha256-hex (.-stdout p))
                                    "stderrSHA256" (u/sha256-hex (.-stderr p))))
                 (save)
                 (println name (.-returncode p))
                 (.flush sys/stdout)
                 (u/chk (= code (.-returncode p)) (str name " " (.-returncode p)))
                 [(.decode (.-stdout p)) (.decode (.-stderr p))])))
        build (fn [name text]
                (let [src (.joinpath out (str name ".kotoba"))]
                  (.write_text src text)
                  (if darwin
                    (let [[image unsigned] (macos/build compiler packager out (.-name src) name)]
                      (when-not (contains? report "unsignedImages") (operator/setitem report "unsignedImages" (u/pydict)))
                      (operator/setitem (u/geti report "unsignedImages") name (u/pin unsigned))
                      (save)
                      image)
                    (let [image (.joinpath out (str name ".elf"))]
                      (run (str "build-" name) [compiler "compile" src "--target" target "--output" image "--format" "static"])
                      (.chmod image 0755)
                      image))))
        read-all (fn [ps] (str/join "\n" (for [p ps] (.read_text (.joinpath root p)))))
        text (read-all paths)
        cli (build "definition-cids" text)
        oracle (build "oracle" (read-all oracle-modules))
        swap1 (fn [src old new] (let [t (.replace src old new 1)] (u/chk (not= t src) old) t))
        mutant (build "mutant-encoder" (swap1 text "(dc-entry \"effect-row\" (dcp-effect-row effects))" "(dc-entry \"effect-rowx\" (dcp-effect-row effects))"))
        ;; B1 mutants (JUN-588): the sealed closure head, and a closure encoder that does not bind its parameters.
        mutant-head (build "mutant-fn-head" (swap1 text "(dcp-list (typed-list-new [:list :string] (dcp-sym \"fn\") (dcp-vec names) value))"
                                                    "(dcp-list (typed-list-new [:list :string] (dcp-sym \"fnx\") (dcp-vec names) value))"))
        mutant-keep (build "mutant-fn-unbound" (swap1 text ":string (dcp-bind M A n))\n(defn- dcp-fn [" ":string (dcp-sym \"k0\"))\n(defn- dcp-fn ["))
        ;; JUN-584 per-definition refusal mutants.
        mutant-close (build "mutant-no-close" (swap1 text "        closed (if refused (dsr-close M C Q) 0)]" "        closed 0]"))
        mutant-blocked (build "mutant-no-blocked" (swap1 text "code (cond (dcs-blocked? A X C) 2 (> n 8) 1 :else 0)]" "code (cond false 2 (> n 8) 1 :else 0)]"))
        record-guard "(= (nm-form-head M n) HD-DEFRECORD) (let [bad (dsb-bad C 3 n)] 0)"
        _ (u/chk (= 1 (.count text record-guard)))
        mutant-record (build "mutant-no-record-guard" (swap1 text record-guard "false (let [bad (dsb-bad C 3 n)] 0)"))
        cids (fn cids
               ([name source] (cids name source cli 0 false))
               ([name source image code groups]
                (let [p (.joinpath out (str name ".kotoba"))
                      _ (.write_text p (str (str/join "\n" source) "\n"))
                      argv (concat [image "definition-cids" p] (when groups ["--groups"]))
                      tag (str name (when groups "-groups"))
                      [stdout stderr] (run (str "cids-" tag) argv code)]
                  (when (identical? image cli)
                    ;; The shipped full compiler answers the same question with the same bytes (JUN-584).
                    (let [[fo fe] (run (str "full-cids-" tag) (cons compiler (rest argv)) code)]
                      (u/chk (and (= fo stdout) (= fe stderr)) (str "full compiler disagrees: " name))))
                  (if (pos? code)
                    (do (u/chk (and (= "" stdout) (.startswith stderr "DSB:")) name)
                        (u/pydict))
                    (let [_ (u/chk (= "" stderr) name)
                          ls (lines-of stdout)
                          rows (mapv row-split (butlast ls))
                          refused? (fn [r] (.startswith (second r) "REFUSED:"))
                          identified (count (remove refused? rows))]
                      ;; ADR 0300: one row per definition in declaration order, `name<TAB>CID` or
                      ;; `name<TAB>REFUSED:<marker>`, then SCANNED<TAB><identified>/<total>.
                      (u/chk (= (last ls) (str "SCANNED\t" identified "/" (count rows))) (last ls))
                      (u/chk (and (every? #(= (count %) (if groups 4 2)) rows) (= (count (set (map first rows))) (count rows))) name)
                      (u/chk (every? #(not= "DCP1" (first %)) rows))
                      (u/chk (every? #(= (vec (drop 2 %)) ["-" "-1"]) (filter #(and groups (refused? %)) rows)))
                      (u/chk (every? #(and (.startswith (second %) "bafyrei") (= 59 (count (second %)))) (remove refused? rows)))
                      (u/pydict-from (for [r rows] [(first r) (python/list (rest r))])))))))
        cids1 (fn [name source] (cids name source cli 0 false))
        golden (fn [name]
                 (let [[stdout _] (run (str "oracle-" name) [oracle name])
                       s (.strip stdout)]
                   (u/chk (= 59 (count s)) name)
                   s))
        order (.joinpath out "order.kotoba")
        _ (.write_text order (str (dfn "zeta" ["x"] "(+ x 1)") "\n" (dfn "alpha" ["x"] "(+ x 2)") "\n"))
        [order-out _] (run "order" [cli "definition-cids" order])
        _ (u/chk (= ["zeta" "alpha" "SCANNED"] (mapv #(first (row-split %)) (lines-of order-out))) order-out)
        _ (u/chk (= order-out (first (run "full-order" [compiler "definition-cids" order]))))
        const (cids1 "const" [(dfn "main" [] "42")])
        _ (u/chk (= (cid-of const "main") (golden "const")))
        leaf (cids1 "leaf" [(dfn "f" ["x"] "(+ x 1)")])
        _ (u/chk (= (cid-of leaf "f") (golden "leaf")))
        _ (u/chk (u/deq (u/geti (cids1 "rename" [(dfn "zz" ["another"] "(+ another 1)")]) "zz") (u/geti leaf "f")))
        caller (cids1 "caller" [(dfn "f" ["x"] "(+ x 1)") (dfn "main" ["x"] "(f x)")])
        _ (u/chk (and (u/deq (u/geti caller "f") (u/geti leaf "f")) (= (cid-of caller "main") (golden "caller"))))
        _ (u/chk (u/deq (cids1 "reordered" [(dfn "main" ["y"] "(f y)") (dfn "f" ["a"] "(+ a 1)")]) caller))
        edit (cids1 "dependency-edit" [(dfn "f" ["x"] "(+ x 2)") (dfn "main" ["x"] "(f x)")])
        _ (u/chk (and (= (cid-of edit "f") (golden "leaf2")) (= (cid-of edit "main") (golden "caller2"))))
        _ (u/chk (not= (cid-of edit "main") (cid-of caller "main")))
        _ (u/chk (= (cid-of (cids1 "self" [(dfn "f" ["x"] "(if (= x 0) 1 (f (- x 1)))")]) "f") (golden "self")))
        ;; --groups keeps group/SCC information: same CIDs, plus group CID and member index.
        flat (cids1 "cycle2-flat" (cycle* 2))
        grouped (cids "cycle2" (cycle* 2) cli 0 true)
        cid-map (fn [d] (into {} (for [k (keys-of d)] [k (cid-of d k)])))
        _ (u/chk (= (cid-map grouped) (cid-map flat)))
        _ (u/chk (and (= #{"0" "1"} (set (for [k (keys-of grouped)] (u/geti (u/geti grouped k) 2))))
                      (= (u/geti (u/geti grouped "a") 1) (u/geti (u/geti grouped "b") 1))
                      (not= "-" (u/geti (u/geti grouped "a") 1))))
        _ (u/chk (and (= (cid-of grouped "b") (golden "cycle2-first")) (= (cid-of grouped "a") (golden "cycle2-second"))))
        eight (cids "cycle8" (cycle* 8) cli 0 true)
        _ (doseq [i (range 8)] (u/chk (= (cid-of eight (python/chr (- 104 i))) (golden (str "c8-" i)))))
        ;; B1 local closures (JUN-588). Expected CIDs are hand-authored payloads in the oracle image, never the producer.
        clo (cids1 "closure" [(dfn "f" ["n"] "(let [g (fn [x] (+ x 1))] (g n))")])
        _ (u/chk (= (cid-of clo "f") (golden "closure")))
        ;; Renaming the lambda parameter, the let name and the definition leaves the CID alone; the body does not.
        _ (u/chk (u/deq (u/geti (cids1 "closure-renamed" [(dfn "zz" ["m"] "(let [h (fn [y] (+ y 1))] (h m))")]) "zz") (u/geti clo "f")))
        _ (u/chk (not= (cid-of (cids1 "closure-body" [(dfn "f" ["n"] "(let [g (fn [x] (+ x 2))] (g n))")]) "f") (cid-of clo "f")))
        ;; Observation (pinned, not a claim of equivalence): a closure keeps its own identity; the hand-inlined body is the leaf.
        inlined (cids1 "closure-inlined" [(dfn "f" ["n"] "(+ n 1)")])
        _ (u/chk (and (= (cid-of inlined "f") (golden "leaf")) (not= (cid-of inlined "f") (cid-of clo "f"))))
        _ (operator/setitem report "observations"
                            (u/pydict "closureLetFn" (cid-of clo "f") "handInlined" (cid-of inlined "f") "equal" false
                                      "closureReferenceParity" false
                                      "note" "native-only closure identity; the reference lambda-lifts and leaks the module lambda counter; no parity claimed"))
        ;; A captured outer local is a binder reference: its name does not matter, which binder it is does.
        cap (cids1 "closure-capture" [(dfn "f" ["n"] "(let [k 5 g (fn [x] (+ x k))] (g n))")])
        _ (u/chk (= (cid-of cap "f") (golden "closure-capture")))
        _ (u/chk (u/deq (cids1 "closure-capture-renamed" [(dfn "f" ["n"] "(let [m 5 q (fn [z] (+ z m))] (q n))")]) cap))
        pick-k (cids1 "closure-capture-k" [(dfn "f" ["n"] "(let [k 5 j 6 g (fn [x] (+ x k))] (g n))")])
        pick-j (cids1 "closure-capture-j" [(dfn "f" ["n"] "(let [k 5 j 6 g (fn [x] (+ x j))] (g n))")])
        _ (u/chk (not= (cid-of pick-k "f") (cid-of pick-j "f")))
        _ (u/chk (not= (cid-of (cids1 "closure-param-vs-capture-a" [(dfn "f" ["n"] "(let [g (fn [x] (+ x n))] (g n))")]) "f")
                       (cid-of (cids1 "closure-param-vs-capture-b" [(dfn "f" ["n"] "(let [g (fn [x] (+ x x))] (g n))")]) "f")))
        ;; A top-level definition referenced inside the body is a direct dependency (by CID).
        dep (cids1 "closure-dep" [(dfn "h" ["x"] "(+ x 1)") (dfn "f" ["n"] "(let [g (fn [y] (h y))] (g n))")])
        _ (u/chk (and (= (cid-of dep "h") (golden "leaf")) (= (cid-of dep "f") (golden "closure-dep"))))
        dep2 (cids1 "closure-dep-edit" [(dfn "h" ["x"] "(+ x 2)") (dfn "f" ["n"] "(let [g (fn [y] (h y))] (g n))")])
        _ (u/chk (not= (cid-of dep2 "f") (cid-of dep "f")))
        _ (u/chk (= (cid-of (cids1 "closure-nested" [(dfn "f" ["n"] "(let [g (fn [x] (let [h (fn [y] (+ y x))] (h n)))] (g 1))")]) "f")
                    (golden "closure-nested")))
        _ (u/chk (= (cid-of (cids1 "closure-two" [(dfn "f" ["n"] "(let [a 1 b 2 g (fn [x] (+ x (+ a b)))] (g n))")]) "f")
                    (golden "closure-two")))
        refuse (fn [name source] (cids name source cli 66 false))]
    ;; Negative controls: the gate must refuse / detect, not merely pass. A module the frontend rejects has no
    ;; identity at all: exit 66, empty stdout, a named DSB: diagnostic.
    (refuse "refuse-unbound" [(dfn "f" ["x"] "(missing x)")])
    (refuse "refuse-syntax" ["(defn f [x :i64] :i64 (+ x 1)"])
    ;; No definition at all is no identity (reference: `:entries :unavailable`), not an empty report.
    (refuse "refuse-no-definitions" ["(def k 5)"])
    ;; Constructor identities for defrecord are not bridged; never emit a partial report even when the generated
    ;; constructor is unused.
    (doseq [[suffix fun] [["unused" "(defn- f [] :i64 42)"] ["referenced" "(defn- f [x [:ref :demo/Pair]] :i64 42)"]]]
      (refuse (str "refuse-defrecord-" suffix) ["(ns demo (:export []))" "(defrecord Pair [a :i64 b :string])" fun]))
    ;; Executing the removed-guard mutant demonstrates the omission: it reports f but not the implicitly generated
    ;; ->Pair constructor.
    (let [record-mutant (cids "mutant-defrecord-unused" ["(ns demo (:export []))" "(defrecord Pair [a :i64 b :string])" "(defn- f [] :i64 42)"]
                              mutant-record 0 false)]
      (u/chk (= ["f"] (keys-of record-mutant))))
    (refuse "refuse-closure-unbound" [(dfn "f" ["n"] "(let [g (fn [x] (+ x missing))] (g n))")])
    (refuse "refuse-closure-callback" ["(defn ap [g [:fn [:i64] :i64] x :i64] :i64 (g x))" (dfn "f" ["n"] "(ap (fn [x] (+ x 1)) n)")])
    ;; A checked definition the bridge cannot express is refused PER DEFINITION (JUN-584), never a wrong CID:
    ;; exit 0, a REFUSED:unbridged-source row, SCANNED 0/1.
    (doseq [[name body] [["closure-in-loop" "(loop [i 0] (if (< i n) (let [g (fn [x] (+ x i))] (recur (+ i (g 1)))) i))"]
                         ["loop-in-closure" "(let [g (fn [x] (loop [i 0] (if (< i x) (recur (+ i 1)) i)))] (g n))"]
                         ["closure-operator" "((fn [x] (+ x 1)) n)"]]]
      (u/chk (u/deq (cids1 (str "refuse-" name) [(dfn "f" ["n"] body)]) (u/pydict "f" (python/list ["REFUSED:unbridged-source"])))))
    ;; Abort control rows are not yet sealed from fresh source facts. The public report must refuse both escaping and
    ;; caught aborts; it must not give their transitive callers an identity or poison independent rows.
    (let [aborting "(defn- bad [x :i64] :i64 (if (= x 0) (throw 7) x))"
          caller-abort "(defn- caller [x :i64] :i64 (bad x))"
          caught-direct "(defn- direct [x :i64] :i64 (try (if (= x 0) (throw 7) x) (catch :i64 e (+ e 2))))"
          caught-callee "(defn- caught [x :i64] :i64 (try (bad x) (catch :i64 e (+ e 2))))"
          throwing-handler "(defn- handler [x :i64] :i64 (try (if (= x 0) (throw x) 4) (catch :i64 e (throw (+ e 1)))))"
          abort-cases [aborting caller-abort caught-direct caught-callee throwing-handler (dfn "clean" ["x"] "(+ x 1)")]]
      (doseq [g [false true]]
        (let [rows (cids "abort-report" abort-cases cli 0 g)]
          (u/chk (= ["bad" "caller" "direct" "caught" "handler" "clean"] (keys-of rows)))
          (u/chk (every? #(= "REFUSED:unbridged-source" (cid-of rows %)) ["bad" "direct" "caught" "handler"]))
          (u/chk (= "REFUSED:dependency-unavailable" (cid-of rows "caller")))
          (u/chk (= (golden "leaf") (cid-of rows "clean")))))
      (cids "mutant-no-close-abort" abort-cases mutant-close 66 false))
    ;; Explicit namespace record schemas reach the report bridge; an unrelated unsupported row and its caller
    ;; remain refused without changing f's CID.
    (let [schema-ns "(ns demo (:export []) (:schemas {:s/r [:record :s/r [[:a :i64]]]}))"
          schema-fn "(defn- f [x [:ref :s/r]] :i64 42)"
          schema-leaf (cids1 "schema-leaf" [schema-ns schema-fn])
          _ (u/chk (= "bafyreiagssxmxbxfy7i3zq4m6ayucfkyjylomcruexauvgvw6dtjqtfeeu" (cid-of schema-leaf "f")))
          schema-mixed (cids1 "schema-mixed" [schema-ns (dfn "bad" ["n"] "((fn [x] (+ x 1)) n)") schema-fn (dfn "caller" ["x"] "(bad x)")])]
      (u/chk (= "REFUSED:unbridged-source" (cid-of schema-mixed "bad")))
      (u/chk (= "REFUSED:dependency-unavailable" (cid-of schema-mixed "caller")))
      (u/chk (u/deq (u/geti schema-mixed "f") (u/geti schema-leaf "f"))))
    ;; Per-definition refusal parity with the reference shape: the refused row keeps its place in declaration order,
    ;; its callers are dependency-unavailable (also through a loop helper), everything else keeps the CID it has in
    ;; a module without the refused definitions.
    (let [mixed-src mixed-source
          mixed (cids "mixed" mixed-src cli 0 true)
          _ (u/chk (= ["bad" "f" "main" "caller" "s" "t" "__kotoba_loop_2"] (keys-of mixed)) (keys-of mixed))
          _ (u/chk (= "REFUSED:unbridged-source" (cid-of mixed "bad")))
          _ (u/chk (= "REFUSED:dependency-unavailable" (cid-of mixed "main") (cid-of mixed "s")))
          _ (u/chk (and (= (cid-of mixed "f") (golden "leaf")) (= (cid-of mixed "caller") (golden "caller"))))
          kept (cids "mixed-kept" [(nth mixed-src 1) (nth mixed-src 3) (nth mixed-src 5)] cli 0 true)]
      (u/chk (= ["f" "caller" "t" "__kotoba_loop_1"] (keys-of kept)) (keys-of kept))
      (u/chk (every? #(u/deq (u/geti kept %) (u/geti mixed %)) ["f" "caller" "t"]))
      (u/chk (u/deq (u/geti kept "__kotoba_loop_1") (u/geti mixed "__kotoba_loop_2"))))
    ;; A recursive group above the scc-v1 bound (8) is refused member by member, never hashed by name; its caller is
    ;; dependency-unavailable, an independent definition is identified.
    (let [nine (cids "cycle9" (concat (cycle* 9) [(dfn "main" ["x"] "(a x)") (dfn "z" ["x"] "(+ x 1)")]) cli 0 true)]
      (u/chk (every? #(= "REFUSED:recursive-group-too-large" (cid-of nine (python/chr (+ 97 %)))) (range 9)))
      (u/chk (and (= "REFUSED:dependency-unavailable" (cid-of nine "main")) (= (golden "leaf") (cid-of nine "z")))))
    ;; Every row refused is still a report (exit 0, SCANNED 0/n), not "no identity" (66).
    (let [only (cids1 "cycle9-only" (cycle* 9))]
      (u/chk (= #{"REFUSED:recursive-group-too-large"} (set (for [k (keys-of only)] (cid-of only k))))))
    (operator/setitem (u/geti report "observations") "perDefinitionRefusal"
                      (u/pydict "markers" (python/list ["unbridged-source" "dependency-unavailable" "recursive-group-too-large" "unbridged-effect"])
                                "nativeOnlyMarkers" (python/list ["unbridged-source"])
                                "referenceShape" "src/kotoba/compiler/definition_identity.cljk" "referenceRouteExecuted" false))
    ;; Mutants of the per-definition layer must not reproduce the report: dropping the dependency closure leaves a
    ;; caller of a refused definition in the KIR (the fresh check refuses the module), dropping the blocked-
    ;; component test makes the producer meet a hole (refused whole). Neither may print a CID for main.
    (cids "mutant-no-close" mixed-source mutant-close 66 false)
    (cids "mutant-no-blocked" (concat (cycle* 9) [(dfn "main" ["x"] "(a x)")]) mutant-blocked 66 false)
    ;; A producer with a changed payload field is refused by its own canonical validator (04) -- no CID leaks.
    (cids "mutant-encoder" [(dfn "f" ["x"] "(+ x 1)")] mutant 66 false)
    ;; The closure encoder mutants must not reproduce the oracle CID (head spelling), and the one that never binds the
    ;; parameter must not produce a CID (the body's reference is then unbound: refused).
    (let [moved (cids "mutant-fn-head" [(dfn "f" ["n"] "(let [g (fn [x] (+ x 1))] (g n))")] mutant-head 0 false)]
      (u/chk (not= (cid-of moved "f") (golden "closure"))))
    (u/chk (= (cid-of (cids "mutant-fn-head-plain" [(dfn "f" ["x"] "(+ x 1)")] mutant-head 0 false) "f") (golden "leaf")))
    (cids "mutant-fn-unbound" [(dfn "f" ["n"] "(let [g (fn [x] (+ x 1))] (g n))")] mutant-keep 66 false)
    ;; Usage errors are not "no identity": distinct exit code.
    (doseq [[image tag] [[cli ""] [compiler "full-"]]]
      (run (str tag "usage-extra-arg") [image "definition-cids" order "--nope"] 2)
      (run (str tag "usage-missing-file-arg") [image "definition-cids"] 2))
    ;; JUN-579: `.cljk` is input sugar through the same frontend. A sugar spelling and its pure `.kotoba` spelling
    ;; mint one CID, a meaning change does not, and retired extensions are usage errors with no report.
    (let [spelled (fn [name suffix source]
                    (let [p (.joinpath out (str name suffix))]
                      (.write_text p (str (str/join "\n" source) "\n"))
                      p))
          rows (fn rows
                 ([name path] (rows name path cli))
                 ([name path image]
                  (let [[stdout stderr] (run name [image "definition-cids" path])]
                    (u/chk (= "" stderr) name)
                    (u/pydict-from (for [r (butlast (lines-of stdout))] (row-split r))))))
          g (dfn "g" ["x"] "(+ x 1)")
          pure (rows "cljk-pure" (spelled "cljk-pure" ".kotoba" [g (dfn "f" ["n"] "(g (g n))")]))]
      (doseq [[image tag] [[cli ""] [compiler "full-"]]]
        (let [same (rows (str tag "cljk-same-text") (spelled (str tag "cljk-same-text") ".cljk" [g (dfn "f" ["n"] "(g (g n))")]) image)
              sugar (rows (str tag "cljk-thread") (spelled (str tag "cljk-thread") ".cljk" [g (dfn "f" ["n"] "(-> n g g)")]) image)
              control (rows (str tag "cljk-control") (spelled (str tag "cljk-control") ".cljk" [g (dfn "f" ["n"] "(-> n g)")]) image)
              branch (rows (str tag "cljk-reader-branch")
                           (spelled (str tag "cljk-reader-branch") ".cljk" [g (dfn "f" ["n"] "#?(:kotoba (g (g n)) :clj (g n))")]) image)]
          (u/chk (u/deq same pure) (str tag "same"))
          (u/chk (u/deq sugar pure) (str tag "sugar"))
          (u/chk (and (not= (u/geti control "f") (u/geti pure "f")) (= (u/geti control "g") (u/geti pure "g"))) (str tag "control"))
          (u/chk (u/deq branch pure) (str tag "branch"))
          (doseq [suffix [".cljc" ".cljs" ".clj" ".txt"]]
            (let [[stdout _] (run (str tag "retired" suffix) [image "definition-cids" (spelled (str tag "retired") suffix [g])] 2)]
              (u/chk (= "" stdout) (str tag suffix))))))
      (let [[stdout _] (run "full-check-cljk" [compiler "check" (spelled "full-check-cljk" ".cljk" [g])])]
        (u/chk (= "ok" (.strip stdout)) stdout))
      (run "full-check-cljc" [compiler "check" (spelled "full-check-cljc" ".cljc" [g])] 2)
      (run "full-compile-cljk" [compiler "compile" (spelled "full-compile-cljk" ".cljk" [g])] 2))
    ;; The unchanged core driver still answers its own commands through this entry.
    (let [ok (.joinpath out "ok.kotoba")]
      (.write_text ok (str (dfn "f" ["x"] "(+ x 1)") "\n"))
      (let [[stdout _] (run "driver-check" [cli "check" ok])]
        (u/chk (= "ok" (.strip stdout)) stdout)))
    (operator/setitem report "status" "PASS_NATIVE_DEFINITION_CIDS")
    (save)
    (println (u/geti report "status"))
    (.flush sys/stdout)))

(defn -main [& args]
  (main (.resolve (pathlib/Path (or (u/opt args "--compiler") (sys/exit "--compiler is required"))))
        (.resolve (pathlib/Path (or (u/opt args "--output") (sys/exit "--output is required"))))))

(when (some #(or (= % "check-definition-cids-native.cljc") (str/ends-with? % "/check-definition-cids-native.cljc")) sys/argv)
  (apply -main *command-line-args*))
