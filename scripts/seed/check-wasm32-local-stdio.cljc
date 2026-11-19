;; Observe local Worker stdin/stdout with a selfhost-compiled Wasm probe. Ported from check-wasm32-local-stdio.py
;; (Basilisp, JUN-974); uses the DevTools-pipe client of wasm32_browser_lib.cljc.
;; Run: basilisp run -p scripts/seed scripts/seed/check-wasm32-local-stdio.cljc -- --wasm F --output-probe F
;;   --read-probe F --broker-probe F --all-probe F --browser PATH --output DIR
(ns check-wasm32-local-stdio
  (:require [basilisp.string :as str]
            [gate-util :as u]
            [wasm32-browser-lib :as w])
  (:import base64 hashlib json operator pathlib shutil sys time))

(def root u/root)
(defn rp [rel] (pathlib/Path root rel))
(defn g [m & ks] (reduce (fn [a k] (operator/getitem a k)) m ks))
(defn has? [m k] (operator/contains m k))
(defn chk [c m] (u/chk c (str m)))
(defn b64 [data] (.decode (base64/b64encode data)))
(defn sha [data] (u/sha256-hex data))
(defn lst [& xs] (python/list xs))
(defn kinds [row] (python/list (map #(g % "kind") (g row "events"))))
(defn reads [row] (python/list (for [e (g row "events") :when (= (g e "kind") "read")] (g e "request"))))
(defn read-count [row] (count (filter #(= (g % "kind") "read") (g row "events"))))
(defn contains-str? [s sub] (and (string? s) (str/includes? s sub)))

(defn -main [& args]
  (let [need (fn [k] (or (u/opt args k) (sys/exit (str k " is required"))))
        wasm-path (pathlib/Path (need "--wasm")) output-probe (pathlib/Path (need "--output-probe"))
        read-probe (pathlib/Path (need "--read-probe")) broker-probe (pathlib/Path (need "--broker-probe"))
        all-probe (pathlib/Path (need "--all-probe")) browser-arg (need "--browser")
        out (.resolve (pathlib/Path (need "--output")))
        _ (.mkdir out ** :parents true :exist_ok false)
        host (rp "runtime/wasm32-browser-static-host.js")
        page (rp "runtime/wasm32-browser-local-stdio-test.html")
        queue (rp "runtime/wasm32-browser-local-stdio.js")]
    (doseq [source [host page queue]] (shutil/copyfile source (pathlib/Path out (.-name source))))
    (let [data (.read_bytes wasm-path) output-data (.read_bytes output-probe) read-data (.read_bytes read-probe)
          broker-data (.read_bytes broker-probe) all-data (.read_bytes all-probe)
          magic (u/bytes-of 0 0x61 0x73 0x6d 1 0 0 0)]
      (chk (u/deq (u/bslice data 0 8) magic) "wasm magic")
      (chk (every? #(u/deq (u/bslice % 0 8) magic) [output-data read-data broker-data all-data]) "probe magic")
      (.write_text (pathlib/Path out "runs.js")
                   (str "window.KOTOBA_WASM=" (json/dumps (b64 data)) ";\n"
                        "window.KOTOBA_OUTPUT_WASM=" (json/dumps (b64 output-data)) ";\n"
                        "window.KOTOBA_READ_WASM=" (json/dumps (b64 read-data)) ";\n"
                        "window.KOTOBA_BROKER_WASM=" (json/dumps (b64 broker-data)) ";\n"
                        "window.KOTOBA_ALL_WASM=" (json/dumps (b64 all-data)) ";\n"))
      (let [browser (w/find-browser browser-arg)
            _ (chk browser "browser")
            profile (pathlib/Path out "profile")
            _ (.mkdir profile)
            pipe (w/open-pipe browser profile)
            [version result]
            (try
              (let [version (w/call pipe "Browser.getVersion")
                    target (g (w/call pipe "Target.createTarget" (u/pydict "url" (.as_uri (pathlib/Path out (.-name page))))) "targetId")
                    session (g (w/call pipe "Target.attachToTarget" (u/pydict "targetId" target "flatten" true)) "sessionId")
                    deadline (+ (time/monotonic) 150)
                    result (loop []
                             (let [value (w/call pipe "Runtime.evaluate"
                                                 (u/pydict "expression" "document.title === 'kotoba-done' ? document.getElementById('results').textContent : null" "returnByValue" true)
                                                 session)
                                   v (.get (.get value "result" (python/dict)) "value")]
                               (cond (some? v) (json/loads v)
                                     (< (time/monotonic) deadline) (do (time/sleep 0.2) (recur))
                                     :else nil)))]
                (chk (and (some? result) (true? (.get result "jspi"))) result)
                [version result])
              (finally (w/close-pipe pipe)))]
        (.write_text (pathlib/Path out "results.json") (str (json/dumps result ** :ensure_ascii false :indent 2) "\n"))
        (let [rows (python/dict)]
          (doseq [row (g result "results")] (operator/setitem rows (g row "name") row))
          (chk (u/deq (python/set (python/list (.keys rows)))
                      (python/set ["success" "queued" "queue-abort" "queue-read-all" "ack-output" "ack-large-output" "ack-rejected" "ack-aborted" "ack-no-jspi" "denied" "not-local" "no-jspi" "conflict" "oversized" "lone-surrogate" "read-refused" "bounded-output" "bounded-read-log" "broker-isolation"]))
               "row names")
          (let [r (fn [n] (g rows n))
                success (r "success")]
            (chk (and (= (g success "exit") 0) (contains-str? (g success "report") ":status :ok :result 42")) success)
            (chk (= (g success "output") "READY\nDONE\n") success)
            (chk (u/deq (kinds success) (lst "output" "read" "read" "read" "output" "output")) success)
            (chk (and (= (g (g success "events") 0 "text") "READY\n") (= (g (g success "events") 4 "text") "DONE\n")) "success texts")
            (chk (.startswith (g (g success "events") 5 "text") "{:status :ok :result 42 ") "success report event")
            (chk (u/deq (reads success) (lst "1" "1" "1")) "success reads")
            (let [queued (r "queued")]
              (chk (and (= (g queued "exit") 0) (contains-str? (g queued "report") ":status :ok :result 42")) "queued")
              (chk (and (g queued "capacityRefused") (g queued "invalidUnicodeRefused")) "queued refusals")
              (chk (u/deq (kinds queued) (lst "output" "read" "read" "read" "output" "output")) "queued kinds")
              (chk (= (apply str (for [item (g queued "queueOutput") :when (= (g item "fd") 1)] (g item "text"))) (g queued "stdout")) "queue stdout"))
            (chk (and (= (g (r "queue-abort") "exit") 120) (contains-str? (g (r "queue-abort") "report") ":status :trap")) "queue-abort")
            (chk (and (= (g (r "queue-read-all") "exit") 0) (contains-str? (g (r "queue-read-all") "report") ":status :ok :result 42")) "queue-read-all")
            (chk (u/deq (reads (r "queue-read-all")) (lst "")) "queue-read-all reads")
            (let [ack (r "ack-output")]
              (chk (and (= (g ack "exit") 0) (contains-str? (g ack "report") ":status :ok :result 42")) ack)
              (chk (and (= (g ack "maxActiveOutput") 1) (= (g ack "settledOutput") (python/len (g ack "queueOutput")) 3)) ack)
              (chk (= (apply str (map #(g % "text") (g ack "queueOutput"))) (g ack "stdout")) ack))
            (let [large-ack (r "ack-large-output")]
              (chk (and (= (g large-ack "exit") 0) (= (g large-ack "maxActiveOutput") 1) (g large-ack "stdoutTruncated")) large-ack)
              (chk (u/deq (python/list (map #(python/len (g % "text")) (operator/getitem (g large-ack "queueOutput") (python/slice nil 2)))) (lst 65536 4464)) large-ack))
            (doseq [name ["ack-rejected" "ack-aborted"]]
              (let [refused (r name)]
                (chk (and (= (g refused "exit") 120) (contains-str? (g refused "wasmTrap") "local output refused") (= (python/len (g refused "events")) 1)) refused)))
            (let [no-jspi (r "ack-no-jspi")]
              (chk (and (= (g no-jspi "exit") 120) (contains-str? (g no-jspi "wasmTrap") "requires localStdio and JSPI") (zero? (python/len (g no-jspi "events")))) no-jspi))
            (chk (not (some (fn [[name row]] (and (not= name "broker-isolation") (some #(= (g % "kind") "broker") (g row "events")))) (.items rows))) "no broker events outside isolation")
            (doseq [name ["denied" "not-local" "no-jspi" "oversized" "lone-surrogate" "read-refused"]]
              (chk (and (= (g (r name) "exit") 120) (contains-str? (or (g (r name) "report") "") ":status :trap")) (r name)))
            (chk (not (some #(= (g % "kind") "read") (mapcat #(g (r %) "events") ["denied" "not-local" "no-jspi"]))) "no reads when denied")
            (chk (and (= (g (r "conflict") "exit") 120) (contains-str? (g (r "conflict") "wasmTrap") "both local stdin and broker-bound")) "conflict")
            (chk (every? #(= (read-count (r %)) 1) ["oversized" "lone-surrogate" "read-refused"]) "single reads")
            (let [large (r "bounded-output")]
              (chk (and (= (g large "exit") 0) (contains-str? (g large "report") ":status :ok :result 42") (true? (g large "stdoutTruncated"))) large)
              (chk (and (<= (python/len (.encode (g large "stdout") "utf-8")) 65536)
                        (> (reduce + (for [e (g large "events") :when (= (g e "kind") "output")] (python/len (g e "text")))) 70000)) large))
            (let [many (r "bounded-read-log")]
              (chk (and (= (g many "exit") 0) (contains-str? (g many "report") ":status :ok :result 42") (true? (g many "localReadLogTruncated"))) many)
              (chk (and (= (read-count many) 257) (= (python/len (g many "capLog")) 256)) many))
            (let [broker (r "broker-isolation")]
              (chk (and (= (g broker "exit") 0) (contains-str? (g broker "report") ":status :ok :result 6") (= (g broker "output") "200\nok\n")) broker)
              (chk (u/deq (g broker "events") (python/list [(u/pydict "kind" "broker" "wire" 45)])) broker))))
        (let [receipt (u/pydict "status" "PASS_LOCAL_STDIO_OFFLINE" "browser" (.get version "product")
                                "wasmSha256" (sha data) "outputProbeSha256" (sha output-data) "readProbeSha256" (sha read-data)
                                "brokerProbeSha256" (sha broker-data) "allProbeSha256" (sha all-data)
                                "hostSha256" (sha (.read_bytes host)) "pageSha256" (sha (.read_bytes page)) "queueSha256" (sha (.read_bytes queue))
                                "network" "CSP connect-src none" "realUserQualified" false "browserProjectQualified" false "brokerReviewQualified" false)]
          (.write_text (pathlib/Path out "receipt.json") (u/json-dump receipt))
          (println (g receipt "status") (g receipt "browser")))))))

(when (some #(or (= % "check-wasm32-local-stdio.cljc") (str/ends-with? % "/check-wasm32-local-stdio.cljc")) sys/argv)
  (apply -main *command-line-args*))
