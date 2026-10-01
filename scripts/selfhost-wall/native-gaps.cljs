;; bootstrap-tooling
;; BOOTSTRAP SCAFFOLDING (nbb): the native-backend gap scanner. For one guest module (GUEST=<file>) it analyzes the
;; linked project exactly as `amu compile` does, then asks the native admission gate (kotoba.kir
;; `only-native-word-typed-features?`, through kotoba.compiler.nbb.cli `unqualified-native-feature`) about EVERY function on
;; its own, not just the first: one TSV row per refused function, `function<TAB>kind<TAB>detail`, kind = boundary |
;; feature. `native-gaps.sh` aggregates the details; docs/selfhost-native-gaps-20261001.md is the written result.
;; The wasm and verifier halves list the KIR operation heads that no kotoba-wasm source (WASM_SRC) / kotoba-verifier source
;; (VERIFIER_SRC) mentions (an approximation: both dispatch on literal symbols, so an absent name is an unqualified
;; operation; the native verifier is a second gate behind `only-native-word-typed-features?`).
;; Env: KROOTS, GUEST, WASM_SRC (kotoba-wasm src dir, for the operation names).
(ns native-gaps
  (:require ["node:fs" :as fs]
            [clojure.string :as str] [clojure.walk :as walk]
            [kotoba.sema :as sema] [kotoba.kir :as kir]
            [kotoba.compiler.project :as project] [kotoba.compiler.project-files :as pf]
            [kotoba.compiler.nbb.cli :as cli]))
(def env js/process.env)
(def roots (vec (str/split (.-KROOTS env) #":")))
(let [graph (pf/load-closed-graph (.-GUEST env) roots)
      linked (project/link-source (:sources graph) (:root graph))
      hir (sema/analyze (:source linked) {:admit-linked-synthetics? true})
      k (kir/lower hir)
      fns (:functions hir)]
  (println (str "#functions\t" (count fns)))
  (doseq [f fns]
    (when-let [found (cli/unqualified-native-feature (assoc hir :functions [f]))]
      (if (:boundary-types found)
        (println (str (:function found) "\tboundary\t" (pr-str (:boundary-types found))))
        (println (str (:function found) "\tfeature\t" (:feature found))))))
  (let [names (set (map :name (:functions k)))
        heads (volatile! #{})
        wasm-text (->> (js->clj (.readdirSync fs (.-WASM_SRC env)))
                       (filter #(str/ends-with? % ".cljk"))
                       (map #(.readFileSync fs (str (.-WASM_SRC env) "/" %) "utf8"))
                       (str/join "\n"))]
    (walk/postwalk (fn [x] (when (and (seq? x) (symbol? (first x)) (not (names (first x)))) (vswap! heads conj (first x))) x)
                   (:functions k))
    (let [ver-text (.readFileSync fs (or (.-VERIFIER_SRC env) "/private/tmp/wt-D-kotoba-verifier/src/kotoba/verifier.cljk") "utf8")]
      (doseq [h (sort @heads)]
        (when (re-find #"^[a-z]" (str h))
          (when-not (str/includes? wasm-text (str h)) (println (str h "\twasm-op-absent\t")))
          (when-not (str/includes? ver-text (str h)) (println (str h "\tverifier-op-absent\t"))))))))
