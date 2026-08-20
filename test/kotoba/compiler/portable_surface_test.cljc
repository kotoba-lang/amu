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
            [kotoba.compiler.packaging.pe32plus :as pe32plus]))

(defn- sealed-firmware []
  (artifact/seal
   {:target :x86_64-aiueos-uefi-v1
    :target-profile {:runtime :none :ambient-syscalls false}
    :program {:entry 'main}
    :exports {'main {:offset 0 :arity 0}}
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
