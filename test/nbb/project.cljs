(ns test.nbb.project
  (:require [kotoba.sema :as sema]
            [kotoba.kir :as ir]
            [kotoba.compiler.project :as project]))

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
