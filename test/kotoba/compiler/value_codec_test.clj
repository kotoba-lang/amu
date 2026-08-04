(ns kotoba.compiler.value-codec-test
  (:require [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.value-codec :as codec]))

(deftest org-codec-is-the-only-bounded-value-wire-contract
  (is (= {:format :kotoba.value-boundary/v1
          :codec "kotoba.value.v1"
          :representation :bytes
          :limit-authority :ability-max-bytes}
         codec/wire-contract))
  (let [value {:actor/id 7 :message ["ready" true]}
        encoded (codec/encode-bounded value 256)]
    (is (= value (codec/decode-bounded encoded 256)))))

(deftest ability-byte-limit-is-checked-before-and-after-the-boundary
  (let [value {:payload (apply str (repeat 64 "x"))}
        encoded (codec/encode-bounded value 256)]
    (testing "encode cannot exceed the declared ability limit"
      (is (thrown-with-msg? clojure.lang.ExceptionInfo #"exceeds ability max-bytes"
                            (codec/encode-bounded value 8))))
    (testing "decode rejects the same payload under a narrower grant"
      (is (thrown-with-msg? clojure.lang.ExceptionInfo #"exceeds ability max-bytes"
                            (codec/decode-bounded encoded 8))))
    (testing "zero, negative, and non-integer limits fail closed"
      (doseq [limit [0 -1 1.5 nil]]
        (is (thrown-with-msg? clojure.lang.ExceptionInfo #"positive max-bytes"
                              (codec/encode-bounded value limit)))))))
