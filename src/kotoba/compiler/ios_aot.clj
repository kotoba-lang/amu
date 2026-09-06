(ns kotoba.compiler.ios-aot
  (:require [kotoba.artifact.core :as artifact]
            [kotoba.object.macho64 :as macho]
            [kotoba.verifier :as verifier])
  (:import [java.nio.charset StandardCharsets]))

(def ^:private ios-target :aarch64-ios-kotoba-v1)

(defn- reject! [message data]
  (throw (ex-info message (merge {:phase :verify} data))))

(def ^:private platforms #{:ios :ios-simulator})
(def ^:private minimum-os [15 0 0])

(defn package
  "Verify an iOS KEXE and return a canonical static Mach-O object plus manifest."
  ([kexe entry] (package kexe entry {:platform :ios}))
  ([kexe entry {:keys [platform] :or {platform :ios}}]
   (verifier/verify-artifact! kexe)
   (when-not (= ios-target (:target kexe))
     (reject! "iOS AOT packaging requires the explicit iOS target"
              {:target (:target kexe)}))
   (when-not (symbol? entry)
     (reject! "iOS AOT entry must be a symbol" {:entry entry}))
   (when-not (contains? platforms platform)
     (reject! "iOS AOT platform is unsupported" {:platform platform}))
   (let [export (get (:exports kexe) entry)]
     (when-not export
       (reject! "iOS AOT entry is not exported" {:entry entry}))
     (let [code (:code kexe)
           offset (:offset export)
           target-profile (.getBytes "aarch64-ios-kotoba-v1" StandardCharsets/US_ASCII)
           object-vector (macho/encode-object
                          {:machine :aarch64
                           :platform platform
                           :minimum-os minimum-os
                           :sections [{:segment "__TEXT" :name "__text" :align 2
                                       :flags 0x80000000 :bytes code}
                                      {:segment "__TEXT" :name "__const" :align 0
                                       :flags 0
                                       :bytes (conj (mapv #(bit-and (int %) 0xff)
                                                          target-profile)
                                                    0)}]
                           :symbols [{:name "_kotoba_ios_code_start" :section 1
                                      :value 0 :external? true :description 0x20}
                                     {:name "_kotoba_ios_code_end" :section 1
                                      :value (count code) :external? true
                                      :description 0x20}
                                     {:name "_kotoba_ios_entry" :section 1
                                      :value offset :external? true :description 0x20}
                                     {:name "_kotoba_ios_target_profile" :section 2
                                      :value 0 :external? true :description 0x20}]})
           object (byte-array (map unchecked-byte object-vector))
           manifest {:format :kotoba.ios-aot/v2
                     :target ios-target
                     :platform platform
                     :minimum-os minimum-os
                     :target-profile (:target-profile kexe)
                     :artifact-sha256 (:sha256 kexe)
                     :code-sha256 (artifact/sha256 code)
                     :entry {:name entry :offset offset :arity (:arity export)}
                     :object-sha256 (artifact/sha256 object-vector)}]
       {:object object :manifest manifest}))))
