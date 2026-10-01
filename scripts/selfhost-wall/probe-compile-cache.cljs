;; Differential probe: the Kotoba reading of kotoba.compiler.nbb.compile-cache (key-for-kind, stage-key-for,
;; sha256, sha256-bytes on the KIR interpreter over a linked project) against the host reading (nbb).
;; KROOTS as in probe-definition-identity.cljs: every classpath src dir, this repo's src, kotoba-lang/lang/compat.
(ns cc-probe
  (:require ["node:fs" :as fs]
            [clojure.string :as str]
            [kotoba.sema :as sema]
            [kotoba.kir :as kir]
            [kotoba.compiler.project :as project]
            [kotoba.compiler.project-files :as pf]
            ["node:crypto" :as crypto]
            [kotoba.compiler.nbb.compile-cache :as host]))

;; The hash/sha256 ability (wire 3) for the KIR interpreter: node:crypto, as the nbb handler.
(defn typed-cap-call [id request-type result-type request]
  (case (js/Number id)
    3 (-> (.createHash crypto "sha256") (.update request) (.digest "hex"))
    (throw (ex-info "unhandled capability" {:id id :request-type request-type}))))

(def roots (vec (str/split (.-KROOTS js/process.env) #":")))

(defn run-main [body]
  (let [root "/tmp/probe_cc_main.cljk"
        src (str "(ns probe.cc-main\n  {:kotoba/export [main]}\n  (:require [kotoba.compiler.nbb.compile-cache :as cc]))\n"
                 "(defn main [] :vector-i64 (vector-i64-from-bytes (string-to-utf8 " body ")))\n")]
    (.writeFileSync fs root src)
    (let [graph (pf/load-closed-graph root roots)
          linked (project/link-source (:sources graph) (:root graph))
          hir (sema/analyze (:source linked) {:admit-linked-synthetics? true})
          r (kir/execute (kir/lower hir) 'main [] {:typed-cap-call typed-cap-call :fuel 1000000000 :frames 400000 :cells 100000000 :bytes 100000000})]
      (.toString (js/Buffer.from (clj->js (mapv js/Number r))) "utf8"))))

(defn q [s] (pr-str s))

(def sources ["" "a" "(ns x)\n(defn f [] 1)" "caf\\u00e9 \"quoted\" \\\\ \n\t" "x"])

(def cases
  (concat
   (for [s sources]
     {:label (str "sha256 " (pr-str s))
      :want (host/sha256 s) :body (str "(cc/sha256 " (q s) ")")})
   (for [s sources]
     {:label (str "stage-key-for " (pr-str s))
      :want (host/stage-key-for :hir s) :body (str "(cc/stage-key-for \"hir\" " (q s) ")")})
   (for [s sources linked? [true false] present? [true false] kind [nil "wasm" "kexe"]]
     (let [meta* {:fuel 7}]
       {:label (str "key-for " (pr-str [s linked? present? kind]))
        :want (host/key-for :wasm32-kotoba-v1 s {:present? present? :text (if present? "{}\n" "")}
                            meta* linked? kind)
        :body (str "(cc/key-for-kind \"wasm32-kotoba-v1\" " (q s) " " present? " " (q (if present? "{}\n" ""))
                   " " (q (pr-str meta*)) " " linked? " " (q (or kind "")) " " (boolean kind) ")")}))))

(let [joined (reduce (fn [acc c] (str "(string-concat " acc " (string-concat \"\\n\" " (:body c) "))"))
                     "\"\"" cases)
      out (try (run-main joined) (catch :default e (str "ERR " (subs (str e) 0 400))))
      lines (str/split out #"\n")
      all (doall (map (fn [c got]
                        (let [ok (= got (:want c))]
                          (println (if ok "ok  " "FAIL") (:label c) (if ok "" (str got " <> " (:want c))))
                          ok))
                      cases (rest lines)))]
  (println (count (filter true? all)) "of" (count cases) "agree")
  (.exit js/process (if (and (= (count all) (count cases)) (every? true? all)) 0 1)))
