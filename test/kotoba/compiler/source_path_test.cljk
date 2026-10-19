(ns kotoba.compiler.source-path-test
  (:require #?(:clj  [clojure.test :refer [deftest is testing]]
               :cljs [cljs.test :refer [deftest is testing] :include-macros true])
            [kotoba.compiler.source-path :as source-path]))

(deftest source-extensions-select-discovery-not-runtime
  (is (= :kotoba (source-path/source-kind "safe.kotoba")))
  (is (= :clj-kotoba (source-path/source-kind "safe.cljk")))
  (is (= :portable-common (source-path/source-kind "safe.cljc")))
  (doseq [path ["safe.kotoba" "safe.cljk" "safe.cljc"]]
    (testing path (is (= path (source-path/admit! path)))))
  (is (nil? (source-path/source-kind "unsafe.clj")))
  (is (thrown-with-msg? #?(:clj clojure.lang.ExceptionInfo :cljs ExceptionInfo)
                        #"\.kotoba, \.cljk, or \.cljc"
                        (source-path/admit! "unsafe.cljs"))))

(defn- refusal
  "The ex-data of a refusal, or `:admitted` if the call answered instead."
  [value path]
  (try (do (source-path/admit-native-artifact! value path) :admitted)
       (catch #?(:clj clojure.lang.ExceptionInfo :cljs :default) error
         (ex-data error))))

(deftest extract-native-refuses-a-source-file-with-the-reason-it-decided
  ;; The phase is the assertion. Before `admit-native-artifact!` existed, all
  ;; four inputs below reached `verify-artifact!`/`get` and died on a protocol
  ;; error carrying no `:phase`, which the CLI maps to `:internal` -- exit 70,
  ;; "internal compiler error", the code reserved for the compiler breaking.
  ;; Measured 2026-09-09 with this function reverted:
  ;;   amu extract-native one-form.kotoba --symbol main
  ;;   => {:error :internal, :message "internal compiler error"}   exit 70
  ;; and with it:
  ;;   => {:error :decode,
  ;;       :message "extract-native reads a compiled artifact, not a source file"}
  ;;      exit 65
  (testing "a source path is refused by its extension, which is a closed contract"
    (doseq [path ["app.kotoba" "app.cljk" "app.cljc"]]
      (let [data (refusal {:exports {} :code []} path)]
        (testing path
          (is (= :decode (:phase data)))
          (is (= (source-path/source-kind path) (:source-kind data)))))))
  (testing "a non-map input is refused by shape"
    (is (= :decode (:phase (refusal '(ns m) "artifact.kexe"))))
    (is (= :decode (:phase (refusal "not edn" "artifact.kexe")))))
  (testing "a map without the keys extract-native reads is refused by name"
    (let [data (refusal {:target :aarch64-macos-kotoba-v1} "artifact.kexe")]
      (is (= :decode (:phase data)))
      (is (= [:exports :code] (:missing data)))))
  (testing "and an artifact-shaped value is admitted, unchanged"
    ;; Without this the three refusals above are also satisfied by a function
    ;; that refuses everything.
    (let [artifact {:exports {'main {:offset 0 :length 4 :arity 0}} :code [0 1 2 3]}]
      (is (= artifact (source-path/admit-native-artifact! artifact "artifact.kexe"))))))
