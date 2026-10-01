;; Differential probe: the Kotoba reading of kotoba.compiler.nbb.output-attestation (signer-id, sign, verify!) on the
;; KIR interpreter against the host reading (node:crypto Ed25519). Ed25519 is deterministic, so `sign` must produce the
;; host's envelope byte for byte; `verify!` must accept what the host accepts and refuse with the host's :phase and
;; :reason for every refusal clause. KROOTS as in probe-compile-cache.cljs.
(ns oat-probe
  (:require ["node:fs" :as fs]
            ["node:crypto" :as crypto]
            [clojure.string :as str]
            [clojure.walk :as walk]
            [kotoba.sema :as sema]
            [kotoba.kir :as kir]
            [kotoba.compiler.project :as project]
            [kotoba.compiler.project-files :as pf]
            [kotoba.compiler.nbb.output-attestation :as host]))

(def roots (vec (str/split (.-KROOTS js/process.env) #":")))

(defn hex->buf [x] (js/Buffer.from x "hex"))
(def spki-prefix (js/Buffer.from "302a300506032b6570032100" "hex"))
(def pkcs8-prefix (js/Buffer.from "302e020100300506032b657004220420" "hex"))
(defn pkey [seed-hex]
  (.createPrivateKey crypto #js {:key (js/Buffer.concat #js [pkcs8-prefix (hex->buf seed-hex)]) :format "der" :type "pkcs8"}))

;; identity/sign (1) and identity/verify (2) answer for the probe-only ed25519.sign stand-in
;; (/private/tmp/cc/edstub or scripts/selfhost-wall/probe-ed25519-stub): the curve math by node:crypto.
(defn typed-cap-call [id _ _ request]
  (case (js/Number id)
    1 (let [[kind a b] (str/split request #":")]
        (case kind
          "pub" (-> (.createPublicKey crypto (pkey a)) (.export #js {:type "spki" :format "der"}) (.subarray 12) (.toString "hex"))
          "sig" (.toString (.sign crypto nil (hex->buf b) (pkey a)) "hex")))
    2 (let [[pub msg sig] (str/split request #":")]
        (if (try (.verify crypto nil (hex->buf msg)
                          (.createPublicKey crypto #js {:key (js/Buffer.concat #js [spki-prefix (hex->buf pub)]) :format "der" :type "spki"})
                          (hex->buf sig))
                 (catch :default _ false))
          "1" "0"))
    3 (-> (.createHash crypto "sha256") (.update request) (.digest "hex"))
    (throw (ex-info "unhandled capability" {:id id}))))

(defn big [n] (js/BigInt n))
(defn h [c] (apply str (repeat 64 c)))
(defn keypair []
  (let [kp (.generateKeyPairSync crypto "ed25519")
        pub (.toString (.export (.-publicKey kp) #js {:type "spki" :format "der"}) "base64")
        priv (.toString (.export (.-privateKey kp) #js {:type "pkcs8" :format "der"}) "base64")]
    {:format :kotoba.signing-key/v1 :algorithm :ed25519 :signer (host/signer-id pub) :public-key pub :private-key priv}))
(def k1 (keypair))
(def k2 (keypair))

(def marker {:sha256 (h "1")})
(def provenance {:sha256 (h "2") :target :wasm32-kotoba-v1 :outputs {:primary {:sha256 (h "3")}}})
(def other-marker {:sha256 (h "4")})
(defn trust [& {:as over}]
  (merge {:format :kotoba.trust/v1 :trusted-signers #{(:signer k1)} :revoked-signers #{} :revoked-artifacts #{}} over))

(defn ->edn [x]
  (cond (= "[object BigInt]" (.call (.-toString js/Object.prototype) x)) (str x)
        (map? x) (str "{" (str/join " " (map (fn [[k v]] (str (->edn k) " " (->edn v))) x)) "}")
        (set? x) (str "#{" (str/join " " (map ->edn x)) "}")
        (vector? x) (str "[" (str/join " " (map ->edn x)) "]")
        :else (pr-str x)))
(defn doc [x] (str "(document-edn-read " (pr-str (->edn x)) ")"))

(def good (host/sign marker provenance k1 (big 100) (big 200)))
(defn put-st [env k v] (assoc-in env [:statement k] v))
(defn host-verify [env tr m p now]
  (try (let [r (host/verify! env tr m p (big now))] {:ok (:publisher r)})
       (catch :default e {:threw (:reason (ex-data e)) :phase (:phase (ex-data e))})))
(defn host-sign [m p k nb ex]
  (try {:ok (host/sign m p k (big nb) (big ex))}
       (catch :default e {:threw (:reason (ex-data e))})))

(defn verify-body [env tr m p now]
  (str "(let [r (oat/verify! " (doc env) " " (doc tr) " " (doc m) " " (doc p) " " now ")] "
       "(if (result-ok?-of [:result :document :document] r) "
       "(string-concat \"ok \" (option-value-of [:option :string] (document-string-value (get (result-value-of [:result :document :document] r (document-null)) :publisher (document-null))) \"\")) "
       "(document-edn-print (result-error-of [:result :document :document] r (document-null)))))"))
(defn sign-body [m p k nb ex]
  (str "(let [r (oat/sign " (doc m) " " (doc p) " " (doc k) " " nb " " ex ")] "
       "(if (result-ok?-of [:result :document :document] r) "
       "(document-edn-print (result-value-of [:result :document :document] r (document-null))) "
       "(document-edn-print (result-error-of [:result :document :document] r (document-null)))))"))

(def verify-cases
  [["valid" good (trust) marker provenance 150]
   ["valid at not-before" good (trust) marker provenance 100]
   ["not yet valid" good (trust) marker provenance 99]
   ["expired (at expires)" good (trust) marker provenance 200]
   ["untrusted signer" good (trust :trusted-signers #{(:signer k2)}) marker provenance 150]
   ["revoked signer" good (trust :revoked-signers #{(:signer k1)}) marker provenance 150]
   ["revoked artifact" good (trust :revoked-artifacts #{(h "3")}) marker provenance 150]
   ["revoked marker" good (trust :revoked-artifacts #{(h "1")}) marker provenance 150]
   ["identity mismatch (other marker)" good (trust) other-marker provenance 150]
   ["tampered signature" (assoc good :signature (str/replace (:signature good) #"^." "A")) (trust) marker provenance 150]
   ["signature not base64" (assoc good :signature "!!!!") (trust) marker provenance 150]
   ["statement mutated, signature stale" (put-st good :artifact-sha256 (h "9")) (trust) marker provenance 150]
   ["validity interval inverted" (-> good (put-st :not-before (big 300))) (trust) marker provenance 150]
   ["extra envelope key" (assoc good :extra 1) (trust) marker provenance 150]
   ["wrong envelope format" (assoc good :format :nope) (trust) marker provenance 150]
   ["signer does not match key" (put-st good :signer (h "7")) (trust) marker provenance 150]
   ["malformed trust (no revoked-signers)" good (dissoc (trust) :revoked-signers) marker provenance 150]
   ["malformed trust (non-digest member)" good (trust :trusted-signers #{"x"}) marker provenance 150]
   ["trust with optional runtime sets" good (trust :trusted-runtime-sha256 #{(h "8")}) marker provenance 150]
   ["unattestable marker" good (trust) {:sha256 "nope"} provenance 150]
   ["unattestable provenance target" good (trust) marker (assoc provenance :target "wasm") 150]])

(def sign-cases
  [["sign valid" marker provenance k1 100 200]
   ["sign second key" other-marker provenance k2 5 6]
   ["sign inverted interval" marker provenance k1 200 100]
   ["sign equal interval" marker provenance k1 100 100]
   ["sign key with wrong signer" marker provenance (assoc k1 :signer (h "7")) 100 200]
   ["sign key with mismatched pair" marker provenance (assoc k1 :private-key (:private-key k2)) 100 200]
   ["sign key with extra field" marker provenance (assoc k1 :extra 1) 100 200]
   ["sign unattestable marker" {:sha256 "nope"} provenance k1 100 200]])

(def cases
  (concat
   [{:label "signer-id = host" :want (host/signer-id (:public-key k1))
     :body (str "(oat/signer-id " (pr-str (:public-key k1)) ")")}]
   (for [[label env tr m p now] verify-cases]
     (let [r (host-verify env tr m p now)]
       {:label (str "verify! " label)
        :want (if (:ok r) (str "ok " (:ok r)) (str ":reason :" (name (:threw r)) " :phase :" (name (:phase r))))
        :body (verify-body env tr m p now)}))
   (for [[label m p k nb ex] sign-cases]
     (let [r (host-sign m p k nb ex)]
       {:label label
        :want (if (:ok r) {:envelope (:ok r)} (str ":reason :" (name (:threw r))))
        :body (sign-body m p k nb ex)}))))

(defn run-main [body]
  (let [root "/tmp/probe_oat_main.cljk"
        src (str "(ns probe.oat-main\n  {:kotoba/export [main]}\n  (:require [kotoba.compiler.nbb.output-attestation :as oat]))\n"
                 "(defn main [] :vector-i64 (vector-i64-from-bytes (string-to-utf8 " body ")))\n")]
    (.writeFileSync fs root src)
    (let [graph (pf/load-closed-graph root roots)
          linked (project/link-source (:sources graph) (:root graph))
          hir (sema/analyze (:source linked) {:admit-linked-synthetics? true})
          r (kir/execute (kir/lower hir) 'main [] {:typed-cap-call typed-cap-call :fuel 400000000000 :frames 4000000
                                                   :cells 4000000000 :bytes 4000000000})]
      (.toString (js/Buffer.from (clj->js (mapv js/Number r))) "utf8"))))

(def only (some-> (.-ONLY js/process.env) (str/split #",") (->> (map js/Number) set)))
(def cases* (vec cases))
(def cases-run (if only (vec (keep-indexed (fn [i c] (when (only i) c)) cases*)) cases*))

(let [joined (reduce (fn [acc c] (str "(string-concat " acc " (string-concat \"\\n\" " (:body c) "))")) "\"\"" cases-run)
      out (try (run-main joined) (catch :default e (str "ERR " (subs (str e) 0 800))))
      lines (rest (str/split out #"\n"))
      _ (when (str/starts-with? out "ERR") (println out))
      results (doall
               (map (fn [c got]
                      (let [want (:want c)
                            ok (cond (map? want)
                                     ;; the host envelope, compared field by field on the Kotoba edn text
                                     (let [env (:envelope want)]
                                       (and (str/includes? got (str "\"" (:signature env) "\""))
                                            (str/includes? got (:signer (:statement env)))
                                            (str/includes? got (:public-key (:statement env)))))
                                     (str/starts-with? want ":reason")
                                     (let [[_ reason phase] (re-find #":reason :([a-z-]+) :phase :([a-z-]+)" want)
                                           has-reason (str/includes? got (str ":reason :" reason))]
                                       (and has-reason (or (nil? phase) (str/includes? got (str ":phase :" phase)))))
                                     :else (= got want))]
                        (println (if ok "ok  " "FAIL") (:label c) (if ok "" (str (subs got 0 (min 200 (count got))) " <> " (if (map? want) "(host envelope)" want))))
                        ok))
                    cases-run lines))]
  (println (count (filter true? results)) "of" (count cases-run) "agree")
  (.exit js/process (if (and (= (count results) (count cases-run)) (every? true? results)) 0 1)))
