(ns kotoba.compiler.test-profile-test
  (:require [clojure.test :refer [deftest is]]
            [kotoba.compiler.test-profile :as profile]))

(def source
  "(ns test.portable
     (:capabilities #{:http/post})
     (:export [test-handler test-pure test-ability]))
   (defn test-handler [cap-id value]
     (if (= cap-id 4) (+ value 1) 0))
   (defn test-pure [] (if (= (+ 20 22) 42) 1 0))
   (defn test-ability [] (if (= (cap-call :http/post 41) 42) 1 0))")

(deftest one-kotoba-test-source-runs-on-every-target
  (let [report (profile/run-source source)]
    (is (:ok report) (pr-str (:failed report)))
    (is (= ['test-pure 'test-ability] (:tests report)))
    (is (= #{:jvm-kir :js :wasm} (set (keys (:results report)))))
    (is (re-matches #"[0-9a-f]{64}" (:test-definition-cid report)))))
