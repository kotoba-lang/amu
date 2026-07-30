(ns kotoba.compiler.host-profile-test
  (:require [clojure.edn :as edn]
            [clojure.string :as str]
            [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.host-profile :as host-profile]))

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
          :max-request-bytes 65536
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
    ;; Egress stays GET-only; ingress defaults include POST for app routes.
    (is (= ["GET"] (get-in profile [:http :allowed-methods])))
    (is (= ["DELETE" "GET" "HEAD" "POST" "PUT"]
           (get-in profile [:http :ingress-methods])))
    (is (= "./worker.mjs" (:main wrangler)))
    (is (= [{:binding "TOSHOKAN_BUCKET"
             :bucket_name "murakumo-toshokan"}]
           (:r2_buckets wrangler)))
    (is (= :kotoba.host-artifact/v1 (:format manifest)))
    (is (re-find #"capability-denied:http" worker-source))
    (is (re-find #"capability-denied:http-ingress" worker-source))
    (is (re-find #"ingressMethods" worker-source))
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
    (is (re-find #"maxRequestBytes" worker-source))
    (is (re-find #"handleIncoming" worker-source))
    (is (re-find #"toIncoming" worker-source))
    (is (re-find #"fromReply" worker-source))
    (is (re-find #"resource-limit:http-request-bytes" worker-source))
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
           [:request-unbounded
            (assoc-in valid-profile [:http :max-request-bytes] 999999999)]
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
