;; Pinned verifier archive staging, refusal and no-clobber controls.
;; Ported from test_stage_pinned_gh.py.
(ns test-stage-pinned-gh
  (:require [basilisp.test :refer [deftest is]]
            [stage-pinned-gh :as stage])
  (:import hashlib io pathlib tarfile tempfile))

(defn sha [data] (.hexdigest (hashlib/sha256 data)))

(defn make-archive [root name & {:keys [symlink duplicate]}]
  (let [path (.joinpath root name)]
    (with-open [tar (tarfile/open path "w:gz")]
      (let [row (tarfile/TarInfo stage/member)]
        (if symlink
          (do (set! (.-type row) tarfile/SYMTYPE)
              (set! (.-linkname row) "../../escape")
              (.addfile tar row))
          (do (set! (.-size row) 3)
              (.addfile tar row (io/BytesIO (.encode "elf")))
              (when duplicate (.addfile tar row (io/BytesIO (.encode "elf"))))))))
    path))

(deftest pins-and-no-clobber
  (with-open [temp (tempfile/TemporaryDirectory ** :prefix "gh-stage-")]
    (let [root (pathlib/Path temp)
          archive (make-archive root "valid.tar.gz")
          output (.joinpath root "gh")
          pin (sha (.read_bytes archive))]
      (with-redefs [stage/archive-sha256 pin
                    stage/gh-sha256 (fn [] (sha (.encode "elf")))]
        (stage/stage archive output)
        (is (= (.encode "elf") (.read_bytes output)))
        (is (thrown? python/FileExistsError (stage/stage archive output)))
        (is (= (.encode "elf") (.read_bytes output))))
      (with-redefs [stage/archive-sha256 (apply str (repeat 64 "0"))]
        (is (thrown? python/ValueError (stage/stage archive (.joinpath root "bad")))))
      (is (not (.exists (.joinpath root "bad")))))))

(deftest duplicate-or-symlinked-member-is-rejected
  (with-open [temp (tempfile/TemporaryDirectory ** :prefix "gh-stage-")]
    (let [root (pathlib/Path temp)]
      (doseq [kind ["duplicate" "symlink"]]
        (let [archive (make-archive root (str kind ".tar.gz") :duplicate (= kind "duplicate") :symlink (= kind "symlink"))
              pin (sha (.read_bytes archive))
              out (.joinpath root (str kind "-out"))]
          (with-redefs [stage/archive-sha256 pin]
            (is (thrown? python/ValueError (stage/stage archive out)) kind))
          (is (not (.exists out)) kind))))))
