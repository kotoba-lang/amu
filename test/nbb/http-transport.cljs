(ns test.nbb.http-transport
  "Repeatable nbb regression tests for the :cljs production HTTP transport
  (ADR 0117). Uses a sibling Node HTTP server process and a port file so the
  parent does not need to process async stdout while blocked on spawnSync.

  Canonical-origin is temporarily widened to accept http:// and
  destination-blocked? forced false for loopback fixtures — matching the
  clj http_transport_test.clj with-redefs pattern (allow-list membership
  itself is never redefined)."
  (:require [clojure.string :as string]
            [provider.http-transport :as transport]
            ["node:child_process" :as child]
            ["node:fs" :as fs]
            ["node:os" :as os]
            ["node:path" :as path]
            ["node:process" :as process]))

(defn- check [name ok? detail]
  {:name name :ok? (boolean ok?) :detail (when-not ok? detail)})

(def ^:private server-script
  "const http=require('http');const fs=require('fs');
const mode=process.argv[1]||'echo';
const portfile=process.argv[2];
const s=http.createServer((req,res)=>{
  let b='';
  req.on('data',c=>b+=c);
  req.on('end',()=>{
    if(mode==='redirect'){
      res.writeHead(302,{location:process.argv[3]});
      res.end('redir');
      return;
    }
    if(mode==='outside-redirect'){
      res.writeHead(302,{location:'https://evil.example.test/x'});
      res.end('outside');
      return;
    }
    res.writeHead(200,{'content-type':'text/plain','x-echo':'ok'});
    res.end('hello-'+b);
  });
});
s.listen(0,'127.0.0.1',()=>{
  fs.writeFileSync(portfile, String(s.address().port));
});
")

(defn- sleep-ms! [ms]
  (.spawnSync child js/process.execPath
              #js ["-e" (str "Atomics.wait(new Int32Array(new SharedArrayBuffer(4)),0,0," ms ")")]
              #js {:timeout (+ ms 1000)}))

(defn- start-server!
  ([mode] (start-server! mode nil))
  ([mode redirect-target]
   (let [portfile (.join path (.tmpdir os) (str "kotoba-http-fixture-" (js/Date.now) ".port"))
         args (cond-> [js/process.execPath "-e" server-script mode portfile]
                redirect-target (conj redirect-target))
         proc (.spawn child (first args) (clj->js (vec (rest args)))
                      #js {:stdio "ignore"})]
     (loop [i 0]
       (when (and (not (.existsSync fs portfile)) (< i 200))
         (sleep-ms! 20)
         (recur (inc i))))
     (when-not (.existsSync fs portfile)
       (try (.kill proc) (catch :default _))
       (throw (js/Error. "server failed to publish port file")))
     (let [port (string/trim (.readFileSync fs portfile "utf8"))]
       (try (.unlinkSync fs portfile) (catch :default _))
       {:proc proc :port port
        :origin (str "http://127.0.0.1:" port)}))))

(defn- stop-server! [{:keys [proc]}]
  (when proc
    (try (.kill proc) (catch :default _ nil))))

(defn- http-origin
  "Test-only: accept http:// and https:// absolute origins (no fragment)."
  [url]
  (when (and (string? url) (not (string/includes? url "#")))
    (when-let [[_ scheme host port]
               (re-matches #"(https?)://([A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?)(?::([0-9]+))?(?:/[^ ]*)?"
                           url)]
      (str scheme "://" (string/lower-case host) (when port (str ":" port))))))

(defn- with-http-fixture
  "Widen canonical-origin to http:// and disable destination block for loopback."
  [origins f]
  (with-redefs [transport/canonical-origin http-origin
                transport/destination-blocked? (fn [_] false)]
    (f)))

(defn- successful-post-case []
  "Transport-layer echo POST against a sibling server. Full typed
  provider boundary requires absolute HTTPS (http.cljc), so the local
  plaintext fixture exercises production-transport itself — the same
  reply shape http.cljc already dual-runtime-tests with mock transports."
  (let [server (start-server! "echo")]
    (try
      (with-http-fixture #{(:origin server)}
        (fn []
          (let [origin (:origin server)
                t (transport/production-transport {:allowed-origins #{origin}})
                reply (t {:url (str origin "/p")
                          :headers {:x-test "1"}
                          :body "world"
                          :timeout-ms 5000})]
            (check "cljs-production-transport-posts-to-local-echo-server"
                   (and (= 200 (:status reply))
                        (= "hello-world" (:body reply))
                        (nil? (:error reply))
                        (= "ok" (get-in reply [:headers :x-echo])))
                   (pr-str reply)))))
      (catch :default e
        (check "cljs-production-transport-posts-to-local-echo-server"
               false (.-message e)))
      (finally (stop-server! server)))))

(defn- destination-blocked-literal-case []
  (try
    (check "cljs-destination-blocked-detects-loopback-and-private-literals"
           (and (true? (transport/destination-blocked? "127.0.0.1"))
                (true? (transport/destination-blocked? "::1"))
                (true? (transport/destination-blocked? "10.0.0.5"))
                (true? (transport/destination-blocked? "192.168.1.1"))
                (true? (transport/destination-blocked? "169.254.169.254"))
                (true? (transport/destination-blocked? "172.16.0.1"))
                (false? (transport/destination-blocked? "203.0.113.5")))
           "literal checks failed")
    (catch :default e
      (check "cljs-destination-blocked-detects-loopback-and-private-literals"
             false (.-message e)))))

(defn- constructor-requires-origins-case []
  (try
    (let [threw? (try (transport/production-transport {})
                      false
                      (catch :default _ true))]
      (check "cljs-production-transport-requires-non-empty-allowed-origins"
             threw? "did not throw"))
    (catch :default e
      (check "cljs-production-transport-requires-non-empty-allowed-origins"
             false (.-message e)))))

(defn- redirect-outside-not-followed-case []
  (let [server (start-server! "outside-redirect")]
    (try
      (with-http-fixture #{(:origin server)}
        (fn []
          (let [origin (:origin server)
                t (transport/production-transport {:allowed-origins #{origin}})
                reply (t {:url (str origin "/r")
                          :headers {}
                          :body ""
                          :timeout-ms 5000})]
            (check "cljs-redirect-outside-allow-list-is-not-followed"
                   (and (nil? (:error reply))
                        (<= 300 (:status reply) 399))
                   (pr-str reply)))))
      (catch :default e
        (check "cljs-redirect-outside-allow-list-is-not-followed" false (.-message e)))
      (finally (stop-server! server)))))

(defn- first-hop-blocked-errors-case []
  (try
    (let [t (transport/production-transport
             {:allowed-origins #{"https://example.test"}})
          reply (t {:url "https://evil.example.test/x"
                    :headers {}
                    :body ""
                    :timeout-ms 3000})]
      (check "cljs-first-hop-outside-allow-list-is-typed-destination-blocked-error"
             (and (map? (:error reply))
                  (= :http/destination-blocked (get-in reply [:error :code]))
                  (false? (get-in reply [:error :retryable])))
             (pr-str reply)))
    (catch :default e
      (check "cljs-first-hop-outside-allow-list-is-typed-destination-blocked-error"
             false (.-message e)))))

(defn- get-stream-constructor-case []
  (try
    (let [threw? (try (transport/production-get-stream-transport {})
                      false
                      (catch :default _ true))]
      (check "cljs-production-get-stream-transport-requires-allowed-origins"
             threw?
             "constructor should require allowed-origins"))
    (catch :default e
      (check "cljs-production-get-stream-transport-requires-allowed-origins"
             false (.-message e)))))

(defn- get-stream-first-hop-blocked-case []
  (try
    (let [t (transport/production-get-stream-transport
             {:allowed-origins #{"https://example.test"}})
          threw? (try
                   (t {:operation :get-stream
                       :url "https://evil.example.test/x"
                       :headers {}})
                   false
                   (catch :default _ true))]
      (check "cljs-get-stream-first-hop-outside-allow-list-throws"
             threw?
             "get-stream should throw on first-hop refuse"))
    (catch :default e
      (check "cljs-get-stream-first-hop-outside-allow-list-throws"
             false (.-message e)))))

(let [results [(destination-blocked-literal-case)
               (constructor-requires-origins-case)
               (first-hop-blocked-errors-case)
               (successful-post-case)
               (redirect-outside-not-followed-case)
               (get-stream-constructor-case)
               (get-stream-first-hop-blocked-case)]
      failures (remove :ok? results)]
  (doseq [{:keys [name ok? detail]} results]
    (println (if ok? "PASS" "FAIL") name (or detail "")))
  (println (count results) "cases," (count failures) "failed")
  (when (seq failures) (.exit process 1)))
