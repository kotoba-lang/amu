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
(def required-polyglot-comparators ["rust" "clang-c11" "zig" "go" "swift"])
(def bounded-fastest-v2-sentence
  "Amu native is fastest among the enumerated implementations (rustc, Apple Clang C11, Zig, Go c-shared, and Swift) on all six required domains, on one recorded Darwin arm64 machine using native execution, under the named perfgate policy.")

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

(defn validate-manifest-v2! [manifest]
  (let [claim (:claimContract manifest)
        required-domain-ids (mapv :id (:requiredDomains manifest))
        required-engines (:requiredEngines manifest)
        required-comparators (:requiredComparators manifest)
        required-targets (:requiredTargets manifest)]
    (require! (= "kotoba.runtime-multidomain-manifest/v2" (:format manifest))
              "multidomain manifest format is unsupported" {})
    (require! (= "amu.bounded-fastest-claim-contract/v2" (:format claim))
              "claim contract format is unsupported" {})
    (require! (and (string? (:asOf claim))
                   (re-matches #"\d{4}-\d{2}-\d{2}" (:asOf claim)))
              "claim contract needs an explicit date" {})
    (require! (= bounded-fastest-v2-sentence (:allowedSentence claim))
              "v2 claim wording is not the exact bounded sentence" {})
    (require! (= "amu-native" (:candidate claim))
              "v2 candidate is not amu-native" {})
    (require! (= "steady-state-runtime" (:metric claim))
              "v2 metric is unsupported" {})
    (require! (= "nanoseconds-per-kernel" (:unit claim))
              "v2 unit is unsupported" {})
    (require! (= "lower-is-better" (:direction claim))
              "v2 direction is unsupported" {})
    (require! (= "kotoba.perfgate.policy/default-v1" (:perfgatePolicyId claim))
              "claim contract names an unsupported perfgate policy" {})
    (require! (= "kotoba.native-artifact-i64x8-to-i64-indirect/v1"
                 (:nativeArtifactAbi claim))
              "claim contract does not require the common native artifact ABI" {})
    (require! (= ["input" "zero" "zero" "zero" "zero"
                  "x86_64-context-or-zero" "zero" "aarch64-context-or-zero"]
                 (:nativeArtifactArgMap claim))
              "claim contract native artifact argument map drifted" {})
    (require! (= "cc -std=c11 -O3 -Wall -Wextra -Werror" (:nativeRunnerCompiler claim))
              "claim contract native runner compiler drifted" {})
    (require! (and (pos-int? (:evidenceMaxAgeHours claim))
                   (false? (:worldFastestClaimQualified claim)))
              "v2 freshness/world-fastest boundary is invalid" {})
    (require! (= ["amu-native"] required-engines)
              "v2 requiredEngines must be exactly [amu-native]"
              {:actual required-engines})
    (require! (= required-polyglot-comparators required-comparators)
              "v2 requiredComparators must be the exact enumerated polyglot set"
              {:actual required-comparators})
    (require! (= [{:id "darwin-arm64-native"
                   :os "darwin" :architecture "arm64"
                   :isa "aarch64" :execution "native"}]
                 required-targets)
              "v2 requiredTargets must contain exactly the Darwin arm64 native profile"
              {:actual required-targets})
    (require! (and (seq required-domain-ids) (unique? required-domain-ids))
              "manifest requirement IDs must be non-empty and unique"
              {:set :required-domains :ids required-domain-ids})
    manifest))

(defn validate-multidomain! [report manifest manifest-sha]
  (validate-manifest-v2! manifest)
  (let [claim (:claimContract manifest)
        required-domain-ids (mapv :id (:requiredDomains manifest))
        report-domain-ids (mapv :id (:domains report))
        required-comparators (:requiredComparators manifest)
        required-engines (:requiredEngines manifest)
        required-targets (:requiredTargets manifest)
        mode (get-in report [:contract :mode])]
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
    (require! (boolean (re-matches sha256-pattern
                                   (or (get-in report [:contract :preparedIndexSha256]) "")))
              "root prepared bundle index is not sealed by SHA-256" {})
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
      (require! (= (:nativeArtifactAbi claim) (get-in domain [:contract :nativeArtifactAbi]))
                "domain did not use the claim contract's common native artifact ABI"
                {:domain (:id required)})
      (require! (= (:nativeArtifactArgMap claim) (get-in domain [:contract :nativeArtifactArgMap]))
                "domain native artifact argument map drifted" {:domain (:id required)})
      (require! (= (:nativeRunnerCompiler claim) (get-in domain [:contract :nativeRunnerCompiler]))
                "domain native runner compiler drifted" {:domain (:id required)})
      (require! (= "aarch64" (get-in domain [:contract :nativeArtifactTarget]))
                "bounded v2 evidence did not execute the aarch64 artifact ABI"
                {:domain (:id required)})
      (require! (boolean (re-matches sha256-pattern
                                     (or (get-in domain [:contract :preparedBundleSha256]) "")))
                "child prepared bundle is not sealed by SHA-256" {:domain (:id required)})
      (let [vectors (get-in domain [:contract :semanticVectors])
            claim-arms (concat required-engines (when (= "competitive" mode)
                                                  required-comparators))]
        (require! (= (:verificationInputs required) (mapv :input vectors))
                  "domain semantic vector corpus drifted" {:domain (:id required)})
        (require! (= (:verificationResults required) (mapv :expectedResult vectors))
                  "domain semantic vector expected results drifted" {:domain (:id required)})
        (require! (> (count (set (map :expectedResult vectors))) 1)
                  "domain semantic vectors do not reject a constant-return artifact"
                  {:domain (:id required)})
        (doseq [[vector amu-fuel] (map vector vectors (:verificationAmuFuelConsumed required))]
          (require! (every? #(contains? (set (:verifiedBy vector)) %) claim-arms)
                    "semantic vector was not verified by every claim arm"
                    {:domain (:id required) :input (:input vector)})
          (doseq [engine claim-arms
                  :let [sample (get-in vector [:arms (keyword engine)])]]
            (require! (and (= (:expectedResult vector) (:result sample))
                           (= (:nativeArtifactAbi claim) (:nativeArtifactAbi sample))
                           (= (if (= engine "amu-native") "raw" "dylib") (:artifactKind sample))
                           (= (if (= engine "amu-native") amu-fuel 0)
                              (:contextFuelConsumed sample)))
                      "semantic vector did not cross the common runner correctly"
                      {:domain (:id required) :input (:input vector) :engine engine}))))
      (doseq [engine (concat required-engines (when (= "competitive" mode)
                                                required-comparators))
              sample (get-in domain [:engines (keyword engine) :samples])]
        (require! (= (:nativeArtifactAbi claim) (:nativeArtifactAbi sample))
                  "claim arm sample did not cross the common native artifact ABI"
                  {:domain (:id required) :engine engine})
        (require! (= (if (= engine "amu-native") "raw" "dylib") (:artifactKind sample))
                  "claim arm artifact kind did not use the common runner"
                  {:domain (:id required) :engine engine})
        (let [before (:contextFuelBefore sample)
              after (:contextFuelAfter sample)
              consumed (:contextFuelConsumed sample)
              n (get-in domain [:knownAnswer :n])
              expected-amu-fuel (:contextFuelConsumed
                                 (get-in (first (filter #(= n (:input %))
                                                       (get-in domain [:contract :semanticVectors])))
                                         [:arms :amu-native]))]
          (require! (and (= before (get-in domain [:contract :fuelPerInstance]))
                         (nat-int? after) (<= after before)
                         (= consumed (- before after))
                         (= consumed (if (= engine "amu-native") expected-amu-fuel 0)))
                    "claim arm omitted common-runner context fuel evidence"
                    {:domain (:id required) :engine engine})))
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
      (doseq [artifact-key (concat [:amuNativeKexe :amuNativeCode :amuNativeProvenance
                                    :nativeBenchmarkRunner :nativeBenchmarkRunnerSource]
                                   (when (= "competitive" mode)
                                     (concat
                                      (mapcat (fn [name]
                                                [(keyword name) (keyword (str name "Source"))])
                                              required-comparators)
                                      [:swiftHelper :swiftHelperSource])))]
        (require! (boolean (re-matches sha256-pattern
                                       (or (get-in domain [:artifacts artifact-key :sha256]) "")))
                  "claim artifact input is not sealed by SHA-256"
                  {:domain (:id required) :artifact artifact-key}))
      (require! (false? (get-in domain [:environment :preparedBundle :buildPhaseEnteredDuringMeasure]))
                "measurement entered the build phase" {:domain (:id required)})
      (require! (and (string? (get-in domain [:environment :cc]))
                     (seq (get-in domain [:environment :cc])))
                "native runner compiler version receipt is missing" {:domain (:id required)})
      (when (= "competitive" mode)
        (require! (every? #(get-in domain [:engines (keyword %)]) required-comparators)
                  "required comparator is missing" {:domain (:id required)})
        (require! (= (set required-comparators)
                     (set (map name (keys (get-in domain [:contract :comparatorBuilds])))))
                  "comparator build contract is not exact" {:domain (:id required)})
        (require! (= "rustc --edition 2021 --crate-type cdylib -C opt-level=3 -C codegen-units=1 -C strip=symbols"
                     (get-in domain [:contract :rustOptimization]))
                  "Rust optimization policy drifted" {:domain (:id required)})
        (require! (and (string? (get-in domain [:environment :rustcVerbose]))
                       (re-find #"(?m)^host: .+$" (get-in domain [:environment :rustcVerbose])))
                  "Rust verbose toolchain/target receipt is missing" {:domain (:id required)}))
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
                         (:domains report))
          runner-shas (set (map #(get-in % [:artifacts :nativeBenchmarkRunner :sha256])
                                (:domains report)))
          runner-source-shas (set (map #(get-in % [:artifacts :nativeBenchmarkRunnerSource :sha256])
                                       (:domains report)))
          cc-versions (set (map #(get-in % [:environment :cc]) (:domains report)))
          comparator-receipts
          (into {} (for [name required-comparators]
                     [name (set (map #(get-in % [:environment (keyword (if (= name "rust")
                                                                       "rustcVerbose" name))])
                                         (:domains report))) ]))]
      (require! (= 1 (count (set machines)))
                "domains were recorded on different machines/ISAs" {:machines machines})
      (require! (and (= 1 (count runner-shas)) (= 1 (count runner-source-shas))
                     (= 1 (count cc-versions)))
                "domains did not share one sealed native runner/toolchain"
                {:runner-shas runner-shas :runner-source-shas runner-source-shas})
      (when (= "competitive" mode)
        (doseq [[name receipts] comparator-receipts]
          (require! (and (= 1 (count receipts)) (string? (first receipts)) (seq (first receipts)))
                    "comparator toolchain receipt changed or is missing inside one suite"
                    {:comparator name}))))
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

(defn qualify-comparator-domain [report domain comparator claim manifest-sha target-id]
  (let [comparator-key (keyword comparator)]
   (when (get-in domain [:engines comparator-key])
    (let [id (:id domain)
          plan-id (keyword (:id claim) (str target-id "." comparator "." id))
          machine (recorded-machine domain)
          source (str "scripts/runtime-multidomain-suite.mjs comparator=" comparator " domain=" id)
          samples (fn [engine]
                    (mapv :nanosecondsPerKernel
                          (get-in domain [:engines engine :samples])))
          baseline (observation-on machine (keyword comparator "baseline") plan-id
                                   (keyword (:metric claim)) (keyword (:unit claim))
                                   (samples comparator-key) (str source " manifest-sha256=" manifest-sha)
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
       :comparator comparator
       :claim (when (:qualified? verdict) (g/claim verdict candidate baseline))}))))

(defn qualify-multidomain [report]
  (let [{:keys [sha256 value]} (canonical-manifest)
        {:keys [claim mode required-targets]} (validate-multidomain! report value sha256)
        target-id (:id (first required-targets))
        target-set-complete? (= (set (map target-without-id required-targets))
                                (set (map (comp target-without-id :target) (:domains report))))
        state (evidence-state report claim)
        domains (mapv #(qualify-domain report % sha256) (:domains report))
        comparator-domains (if (= "competitive" mode)
                             (into {} (for [comparator (:requiredComparators value)]
                                        [comparator
                                         (mapv #(qualify-comparator-domain
                                                 report % comparator claim sha256 target-id)
                                               (:domains report))]))
                             {})
        host? (and (boolean (get-in report [:qualification :hostLoadQualified]))
                   (every? #(get-in % [:qualification :hostLoad :qualified]) (:domains report)))
        complete? (= (mapv :id (:requiredDomains value)) (mapv :id (:domains report)))
        comparator-complete?
        (into {} (for [[name results] comparator-domains]
                   [name (= (count results) (count (:requiredDomains value)))]))
        comparator-qualified?
        (into {} (for [[name results] comparator-domains]
                   [name (and host? complete? (get comparator-complete? name)
                              target-set-complete? (:fresh? state) (:clean? state)
                              (every? #(get-in % [:verdict :qualified?]) results))]))
        comparator-set-qualified? (and (= "competitive" mode)
                                       (= (set (keys comparator-qualified?))
                                          (set (:requiredComparators value)))
                                       (every? true? (vals comparator-qualified?)))
        machine (when (seq (:domains report)) (recorded-machine (first (:domains report))))
        evidence-report-sha256 (sha256-string (m/canonical-string report))
        all-comparator-domains (vec (mapcat second comparator-domains))
        claim-body (when comparator-set-qualified?
                     {:format "amu.bounded-fastest-claim/v2"
                      :claim-contract claim
                      :allowed-sentence (:allowedSentence claim)
                      :manifest {:id (:id value) :sha256 sha256}
                      :evidence-report {:format (:format report)
                                        :suite (:suite report)
                                        :sha256 evidence-report-sha256}
                      :target (first required-targets)
                      :machine {:id (:machine/id machine)
                                :fingerprint (m/fingerprint machine)
                                :recorded (select-keys (:environment (first (:domains report)))
                                                       [:platform :architecture :cpu :logicalCpus])}
                      :compiler-commit (:compiler-commit state)
                      :generated-at (:generated-at state)
                      :comparators (:requiredComparators value)
                      :plan-ids (mapv #(json-keyword (:plan-id %)) all-comparator-domains)
                      :metric (:metric claim)
                      :unit (:unit claim)
                      :direction (:direction claim)
                      :policy-id (:perfgatePolicyId claim)
                      :aggregation-policy (:aggregationPolicy claim)
                      :domain-claims (mapv :claim all-comparator-domains)})
        claim-artifact (when claim-body
                         {:format "amu.content-addressed-bounded-fastest-claim/v2"
                          :content-encoding "machine.core/canonical-string-v1"
                          :sha256 (sha256-string (m/canonical-string claim-body))
                          :body claim-body})]
    {:format "amu.multidomain-perfgate-qualification/v2"
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
     (into {} (for [[name results] comparator-domains]
                [(keyword name) {:domain-set-complete? (get comparator-complete? name)
                                 :domains (mapv #(dissoc % :claim) results)
                                 :all-domains-perfgate-qualified? (get comparator-qualified? name)}]))
     :comparator-set-qualified? comparator-set-qualified?
     :bounded-fastest-claim-qualified? comparator-set-qualified?
     :bounded-fastest-claim claim-artifact
     ;; This exact five-comparator set is still an enumerated implementation
     ;; universe, not an exhaustive proof about every language implementation.
     :broad-fastest-claim-qualified? false
     :reason (cond
               comparator-set-qualified? (:allowedSentence claim)
               (not (:clean? state)) "compiler evidence is dirty; no claim artifact emitted"
               (not (:fresh? state)) "benchmark evidence is stale; no claim artifact emitted"
               (not target-set-complete?) "recorded physical target is outside the bounded claim contract"
               (and (= "competitive" mode)
                    (every? true? (vals comparator-complete?)))
               "all comparator domain sets are complete but not fully qualified; no claim artifact emitted"
               :else "the required comparator set does not cover every required domain")}))

(defn -main [& args]
  (let [input (first args)]
    (when-not (and (string? input) (seq input))
      (binding [*out* *err*]
        (println "usage: perfgate-qualify <benchmark.json> | --validate-manifest-v2 <manifest.json>"))
      (System/exit 2))
    (if (= "--validate-manifest-v2" input)
      (let [path (second args)]
        (require! (and (string? path) (seq path))
                  "--validate-manifest-v2 requires a manifest path" {})
        (validate-manifest-v2! (json/read-str (slurp path) :key-fn keyword))
        (println (json/write-str {:format "amu.bounded-fastest-manifest-validation/v2"
                                 :valid? true})))
      (let [report (json/read-str (slurp input) :key-fn keyword)]
        (if (= "kotoba.runtime-multidomain-report/v2" (:format report))
          (println (json/write-str (qualify-multidomain report)
                                  :value-fn (fn [_ v] (if (keyword? v) (json-keyword v) v))))
          (let [fixture (:fixture report)
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
                      :value-fn (fn [_ v] (if (keyword? v) (json-keyword v) v))))))))))
