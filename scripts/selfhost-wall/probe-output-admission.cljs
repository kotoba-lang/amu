;; Differential probe: the Kotoba reading of kotoba.compiler.nbb.output-admission/admit! on the KIR interpreter
;; against the host reading. For a primary Wasm output the Kotoba reading verifies the provenance record, the target,
;; the artifact size and its SHA-256 (pure sha2), then names what it lacks: no WebAssembly validator. So every
;; refusal REASON must equal the host's; the one deliberate difference is a fully matching module, which the host
;; admits (WebAssembly.validate) and the Kotoba route refuses as wasm-validator-unavailable. KROOTS as in
;; probe-compile-cache.cljs.
(ns oa-probe
  (:require ["node:fs" :as fs]
            ["node:crypto" :as crypto]
            [clojure.string :as str]
            [kotoba.sema :as sema]
            [kotoba.kir :as kir]
            [kotoba.artifact.core :as artifact]
            [kotoba.kir.compatibility :as compat]
            [kotoba.compiler.project :as project]
            [kotoba.compiler.project-files :as pf]
            [kotoba.compiler.nbb.output-admission :as host]))

(def roots (vec (str/split (.-KROOTS js/process.env) #":")))

(defn typed-cap-call [id _ _ request]
  (case (js/Number id)
    3 (-> (.createHash crypto "sha256") (.update request) (.digest "hex"))
    (throw (ex-info "unhandled capability" {:id id}))))

(def module-bytes [0 97 115 109 1 0 0 0])           ; the empty module: valid WebAssembly
(def other-bytes [0 97 115 109 1 0 0 0 0 1 0])       ; a different (invalid) buffer
(defn buf [v] (js/Buffer.from (clj->js v)))
(defn sha [v] (-> (.createHash crypto "sha256") (.update (buf v)) (.digest "hex")))
(defn h [c] (apply str (repeat 64 c)))

(defn provenance [& {:as over}]
  (let [primary (merge {:format :wasm :sha256 (sha module-bytes) :size (count module-bytes)} (:primary over))
        base {:format :kotoba.provenance/v1 :builder :kotoba-compiler/v1
              :compiler compat/compiler-version :language compat/language-version
              :source-sha256 (h "1") :policy-sha256 (h "2") :build-metadata-sha256 (h "3")
              :hir-sha256 (h "4") :kir-sha256 (h "5") :target (or (:target over) :wasm32-kotoba-v1)
              :target-profile-sha256 (h "6") :compatibility-sha256 (h "7")
              :definitions (or (:definitions over) {:contract :kotoba.definition-identity/v1})
              :outputs {:primary primary}}]
    (artifact/seal (if (:drop over) (dissoc base (:drop over)) base))))

(def cases
  [["matching module" module-bytes (provenance)]
   ["wrong size" module-bytes (provenance :primary {:size 9})]
   ["wrong digest" module-bytes (provenance :primary {:sha256 (h "9")})]
   ["bytes differ from provenance" other-bytes (provenance)]
   ["non-wasm target" module-bytes (provenance :target :x86_64-kotoba-v1)]
   ["extra primary key" module-bytes (provenance :primary {:extra 1})]
   ["missing definitions" module-bytes (provenance :drop :definitions)]
   ["wrong definitions contract" module-bytes (provenance :definitions {:contract :nope})]
   ["unsupported primary format" module-bytes (provenance :primary {:format :elf})]
   ["native primary" module-bytes (provenance :primary {:format :kotoba.kexe/v1 :sha256 (h "8")})]])

(defn host-reason [bytes prov]
  (try (host/admit! (buf bytes) prov) "admitted"
       (catch :default e (name (or (:reason (ex-data e)) :unknown)))))

(defn doc [x] (str "(document-edn-read " (pr-str (pr-str x)) ")"))
(defn q [s] (pr-str s))

(defn body [bytes prov]
  (str "(let [r (oa/admit! (bytes-from-vector-i64 (vector-i64 " (str/join " " bytes) ")) " (doc prov) ")] "
       "(if (result-ok?-of [:result :document :document] r) \"admitted\" "
       "(document-edn-print (result-error-of [:result :document :document] r (document-null)))))"))

(defn run-main [b]
  (let [root "/tmp/probe_oa_main.cljk"
        src (str "(ns probe.oa-main\n  {:kotoba/export [main]}\n  (:require [kotoba.compiler.nbb.output-admission :as oa]))\n"
                 "(defn main [] :vector-i64 (vector-i64-from-bytes (string-to-utf8 " b ")))\n")]
    (.writeFileSync fs root src)
    (let [graph (pf/load-closed-graph root roots)
          linked (project/link-source (:sources graph) (:root graph))
          hir (sema/analyze (:source linked) {:admit-linked-synthetics? true})
          r (kir/execute (kir/lower hir) 'main [] {:typed-cap-call typed-cap-call :fuel 4000000000 :frames 400000
                                                   :cells 400000000 :bytes 400000000})]
      (.toString (js/Buffer.from (clj->js (mapv js/Number r))) "utf8"))))

(let [joined (reduce (fn [acc [_ b p]] (str "(string-concat " acc " (string-concat \"\\n\" " (body b p) "))")) "\"\"" cases)
      out (try (run-main joined) (catch :default e (str "ERR " (subs (str e) 0 600))))
      lines (rest (str/split out #"\n"))
      _ (when (str/starts-with? out "ERR") (println out))
      results
      (doall
       (map (fn [[label bytes prov] got]
              (let [want (host-reason bytes prov)
                    ;; the deliberate difference: the host admits the matching module
                    expected-kotoba (if (= want "admitted") "wasm-validator-unavailable" want)
                    native? (= label "native primary")
                    expected-kotoba (if native? "native-verifier-unavailable" expected-kotoba)
                    expected-kotoba (if (= want "unsupported-primary-format") want expected-kotoba)
                    expected-kotoba (if (= want "malformed-provenance") want expected-kotoba)
                    ok (str/includes? got expected-kotoba)]
                (println (if ok "ok  " "FAIL") label "| host:" want "| kotoba:" (subs got 0 (min 140 (count got))))
                ok))
            cases lines))]
  (println (count (filter true? results)) "of" (count cases) "agree")
  (.exit js/process (if (and (= (count results) (count cases)) (every? true? results)) 0 1)))
