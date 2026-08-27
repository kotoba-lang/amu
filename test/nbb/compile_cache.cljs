(ns test.nbb.compile-cache
  (:require [kotoba.compiler.nbb.compile-cache :as cache]))

(defn ensure! [condition message]
  (when-not condition (throw (js/Error. message))))

(aset js/process.env "KOTOBA_WORKER_CACHE_ENTRIES" "2")
(aset js/process.env "KOTOBA_WORKER_CACHE_BYTES" "16")
(aset js/process.env "KOTOBA_WORKER_STAGE_CACHE_ENTRIES" "2")
(aset js/process.env "KOTOBA_WORKER_STAGE_CACHE_BYTES" "1024")

(let [store (cache/create)
      no-policy {:present? false :text ""}
      explicit-policy {:present? true :text "{}\n"}
      key-a (cache/key-for :wasm32-kotoba-v1 "source-a" no-policy)
      key-fuel (cache/key-for :wasm32-kotoba-v1 "source-a" no-policy
                              {:fuel (js/BigInt "1048576")})
      key-policy (cache/key-for :wasm32-kotoba-v1 "source-a" explicit-policy)
      key-target (cache/key-for :aarch64-kotoba-v1 "source-a" no-policy)
      key-b (cache/key-for :wasm32-kotoba-v1 "source-b" no-policy)
      key-c (cache/key-for :wasm32-kotoba-v1 "source-c" no-policy)]
  (ensure! (and (not= key-a key-policy) (not= key-a key-target)
                (not= key-a key-fuel))
           "policy, build metadata, and target must be part of the cache key")
  (cache/put! store key-a :a 4)
  (cache/put! store key-b :b 4)
  (ensure! (= :a (cache/lookup! store key-a)) "cache lookup failed")
  ;; Looking up A makes B the least-recently-used entry.
  (cache/put! store key-c :c 4)
  (ensure! (nil? (cache/lookup! store key-b)) "LRU entry was not evicted")
  (ensure! (= #{:a :c} #{(cache/lookup! store key-a) (cache/lookup! store key-c)})
           "live cache entries changed during eviction")
  ;; An entry larger than the total byte ceiling is never retained.
  (cache/put! store "oversized" :oversized 17)
  (ensure! (nil? (cache/lookup! store "oversized")) "oversized entry was retained")
  (ensure! (= 8 (:bytes (cache/stats store))) "cache byte accounting drifted")
  (ensure! (= 64 (count (cache/sha256 "integrity"))) "cache digest is not SHA-256"))

(let [store (:stages (cache/create-context))
      calls (volatile! 0)
      compute (fn [] (vswap! calls inc) {:format :test.hir/v1 :value 42})
      first-result (cache/resolve-stage! store :hir "source" compute)
      second-result (cache/resolve-stage! store :hir "source" compute)
      hir-key (cache/stage-key-for :hir "source")
      kir-key (cache/stage-key-for :kir "source")]
  (ensure! (not= hir-key kir-key) "stage identity is absent from stage cache key")
  (ensure! (= :miss (:cache first-result)) "first stage resolution was not a miss")
  (ensure! (= :hit (:cache second-result)) "second stage resolution was not a hit")
  (ensure! (= 1 @calls) "stage computation ran on a cache hit")
  (ensure! (= (:value first-result) (:value second-result))
           "stage cache changed the immutable value")
  ;; Corruption is fail-stop and the bad entry is evicted.
  (cache/put! store hir-key {:value {:corrupt true} :sha256 "bad"} 1)
  (let [rejected? (try (cache/lookup-stage! store hir-key) false
                       (catch :default _ true))]
    (ensure! rejected? "corrupt stage cache entry was accepted")
    (ensure! (nil? (cache/lookup! store hir-key))
             "corrupt stage cache entry was not evicted")))

(println "compile-cache: artifact/stage keys, integrity, LRU, and byte ceilings passed")
