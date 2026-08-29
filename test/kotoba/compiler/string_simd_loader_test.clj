(ns kotoba.compiler.string-simd-loader-test
  (:require [clojure.java.io :as io]
            [clojure.java.shell :as shell]
            [clojure.string :as str]
            [clojure.test :refer [deftest is testing]]))

(def ^:private loader-source (io/file "tools" "kexe_loader.c"))

(deftest posix-loader-emits-the-host-simd-family
  (let [tmp (java.nio.file.Files/createTempDirectory
             "kexe-string-simd" (make-array java.nio.file.attribute.FileAttribute 0))
        assembly (.toFile (.resolve tmp "kexe_loader.s"))
        binary (.toFile (.resolve tmp "kexe_loader"))
        compile-result (shell/sh "cc" "-std=c11" "-O3" "-Wall" "-Wextra"
                                 "-Werror" (.getPath loader-source) "-o" (.getPath binary))
        assembly-result (shell/sh "cc" "-std=c11" "-O3" "-S"
                                  (.getPath loader-source) "-o" (.getPath assembly))]
    (is (= 0 (:exit compile-result)) (:err compile-result))
    (is (= 0 (:exit assembly-result)) (:err assembly-result))
    (when (zero? (:exit assembly-result))
      (let [text (slurp assembly)
            arch (str/lower-case (System/getProperty "os.arch"))]
        (testing "the optimized assembly contains the selected 16-byte compare"
          (cond
            (contains? #{"aarch64" "arm64"} arch)
            (is (and (re-find #"(?i)\bcmeq\b" text)
                     (re-find #"(?i)\buminv\b" text)))

            (contains? #{"x86_64" "amd64"} arch)
            (is (and (re-find #"(?i)(p|v)?cmpeq" text)
                     (re-find #"(?i)(p|v)?movmsk" text)))

            :else
            (is true "unsupported host keeps the scalar fallback")))))))
