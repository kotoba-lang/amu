(ns kotoba.compiler.native-device-io-test
  (:require [clojure.edn :as edn]
            [clojure.java.io :as io]
            [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]
            [kotoba.sema :as sema]))

(def contract
  (-> "kotoba/lang/native-device-io-v1.edn" io/resource slurp edn/read-string))

(deftest contract-keeps-four-authorities-separate
  (is (= {:link-frame :link/frame
          :dma-region :dma/map
          :mmio-region :mmio/map
          :transport :net/transport}
         (:authority-boundaries contract)))
  (is (= 60 (get-in contract [:ethernet :minimum-pre-fcs-bytes])))
  (is (= [8 16 32] (get-in contract [:mmio :width-bits])))
  (is (= :trap-before-load-or-store
         (get-in contract [:memory-region :invalid-access]))))

(deftest width-specific-mmio-operations-reach-native-codegen
  (doseq [[load store] [['kernel-load-u8 'kernel-store-u8]
                        ['kernel-load-u16 'kernel-store-u16]
                        ['kernel-load-u32 'kernel-store-u32]]]
    (testing (str load " / " store)
      (let [source (str "(defn access [base length offset value] "
                        "(do (" store " base length offset value) "
                        "(" load " base length offset))) "
                        "(defn main [] 0)")
            result (compiler/compile-source source :x86_64-aiueos-kernel-v1)]
        (is (seq (:binary result)))))))

(deftest rooted-region-proof-crosses-a-common-wrapper
  (is (map? (sema/analyze
             "(defn common-load [base length offset]
                (kernel-load-u32 base length offset))
              (defn caller [base length] (common-load base length 0))
              (defn main [] 0)")))
  (is (thrown-with-msg?
       Exception #"memory base"
       (sema/analyze
        "(defn common-load [base length offset]
           (kernel-load-u32 base length offset))
         (defn caller [buffer length]
           (common-load (kernel-load-u8 buffer length 0) 512 0))
         (defn main [] 0)"))))

(deftest descriptor-publication-order-is-machine-readable
  (is (= [:write-extension :write-address :release-fence :set-owner
          :release-fence :doorbell]
         (get-in contract [:dma-publication :tx])))
  (is (= 'kernel-cpuid-eax
         (get-in contract [:dma-publication :release-fence :x86-64]))))
