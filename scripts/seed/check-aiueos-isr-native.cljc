;; Observe the native ISR table's shape and compile-time refusal controls.
;;
;; QEMU interrupt execution and its failing marker control run separately.
;; Ported from check-aiueos-isr-native.py (Basilisp). Linux only.
;; Run: basilisp run scripts/seed/check-aiueos-isr-native.cljc -- (--build DIR | --complete DIR) --output OUT
(ns check-aiueos-isr-native
  (:require [aiueos-native-proof :as proof]
            [basilisp.string :as str]
            [gate-util :as u])
  (:import json operator os pathlib struct subprocess sys))

(def source-text
  "(ns entry (:export [main aiueos-isr-3]))
(defn aiueos-isr-3 [vector :i64 error :i64 rip :i64 rsp :i64] :i64
 (let [r (kernel-subregion (kernel-boot-info) 16544 152 8)
       value (if (and (= vector 3) (= error 0) (>= rip 1052672) (> rsp 0)) 42 0)
       mark (kernel-store-u32 r 8 0 value)]
  (+ mark 1234)))
(defn main [] :i64
 (let [boot (kernel-boot-info)
       workspace (kernel-subregion boot 16544 12448 4096)
       idt (kernel-subregion workspace 4096 0 64)
       descriptor (kernel-subregion workspace 4096 512 10)
       record (kernel-subregion boot 16544 152 8)
       saved (kernel-load-u64 record 8 0)
       clear (kernel-store-u32 record 8 0 0)
       address (kernel-isr-entry-address 3) cs (kernel-read-cs)
       s0 (kernel-store-u16 idt 64 48 (bit-and address 65535))
       s1 (kernel-store-u16 idt 64 50 cs)
       s2 (kernel-store-u8 idt 64 52 0)
       s3 (kernel-store-u8 idt 64 53 142)
       s4 (kernel-store-u16 idt 64 54 (bit-and (u64-shift-right address 16) 65535))
       s5 (kernel-store-u32 idt 64 56 (u64-shift-right address 32))
       s6 (kernel-store-u32 idt 64 60 0)
       d0 (kernel-store-u16 descriptor 10 0 63)
       d1 (kernel-store-u32 descriptor 10 2 (bit-and idt 4294967295))
       d2 (kernel-store-u32 descriptor 10 6 (u64-shift-right idt 32))
       loaded (kernel-load-idt descriptor 10)
       fired (if (= loaded 1) (kernel-debug-break) 0)
       received (kernel-load-u32 record 8 0)
       restored (kernel-store-u64 record 8 0 saved)]
  (if (and (= loaded 1) (= fired 0) (= received 42) (= restored saved)
           (= clear 0) (= cs 8) (> address 1052672)
           (= s0 (bit-and address 65535)) (= s1 cs) (= s2 0) (= s3 142)
           (= s4 (bit-and (u64-shift-right address 16) 65535))
           (= s5 (u64-shift-right address 32)) (= s6 0) (= d0 63)
           (= d1 (bit-and idt 4294967295)) (= d2 (u64-shift-right idt 32))) 42 0)))
")

(defn- unpack [fmt b off] (struct/unpack_from fmt b off))
(defn- q-at [b off] (u/geti (unpack "<Q" b off) 0))
(defn- i-at [b off] (u/geti (unpack "<i" b off) 0))
(defn- I-at [b off] (u/geti (unpack "<I" b off) 0))
(defn- byte-at [b i] (u/geti b i))

(defn verify [image]
  (let [b (.read_bytes image)
        ph (q-at b 32)
        rx (unpack "<IIQQQQQQ" b ph)
        rw (unpack "<IIQQQQQQ" b (+ ph 56))
        table (q-at b (+ (u/geti rw 2) 328))
        _ (u/chk (and (>= table (u/geti rx 3)) (<= (+ table 8192) (+ (u/geti rx 3) (u/geti rx 5))) (zero? (mod table 128))))
        at (- (+ (u/geti rx 2) table) (u/geti rx 3))
        slot (u/bslice b (+ at (* 3 128)) (+ at (* 4 128)))]
    (u/chk (and (= (u/bslice slot 0 2) (u/bytes-of 0x6a 0)) (= (byte-at slot 25) 0xfc)
                (= (u/bslice slot 26 29) (u/hex->bytes "4c8d0d"))))
    (u/chk (= (+ (i-at slot 29) table (* 3 128) 33) (u/geti rw 3)))
    (u/chk (and (= (u/bslice slot 33 41) (u/hex->bytes "41ff710849c74108")) (= (I-at slot 41) 4096)))
    (u/chk (and (= (byte-at slot 45) 191) (= (I-at slot 46) 3) (= (byte-at slot 74) 232)))
    (let [body (+ table (* 3 128) 79 (i-at slot 75))]
      (u/chk (and (<= (+ (u/geti rx 3) 77) body) (< body table) (= (u/bslice slot 79 83) (u/hex->bytes "418f4108"))
                  (= (u/bslice slot 110 112) (u/hex->bytes "48cf"))))
      (u/chk (= (u/bslice slot 112 nil) (u/bytes-of-n 16 204)))
      (doseq [v (range 64)]
        (when-not (contains? #{3 6} v)
          (u/chk (= (u/bslice b (+ at (* v 128)) (+ at (* (inc v) 128)))
                    (operator/add (u/hex->bytes "faf4ebfd") (u/bytes-of-n 124 204))))))
      (u/chk (and (= (byte-at b (+ at (* 6 128))) 250)
                  (= (u/bslice b (+ at (* 6 128) 35) (+ at (* 7 128))) (u/bytes-of-n 93 204))))
      (u/pydict "vectors" 64 "stride" 128 "table" table "context" (u/geti rw 3) "body" body "entryFuel" 4096))))

(defn main [build out complete]
  (let [[graph producers _] (proof/load-native-producers :build build :complete complete)
        _ (.mkdir out ** :parents true :exist_ok false)
        routes (python/list)]
    (doseq [compiler producers]
      (let [scope (.joinpath out (.-stem compiler))
            _ (.mkdir scope)
            source (.joinpath scope "entry.kotoba")
            lock (.joinpath scope "source.ksl")
            calls (python/list)
            artifacts (python/dict)
            compile- (fn [name text diagnostic]
                       (.write_text source text)
                       (.write_text lock (str "KSL1\nentry " source "\nroot " scope "\nfile " (u/geti (u/pin source) "sha256") " " source "\n"))
                       (let [image (.joinpath scope (str name ".elf"))
                             env (python/dict {"PATH" "/nonexistent" "KEXE_STACK_BYTES" "8388608" "KEXE_CAP_RESOURCES_35" (str scope)})
                             args (python/list [(str compiler) "compile" (str source) "--target" "x86_64-aiueos-kernel-v1" "--artifact" "image"
                                                "--output" (str image) "--fuel" "1000000" "--source-path" (str scope)
                                                "--source-lock" (str lock) "--source-lock-sha256" (u/geti (u/pin lock) "sha256")])
                             r (subprocess/run args ** :env env :capture_output true :timeout 240)]
                         (.append calls (u/pydict "name" name "exit" (.-returncode r) "stderr" (.decode (.-stderr r))
                                                  "source" (u/pin source) "sourceText" text))
                         (.write_text (.joinpath scope "calls.json") (u/json-dump calls))
                         (if diagnostic
                           (u/chk (and (= 1 (.-returncode r)) (u/has-bytes? (.encode diagnostic) (.-stderr r))
                                       (not (u/has-bytes? (.encode "KEXE_TRAP") (.-stderr r))) (not (.exists image)))
                                  (u/geti calls -1))
                           (do (u/chk (and (= 0 (.-returncode r)) (not (u/nonempty? (.-stderr r))) (.exists image)) (u/geti calls -1))
                               (let [shape (verify image)
                                     efi (.joinpath scope (str name ".efi"))
                                     q (subprocess/run (python/list [(str compiler) "package-aiueos-boot" (str image) "--output" (str efi)])
                                                       ** :env env :capture_output true :timeout 180)]
                                 (u/chk (and (= 0 (.-returncode q)) (not (u/nonempty? (.-stderr q)))) (.-stderr q))
                                 (operator/setitem artifacts name (u/pydict "kernel" (u/pin image) "efi" (u/pin efi) "shape" shape)))))))]
        (compile- "interrupt" source-text nil)
        (compile- "wrong-marker" (.replace source-text ")) 42 0)" ")) 43 0)" 1) nil)
        (doseq [[name text code]
                [["invalid-vector" (.replace source-text "aiueos-isr-3" "aiueos-isr-64") "E7102"]
                 ["leading-zero" (.replace source-text "aiueos-isr-3" "aiueos-isr-03") "E7102"]
                 ["bool-parameter" (.replace (.replace source-text "vector :i64" "vector :bool") "(= vector 3)" "vector") "E7102"]
                 ["direct-call" (.replace source-text "(kernel-debug-break)" "(aiueos-isr-3 3 0 1052672 1)") "E7106"]
                 ["hardware-argument-root" (.replace source-text "(+ mark 1234)" "(kernel-load-u8 vector error 0)") "E7106"]
                 ["no-table" "(ns entry (:export [main]))\n(defn main [] :i64 (kernel-isr-entry-address 3))\n" "E7102"]
                 ["unknown-export" (str (.replace source-text "[main aiueos-isr-3]" "[main aiueos-isr-3 other]") "\n(defn other [] :i64 0)\n") "E7102"]]]
          (compile- name text code))
        (.append routes (u/pydict "compiler" (u/pin compiler) "artifacts" artifacts "refusals" 7))))
    (u/chk (u/deq (u/geti (u/geti routes 0) "artifacts") (u/geti (u/geti routes 1) "artifacts")))
    (let [report (u/pydict "status" "PASS_NATIVE_ISR_PACKAGING" "source" graph "routes" routes
                           "guestInterruptExecution" false "errorCodeInterruptExecution" false "fullKernel" false
                           "liveRuntime" false "nativeCDCI" false)]
      (.write_text (.joinpath out "native-isr.json") (u/json-dump report))
      (println (u/geti report "status") "64-vector layout, typed callback ABI and 7 refusal controls; interrupt execution separate"))))

(defn -main [& args]
  (let [build (u/opt args "--build") complete (u/opt args "--complete")
        out (or (u/opt args "--output") (sys/exit "--output is required"))]
    (when (= (nil? build) (nil? complete)) (sys/exit "exactly one of --build/--complete is required"))
    (main (when build (.resolve (pathlib/Path build))) (.resolve (pathlib/Path out)) (when complete (.resolve (pathlib/Path complete))))))

(when (some #(or (= % "check-aiueos-isr-native.cljc") (str/ends-with? % "/check-aiueos-isr-native.cljc")) sys/argv)
  (apply -main *command-line-args*))
