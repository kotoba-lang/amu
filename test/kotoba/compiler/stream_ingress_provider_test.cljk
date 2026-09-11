(ns kotoba.compiler.stream-ingress-provider-test
  "root ADR-2608150900 — a Kotoba guest hearing and speaking on a frame stream.

  The kit and the provider are only a claim until a guest compiled from source,
  under a policy that admits exactly these two capabilities, actually reaches
  them through the reference runtime. That is what `:reference :implemented`
  means in `stream-ingress-v1.edn`, and this is the test that earns it."
  (:require [clojure.test :refer [deftest is testing]]
            [clojure.edn :as edn]
            [clojure.java.io :as io]
            [kotoba.compiler.core :as compiler]
            [kotoba.kir :as ir]
            [kotoba.compiler.reference-runtime :as runtime]
            [provider.stream-ingress :as stream]))

(def source
  (str "(ns app.stream (:export [listen speak]) "
       "(:capabilities #{:stream/accept :stream/send}))"
       "(defn listen [request " (pr-str stream/accept-request-type) "] "
       (pr-str stream/accept-result-type)
       " (typed-cap-call :stream/accept "
       (pr-str stream/accept-request-type) " "
       (pr-str stream/accept-result-type) " request))"
       "(defn speak [frame " (pr-str stream/send-request-type) "] "
       (pr-str stream/send-result-type)
       " (typed-cap-call :stream/send "
       (pr-str stream/send-request-type) " "
       (pr-str stream/send-result-type) " frame))"))

(defn- hosted [& [opts]]
  (let [kit (stream/create-provider (or opts {}))
        kir (ir/lower (:hir (compiler/check-source
                             source {:allow #{[:cap/call 25] [:cap/call 26]}})))]
    {:kit kit
     :runtime (runtime/instantiate kir {:allow #{25 26}
                                        :providers (:providers kit)})}))

(defn- hear [runtime]
  ((:invoke runtime) 'listen [[stream/accept-request-type 0]]))

;; ── the guest hears ──────────────────────────────────────────────────────────

(deftest test-a-guest-hears-open-then-frame
  (let [{:keys [kit runtime]} (hosted)
        id ((:open! kit) :media)]
    ((:deliver! kit) id "QUFB")
    (let [opened (hear runtime)
          framed (hear runtime)]
      (is (= :opened (nth (nth opened 2) 1)))
      (is (= :frame (nth (nth framed 2) 1)))
      (testing "and the payload arrives as the host sent it"
        (is (= "QUFB" (nth (nth (nth framed 2) 2) 2)))))))

(deftest test-an-empty-stream-is-none-to-the-guest
  (let [{:keys [runtime]} (hosted)]
    (is (= [stream/accept-result-type false] (hear runtime)))))

;; ── the guest speaks ─────────────────────────────────────────────────────────

(deftest test-a-guest-speaks-and-the-host-sees-it
  (let [{:keys [kit runtime]} (hosted)
        id ((:open! kit) :media)]
    (is (true? ((:invoke runtime) 'speak
                [[stream/send-request-type id "Zm9v" false]])))
    (is (= [{:stream id :payload "Zm9v" :final false}] ((:sent kit))))))

;; ── the separation is enforced at the policy, not just declared ──────────────

(deftest test-a-guest-admitted-only-to-listen-cannot-speak
  (testing "hearing a stream is not permission to speak into it"
    (let [kit (stream/create-provider)
          kir (ir/lower (:hir (compiler/check-source
                               source {:allow #{[:cap/call 25] [:cap/call 26]}})))
          ;; The runtime admits accept only. Measured: instantiate does NOT
          ;; refuse a guest whose contracts mention an unadmitted capability --
          ;; the refusal lands where the guest tries to USE it. That is
          ;; fail-closed at the point of use, which is the property that
          ;; matters; this test asserts it where it actually happens rather
          ;; than where it would have been tidier.
          runtime (runtime/instantiate kir {:allow #{25}
                                            :providers (select-keys (:providers kit) [25])})
          id ((:open! kit) :media)]
      (testing "listening still works"
        ((:deliver! kit) id "QUFB")
        (is (true? (second (hear runtime)))))
      (testing "speaking is denied"
        (is (thrown-with-msg?
             Exception #"capability denied"
             ((:invoke runtime) 'speak [[stream/send-request-type id "Zm9v" false]]))))
      (testing "and nothing was said"
        (is (empty? ((:sent kit))))))))

;; ── the kit says what the provider does ──────────────────────────────────────

(deftest test-the-kit-and-the-provider-agree
  (let [kit (edn/read-string
             (slurp (io/resource "kotoba/lang/capability-kits/stream-ingress-v1.edn")))
        by-name (into {} (map (juxt :name identity) (:capabilities kit)))]
    (is (= 25 (:id (get by-name :stream/accept))))
    (is (= 26 (:id (get by-name :stream/send))))
    (testing "types are the provider's own, not a look-alike retyped here"
      (is (= stream/accept-request-type (:request (get by-name :stream/accept))))
      (is (= stream/accept-result-type (:result (get by-name :stream/accept))))
      (is (= stream/send-request-type (:request (get by-name :stream/send))))
      (is (= stream/send-result-type (:result (get by-name :stream/send)))))
    (testing "and the declared overflow behaviour is the one implemented"
      (is (= :close-stream (get-in kit [:semantics :on-queue-overflow])))
      (is (= (get-in kit [:semantics :max-queue-depth])
             stream/default-max-queue-depth)))))
