(ns kotoba.compiler.native-executor-test
  (:require [clojure.edn :as edn]
            [clojure.string :as str]
            [clojure.test :refer [deftest is]]
            [kotoba.compiler.atomic-output :as atomic-output]
            [kotoba.native.aarch64 :as aarch64]
            [kotoba.native.x86-64 :as x86-64]
            [kotoba.compiler.core :as compiler]
            [kototama.native.executor :as executor]
            [kotoba.artifact.runtime-identity :as runtime-identity]
            [kotoba.verifier.signing :as signing]))

(defn- target []
  (if (contains? #{"aarch64" "arm64"} (.toLowerCase (System/getProperty "os.arch")))
    :aarch64-kotoba-v1
    :x86_64-kotoba-v1))

(defn- signed [source policy]
  (let [artifact (:artifact (compiler/compile-source source (target) policy))
        key (signing/generate-keypair)
        envelope (signing/sign artifact key {:not-before 1000 :expires 2000})
        trust {:format :kotoba.trust/v1 :trusted-signers #{(:signer key)}
               :revoked-signers #{} :revoked-artifacts #{}}]
    {:artifact artifact :key key :envelope envelope :trust trust}))

(defonce measured-runtime
  (delay
    (let [{:keys [runtime loader-bytes]} (executor/measure-runtime)
          loader (doto (java.io.File/createTempFile "kotoba-test-loader-" "")
                   (.deleteOnExit))]
      (atomic-output/write-bytes! (.getPath loader) loader-bytes {:executable? true})
      {:runtime runtime :loader-path (.getPath loader)})))

(defn- execution-options [trust]
  (let [{:keys [runtime loader-path]} @measured-runtime]
    {:trust (assoc trust :trusted-runtime-sha256
                   #{(runtime-identity/identity-sha256 runtime)})
     :options {:now 1500 :entry 'main :runtime runtime :loader-path loader-path}}))

(deftest verified-native-execution-produces-measured-evidence
  (let [{:keys [envelope trust]} (signed "(defn main [] 42)" {:allow #{}})
        {:keys [trust options]} (execution-options trust)
        result (executor/execute envelope trust {:allow #{}} {:args []}
                                 options)]
    (is (= {:status :ok :result 42} (select-keys (:evidence result) [:status :result])))
    (is (= :kotoba.native-runtime/v6 (get-in result [:evidence :runtime :format])))
    (is (= :native (get-in result [:evidence :runtime :target-profile :execution])))
    (is (= executor/loader-source-sha256
           (get-in result [:evidence :runtime :loader-source-sha256])))
    (is (every? #(re-matches #"[0-9a-f]{64}" %)
                (vals (dissoc (get-in result [:evidence :runtime])
                              :format :target-profile))))
    ;; 512, not 511. `(defn main [] 42)` is an acyclic leaf: it cannot
    ;; re-enter guest or host work, so it is finite without an entry
    ;; decrement and kotoba-native stopped charging one (codegen
    ;; co-scientist iteration 11). A leaf that spends fuel here again is a
    ;; regression, not a rounding difference.
    (is (= {:status :ok :result 42
            :fuel {:initial 512 :remaining 512}
            :heap {:capacity 4096 :used 0}}
           (:report result)))
    (is (<= (:started-at result) (:finished-at result)))))

(deftest entryless-native-library-preserves-the-bool-host-boundary
  (let [source "(ns maturity.native-library (:export [choose negate]))
                (defn choose [enabled :bool value :i64] :i64
                  (if enabled value 0))
                (defn negate [value :bool witness :i64] :bool
                  (if value false true))"
        {:keys [envelope trust]} (signed source {:allow #{}})
        {:keys [trust options]} (execution-options trust)
        run (fn [entry args]
              (executor/execute envelope trust {:allow #{}} {:args args}
                                (assoc options :entry entry)))]
    (is (= 41 (get-in (run 'choose [true 41]) [:evidence :result]))
        "a host boolean enters an entryless native export as a typed :bool")
    (is (true? (get-in (run 'negate [false 0]) [:evidence :result]))
        "a :bool result from the selected export leaves as a host boolean")
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"entry arguments"
                          (run 'choose [1 41]))
        "the old raw 0/1 word spelling cannot impersonate a host boolean")
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"entry arguments"
                          (run 'choose [true true]))
        "a host boolean cannot cross an :i64 slot")))

(deftest entryless-native-library-copies-strings-across-the-real-process-boundary
  (let [source "(ns maturity.native-string-library (:export [echo decorate literal]))
                (defn echo [value :string] :string value)
                (defn decorate [value :string] :string
                  (string-concat \"[\" (string-concat value \"]\")))
                (defn literal [witness :i64] :string \"日本😀\")"
        {:keys [envelope trust]} (signed source {:allow #{}})
        {:keys [trust options]} (execution-options trust)
        run (fn [entry args]
              (executor/execute envelope trust {:allow #{}} {:args args}
                                (assoc options :entry entry)))]
    (is (= "hi\u0000😀" (get-in (run 'echo ["hi\u0000😀"]) [:evidence :result]))
        "host UTF-8, including NUL, is copied into the bounded native arena")
    (is (= "[言葉]" (get-in (run 'decorate ["言葉"]) [:evidence :result]))
        "a dynamic string-pool result is copied before the loader exits")
    (is (= "日本😀" (get-in (run 'literal [0]) [:evidence :result]))
        "a code-region literal result crosses the same inspected boundary")
    (is (= "" (get-in (run 'echo [""]) [:evidence :result]))
        "the empty string retains a real handle and is not confused with nil")
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"entry arguments"
                          (run 'echo [1]))
        "an integer handle cannot impersonate a host string")))

(deftest native-loader-refuses-an-invalid-string-result-handle
  (let [artifact (:artifact (compiler/compile-source "(defn main [] 0)" (target)))
        export (get (:exports artifact) 'main)
        {:keys [loader-path]} @measured-runtime
        host-os ((deref #'executor/host-os))
        run-process (deref #'executor/run-process)
        runtime-environment (deref #'executor/runtime-environment)
        delete-tree! (deref #'executor/delete-tree!)
        isa (if (= (target) :aarch64-kotoba-v1) "aarch64" "x86_64")
        directory (java.nio.file.Files/createTempDirectory
                   "kotoba-invalid-string-result-"
                   (make-array java.nio.file.attribute.FileAttribute 0))
        code-file (java.io.File. (.toFile directory) "program.bin")]
    (try
      (atomic-output/write-bytes!
       (.getPath code-file)
       (byte-array (map unchecked-byte (:code artifact))))
      (let [command [loader-path (.getPath code-file) (str (:offset export))
                     "0" isa "-"]
            process (run-process command (runtime-environment host-os :string)
                                 {:timeout-ms 5000 :output-limit 160000})
            report (edn/read-string (str/trim (:stdout process)))]
        (is (= 126 (:exit process)))
        (is (= {:status :trap :exit 126}
               (select-keys report [:status :exit])))
        (is (str/includes? (:stderr process)
                           ":reason :invalid-string-handle")))
      (finally (delete-tree! (.toFile directory))))))

(deftest entryless-native-library-copies-scalar-records-across-the-real-process-boundary
  (let [record-type "[:record :maturity/pair [[:left :i64] [:ready :bool]]]"
        source (str "(ns maturity.native-record-library (:export [echo fresh score]))\n"
                    "(defn echo [value " record-type "] " record-type " value)\n"
                    "(defn fresh [witness :i64] " record-type
                    " (record-new " record-type " -9 false))\n"
                    "(defn score [value " record-type "] :i64 "
                    " (+ (record-get value :left)"
                    " (if (record-get value :ready) 100 0)))")
        {:keys [envelope trust]} (signed source {:allow #{}})
        {:keys [trust options]} (execution-options trust)
        run (fn [entry args]
              (executor/execute envelope trust {:allow #{}} {:args args}
                                (assoc options :entry entry)))]
    (is (= {:left Long/MIN_VALUE :ready true}
           (get-in (run 'echo [{:ready true :left Long/MIN_VALUE}])
                   [:evidence :result]))
        "field order comes from the sealed descriptor, not host map order")
    (is (= {:left -9 :ready false}
           (get-in (run 'fresh [0]) [:evidence :result]))
        "guest-allocated records are copied before the loader exits")
    (is (= 107 (get-in (run 'score [{:left 7 :ready true}])
                       [:evidence :result]))
        "a host record is materialized as the native pair chain")
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"record fields"
                          (run 'echo [{:left 7}])))
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"record fields"
                          (run 'echo [{:left 7 :ready true :extra 0}])))
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"record field"
                          (run 'echo [{:left 7 :ready 1}])))))

(deftest native-loader-refuses-an-invalid-record-result-chain
  (let [artifact (:artifact (compiler/compile-source "(defn main [] 0)" (target)))
        export (get (:exports artifact) 'main)
        {:keys [loader-path]} @measured-runtime
        host-os ((deref #'executor/host-os))
        run-process (deref #'executor/run-process)
        runtime-environment (deref #'executor/runtime-environment)
        delete-tree! (deref #'executor/delete-tree!)
        record-type [:record :maturity/pair [[:left :i64] [:ready :bool]]]
        isa (if (= (target) :aarch64-kotoba-v1) "aarch64" "x86_64")
        directory (java.nio.file.Files/createTempDirectory
                   "kotoba-invalid-record-result-"
                   (make-array java.nio.file.attribute.FileAttribute 0))
        code-file (java.io.File. (.toFile directory) "program.bin")]
    (try
      (atomic-output/write-bytes!
       (.getPath code-file)
       (byte-array (map unchecked-byte (:code artifact))))
      (let [command [loader-path (.getPath code-file) (str (:offset export))
                     "0" isa "-"]
            process (run-process command
                                 (runtime-environment host-os record-type)
                                 {:timeout-ms 5000 :output-limit 65536})
            report (edn/read-string (str/trim (:stdout process)))]
        (is (= 127 (:exit process)))
        (is (= {:status :trap :exit 127}
               (select-keys report [:status :exit])))
        (is (str/includes? (:stderr process)
                           ":reason :invalid-record-chain")))
      (finally (delete-tree! (.toFile directory))))))

(deftest entryless-native-library-copies-option-and-result-across-the-real-process-boundary
  (let [source "(ns maturity.native-tagged-library
                  (:export [echo-option make-none make-some inspect-option
                            echo-result make-ok make-err inspect-result]))
                (defn echo-option [value :option-i64] :option-i64 value)
                (defn make-none [witness :i64] :option-i64 (option-none))
                (defn make-some [value :i64] :option-i64 (option-some value))
                (defn inspect-option [value :option-i64] :i64
                  (option-value value 99))
                (defn echo-result [value :result-i64] :result-i64 value)
                (defn make-ok [value :i64] :result-i64 (result-ok value))
                (defn make-err [value :i64] :result-i64 (result-err value))
                (defn inspect-result [value :result-i64] :i64
                  (+ (result-value value 1000) (result-error value 2000)))"
        {:keys [envelope trust]} (signed source {:allow #{}})
        {:keys [trust options]} (execution-options trust)
        run (fn [entry args]
              (executor/execute envelope trust {:allow #{}} {:args args}
                                (assoc options :entry entry)))]
    (is (= [false] (get-in (run 'echo-option [[false]]) [:evidence :result])))
    (is (= [true Long/MIN_VALUE]
           (get-in (run 'echo-option [[true Long/MIN_VALUE]])
                   [:evidence :result])))
    (is (= [false] (get-in (run 'make-none [0]) [:evidence :result])))
    (is (= [true Long/MAX_VALUE]
           (get-in (run 'make-some [Long/MAX_VALUE]) [:evidence :result])))
    (is (= 99 (get-in (run 'inspect-option [[false]]) [:evidence :result])))
    (is (= -7 (get-in (run 'inspect-option [[true -7]]) [:evidence :result])))
    (is (= [true Long/MIN_VALUE]
           (get-in (run 'echo-result [[true Long/MIN_VALUE]])
                   [:evidence :result])))
    (is (= [false Long/MAX_VALUE]
           (get-in (run 'echo-result [[false Long/MAX_VALUE]])
                   [:evidence :result])))
    (is (= [true -9] (get-in (run 'make-ok [-9]) [:evidence :result])))
    (is (= [false 11] (get-in (run 'make-err [11]) [:evidence :result])))
    (is (= 2007 (get-in (run 'inspect-result [[true 7]]) [:evidence :result])))
    (is (= 1008 (get-in (run 'inspect-result [[false 8]]) [:evidence :result])))
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"tagged i64 value"
                          (run 'echo-option [[false 0]])))
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"tagged i64 value"
                          (run 'echo-option [[true]])))
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"tagged i64 value"
                          (run 'echo-result [[1 0]])))))

(deftest native-loader-refuses-invalid-option-and-result-handles
  (let [artifact (:artifact (compiler/compile-source "(defn main [] 0)" (target)))
        export (get (:exports artifact) 'main)
        {:keys [loader-path]} @measured-runtime
        host-os ((deref #'executor/host-os))
        run-process (deref #'executor/run-process)
        runtime-environment (deref #'executor/runtime-environment)
        delete-tree! (deref #'executor/delete-tree!)
        isa (if (= (target) :aarch64-kotoba-v1) "aarch64" "x86_64")
        directory (java.nio.file.Files/createTempDirectory
                   "kotoba-invalid-tagged-result-"
                   (make-array java.nio.file.attribute.FileAttribute 0))
        code-file (java.io.File. (.toFile directory) "program.bin")]
    (try
      (atomic-output/write-bytes!
       (.getPath code-file)
       (byte-array (map unchecked-byte (:code artifact))))
      (doseq [[result-type expected-exit reason]
              [[:option-i64 128 ":reason :invalid-option-i64"]
               [:result-i64 129 ":reason :invalid-result-i64"]]]
        (let [command [loader-path (.getPath code-file) (str (:offset export))
                       "0" isa "-"]
              process (run-process command
                                   (runtime-environment host-os result-type)
                                   {:timeout-ms 5000 :output-limit 65536})
              report (edn/read-string (str/trim (:stdout process)))]
          (is (= expected-exit (:exit process)) (name result-type))
          (is (= {:status :trap :exit expected-exit}
                 (select-keys report [:status :exit])) (name result-type))
          (is (str/includes? (:stderr process) reason) (name result-type))))
      (finally (delete-tree! (.toFile directory))))))

(deftest scalar-variant-crosses-the-real-native-process-boundary
  (let [type [:variant :maturity/outcome [[:count :i64] [:ready :bool]]]
        type-text (pr-str type)
        run-source
        (fn [source entry args]
          (let [{:keys [envelope trust]} (signed source {:allow #{}})
                {:keys [trust options]} (execution-options trust)]
            (executor/execute envelope trust {:allow #{}} {:args args}
                              (assoc options :entry entry))))
        echo-source (str "(ns maturity.variant-echo (:export [echo]))\n"
                         "(defn echo [value " type-text "] " type-text " value)")
        fresh-source (str "(ns maturity.variant-fresh (:export [fresh]))\n"
                          "(defn fresh [witness :i64] " type-text
                          " (variant-new " type-text " :ready true))")
        score-source (str "(ns maturity.variant-score (:export [score]))\n"
                          "(defn score [value " type-text "] :i64 "
                          " (match-variant value " type-text
                          " (:count n n) (:ready b (if b 100 0))))")]
    (is (= [type :count Long/MIN_VALUE]
           (get-in (run-source echo-source 'echo
                               [[type :count Long/MIN_VALUE]])
                   [:evidence :result])))
    (is (= [type :ready false]
           (get-in (run-source echo-source 'echo [[type :ready false]])
                   [:evidence :result])))
    (is (= [type :ready true]
           (get-in (run-source fresh-source 'fresh [0]) [:evidence :result])))
    (is (= 7 (get-in (run-source score-source 'score [[type :count 7]])
                     [:evidence :result])))
    (is (= 100 (get-in (run-source score-source 'score [[type :ready true]])
                       [:evidence :result])))
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"scalar variant"
                          (run-source echo-source 'echo [[type :missing 1]])))
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"scalar variant"
                          (run-source echo-source 'echo [[type :ready 1]])))))

(deftest native-loader-refuses-an-invalid-variant-result-handle
  (let [artifact (:artifact (compiler/compile-source "(defn main [] 0)" (target)))
        export (get (:exports artifact) 'main)
        {:keys [loader-path]} @measured-runtime
        host-os ((deref #'executor/host-os))
        run-process (deref #'executor/run-process)
        runtime-environment (deref #'executor/runtime-environment)
        delete-tree! (deref #'executor/delete-tree!)
        type [:variant :maturity/outcome [[:count :i64] [:ready :bool]]]
        isa (if (= (target) :aarch64-kotoba-v1) "aarch64" "x86_64")
        directory (java.nio.file.Files/createTempDirectory
                   "kotoba-invalid-variant-result-"
                   (make-array java.nio.file.attribute.FileAttribute 0))
        code-file (java.io.File. (.toFile directory) "program.bin")]
    (try
      (atomic-output/write-bytes!
       (.getPath code-file)
       (byte-array (map unchecked-byte (:code artifact))))
      (let [command [loader-path (.getPath code-file) (str (:offset export))
                     "0" isa "-"]
            process (run-process command (runtime-environment host-os type)
                                 {:timeout-ms 5000 :output-limit 65536})
            report (edn/read-string (str/trim (:stdout process)))]
        (is (= 130 (:exit process)))
        (is (= {:status :trap :exit 130}
               (select-keys report [:status :exit])))
        (is (str/includes? (:stderr process) ":reason :invalid-variant")))
      (finally (delete-tree! (.toFile directory))))))

(deftest typed-i64-capability-call-is-qualified-on-native
  (let [source "(defn main [] :i64 (typed-cap-call 4 :i64 :i64 41))"
        policy {:allow #{[:cap/call 4]}}
        {:keys [envelope trust]} (signed source policy)
        {:keys [trust options]} (execution-options trust)
        result (executor/execute envelope trust policy {:args []} options)]
    (is (= {:status :ok :result 42}
           (select-keys (:evidence result) [:status :result])))
    (is (= #{[:cap/call 4]} (get-in envelope [:artifact :effects])))
    (is (= '(typed-cap-call 4 :i64 :i64 41)
           (get-in envelope [:artifact :program :functions 0 :body])))))

(deftest typed-string-capability-call-validates-native-pointer-length-boundary
  (let [source "(defn main [] :i64
                  (string-byte-length
                    (typed-cap-call 4 :string :string \"hello😀\")))"
        policy {:allow #{[:cap/call 4]}}
        {:keys [envelope trust]} (signed source policy)
        {:keys [trust options]} (execution-options trust)
        result (executor/execute envelope trust policy {:args []} options)]
    (is (= {:status :ok :result 9}
           (select-keys (:evidence result) [:status :result])))
    (is (= '(string-byte-length
              (typed-cap-call 4 :string :string "hello😀"))
           (get-in envelope [:artifact :program :functions 0 :body])))
    (is (= 128 (get-in envelope [:artifact :context-abi
                                 :typed-cap-call-offset])))))

(deftest typed-option-and-result-capability-calls-validate-native-tagged-boundaries
  (let [source "(defn main [] :i64
                  (+ (option-value
                       (typed-cap-call 4 :option-i64 :option-i64 (some 41)) 0)
                     (option-value
                       (typed-cap-call 4 :option-i64 :option-i64 nil) 5)
                     (result-value
                       (typed-cap-call 4 :result-i64 :result-i64 (result-ok 7)) 0)
                     (result-error
                       (typed-cap-call 4 :result-i64 :result-i64 (result-err 9)) 0)))"
        policy {:allow #{[:cap/call 4]}}
        {:keys [envelope trust]} (signed source policy)
        {:keys [trust options]} (execution-options trust)
        result (executor/execute envelope trust policy {:args []} options)]
    (is (= {:status :ok :result 62}
           (select-keys (:evidence result) [:status :result])))
    (is (= #{[:cap/call 4]} (get-in envelope [:artifact :effects])))
    (is (= :kotoba.kir/v4 (get-in envelope [:artifact :program :format])))))

(deftest typed-option-and-result-capability-calls-emit-on-both-native-isas
  (let [source "(defn main [] :i64
                  (+ (option-value
                       (typed-cap-call 4 :option-i64 :option-i64 (some 3)) 0)
                     (result-error
                       (typed-cap-call 4 :result-i64 :result-i64 (result-err 4)) 0)))"
        policy {:allow #{[:cap/call 4]}}]
    (doseq [native-target [:x86_64-kotoba-v1 :aarch64-kotoba-v1]]
      (let [artifact (:artifact (compiler/compile-source source native-target policy))]
        (is (seq (:code artifact)) (name native-target))
        (is (= #{[:cap/call 4]} (:effects artifact)) (name native-target))))))

(def generic-option-result-source
  "(defn main [] :i64
     (+ (match-option
          (option-some-of [:option :string] \"abc\") [:option :string]
          (none 100)
          (some text (string-byte-length text)))
        (string-byte-length
          (result-value-of
            [:result :string [:option :i64]]
            (result-ok-of [:result :string [:option :i64]] \"hello\")
            \"fallback\"))
        (option-value-of
          [:option :i64]
          (result-error-of
            [:result :string [:option :i64]]
            (result-err-of
              [:result :string [:option :i64]]
              (option-some-of [:option :i64] 7))
            (option-none-of [:option :i64]))
          0)
        (match-option
          (option-none-of [:option [:result :i64 :bool]])
          [:option [:result :i64 :bool]]
          (none 11)
          (some nested 100))
        (match-result
          (result-err-of [:result :bool :i64] 13)
          [:result :bool :i64]
          (ok value 100)
          (err error error))))")

(deftest generic-option-and-result-values-execute-through-real-native-loader
  (let [{:keys [envelope trust]} (signed generic-option-result-source {:allow #{}})
        {:keys [trust options]} (execution-options trust)
        result (executor/execute envelope trust {:allow #{}} {:args []} options)]
    (is (= 39 (get-in result [:evidence :result])))
    (is (= :kotoba.kir/v4 (get-in envelope [:artifact :program :format])))
    (is (= {:capacity 4096 :used 8} (get-in result [:report :heap])))))

(deftest generic-option-and-result-values-emit-on-both-native-isas
  (doseq [native-target [:x86_64-kotoba-v1 :aarch64-kotoba-v1]]
    (let [artifact (:artifact
                    (compiler/compile-source generic-option-result-source
                                             native-target))]
      (is (seq (:code artifact)) (name native-target))
      (is (= :kotoba.kir/v4 (get-in artifact [:program :format]))
          (name native-target)))))

(deftest native-generic-option-still-rejects-non-word-payloads
  (let [record-type
        "[:record :demo/person [[:age :i64]]]"
        source
        (str "(defn main [] :i64 "
             "(match-option "
             "(option-some-of [:option " record-type "] "
             "(record-new " record-type " 7)) "
             "[:option " record-type "] "
             "(none 0) (some person (record-get " record-type " person :age))))")]
    (let [error (try
                  (compiler/compile-source source (target))
                  nil
                  (catch clojure.lang.ExceptionInfo error error))]
      (is (instance? clojure.lang.ExceptionInfo error))
      (is (= :scalar-value-required (:problem (ex-data error))))
      (is (= :kir-to-gmir (:ir/phase (ex-data error))))
      (is (re-find #"machine IR rejected" (.getMessage error))))))

(deftest execution-rejects-before-entering-untrusted-or-unauthorized-code
  (let [{:keys [envelope trust]} (signed "(defn main [] 42)" {:allow #{}})
        tampered (assoc-in envelope [:artifact :code 0] 255)
        {:keys [runtime loader-path]} @measured-runtime
        {trusted-trust :trust trusted-options :options} (execution-options trust)]
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"runtime identity is not trusted"
                          (executor/execute envelope trust {:allow #{}} {:args []}
                                            {:now 1500 :entry 'main :runtime runtime
                                             :loader-path loader-path})))
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"artifact integrity mismatch"
                          (executor/execute tampered trust {:allow #{}} {:args []}
                                            {:now 1500 :entry 'main})))
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"entry arity"
                          (executor/execute envelope trusted-trust {:allow #{}}
                                            {:args [1]} trusted-options))))
  (let [policy {:allow #{[:cap/call 7]}}
        {:keys [envelope trust]} (signed "(defn main [] (cap-call 7 41))" policy)
        {trusted-trust :trust options :options} (execution-options trust)]
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"denies required effects"
                          (executor/execute envelope trusted-trust {:allow #{}}
                                            {:args []} options)))))

(deftest execution-rejects-a-valid-artifact-sealed-for-another-os
  (let [isa (if (= (target) :aarch64-kotoba-v1) "aarch64" "x86_64")
        other-os (if (.contains (.toLowerCase (System/getProperty "os.name")) "mac")
                   "linux" "macos")
        explicit-target (keyword (str isa "-" other-os "-kotoba-v1"))
        artifact (:artifact (compiler/compile-source "(defn main [] 42)" explicit-target))
        key (signing/generate-keypair)
        envelope (signing/sign artifact key {:not-before 1000 :expires 2000})
        trust {:format :kotoba.trust/v1 :trusted-signers #{(:signer key)}
               :revoked-signers #{} :revoked-artifacts #{}}]
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"does not match execution host"
                          (executor/execute envelope trust {:allow #{}} {:args []}
                                            {:now 1500 :entry 'main})))))

(deftest execution-rejects-a-trusted-runtime-measured-for-another-platform
  (let [{:keys [envelope trust]} (signed "(defn main [] 42)" {:allow #{}})
        {:keys [runtime loader-path]} @measured-runtime
        other-os (if (= :macos (get-in runtime [:target-profile :os])) :linux :macos)
        other-runtime (-> runtime
                          (assoc-in [:target-profile :os] other-os)
                          (assoc-in [:target-profile :runtime]
                                    (if (= other-os :linux)
                                      :kotoba-linux-supervisor-v1
                                      :kotoba-macos-supervisor-v1)))
        pinned (assoc trust :trusted-runtime-sha256
                      #{(runtime-identity/identity-sha256 other-runtime)})]
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"runtime target profile"
                          (executor/execute envelope pinned {:allow #{}} {:args []}
                                            {:now 1500 :entry 'main
                                             :runtime other-runtime
                                            :loader-path loader-path})))))

(deftest windows-runtime-identity-requires-the-windows-loader-source
  (let [{:keys [runtime]} @measured-runtime]
    (doseq [target [:x86_64-windows-kotoba-v1 :aarch64-windows-kotoba-v1]]
      (let [windows-profile (compiler/compile-source "(defn main [] 42)" target)
            windows-runtime (-> runtime
                                (assoc :target-profile (get-in windows-profile [:artifact :target-profile]))
                                (assoc :loader-source-sha256
                                       runtime-identity/windows-loader-source-sha256))]
        (is (= windows-runtime (runtime-identity/validate! windows-runtime)))
        (is (thrown-with-msg? clojure.lang.ExceptionInfo #"runtime identity rejected"
                              (runtime-identity/validate!
                               (assoc windows-runtime :loader-source-sha256
                                      runtime-identity/loader-source-sha256))))))))

(deftest windows-loader-source-bytes-match-the-pinned-runtime-identity
  (let [file-sha256 (deref #'executor/file-sha256)
        source (java.io.File. "tools/kexe_loader_windows.c")]
    (is (.isFile source) "the measured Windows loader source must be present")
    (is (= runtime-identity/windows-loader-source-sha256
           (file-sha256 source))
        "runtime trust must name the bytes that the Windows build actually compiles")))

(deftest execution-rejects-a-loader-that-does-not-match-the-approved-bytes
  (let [{:keys [envelope trust]} (signed "(defn main [] 42)" {:allow #{}})
        {:keys [trust options]} (execution-options trust)
        changed (doto (java.io.File/createTempFile "kotoba-changed-loader-" "")
                  (.deleteOnExit))]
    (atomic-output/write-bytes! (.getPath changed) (byte-array [0 1 2 3])
                                {:executable? true})
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"does not match runtime identity"
                          (executor/execute envelope trust {:allow #{}} {:args []}
                                            (assoc options :loader-path (.getPath changed)))))))

(deftest host-process-boundary-is-time-and-output-bounded
  (let [run-process @#'executor/run-process
        test-env {"PATH" "/usr/bin:/bin"}
        normal (run-process ["/bin/sh" "-c" "printf ok"] test-env
                            {:timeout-ms 1000 :output-limit 1024})
        timeout (run-process ["/bin/sh" "-c" "sleep 10"] test-env
                             {:timeout-ms 100 :output-limit 1024})
        flood (run-process ["/bin/sh" "-c" "yes x"] test-env
                           {:timeout-ms 2000 :output-limit 1024})
        isolated (run-process ["/bin/sh" "-c" "printf %s \"${HOME-unset}\""] {}
                              {:timeout-ms 1000 :output-limit 1024})]
    (is (= {:exit 0 :stdout "ok" :stderr "" :timed-out? false
            :output-exceeded? false}
           normal))
    (is (:timed-out? timeout))
    (is (:output-exceeded? flood))
    (is (<= (count (:stdout flood)) 1024))
    (is (= "unset" (:stdout isolated)))))

(deftest windows-loader-failure-class-is-path-free
  (let [failure-class @#'executor/loader-failure-class]
    (is (= "CreateAppContainerProfile/win32=5"
           (failure-class
            "kexe-loader-windows: CreateAppContainerProfile: win32=5\n")))
    (is (= "child contract requires an AppContainer process token"
           (failure-class
            "kexe-loader-windows: child contract requires an AppContainer process token\n")))
    (is (nil? (failure-class "unable to open C:\\secret\\program.bin\n")))))

(deftest native-runtime-environment-does-not-inherit-ambient-authority
  (is (= {"KEXE_STRUCTURED_REPORT" "1"}
         ((deref #'executor/runtime-environment) :linux))))

(deftest compiler-executable-is-resolved-to-a-hashed-real-file
  (let [resolve-executable @#'executor/resolve-executable
        file-sha256 @#'executor/file-sha256
        path (resolve-executable "cc")]
    (is (.isAbsolute path))
    (is (java.nio.file.Files/isRegularFile
         path (make-array java.nio.file.LinkOption 0)))
    (is (java.nio.file.Files/isExecutable path))
    (is (re-matches #"[0-9a-f]{64}" (file-sha256 (.toFile path))))
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"invalid toolchain"
                          (resolve-executable "./cc")))))

(deftest compiler-reported-tools-require-canonical-executable-paths
  (let [resolve-tool @#'executor/resolve-reported-tool
        env {"PATH" "/usr/bin:/bin"}]
    (is (.isAbsolute (resolve-tool "/bin/sh\n" env)))
    (is (.isAbsolute (resolve-tool "sh\n" env)))
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"not an executable"
                          (resolve-tool "relative/tool\n" env)))
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"malformed tool path"
                          (resolve-tool "as\nld\n" env)))
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"malformed tool path"
                          (resolve-tool (str "as" \u0000) env)))))

(deftest compiler-resource-manifest-is-deterministic-bounded-and-symlink-free
  (let [manifest @#'executor/directory-manifest-sha256
        delete-tree @#'executor/delete-tree!
        root (java.nio.file.Files/createTempDirectory
              "kotoba-resource-test-" (make-array java.nio.file.attribute.FileAttribute 0))]
    (try
      (let [nested (java.nio.file.Files/createDirectory
                    (.resolve root "nested")
                    (make-array java.nio.file.attribute.FileAttribute 0))
            first-file (.resolve root "a.h")
            second-file (.resolve nested "b.h")]
        (java.nio.file.Files/writeString first-file "alpha"
                                         (make-array java.nio.file.OpenOption 0))
        (java.nio.file.Files/writeString second-file "beta"
                                         (make-array java.nio.file.OpenOption 0))
        (let [first-hash (manifest root)]
          (is (= first-hash (manifest root)))
          (java.nio.file.Files/writeString second-file "changed"
                                           (make-array java.nio.file.OpenOption 0))
          (is (not= first-hash (manifest root))))
        (java.nio.file.Files/createSymbolicLink
         (.resolve root "link") first-file
         (make-array java.nio.file.attribute.FileAttribute 0))
        (is (thrown-with-msg? clojure.lang.ExceptionInfo #"contains a symlink"
                              (manifest root)))
        (java.nio.file.Files/delete (.resolve root "link"))
        (with-open [large (java.io.RandomAccessFile. (.toFile (.resolve root "large")) "rw")]
          (.setLength large (inc (* 64 1024 1024))))
        (is (thrown-with-msg? clojure.lang.ExceptionInfo #"bytes exceed limit"
                              (manifest root))))
      (finally (delete-tree (.toFile root))))))

(deftest compiler-dependency-closure-parser-and-manifest-fail-closed
  (let [parse-deps @#'executor/parse-dependency-file
        manifest @#'executor/dependency-manifest-sha256
        delete-tree @#'executor/delete-tree!
        root (java.nio.file.Files/createTempDirectory
              "kotoba-dependency-test-" (make-array java.nio.file.attribute.FileAttribute 0))]
    (try
      (is (= ["path with space.h" "next.h"]
             (parse-deps "output.o: path\\ with\\ space.h \\\n  next.h\n")))
      (is (= ["C:\\Program Files\\SDK\\windows.h" "D:\\a\\source.h"]
             (parse-deps (str "D:\\a\\output.o: C:\\Program\\ Files\\SDK\\windows.h \\\r\n"
                              " D:\\a\\source.h\r\n"))))
      (is (thrown-with-msg? clojure.lang.ExceptionInfo #"no target separator"
                            (parse-deps "missing target")))
      (is (thrown-with-msg? clojure.lang.ExceptionInfo #"ends in an escape"
                            (parse-deps "out: path\\")))
      (let [first-file (.resolve root "first.h")
            second-file (.resolve root "second.h")]
        (java.nio.file.Files/writeString first-file "alpha"
                                         (make-array java.nio.file.OpenOption 0))
        (java.nio.file.Files/writeString second-file "beta"
                                         (make-array java.nio.file.OpenOption 0))
        (let [first-hash (manifest [(str second-file) (str first-file)])]
          (is (= first-hash (manifest [(str first-file) (str second-file)])))
          (java.nio.file.Files/writeString second-file "changed"
                                           (make-array java.nio.file.OpenOption 0))
          (is (not= first-hash (manifest [(str first-file) (str second-file)]))))
        (java.nio.file.Files/delete second-file)
        (is (thrown-with-msg? clojure.lang.ExceptionInfo #"not a regular file"
                              (manifest [(str second-file)])))
        (let [large (.resolve root "large.h")]
          (with-open [file (java.io.RandomAccessFile. (.toFile large) "rw")]
            (.setLength file (inc (* 64 1024 1024))))
          (is (thrown-with-msg? clojure.lang.ExceptionInfo #"bytes exceed limit"
                                (manifest [(str large)])))))
      (finally (delete-tree (.toFile root))))))

(deftest native-trap-is-returned-as-measured-evidence
  (let [{:keys [envelope trust]}
        (signed "(defn forever [x] (forever x)) (defn main [] 0)" {:allow #{}})
        {:keys [trust options]} (execution-options trust)
        result (executor/execute envelope trust {:allow #{}} {:args [0]}
                                 (assoc options :entry 'forever))
        expected-signal (if (= (target) :aarch64-kotoba-v1) :SIGTRAP :SIGILL)]
    (is (= :trap (get-in result [:evidence :status])))
    (is (= {:kind :signal :signal expected-signal}
           (get-in result [:evidence :trap])))
    (is (= 0 (get-in result [:report :fuel :remaining])))
    (is (= 120 (get-in result [:report :exit])))))

(deftest bounded-pair-arena-executes-and-rejects-forged-handles
  (let [{:keys [envelope trust]}
        (signed "(defn bad [handle] (pair-first handle))
                 (defn main [] (+ (pair-first (pair 20 99))
                                  (pair-second (pair 1 22))))" {:allow #{}})
        {:keys [trust options]} (execution-options trust)
        result (executor/execute envelope trust {:allow #{}} {:args []} options)
        forged (executor/execute envelope trust {:allow #{}} {:args [1]}
                                 (assoc options :entry 'bad))
        expected-signal (if (= (target) :aarch64-kotoba-v1) :SIGILL :SIGILL)]
    (is (= 42 (get-in result [:evidence :result])))
    (is (= {:capacity 4096 :used 2} (get-in result [:report :heap])))
    (is (= :trap (get-in forged [:evidence :status])))
    (is (= {:kind :signal :signal expected-signal}
           (get-in forged [:evidence :trap])))))

;; ADR-2607198300 / ADR-2607198200: the native (JVM/Node/browser-free) analog
;; of the com-stripe Customer create/get/list pilot -- entity/attribute/value
;; are caller-assigned integers rather than EDN strings (this backend has no
;; addressable buffer), but the EAVT mechanism (assert, point-get, count
;; distinct entities, index into them) is proven end to end via the real
;; kexe-loader native process, no JVM/JS engine involved once the artifact
;; is compiled.
(deftest kgraph-native-customer-pilot-asserts-and-queries-through-real-kexe-loader
  ;; NOTE: this backend's `let` (aarch64.clj/x86-64.clj `normalize-expr`) is a
  ;; compile-time substitution pass, not an imperative sequence -- a binding
  ;; whose value is never referenced in the body is never emitted at all, so
  ;; a side-effecting call (kgraph-assert!, create-customers itself) MUST
  ;; have its return value actually consumed (here, summed) or it silently
  ;; never executes. No `let` is used below for exactly this reason.
  (let [{:keys [envelope trust]}
        (signed "(defn create-customers []
                   (+ (kgraph-assert! 1 1 1001)
                      (kgraph-assert! 1 2 2001)
                      (kgraph-assert! 1 3 0)
                      (kgraph-assert! 2 1 1002)
                      (kgraph-assert! 2 2 2002)
                      (kgraph-assert! 2 3 500)))
                 (defn main []
                   (+ (if (= (create-customers) 6) 1 0)
                      (if (= (kgraph-get 1 1) 1001) 1 0)
                      (if (= (kgraph-get 1 2) 2001) 1 0)
                      (if (= (kgraph-get 1 3) 0) 1 0)
                      (if (= (kgraph-get 2 1) 1002) 1 0)
                      (if (= (kgraph-get 2 2) 2002) 1 0)
                      (if (= (kgraph-get 2 3) 500) 1 0)
                      (if (= (kgraph-count 1) 2) 1 0)
                      (if (= (kgraph-entity-at 1 0) 1) 1 0)
                      (if (= (kgraph-entity-at 1 1) 2) 1 0)))
                 (defn get-unknown-field [] (+ (create-customers) (kgraph-get 1 999)))
                 (defn entity-at-out-of-range [] (+ (create-customers) (kgraph-entity-at 1 5)))"
               {:allow #{}})
        {:keys [trust options]} (execution-options trust)
        result (executor/execute envelope trust {:allow #{}} {:args []} options)
        unknown (executor/execute envelope trust {:allow #{}} {:args []}
                                  (assoc options :entry 'get-unknown-field))
        out-of-range (executor/execute envelope trust {:allow #{}} {:args []}
                                       (assoc options :entry 'entity-at-out-of-range))
        expected-signal (if (= (target) :aarch64-kotoba-v1) :SIGILL :SIGILL)]
    (is (= 10 (get-in result [:evidence :result]))
        "create-customers returned 6, and all 9 get/count/entity-at checks matched -- genuinely native EAVT assert/query")
    (is (= (+ 6 Long/MIN_VALUE) (get-in unknown [:evidence :result]))
        "kgraph-get on an unasserted (entity,attribute) returns the not-found sentinel, not a trap")
    (is (= :trap (get-in out-of-range [:evidence :status]))
        "kgraph-entity-at past the distinct-entity count traps closed, like a forged pair handle")
    (is (= {:kind :signal :signal expected-signal}
           (get-in out-of-range [:evidence :trap])))))

;; ADR-2607198300 follow-up: `let` genuinely sequences (evaluates each binding
;; exactly once, in order, before the body) instead of the prior compile-time
;; substitution pass, which silently dropped an unreferenced side-effecting
;; binding, silently duplicated a repeatedly-referenced one, and silently made
;; an unconditionally-intended effect conditional if its one reference sat
;; inside an `if` branch. Each deftest below exercises one of those three
;; failure modes and would have failed before the fix (either wrong `:result`,
;; wrong `:report`, or -- for the unused-binding case -- an unchanged not-found
;; sentinel proving the assert never ran).

(deftest let-runs-an-unreferenced-side-effecting-binding-exactly-once
  (let [{:keys [envelope trust]}
        (signed "(defn main []
                   (let [_unused (kgraph-assert! 1 1 42)]
                     (kgraph-get 1 1)))"
               {:allow #{}})
        {:keys [trust options]} (execution-options trust)
        result (executor/execute envelope trust {:allow #{}} {:args []} options)]
    (is (= 42 (get-in result [:evidence :result]))
        "an unreferenced kgraph-assert! binding still runs -- a real let, not inlining-by-reference")))

(deftest let-runs-a-repeatedly-referenced-side-effecting-binding-exactly-once
  (let [{:keys [envelope trust]}
        (signed "(defn main []
                   (let [x (pair 1 1)]
                     (+ x x)))"
               {:allow #{}})
        {:keys [trust options]} (execution-options trust)
        result (executor/execute envelope trust {:allow #{}} {:args []} options)]
    (is (= 2 (get-in result [:evidence :result]))
        "x is the same handle both times (1+1=2) -- pair ran once and was reused, not
         re-evaluated per reference (which would return the first call's handle (1)
         plus the second call's handle (2), summing to 3)")
    (is (= {:capacity 4096 :used 1} (get-in result [:report :heap]))
        "exactly one pair allocation happened")))

(deftest let-runs-a-side-effecting-binding-unconditionally-even-when-its-one-reference-is-in-a-dead-if-branch
  (let [{:keys [envelope trust]}
        (signed "(defn main []
                   (let [x (pair 1 1)]
                     (if 0 x 999)))"
               {:allow #{}})
        {:keys [trust options]} (execution-options trust)
        result (executor/execute envelope trust {:allow #{}} {:args []} options)]
    (is (= 999 (get-in result [:evidence :result]))
        "the else branch is taken (test is 0/falsy)")
    (is (= {:capacity 4096 :used 1} (get-in result [:report :heap]))
        "pair still ran -- a real let evaluates its binding before the if is even
         reached, unlike substitution, which would inline `pair` only into the
         (never-executed) then-branch and never run it at all")))

(deftest nested-lets-compose-with-correct-depth-relative-addressing
  (let [{:keys [envelope trust]}
        (signed "(defn main []
                   (let [a (pair 10 20)]
                     (let [b (pair 30 40)]
                       (+ (pair-first a) (pair-second b)))))"
               {:allow #{}})
        {:keys [trust options]} (execution-options trust)
        result (executor/execute envelope trust {:allow #{}} {:args []} options)]
    (is (= 50 (get-in result [:evidence :result]))
        "pair-first of the outer let's binding (10) + pair-second of the inner let's
         binding (40) -- proves the outer binding is still reachable at the correct
         stack depth after the inner let has pushed its own slot")
    (is (= {:capacity 4096 :used 2} (get-in result [:report :heap])))))

(deftest let-composes-with-recursion-within-the-fuel-budget
  (let [{:keys [envelope trust]}
        (signed "(defn count-down [n acc]
                   (let [_touch (pair n acc)]
                     (if (= n 0) acc (count-down (- n 1) (+ acc 1)))))
                 (defn main [] (count-down 50 0))"
               {:allow #{}})
        {:keys [trust options]} (execution-options trust)
        result (executor/execute envelope trust {:allow #{}} {:args []} options)]
    (is (= 50 (get-in result [:evidence :result]))
        "50 levels of ordinary (non-tail-optimized self-call from inside a let,
         intentionally falling back off the tail-call fast path -- see emit-call's
         zero-temp-depth guard) recursion, well within the 512-call fuel budget")
    (is (= {:capacity 4096 :used 51} (get-in result [:report :heap]))
        "one pair per call: the initial call plus 50 recursive calls")))

;; ADR-2607198300 follow-up: string values are pair(offset,length) handles
;; whose bytes live either in the artifact's own code+literal-data region
;; (compile-time literals, embedded once per distinct content past the last
;; function's code) or in a runtime string pool (string-concat results),
;; uniformly resolved host-side by sign. Proven end to end through the real
;; kexe-loader native process -- no JVM, no JS engine.
(deftest string-literal-byte-length-round-trips-through-real-kexe-loader
  (let [{:keys [envelope trust]}
        (signed "(defn main [] (string-byte-length \"hello\"))" {:allow #{}})
        {:keys [trust options]} (execution-options trust)
        result (executor/execute envelope trust {:allow #{}} {:args []} options)]
    (is (= 5 (get-in result [:evidence :result]))
        "string-byte-length is exactly pair-second of the literal's own (offset,length) handle")))

(deftest string-equal-compares-content-not-handle-identity
  (let [{:keys [envelope trust]}
        (signed "(defn same [] :bool (string=? \"same\" \"same\"))
                 (defn different-content [] :bool (string=? \"abc\" \"xyz\"))
                 (defn different-length [] :bool (string=? \"ab\" \"abc\"))
                 (defn main []
                   (+ (if (same) 1 0)
                      (+ (if (different-content) 1 0)
                         (if (different-length) 1 0))))"
               {:allow #{}})
        {:keys [trust options]} (execution-options trust)
        result (executor/execute envelope trust {:allow #{}} {:args []} options)]
    (is (= 1 (get-in result [:evidence :result]))
        "\"same\"=\"same\" (1) is the ONLY true comparison of the three -- two
         SEPARATE literal occurrences of identical content get two DIFFERENT
         pair handles (pair_new allocates a fresh slot every call), so this
         proves string=? compares the addressed BYTES, not handle identity")))

(deftest string-concat-produces-a-pool-handle-comparable-to-a-literal
  (let [{:keys [envelope trust]}
        (signed "(defn main []
                   (+ (string-byte-length (string-concat \"foo\" \"bar\"))
                      (if (string=? (string-concat \"foo\" \"bar\") \"foobar\") 1 0)))"
               {:allow #{}})
        {:keys [trust options]} (execution-options trust)
        result (executor/execute envelope trust {:allow #{}} {:args []} options)]
    (is (= 7 (get-in result [:evidence :result]))
        "6 (byte-length of the concatenated \"foobar\") + 1 (string=? against
         the literal \"foobar\" is true) -- proves string=? correctly compares
         a runtime string-pool handle (concat's own output, negative-encoded
         offset) against a code-region literal handle (non-negative offset)")))

;; ADR 0062: the first native (x86-64/aarch64) value-representation
;; increment -- a sealed, all-scalar (`:i64`/`:bool` fields only, no
;; `:f64`; see `ir/only-native-word-typed-features?`'s own
;; doc comment for why) record, construction + field projection only, real
;; native-process evidence matching every other deftest in this file (no
;; synthetic byte-level check). The record schema itself has no independent
;; runtime representation at all: `(record-get schema (record-new schema
;; ...) field)` desugars to the SAME `let`/`load-let` stack machinery this
;; file's own `let`-sequencing deftests above already prove correct -- see
;; `emit-record-get-of-new` in both `backend/x86-64.cljc` and
;; `backend/aarch64.cljc`.
(def ^:private native-record-schema
  '[:record :native/scalar-record [[:a :i64] [:b :i64] [:c :bool]]])

(deftest native-scalar-record-construction-and-field-projection-round-trips-through-real-kexe-loader
  (let [schema (pr-str native-record-schema)
        source (str
                "(defn checks [a b]
                   (+ (if (= (record-get " schema " (record-new " schema " a b true) :a) a) 1 0)
                      (+ (if (= (record-get " schema " (record-new " schema " a b true) :b) b) 1 0)
                         (+ (if (record-get " schema " (record-new " schema " a b true) :c) 1 0)
                            (if (record-get " schema " (record-new " schema " a b false) :c) 0 1)))))
                 (defn main [] (checks 11 22))")
        {:keys [envelope trust]} (signed source {:allow #{}})
        {:keys [trust options]} (execution-options trust)
        result (executor/execute envelope trust {:allow #{}} {:args []} options)]
    (is (= 4 (get-in result [:evidence :result]))
        "all four checks passed (1 each): field :a projects back the i64
         constructor argument unchanged, field :b likewise for its own
         (different) argument -- proving fields are not aliased or
         off-by-one -- and field :c (the :bool field) projects back TRUE
         when constructed with a literal `true` and FALSE when constructed
         with a literal `false`, through a REAL native process (not a
         JVM-side oracle-value check)")))

;; ADR 0062 fail-closed requirement: a record field type this native
;; increment does not admit (`:symbol`, disjoint from the native word field
;; profile) must be
;; rejected at COMPILE TIME with a clear error, never silently miscompiled.
;; The function's own declared result type is annotated `:symbol` (matching
;; the field it projects) so this negative vector exercises ONLY the
;; native-target record-field-type gate, not an unrelated generic
;; function-result type mismatch that would fire even before that gate is
;; reached.
(deftest native-record-with-an-unsupported-field-type-is-rejected-at-compile-time
  (let [schema (pr-str '[:record :native/symbol-field-record [[:s :symbol]]])
        source (str
                "(defn project-s [] :symbol
                   (record-get " schema " (record-new " schema " (symbol \"x\")) :s))
                 (defn main [] 0)")]
    (is (thrown-with-msg? clojure.lang.ExceptionInfo
                          #"qualified native"
                          (compiler/compile-source source (target))))
    ;; Confirms the rejection is native-specific admission, not a generic
    ;; type error: the identical source compiles fine on the Wasm target,
    ;; which already supports symbol-bearing records.
    (is (= :wasm/v1 (:format (compiler/compile-source source :wasm32-kotoba-v1))))))

;; Record SROA increment: a directly projected value-position `if` is the same
;; ordered SSA bundle as the one-let form in the shared ISA gate. Both branches
;; must construct the same exact scalar record; the verifier re-derives that
;; shape independently before each target re-emits it.
(deftest native-record-get-over-a-same-schema-scalar-if-emits-on-both-isas
  (let [schema (pr-str native-record-schema)
        source (str
                "(defn project-a [flag a b]
                   (record-get " schema "
                     (if (= flag 1)
                       (record-new " schema " a b true)
                       (record-new " schema " a b false))
                     :a))
                 (defn main [] 0)")]
    (doseq [native-target [:x86_64-kotoba-v1 :aarch64-kotoba-v1]]
      (let [artifact (:artifact (compiler/compile-source source native-target))]
        (is (seq (:code artifact)) (name native-target))
        (is (= :kotoba.kir/v4 (get-in artifact [:program :format]))
            (name native-target))))))

;; ADR 0063: the second native (x86-64/aarch64) value-representation
;; increment, immediately following ADR 0062's record -- a sealed variant
;; whose cases carry a bare `:i64`, a bare `:bool` (both `true` and `false`,
;; the SAME both-directions proof ADR 0062's own record `:bool` field
;; established), or nothing meaningfully read at all (a tag-only/"unit"-like
;; case whose branch body never references its own bound payload symbol --
;; see `native.scalar-variant-type?`'s own doc comment in `ir.cljc` for why
;; this ADR does not introduce a genuine zero-payload marker type). Real
;; native-process evidence matching every other deftest in this file: the
;; variant has NO independent runtime representation -- `(variant-match
;; schema (variant-new schema tag payload) branches)` is rewritten into TWO
;; synthetic stack slots (discriminant, payload) on the same `emit-let`/
;; `load-let` machinery this file's own `let`-sequencing deftests above
;; already prove correct, and dispatch is a REAL runtime compare-and-branch
;; chain over the stored discriminant, never a compile-time selection -- see
;; `emit-variant-dispatch` in both `backend/x86-64.cljc` and
;; `backend/aarch64.cljc`.
(def ^:private native-variant-schema
  '[:variant :native/traffic-signal [[:count :i64] [:enabled :bool] [:disabled :bool] [:idle :bool]]])

(deftest native-scalar-variant-construction-and-dispatch-round-trips-through-real-kexe-loader
  (let [schema (pr-str native-variant-schema)
        source (str
                "(defn check-count [n]
                   (variant-match " schema " (variant-new " schema " :count n)
                     [[:count v (if (= v n) 1 0)] [:enabled v 0] [:disabled v 0] [:idle v 0]]))
                 (defn check-enabled []
                   (variant-match " schema " (variant-new " schema " :enabled true)
                     [[:count v 0] [:enabled v (if v 1 0)] [:disabled v 0] [:idle v 0]]))
                 (defn check-disabled []
                   (variant-match " schema " (variant-new " schema " :disabled false)
                     [[:count v 0] [:enabled v 0] [:disabled v (if v 0 1)] [:idle v 0]]))
                 (defn check-idle []
                   (variant-match " schema " (variant-new " schema " :idle false)
                     [[:count v 0] [:enabled v 0] [:disabled v 0] [:idle v 1]]))
                 (defn main [] (+ (check-count 42) (+ (check-enabled) (+ (check-disabled) (check-idle)))))")
        {:keys [envelope trust]} (signed source {:allow #{}})
        {:keys [trust options]} (execution-options trust)
        result (executor/execute envelope trust {:allow #{}} {:args []} options)]
    (is (= 4 (get-in result [:evidence :result]))
        "all four checks passed (1 each): the :i64-payload case (:count)
         round-trips a genuinely runtime, parameter-derived value through
         construction+dispatch; the :bool-payload case round-trips TRUE
         (:enabled) and, separately, FALSE (:disabled); and the tag-only
         case (:idle) dispatches to the exact correct branch WITHOUT that
         branch ever reading its own bound payload symbol -- all four
         through a REAL native process (not a JVM-side oracle-value check),
         and each construction site emits the SAME full compare-and-branch
         chain over all four declared cases regardless of which one that
         particular site happens to construct (see `emit-variant-dispatch`'s
         own doc comment)")))

;; ADR 0063 fail-closed requirement (first vector, mirroring ADR 0062's own
;; first vector exactly): a variant case payload type this increment does
;; not admit (`:symbol`, disjoint from the native word payload profile) is
;; rejected at COMPILE TIME with the expected
;; native-admission error message, confirmed to be the native-specific gate
;; and not an unrelated generic type error by additionally confirming the
;; IDENTICAL source compiles successfully on `:wasm32-kotoba-v1` (whose
;; typed backend admits arbitrary typed values, including a symbol-cased
;; variant, unconditionally -- see `core.clj`'s own comment on why
;; `:wasm32-kotoba-v1`/`:js-kotoba-v1` need no content-based ir check at
;; all).
(deftest native-variant-with-an-unsupported-case-payload-type-is-rejected-at-compile-time
  (let [schema (pr-str '[:variant :native/symbol-case-variant [[:s :symbol]]])
        source (str
                "(defn project-s [] :symbol
                   (variant-match " schema " (variant-new " schema " :s (symbol \"x\")) [[:s v v]]))
                 (defn main [] 0)")]
    (is (thrown-with-msg? clojure.lang.ExceptionInfo
                          #"qualified native"
                          (compiler/compile-source source (target))))
    (is (= :wasm/v1 (:format (compiler/compile-source source :wasm32-kotoba-v1))))))

;; ADR 0229 closes ADR 0063's local computed-value gap. A same-schema scalar
;; variant IF is now a tag/payload SSA bundle and reaches both production ISAs.
(deftest native-variant-match-over-a-same-schema-scalar-if-emits-on-both-isas
  (let [schema (pr-str native-variant-schema)
        source (str
                "(defn project [flag n]
                   (variant-match " schema "
                     (if (= flag 1)
                       (variant-new " schema " :count n)
                       (variant-new " schema " :count n))
                     [[:count v v] [:enabled v 0] [:disabled v 0] [:idle v 0]]))
                 (defn main [] 0)")]
    (doseq [native-target [:x86_64-kotoba-v1 :aarch64-kotoba-v1]]
      (let [artifact (:artifact (compiler/compile-source source native-target))]
        (is (seq (:code artifact)) (name native-target))
        (is (= :kotoba.kir/v4 (get-in artifact [:program :format]))
            (name native-target))))))

;; ADR 0063 fail-closed requirement (third vector -- REAL native-process
;; trap evidence, not just a compile-time rejection): an out-of-range/
;; unrecognized variant discriminant must never silently do something
;; undefined. Reading `emit-variant-dispatch`'s own doc comment: this
;; repository's own pipeline provably CANNOT ever produce such a value --
;; frontend's shared, unchanged `variant-new` grammar rejects an undeclared
;; tag at compile time (`infer-expression-type`'s existing "variant
;; constructor tag is not declared" check); this backend's own codegen
;; independently re-derives the tag-to-ordinal lookup a second time and
;; throws if it does not resolve; `kotoba.verifier`'s OWN
;; independent re-derivation (the new `variant-new`/`variant-match` cases in
;; `verify-expr!` added by this ADR) enforces the identical narrow shape a
;; THIRD time; and -- unique to this repository's native track -- BOTH
;; `kotoba.verifier.signing/sign` and `signing/verify` unconditionally
;; re-run `verifier/verify-artifact!` (confirmed by reading `signing.clj`),
;; and `signing/verify` runs on EVERY execution (`native-executor/execute`
;; calls it, not just once at compile time) -- so there is no way, at any
;; layer, INCLUDING a hand-crafted artifact that bypasses `sema/analyze`
;; entirely, to reach real `kexe-loader` execution with a variant
;; discriminant the type system did not itself validate as a declared
;; case's ordinal.
;;
;; Given that, this deftest does not attempt to smuggle a bad discriminant
;; through the compile/sign/execute pipeline (that pipeline's own defense in
;; depth makes it impossible by design, which is itself the point). Instead
;; it directly exercises `emit-variant-dispatch`'s own defensive UD2/BRK
;; fallback -- present in the compiled machine code as insurance, matching
;; this codebase's own `kernel-load-u8`/`kgraph-entity-at` defense-in-depth
;; style and the WASM Component Model track's own `variant-wat` discriminant
;; range check -- by calling the PRIVATE dispatch primitive directly (the
;; SAME technique this file already uses for other internals, e.g.
;; `@#'executor/run-process` above) with a literal ordinal (99) no admitted
;; `.kotoba` program could ever produce for a 3-case dispatch, wraps the
;; result in a minimal hand-assembled function (bypassing `emit-function`/
;; `emit-program`/`sema/analyze`/`verifier/verify-artifact!` entirely),
;; and runs the resulting bytes through the SAME measured, real `kexe-
;; loader` native process every other deftest in this file uses -- proving
;; the fallback trap is REAL, present, byte-correct machine code, not merely
;; a code comment's claim.
(defn- raw-out-of-range-dispatch-code []
  (if (= (target) :aarch64-kotoba-v1)
    (let [emit-variant-dispatch (deref #'aarch64/emit-variant-dispatch)
          fuel-charge (deref #'aarch64/fuel-charge)
          insn (deref #'aarch64/insn)
          branch-specs [{:binder '_a :body 10} {:binder '_b :body 20} {:binder '_c :body 30}]
          body (emit-variant-dispatch 99 0 branch-specs {} 0)]
      ;; Mirrors `emit-function`'s own n=0-parameter prologue/epilogue
      ;; exactly (register-frame = 16*(quot 1 2) = 0, so no save/restore
      ;; frame at all): fuel-charge; stp fp,lr,[sp,#-16]!; mov fp,sp; <body>;
      ;; ldp fp,lr,[sp],#16; ret.
      (vec (concat fuel-charge (insn 0xa9bf7bfd) (insn 0x910003fd)
                   body
                   (insn 0xa8c17bfd) (insn 0xd65f03c0))))
    (let [emit-variant-dispatch (deref #'x86-64/emit-variant-dispatch)
          fuel-charge (deref #'x86-64/fuel-charge)
          le32 (deref #'x86-64/le32)
          branch-specs [{:binder '_a :body 10} {:binder '_b :body 20} {:binder '_c :body 30}]
          body (emit-variant-dispatch 99 0 branch-specs {}
                                      {:param-count 0 :pad? true :temp-depth 0
                                       :function-name 'raw-dispatch-trap :tail? true})]
      ;; Mirrors `emit-function`'s own n=0-parameter prologue/epilogue
      ;; exactly (pad? = (even? 0) = true, frame-bytes = 8*(0+1) = 8):
      ;; fuel-charge; push rax (alignment padding); <body>; add rsp,8; ret.
      (vec (concat fuel-charge [0x50] body [0x48 0x81 0xc4] (le32 8) [0xc3])))))

(deftest variant-dispatch-fallback-traps-on-a-discriminant-no-admitted-program-can-ever-produce
  (let [{:keys [loader-path]} @measured-runtime
        host-os ((deref #'executor/host-os))
        run-process (deref #'executor/run-process)
        runtime-environment (deref #'executor/runtime-environment)
        delete-tree! (deref #'executor/delete-tree!)
        isa (if (= (target) :aarch64-kotoba-v1) "aarch64" "x86_64")
        code (raw-out-of-range-dispatch-code)
        directory (java.nio.file.Files/createTempDirectory
                   "kotoba-raw-native-" (make-array java.nio.file.attribute.FileAttribute 0))
        code-file (java.io.File. (.toFile directory) "program.bin")]
    (try
      (atomic-output/write-bytes! (.getPath code-file) (byte-array (map unchecked-byte code)))
      (let [command [loader-path (.getPath code-file) "0" "0" isa "-"]
            process (run-process command (runtime-environment host-os)
                                 {:timeout-ms 5000 :output-limit 65536})
            report (edn/read-string (str/trim (:stdout process)))]
        (is (= :trap (:status report))
            "the dispatch chain's defensive fallback (UD2 on x86-64, BRK on
             aarch64) fired as real, executed machine code for a
             discriminant (99) outside the declared [0,3) case range --
             fail-closed, not silently undefined -- confirmed via the SAME
             real `kexe-loader` native process every other deftest in this
             file uses"))
      (finally (delete-tree! (.toFile directory))))))

;; string-substring's general form (host callback at context offset 136).
;; The all-ASCII-literal case compiles to pure pair arithmetic and never
;; reaches the host, so these deliberately use shapes it cannot claim: a
;; concat result (string_pool-backed, NEGATIVE offset, where advancing by
;; `start` bytes SUBTRACTS) and a non-ASCII literal (code+literal-data
;; backed, positive offset, where it adds).
(deftest general-string-substring-executes-through-real-native-loader
  (let [{:keys [envelope trust]}
        (signed (str "(defn main [] (string-byte-length"
                     " (string-substring (string-concat \"ab\" \"cde\") 1 4)))")
                {:allow #{}})
        {:keys [trust options]} (execution-options trust)
        result (executor/execute envelope trust {:allow #{}} {:args []} options)]
    (is (= {:status :ok :result 3}
           (select-keys (:evidence result) [:status :result])))))

(deftest general-string-substring-preserves-content-over-pool-backed-source
  (let [{:keys [envelope trust]}
        (signed (str "(defn main [] (if (string=?"
                     " (string-substring (string-concat \"日本\" \"語\") 3 9)"
                     " \"本語\") 1 0))")
                {:allow #{}})
        {:keys [trust options]} (execution-options trust)
        result (executor/execute envelope trust {:allow #{}} {:args []} options)]
    (is (= {:status :ok :result 1}
           (select-keys (:evidence result) [:status :result])))))

(deftest general-string-substring-preserves-content-over-literal-source
  (let [{:keys [envelope trust]}
        (signed (str "(defn main [] (if (string=?"
                     " (string-substring \"日本語\" 3 9) \"本語\") 1 0))")
                {:allow #{}})
        {:keys [trust options]} (execution-options trust)
        result (executor/execute envelope trust {:allow #{}} {:args []} options)]
    (is (= {:status :ok :result 1}
           (select-keys (:evidence result) [:status :result])))))

;; The shared oracle kotoba.kir.value/utf8-substring! rejects an index that
;; splits a code point. The loader must too, rather than silently returning a
;; handle to a partial code point -- that would be a string value whose bytes
;; are not canonical UTF-8.
(deftest constant-string-substring-splitting-a-code-point-is-rejected-at-compile-time
  (is (thrown-with-msg?
       clojure.lang.ExceptionInfo #"splits a UTF-8 code point"
       (compiler/compile-source
        "(defn main [] (string-byte-length (string-substring \"日本語\" 1 9)))"
        (target) {:allow #{}}))))

;; There is deliberately no test that reaches the loader's boundary check at
;; run time, because from this compiler no artifact can. The entry takes zero
;; arguments ("main must take zero arguments"), and compilation evaluates the
;; entry with the shared oracle before emitting -- an index that splits a code
;; point therefore always fails at compile time, as the test above shows, and
;; there is no input left that the compiler cannot decide. The loader checks
;; anyway for the same reason checked_string_concat rules out overflow: it does
;; not trust what a guest put in a pair cell, and an artifact need not have
;; come from this compiler. Attempts to reach it from here were tried and are
;; recorded so they are not retried: a recursive index is still evaluated by
;; the oracle, and passing :args to a zero-arity entry is rejected as an
;; entry-arity error before execution.

;; string-code-point-at (host callback at context offset 144). The oracle
;; evaluates constant operands but does not replace the expression, so these
;; still reach the loader -- which is how the probe that found this gap saw
;; "operation not implemented on this backend" for a fully constant program.
(deftest string-code-point-at-executes-through-real-native-loader
  (let [{:keys [envelope trust]}
        (signed "(defn main [] (string-code-point-at \"abc\" 1))" {:allow #{}})
        {:keys [trust options]} (execution-options trust)
        result (executor/execute envelope trust {:allow #{}} {:args []} options)]
    (is (= {:status :ok :result 98}
           (select-keys (:evidence result) [:status :result])))))

;; U+672C. A three-byte sequence exercises the decode path, not just the ASCII
;; short-circuit, and offset 3 is the boundary after 日 (also three bytes).
(deftest string-code-point-at-decodes-a-multi-byte-sequence-on-native
  (let [{:keys [envelope trust]}
        (signed "(defn main [] (string-code-point-at \"日本語\" 3))" {:allow #{}})
        {:keys [trust options]} (execution-options trust)
        result (executor/execute envelope trust {:allow #{}} {:args []} options)]
    (is (= {:status :ok :result 26412}
           (select-keys (:evidence result) [:status :result])))))

;; Pool-backed source (negative offset), where resolve_string_bytes takes the
;; other half of the offset space.
(deftest string-code-point-at-reads-a-pool-backed-string-on-native
  (let [{:keys [envelope trust]}
        (signed (str "(defn main [] (string-code-point-at"
                     " (string-concat \"日\" \"本\") 3))")
                {:allow #{}})
        {:keys [trust options]} (execution-options trust)
        result (executor/execute envelope trust {:allow #{}} {:args []} options)]
    (is (= {:status :ok :result 26412}
           (select-keys (:evidence result) [:status :result])))))

(deftest string-code-point-at-splitting-a-code-point-is-rejected-at-compile-time
  (is (thrown-with-msg?
       clojure.lang.ExceptionInfo #"splits a UTF-8 code point"
       (compiler/compile-source "(defn main [] (string-code-point-at \"日本語\" 1))"
                                (target) {:allow #{}}))))

;; f64 comparisons on native. The bit patterns are 1.0, 2.0 and a quiet NaN;
;; the NaN rows are the point of the test, because the naive encodings
;; (`setb`/`setbe` on x86-64, `LT`/`LE` on aarch64) are TRUE when a compare is
;; unordered and would pass every ordered row here while being wrong.
(def ^:private f64-one 4607182418800017408)      ; 0x3ff0000000000000
(def ^:private f64-two 4611686018427387904)      ; 0x4000000000000000
(def ^:private f64-nan 9221120237041090560)      ; 0x7ff8000000000000

(defn- f64-compare-result [op a b]
  (let [{:keys [envelope trust]}
        (signed (str "(defn main [] (if (" op " (f64-from-bits " a ")"
                     " (f64-from-bits " b ")) 1 0))")
                {:allow #{}})
        {:keys [trust options]} (execution-options trust)]
    (:evidence (executor/execute envelope trust {:allow #{}} {:args []} options))))

(deftest f64-comparisons-execute-with-ieee-semantics-on-native
  (doseq [[op a b expected]
          [["f64-lt" f64-one f64-two 1] ["f64-lt" f64-two f64-one 0]
           ["f64-gt" f64-two f64-one 1] ["f64-gt" f64-one f64-two 0]
           ["f64-le" f64-two f64-two 1] ["f64-le" f64-two f64-one 0]
           ["f64-ge" f64-two f64-two 1] ["f64-ge" f64-one f64-two 0]
           ["f64-eq" f64-one f64-one 1] ["f64-eq" f64-one f64-two 0]
           ;; NaN is equal to nothing, ordered against nothing, unordered
           ;; with everything -- including itself.
           ["f64-eq" f64-nan f64-nan 0]
           ["f64-lt" f64-nan f64-one 0] ["f64-lt" f64-one f64-nan 0]
           ["f64-gt" f64-nan f64-one 0] ["f64-le" f64-nan f64-one 0]
           ["f64-ge" f64-nan f64-one 0]
           ["f64-unordered" f64-nan f64-one 1]
           ["f64-unordered" f64-nan f64-nan 1]
           ["f64-unordered" f64-one f64-two 0]]]
    (is (= {:status :ok :result expected}
           (select-keys (f64-compare-result op a b) [:status :result]))
        (str op " " a " " b))))

;; ---------------------------------------------------------------------------
;; Context ABI v4: vector-alloc (offset 200) and vector-assoc! (offset 208)
;; ---------------------------------------------------------------------------
;;
;; Two operations `kotoba-kir` has declared and `only-native-word-typed-
;; features?` has admitted since kotoba-kir b6bfe23, with nothing on native to
;; emit them and no host slot to call. Superproject ADR-2609010200.
;;
;; ## Why the third deftest is the one that pins the LOWERING
;;
;; A copy and an in-place write are INDISTINGUISHABLE on a handle the caller
;; has proved dead afterwards. That is the whole argument for admitting
;; `vector-assoc!`, and the KIR interpreter refuses to tell them apart for
;; exactly that reason -- so the round-trip deftest below would return the
;; same answer if `vector-assoc!` were lowered to the copying slot at 184. It
;; pins correctness, not the lowering.
;;
;; What DOES separate them is the arena, and it separates them at a number
;; this file can compute in advance. The element arena is bump-only and never
;; reclaimed (`KEXE_VECTOR_ITEM_CAPACITY` 65536 words), so a copying update
;; caps a vector's whole-program write count at `(capacity - length) / length`.
;; For a 256-slot vector that is exactly 255 writes. The in-place store
;; allocates nothing, so its count is not bounded by the arena at all.
;;
;; So: same program, same numbers, one head changed. 300 writes over 256 slots
;; is `:ok` through `vector-assoc!` and a trap through `vector-assoc`.

(def ^:private slab-source
  "The shape a struct of arrays actually writes: a vector threaded through a
  tail-recursive parameter, read in the base case and consumed in the step.
  `%s` is the update head, the only thing that differs between the two runs.

  `go` is not exported, which is what lets it take a `:vector-i64` at all --
  a vector handle is one machine word at an internal call boundary and is
  deliberately not a host ABI (`native-private-handle-type?`)."
  "(ns pilot.native-slab (:export [fill]))
   (defn go [items :vector-i64 i :i64 n :i64] :i64
     (if (>= i n)
       (vector-at items 0)
       (go (%s items 0 i) (+ i 1) n)))
   (defn fill [length :i64 n :i64] :i64
     (go (vector-alloc length) 0 n))")

(defn- run-slab [head length writes]
  (let [{:keys [envelope trust]} (signed (format slab-source head) {:allow #{}})
        {:keys [trust options]} (execution-options trust)]
    (executor/execute envelope trust {:allow #{}} {:args [length writes]}
                      (assoc options :entry 'fill))))

(deftest native-vector-alloc-and-in-place-write-round-trip-through-real-kexe-loader
  (let [{:keys [envelope trust]}
        (signed "(ns pilot.native-slab (:export [write-and-read]))
                 (defn write-and-read [slots :i64 index :i64 value :i64] :i64
                   (let [fresh (vector-alloc slots)
                         filled (vector-assoc! fresh index value)]
                     (+ (vector-at filled index) (vector-count filled))))"
                {:allow #{}})
        {:keys [trust options]} (execution-options trust)
        result (executor/execute envelope trust {:allow #{}} {:args [8 5 41]}
                                 (assoc options :entry 'write-and-read))]
    ;; 41 written into slot 5 of an 8-slot allocation, read back, plus the
    ;; count. Predicted before running: 41 + 8 = 49.
    (is (= {:status :ok :result 49}
           (select-keys (:evidence result) [:status :result])))))

(deftest native-vector-alloc-zeroes-the-slots-it-allocates
  ;; The store writes ONE word, not a region: every slot the write did not
  ;; name still holds the zero `vector-alloc` put there.
  (let [{:keys [envelope trust]}
        (signed "(ns pilot.native-slab (:export [neighbour]))
                 (defn neighbour [slots :i64 written :i64 read :i64] :i64
                   (let [fresh (vector-alloc slots)
                         filled (vector-assoc! fresh written 41)]
                     (vector-at filled read)))"
                {:allow #{}})
        {:keys [trust options]} (execution-options trust)
        at (fn [written read]
             (select-keys (:evidence (executor/execute
                                      envelope trust {:allow #{}}
                                      {:args [8 written read]}
                                      (assoc options :entry 'neighbour)))
                          [:status :result]))]
    (is (= {:status :ok :result 41} (at 5 5)) "the slot that was written")
    (doseq [read [0 4 6 7]]
      (is (= {:status :ok :result 0} (at 5 read))
          (str "slot " read " beside the written one is still zero")))))

(deftest the-in-place-store-is-what-lets-a-slab-be-written-more-than-the-arena-allows
  ;; 255 = (65536 - 256) / 256, the copying update's whole-program write
  ;; budget for a 256-slot vector. 300 is past it on purpose.
  (let [in-place (run-slab "vector-assoc!" 256 300)
        copying (run-slab "vector-assoc" 256 300)]
    (is (= {:status :ok :result 299}
           (select-keys (:evidence in-place) [:status :result]))
        "300 in-place writes finish, and the last one is what index 0 reads")
    (is (= :trap (get-in copying [:report :status]))
        "the same 300 writes exhaust the element arena when each one copies")
    ;; Not a fuel difference. Both runs charge the same iterations, and the
    ;; copying run stops with MORE fuel left than the run that completed --
    ;; it ran out of arena, not out of budget. Stated because "it trapped"
    ;; would otherwise be consistent with the loop simply being too long.
    (is (pos? (get-in copying [:report :fuel :remaining]))
        "the copying run trapped with fuel remaining, so this is the arena")
    (is (< (get-in in-place [:report :fuel :remaining])
           (get-in copying [:report :fuel :remaining]))
        "and it stopped EARLIER than the run that completed")))

(deftest the-affine-gate-refuses-an-in-place-write-to-a-handle-that-is-read-after
  ;; The claim the bang makes is checked, not assumed. Here the handle written
  ;; in place is read again afterwards, which is precisely the program an
  ;; in-place store would corrupt -- so it is refused at compile time rather
  ;; than lowered to the copying slot as a silent fallback.
  (is (thrown-with-msg?
       clojure.lang.ExceptionInfo #"vector-assoc! requires a linear handle"
       (compiler/compile-source
        "(ns pilot.native-slab (:export [leak]))
         (defn leak [slots :i64] :i64
           (let [fresh (vector-alloc slots)
                 filled (vector-assoc! fresh 0 7)]
             (+ (vector-at fresh 0) (vector-at filled 0))))"
        (target) {:allow #{}}))))

;; The host bound is the only one that can answer here. `n` arrives as an
;; entry ARGUMENT, so the compile-time KIR oracle -- which refuses a literal
;; `(vector-alloc 20000)` with `:vector-alloc-out-of-range` before any code is
;; emitted -- has nothing to fold, and `checked_vector_alloc`'s own
;; re-derivation of `vector-item-limit` is what decides. That re-derivation is
;; the thing being tested: 16384 is the limit, so 16384 must be ADMITTED and
;; 16385 refused. A bound checked with `>=` instead of `>` passes every
;; too-large case and still refuses one program that should run.
(deftest native-vector-alloc-fails-closed-at-the-item-limit-the-host-re-derives
  (let [{:keys [envelope trust]}
        (signed "(ns pilot.native-slab (:export [alloc-count]))
                 (defn alloc-count [n :i64] :i64 (vector-count (vector-alloc n)))"
                {:allow #{}})
        {:keys [trust options]} (execution-options trust)
        run (fn [n] (executor/execute envelope trust {:allow #{}} {:args [n]}
                                      (assoc options :entry 'alloc-count)))]
    (is (= {:status :ok :result 0} (select-keys (:evidence (run 0)) [:status :result]))
        "zero slots is a real handle over an empty slice, not an error")
    (is (= {:status :ok :result 16384}
           (select-keys (:evidence (run 16384)) [:status :result]))
        "the limit itself is admitted -- an off-by-one here refuses a legal program")
    (is (= :trap (get-in (run 16385) [:report :status]))
        "one past the limit is refused by the host, not by the oracle")
    (is (= :trap (get-in (run -1) [:report :status]))
        "a negative count is refused before it is widened to a length")))
