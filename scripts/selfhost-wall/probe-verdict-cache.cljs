;; Differential probe: the Kotoba reading of kotoba.compiler.nbb.verdict-cache (key-material, key-for,
;; record-digest, limits-digest, toolchain-digest, open-store, lookup-verdict, store-verdict!) on the KIR
;; interpreter, with fs/app-data, fs/browse, env/read and entropy/draw answered by the nbb handlers, against the
;; host reading and a real directory:
;;  * key-material/key-for are the host's, byte for byte;
;;  * limits-digest equals the host's;
;;  * toolchain-digest equals an independent JS evaluation of the host's algorithm (runtime named "kotoba", as the
;;    host's non-Node reading names it; the Node version cannot be reproduced);
;;  * a record the Kotoba reading writes is a :hit for the host's resolve!, and a record the host wrote is read by
;;    the Kotoba lookup-verdict; corrupt / foreign / symlinked entries are misses and are deleted.
;; KROOTS as in probe-compile-cache.cljs.
(ns vc-probe
  (:require ["node:fs" :as fs]
            ["node:os" :as os]
            ["node:path" :as path]
            ["node:crypto" :as crypto]
            [clojure.string :as str]
            [kotoba.sema :as sema]
            [kotoba.kir :as kir]
            [kotoba.compiler.project :as project]
            [kotoba.compiler.project-files :as pf]
            [kotoba.compiler.nbb.host.fs :as host-fs]
            [kotoba.compiler.nbb.host.env :as host-env]
            [kotoba.compiler.nbb.host.entropy :as host-entropy]
            [kotoba.kir.compatibility :as compat]
            [kotoba.compiler.nbb.verdict-cache :as host]))

(def roots (vec (str/split (.-KROOTS js/process.env) #":")))
(defn as-buffer [x] (if (string? x) (.from js/Buffer x "utf8") (.from js/Buffer x)))
(def token "WRITE_SEP")

(defn typed-cap-call [id request-type result-type request]
  (case (js/Number id)
    3 (-> (.createHash crypto "sha256") (.update request) (.digest "hex"))
    23 (host-entropy/draw request)
    33 (host-env/read request)
    34 (host-fs/browse request)
    35 (if (string? request)
         (if (= result-type :bytes) (host-fs/app-data-bytes request) (host-fs/app-data request))
         (let [buf (as-buffer request)
               at (.indexOf buf token)]
           (if (>= at 0)
             (do (host-fs/app-data-bytes (str (.toString (.subarray buf 0 at) "utf8") token)
                                         (.subarray buf (+ at (count token))))
                 (if (= result-type :bytes) (js/Uint8Array. 0) ""))
             (host-fs/app-data-bytes (.toString buf "utf8")))))
    (throw (ex-info "unhandled capability" {:id id}))))

(defn q [s] (pr-str s))
(defn doc [x] (str "(document-edn-read " (q (pr-str x)) ")"))
(defn sha [x] (-> (.createHash crypto "sha256") (.update x) (.digest "hex")))
(defn h [c] (apply str (repeat 64 c)))

;; ---- fixtures ----------------------------------------------------------
(def base (.mkdtempSync fs (.join path (.tmpdir os) "vc-probe-")))
(defn p [& xs] (apply (.-join path) base xs))
(defn write! [file text] (.mkdirSync fs (.dirname path file) #js {:recursive true}) (.writeFileSync fs file text))
(write! (p "cp1" "a.txt") "alpha")
(write! (p "cp1" "sub" "b.txt") "beta \u00e9")
(write! (p "cp1" "sub" "deep" "c.txt") "gamma")
(write! (p "cp2" "kotoba" "lang" "limits.edn") "{:record-fields 4096}\n")
(write! (p "cp3" "single.cljk") "(ns x)")
(def gitlib (p "cp4" ".gitlibs" "libs" "grp" "art" (apply str (repeat 40 "a"))))
(write! (p gitlib "x.cljk") "pinned content")
(def entries [(p "cp1") (p "cp2") (p "cp3" "single.cljk") (p "missing") gitlib])

;; the toolchain text, independently, from the host's documented algorithm with the Kotoba runtime name
(defn files-under [dir rel]
  (mapcat (fn [name]
            (let [file (.join path dir name) r (if (= "" rel) name (str rel "/" name))
                  st (.lstatSync fs file)]
              (cond (.isDirectory st) (files-under file r)
                    (.isFile st) [[r file]])))
          (sort (fn [a b] (js/Buffer.compare (js/Buffer.from a) (js/Buffer.from b))) (js->clj (.readdirSync fs dir)))))
(defn pinned? [e] (boolean (re-find #"[/\\]\.gitlibs[/\\]libs[/\\].+[/\\][0-9a-f]{40}([/\\]|$)" e)))
(def toolchain-expected
  (sha (apply str "kotoba.verdict-toolchain/v2\u0000kotoba\u0000" (pr-str compat/compiler-version) "\u0000"
              (for [e entries]
                (str "entry\u0000" e "\u0000"
                     (cond (pinned? e) "pinned\u0000"
                           (not (.existsSync fs e)) "absent\u0000"
                           (.isFile (.statSync fs e)) (str "sha256\u0000" (sha (.readFileSync fs e)) "\u0000")
                           :else (apply str (for [[r f] (files-under e "")]
                                              (str "file\u0000" r "\u0000" (sha (.readFileSync fs f)) "\u0000")))))))))

(def fields1 {:definitions ["d1" "d2"] :subject (h "5") :toolchain (h "6") :target :wasm32-kotoba-v1
              :capabilities (h "7") :limits (h "8")})
(def fields2 (dissoc fields1 :limits))
(def kind :kotoba.verdict/native-verify)

;; ---- the store fixtures for the lookup half ----------------------------
(def store (p "store"))
(.mkdirSync fs store #js {:mode 448})
(.chmodSync fs store 448)
(host-env/read "HOME")
(defn host-write! [n]
  ;; a record written by the HOST reading (resolve! miss), for fields varying in :subject
  (let [fields (assoc fields1 :subject (h (str n)))
        result (host/resolve! {:dir store :max-entries 4096 :max-bytes 16777216} kind fields (fn [] nil))]
    {:key (:key result) :fields fields}))
(def good (host-write! 1))
(def corrupt (host-write! 2))
(def foreign (host-write! 3))
(def linked (host-write! 4))
(def absent {:key (sha "never written")})
(let [f (.join path store (str (:key corrupt) ".edn"))]
  (.writeFileSync fs f (str/replace (.readFileSync fs f "utf8") #":digest \"[0-9a-f]{2}" ":digest \"00")))
(.chmodSync fs (.join path store (str (:key foreign) ".edn")) 438)
(let [f (.join path store (str (:key linked) ".edn"))]
  (.unlinkSync fs f)
  (.symlinkSync fs (.join path store (str (:key good) ".edn")) f))
;; a refused verdict, host-written
(def refused-fields (assoc fields1 :subject (h "r")))
(def refused-result
  (try (host/resolve! {:dir store :max-entries 4096 :max-bytes 16777216} kind refused-fields
                      (fn [] (throw (ex-info "native refusal" {:phase :verify :code 7}))))
       (catch :default _ nil)))
(def refused-key (host/key-for (host/key-material kind refused-fields)))

;; the Kotoba-written store, a fresh private dir
(def kstore (p "kstore"))
(def kfields (assoc fields1 :subject (h "k")))
(def kmaterial (host/key-material kind kfields))
(def kkey (host/key-for kmaterial))
(def krefused-fields (assoc fields1 :subject (h "kr")))
(def krefused-material (host/key-material kind krefused-fields))
(def krefused-key (host/key-for krefused-material))

(defn str-result [expr]
  (str "(let [r " expr "] (if (result-ok?-of [:result :string :document] r) (result-value-of [:result :string :document] r \"\") "
       "(string-concat \"threw \" (document-edn-print (result-error-of [:result :string :document] r (document-null))))))"))
(defn bool-text [expr] (str "(if " expr " \"true\" \"false\")"))
(defn doc-text [expr] (str "(document-edn-print " expr ")"))
(defn some-text [expr] (str "(option-value-of [:option :string] " expr " \"none\")"))

(def cases
  [{:label "key-material = host (all fields)" :want (pr-str (host/key-material kind fields1))
    :body (doc-text (str "(vc/key-material :kotoba.verdict/native-verify " (doc fields1) ")"))}
   {:label "key-material = host (field absent -> nil)" :want (pr-str (host/key-material kind fields2))
    :body (doc-text (str "(vc/key-material :kotoba.verdict/native-verify " (doc fields2) ")"))}
   {:label "key-for = host" :want (host/key-for (host/key-material kind fields1))
    :body (str "(vc/key-for (vc/key-material :kotoba.verdict/native-verify " (doc fields1) "))")}
   {:label "key-for = host (absent field)" :want (host/key-for (host/key-material kind fields2))
    :body (str "(vc/key-for (vc/key-material :kotoba.verdict/native-verify " (doc fields2) "))")}
   {:label "record-digest = host" :want (host/record-digest (h "a") (host/key-material kind fields1) {:admitted true})
    :body (str "(vc/record-digest " (q (h "a")) " " (doc (host/key-material kind fields1)) " " (doc {:admitted true}) ")")}
   {:label "limits-digest = host" :want (host/limits-digest entries)
    :body (some-text (str "(vc/limits-digest " (doc entries) ")"))}
   {:label "limits-digest none" :want "none"
    :body (some-text (str "(vc/limits-digest " (doc [(p "cp1") (p "missing")]) ")"))}
   {:label "toolchain-digest = host algorithm" :want toolchain-expected
    :body (str-result (str "(vc/toolchain-digest " (doc entries) " \"/\")"))}
   {:label "open-store existing private dir" :want store
    :body (str-result (str "(vc/open-store " (q store) ")"))}
   {:label "open-store creates a private dir" :want kstore
    :body (str-result (str "(vc/open-store " (q kstore) ")"))}
   {:label "lookup host-written admitted" :want "{:admitted true}"
    :body (doc-text (str "(vc/lookup-verdict " (q store) " " (q (:key good)) ")"))}
   {:label "lookup host-written refused" :want (pr-str {:refused {:message "native refusal" :data {:phase :verify :code 7}}})
    :body (doc-text (str "(vc/lookup-verdict " (q store) " " (q refused-key) ")"))}
   {:label "lookup corrupt digest is a miss" :want "nil"
    :body (doc-text (str "(vc/lookup-verdict " (q store) " " (q (:key corrupt)) ")"))}
   {:label "lookup foreign mode is a miss" :want "nil"
    :body (doc-text (str "(vc/lookup-verdict " (q store) " " (q (:key foreign)) ")"))}
   {:label "lookup symlinked entry is a miss" :want "nil"
    :body (doc-text (str "(vc/lookup-verdict " (q store) " " (q (:key linked)) ")"))}
   {:label "lookup absent is a miss" :want "nil"
    :body (doc-text (str "(vc/lookup-verdict " (q store) " " (q (:key absent)) ")"))}
   {:label "lookup with the store off" :want "nil"
    :body (doc-text (str "(vc/lookup-verdict \"\" " (q (:key good)) ")"))}
   {:label "store-verdict! admitted" :want "1"
    :body (str "(string-from-i64 (vc/store-verdict! " (q kstore) " " (q kkey) " " (doc kmaterial) " " (doc {:admitted true}) "))")}
   {:label "store-verdict! refused" :want "1"
    :body (str "(string-from-i64 (vc/store-verdict! " (q kstore) " " (q krefused-key) " " (doc krefused-material) " "
               (doc {:refused {:message "kotoba refusal" :data {:phase :verify}}}) "))")}
   {:label "lookup what Kotoba wrote" :want "{:admitted true}"
    :body (doc-text (str "(vc/lookup-verdict " (q kstore) " " (q kkey) ")"))}])

(def only (some-> (.-ONLY js/process.env) (str/split #",") (->> (map js/Number) set)))
(def cases* cases)
(defn run-main [body]
  (let [root "/tmp/probe_vc_main.cljk"
        src (str "(ns probe.vc-main\n  {:kotoba/export [main]}\n  (:require [kotoba.compiler.nbb.verdict-cache :as vc] [kotoba.lang.edn :as edn]))\n"
                 "(defn main [] :vector-i64 (vector-i64-from-bytes (string-to-utf8 " body ")))\n")]
    (.writeFileSync fs root src)
    (let [graph (pf/load-closed-graph root roots)
          linked (project/link-source (:sources graph) (:root graph))
          hir (sema/analyze (:source linked) {:admit-linked-synthetics? true})
          r (kir/execute (kir/lower hir) 'main [] {:typed-cap-call typed-cap-call :fuel 4000000000 :frames 400000
                                                   :cells 400000000 :bytes 400000000})]
      (.toString (js/Buffer.from (clj->js (mapv js/Number r))) "utf8"))))

(when-let [b (.-BODY js/process.env)]
  (println (try (run-main (-> b (str/replace "STORE" (q store)) (str/replace "GOODKEY" (q (:key good))))) (catch :default e (str "ERR " (subs (str e) 0 500)))))
  (.exit js/process 0))
(def cases (if only (vec (keep-indexed (fn [i c] (when (only i) c)) cases*)) cases*))
(let [joined (reduce (fn [acc c] (str "(string-concat " acc " (string-concat \"\\n\" " (:body c) "))")) "\"\"" cases)
      out (try (run-main joined) (catch :default e (str "ERR " (subs (str e) 0 800))))
      lines (rest (str/split out #"\n"))
      _ (when (str/starts-with? out "ERR") (println out))
      same-doc? (fn [want got] (or (= want got)
                                   ;; maps print in the document's key order
                                   (and (str/starts-with? want "{")
                                        (let [norm (fn [t] (sort (str/replace t #"[\s,]" "")))] (= (norm want) (norm got))))))
      results (doall (map (fn [c got]
                            (let [ok (same-doc? (:want c) got)]
                              (println (if ok "ok  " "FAIL") (:label c) (if ok "" (str got " <> " (:want c))))
                              ok))
                          cases lines))
      gone? (fn [k] (not (.existsSync fs (.join path store (str k ".edn")))))
      extra (when-not only [["rejected corrupt entry deleted" (gone? (:key corrupt))]
             ["rejected foreign entry deleted" (gone? (:key foreign))]
             ["rejected symlink deleted (target kept)" (and (gone? (:key linked)) (not (gone? (:key good))))]
             ["Kotoba store dir is 0700" (= 448 (bit-and (.-mode (.statSync fs kstore)) 511))]
             ["Kotoba record file is 0600" (= 384 (bit-and (.-mode (.statSync fs (.join path kstore (str kkey ".edn")))) 511))]
             ["no temporary left behind" (empty? (filter #(str/ends-with? % ".tmp") (js->clj (.readdirSync fs kstore))))]
             ["host reads the Kotoba admitted record as a hit"
              (= :hit (:cache (host/resolve! {:dir kstore} kind kfields (fn [] (throw (ex-info "recomputed" {}))))))]
             ["host reads the Kotoba refused record as the same refusal"
              (= "kotoba refusal"
                 (try (host/resolve! {:dir kstore} kind krefused-fields (fn [] nil)) nil
                      (catch :default e (ex-message e))))]])
      extra-results (if only [] (doall (map (fn [[label ok]] (println (if ok "ok  " "FAIL") label) ok) extra)))
      all (concat results extra-results)]
  (println (count (filter true? all)) "of" (+ (count cases) (count extra)) "agree")
  (.exit js/process (if (and (= (count results) (count cases)) (every? true? all)) 0 1)))
