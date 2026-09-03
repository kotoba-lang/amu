(ns kotoba.compiler.fuel64-ceiling-test
  "fuel64: amu is where the fuel ceiling's four statements can actually be
  compared, so this is where they are.

  The number lives in `kotoba.kir/max-fuel` and is RESTATED in three other
  places, each for a reason that is not laziness:

    `kotoba.native.elf64/max-object-fuel`   the packager must not pull the
                                            interpreter onto the JVM-free
                                            packaging path for one integer
    `kotoba.verifier` (`max-native-fuel`)   reads it (a ceiling is not a set,
                                            see that file)
    `kotoba.compiler.nbb.cli`               same, on the Node route

  Only two of those are on any single classpath at once -- the packager and
  the interpreter never meet in kotoba-native, and the verifier never loads
  the packager's object route. amu loads all of them. A restatement nobody
  compares is a copy, and a copy drifts; this is the comparison.

  The failure this prevents is not hypothetical in shape. kotoba-native's
  `elf64_twin_parity_test` exists because the SAME table in two files of ONE
  repository drifted in both directions and shipped that way, and the symptom
  was an aiueos object taking an unexpected vector 6 that read as a protocol
  bug."
  (:require [clojure.test :refer [deftest is testing]]
            [kotoba.kir :as ir]
            [kotoba.native.elf64 :as elf64]
            [kotoba.verifier]))

(deftest every-statement-of-the-ceiling-is-the-same-number
  (is (= 9007199254740991 ir/max-fuel)
      "kotoba.kir decides it")
  (is (= ir/max-fuel elf64/max-object-fuel)
      "kotoba-native's packager restates it; a drift here means the packager
       writes a tier the oracle cannot count, or refuses one it can")
  (is (= ir/max-fuel @#'kotoba.verifier/max-native-fuel)
      "kotoba-verifier reads it")
  (testing "and it is Number.MAX_SAFE_INTEGER, which is the whole argument"
    (is (= ir/max-fuel (dec (long (Math/pow 2 53)))))))

;; The JVM-free route's own bound is `Number.isSafeInteger`, which cannot be
;; called from here. What CAN be checked from here is that the constant it
;; multiplies against is the same one -- the cljs file is read as text for the
;; same reason `elf64_twin_parity_test` reads its two files as text: no JVM
;; can load it.
(deftest the-jvm-free-route-names-the-same-source
  (let [text (slurp "src/kotoba/compiler/nbb/cli.cljs")]
    (is (re-find #"\(def \^:private max-native-fuel ir/max-fuel\)" text)
        "kotoba.compiler.nbb.cli must read the ceiling rather than carry a literal")
    (is (nil? (re-find #"max-native-fuel 1048576" text))
        "the 2^20 literal must not come back")))
