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
