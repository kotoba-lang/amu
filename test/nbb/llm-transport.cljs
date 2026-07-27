(ns test.nbb.llm-transport
  "Repeatable nbb regression tests for the :cljs production LLM transport
  (ADR 0118). Uses a sibling Node HTTP server + port file (same fixture
  pattern as test/nbb/http-transport.cljs) so spawnSync hops can reach a
  local Anthropic-Messages-shaped /v1/messages without blocking the server
  event loop."
  (:require [clojure.string :as string]
            [provider.llm-transport :as transport]
            ["node:child_process" :as child]
            ["node:fs" :as fs]
            ["node:os" :as os]
            ["node:path" :as path]
            ["node:process" :as process]))

(defn- check [name ok? detail]
  {:name name :ok? (boolean ok?) :detail (when-not ok? detail)})

(def ^:private server-script
  "const http=require('http');const fs=require('fs');
const mode=process.argv[1]||'ok';
const portfile=process.argv[2];
const s=http.createServer((req,res)=>{
  let b='';
  req.on('data',c=>b+=c);
  req.on('end',()=>{
    const send=(code,body)=>{
      const buf=Buffer.from(body,'utf8');
      res.writeHead(code,{'content-type':'application/json','content-length':buf.length});
      res.end(buf);
    };
    if(mode==='ok'){
      send(200, JSON.stringify({content:[{type:'text',text:'hello'}],
        stop_reason:'end_turn',usage:{input_tokens:12,output_tokens:3}}));
      return;
    }
    if(mode==='empty'){
      send(200, JSON.stringify({content:[{type:'thinking',thinking:'...'}],
        stop_reason:'max_tokens',usage:{input_tokens:5,output_tokens:16}}));
      return;
    }
    if(mode==='429'){ send(429, JSON.stringify({error:{message:'slow down'}})); return; }
    if(mode==='401'){ send(401, JSON.stringify({error:{message:'invalid key'}})); return; }
    if(mode==='500'){ send(500, JSON.stringify({error:{message:'boom'}})); return; }
    if(mode==='auth'){
      const auth=req.headers['authorization']||'';
      send(200, JSON.stringify({content:[{type:'text',text:auth}],
        stop_reason:'end_turn',usage:{input_tokens:1,output_tokens:1}}));
      return;
    }
    send(404, '{}');
  });
});
s.listen(0,'127.0.0.1',()=>{fs.writeFileSync(portfile, String(s.address().port));});
")

(defn- sleep-ms! [ms]
  (.spawnSync child js/process.execPath
              #js ["-e" (str "Atomics.wait(new Int32Array(new SharedArrayBuffer(4)),0,0," ms ")")]
              #js {:timeout (+ ms 1000)}))

(defn- start-server! [mode]
  (let [portfile (.join path (.tmpdir os) (str "kotoba-llm-fixture-" (js/Date.now) ".port"))
        proc (.spawn child js/process.execPath
                     #js ["-e" server-script mode portfile]
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
      {:proc proc :port port :origin (str "http://127.0.0.1:" port)})))

(defn- stop-server! [{:keys [proc]}]
  (when proc (try (.kill proc) (catch :default _ nil))))

(defn- call-transport [origin mode-opts request]
  (let [t (transport/production-transport
           (merge {:endpoint-override origin :model-override "test-model"}
                  mode-opts))]
    (t (merge {:system "" :prompt "hi" :max-output-tokens 16 :temperature-milli 0}
              request))))

(defn- override-resolve-case []
  (try
    (let [r (transport/resolve-model
             {:endpoint-override "https://pinned.example.test"
              :model-override "pinned-model"})]
      (check "cljs-resolve-model-override-wins-without-network"
             (= r {:endpoint "https://pinned.example.test"
                   :model "pinned-model"
                   :resolution :override})
             (pr-str r)))
    (catch :default e
      (check "cljs-resolve-model-override-wins-without-network" false (.-message e)))))

(defn- successful-generate-case []
  (let [server (start-server! "ok")]
    (try
      (let [reply (call-transport (:origin server) {} {})]
        (check "cljs-production-transport-successful-generation"
               (and (= "hello" (:text reply))
                    (= :end_turn (:finish-reason reply))
                    (= 12 (:input-tokens reply))
                    (= 3 (:output-tokens reply))
                    (nil? (:error reply)))
               (pr-str reply)))
      (catch :default e
        (check "cljs-production-transport-successful-generation" false (.-message e)))
      (finally (stop-server! server)))))

(defn- empty-text-case []
  (let [server (start-server! "empty")]
    (try
      (let [reply (call-transport (:origin server) {} {})]
        (check "cljs-empty-content-yields-empty-text-not-nil"
               (and (= "" (:text reply))
                    (= :max_tokens (:finish-reason reply))
                    (= 5 (:input-tokens reply))
                    (= 16 (:output-tokens reply)))
               (pr-str reply)))
      (catch :default e
        (check "cljs-empty-content-yields-empty-text-not-nil" false (.-message e)))
      (finally (stop-server! server)))))

(defn- rate-limited-case []
  (let [server (start-server! "429")]
    (try
      (let [reply (call-transport (:origin server) {} {})]
        (check "cljs-http-429-maps-to-retryable-typed-error"
               (and (= :llm/rate-limited (get-in reply [:error :code]))
                    (true? (get-in reply [:error :retryable]))
                    (string/includes? (get-in reply [:error :message]) "429"))
               (pr-str reply)))
      (catch :default e
        (check "cljs-http-429-maps-to-retryable-typed-error" false (.-message e)))
      (finally (stop-server! server)))))

(defn- unauthorized-case []
  (let [server (start-server! "401")]
    (try
      (let [reply (call-transport (:origin server) {} {})]
        (check "cljs-http-401-maps-to-non-retryable-typed-error"
               (and (= :llm/unauthorized (get-in reply [:error :code]))
                    (false? (get-in reply [:error :retryable])))
               (pr-str reply)))
      (catch :default e
        (check "cljs-http-401-maps-to-non-retryable-typed-error" false (.-message e)))
      (finally (stop-server! server)))))

(defn- upstream-error-case []
  (let [server (start-server! "500")]
    (try
      (let [reply (call-transport (:origin server) {} {})]
        (check "cljs-http-500-maps-to-retryable-typed-error"
               (and (= :llm/upstream-error (get-in reply [:error :code]))
                    (true? (get-in reply [:error :retryable])))
               (pr-str reply)))
      (catch :default e
        (check "cljs-http-500-maps-to-retryable-typed-error" false (.-message e)))
      (finally (stop-server! server)))))

(defn- api-key-bearer-case []
  (let [server (start-server! "auth")]
    (try
      (let [reply (call-transport (:origin server) {:api-key "secret-token-value"} {})]
        (check "cljs-api-key-is-sent-as-bearer-header"
               (= "Bearer secret-token-value" (:text reply))
               (pr-str reply)))
      (catch :default e
        (check "cljs-api-key-is-sent-as-bearer-header" false (.-message e)))
      (finally (stop-server! server)))))

(let [results [(override-resolve-case)
               (successful-generate-case)
               (empty-text-case)
               (rate-limited-case)
               (unauthorized-case)
               (upstream-error-case)
               (api-key-bearer-case)]
      failures (remove :ok? results)]
  (doseq [{:keys [name ok? detail]} results]
    (println (if ok? "PASS" "FAIL") name (or detail "")))
  (println (count results) "cases," (count failures) "failed")
  (when (seq failures) (.exit process 1)))
