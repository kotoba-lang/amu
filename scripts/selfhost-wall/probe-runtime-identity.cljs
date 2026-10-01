;; Differential probe: the Kotoba reading of kotoba.artifact.runtime-identity (validate!, validate-measurement!,
;; identity-sha256, loader-source-for-profile, admit!) on the KIR interpreter over a linked project, against the
;; host reading under nbb. Same EDN text on both sides. KROOTS as in probe-compile-cache.cljs.
(ns ri-probe
  (:require ["node:fs" :as fs]
            ["node:crypto" :as crypto]
            [clojure.string :as str]
            [cljs.reader :as reader]
            [kotoba.sema :as sema]
            [kotoba.kir :as kir]
            [kotoba.compiler.project :as project]
            [kotoba.compiler.project-files :as pf]
            [kotoba.kir.target :as target]
            [kotoba.artifact.runtime-identity :as host]))

(def roots (vec (str/split (.-KROOTS js/process.env) #":")))

(defn typed-cap-call [id _ _ request]
  (case (js/Number id)
    3 (-> (.createHash crypto "sha256") (.update request) (.digest "hex"))
    (throw (ex-info "unhandled capability" {:id id}))))

(defn h [c] (apply str (repeat 64 c)))
(defn runtime [& {:as over}]
  (merge {:format :kotoba.native-runtime/v6
          :target-profile (get target/profiles :x86_64-linux-kotoba-v1)
          :loader-source-sha256 host/loader-source-sha256
          :loader-binary-sha256 (h "a") :compiler-binary-sha256 (h "b") :compiler-version-sha256 (h "c")
          :assembler-binary-sha256 (h "d") :linker-binary-sha256 (h "e")
          :compiler-resource-sha256 (h "f") :system-header-closure-sha256 (h "0")}
         over))

(def runtimes
  [["linux" (runtime)]
   ["macos" (runtime :target-profile (get target/profiles :aarch64-macos-kotoba-v1))]
   ["windows" (runtime :target-profile (get target/profiles :x86_64-windows-kotoba-v1)
                       :loader-source-sha256 host/windows-loader-source-sha256)]
   ["static linux (native, os linux)" (runtime :target-profile (get target/profiles :x86_64-linux-static-kotoba-v1))]
   ["wrong format" (runtime :format :kotoba.native-runtime/v5)]
   ["extra key" (assoc (runtime) :extra (h "1"))]
   ["missing key" (dissoc (runtime) :linker-binary-sha256)]
   ["uppercase sha" (runtime :linker-binary-sha256 (h "E"))]
   ["short sha" (runtime :linker-binary-sha256 "abc")]
   ["non-string sha" (runtime :linker-binary-sha256 7)]
   ["wasm profile" (runtime :target-profile (get target/profiles :wasm32-kotoba-v1))]
   ["android (native, os not admitted)" (runtime :target-profile (get target/profiles :aarch64-android-kotoba-v1))]
   ["mutated profile" (runtime :target-profile (assoc (get target/profiles :x86_64-linux-kotoba-v1) :abi :other))]
   ["unknown profile" (runtime :target-profile {:execution :native :os :linux})]
   ["loader mismatch" (runtime :loader-source-sha256 host/windows-loader-source-sha256)]
   ["windows with posix loader" (runtime :target-profile (get target/profiles :x86_64-windows-kotoba-v1))]
   ["not a map" [1 2]]])

(def measurements
  [["measurement ok" {:format :kotoba.runtime-measurement/v1 :runtime (runtime)}]
   ["measurement bad format" {:format :kotoba.runtime-measurement/v2 :runtime (runtime)}]
   ["measurement extra key" {:format :kotoba.runtime-measurement/v1 :runtime (runtime) :x 1}]
   ["measurement bad runtime" {:format :kotoba.runtime-measurement/v1 :runtime (runtime :format :no)}]])

(defn q [s] (pr-str s))
;; A Kotoba function that can abort answers a [:result T :document] to its caller (the abort is a value there):
;; these read it back the way kotoba.compiler.json-text/decode-object does.
(defn str-result [expr]
  (str "(let [r " expr "] (if (result-ok?-of [:result :string :document] r) (result-value-of [:result :string :document] r \"\") "
       "(string-concat \"threw \" (document-edn-print (result-error-of [:result :string :document] r (document-null))))))"))
(defn doc-result [expr ok-text]
  (str "(let [r " expr "] (if (result-ok?-of [:result :document :document] r) " (q ok-text) " "
       "(string-concat \"threw \" (document-edn-print (result-error-of [:result :document :document] r (document-null))))))"))
(defn doc [x] (str "(document-edn-read " (q (pr-str x)) ")"))

(defn host-validate [r] (try (host/validate! r) "ok" (catch :default _ "REJECT")))
(defn host-measure [m] (try (host/validate-measurement! m) "ok" (catch :default _ "REJECT")))
(defn host-admit [r trust]
  (try (let [a (host/admit! r trust)] (str "admitted " (:runtime-sha256 a) " " (:trusted? a)))
       (catch :default e (str "REJECT " (ex-message e)))))

(def good-id (host/identity-sha256 (runtime)))
(def admit-cases
  [["trusted" (runtime) {:trusted-runtime-sha256 #{good-id}}]
   ["not trusted" (runtime) {:trusted-runtime-sha256 #{(h "9")}}]
   ["trusted but revoked" (runtime) {:trusted-runtime-sha256 #{good-id} :revoked-runtime-sha256 #{good-id}}]
   ["revoked other, trusted" (runtime) {:trusted-runtime-sha256 #{good-id} :revoked-runtime-sha256 #{(h "9")}}]
   ["no trust set" (runtime) {}]
   ["trusted is a vector" (runtime) {:trusted-runtime-sha256 [good-id]}]])

(def cases
  (concat
   (for [[label r] runtimes]
     {:label (str "validate! " label) :want (let [w (host-validate r)] (if (= w "ok") w "threw native runtime identity rejected"))
      :loose true
      :body (str (doc-result (str "(rid/validate! " (doc r) ")") "ok"))})
   (for [[label r] runtimes :when (= "ok" (host-validate r))]
     {:label (str "identity-sha256 " label) :want (host/identity-sha256 r)
      :body (str-result (str "(rid/identity-sha256 " (doc r) ")"))})
   (for [[label m] measurements]
     {:label (str "validate-measurement! " label) :want (let [w (host-measure m)] (if (= w "ok") w "threw"))
      :loose true
      :body (str (doc-result (str "(rid/validate-measurement! " (doc m) ")") "ok"))})
   (for [[label r trust] admit-cases]
     {:label (str "trust-decision " label)
      :want (let [w (host-admit r trust)]
              (cond (str/includes? w "revoked") "revoked" (str/starts-with? w "admitted") "trusted" :else "untrusted"))
      :body (str "(keyword-name (rid/trust-decision " (doc trust) " " (q (host/identity-sha256 r)) "))")})
   (for [[label r trust] admit-cases]
     {:label (str "admit! " label)
      :want (let [w (host-admit r trust)] (cond (str/starts-with? w "admitted") (str "admitted " good-id)
                                                (str/includes? w "revoked") "threw native runtime identity is revoked"
                                                :else "threw native runtime identity is not trusted"))
      :body (str "(let [r (rid/admit! " (doc r) " " (doc trust) ")] (if (result-ok?-of [:result :document :document] r) "
                 "(string-concat \"admitted \" (option-value-of [:option :string] (document-string-value (get (result-value-of [:result :document :document] r (document-null)) :runtime-sha256 (document-null))) \"\")) "
                 "(string-concat \"threw \" (document-edn-print (result-error-of [:result :document :document] r (document-null))))))")})
   [{:label "loader-source-for-profile linux" :want host/loader-source-sha256
     :body (str "(option-value-of [:option :string] (rid/loader-source-for-profile " (doc (get target/profiles :x86_64-linux-kotoba-v1)) ") \"none\")")}
    {:label "loader-source-for-profile windows" :want host/windows-loader-source-sha256
     :body (str "(option-value-of [:option :string] (rid/loader-source-for-profile " (doc (get target/profiles :aarch64-windows-kotoba-v1)) ") \"none\")")}
    {:label "loader-source-for-profile wasm (nil)" :want "none"
     :body (str "(option-value-of [:option :string] (rid/loader-source-for-profile " (doc (get target/profiles :wasm32-kotoba-v1)) ") \"none\")")}
    {:label "pinned loader identities" :want (str host/loader-source-sha256 " " host/windows-loader-source-sha256)
     :body "(string-concat (rid/loader-source-sha256) (string-concat \" \" (rid/windows-loader-source-sha256)))"}]))

(defn run-main [body]
  (let [root "/tmp/probe_ri_main.cljk"
        src (str "(ns probe.ri-main\n  {:kotoba/export [main]}\n  (:require [kotoba.artifact.runtime-identity :as rid]))\n"
                 "(defn main [] :vector-i64 (vector-i64-from-bytes (string-to-utf8 " body ")))\n")]
    (.writeFileSync fs root src)
    (let [graph (pf/load-closed-graph root roots)
          linked (project/link-source (:sources graph) (:root graph))
          hir (sema/analyze (:source linked) {:admit-linked-synthetics? true})
          r (kir/execute (kir/lower hir) 'main [] {:typed-cap-call typed-cap-call :fuel 4000000000 :frames 400000
                                                   :cells 400000000 :bytes 400000000})]
      (.toString (js/Buffer.from (clj->js (mapv js/Number r))) "utf8"))))

(let [joined (reduce (fn [acc c] (str "(string-concat " acc " (string-concat \"\\n\" " (:body c) "))")) "\"\"" cases)
      out (try (run-main joined) (catch :default e (str "ERR " (subs (str e) 0 600))))
      lines (str/split out #"\n")
      _ (when (str/starts-with? out "ERR") (println out))
      all (doall (map (fn [c got]
                        (let [want (:want c)
                              ok (if (str/starts-with? want "threw")
                                   (and (str/starts-with? (str got) "threw") (str/includes? got (str/trim (subs want 5))))
                                   (= got want))]
                          (println (if ok "ok  " "FAIL") (:label c) (if ok "" (str got " <> " (:want c))))
                          ok))
                      cases (rest lines)))]
  (println (count (filter true? all)) "of" (count cases) "agree")
  (.exit js/process (if (and (= (count all) (count cases)) (every? true? all)) 0 1)))
