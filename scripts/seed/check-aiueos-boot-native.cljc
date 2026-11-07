;; Native transition packager diagnostics. Basilisp inspects, never packages.
;;
;; This is a bounded packaging gate, not native CDCI, a full OS boot or K16 qualification. Run the QEMU entry
;; check separately against the emitted pair.
;; Ported from check-aiueos-boot-native.py (Basilisp). Linux only.
;; Run: basilisp run scripts/seed/check-aiueos-boot-native.cljc -- (--build DIR | --complete DIR) --output OUT
(ns check-aiueos-boot-native
  (:require [aiueos-native-proof :as proof]
            [basilisp.string :as str]
            [gate-util :as u])
  (:import operator os platform struct sys))

(defn- up [fmt b off] (vec (struct/unpack_from fmt b off)))
(defn- any-set? [b] (boolean (python/any b)))
(defn- cat-bytes [& parts] (reduce operator/add (u/bytes-of) parts))
(defn- align-up [n a] (bit-and (+ n (dec a)) (- a)))

(defn verify [efi kernel payload]
  (let [pe (u/geti (struct/unpack_from "<I" efi 60) 0)
        _ (u/chk (and (= (u/bslice efi 0 2) (.encode "MZ")) (= 128 pe) (= (u/bslice efi pe (+ pe 4)) (u/bytes-of 0x50 0x45 0 0))))
        _ (u/chk (= [0x8664 3 0 0 0 240 0x22] (up "<HHIIIHH" efi (+ pe 4))))
        opt (+ pe 24)
        _ (u/chk (= 0x20b (u/geti (struct/unpack_from "<H" efi opt) 0)))
        [entry code loader-base alignment file-alignment] (up "<IIQII" efi (+ opt 16))
        _ (u/chk (= [4096 4096 4096 512] [entry code alignment file-alignment]))
        _ (u/chk (= [10 0x160] (up "<HH" efi (+ opt 68))))
        _ (u/chk (= 16 (u/geti (struct/unpack_from "<I" efi (+ opt 108)) 0)))
        [image-size header-size] (up "<II" efi (+ opt 56))
        phoff (u/geti (struct/unpack_from "<Q" kernel 32) 0)
        segments (vec (for [i (range 2)] (up "<IIQQQQQQ" kernel (+ phoff (* i 56)))))
        choices (filterv (fn [base] (every? (fn [p] (or (<= (+ base image-size) (nth p 3)) (<= (+ (nth p 3) (nth p 5)) base))) segments))
                         [0x400000 0x1000000 0x2000000])
        _ (u/chk (and (seq choices) (= loader-base (first choices))) "loader overlaps a fixed kernel segment")
        _ (u/chk (= 512 header-size))
        sections
        (reduce
          (fn [sections [i name]]
            (let [row (up "<8sIIIIIIHHI" efi (+ opt 240 (* 40 i)))
                  _ (u/chk (= (.encode name) (.rstrip (nth row 0) (u/bytes-of 0))))
                  [size rva raw off] (subvec row 1 5)]
              (u/chk (and (pos? size) (zero? (mod rva 4096)) (zero? (mod off 512)) (zero? (mod raw 512))))
              (u/chk (and (= raw (align-up size 512)) (>= (python/len efi) (+ off raw))))
              (u/chk (= [0 0 0 0] (subvec row 5 9)))
              (u/chk (= (nth row 9) (nth [0x60000020 0xc0000040 0x42000040] i)))
              (if (seq sections)
                (let [prev (peek sections)]
                  (u/chk (>= rva (align-up (+ (nth prev 1) (nth prev 0)) 4096)))
                  (u/chk (= off (+ (nth prev 3) (nth prev 2)))))
                (u/chk (and (= rva 4096) (= off 512))))
              (u/chk (not (any-set? (u/bslice efi (+ off size) (+ off raw)))))
              (conj sections [size rva raw off])))
          [] (map-indexed vector [".text" ".data" ".reloc"]))
        _ (u/chk (= (python/len efi) (+ (nth (peek sections) 2) (nth (peek sections) 3))))
        _ (u/chk (= image-size (align-up (+ (nth (peek sections) 1) (nth (peek sections) 0)) 4096)))
        _ (doseq [i (range 16)]
            (u/chk (= (up "<II" efi (+ opt 112 (* i 8))) (if (= i 5) [(nth (nth sections 2) 1) 12] [0 0]))))
        _ (u/chk (= (u/bslice efi (nth (nth sections 2) 3) (+ (nth (nth sections 2) 3) 12)) (struct/pack "<III" 0 12 0)))
        d (u/bslice efi (nth (nth sections 1) 3) (+ (nth (nth sections 1) 3) (nth (nth sections 1) 0)))
        ph (u/geti (struct/unpack_from "<Q" kernel 32) 0)
        rx (up "<8Q" kernel ph) rw (up "<8Q" kernel (+ ph 56))
        _ (u/chk (= [(nth rx 3) (nth rw 3) 0x544f4f4245554941 5] (up "<4Q" d 0)))
        _ (u/chk (not (any-set? (u/bslice d 32 72))))
        _ (u/chk (= [(align-up (+ (nth rx 3) (nth rx 5)) 4096) (nth rw 3) (+ (nth rw 3) (nth rw 5)) 0 15] (up "<5Q" d 72)))
        _ (u/chk (not (any-set? (u/bslice d 112 16560))))
        plen (python/len payload)
        _ (u/chk (= payload (u/bslice d 16560 (+ 16560 plen))))
        ko (bit-and (+ 16560 plen 15) -16)
        klen (python/len kernel)
        _ (u/chk (= kernel (u/bslice d ko (+ ko klen))))
        _ (u/chk (= 1 (.count efi kernel)))
        guid (bit-and (+ ko klen 7) -8)
        _ (u/chk (and (not (any-set? (u/bslice d (+ 16560 plen) ko))) (not (any-set? (u/bslice d (+ ko klen) guid)))))
        _ (u/chk (= (u/bslice d guid nil) (cat-bytes (u/hex->bytes "dea94290dc23384a96fb7aded080516a") (u/bytes-of-n 8 0))))
        _ (u/chk (u/has-bytes? (u/hex->bytes "41ff9640010000") (u/bslice efi 512 (+ 512 (nth (nth sections 0) 0)))))]
    nil))

(defn main [build output complete]
  (let [[source-graph producers _] (proof/load-native-producers :build build :complete complete)
        _ (.mkdir output ** :parents true :exist_ok false)
        rows (python/list)]
    (doseq [producer producers]
      (let [scope (.joinpath output (.-stem producer))
            _ (.mkdir scope)
            env (let [e (python/dict os/environ)]
                  (operator/setitem e "KEXE_CAP_RESOURCES_35" (str scope))
                  (operator/setitem e "KEXE_STACK_BYTES" "8388608")
                  e)
            src (.joinpath scope "kernel.kotoba") kernel (.joinpath scope "KERNEL.ELF")
            _ (.write_text src "(ns boot-entry (:export [main]))\n(defn main [] :i64 42)\n")
            r (u/run-process [producer "compile" src "--target" "x86_64-aiueos-kernel-v1" "--artifact" "image" "--output" kernel "--fuel" "1024"] env 120)
            _ (u/chk (and (zero? (.-returncode r)) (.exists kernel)) [(.-returncode r) (.-stderr r)])
            blob (.read_bytes kernel)
            commands (python/list) positive (python/dict) refused (python/list)
            package (fn [name & {:keys [k payload extra sentinel] :or {k kernel extra []}}]
                      (let [dst (.joinpath scope (str name ".EFI"))]
                        (when sentinel (.write_bytes dst sentinel))
                        (let [r (u/run-process (concat [producer "package-aiueos-boot" k "--output" dst] (when payload ["--payload" payload]) extra) env 120)]
                          (.append commands (u/pydict "name" name "exit" (.-returncode r) "stdout" (.decode (.-stdout r)) "stderr" (.decode (.-stderr r))))
                          [dst r])))
            refusal! (fn [dst r label] (u/chk (and (not (zero? (.-returncode r))) (not (.exists dst))) [label (.-stdout r) (.-stderr r)]))]
        (doseq [[name payload] [["plain" (u/bytes-of)] ["payload" (operator/add (.encode "native payload") (u/bytes-of 0 255))]
                                ["payload-max" (u/bytes-of-n 524288 0)]]]
          (let [path (.joinpath scope (str name ".bin"))
                _ (.write_bytes path payload)
                [dst r] (package name :payload (when (pos? (python/len payload)) path))]
            (u/chk (and (zero? (.-returncode r)) (not (u/nonempty? (.-stderr r)))) [name (.-returncode r) (.-stderr r)])
            (verify (.read_bytes dst) blob payload)
            (operator/setitem positive name (u/pin dst))))
        (doseq [[name off fmt value] [["magic" 0 "<I" 0] ["class" 4 "<B" 1] ["type" 16 "<H" 1] ["machine" 18 "<H" 183] ["phnum" 56 "<H" 3]
                                      ["phoff" 32 "<Q" (dec (bit-shift-left 1 64))] ["phalign" 32 "<Q" 65] ["entry" 24 "<Q" 0x108000]
                                      ["rwx" 68 "<I" 7] ["zero-size" 96 "<Q" 0] ["memory-size" 104 "<Q" 999999]
                                      ["high-address" 88 "<Q" 0x40000000] ["unaligned" 88 "<Q" 0x101001]
                                      ["file-offset" 72 "<Q" (python/len blob)] ["overlap" 144 "<Q" 0x101000]]]
          (let [bad (python/bytearray blob)]
            (struct/pack_into fmt bad off value)
            ;; Keep p_vaddr == p_paddr so this exercises the overlap predicate, rather than failing the segment's alias check.
            (when (= name "overlap") (struct/pack_into "<Q" bad 136 value))
            (let [path (.joinpath scope (str name ".ELF"))]
              (.write_bytes path bad)
              (let [[dst r] (package (str "bad-" name) :k path)]
                (refusal! dst r name)
                (.append refused name)))))
        (doseq [[name data] [["empty" (u/bytes-of)] ["short" (u/bslice blob 0 100)]]]
          (let [path (.joinpath scope (str name ".ELF"))]
            (.write_bytes path data)
            (let [[dst r] (package (str "bad-" name) :k path)]
              (refusal! dst r name)
              (.append refused name))))
        (let [payload (.joinpath scope "too-large.bin")]
          (.write_bytes payload (u/bytes-of-n 524289 0))
          (let [[dst r] (package "too-large" :payload payload)]
            (refusal! dst r "too-large")
            (.append refused "payload-too-large")))
        (doseq [flag ["--resident" "--k16-preflight" "--jvm-free"]]
          (let [[dst r] (package (str "bad-" (subs flag 2)) :extra [flag])]
            (refusal! dst r flag)
            (.append refused flag)))
        (let [[dst r] (package "existing" :sentinel (.encode "preserve"))]
          (u/chk (and (not (zero? (.-returncode r))) (= (.encode "preserve") (.read_bytes dst))))
          (.append refused "existing-output"))
        (.write_text (.joinpath scope "commands.json") (u/json-dump commands))
        (.append rows (u/pydict "producer" (u/pin producer) "kernel" (u/pin kernel) "artifacts" positive "refusals" refused))))
    (u/chk (and (u/deq (u/geti (u/geti rows 0) "kernel") (u/geti (u/geti rows 1) "kernel"))
                (u/deq (u/geti (u/geti rows 0) "artifacts") (u/geti (u/geti rows 1) "artifacts"))))
    (let [report (u/pydict "status" "PASS_NATIVE_AIUEOS_BOOT_PACKAGING" "source" source-graph "routes" rows
                           "host" (python/list [(platform/system) (platform/machine)]) "cCompilerOrLoader" false
                           "JVMNodeOrGraalFallback" false "nativeCDCI" false "completeKernel" false "qemuBoot" false
                           "gpt" false "resident" false "k16Tender" false)]
      (.write_text (.joinpath output "native-boot.json") (u/json-dump report))
      (println (u/geti report "status") (reduce + (map #(python/len (u/geti % "artifacts")) rows)) "EFI images; QEMU entry gate separate"))))

(defn -main [& args]
  (let [[build out complete] (u/parse-build-complete-output args)]
    (main build out complete)))

(when (some #(or (= % "check-aiueos-boot-native.cljc") (str/ends-with? % "/check-aiueos-boot-native.cljc")) sys/argv)
  (apply -main *command-line-args*))
