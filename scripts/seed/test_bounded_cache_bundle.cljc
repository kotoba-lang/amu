;; Native round trip and hostile archive controls; no cached verdicts.
;; Ported from test_bounded_cache_bundle.py. The native cases need AMU_BOUNDED_FIXTURE (a directory with
;; producer.elf and cache/), exactly as before; the hostile-archive and refusal cases do not.
(ns test-bounded-cache-bundle
  (:require [basilisp.test :refer [deftest is]]
            [bounded-cache-bundle :as b]
            [check-bounded-producer-attestation :as producer]
            [sealed-image :as sealed])
  (:import io os pathlib shutil tarfile tempfile))

(defn fixture []
  (let [v (.get os/environ "AMU_BOUNDED_FIXTURE")]
    (when-not v (throw (python/RuntimeError "AMU_BOUNDED_FIXTURE is required for the native cases")))
    (.resolve (pathlib/Path v))))

(defn with-root [dir f]
  (with-open [tmp (tempfile/TemporaryDirectory ** :prefix "bounded-test-" :dir dir)]
    (f (pathlib/Path tmp))))

(deftest native-object-round-trip
  (let [fx (fixture)]
    (with-root (.-parent fx)
      (fn [root]
        (let [bundle (.joinpath root "bundle.tar")]
          (b/pack (.joinpath fx "producer.elf") (.joinpath fx "cache") bundle)
          (let [[image objects digest] (sealed/with-sealed-blob bundle (fn [fd _] (b/extract-sealed fd (.joinpath root "unpacked"))))]
            (producer/exercise image objects digest root)))))))

(deftest unexpected-cache-file-is-refused
  (let [fx (fixture)]
    (with-root (.-parent fx)
      (fn [root]
        (let [cache (.joinpath root "cache") bundle (.joinpath root "bundle.tar")]
          (shutil/copytree (.joinpath fx "cache") cache)
          (.chmod cache 0700)
          (.write_text (.joinpath cache "stdout") "old result")
          (is (thrown? python/ValueError (b/pack (.joinpath fx "producer.elf") cache bundle)))
          (is (not (.exists bundle))))))))

(defn- hostile-bundle [bundle kind]
  (with-open [tar (tarfile/open bundle "w")]
    (let [image (tarfile/TarInfo "producer.elf")]
      (set! (.-size image) 1)
      (.addfile tar image (io/BytesIO (.encode "x"))))
    (let [name (get {"traversal" "../escaped" "symlink" (str "objects/" (apply str (repeat 64 "a")) ".kdo")
                     "duplicate" "producer.elf" "verdict" "stdout"} kind)
          row (tarfile/TarInfo name)]
      (if (= kind "symlink")
        (do (set! (.-type row) tarfile/SYMTYPE)
            (set! (.-linkname row) "../../escaped")
            (.addfile tar row))
        (do (set! (.-size row) 1)
            (.addfile tar row (io/BytesIO (.encode "x"))))))))

(deftest hostile-archive-paths-and-links-are-refused-and-cleaned-up
  (with-root nil
    (fn [root]
      (doseq [kind ["traversal" "symlink" "duplicate" "verdict"]]
        (let [bundle (.joinpath root (str kind ".tar")) out (.joinpath root (str kind "-out"))]
          (hostile-bundle bundle kind)
          (is (thrown? python/ValueError (sealed/with-sealed-blob bundle (fn [fd _] (b/extract-sealed fd out)))) kind)
          (is (not (.exists out)) kind)
          (is (not (.exists (.joinpath root "escaped"))) kind))))))

(deftest unsealed-fd-is-refused
  (with-root nil
    (fn [root]
      (let [path (.joinpath root "plain.tar")]
        (hostile-bundle path "verdict")
        (let [fd (os/open path os/O_RDONLY)]
          (try
            (is (thrown? python/Exception (b/extract-sealed fd (.joinpath root "out")))) ; non-memfd: EINVAL or "not sealed"
            (finally (os/close fd))))))))

(deftest insecure-or-symlinked-object-is-refused
  (let [fx (fixture)]
    (with-root (.-parent fx)
      (fn [root]
        (doseq [kind ["permissions" "symlink"]]
          (let [cache (.joinpath root (str kind "-cache")) bundle (.joinpath root (str kind ".tar"))]
            (shutil/copytree (.joinpath fx "cache") cache)
            (.chmod cache 0700)
            (let [obj (first (python/list (.iterdir cache)))]
              (if (= kind "permissions")
                (.chmod obj 0600)
                (do (.unlink obj) (.symlink_to obj (.joinpath fx "producer.elf")))))
            (is (thrown? python/Exception (b/pack (.joinpath fx "producer.elf") cache bundle)) kind)
            (is (not (.exists bundle)) kind)))))))
