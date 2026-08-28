(ns perfgate-qualify
  (:require [clojure.data.json :as json]
            [clojure.java.io :as io]
            [clojure.string :as str]
            [machine.core :as m]
            [perfgate.core :as g])
  (:import [java.nio.charset StandardCharsets]
           [java.security MessageDigest]
           [java.time Duration Instant]))

(defn sysctl [name]
  (try
    (let [pb (ProcessBuilder. (into-array String ["sysctl" name]))
          proc (.start pb)]
      (when (zero? (.waitFor proc))
        (second (str/split (str/trim (slurp (.getInputStream proc))) #":\s+" 2))))
    (catch Exception _ nil)))

(defn measured-machine []
  (let [brand (or (sysctl "machdep.cpu.brand_string") "unknown-cpu")
        cores (or (some-> (sysctl "hw.logicalcpu") parse-long)
                  (.availableProcessors (Runtime/getRuntime)))
        line (or (some-> (sysctl "hw.cachelinesize") parse-long) 64)
        l1 (or (some-> (sysctl "hw.l1dcachesize") parse-long) 32768)
        l2 (or (some-> (sysctl "hw.l2cachesize") parse-long) 262144)]
    (m/measured
     {:format m/format-id
      :machine/id (str "darwin-" (str/replace (str/lower-case brand) #"[^a-z0-9]+" "-"))
      :cpu {:arch (if (= "arm64" (System/getProperty "os.arch")) :aarch64 :x86-64)
            :cores cores
            :cache [{:level 1 :kind :data :bytes l1 :line-bytes line :shared-by 1}
                    {:level 2 :kind :unified :bytes l2 :line-bytes line :shared-by 1}]}
      :page {:base-bytes (or (some-> (sysctl "hw.pagesize") parse-long) 4096) :huge []}
      :numa {:nodes 1 :distance [[10]]}}
     (str "sysctl darwin host probe on "
          (.. java.net.InetAddress getLocalHost getHostName)))))

(defn observation-on [machine id plan-id metric unit samples source lower-is-better?]
  (g/observation {:id id
                  :plan-id plan-id
                  :machine machine
                  :metric metric
                  :unit unit
                  :samples (vec samples)
                  :source source
                  :lower-is-better? lower-is-better?}))

(defn observation [id plan-id metric unit samples source]
  (observation-on (measured-machine) id plan-id metric unit samples source true))

(defn host-load-qualified? [report]
  (let [host (or (:hostLoadQualified (:environment report))
                 (get-in report [:qualification :hostLoad :qualified]))]
    (boolean host)))

(defn performance-verdict [report]
  (or (get-in report [:qualification :performance :verdict])
      (when-not (host-load-qualified? report) "unqualified-host-load")
      "deferred-quiet-host-rerun"))

(defn json-keyword [value]
  (if-let [ns (namespace value)]
    (str ns "/" (name value))
    (name value)))

(def manifest-path "bench/runtime-comparison/multidomain-suite.json")
(def sha256-pattern #"[0-9a-f]{64}")

(defn sha256-bytes [bytes]
  (let [digest (.digest (MessageDigest/getInstance "SHA-256") bytes)]
    (apply str (map #(format "%02x" (bit-and (int %) 0xff)) digest))))

(defn sha256-string [s]
  (sha256-bytes (.getBytes s StandardCharsets/UTF_8)))

(defn require! [pred message data]
  (when-not pred
    (throw (ex-info message (merge {:phase :bounded-fastest/validation} data)))))

(defn unique? [xs] (= (count xs) (count (set xs))))

(defn canonical-manifest []
  (let [bytes (java.nio.file.Files/readAllBytes (.toPath (io/file manifest-path)))]
    {:bytes bytes
     :sha256 (sha256-bytes bytes)
     :value (json/read-str (String. bytes StandardCharsets/UTF_8) :key-fn keyword)}))

(defn target-without-id [target]
  (select-keys target [:os :architecture :isa :execution]))

(defn recorded-machine [domain]
  (let [{:keys [platform architecture cpu logicalCpus]} (:environment domain)
        isa (get {"arm64" :aarch64 "x64" :x86-64} architecture)]
    (require! (and (seq platform) (seq architecture) (seq cpu)
                   (pos-int? logicalCpus) isa)
              "recorded machine/ISA is incomplete" {:domain (:id domain)})
    (m/measured {:format m/format-id
                 :machine/id (str platform "-" architecture "-"
                                  (str/replace (str/lower-case cpu) #"[^a-z0-9]+" "-")
                                  "-" logicalCpus)
                 :cpu {:arch isa :cores logicalCpus}}
                (str "recorded benchmark environment for " (:id domain)))))

(defn parse-instant [value label]
  (try
    (Instant/parse value)
    (catch Exception _
      (throw (ex-info (str label " is not an ISO-8601 instant")
                      {:phase :bounded-fastest/validation :value value})))))

(defn validate-multidomain! [report manifest manifest-sha]
  (let [claim (:claimContract manifest)
        required-domain-ids (mapv :id (:requiredDomains manifest))
        report-domain-ids (mapv :id (:domains report))
        required-comparators (:requiredComparators manifest)
        required-engines (:requiredEngines manifest)
        required-targets (:requiredTargets manifest)
        mode (get-in report [:contract :mode])]
    (require! (= "amu.bounded-fastest-claim-contract/v1" (:format claim))
              "claim contract format is unsupported" {})
    (require! (and (string? (:asOf claim))
                   (re-matches #"\d{4}-\d{2}-\d{2}" (:asOf claim)))
              "claim contract needs an explicit date" {})
    (require! (and (str/includes? (:allowedSentence claim) "fastest among the enumerated universe")
                   (not (str/includes? (str/lower-case (:allowedSentence claim)) "world fastest"))
                   (false? (:worldFastestClaimQualified claim)))
              "claim wording exceeds the bounded enumerated universe" {})
    (require! (= "kotoba.perfgate.policy/default-v1" (:perfgatePolicyId claim))
              "claim contract names an unsupported perfgate policy" {})
    (doseq [[label values] [[:required-domains required-domain-ids]
                            [:required-engines required-engines]
                            [:required-comparators required-comparators]
                            [:required-targets (mapv :id required-targets)]]]
      (require! (and (seq values) (unique? values))
                "manifest requirement IDs must be non-empty and unique" {:set label :ids values}))
    (require! (= (:id manifest) (:suite report)) "report suite does not identify the manifest" {})
    (require! (= manifest-sha (get-in report [:manifest :sha256]))
              "report manifest identity is stale or fabricated" {})
    (require! (= manifest-path (get-in report [:manifest :path]))
              "report manifest path drifted" {})
    (require! (= claim (get-in report [:contract :claimContract]))
              "report claim contract differs from the identified manifest" {})
    (require! (= required-engines (get-in report [:contract :requiredEngines]))
              "report required engine set drifted" {})
    (require! (= required-comparators (get-in report [:contract :requiredComparators]))
              "report required comparator set drifted" {})
    (require! (= required-targets (get-in report [:contract :requiredTargets]))
              "report required target set drifted" {})
    (require! (unique? report-domain-ids) "report contains duplicate domain IDs"
              {:ids report-domain-ids})
    (require! (= required-domain-ids report-domain-ids)
              "report domain set is not the exact manifest domain set"
              {:required required-domain-ids :actual report-domain-ids})
    (require! (contains? #{"core" "competitive"} mode)
              "report mode is not core or competitive" {:mode mode})
    (require! (= (set required-comparators) (set (map name (keys (:externalComparators report)))))
              "report comparator registry is not exact" {})
    (doseq [[required domain] (map vector (:requiredDomains manifest) (:domains report))]
      (require! (= [(:id required) (:fixture required) (:knownAnswer required)]
                   [(:id domain) (:fixture domain) (get-in domain [:knownAnswer :benchmark])])
                "domain benchmark identity drifted" {:domain (:id required)})
      (require! (every? #(get-in domain [:engines (keyword %)]) required-engines)
                "required target engine is missing" {:domain (:id required)})
      (require! (get-in domain [:engines :amu-wasm32])
                "core semantic baseline is missing" {:domain (:id required)})
      (require! (= "all-engine-pairs ABBA/BAAB per run" (get-in domain [:contract :rotation]))
                "domain rotation policy drifted" {:domain (:id required)})
      (require! (every? #(contains? (set (get-in domain [:knownAnswer :verifiedBy])) %)
                        (concat required-engines (when (= "competitive" mode)
                                                   required-comparators)))
                "known answer was not verified by every claim arm" {:domain (:id required)})
      (doseq [engine (concat required-engines (when (= "competitive" mode)
                                                required-comparators))
              :let [samples (get-in domain [:engines (keyword engine) :samples])]]
        (require! (and (seq samples)
                       (every? #(= (get-in domain [:knownAnswer :result]) (:result %)) samples))
                  "claim arm failed its recorded known answer"
                  {:domain (:id required) :engine engine}))
      (doseq [artifact-key (concat [:amuNativeKexe :amuNativeCode :amuNativeProvenance]
                                   (when (= "competitive" mode) [:rust :rustSource]))]
        (require! (boolean (re-matches sha256-pattern
                                       (or (get-in domain [:artifacts artifact-key :sha256]) "")))
                  "claim artifact input is not sealed by SHA-256"
                  {:domain (:id required) :artifact artifact-key}))
      (require! (false? (get-in domain [:environment :preparedBundle :buildPhaseEnteredDuringMeasure]))
                "measurement entered the build phase" {:domain (:id required)})
      (when (= "competitive" mode)
        (require! (every? #(get-in domain [:engines (keyword %)]) required-comparators)
                  "required comparator is missing" {:domain (:id required)})
        (require! (= "rustc --edition 2021 -C opt-level=3 -C codegen-units=1 -C strip=symbols"
                     (get-in domain [:contract :rustOptimization]))
                  "Rust optimization policy drifted" {:domain (:id required)}))
      (let [target (target-without-id (:target domain))
            environment (:environment domain)
            expected {:os (:platform environment)
                      :architecture (:architecture environment)
                      :isa (get {"arm64" "aarch64" "x64" "x86-64"}
                                (:architecture environment))
                      :execution "native"}]
        (require! (and (every? #(seq (str (get target %)))
                                [:os :architecture :isa :execution])
                       (= expected target))
                  "recorded target is missing or disagrees with its machine/ISA"
                  {:domain (:id required) :target target :expected expected})))
    (let [machines (mapv #(select-keys (:environment %)
                                      [:platform :architecture :cpu :logicalCpus])
                         (:domains report))]
      (require! (= 1 (count (set machines)))
                "domains were recorded on different machines/ISAs" {:machines machines}))
    {:claim claim :mode mode :required-domain-ids required-domain-ids
     :required-comparators required-comparators :required-targets required-targets}))

(defn evidence-state [report claim]
  (let [generated (parse-instant (:generatedAt report) "generatedAt")
        now (Instant/now)
        max-age (Duration/ofHours (:evidenceMaxAgeHours claim))
        prepared (mapv #(parse-instant (get-in % [:environment :preparedBundle :preparedAt])
                                      (str (:id %) " preparedAt"))
                       (:domains report))
        fresh? (and (not (.isAfter generated (.plusSeconds now 300)))
                    (not (.isBefore generated (.minus now max-age)))
                    (every? #(and (not (.isAfter % generated))
                                  (not (.isBefore % (.minus generated max-age)))) prepared))
        commits (mapv #(get-in % [:environment :compilerCommit]) (:domains report))
        clean? (and (every? #(false? (get-in % [:environment :compilerDirty])) (:domains report))
                    (= 1 (count (set commits)))
                    (every? #(boolean (re-matches #"[0-9a-f]{40}" (or % ""))) commits))]
    {:fresh? fresh? :clean? clean? :compiler-commit (when (= 1 (count (set commits)))
                                                       (first commits))
     :generated-at (:generatedAt report)}))

(defn qualify-arm [label report-key metric-key metric unit plan-id source report]
  (let [baseline-samples (mapv metric-key (get-in report [report-key :baseline :samples]))
        candidate-samples (mapv metric-key (get-in report [report-key :candidate :samples]))
        baseline (observation (keyword (name label) "baseline") plan-id metric unit baseline-samples source)
        candidate (observation (keyword (name label) "candidate") plan-id metric unit candidate-samples source)
        raw-verdict (g/qualify candidate baseline)
        verdict (if (host-load-qualified? report)
                  raw-verdict
                  (assoc raw-verdict
                         :qualified? false
                         :verdict :unqualified-host-load
                         :reason "host load exceeds logical CPU count"))]
    {:label label
     :metric metric
     :unit unit
     :baseline (:observation/summary baseline)
     :candidate (:observation/summary candidate)
     :verdict verdict}))

(defn qualify-domain [report domain manifest-sha]
  (let [id (:id domain)
        plan-id (keyword "runtime-multidomain" id)
        machine (recorded-machine domain)
        source (str "scripts/runtime-multidomain-suite.mjs domain=" id
                    " manifest-sha256=" manifest-sha)
        samples (fn [engine]
                  (mapv :nanosecondsPerKernel
                        (get-in domain [:engines engine :samples])))
        baseline (observation-on machine :wasm-baseline plan-id :steady-state-runtime
                                 :nanoseconds-per-kernel (samples :amu-wasm32) source true)
        candidate (observation-on machine :native-candidate plan-id :steady-state-runtime
                                  :nanoseconds-per-kernel (samples :amu-native) source true)
        raw (g/qualify candidate baseline)
        qualified-host? (and (boolean (get-in report [:qualification :hostLoadQualified]))
                             (boolean (get-in domain [:qualification :hostLoad :qualified])))
        verdict (if qualified-host?
                  raw
                  (assoc raw :qualified? false :verdict :unqualified-host-load
                         :reason "multidomain host-load gate failed"))]
    {:id id
     :fixture (:fixture domain)
     :plan-id plan-id
     :machine-id (:machine/id machine)
     :machine-fingerprint (m/fingerprint machine)
     :unit :nanoseconds-per-kernel
     :direction :lower-is-better
     :policy-id (get-in raw [:policy :policy/id])
     :baseline (:observation/summary baseline)
     :candidate (:observation/summary candidate)
     :verdict verdict}))

(defn qualify-rust-domain [report domain claim manifest-sha target-id]
  (when (get-in domain [:engines :rust])
    (let [id (:id domain)
          plan-id (keyword (:id claim) (str target-id "." id))
          machine (recorded-machine domain)
          source (str "scripts/runtime-multidomain-suite.mjs comparator=rust domain=" id)
          samples (fn [engine]
                    (mapv :nanosecondsPerKernel
                          (get-in domain [:engines engine :samples])))
          baseline (observation-on machine :rust-baseline plan-id
                                   (keyword (:metric claim)) (keyword (:unit claim))
                                   (samples :rust) (str source " manifest-sha256=" manifest-sha)
                                   (= "lower-is-better" (:direction claim)))
          candidate (observation-on machine :amu-native-candidate plan-id
                                    (keyword (:metric claim)) (keyword (:unit claim))
                                    (samples :amu-native) (str source " manifest-sha256=" manifest-sha)
                                    (= "lower-is-better" (:direction claim)))
          raw (g/qualify candidate baseline)
          qualified-host? (and (boolean (get-in report [:qualification :hostLoadQualified]))
                               (boolean (get-in domain [:qualification :hostLoad :qualified])))
          verdict (if qualified-host?
                    raw
                    (assoc raw :qualified? false :verdict :unqualified-host-load
                           :reason "multidomain host-load gate failed"))]
      {:id id
       :fixture (:fixture domain)
       :plan-id plan-id
       :machine-id (:machine/id machine)
       :machine-fingerprint (m/fingerprint machine)
       :unit (keyword (:unit claim))
       :direction (keyword (:direction claim))
       :policy-id (get-in raw [:policy :policy/id])
       :baseline (:observation/summary baseline)
       :candidate (:observation/summary candidate)
       :verdict verdict
       :claim (when (:qualified? verdict) (g/claim verdict candidate baseline))})))

(defn qualify-multidomain [report]
  (let [{:keys [sha256 value]} (canonical-manifest)
        {:keys [claim mode required-targets]} (validate-multidomain! report value sha256)
        target-id (:id (first required-targets))
        target-set-complete? (= (set (map target-without-id required-targets))
                                (set (map (comp target-without-id :target) (:domains report))))
        state (evidence-state report claim)
        domains (mapv #(qualify-domain report % sha256) (:domains report))
        rust-domains (if (= "competitive" mode)
                       (mapv #(qualify-rust-domain report % claim sha256 target-id)
                             (:domains report))
                       [])
        host? (and (boolean (get-in report [:qualification :hostLoadQualified]))
                   (every? #(get-in % [:qualification :hostLoad :qualified]) (:domains report)))
        complete? (= (mapv :id (:requiredDomains value)) (mapv :id (:domains report)))
        rust-complete? (and (= "competitive" mode)
                            (= (count rust-domains) (count (:requiredDomains value))))
        rust-qualified? (and host? complete? rust-complete? target-set-complete?
                             (:fresh? state) (:clean? state)
                             (every? #(get-in % [:verdict :qualified?]) rust-domains))
        machine (when (seq (:domains report)) (recorded-machine (first (:domains report))))
        claim-body (when rust-qualified?
                     {:format "amu.bounded-fastest-claim/v1"
                      :claim-contract claim
                      :allowed-sentence (:allowedSentence claim)
                      :manifest {:id (:id value) :sha256 sha256}
                      :target (first required-targets)
                      :machine {:id (:machine/id machine)
                                :fingerprint (m/fingerprint machine)
                                :recorded (select-keys (:environment (first (:domains report)))
                                                       [:platform :architecture :cpu :logicalCpus])}
                      :compiler-commit (:compiler-commit state)
                      :generated-at (:generated-at state)
                      :plan-ids (mapv #(json-keyword (:plan-id %)) rust-domains)
                      :metric (:metric claim)
                      :unit (:unit claim)
                      :direction (:direction claim)
                      :policy-id (:perfgatePolicyId claim)
                      :aggregation-policy (:aggregationPolicy claim)
                      :domain-claims (mapv :claim rust-domains)})
        claim-artifact (when claim-body
                         {:format "amu.content-addressed-bounded-fastest-claim/v1"
                          :content-encoding "machine.core/canonical-string-v1"
                          :sha256 (sha256-string (m/canonical-string claim-body))
                          :body claim-body})]
    {:format "amu.multidomain-perfgate-qualification/v1"
     :suite (:suite report)
     :manifest-sha256 sha256
     :claim-contract-id (:id claim)
     :host-load-qualified? host?
     :evidence-clean? (:clean? state)
     :evidence-fresh? (:fresh? state)
     :target-set-complete? target-set-complete?
     :domain-set-complete? complete?
     :domains domains
     :all-domains-perfgate-qualified?
     (and host? complete? (every? #(get-in % [:verdict :qualified?]) domains))
     :external-comparators
     {:rust {:domain-set-complete? rust-complete?
             :domains (mapv #(dissoc % :claim) rust-domains)
             :all-domains-perfgate-qualified? rust-qualified?
             :rust-comparison-qualified? rust-qualified?}}
     :rust-comparison-qualified? rust-qualified?
     :bounded-fastest-claim-qualified? rust-qualified?
     :bounded-fastest-claim claim-artifact
     ;; Six Rust twins qualify only this prespecified Amu-vs-Rust suite.  They
     ;; do not define, much less exhaust, the universe needed for "world's
     ;; fastest" or another broad superlative.
     :broad-fastest-claim-qualified? false
     :reason (cond
               rust-qualified? (:allowedSentence claim)
               (not (:clean? state)) "compiler evidence is dirty; no claim artifact emitted"
               (not (:fresh? state)) "benchmark evidence is stale; no claim artifact emitted"
               (not target-set-complete?) "recorded physical target is outside the bounded claim contract"
               rust-complete? "Rust domain set is complete but not fully qualified; no claim artifact emitted"
               :else "no external comparator covers every required domain")}))

(defn -main [& args]
  (let [input (first args)]
    (when-not (and (string? input) (seq input))
      (binding [*out* *err*]
        (println "usage: perfgate-qualify <benchmark.json>"))
      (System/exit 2))
    (let [report (json/read-str (slurp input) :key-fn keyword)]
      (if (= "kotoba.runtime-multidomain-report/v1" (:format report))
        (println (json/write-str (qualify-multidomain report)
                                :value-fn (fn [_ v] (if (keyword? v) (json-keyword v) v))))
        (let [
          fixture (:fixture report)
          target (:target report)
          plan-id (keyword "postalloc-scheduling" (str fixture "." target))
          source (str "scripts/postalloc-scheduling-benchmark.mjs --fixture " fixture
                      " --target " target)
          runtime (qualify-arm :runtime :runtime :nanosecondsPerKernel :runtime :ns plan-id source report)
          compile (when (and (:compile report)
                             (not (:error (:compile report)))
                             (get-in report [:compile :baseline :samples]))
                    (qualify-arm :compile :compile :compileWallMilliseconds :compile :ms plan-id source report))]
          (println (json/write-str
                {:format "amu.perfgate-qualification/v1"
                 :fixture fixture
                 :target target
                 :plan-id plan-id
                 :host-load-qualified? (host-load-qualified? report)
                 :performance-verdict (performance-verdict report)
                 :runtime runtime
                 :compile compile
                 :any-qualified? (and (host-load-qualified? report)
                                      (or (:qualified? (:verdict runtime))
                                          (boolean (and compile (:qualified? (:verdict compile))))))}
                    :value-fn (fn [_ v] (if (keyword? v) (json-keyword v) v)))))))))
