(ns test.nbb.project
  (:require [kotoba.sema :as sema]
            [kotoba.kir :as ir]
            [kotoba.compiler.project :as project]
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
