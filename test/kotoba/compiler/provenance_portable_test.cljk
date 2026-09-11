(ns kotoba.compiler.provenance-portable-test
  "`kotoba.compiler.provenance` is `.cljc` and was reached only by `.clj`
  tests (`core-test`, `ipld-adl-source-test`), so its cljs half had never run.

  That half is not incidental. The namespace carries SIX reader conditionals,
  and every one of them is a place two hosts can answer differently about the
  same bytes: `hex` (JVM `format \"%02x\"` -- which does not exist in cljs at
  all), `raw-sha256` (`MessageDigest` vs `node:crypto`), `text-sha256` (UTF-8
  via `String/getBytes` vs `js/Buffer`), `byte-size`, the EVM
  `creation-bytes` path (`byte-array` + `unchecked-byte` vs
  `js/Buffer.from`), and `sha256-equal?` (`MessageDigest/isEqual` vs
  `crypto.timingSafeEqual`).

  A provenance descriptor is the thing a caller checks a build against, so a
  host that hashed differently would not fail loudly -- it would reject its own
  compiler's honest output, or accept one it should not.

  The hex literals below are pinned to the STANDARD, computed independently,
  not to whatever this code happens to answer. Both hosts have to agree with
  SHA-256 rather than merely with each other.

  Three of the byte vectors are chosen for the signed/unsigned boundary: 255,
  128 and 127. The JVM path goes through `unchecked-byte`, where 255 becomes
  -1, and the same class of defect was measured and fixed today in
  `kotoba.codegen.relocation` and `kototama.evm-tender`."
  (:require #?(:clj  [clojure.test :refer [deftest is testing]]
               :cljs [cljs.test :refer [deftest is testing] :include-macros true])
            [kotoba.artifact.core :as artifact]
            [kotoba.compiler.provenance :as provenance]))

(def ^:private result
  {:target :wasm32-browser-v1
   :hir {:a 1} :kir {:b 2}
   :compatibility {:c 3} :target-profile {:t 4}
   :binary {:format :wasm :bytes [0 1 2 3]}})

(deftest a-source-digest-is-sha256-of-its-utf8-bytes
  ;; The canonical SHA-256 of "abc". Pinning the standard rather than this
  ;; code's own answer is the point: `text-sha256` splits on the host.
  (is (= "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
         (:source-sha256 (provenance/descriptor "abc" {} {} result))))
  (testing "and non-ASCII source is hashed as UTF-8, not as UTF-16 or Latin-1"
    ;; SHA-256 of the three UTF-8 bytes of U+3042 (HIRAGANA LETTER A), E3 81
    ;; 82, computed independently of this code. A host that encoded the same
    ;; character as UTF-16LE would answer
    ;; 05816a1560db947d6ff798e30909816f400f14230e9a06afac8f8b213127aa21, so
    ;; this assertion separates the two encodings rather than merely checking
    ;; that the hosts agree with each other.
    (is (= "dc5a4d3d82f7e15792959dc661538ae0e541ce66494516f5c9cfd9cd3308494d"
           (:source-sha256 (provenance/descriptor "あ" {} {} result))))))

(deftest binary-bytes-are-hashed-across-the-signed-boundary
  ;; The `:binary` path on both hosts, at the byte values where a JVM
  ;; `unchecked-byte` and a JS unsigned byte disagree if anything is wrong.
  (doseq [[bytes expected]
          [[[0 1 2 3]
            "054edec1d0211f624fed0cbca9d4f9400b0e491c43742af2c5b0abebf0c990d8"]
           [[255 128 127 0]
            "db71c5ffe8b01c5fe9c9bf50e569f4e4a69d4b40bb0fb39fc60b73e3edcca64e"]
           [[222 173 190 239]
            "5f78c33274e43fa9de5659265c1d917e25c03722dcb0b8d27db8d5feaa813953"]]]
    (testing (pr-str bytes)
      (let [d (provenance/descriptor "x" {} {} (assoc result :binary {:format :wasm :bytes bytes}))]
        (is (= expected (:sha256 (:binary (:outputs d)))))
        (is (= (count bytes) (:size (:binary (:outputs d)))))))))

(deftest the-evm-creation-path-is-the-other-byte-split
  ;; A separate reader conditional from the one above, so it gets its own
  ;; boundary bytes rather than riding on that one's.
  (doseq [[bytes expected]
          [[[0 1 2 3]
            "054edec1d0211f624fed0cbca9d4f9400b0e491c43742af2c5b0abebf0c990d8"]
           [[255 128 127 0]
            "db71c5ffe8b01c5fe9c9bf50e569f4e4a69d4b40bb0fb39fc60b73e3edcca64e"]]]
    (testing (pr-str bytes)
      (let [d (provenance/descriptor "x" {} {} {:format :evm/v1 :target :evm-v1
                                                :creation-bytes bytes})
            primary (:primary (:outputs d))]
        (is (= :evm-creation-bytes (:format primary)))
        (is (= expected (:sha256 primary)))
        (is (= (count bytes) (:size primary))))))
  (testing "a result that already carries its own digest is not recomputed"
    (is (= "carried"
           (:sha256 (:primary (:outputs (provenance/descriptor
                                         "x" {} {}
                                         {:format :evm/v1 :target :evm-v1
                                          :creation-bytes [1]
                                          :creation-sha256 "carried"}))))))))

(deftest the-descriptor-is-sealed-and-verifies-against-its-own-inputs
  (let [attached (provenance/attach "abc" {:allow #{}} {} result)
        d (:provenance attached)]
    (is (= :kotoba.provenance/v1 (:format d)))
    (is (true? (artifact/valid-seal? d)))
    (is (= d (provenance/verify! "abc" {:allow #{}} {} attached)))))

(deftest verify-refuses-when-any-input-differs
  ;; Both directions, and the reason literal is pinned rather than just the
  ;; fact of a throw: a refusal for a different reason is not this one.
  (let [attached (provenance/attach "abc" {:allow #{}} {} result)
        refusal (fn [& args]
                  (try (do (apply provenance/verify! args) :verified)
                       (catch #?(:clj clojure.lang.ExceptionInfo :cljs :default) e
                         (ex-data e))))]
    (doseq [[what data]
            [["a different source"   (refusal "abd" {:allow #{}} {} attached)]
             ["a different policy"   (refusal "abc" {:allow #{:x}} {} attached)]
             ["different build data" (refusal "abc" {:allow #{}} {:k 1} attached)]
             ["a tampered digest"
              (refusal "abc" {:allow #{}} {}
                       (assoc-in attached [:provenance :source-sha256] "0"))]
             ["a missing descriptor" (refusal "abc" {:allow #{}} {}
                                              (dissoc attached :provenance))]]]
      (testing what
        (is (= :provenance (:phase data)))
        (is (= :identity-mismatch (:reason data)))))))
