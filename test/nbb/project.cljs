(ns test.nbb.project
  (:require [kotoba.sema :as sema]
            [kotoba.kir :as ir]
            [kotoba.compiler.project :as project]
            [kotoba.compiler.nbb.module-lock :as module-lock]
            [kotoba.compiler.nbb.project-files :as project-files]
            ["node:fs" :as fs]
            ["node:os" :as os]
            ["node:path" :as path]))

(def sources
  {'example.text
   "(ns example.text (:export [greet]))
    (defn greet [name :string] :string (string-concat \"こんにちは、\" name))"
   'example.app
   "(ns example.app (:require [example.text :as text]) (:export [welcome]))
    (defn welcome [name :string] :string (text/greet name))"})

;; The same shape, carrying integers, and that difference is the whole point.
;; `link-source` prints the linked module graph back to source text for the
;; reader to read again. On ClojureScript the reader returns integer literals
;; as JS BigInt and `pr-str` renders a BigInt as `#object[BigInt 42]`, which the
;; reader then refuses -- so linking failed for every project containing a
;; number. The fixture above is strings only, so this test ran on the right
;; function, on the right runtime, and passed for four months without ever
;; touching the defect. Measured 2026-08-31 against aiueos: every one of its
;; objects that got as far as this step died here.
(def numeric-sources
  {'example.math
   "(ns example.math (:export [double-it]))
    (defn double-it [n :i64] :i64 (* n 2))"
   'example.calc
   "(ns example.calc (:require [example.math :as math]) (:export [compute]))
    (defn compute [n :i64] :i64 (+ (math/double-it n) 1))"})

(defn- check [label thunk]
  (try (thunk) (println "PASS" label)
       (catch :default error
         (println "FAIL" label (.-message error))
         (.exit js/process 1))))

(check "safe-project-link"
  (fn []
    (let [{:keys [source module-order]} (project/link-source sources 'example.app)
          kir (ir/lower (sema/analyze source))]
      (assert (= ['example.text 'example.app] module-order))
      (assert (= "こんにちは、言葉" (ir/execute kir 'welcome ["言葉"]))))))

(check "linked-source-round-trips-integers"
  (fn []
    (let [{:keys [source module-order]} (project/link-source numeric-sources 'example.calc)]
      (assert (= ['example.math 'example.calc] module-order))
      ;; The linked text must be readable by the reader that will read it.
      (assert (not (re-find #"#object" source))
              (str "linked source is not readable: " (subs source 0 (min 200 (count source)))))
      ;; And it must still mean what it meant.
      (let [kir (ir/lower (sema/analyze source))]
        (assert (= 43 (js/Number (ir/execute kir 'compute [21]))))))))

;; ---------------------------------------------------------------------------
;; Filesystem graph discovery
;;
;; `link-source` above takes a source MAP, so everything above this line passes
;; whether or not a namespace can be found on disk. Resolution is the half that
;; was JVM-only, and it is also the half that carries the confinement rules --
;; which means until now nothing on this runtime exercised them.
;;
;; Each rejection below asserts the MESSAGE, not merely that something threw.
;; A control that only checks for failure counts a run that died for an
;; unrelated reason as a success, and these five failures are easy to confuse:
;; they all end with a module that did not load.

(defn- tmpdir []
  (.mkdtempSync fs (.join path (.tmpdir os) "kotoba-project-files-")))

(defn- spit! [dir name text]
  (.mkdirSync fs dir #js {:recursive true})
  (let [p (.join path dir name)]
    (.writeFileSync fs p text "utf8")
    p))

(def ^:private entry
  "(ns main (:require [util :as u]) (:export [run]))
   (defn run [x :i64] :i64 (+ 1 (u/twice x)))")

(defn- util [factor]
  (str "(ns util (:export [twice]))\n(defn twice [x :i64] :i64 (* " factor " x))"))

(defn- rejects [thunk expected]
  (try (thunk)
       (str "expected a rejection carrying " (pr-str expected) ", got none")
       (catch :default error
         (when-not (= expected (.-message error))
           (str "expected " (pr-str expected) ", got " (pr-str (.-message error)))))))

(check "filesystem-graph-links-and-runs"
  (fn []
    (let [root (tmpdir)
          main (spit! root "main.cljk" entry)
          _ (spit! root "util.cljk" (util 2))
          graph (project-files/load-closed-graph main [root])
          {:keys [source module-order]} (project/link-source (:sources graph) (:root graph))]
      (assert (= 'main (:root graph)))
      (assert (= ['util 'main] module-order))
      ;; Not just that it linked -- that the OTHER module's code is what ran.
      (let [kir (ir/lower (sema/analyze source {:admit-linked-synthetics? true}))]
        (assert (= 11 (js/Number (ir/execute kir 'run [5]))))))))

(check "missing-module-is-named"
  (fn []
    (let [root (tmpdir)
          main (spit! root "main.cljk" entry)]
      (when-let [failure (rejects #(project-files/load-closed-graph main [root])
                                  "required module is missing from the explicit source paths")]
        (throw (js/Error. failure))))))

(check "namespace-in-two-roots-is-ambiguous-not-ordered"
  (fn []
    (let [a (tmpdir) b (tmpdir)
          main (spit! a "main.cljk" entry)
          _ (spit! a "util.cljk" (util 2))
          _ (spit! b "util.cljk" (util 3))]
      ;; Both argument orders, because "first root wins" would pass one of them.
      (doseq [roots [[a b] [b a]]]
        (when-let [failure (rejects #(project-files/load-closed-graph main roots)
                                    "namespace resolves from multiple explicit source paths")]
          (throw (js/Error. failure)))))))

(check "symlink-out-of-the-root-is-refused"
  (fn []
    (let [root (tmpdir) outside (tmpdir)
          main (spit! root "main.cljk" entry)
          target (spit! outside "util.cljk" (util 9))]
      (.symlinkSync fs target (.join path root "util.cljk"))
      (when-let [failure (rejects #(project-files/load-closed-graph main [root])
                                  "project module escapes the explicit source paths")]
        (throw (js/Error. failure))))))

(check "sibling-directory-sharing-a-prefix-is-outside"
  (fn []
    ;; The control the plain string comparison fails. `<tmp>/src-evil` starts
    ;; with `<tmp>/src`, so a prefix test admits it; containment is per path
    ;; SEGMENT. Verified by breaking it: with `str/starts-with?` alone this
    ;; case links and exits 0.
    (let [base (tmpdir)
          root (.join path base "src")
          evil (.join path base "src-evil")
          main (spit! root "main.cljk" entry)
          target (spit! evil "util.cljk" (util 7))]
      (.symlinkSync fs target (.join path root "util.cljk"))
      (when-let [failure (rejects #(project-files/load-closed-graph main [root])
                                  "project module escapes the explicit source paths")]
        (throw (js/Error. failure))))))

(check "declared-namespace-must-match-the-requirement"
  (fn []
    (let [root (tmpdir)
          main (spit! root "main.cljk" entry)
          _ (spit! root "util.cljk" "(ns other (:export [twice]))\n(defn twice [x :i64] :i64 (* 2 x))")]
      (when-let [failure (rejects #(project-files/load-closed-graph main [root])
                                  "resolved path namespace does not match requirement")]
        (throw (js/Error. failure))))))

(check "source-root-must-be-a-directory"
  (fn []
    (let [root (tmpdir)
          main (spit! root "main.cljk" entry)
          file (spit! root "util.cljk" (util 2))]
      (when-let [failure (rejects #(project-files/load-closed-graph main [file])
                                  "source path must be a readable directory")]
        (throw (js/Error. failure))))))

;; ---------------------------------------------------------------------------
;; CID-pinned graph discovery
;;
;; The property under test is not "it can find the files" -- the path resolver
;; above already does that. It is that resolution is CLOSED: what gets compiled
;; is exactly what the lock names, proven by hash, with no path search
;; available as a fallback when the lock is wrong or incomplete. Every
;; rejection is asserted by its MESSAGE, and each message is byte-identical to
;; the one `kotoba.compiler.module-lock` raises on the JVM, so a caller that
;; matches on it gets one answer from both routes.

(defn- blocks-dir []
  (.mkdtempSync fs (.join path (.tmpdir os) "kotoba-blocks-")))

(def ^:private lib-source
  "(ns example.lib (:export [answer])) (defn answer [] :i64 42)")

(def ^:private app-source
  "(ns example.root (:require [example.lib :as lib]) (:export [main]))
   (defn main [] :i64 (lib/answer))")

(defn- write-lock!
  "Persist SOURCES as blocks and write a lock naming ROOT."
  [sources root]
  (let [blocks (blocks-dir)
        lock (.join path (tmpdir) "kotoba.modules.edn")
        modules (into (sorted-map)
                      (map (fn [[namespace source]]
                             [namespace (module-lock/write-block! blocks source)]))
                      sources)]
    (.writeFileSync fs lock
                    (pr-str {:schema module-lock/lock-schema :root root :modules modules})
                    "utf8")
    {:blocks blocks :lock lock :modules modules}))

;; Golden vectors, produced by the JVM twin (`multiformats.core/cidv1-raw`,
;; which is also what `ipfs add --cid-version=1 --raw-leaves` produces for a
;; single block). This file assembles the CID from node:crypto's SHA-256 and
;; `multiformats.base32` rather than loading `multiformats.core`, whose
;; ClojureScript branch needs an npm package Amu does not depend on. That
;; shortcut is only safe if the digest is the SAME digest -- a resolver that
;; verified against its own private hash would accept every block and reject
;; every lock written by the other route, while looking exactly like this one.
(check "cid-matches-the-jvm-twin"
  (fn []
    (let [blocks (blocks-dir)]
      (assert (= "bafkreicnabst32iqvrylj36cgn2cm2xfywgxyyoielxnejmqywmcaswmbi"
                 (module-lock/write-block!
                  blocks "(ns util (:export [twice]))\n(defn twice [x :i64] :i64 (* 2 x))\n")))
      (assert (= "bafkreibqtanjq6cttjjq6eywse4a3ryai5txbtswhimcuodgbwnvqx6u3a"
                 (module-lock/write-block!
                  blocks (str "(ns main (:require [util :as u]) (:export [run]))\n"
                              "(defn run [x :i64] :i64 (+ 1 (u/twice x)))\n"))))
      ;; And the identity of the whole pinned input set, not just of one block.
      (assert (= "bafkreibhyfwgozu7dmqhxz2fq7h2xkhmcnmwie4duqf56hx6v2bjy7szvy"
                 (module-lock/lock-cid
                  {:root 'main
                   :modules {'main "bafkreibqtanjq6cttjjq6eywse4a3ryai5txbtswhimcuodgbwnvqx6u3a"
                             'util "bafkreicnabst32iqvrylj36cgn2cm2xfywgxyyoielxnejmqywmcaswmbi"}}))))))

(check "locked-graph-links-and-runs"
  (fn []
    (let [{:keys [blocks lock]} (write-lock! {'example.lib lib-source
                                              'example.root app-source}
                                             'example.root)
          graph (module-lock/load-locked-graph lock blocks)
          {:keys [source module-order]} (project/link-source (:sources graph) (:root graph))]
      (assert (= 'example.root (:root graph)))
      (assert (= #{'example.lib 'example.root} (set (keys (:sources graph)))))
      (assert (string? (:lock-cid graph)))
      (assert (= ['example.lib 'example.root] module-order))
      ;; Not just that it linked -- that the pinned dependency's code is what ran.
      (let [kir (ir/lower (sema/analyze source {:admit-linked-synthetics? true}))]
        (assert (= 42 (js/Number (ir/execute kir 'main []))))))))

(check "a-block-that-does-not-hash-to-its-cid-is-refused"
  (fn []
    (let [{:keys [blocks lock modules]} (write-lock! {'example.lib lib-source
                                                      'example.root app-source}
                                                     'example.root)]
      ;; Same filename, different bytes: the only thing standing between this
      ;; and a silently different build is the hash check.
      (.writeFileSync fs (.join path blocks (get modules 'example.lib))
                      "(ns example.lib (:export [answer])) (defn answer [] :i64 0)" "utf8")
      (when-let [failure (rejects #(module-lock/load-locked-graph lock blocks)
                                  "locked module block does not hash to its CID")]
        (throw (js/Error. failure))))))

(check "an-unpinned-dependency-stops-the-build-instead-of-being-searched-for"
  (fn []
    ;; example.lib is written as a block, and in the path-resolved world it
    ;; would also be sitting next to its requirer. Here it simply is not
    ;; pinned, and that is fatal rather than a reason to go looking.
    (let [{:keys [blocks lock]} (write-lock! {'example.root app-source} 'example.root)]
      (when-let [failure (rejects #(module-lock/load-locked-graph lock blocks)
                                  "required module is not pinned by the lock")]
        (throw (js/Error. failure))))))

(check "a-block-declaring-a-different-namespace-is-refused"
  (fn []
    (let [{:keys [blocks lock modules]} (write-lock! {'example.lib lib-source
                                                      'example.root app-source}
                                                     'example.root)
          impostor (module-lock/write-block!
                    blocks "(ns example.other (:export [answer])) (defn answer [] :i64 1)")
          tampered (.join path (.dirname path lock) "tampered.edn")]
      (.writeFileSync fs tampered
                      (pr-str {:schema module-lock/lock-schema
                               :root 'example.root
                               :modules (assoc modules 'example.lib impostor)})
                      "utf8")
      (when-let [failure (rejects #(module-lock/load-locked-graph tampered blocks)
                                  "locked module declares a different namespace")]
        (throw (js/Error. failure))))))

(check "a-missing-block-is-not-a-reason-to-look-elsewhere"
  (fn []
    (let [{:keys [blocks lock modules]} (write-lock! {'example.lib lib-source
                                                      'example.root app-source}
                                                     'example.root)]
      (.rmSync fs (.join path blocks (get modules 'example.lib)))
      (when-let [failure (rejects #(module-lock/load-locked-graph lock blocks)
                                  "locked module block is missing from the block store")]
        (throw (js/Error. failure))))))

(check "a-cid-that-is-not-a-plain-base32-cid-is-refused-before-any-read"
  (fn []
    ;; `../` in a pinned name would be a path, and a path is the one thing a
    ;; lock is supposed to have removed. Rejected on the shape, before the
    ;; block store is touched.
    (let [{:keys [blocks lock modules]} (write-lock! {'example.lib lib-source
                                                      'example.root app-source}
                                                     'example.root)
          tampered (.join path (.dirname path lock) "escaping.edn")]
      (.writeFileSync fs tampered
                      (pr-str {:schema module-lock/lock-schema
                               :root 'example.root
                               :modules (assoc modules 'example.lib "../../etc/passwd")})
                      "utf8")
      (when-let [failure (rejects #(module-lock/load-locked-graph tampered blocks)
                                  "module CID is not a plain base32 CIDv1")]
        (throw (js/Error. failure))))))

(check "a-lock-that-does-not-pin-its-own-root-is-refused"
  (fn []
    (let [lock (.join path (tmpdir) "kotoba.modules.edn")]
      (.writeFileSync fs lock
                      (pr-str {:schema module-lock/lock-schema
                               :root 'example.missing
                               :modules {'example.lib "bafkone"}})
                      "utf8")
      (when-let [failure (rejects #(module-lock/read-lock lock)
                                  "module lock does not pin its own root")]
        (throw (js/Error. failure))))))

(check "an-unknown-lock-schema-is-refused"
  (fn []
    (let [lock (.join path (tmpdir) "kotoba.modules.edn")]
      (.writeFileSync fs lock
                      (pr-str {:schema :kotoba.module-lock/v0
                               :root 'example.lib
                               :modules {'example.lib "bafkone"}})
                      "utf8")
      (when-let [failure (rejects #(module-lock/read-lock lock)
                                  "unknown module lock schema")]
        (throw (js/Error. failure))))))

(check "an-empty-lock-pins-nothing-and-is-refused"
  (fn []
    (let [lock (.join path (tmpdir) "kotoba.modules.edn")]
      (.writeFileSync fs lock
                      (pr-str {:schema module-lock/lock-schema
                               :root 'example.lib :modules {}})
                      "utf8")
      (when-let [failure (rejects #(module-lock/read-lock lock)
                                  "module lock must pin at least one module")]
        (throw (js/Error. failure))))))

(check "a-lock-entry-without-a-cid-is-refused"
  (fn []
    (let [lock (.join path (tmpdir) "kotoba.modules.edn")]
      (.writeFileSync fs lock
                      (pr-str {:schema module-lock/lock-schema
                               :root 'example.lib :modules {'example.lib 42}})
                      "utf8")
      (when-let [failure (rejects #(module-lock/read-lock lock)
                                  "module lock entry must pin a CID")]
        (throw (js/Error. failure))))))

(check "a-block-store-that-is-not-a-directory-is-refused"
  (fn []
    (let [{:keys [lock]} (write-lock! {'example.lib lib-source 'example.root app-source}
                                      'example.root)]
      (when-let [failure (rejects #(module-lock/load-locked-graph lock (.join path (tmpdir) "absent"))
                                  "block store is not readable")]
        (throw (js/Error. failure))))))

(check "the-lock-cid-changes-when-any-input-changes"
  (fn []
    (let [base (module-lock/lock-cid {:root 'example.root
                                      :modules {'example.lib "bafkone"
                                                'example.root "bafktwo"}})]
      (assert (= base (module-lock/lock-cid {:root 'example.root
                                             :modules {'example.root "bafktwo"
                                                       'example.lib "bafkone"}}))
              "entry order is not part of the identity")
      (assert (not= base (module-lock/lock-cid {:root 'example.root
                                                :modules {'example.lib "bafkthree"
                                                          'example.root "bafktwo"}}))
              "a changed dependency changes the pinned-input identity")
      (assert (not= base (module-lock/lock-cid {:root 'example.lib
                                                :modules {'example.lib "bafkone"
                                                          'example.root "bafktwo"}}))
              "the same modules compiled from a different root are a different input set"))))

(check "writing-the-same-source-twice-produces-one-block"
  (fn []
    (let [blocks (blocks-dir)]
      (assert (= (module-lock/write-block! blocks lib-source)
                 (module-lock/write-block! blocks lib-source)))
      (assert (= 1 (alength (.readdirSync fs blocks)))))))

(check "a-block-store-holding-different-bytes-under-a-cid-is-refused"
  (fn []
    (let [blocks (blocks-dir)
          cid (module-lock/write-block! blocks lib-source)]
      (.writeFileSync fs (.join path blocks cid) "different" "utf8")
      (when-let [failure (rejects #(module-lock/write-block! blocks lib-source)
                                  "existing block has different bytes for its CID")]
        (throw (js/Error. failure))))))

(check "a-lock-derived-from-source-paths-resolves-back-to-the-same-graph"
  (fn []
    ;; The migration edge, both directions in one case: a path-resolved
    ;; project is pinned once, and the pinned form loads to the same sources.
    (let [root (tmpdir)
          blocks (blocks-dir)
          main (spit! root "main.cljk" entry)
          _ (spit! root "util.cljk" (util 2))
          lock (module-lock/lock-from-source-paths
                project-files/load-closed-graph main [root] blocks)
          lock-file (.join path (tmpdir) "kotoba.modules.edn")]
      (.writeFileSync fs lock-file (pr-str (dissoc lock :lock-cid)) "utf8")
      (let [graph (module-lock/load-locked-graph lock-file blocks)]
        (assert (= 'main (:root graph)))
        (assert (= (:modules lock) (:modules graph)))
        (assert (= (:lock-cid lock) (:lock-cid graph)))
        (let [{:keys [source]} (project/link-source (:sources graph) (:root graph))
              kir (ir/lower (sema/analyze source {:admit-linked-synthetics? true}))]
          (assert (= 11 (js/Number (ir/execute kir 'run [5])))))))))

;; ---------------------------------------------------------------------------
;; Multi-arity exports across a module boundary
;;
;; A .cljc module routinely publishes a multi-arity function, and until this
;; landed a project could not export one: the analysed module's functions are
;; already `twice$arity$1` / `twice$arity$2`, the `:export` vector still says
;; `twice`, and the linker looked one up among the other and refused with
;; "export does not name a declared function" -- naming a cause that was not
;; the cause. Both controls were measured before the fix: the same project
;; with a SINGLE-arity `twice` linked and ran, and the same multi-arity
;; `twice` in a single file (no project) compiled and reported
;; `:exports [twice$arity$1 twice$arity$2]`.
;;
;; What is asserted here is not that it links. It is that BOTH arities run and
;; return the value each clause defines -- a wrapper that routes every call to
;; one clause would link, export two names, and still be wrong.

(def ^:private multi-arity-sources
  {'ma.lib
   "(ns ma.lib (:export [twice]))
    (defn twice
      ([x :i64] :i64 (* 2 x))
      ([x :i64 y :i64] :i64 (* y x)))"
   'app.main
   "(ns app.main (:require [ma.lib :as l]) (:export [main twice]))
    (defn main [] :i64 (l/twice 5))
    (defn twice
      ([x :i64] :i64 (l/twice x))
      ([x :i64 y :i64] :i64 (l/twice x y)))"})

(check "multi-arity-export-runs-at-every-arity"
  (fn []
    (let [{:keys [source module-order]} (project/link-source multi-arity-sources 'app.main)
          kir (ir/lower (sema/analyze source {:admit-linked-synthetics? true}))]
      (assert (= ['ma.lib 'app.main] module-order))
      ;; The same export surface a single-file compile of the same function
      ;; gives. `twice` itself is not an export: it is the source name the two
      ;; ABI names were derived from.
      (assert (= ['main 'twice$arity$1 'twice$arity$2] (vec (:exports kir)))
              (str "exports were " (pr-str (:exports kir))))
      ;; The clause bodies differ, so a wrapper collapsing them shows up here.
      (assert (= 10 (js/Number (ir/execute kir 'twice$arity$1 [5]))))
      (assert (= 15 (js/Number (ir/execute kir 'twice$arity$2 [5 3]))))
      ;; And the cross-module call the root makes reaches the 1-arity clause.
      (assert (= 10 (js/Number (ir/execute kir 'main [])))))))

(check "the-import-stub-does-not-survive-linking"
  (fn []
    ;; The stub is a multi-arity `defn-` now, which the frontend splits into
    ;; one function per arity. Those carry generated names, so filtering the
    ;; stub out of a module's locals by `:name` misses them and emits them
    ;; into the linked source as real functions returning a stub value -- 0
    ;; here, which would have made `main` return 0 instead of 10 above.
    (let [{:keys [source]} (project/link-source multi-arity-sources 'app.main)]
      (assert (not (re-find #"kotoba_import__" source))
              (str "an import stub reached the linked source: " source)))))

(check "an-imported-multi-arity-export-is-callable-at-each-declared-arity-only"
  (fn []
    ;; The refusal must be the frontend's own arity message. Before this
    ;; landed, EVERY arity of an imported multi-arity export failed, and it
    ;; failed with the export message rather than this one.
    (when-let [failure
               (rejects #(project/link-source
                          (assoc multi-arity-sources
                                 'app.main
                                 "(ns app.main (:require [ma.lib :as l]) (:export [main]))
                                  (defn main [] :i64 (l/twice 1 2 3))")
                          'app.main)
                        "no matching multi-arity clause")]
      (throw (js/Error. failure)))))

(check "multi-arity-clauses-keep-their-own-result-types"
  (fn []
    ;; Each clause is monomorphic, so one export can return :i64, :string and
    ;; :bool at three arities. The import stub has to carry all three, or the
    ;; importing module type-checks against the wrong one.
    (let [{:keys [source]}
          (project/link-source
           {'ma.lib "(ns ma.lib (:export [f]))
                     (defn f
                       ([x :i64] :i64 (* 2 x))
                       ([x :i64 y :i64] :string (string-from-i64 (+ x y)))
                       ([x :i64 y :i64 z :i64] :bool (> (+ x y) z)))"
            'app.main "(ns app.main (:require [ma.lib :as l]) (:export [a b c]))
                       (defn a [] :i64 (l/f 3))
                       (defn b [] :string (l/f 1 2))
                       (defn c [] :bool (l/f 1 2 0))"}
           'app.main)
          kir (ir/lower (sema/analyze source {:admit-linked-synthetics? true}))]
      (assert (= 6 (js/Number (ir/execute kir 'a []))))
      (assert (= "3" (ir/execute kir 'b [])))
      (assert (true? (ir/execute kir 'c []))))))

(check "a-multi-arity-export-crosses-more-than-one-module-boundary"
  (fn []
    ;; The middle module both imports a multi-arity export and publishes one.
    (let [{:keys [source module-order]}
          (project/link-source
           {'m.base "(ns m.base (:export [f]))
                     (defn f ([x :i64] :i64 (+ x 1)) ([x :i64 y :i64] :i64 (+ x y)))"
            'm.mid "(ns m.mid (:require [m.base :as b]) (:export [g]))
                    (defn g ([x :i64] :i64 (b/f x)) ([x :i64 y :i64] :i64 (b/f x y)))"
            'm.top "(ns m.top (:require [m.mid :as m]) (:export [main]))
                    (defn main [] :i64 (+ (m/g 1) (m/g 10 20)))"}
           'm.top)
          kir (ir/lower (sema/analyze source {:admit-linked-synthetics? true}))]
      (assert (= ['m.base 'm.mid 'm.top] module-order))
      (assert (= 32 (js/Number (ir/execute kir 'main [])))))))
