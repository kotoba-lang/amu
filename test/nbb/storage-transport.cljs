(ns test.nbb.storage-transport
  "Repeatable nbb regression tests for the :cljs production storage transport
  (ADR 0119). Sibling Node HTTP server + port file (same pattern as
  http/llm nbb transport tests) speaking the host-configured KV wire
  protocol from ADR 0071."
  (:require [clojure.string :as string]
            [provider.storage-transport :as transport]
            ["node:child_process" :as child]
            ["node:fs" :as fs]
            ["node:os" :as os]
            ["node:path" :as path]
            ["node:process" :as process]))

(defn- check [name ok? detail]
  {:name name :ok? (boolean ok?) :detail (when-not ok? detail)})

(def ^:private server-script
  "const http=require('http');const fs=require('fs');
const mode=process.argv[1]||'kv';
const portfile=process.argv[2];
const store=new Map();
const s=http.createServer((req,res)=>{
  let b='';
  req.on('data',c=>b+=c);
  req.on('end',()=>{
    const send=(code,obj)=>{
      const body=JSON.stringify(obj);
      const buf=Buffer.from(body,'utf8');
      res.writeHead(code,{'content-type':'application/json','content-length':buf.length});
      res.end(buf);
    };
    if(mode==='429'){ send(429,{error:{message:'slow'}}); return; }
    if(mode==='500'){ send(500,{error:{message:'boom'}}); return; }
    let parsed;
    try { parsed=JSON.parse(b); } catch(e) { send(400,{tag:'error',error:{code:'bad',message:String(e),retryable:false}}); return; }
    const sk=JSON.stringify([parsed.namespace, parsed.key]);
    const op=parsed.operation;
    if(op==='get'){
      if(store.has(sk)){
        const e=store.get(sk);
        send(200,{tag:'found',value:e.value,version:e.version});
      } else send(200,{tag:'missing'});
      return;
    }
    if(op==='put'){
      const cur=store.get(sk);
      const expected=parsed.expected_version;
      if(expected!=null && cur && expected!==cur.version){
        send(200,{tag:'conflict',current_version:cur.version});
        return;
      }
      const next=(cur?cur.version:0)+1;
      store.set(sk,{value:parsed.value,version:next});
      send(200,{tag:'written',value:parsed.value,version:next});
      return;
    }
    if(op==='delete'){
      const cur=store.get(sk);
      const expected=parsed.expected_version;
      if(expected!=null && cur && expected!==cur.version){
        send(200,{tag:'conflict',current_version:cur.version});
        return;
      }
      store.delete(sk);
      send(200,{tag:'deleted'});
      return;
    }
    send(400,{tag:'error',error:{code:'unknown-op',message:String(op),retryable:false}});
  });
});
s.listen(0,'127.0.0.1',()=>{fs.writeFileSync(portfile, String(s.address().port));});
")

(defn- sleep-ms! [ms]
  (.spawnSync child js/process.execPath
              #js ["-e" (str "Atomics.wait(new Int32Array(new SharedArrayBuffer(4)),0,0," ms ")")]
              #js {:timeout (+ ms 1000)}))

(defn- start-server! [mode]
  (let [portfile (.join path (.tmpdir os) (str "kotoba-storage-fixture-" (js/Date.now) ".port"))
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

(defn- tfn [origin]
  (transport/production-transport {:endpoint origin}))

(defn- resolve-endpoint-case []
  (try
    (let [ok? (= "https://kv.example.test"
                 (transport/resolve-endpoint {:endpoint "https://kv.example.test"}))
          threw? (try (transport/resolve-endpoint {}) false (catch :default _ true))]
      (check "cljs-resolve-endpoint-requires-explicit-host-configuration"
             (and ok? threw?) "resolve-endpoint checks failed"))
    (catch :default e
      (check "cljs-resolve-endpoint-requires-explicit-host-configuration" false (.-message e)))))

(defn- put-get-round-trip-case []
  (let [server (start-server! "kv")]
    (try
      (let [t (tfn (:origin server))
            put (t {:namespace :example/app :operation :put :key :profile/name
                    :value "alice" :expected-version nil})
            get (t {:namespace :example/app :operation :get :key :profile/name
                    :value nil :expected-version nil})]
        (check "cljs-put-then-get-round-trips-through-wire"
               (and (= :written (:tag put))
                    (= "alice" (:value put))
                    (= 1 (:version put))
                    (= :found (:tag get))
                    (= "alice" (:value get))
                    (= 1 (:version get)))
               (pr-str {:put put :get get})))
      (catch :default e
        (check "cljs-put-then-get-round-trips-through-wire" false (.-message e)))
      (finally (stop-server! server)))))

(defn- missing-get-case []
  (let [server (start-server! "kv")]
    (try
      (let [t (tfn (:origin server))
            get (t {:namespace :example/app :operation :get :key :absent
                    :value nil :expected-version nil})]
        (check "cljs-get-of-absent-key-is-missing"
               (= :missing (:tag get))
               (pr-str get)))
      (catch :default e
        (check "cljs-get-of-absent-key-is-missing" false (.-message e)))
      (finally (stop-server! server)))))

(defn- conflict-put-case []
  (let [server (start-server! "kv")]
    (try
      (let [t (tfn (:origin server))
            _ (t {:namespace :example/app :operation :put :key :k
                  :value "v1" :expected-version nil})
            conflict (t {:namespace :example/app :operation :put :key :k
                         :value "v2" :expected-version 99})]
        (check "cljs-version-mismatched-put-is-typed-conflict"
               (and (= :conflict (:tag conflict))
                    (= 1 (:current-version conflict)))
               (pr-str conflict)))
      (catch :default e
        (check "cljs-version-mismatched-put-is-typed-conflict" false (.-message e)))
      (finally (stop-server! server)))))

(defn- delete-case []
  (let [server (start-server! "kv")]
    (try
      (let [t (tfn (:origin server))
            _ (t {:namespace :example/app :operation :put :key :k
                  :value "v" :expected-version nil})
            del (t {:namespace :example/app :operation :delete :key :k
                    :value nil :expected-version nil})
            get (t {:namespace :example/app :operation :get :key :k
                    :value nil :expected-version nil})]
        (check "cljs-delete-then-get-shows-missing"
               (and (= :deleted (:tag del))
                    (= :missing (:tag get)))
               (pr-str {:del del :get get})))
      (catch :default e
        (check "cljs-delete-then-get-shows-missing" false (.-message e)))
      (finally (stop-server! server)))))

(defn- rate-limited-case []
  (let [server (start-server! "429")]
    (try
      (let [t (tfn (:origin server))
            reply (t {:namespace :example/app :operation :get :key :k
                      :value nil :expected-version nil})]
        (check "cljs-http-429-maps-to-retryable-typed-error"
               (and (= :error (:tag reply))
                    (= :storage/rate-limited (get-in reply [:error :code]))
                    (true? (get-in reply [:error :retryable])))
               (pr-str reply)))
      (catch :default e
        (check "cljs-http-429-maps-to-retryable-typed-error" false (.-message e)))
      (finally (stop-server! server)))))

(defn- upstream-error-case []
  (let [server (start-server! "500")]
    (try
      (let [t (tfn (:origin server))
            reply (t {:namespace :example/app :operation :get :key :k
                      :value nil :expected-version nil})]
        (check "cljs-http-500-maps-to-retryable-typed-error"
               (and (= :error (:tag reply))
                    (= :storage/upstream-error (get-in reply [:error :code]))
                    (true? (get-in reply [:error :retryable])))
               (pr-str reply)))
      (catch :default e
        (check "cljs-http-500-maps-to-retryable-typed-error" false (.-message e)))
      (finally (stop-server! server)))))

(let [results [(resolve-endpoint-case)
               (put-get-round-trip-case)
               (missing-get-case)
               (conflict-put-case)
               (delete-case)
               (rate-limited-case)
               (upstream-error-case)]
      failures (remove :ok? results)]
  (doseq [{:keys [name ok? detail]} results]
    (println (if ok? "PASS" "FAIL") name (or detail "")))
  (println (count results) "cases," (count failures) "failed")
  (when (seq failures) (.exit process 1)))
