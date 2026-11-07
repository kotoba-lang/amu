;; Native PCI collector packaging observations, not an OS ownership gate.
;;
;; Basilisp stages, starts native producers and inspects bytes. The collector
;; itself is emitted by the complete Kotoba compiler. QEMU must separately
;; compare its actual catalog to independent PCI device information.
;; Ported from check-aiueos-pci-boot-native.py (Basilisp). Linux only.
;; Run: basilisp run scripts/seed/check-aiueos-pci-boot-native.cljc -- (--build DIR | --complete DIR) --output OUT
(ns check-aiueos-pci-boot-native
  (:require [aiueos-gate :as g]
            [aiueos-proof :as proof]
            [basilisp.string :as str]
            [gate-util :as u])
  (:import operator sys))

(defn main [build out complete]
  (let [[graph producers _] (proof/load-native-producers :build build :complete complete)
        _ (.mkdir out ** :parents true :exist_ok false)
        routes (python/list)]
    (doseq [compiler producers]
      (let [scope (.joinpath out (.-stem compiler))
            _ (.mkdir scope)
            env (python/dict {"PATH" "/nonexistent" "KEXE_CAP_RESOURCES_35" (str scope) "KEXE_STACK_BYTES" "8388608"})
            source (.joinpath scope "entry.kotoba")
            _ (.write_text source "(ns entry (:export [main]))\n(defn main [] :i64 42)\n")
            kernel (.joinpath scope "entry.elf")
            calls (python/list)
            run (fn [name args expected]
                  (let [r (u/run-process (cons compiler args) env 240)]
                    (.append calls (u/pydict "name" name "exit" (.-returncode r) "stdout" (.decode (.-stdout r)) "stderr" (.decode (.-stderr r))))
                    (.write_text (.joinpath scope "calls.json") (u/json-dump calls))
                    (u/chk (= expected (.-returncode r)) [name (u/geti calls -1)])
                    (when (zero? expected) (u/chk (not (u/nonempty? (.-stderr r))) (u/geti calls -1)))
                    r))
            _ (run "compile" ["compile" source "--target" "x86_64-aiueos-kernel-v1" "--artifact" "image" "--output" kernel "--fuel" 1024] 0)
            artifacts (u/pydict "kernel" (u/pin kernel))
            kernel-bytes (.read_bytes kernel)
            ksize (.-st_size (.stat kernel))]
        (doseq [[name payload] [["plain" nil] ["payload" (operator/add (.encode "PCI payload") (u/bytes-of 0 255))]]]
          (let [dst (.joinpath scope (str name ".efi"))
                args (cond-> ["package-aiueos-boot" kernel "--output" dst]
                       payload (into ["--payload" (let [p (.joinpath scope "payload.bin")] (.write_bytes p payload) p)]))]
            (run name (into args ["--pci-resources" "v1"]) 0)
            (let [raw (.read_bytes dst)
                  _ (u/chk (= 1 (.count raw kernel-bytes)))
                  opt (+ (u/geti (g/unpack "<I" raw 60) 0) 24)
                  [size _rva _rawsize offset] (vec (g/unpack "<IIII" raw (+ opt 240 40 8)))
                  data (u/bslice raw offset (+ offset size))
                  pl (or payload (u/bytes-of))
                  plen (python/len pl)]
              (u/chk (= [0x544f4f4245554941 6] (vec (g/unpack "<QQ" data 16))))
              (u/chk (not (python/any (u/bslice data 160 176))))
              (u/chk (= [0x31494350534f4941 1 0 64] (vec (g/unpack "<QQQQ" data 16560))))
              (u/chk (not (python/any (u/bslice data 16592 (+ 16560 8224)))))
              (let [ko (bit-and (+ 16560 8224 plen 15) -16)]
                (u/chk (= pl (u/bslice data (+ 16560 8224) (+ 16560 8224 plen))))
                (u/chk (= kernel-bytes (u/bslice data ko (+ ko ksize))))
                (let [guid (bit-and (+ ko ksize 7) -8)]
                  (u/chk (= (u/hex->bytes "00b2f54cb868a54c9eecb23e3f50029a") (u/bslice data (+ guid 24) (+ guid 40))))
                  (u/chk (= size (+ guid 144)))))
              (operator/setitem artifacts name (u/pin dst)))))
        (doseq [[name flags] [["unknown-version" ["--pci-resources" "v2"]]
                              ["duplicate" ["--pci-resources" "v1" "--pci-resources" "v1"]]
                              ["unsupported" ["--pci-resources" "v1" "--resident" "yes"]]]]
          (let [dst (.joinpath scope (str name ".efi"))]
            (run name (into ["package-aiueos-boot" kernel "--output" dst] flags) 2)
            (u/chk (not (.exists dst)))))
        (.append routes (u/pydict "compiler" (u/pin compiler) "artifacts" artifacts "cliRefusals" 3))))
    (u/chk (u/deq (u/geti (u/geti routes 0) "artifacts") (u/geti (u/geti routes 1) "artifacts")))
    (let [report (u/pydict "status" "PASS_NATIVE_PCI_COLLECTOR_PACKAGING"
                           "observer" (u/pin (.joinpath u/root "scripts/seed/check-aiueos-pci-boot-native.cljc"))
                           "source" graph "routes" routes "osOwnershipQualified" false "guestExecution" false
                           "fullKernel" false "nativeCDCI" false)]
      (.write_text (.joinpath out "native-pci-boot.json") (u/json-dump report))
      (println (u/geti report "status")))))

(defn -main [& args]
  (let [[build out complete] (u/parse-build-complete-output args)]
    (main build out complete)))

(when (some #(or (= % "check-aiueos-pci-boot-native.cljc") (str/ends-with? % "/check-aiueos-pci-boot-native.cljc")) sys/argv)
  (apply -main *command-line-args*))
