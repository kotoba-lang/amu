(ns kotoba.compiler.host-profile-test
  (:require [clojure.data.json :as json]
            [clojure.string :as str]
            [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.host-profile :as host-profile])
  (:import [java.net ServerSocket URI]
           [java.net.http HttpClient HttpRequest HttpResponse$BodyHandlers]
           [java.nio.charset StandardCharsets]
           [java.nio.file Files]
           [java.nio.file.attribute FileAttribute]
           [java.time Duration]
           [java.util.concurrent TimeUnit]))

(def valid-profile
  {:format :kotoba.host-profile/v1
   :target :cloudflare/workerd
   :service "murakumo-toshokan"
   :compatibility-date "2026-07-26"
   :application {:module "./generated/application.mjs"
                 :factory "createApplication"}
   :routes [{:pattern "toshokan.murakumo.cloud" :custom-domain? true}]
   :crons ["17 4 * * *"]
   :bindings [{:binding "TOSHOKAN_BUCKET"
               :bucket-name "murakumo-toshokan"}]
   :vars {:NDL_MAX_RECORDS "20"}
   :secrets #{:TOSHOKAN_RUN_TOKEN}
   :http {:allowed-origins ["https://ndlsearch.ndl.go.jp"]
          :allowed-methods #{:get}
          :max-response-bytes 2097152
          :deadline-ms 30000}
   :object-store
   {:bindings {:TOSHOKAN_BUCKET
               {:key-prefixes ["blocks/" "ndl/" "kotobase/toshokan/"]}}
    :max-object-bytes 2097152}})

(deftest validates-and-generates-a-closed-workerd-host
  (let [{:keys [profile worker-source wrangler manifest]}
        (host-profile/generate valid-profile)]
    (is (= :cloudflare/workerd (:target profile)))
    (is (= "./worker.mjs" (:main wrangler)))
    (is (= [{:binding "TOSHOKAN_BUCKET"
             :bucket_name "murakumo-toshokan"}]
           (:r2_buckets wrangler)))
    (is (= :kotoba.host-artifact/v1 (:format manifest)))
    (is (re-find #"capability-denied:http" worker-source))
    (is (re-find #"capability-denied:object-store" worker-source))
    (is (re-find #"etagDoesNotMatch" worker-source))
    (is (re-find #"getStream" worker-source))
    (is (re-find #"putBlock" worker-source))
    (is (re-find #"boundedStream" worker-source))
    (is (re-find #"const INSTANCES = new WeakMap" worker-source))
    (is (re-find #"queue-handler-unavailable" worker-source))
    (is (re-find #"PROFILE\.secrets\.includes" worker-source))
    (is (re-find #"PROFILE\.vars" worker-source))
    (is (re-find #"allowedOrigins" worker-source))
    (is (not (re-find #"allowed-origins" worker-source)))
    (is (not (re-find #"key-prefixes" worker-source)))
    (is (not (str/includes? worker-source
                            "application(env).fetch(request, env")))))

(deftest rejects-ambient-or-unbounded-profile-input
  (doseq [[label profile]
          [[:unknown-field (assoc valid-profile :javascript "alert(1)")]
           [:module-injection
            (assoc-in valid-profile [:application :module]
                      "./app.mjs\"; globalThis.pwned=true; //")]
           [:http-origin-path
            (assoc-in valid-profile [:http :allowed-origins]
                      ["https://ndlsearch.ndl.go.jp/private"])]
           [:response-unbounded
            (assoc-in valid-profile [:http :max-response-bytes] 999999999)]
           [:undeclared-store
            (assoc-in valid-profile [:object-store :bindings]
                      {:OTHER {:key-prefixes ["data/"]}})]]]
    (testing (name label)
      (let [error (try (host-profile/validate profile)
                       nil
                       (catch clojure.lang.ExceptionInfo error error))]
        (is error)
        (is (= :host-profile (:phase (ex-data error))))))))

(deftest generation-is-deterministic
  (is (= (host-profile/generate valid-profile)
         (host-profile/generate valid-profile))))

(deftest generated-adapter-runs-in-real-workerd
  (let [{:keys [worker-source]} (host-profile/generate valid-profile)
        dir (Files/createTempDirectory
             "kotoba-workerd-host-" (make-array FileAttribute 0))
        worker (.resolve dir "worker.mjs")
        application (.resolve dir "application.mjs")
        config (.resolve dir "config.capnp")
        port (with-open [socket (ServerSocket. 0)] (.getLocalPort socket))
        application-source
        (str
         "export function createApplication(host) { return Object.freeze({\n"
         "  async fetch() {\n"
         "    let denied = false;\n"
         "    try { await host.http.fetch({url:'https://example.invalid/',method:'GET'}); }\n"
         "    catch (error) { denied = String(error.message).includes('capability-denied:http'); }\n"
         "    return new Response(JSON.stringify({denied,"
         "config:host.config.get('NDL_MAX_RECORDS'),"
         "secret:host.secret.get('TOSHOKAN_RUN_TOKEN'),"
         "ambientEnv:typeof globalThis.env}));\n"
         "  }\n"
         "}); }\n")
        config-source
        (str
         "using Workerd = import \"/workerd/workerd.capnp\";\n"
         "const config :Workerd.Config = (\n"
         "  services = [(name = \"main\", worker = (\n"
         "    compatibilityDate = \"2026-07-26\",\n"
         "    modules = [\n"
         "      (name = \"worker.mjs\", esModule = embed \"worker.mjs\"),\n"
         "      (name = \"./generated/application.mjs\", "
         "esModule = embed \"application.mjs\")\n"
         "    ]))],\n"
         "  sockets = [(name = \"http\", address = \"127.0.0.1:" port
         "\", http = (), service = \"main\")]\n"
         ");\n")
        binary (.toAbsolutePath
                (.normalize
                 (.resolve (.toPath (java.io.File. "."))
                           "node_modules/.bin/workerd")))
        process (atom nil)]
    (try
      (Files/writeString worker worker-source StandardCharsets/UTF_8
                         (make-array java.nio.file.OpenOption 0))
      (Files/writeString application application-source StandardCharsets/UTF_8
                         (make-array java.nio.file.OpenOption 0))
      (Files/writeString config config-source StandardCharsets/UTF_8
                         (make-array java.nio.file.OpenOption 0))
      (reset! process
              (.start
               (doto (ProcessBuilder.
                      (into-array String [(str binary) "serve" (str config)]))
                 (.directory (.toFile dir))
                 (.redirectErrorStream true))))
      (let [client (HttpClient/newHttpClient)
            request (-> (HttpRequest/newBuilder
                         (URI/create (str "http://127.0.0.1:" port "/")))
                        (.timeout (Duration/ofSeconds 2))
                        (.GET)
                        (.build))
            unavailable (Object.)
            response
            (loop [attempt 0]
              (when (>= attempt 80)
                (throw (ex-info "workerd did not become ready"
                                {:output
                                 (String. (.readAllBytes
                                           (.getInputStream ^Process @process))
                                          StandardCharsets/UTF_8)})))
              (if-not (.isAlive ^Process @process)
                (throw (ex-info "workerd exited before serving"
                                {:output
                                 (String. (.readAllBytes
                                           (.getInputStream ^Process @process))
                                          StandardCharsets/UTF_8)}))
                (let [response
                      (try
                        (.send client request
                               (HttpResponse$BodyHandlers/ofString))
                        (catch Exception _ unavailable))]
                  (if (identical? unavailable response)
                    (do (Thread/sleep 50)
                        (recur (inc attempt)))
                    response))))]
        (is (= 200 (.statusCode response)))
        (is (= {:denied true
                :config "20"
                :secret nil
                :ambientEnv "undefined"}
               (json/read-str (.body response) :key-fn keyword))))
      (finally
        (when-let [^Process running @process]
          (.destroy running)
          (when-not (.waitFor running 2 TimeUnit/SECONDS)
            (.destroyForcibly running)
            (.waitFor running 2 TimeUnit/SECONDS)))
        (doseq [path [config application worker]]
          (Files/deleteIfExists path))
        (Files/deleteIfExists dir)))))
