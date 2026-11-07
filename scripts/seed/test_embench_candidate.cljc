;; Synthetic observer-format controls, never native benchmark qualification.
;; Ported from test_embench_candidate.py. Run from the repo root:
;;   PYTHONPATH=scripts/seed basilisp test -p no:cacheprovider --rootdir scripts/seed scripts/seed/test_embench_candidate.cljc
(ns test-embench-candidate
  (:require [basilisp.test :refer [deftest is]]
            [embench-candidate-lib]
            [gate-util :as u])
  (:import operator pathlib tempfile))

(def entry-offset embench-candidate-lib/entry-offset)
(def arena embench-candidate-lib/arena)
(def fields embench-candidate-lib/fields)
(def verify-bundle-data embench-candidate-lib/verify-bundle-data)

(defmacro with-payload [[payload] & body]
  `(with-open [temp# (tempfile/TemporaryDirectory)]
     (let [~payload (.joinpath (pathlib/Path temp#) "payload.bin")]
       (.write_bytes ~payload (u/bytes-of-n 8 0))
       ~@body)))

(defn header [payload & {:keys [offset length arity] :or {offset 4 length 8 arity 0}}]
  (.encode (str "{:ok true, :output \"" payload "\", :offset " offset ", :length " length ", :arity " arity "}\n")))

(deftest nonzero-reported-entry-is-preserved
  (with-payload [payload]
    (is (= 4 (entry-offset (header payload) payload)))
    (is (= 0 (entry-offset (header payload :offset 0) payload)))))

(deftest invalid-entry-report-refuses
  (with-payload [payload]
    (doseq [raw [(header payload :offset 2) (header payload :offset 8) (header payload :length 9) (header payload :arity 1)
                 (operator/mul (header payload) 2) (.replace (header payload) (.encode "payload.bin") (.encode "other.bin"))]]
      (is (thrown? python/AssertionError (entry-offset raw payload)) (str raw)))))

(deftest all17-counters-are-required-in-canonical-order
  (let [raw (operator/add (operator/add (.encode "KEXE_ARENA_USE {") (.join (.encode " ") (python/list (for [f fields] (.encode (str ":" f " 0"))))))
                          (.encode "}\n"))]
    (is (u/deq (u/pydict-from (for [f fields] [f 0])) (arena raw)))
    (doseq [bad [(operator/add raw raw) (.replace raw (.encode ":pairs 0 ") (.encode "")) (.replace raw (.encode ":pairs 0") (.encode ":pairs -1"))
                 (.replace raw (.encode ":pairs 0 :string-pool-bytes 0") (.encode ":string-pool-bytes 0 :pairs 0"))
                 (operator/add raw (.encode "unexpected\n"))]]
      (is (nil? (arena bad)) (str bad)))))

(deftest canonical-source-count-and-reference-tables-match-frozen-hashes
  (verify-bundle-data (.joinpath u/root "bench/embench/reproduce-20261015") (.joinpath u/root "bench/embench/proof-v1/native-entry.kotoba")))

(deftest modified-entry-template-refuses
  (with-open [temp (tempfile/TemporaryDirectory)]
    (let [entry (.joinpath (pathlib/Path temp) "entry.kotoba")]
      (.write_bytes entry (operator/add (.read_bytes (.joinpath u/root "bench/embench/proof-v1/native-entry.kotoba")) (.encode " ")))
      (is (thrown? python/AssertionError (verify-bundle-data (.joinpath u/root "bench/embench/reproduce-20261015") entry))))))
