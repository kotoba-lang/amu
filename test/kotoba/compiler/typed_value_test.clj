(ns kotoba.compiler.typed-value-test
  (:require [clojure.test :refer [deftest is]]
            [kotoba.compiler.frontend :as frontend]
            [kotoba.compiler.ir :as ir]
            [kotoba.compiler.value :as value]))

(def typed-source
  (str "(ns pilot.text (:export [greet byte-length same?])) "
       "(defn greet [name :string] :string (string-concat \"こんにちは、\" name)) "
       "(defn byte-length [value :string] (string-byte-length value)) "
       "(defn same? [left :string right :string] (string=? left right))"))

(deftest typed-values-run-through-checked-kir
  (let [kir (ir/lower (frontend/analyze typed-source))]
    (is (= :kotoba.kir/v4 (:format kir)))
    (is (= "こんにちは、言葉" (ir/execute kir 'greet ["言葉"])))
    (is (= 6 (ir/execute kir 'byte-length ["言葉"])))
    (is (thrown? clojure.lang.ExceptionInfo (ir/execute kir 'greet [1])))
    (is (thrown? clojure.lang.ExceptionInfo
                 (ir/execute kir 'greet [(apply str (repeat 65537 "x"))])))))

(deftest utf8-bounds-reject-malformed-unicode
  (is (= 4 (value/utf8-byte-count! "😀")))
  (is (thrown? clojure.lang.ExceptionInfo
               (value/utf8-byte-count! (String. (char-array [(char 0xd800)]))))))
