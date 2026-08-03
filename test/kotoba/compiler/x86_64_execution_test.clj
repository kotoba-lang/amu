(ns kotoba.compiler.x86-64-execution-test
  "Executes x86-64 artifacts on a machine whose CPU is not x86-64.

  This exists because its absence let a real bug ship twice. `emit-heap-call`
  encoded every context offset as a signed disp8, so the callbacks at 136 and
  144 called the wrong address; AArch64 cannot express that mistake, and every
  execution test here runs on AArch64, so nothing failed. Compiling both
  artifacts with the pre-fix backend and running them through this harness
  segfaults -- which is what a test that had existed would have said.

  macOS on Apple silicon can both cross-compile to x86-64 (`cc -arch x86_64`)
  and run the result (Rosetta 2). Where either is missing the tests skip rather
  than fail: on an x86-64 host the ordinary native_executor_test already
  executes this ISA, and this file is only interesting on a host that does not."
  (:require [clojure.java.io :as io]
            [clojure.java.shell :as shell]
            [clojure.string :as str]
            [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]))

(defn- x86-64-execution-available? []
  (and (str/includes? (str/lower-case (System/getProperty "os.name")) "mac")
       (let [probe (io/file (System/getProperty "java.io.tmpdir")
                            "kotoba-x86-probe.c")
             out (io/file (System/getProperty "java.io.tmpdir")
                          "kotoba-x86-probe.bin")]
         (spit probe "int main(void){return 7;}")
         (and (zero? (:exit (shell/sh "cc" "-arch" "x86_64" (.getPath probe)
                                      "-o" (.getPath out))))
              (= 7 (:exit (shell/sh (.getPath out))))))))

(defonce ^:private harness
  (delay
    (when (x86-64-execution-available?)
      (let [loader (io/file (System/getProperty "java.io.tmpdir")
                            "kotoba-x86-loader.bin")
            build (shell/sh "cc" "-arch" "x86_64" "-std=c11" "-O2"
                            "-Wall" "-Wextra" "-Werror"
                            "tools/kexe_loader.c" "-o" (.getPath loader))]
        (when (zero? (:exit build)) (.getPath loader))))))

(defn- run-x86-64 [source]
  (let [artifact (:artifact (compiler/compile-source source :x86_64-kotoba-v1
                                                     {:allow #{}}))
        code (io/file (System/getProperty "java.io.tmpdir") "kotoba-x86-code.bin")
        offset (get-in artifact [:exports 'main :offset])]
    (with-open [out (io/output-stream code)]
      (.write out (byte-array (map #(unchecked-byte (bit-and (int %) 0xff))
                                   (:code artifact)))))
    (:out (shell/sh @harness (.getPath code) (str offset) "0" "x86_64" "-"
                    :env (assoc (into {} (System/getenv))
                                "KEXE_STRUCTURED_REPORT" "1")))))

;; The two host calls whose context offsets exceed the disp8 range. A wrong
;; displacement here is not subtle: it calls into whatever precedes the
;; context, and both of these segfaulted before the encoding was fixed.
(deftest host-calls-past-disp8-execute-on-real-x86-64
  (if-not @harness
    (println "skipping: no x86-64 cross-compile + execution on this host")
    (doseq [[why source expected]
            [["a program with no host call" "(defn main [] 42)" 42]
             ["string-substring at offset 136"
              (str "(defn main [] (string-byte-length (string-substring"
                   " (string-concat \"ab\" \"cde\") 1 4)))") 3]
             ["string-code-point-at at offset 144"
              "(defn main [] (string-code-point-at \"日本語\" 3))" 26412]]]
      (testing why
        (let [report (run-x86-64 source)]
          (is (not (str/includes? report "KEXE_TRAP"))
              (str why " must not trap: " (str/trim report)))
          (is (str/includes? report (str ":result " expected))
              (str why " => " (str/trim report))))))))
