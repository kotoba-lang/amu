#!/usr/bin/env nbb
(ns jdk-free-native-conformance
  (:require [clojure.string :as str]
            ["node:child_process" :as child]
            ["node:fs" :as fs]
            ["node:os" :as os]
            ["node:path" :as path]))

(def root (.resolve path (.dirname path *file*) ".."))
(def tmp (.mkdtempSync fs (.join path (.tmpdir os) "amu-jdk-free-native-")))
(def shadow (.join path tmp "shadow"))
(def marker (.join path tmp "jvm-invoked.log"))
(def amu (.join path root "bin" "amu"))
(defn file [name] (.join path tmp name))
(defn ensure! [condition message] (when-not condition (throw (js/Error. message))))

(defn run
  ([command args env] (run command args env false))
  ([command args env allow-failure?]
   (let [result (.spawnSync child command (clj->js args)
                            #js {:cwd root :encoding "utf8" :maxBuffer 16777216
                                 :env env})
         status (if (nil? (.-status result)) 70 (.-status result))]
     (when (.-error result) (throw (.-error result)))
     (when (and (not allow-failure?) (not= 0 status))
       (throw (js/Error. (str "command failed: " command " " (str/join " " args)
                              "\n" (or (.-stderr result) "")))))
     {:status status :stdout (or (.-stdout result) "")
      :stderr (or (.-stderr result) "")})))

(try
  (fs/mkdirSync shadow)
  (doseq [binary ["java" "javac" "clojure" "clj"]]
    (let [target (.join path shadow binary)]
      (fs/writeFileSync target
                        (str "#!/bin/sh\necho '" binary " $*' >> '" marker
                             "'\necho '" binary ": forbidden by JDK-free conformance' >&2\nexit 127\n"))
      (fs/chmodSync target (js/parseInt "755" 8))))
  (let [platform (.platform os)
        arch (.arch os)
        isa (cond
              (contains? #{"arm64" "aarch64"} arch) "aarch64"
              (= "x64" arch) "x86_64"
              :else (throw (js/Error. (str "unsupported native conformance architecture: " arch))))
        _ (ensure! (contains? #{"darwin" "linux"} platform)
                   (str "unsupported native conformance platform: " platform))
        env (js/Object.assign #js {} js/process.env
                              #js {"PATH" (str shadow (.-delimiter path) (.-PATH js/process.env))
                                   "JAVA_HOME" (.join path tmp "no-java-home")})
        invoke (fn [args] (run js/process.execPath (into [amu] args) env))
        loader (file "kexe-loader")]
    (run "cc" ["-std=c11" "-O2" "-Wall" "-Wextra" "-Werror"
                (.join path root "tools" "kexe_loader.c") "-o" loader] env)
    (doseq [{:keys [source symbol arguments expected]}
            [;; A zero i64 literal reaches MIR as a JavaScript BigInt under
             ;; nbb. Keep this first so register classification can never
             ;; regress into hashing that primitive as a physical register.
             {:source "i64-semantics.kotoba" :symbol "main"
              :arguments [] :expected "0"}
             {:source "structured.kotoba" :symbol "score"
              :arguments ["-7" "2"] :expected "12"}
             {:source "nested-record.kotoba" :symbol "nested-score"
              :arguments [] :expected "15"}
             {:source "held-operations.kotoba" :symbol "held-score"
              :arguments [] :expected "54"}]]
      (let [artifact (file (str symbol ".kexe"))
            binary (file (str symbol ".bin"))]
        (invoke ["compile" (.join path root "examples" source)
                 "--target" isa "--output" artifact])
        (let [extracted (:stdout (invoke ["extract-native" artifact "--symbol" symbol
                                         "--output" binary]))
              [_ offset] (re-find #":offset ([0-9]+)" extracted)]
          (ensure! offset (str "extract-native returned no " symbol " offset"))
          (let [executed (run loader
                              (into [binary offset (str (count arguments)) isa "-"]
                                    arguments)
                              env)]
            (ensure! (= expected (str/trim (:stdout executed)))
                     (str "native " symbol " expected " expected ", got "
                          (str/trim (:stdout executed))))))))
    ;; The aiueos target profiles package the sealed artifact into an ELF64 or
    ;; PE32+ container. Until `kotoba.compiler.nbb.native-package` existed this
    ;; driver had no packaging step at all, so `os/aiueos` built all 67 of its
    ;; kernel objects through `clojure` -- not because code generation needed a
    ;; JVM (these targets reach the same two emitters exercised above) but
    ;; because only the JVM CLI ran the packager.
    ;;
    ;; Asserted on the container bytes rather than on the exit status, because
    ;; the failure this guards against is not a crash: admitting the target
    ;; without a packager would have written artifact EDN to a path named `.o`
    ;; and reported :ok true. A wrong answer, delivered quietly.
    (let [magic (fn [p] (let [b (fs/readFileSync p)]
                          {:head (.toString (.subarray b 0 4) "latin1")
                           :type (.readUInt16LE b 16)
                           :machine (.readUInt16LE b 18)}))]
      (doseq [{:keys [target artifact-kind expect-type expect-machine label]}
              [{:target "x86_64-aiueos-kernel-v1" :artifact-kind nil
                :expect-type 1 :expect-machine 0x3e :label "kernel object (ET_REL, EM_X86_64)"}
               {:target "x86_64-aiueos-kernel-v1" :artifact-kind "image"
                :expect-type 2 :expect-machine 0x3e :label "kernel image (ET_EXEC, EM_X86_64)"}
               {:target "aarch64-aiueos-kernel-v1" :artifact-kind "image"
                :expect-type 2 :expect-machine 0xb7 :label "kernel image (ET_EXEC, EM_AARCH64)"}]]
        (let [out (file (str "aiueos-" target "-" (or artifact-kind "default") ".o"))]
          (invoke (cond-> ["compile" (.join path root "examples" "i64-semantics.kotoba")
                           "--target" target "--output" out]
                    artifact-kind (into ["--artifact" artifact-kind])))
          (let [{:keys [head type machine]} (magic out)]
            (ensure! (= "\u007fELF" head)
                     (str "aiueos " label " is not ELF64; got " (pr-str head)
                          " -- artifact EDN written where a container belongs"))
            (ensure! (= expect-type type)
                     (str "aiueos " label " has e_type " type))
            (ensure! (= expect-machine machine)
                     (str "aiueos " label " has e_machine " machine)))))
      (let [efi (file "aiueos-uefi.efi")]
        (invoke ["compile" (.join path root "examples" "i64-semantics.kotoba")
                 "--target" "x86_64-aiueos-uefi-v1" "--artifact" "image" "--output" efi])
        (ensure! (= "MZ" (.toString (.subarray (fs/readFileSync efi) 0 2) "latin1"))
                 "aiueos UEFI image is not a PE32+ application"))
      ;; An unknown --artifact must be refused BEFORE the work, not discovered
      ;; after it, and must not fall through to writing the artifact EDN.
      (let [rejected (run js/process.execPath
                          [amu "compile" (.join path root "examples" "i64-semantics.kotoba")
                           "--target" "x86_64-aiueos-kernel-v1" "--artifact" "sections"
                           "--output" (file "rejected.o")]
                          env true)]
        (ensure! (not= 0 (:status rejected))
                 "an unknown --artifact kind was accepted")
        (ensure! (not (fs/existsSync (file "rejected.o")))
                 "an unknown --artifact kind still wrote an output file")))

    (when (fs/existsSync marker)
      (throw (js/Error. (str "JVM tool was invoked: " (fs/readFileSync marker "utf8")))))
    (println (str "jdk-free-native: sealed " isa
                  " scalar, aggregate-variant, callable, bounded-apply artifacts independently extracted"
                  " and executed under W^X loader; aiueos ELF64 object/image and PE32+ image packaged")))
  (finally
    (fs/rmSync tmp #js {:recursive true :force true})))
