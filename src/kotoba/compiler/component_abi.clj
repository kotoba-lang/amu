(ns kotoba.compiler.component-abi
  (:require [clojure.edn :as edn]
            [clojure.java.io :as io]
            [clojure.set :as set]))

(defn contract []
  (-> "kotoba/lang/transport-component-abi.edn" io/resource slurp edn/read-string))

(defn validate-component
  "Validate a component manifest against the canonical bounded transport ABI.
  This validates linkage authority; it does not claim that a native provider
  exists for the selected target."
  [{:keys [component/imports component/exports]}]
  (let [abi (contract)
        known-imports (set/union (set (keys (:operations abi)))
                                 (set (keys (:component-operations abi))))
        imports (set imports)
        exports (set exports)
        unknown (set/difference imports known-imports)]
    (cond-> []
      (seq unknown) (conj {:problem :unknown-component-imports :imports unknown})
      (not (every? symbol? imports)) (conj {:problem :non-symbol-import})
      (or (empty? exports) (not (every? symbol? exports)))
      (conj {:problem :invalid-component-exports})
      (some #(contains? #{'syscall 'raw-syscall 'socket-fd} %) imports)
      (conj {:problem :ambient-native-authority}))))

(defn operation [op]
  (or (get-in (contract) [:operations op])
      (get-in (contract) [:component-operations op])))

(defn validate-link-graph
  "Validates explicit consumer-import -> provider-export edges. Every imported
  high-level operation must have exactly one edge and the named provider must
  be the canonical provider for that operation."
  [{:keys [components links]}]
  (let [abi (contract)
        component-ops (:component-operations abi)
        nodes (set (keys components))
        edges-by-consumer-import (group-by (juxt :consumer :import) links)
        required (for [[id manifest] components
                       op (:component/imports manifest)
                       :when (contains? component-ops op)]
                   [id op])]
    (vec
     (concat
      (for [[consumer op] required
            :let [edges (get edges-by-consumer-import [consumer op])]
            :when (not= 1 (count edges))]
        {:problem :component-import-link-cardinality
         :consumer consumer :import op :actual (count edges)})
      (for [{:keys [consumer import provider export]} links
            :let [operation (get component-ops import)
                  provider-manifest (get components provider)]
            :when (or (not (contains? nodes consumer))
                      (not (contains? nodes provider))
                      (nil? operation)
                      (not= import export)
                      (not= (:provider operation) provider)
                      (not (some #{export} (:component/exports provider-manifest))))]
        {:problem :invalid-component-link
         :consumer consumer :import import :provider provider :export export})))))
