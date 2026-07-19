(ns kotoba.compiler.component-abi-test
  (:require [clojure.test :refer [deftest is]]
            [kotoba.compiler.component-abi :as component-abi]))

(deftest bounded-transport-components-validate
  (is (= [] (component-abi/validate-component
             #:component{:imports '[transport-connect tls-open transport-write
                                    transport-read transport-close]
                         :exports '[http-open http-write http-read http-close]})))
  (is (= :net/connect
         (:capability (component-abi/operation 'transport-connect))))
  (is (= :i64 (:result (component-abi/operation 'tls-open)))))

(deftest high-level-component-imports-and-link-graph-validate
  (is (= [] (component-abi/validate-component
             #:component{:imports '[http-open http-write http-read http-close]
                         :exports '[main]})))
  (is (= []
         (component-abi/validate-link-graph
          {:components
           {:app #:component{:imports '[http-open] :exports '[main]}
            :http #:component{:imports '[transport-connect tls-open]
                              :exports '[http-open]}}
           :links [{:consumer :app :import 'http-open
                    :provider :http :export 'http-open}]})))
  (is (seq
       (component-abi/validate-link-graph
        {:components
         {:app #:component{:imports '[http-open] :exports '[main]}
          :http #:component{:imports '[] :exports '[http-open]}}
         :links []}))))

(deftest ambient-native-authority-is-not-an-import
  (let [problems (component-abi/validate-component
                  #:component{:imports '[transport-connect syscall]
                              :exports '[main]})]
    (is (some #(= :unknown-component-imports (:problem %)) problems))
    (is (some #(= :ambient-native-authority (:problem %)) problems))))
