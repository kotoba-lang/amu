;; Differential probe: the Kotoba on-disk store of kotoba.compiler.nbb.compile-cache (put!, lookup, remove!, stats)
;; running on the KIR interpreter, with the fs/app-data, fs/browse and env/read abilities answered by the nbb
;; handlers (kotoba.compiler.nbb.host.*), against a real directory. Checks the contract the module states:
;; round trip, tampered bytes are a miss, a group/world-writable or absent directory disables the store, a key
;; that is not 64 lowercase hex is never joined into a path. KROOTS as in probe-compile-cache.cljs.
(ns cc-store-probe
  (:require ["node:fs" :as fs]
            ["node:os" :as os]
            ["node:path" :as path]
            [clojure.string :as str]
            [kotoba.sema :as sema]
            [kotoba.kir :as kir]
            [kotoba.compiler.project :as project]
            [kotoba.compiler.project-files :as pf]
            [kotoba.compiler.nbb.host.fs :as host-fs]
            [kotoba.compiler.nbb.host.env :as host-env]
            ["node:crypto" :as crypto]
            [kotoba.compiler.nbb.compile-cache :as host]))

(def roots (vec (str/split (.-KROOTS js/process.env) #":")))
(def token "WRITE_SEP")

(defn as-buffer [x] (if (string? x) (.from js/Buffer x "utf8") (.from js/Buffer x)))

(defn typed-cap-call [id request-type result-type request]
  (case (js/Number id)
    3 (-> (.createHash crypto "sha256") (.update request) (.digest "hex"))
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

(defn run-main [body]
  (let [root "/tmp/probe_ccs_main.cljk"
        src (str "(ns probe.ccs-main\n  {:kotoba/export [main]}\n  (:require [kotoba.compiler.nbb.compile-cache :as cc]))\n"
                 "(defn main [] :vector-i64 (vector-i64-from-bytes (string-to-utf8 " body ")))\n")]
    (.writeFileSync fs root src)
    (let [graph (pf/load-closed-graph root roots)
          linked (project/link-source (:sources graph) (:root graph))
          hir (sema/analyze (:source linked) {:admit-linked-synthetics? true})
          r (kir/execute (kir/lower hir) 'main [] {:typed-cap-call typed-cap-call :fuel 1000000000 :frames 400000
                                                   :cells 100000000 :bytes 100000000})]
      (.toString (js/Buffer.from (clj->js (mapv js/Number r))) "utf8"))))

(defn q [s] (pr-str s))
(defn step [dir key]
  ;; put, look up, report; the payload round-trips as text.
  (str "(string-concat \"put=\" (string-concat (string-from-i64 (cc/put! " (q dir) " " (q key) " (string-to-utf8 \"payload \\u00e9\")))"
       " (string-concat \" hit=\" (string-concat (if (record-get (cc/lookup " (q dir) " " (q key) " 1048576) :hit) \"1\" \"0\")"
       " (string-concat \" data=\" (string-from-utf8 (record-get (cc/lookup " (q dir) " " (q key) " 1048576) :data)))))))"))
(defn look [dir key]
  (str "(string-concat \"hit=\" (if (record-get (cc/lookup " (q dir) " " (q key) " 1048576) :hit) \"1\" \"0\"))"))

(def key1 (host/sha256 "k1"))
(def base (.mkdtempSync fs (.join path (.tmpdir os) "cc-store-")))
(def good (.join path base "good"))
(.mkdirSync fs good #js {:mode 448})
(.chmodSync fs good 448)
(def open (.join path base "open"))
(.mkdirSync fs open)
(.chmodSync fs open 511)


(defn check [label got want]
  (let [ok (= got want)] (println (if ok "ok  " "FAIL") label (if ok "" (pr-str {:got got :want want}))) ok))

(def results
  (atom
   [(check "round trip" (run-main (step good key1)) "put=1 hit=1 data=payload \u00e9")
    (check "stage round trip (put-stage!/lookup-stage)"
           (run-main (str "(string-concat (string-from-i64 (cc/put-stage! " (q good) " " (q (host/sha256 "stage")) " \"{:value 42}\")) (string-concat \" \" (cc/lookup-stage " (q good) " " (q (host/sha256 "stage")) " 1048576)))"))
           "1 {:value 42}")
    (check "bin file is 0600"
           (bit-and (.-mode (.statSync fs (.join path good (str key1 ".bin")))) 511) 384)
    (check "stats counts the files of both entries"
           (run-main (str "(string-from-i64 (cc/stats " (q good) "))")) "4")
    (check "stored digest is sha256 of the bytes"
           (.readFileSync fs (.join path good (str key1 ".sha256")) "utf8")
           (-> (.createHash crypto "sha256") (.update (.from js/Buffer "payload \u00e9" "utf8")) (.digest "hex")))
    (do (.writeFileSync fs (.join path good (str key1 ".bin")) (.from js/Buffer "tampered"))
        (check "tampered bytes are a miss" (run-main (look good key1)) "hit=0"))
    (do (.writeFileSync fs (.join path good (str key1 ".bin")) (.from js/Buffer "payload \u00e9"))
        (check "restored bytes hit again" (run-main (look good key1)) "hit=1"))
    (do (.unlinkSync fs (.join path good (str key1 ".sha256")))
        (check "missing digest is a miss" (run-main (look good key1)) "hit=0"))
    (do (run-main (str "(string-from-i64 (cc/remove! " (q good) " " (q key1) "))"))
        (check "remove! leaves no file of that key"
               (count (filter #(str/starts-with? % key1) (js->clj (.readdirSync fs good)))) 0))
    (check "world-writable dir disables" (run-main (step open key1)) "put=0 hit=0 data=")
    (check "absent dir disables" (run-main (step (.join path base "nope") key1)) "put=0 hit=0 data=")
    (check "empty dir name disables" (run-main (step "" key1)) "put=0 hit=0 data=")
    (check "non-hex key is refused" (run-main (step good "../escape")) "put=0 hit=0 data=")]))

(println (count (filter true? @results)) "of" (count @results) "agree")
(.exit js/process (if (every? true? @results) 0 1))
