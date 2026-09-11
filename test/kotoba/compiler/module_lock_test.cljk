(ns kotoba.compiler.module-lock-test
  "CID-pinned module resolution.

  The property under test is not `it can find the files` -- `project-files`
  already does that. It is that resolution is CLOSED: what gets compiled is
  exactly what the lock names, proven by hash, with no path search available as
  a fallback when the lock is wrong or incomplete."
  (:require [clojure.java.io :as io]
            [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]
            [kotoba.compiler.module-lock :as module-lock])
  (:import [java.nio.file Files]))

(def lib-source
  "(ns example.lib (:export [answer])) (defn answer [] :i64 42)")

(def app-source
  "(ns example.root (:require [example.lib :as lib]) (:export [main]))
   (defn main [] :i64 (lib/answer))")

(defn- temp-dir [prefix]
  (.toFile (Files/createTempDirectory prefix (make-array java.nio.file.attribute.FileAttribute 0))))

(defn- delete-tree [root]
  (doseq [f (reverse (file-seq root))] (.delete ^java.io.File f)))

(defn- write-lock!
  "Persist SOURCES as blocks and write a lock naming ROOT, returning both paths."
  [sources root]
  (let [blocks (temp-dir "kotoba-blocks-")
        lock-file (io/file (temp-dir "kotoba-lock-") "kotoba.modules.edn")
        modules (into (sorted-map)
                      (map (fn [[namespace source]]
                             [namespace (module-lock/write-block! blocks source)]))
                      sources)]
    (spit lock-file (pr-str {:schema module-lock/lock-schema :root root :modules modules}))
    {:blocks blocks :lock (str lock-file) :modules modules}))

(defn- with-locked [sources root body-fn]
  (let [{:keys [blocks lock modules]} (write-lock! sources root)]
    (try (body-fn {:blocks blocks :lock lock :modules modules})
         (finally (delete-tree blocks)
                  (delete-tree (.getParentFile (io/file lock)))))))

(deftest resolves-a-closed-graph-by-cid-and-compiles-it
  (with-locked {'example.lib lib-source 'example.root app-source} 'example.root
    (fn [{:keys [blocks lock]}]
      (let [{:keys [sources root lock-cid modules]}
            (module-lock/load-locked-graph lock (str blocks))]
        (is (= 'example.root root))
        (is (= #{'example.lib 'example.root} (set (keys sources))))
        (is (string? lock-cid))
        (is (= 2 (count modules)))
        (testing "and the pinned sources compile exactly as path-resolved ones do"
          (is (= :wasm/v1 (:format (compiler/compile-project sources root :wasm32-kotoba-v1)))))))))

(deftest a-block-that-does-not-hash-to-its-cid-is-refused
  (with-locked {'example.lib lib-source 'example.root app-source} 'example.root
    (fn [{:keys [blocks lock modules]}]
      ;; Same filename, different bytes: the only thing standing between this
      ;; and a silently different build is the hash check.
      (spit (io/file blocks (get modules 'example.lib))
            "(ns example.lib (:export [answer])) (defn answer [] :i64 0)")
      (let [error (try (module-lock/load-locked-graph lock (str blocks))
                       (catch clojure.lang.ExceptionInfo e e))]
        (is (= :module-lock (:phase (ex-data error))))
        (is (re-find #"does not hash" (ex-message error)))))))

(deftest an-unpinned-dependency-stops-the-build-instead-of-being-searched-for
  (with-locked {'example.root app-source} 'example.root
    (fn [{:keys [blocks lock]}]
      ;; example.lib exists on disk in this very repo's test fixtures in the
      ;; path-resolved world. Here it simply is not pinned, and that is fatal.
      (let [error (try (module-lock/load-locked-graph lock (str blocks))
                       (catch clojure.lang.ExceptionInfo e e))]
        (is (= 'example.lib (:module (ex-data error))))
        (is (re-find #"not pinned" (ex-message error)))))))

(deftest a-block-declaring-a-different-namespace-is-refused
  (with-locked {'example.lib lib-source 'example.root app-source} 'example.root
    (fn [{:keys [blocks lock modules]}]
      (let [impostor (module-lock/write-block!
                      blocks "(ns example.other (:export [answer])) (defn answer [] :i64 1)")
            tampered (io/file (.getParentFile (io/file lock)) "tampered.edn")]
        (spit tampered (pr-str {:schema module-lock/lock-schema
                                :root 'example.root
                                :modules (assoc modules 'example.lib impostor)}))
        (let [error (try (module-lock/load-locked-graph (str tampered) (str blocks))
                         (catch clojure.lang.ExceptionInfo e e))]
          (is (= 'example.other (:declared (ex-data error))))
          (is (re-find #"different namespace" (ex-message error))))))))

(deftest the-lock-cid-changes-when-any-input-changes
  (let [base (module-lock/lock-cid {:root 'example.root
                                    :modules {'example.lib "bafkone" 'example.root "bafktwo"}})]
    (is (= base (module-lock/lock-cid {:root 'example.root
                                       :modules {'example.root "bafktwo" 'example.lib "bafkone"}}))
        "entry order is not part of the identity")
    (is (not= base (module-lock/lock-cid {:root 'example.root
                                          :modules {'example.lib "bafkthree" 'example.root "bafktwo"}}))
        "a changed dependency changes the pinned-input identity")
    (is (not= base (module-lock/lock-cid {:root 'example.lib
                                          :modules {'example.lib "bafkone" 'example.root "bafktwo"}}))
        "the same modules compiled from a different root are a different input set")))

(deftest a-lock-that-does-not-pin-its-own-root-is-refused
  (let [dir (temp-dir "kotoba-lock-")
        lock (io/file dir "kotoba.modules.edn")]
    (try
      (spit lock (pr-str {:schema module-lock/lock-schema
                          :root 'example.missing
                          :modules {'example.lib "bafkone"}}))
      (is (re-find #"does not pin its own root"
                   (ex-message (try (module-lock/read-lock (str lock))
                                    (catch clojure.lang.ExceptionInfo e e)))))
      (finally (delete-tree dir)))))

(deftest writing-the-same-source-twice-produces-one-block
  (let [blocks (temp-dir "kotoba-blocks-")]
    (try
      (is (= (module-lock/write-block! blocks lib-source)
             (module-lock/write-block! blocks lib-source)))
      (is (= 1 (count (.listFiles blocks))))
      (finally (delete-tree blocks)))))
