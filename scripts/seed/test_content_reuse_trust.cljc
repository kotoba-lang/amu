;; The orchestration cache must not turn untrusted bytes into a verdict. Ported from test_content_reuse_trust.py
;; (Basilisp, JUN-974) against content_reuse.cljc.
;; Run: PYTHONPATH=scripts/seed basilisp test --rootdir scripts/seed scripts/seed/test_content_reuse_trust.cljc
(ns test-content-reuse-trust
  (:require [basilisp.test :refer [deftest is]]
            [content-reuse :as cr]
            [gate-util :as u])
  (:import json operator pathlib tempfile))

(defn with-tmp [f]
  (let [d (tempfile/TemporaryDirectory)
        name (.__enter__ d)]
    (try (f (pathlib/Path name)) (finally (.__exit__ d nil nil nil)))))

(defn producer [root]
  (let [script (pathlib/Path root "producer.sh")]
    (.write_text script "printf fresh > \"$1\"\nprintf executed\n")
    script))

(deftest store-does-not-publish-process-verdict-or-streams
  (with-tmp
    (fn [root]
      (let [out (pathlib/Path root "out") store (pathlib/Path root "store")
            script (producer root) output (pathlib/Path out "image")]
        (.mkdir out)
        (let [runner (cr/runs out nil store)]
          (cr/run-cached runner "compile" ["/bin/sh" script output] (python/dict) [output])
          (let [entry (first (python/list (.iterdir store)))]
            (is (= (set (map #(.-name %) (python/list (.iterdir entry)))) #{"image" "record.json"}))
            (is (not (operator/contains (json/loads (.read_text (pathlib/Path entry "record.json"))) "exit")))
            (is (u/deq (.read_bytes (pathlib/Path out "raw/compile.stdout")) (.encode "executed")))))))))

(deftest forged-record-and-rewritten-hash-do-not-replace-execution
  (with-tmp
    (fn [root]
      (let [out (pathlib/Path root "out") store (pathlib/Path root "store")
            script (producer root) output (pathlib/Path out "image")
            argv ["/bin/sh" script output]]
        (.mkdir out)
        (.mkdir store)
        (let [runner (cr/runs out store nil)
              material (cr/key-material runner argv (python/dict) [output])
              key (u/sha256-hex (.encode (json/dumps material ** :sort_keys true)))
              entry (pathlib/Path store key)]
          (.mkdir entry)
          (.write_bytes (pathlib/Path entry "image") (.encode "forged"))
          (.write_bytes (pathlib/Path entry "stdout") (.encode "forged success"))
          (.write_bytes (pathlib/Path entry "stderr") (u/bytes-of))
          (.write_text (pathlib/Path entry "record.json")
                       (json/dumps (u/pydict "key" key "material" material "exit" 0 "from" "forged"
                                             "outputs" (u/pydict "image" (cr/pin (pathlib/Path entry "image"))))))
          (cr/run-cached runner "compile" argv (python/dict) [output])
          (is (u/deq (.read_bytes output) (.encode "fresh")))
          (is (u/deq (.read_bytes (pathlib/Path out "raw/compile.stdout")) (.encode "executed")))
          (is (not (operator/contains (first (cr/calls runner)) "reused"))))))))
