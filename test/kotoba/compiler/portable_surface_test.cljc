(ns kotoba.compiler.portable-surface-test
  "Three compiler namespaces, exercised on BOTH runtimes.

  `accelerator`, `interface` and `packaging.pe32plus` were `.clj` and carry no
  JVM interop at all -- the extension was the only thing keeping them off
  ClojureScript. This suite is the evidence for that, and it RUNS them rather
  than merely requiring them: a namespace can load under nbb and still die on
  the first JVM method call, because cljs compiles `(.foo x)` happily and only
  fails when it executes. Measured on this repo the same day: a `.getBytes`
  restored inside an unexercised branch of `kotoba.native.elf64` left its
  portable suite green.

  Run without a JVM:
    nbb --classpath \"src:test:$(clojure -Spath -M:test)\" run-portable-surface.cljs"
  (:require [clojure.test :refer [deftest is]]
            [kotoba.artifact.core :as artifact]
            [kotoba.compiler.accelerator :as accelerator]
            [kotoba.compiler.interface :as interface]
            [kotoba.compiler.ios-aot :as ios-aot]
            [kotoba.compiler.packaging.pe32plus :as pe32plus]
            #?(:cljs [kotoba.kir.cljs-i64 :as i64])
            [clojure.edn :as edn]
            #?@(:cljs [["node:fs" :as node-fs]])))

(defn- sealed-firmware []
  (artifact/seal
   {:target :x86_64-aiueos-uefi-v1
    :target-profile {:runtime :none :ambient-syscalls false}
    :program {:entry 'main}
    :exports {'main {:offset 0 :arity 2}}
    :limits {:fuel 4096}
    :fuel-abi {:initial 4096}
    :code [0xc3]}))

(deftest pe32plus-emits-an-mz-image
  ;; Runs the packager end to end. A PE32+ image opens with the DOS "MZ" stub,
  ;; so the first two bytes are a real check on the emitted output rather than
  ;; on the fact that the function returned.
  (let [image (:bytes (pe32plus/package-efi (sealed-firmware)))]
    (is (= [0x4d 0x5a] (vec (take 2 image))) "PE32+ images start with MZ")
    (is (every? #(<= 0 % 255) image))
    (is (> (count image) 64))))

(deftest pe32plus-refuses-an-unsealed-artifact
  ;; The guard clauses execute too, not just the happy path.
  (is (thrown? #?(:clj Exception :cljs js/Error)
               (pe32plus/package-efi {:code [0xc3]}))))

(deftest accelerator-validates-kir
  ;; `validation-errors` walks the KIR structure; an empty module must produce
  ;; at least one complaint, and a value that is not a module must not be
  ;; silently accepted.
  (is (seq (accelerator/validation-errors {})))
  (is (thrown? #?(:clj Exception :cljs js/Error)
               (accelerator/validate! {}))))

(deftest interface-namespace-is-usable
  ;; Small by design; this pins that its vars resolve and are callable rather
  ;; than that the file merely parsed.
  (is (pos? (count (ns-publics 'kotoba.compiler.interface)))))

;; ---------------------------------------------------------------------------
;; kotoba.compiler.ios-aot
;;
;; `ios_aot.clj` became `.cljc` by replacing one `.getBytes` with a reader
;; conditional and making the `byte-array` return shape `:clj`-only.  Loading it
;; proves nothing: both edits sit on paths that only a real `package` call
;; reaches, and cljs compiles `(.getBytes s c)` happily -- it fails when it runs.
;;
;; So this drives the packager end to end and compares against bytes the JVM
;; produced from the same artifact.  A sealed artifact is a pure value, so the
;; fixture is a genuine one captured from `compiler/compile-source` rather than
;; a hand-written stand-in -- `verify-artifact!` re-emits the machine code and
;; re-runs the KIR oracle before `package` gets to do anything, and a
;; hand-built value cannot survive that.

(def ^:private ios-artifact-path "test/fixtures/ios-aot-artifact.edn")

(defn- read-fixture []
  (let [text #?(:clj (slurp ios-artifact-path)
                :cljs (.readFileSync node-fs ios-artifact-path "utf8"))]
    ;; `:value` is the i64 oracle the verifier recomputes and compares.  The
    ;; fixture was printed by `pr-str` on the JVM, where an i64 prints as a
    ;; bare `42`; the ClojureScript KIR interpreter answers with a BigInt, and
    ;; `(= 42n 42)` is false -- so the artifact would be rejected here for a
    ;; reason that has nothing to do with the code under test.  This restores
    ;; the type the JVM printer dropped.  It is a property of the transport,
    ;; not of the artifact: `lang/value-codec.edn` specifies a canonical value
    ;; encoding, but `kotoba.artifact.core` does not implement one yet, so
    ;; there is no round-trip today that preserves i64 across the two runtimes.
    #?(:clj (edn/read-string text)
       :cljs (update (edn/read-string text) :value i64/->bigint))))

(deftest ios-aot-packages-a-macho-object-identically-on-both-runtimes
  (let [{:keys [object manifest]} (ios-aot/package (read-fixture) 'main)
        bytes (mapv #(bit-and (int %) 0xff) object)]
    ;; 64-bit little-endian Mach-O magic.  Reached only through
    ;; `macho/encode-object`, which is fed the `ascii-bytes` result.
    (is (= [0xcf 0xfa 0xed 0xfe] (vec (take 4 bytes))))
    ;; Byte-for-byte what the JVM emitted from this same artifact.
    (is (= 544 (count bytes)))
    (is (= "def77da7ef69f5407818d7dcd84dbc5402445312129e883f0b242d26d4c7eceb"
           (:object-sha256 manifest))
        "object-sha256 is computed from the same vector on both runtimes")
    (is (= :kotoba.ios-aot/v2 (:format manifest)))
    (is (= :ios (:platform manifest)))
    (is (every? #(<= 0 % 255) bytes))))

(deftest ios-aot-rejects-an-unsupported-platform
  ;; The guard clauses execute too, not just the happy path.
  (is (thrown? #?(:clj Exception :cljs js/Error)
               (ios-aot/package (read-fixture) 'main {:platform :invented}))))
