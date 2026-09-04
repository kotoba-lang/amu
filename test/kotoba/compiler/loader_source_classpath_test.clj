(ns kotoba.compiler.loader-source-classpath-test
  "amu#614 parity gate: the reviewed native loader source `tools/kexe_loader.c`
  must be resolvable through `io/resource`, so that a host which embeds the
  native decision as a library (kototama-native's executor) can locate it
  without knowing the compiler checkout's on-disk layout.

  The fix under test adds `\"tools\"` to `:paths` in deps.edn, which makes
  `tools/` a classpath ROOT -- so the resource name is `kexe_loader.c`,
  not `tools/kexe_loader.c`. ADR-0202's closure lock keeps the tools dir
  content-pinned; this gate pins its visibility."
  (:require [clojure.java.io :as io]
            [clojure.test :refer [deftest is]]))

(deftest kexe-loader-source-is-on-classpath
  (is (some? (io/resource "kexe_loader.c"))
      "kexe_loader.c is not on the classpath; io/resource cannot see it"))
