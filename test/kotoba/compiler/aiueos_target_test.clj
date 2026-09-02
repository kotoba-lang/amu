(ns kotoba.compiler.aiueos-target-test
  (:require [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]
            [kotoba.artifact.core :as artifact]
            [kotoba.compiler.packaging.pe32plus :as pe32plus]
            [kotoba.compiler.packaging.elf-fixture :as elf-fixture]
            [kotoba.kir.target :as target]))

(defn- unsigned [n] (bit-and (int n) 0xff))
(defn- read-le [bytes offset width]
  (reduce (fn [n index]
            (+ n (bit-shift-left (long (unsigned (nth bytes (+ offset index))))
                                 (* 8 index))))
          0 (range width)))

(defn- read-i32 [bytes offset]
  (let [value (read-le bytes offset 4)]
    (if (>= value 0x80000000)
      (- value 0x100000000)
      value)))

(defn- compares-against-bound?
  "Does the code compare some register against BOUND? `cmp r/m64, imm32` is
   REX.W, 0x81, a ModRM with mod=11 and reg=7, then the immediate -- and the
   low three bits of that ModRM, plus REX.B, name whichever register the
   allocator put the length in. Which register that is is not the bound check;
   pinning it made these tests fail when the allocator gained registers, while
   the check itself was still there on RDX and R8."
  [bytes bound]
  (let [imm [(bit-and bound 0xff) (bit-and (bit-shift-right bound 8) 0xff)
             (bit-and (bit-shift-right bound 16) 0xff)
             (bit-and (bit-shift-right bound 24) 0xff)]]
    (boolean
     (some (fn [[rex opcode modrm & immediate]]
             (and (contains? #{0x48 0x49} (unsigned rex))
                  (= 0x81 (unsigned opcode))
                  (= 0xf8 (bit-and (unsigned modrm) 0xf8))
                  (= imm (mapv unsigned immediate))))
           (partition 7 1 bytes)))))


(defn- le-bytes [n width]
  (mapv #(bit-and 0xff (bit-shift-right (long n) (* 8 %)))
        (range width)))

(defn- utf16-bytes [value]
  (vec (mapcat #(le-bytes (int %) 2) value)))

(defn- byte-sequence-offset [bytes needle]
  (first (filter #(= needle (subvec bytes % (+ % (count needle))))
                 (range (inc (- (count bytes) (count needle)))))))

(defn- elf64-load-segments [bytes]
  (let [program-offset (read-le bytes 32 8)
        entry-size (read-le bytes 54 2)
        entry-count (read-le bytes 56 2)]
    (->> (range entry-count)
         (map (fn [index]
                (let [offset (+ program-offset (* index entry-size))]
                  {:type (read-le bytes offset 4)
                   :flags (read-le bytes (+ offset 4) 4)
                   :offset (read-le bytes (+ offset 8) 8)
                   :vaddr (read-le bytes (+ offset 16) 8)
                   :paddr (read-le bytes (+ offset 24) 8)
                   :memsz (read-le bytes (+ offset 40) 8)})))
         (filterv #(= 1 (:type %))))))

(defn- c-string [bytes offset]
  (apply str (map char (take-while pos? (drop offset bytes)))))

(defn- aarch64-op-count [bytes opcode-mask opcode]
  (->> (partition 4 bytes)
       (map #(read-le (vec %) 0 4))
       (filter #(= opcode (bit-and opcode-mask %)))
       count))

(defn- x86-memory-opcode? [bytes opcode]
  (let [opcode-width (count opcode)]
    (some (fn [offset]
            (and (= opcode (subvec bytes offset (+ offset opcode-width)))
                 ;; The ModRM byte follows the opcode. mod=3 would be a
                 ;; register operand, not the bounded memory access promised
                 ;; by these kernel operators.
                 (not= 3 (bit-and 3 (bit-shift-right
                                     (unsigned (nth bytes (+ offset opcode-width)))
                                     6)))))
          (range (inc (- (count bytes) opcode-width 1))))))

(deftest freestanding-aiueos-profiles-have-no-host-runtime
  (doseq [[name expected]
          [[:x86_64-aiueos-uefi-v1
           {:execution :firmware :artifact :pe32+ :subsystem :efi-application
             :entry :efi_main :abi :microsoft-x64
             :entry-contract :microsoft-x64-two-arity-efi-status-v2}]
           [:x86_64-aiueos-kernel-v1
            {:execution :kernel :artifact :elf64
             :entry :aiueos_kernel_entry :abi :aiueos-kernel-v1}]
           [:x86_64-aiueos-user-v1
            {:execution :process :artifact :elf64
             :entry :aiueos_process_entry :abi :aiueos-user-v1}]]]
    (testing (str name)
      (let [profile (target/profile name)]
        (is (= :aiueos (:os profile)))
        (is (= (if (= name :x86_64-aiueos-user-v1)
                 :kotoba-aiueos-user-v1 :none)
               (:runtime profile)))
        (is (false? (:ambient-syscalls profile)))
        (is (= expected (select-keys profile (keys expected))))))))

(deftest aiueos-targets-bind-profile-identity-into-artifacts
  (doseq [name [:x86_64-aiueos-uefi-v1 :x86_64-aiueos-kernel-v1
                :x86_64-aiueos-user-v1]]
    (let [source (if (= name :x86_64-aiueos-uefi-v1)
                   "(defn main [image system-table] (+ image (* 0 system-table)))"
                   "(defn main [] (+ 40 2))")
          artifact (:artifact (compiler/compile-source source name))]
        (is (= name (:target artifact)))
        (is (= (target/profile name) (:target-profile artifact)))
        (is (= (if (= name :x86_64-aiueos-user-v1)
                 :kotoba-aiueos-user-v1 :none)
               (get-in artifact [:target-profile :runtime]))))))

(deftest kernel-target-emits-a-real-freestanding-elf64-image
  (let [{:keys [binary]} (compiler/compile-source "(defn main [] (+ 40 2))"
                                                  :x86_64-aiueos-kernel-v1)
        bytes (:bytes binary)
        section-offset (read-le bytes 40 8)
        section-count (read-le bytes 60 2)
        rw-segment (some #(when (= 6 (:flags %)) %) (elf64-load-segments bytes))]
    (is (= [0x7f 0x45 0x4c 0x46] (subvec bytes 0 4)))
    (is (= 2 (nth bytes 4)) "ELFCLASS64")
    (is (= 2 (read-le bytes 16 2)) "ET_EXEC, not a host-linked object")
    (is (= 0x3e (read-le bytes 18 2)) "EM_X86_64")
    (is (= (:entry-address binary) (read-le bytes 24 8)))
    (is (= 2 (read-le bytes 56 2)) "RX text and RW context PT_LOAD segments")
    (is (= 4 section-count))
    (is (= (* 4 64) (- (count bytes) section-offset)))
    (is (= [:text :data :shstrtab] (:sections binary)))
    (is (empty? (:imports binary)))
    (is (nil? (:interpreter binary)))
    (is (= :aiueos_kernel_entry (:entry binary)))
    ;; Live-boot shim in elf64.clj: cli; lea rsp,[rip+disp]. rdi preservation
    ;; and r9 init still happen, later in the same 144-byte slot, after GDT.
    (is (= [0xfa 0x48 0x8d 0x25] (subvec bytes 0x1000 0x1004))
        "cli; lea rsp,[rip+disp]")
    (let [text (subvec bytes 0x1000 (+ 0x1000 144))]
      (is (some #(= [0x48 0x89 0x3d] %) (partition 3 1 text))
          "preserves loader rdi in context+80")
      (is (some #(= [0x4c 0x8d 0x0d] %) (partition 3 1 text))
          "initializes r9 from the image context"))
    ;; Context fuel is initialized to 512; no host process populates it.
    (is (some? rw-segment) "RW context PT_LOAD exists")
    (is (= 512 (read-le bytes (+ (:offset rw-segment) 8) 8)))))

(deftest kernel-target-lowers-privileged-intrinsics-without-imports
  (let [source (str "(defn main [] "
                    "(let [cr0 (kernel-read-cr0) "
                    "      wp (kernel-write-cr0 cr0) "
                    "      cr3 (kernel-read-cr3) "
                    "      written (kernel-write-cr3 cr3) "
                    "      flushed (kernel-invlpg 4096) "
                    "      marker (kernel-out-u8 233 75)] "
                    "  (kernel-out-u32 244 (+ cr0 wp cr3 written flushed marker))))")
        artifact (:artifact (compiler/compile-source source :x86_64-aiueos-kernel-v1))
        code (:code artifact)]
    (is (empty? (:imports artifact)))
    (is (some #(= [0x41 0x0f 0x20 0xc2] %) (partition 4 1 code)) "mov r10,cr0")
    (is (some #(= [0x41 0x0f 0x22 0xc2] %) (partition 4 1 code)) "mov cr0,r10")
    (is (some #(= [0x41 0x0f 0x20 0xda] %) (partition 4 1 code)) "mov r10,cr3")
    (is (some #(= [0x41 0x0f 0x22 0xda] %) (partition 4 1 code)) "mov cr3,r10")
    (is (some #(= [0x41 0x0f 0x01 0x3a] %) (partition 4 1 code)) "invlpg [r10]")
    (is (some #{0xee} code) "out dx,al")
    (is (some #{0xef} code) "out dx,eax")))

(deftest kernel-target-seals-page-fault-handler-idt-and-three-probes
  (let [source (str "(defn main [] "
                    "(let [handler (kernel-page-fault-handler-address) "
                    "      cs (kernel-read-cs) "
                    "      loaded (kernel-load-idt handler 10)] "
                    "  (+ loaded cs (kernel-probe-guard-write) "
                    "     (kernel-probe-text-write) (kernel-probe-nx-execute))))")
        {:keys [artifact binary]} (compiler/compile-source source :x86_64-aiueos-kernel-v1)
        code (:code artifact)
        rw-segment (some #(when (= 6 (:flags %)) %)
                         (elf64-load-segments (:bytes binary)))
        contains-bytes? (fn [needle]
                          (boolean (some #{needle} (partition (count needle) 1 code))))]
    (is (empty? (:imports artifact)))
    (is (contains-bytes? [0x41 0x0f 0x20 0xd2 0x4c 0x8b 0x1c 0x24])
        "handler reads CR2 and the CPU-pushed error code")
    (is (contains-bytes? [0x66 0x41 0x8c 0xca]) "current CS selector")
    (is (contains-bytes? [0x41 0x0f 0x01 0x1a]) "lidt [r10]")
    (is (contains-bytes? [0x0f 0x01 0x0c 0x24]) "sidt readback")
    (is (contains-bytes? [0xc6 0x04 0x25 0x00 0x00 0x10 0x00 0x00]) "guard write")
    (is (contains-bytes? [0xc6 0x04 0x25 0x00 0x10 0x10 0x00 0x00]) "text write")
    (is (some? rw-segment) "RW context PT_LOAD exists")
    ;; The NX probe still loads 0x110000 (machine_ir / x86_64). elf64.clj
    ;; places the RW PT_LOAD at a dynamic data offset (minimum 0x108000), so
    ;; the encoding is not the segment start. 0x110000 must still fall inside
    ;; that mapping or the probe executes a page the image did not mark NX.
    (let [nx-addr 0x110000]
      (is (contains-bytes? (into [0x49 0xba] (le-bytes nx-addr 8)))
          "NX execute target 0x110000")
      (is (<= (:vaddr rw-segment) nx-addr)
          "NX address at or after RW vaddr")
      (is (< nx-addr (+ (:vaddr rw-segment) (:memsz rw-segment)))
          "NX address inside RW PT_LOAD"))))

(deftest kernel-target-loads-versioned-boot-info-from-its-private-context
  (let [artifact (:artifact (compiler/compile-source
                              "(defn main [] (kernel-boot-info))"
                              :x86_64-aiueos-kernel-v1))]
    (is (some #(= [0x4d 0x8b 0x51 0x50] %)
              (partition 4 1 (:code artifact))))
    (is (empty? (:imports artifact)))))

(deftest privileged-intrinsics-are-rejected-outside-the-kernel-target
  (doseq [target [:x86_64-linux-kotoba-v1 :x86_64-aiueos-user-v1]]
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"requires the aiueos kernel target"
          (compiler/compile-source "(defn main [] (kernel-read-cr3))" target)))))

(deftest compiler-packages-an-embedded-kernel-uefi-boot-application
  (let [kernel (get-in (compiler/compile-source
                        "(defn main [] (kernel-out-u32 244 16))"
                        :x86_64-aiueos-kernel-v1) [:binary :bytes])
        first-image (pe32plus/package-embedded-kernel kernel)
        second-image (pe32plus/package-embedded-kernel kernel)
        bytes (:bytes first-image)]
    (is (= :pe32+-embedded-kernel/v3 (:format first-image)))
    (is (= {:bytes 16480 :memory-map-offset 96 :memory-map-capacity 16384
            :rx-limit-offset 56 :rw-start-offset 64 :rw-end-offset 72
            :kernel-scratch-address-offset 80
            :kernel-scratch-pages-offset 88 :kernel-scratch-pages 14}
           (:boot-info-layout first-image)))
    (is (= [0x4d 0x5a] (subvec bytes 0 2)))
    (is (= [0x50 0x45 0 0] (subvec bytes 0x80 0x84)))
    (is (= 3 (read-le bytes (+ 0x84 2) 2)))
    (is (= 10 (read-le bytes (+ 0x98 68) 2)) "EFI application subsystem")
    (is (empty? (:imports first-image)))
    (is (not-any? #(= [0x41 0xff 0x56 0x40] %)
                  (partition 4 1 bytes))
        "the C-free loader does not AllocatePool a second authority region")
    (is (some #(= [0 0x40 0 0] %)
              (partition 4 1 bytes))
        "GetMemoryMap is bounded to the inline 16 KiB region")
    (is (some #(= [0xb9 0 0 0 0 0xba 2 0 0 0
                    0x41 0xb8 0x0e 0 0 0] %)
              (partition 16 1 bytes))
        "AllocateAnyPages reserves fourteen loader-owned scratch pages")
    (is (= bytes (:bytes second-image)) "embedded boot image is reproducible")
    (let [diagnostic (pe32plus/package-embedded-kernel
                      kernel [] {:k16-preflight? true})
          diagnostic-bytes (:bytes diagnostic)
          kernel-entry (read-le kernel 24 8)
          kernel-entry-segment (some #(when (= 5 (:flags %)) %)
                                     (elf64-load-segments kernel))
          kernel-entry-offset (+ (:offset kernel-entry-segment)
                                 (- kernel-entry (:paddr kernel-entry-segment)))
          returnable-entry (+ kernel-entry 73
                              (read-i32 kernel (+ kernel-entry-offset 69)))
          context-address (+ kernel-entry 68
                             (read-i32 kernel (+ kernel-entry-offset 64)))
          pci-probe [0x66 0xba 0xf8 0x0c 0xb8 0x00 0x00 0x02 0x80
                     0xef 0x66 0xba 0xfc 0x0c 0xed 0x3d
                     0xec 0x10 0x25 0x81]
          probe-offset (byte-sequence-offset diagnostic-bytes pci-probe)
          branch-offset (+ probe-offset (count pci-probe))
          exit-boot-offset (+ branch-offset 6
                              (read-i32 diagnostic-bytes (+ branch-offset 2)))]
      (is (:k16-preflight? diagnostic))
      (is (= returnable-entry (:k16-preflight-returnable-entry diagnostic)))
      (is (= context-address (:k16-preflight-context-address diagnostic)))
      (is (some #(= (vec (concat [0x49 0xb9] (le-bytes context-address 8)
                                  [0x49 0x89 0x79 0x50 0x48 0xb8]
                                  (le-bytes returnable-entry 8)
                                  [0xff 0xd0])) %)
                (partition 26 1 diagnostic-bytes))
          "preflight installs the kernel context and calls returnable main")
      (is (some? probe-offset)
          "K16 preflight is gated by exact 02:00.0 RTL8125 identity")
      (is (= [0x0f 0x85] (subvec diagnostic-bytes branch-offset
                                  (+ branch-offset 2))))
      (is (= [0x4c 0x89 0xe1 0x48 0x8b 0x15]
             (subvec diagnostic-bytes exit-boot-offset
                     (+ exit-boot-offset 6)))
          "the non-K16 rel32 branch lands at the ExitBootServices path")
      (is (some #(= (utf16-bytes "AIUEOS K16 PREFLIGHT ENTER\r\n") %)
                (partition (count (utf16-bytes
                                   "AIUEOS K16 PREFLIGHT ENTER\r\n"))
                           1 diagnostic-bytes)))
      (is (some #(= (utf16-bytes "AIUEOS K16 PREFLIGHT RTL8125\r\n") %)
                (partition (count (utf16-bytes
                                   "AIUEOS K16 PREFLIGHT RTL8125\r\n"))
                           1 diagnostic-bytes)))
      (is (some #(= (utf16-bytes "AIUEOS K16 PREFLIGHT STATUS 00\r\n") %)
                (partition (count (utf16-bytes
                                   "AIUEOS K16 PREFLIGHT STATUS 00\r\n"))
                           1 diagnostic-bytes)))
      (is (some #(= [0xfa 0xf4 0xeb 0xfd] %)
                (partition 4 1 diagnostic-bytes))
          "physical preflight holds the status screen instead of retrying PXE"))
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"x86-64 ET_EXEC"
          (pe32plus/package-embedded-kernel (vec (repeat 128 0)))))))

(deftest compiler-packages-a-bounded-external-rt-payload
  (let [kernel (get-in (compiler/compile-source
                        "(defn main [] (kernel-out-u32 244 16))"
                        :x86_64-aiueos-kernel-v1) [:binary :bytes])
        payload (vec (range 128))
        image (pe32plus/package-embedded-kernel kernel payload)
        bytes (:bytes image)
        pe-offset (read-le bytes 0x3c 4)
        section-table (+ pe-offset 24 (read-le bytes (+ pe-offset 20) 2))
        text-rva (read-le bytes (+ section-table 12) 4)
        text-raw (read-le bytes (+ section-table 20) 4)
        data-rva (read-le bytes (+ section-table 40 12) 4)
        store-prefix [0xb8 0x80 0x00 0x00 0x00 0x48 0x89 0x05]
        store-offset (byte-sequence-offset bytes store-prefix)
        displacement (read-le bytes (+ store-offset 8) 4)
        store-next-rva (+ text-rva (- (+ store-offset 12) text-raw))]
    (is (= {:bytes 16624 :memory-map-offset 112
            :memory-map-capacity 16384
            :rx-limit-offset 56 :rw-start-offset 64 :rw-end-offset 72
            :kernel-scratch-address-offset 80
            :kernel-scratch-pages-offset 88 :kernel-scratch-pages 14
            :payload-offset 16496
            :payload-bytes 128}
           (:boot-info-layout image)))
    (is (= (artifact/sha256 payload) (:embedded-payload-sha256 image)))
    (is (= (+ data-rva 120) (+ store-next-rva displacement))
        "payload length store follows the v4 scratch authority fields")
    (is (= (:bytes image)
           (:bytes (pe32plus/package-embedded-kernel kernel payload))))
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"exceeds 16 KiB"
          (pe32plus/package-embedded-kernel kernel (vec (repeat 16385 0)))))))

(deftest pe32plus-refuses-a-paddr-outside-the-pt-load-contract
  ;; The JVM twin of `test/nbb/run.cljs`'s pe32plus case. Same fixture bytes,
  ;; same assertion. This side has always been correct; it is here so that the
  ;; two runtimes are held to one statement rather than to two descriptions of
  ;; one, and so the fixture has a caller that fails if its shape drifts.
  (let [error (is (thrown-with-msg?
                   clojure.lang.ExceptionInfo #"PT_LOAD contract rejected"
                   (pe32plus/package-embedded-kernel
                    (elf-fixture/kernel-with-out-of-range-paddr))))]
    (is (= elf-fixture/paddr-above-the-bound
           (:paddr (first (:segments (ex-data error)))))
        "refusing for the right reason means having read all eight bytes")))

(deftest aarch64-kernel-target-packages-a-freestanding-elf
  (testing "a bounded-store Kotoba kernel compiles to an EM_AARCH64 ELF64"
    (let [source "(defn main [] (kernel-store-u8 150994944 8 0 72))"
          result (compiler/compile-source source :aarch64-aiueos-kernel-v1)
          bytes (get-in result [:binary :bytes])]
      (is (= [0x7f 0x45 0x4c 0x46] (subvec bytes 0 4)) "ELF magic")
      (is (= 2 (read-le bytes 4 1)) "ELFCLASS64")
      (is (= 2 (read-le bytes 16 2)) "ET_EXEC")
      (is (= 0xb7 (read-le bytes 18 2)) "EM_AARCH64")
      (is (= 0x101000 (read-le bytes 24 8)) "entry = image text base")
      (is (= 2 (read-le bytes 56 2)) "two PT_LOAD program headers (text + context)")
      (is (= :aiueos_kernel_entry (get-in result [:binary :entry])))))
  (testing "kernel intrinsics are rejected on a non-kernel aarch64 target"
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"requires the aiueos kernel target"
          (compiler/compile-source "(defn main [] (kernel-store-u8 1 8 0 0))"
                                   :aarch64-kotoba-v1))))
  (testing "the aarch64 kernel image is reproducible"
    (let [src "(defn main [] (kernel-store-u8 150994952 8 0 1))"
          a (get-in (compiler/compile-source src :aarch64-aiueos-kernel-v1) [:binary :bytes])
          b (get-in (compiler/compile-source src :aarch64-aiueos-kernel-v1) [:binary :bytes])]
      (is (= a b))))
  (testing "u32 MMIO intrinsics (virtio registers) compile to memory ldr/str"
    (let [artifact (:artifact (compiler/compile-source
                               "(defn main [] (let [m (kernel-load-u32 167772160 512 0)] (kernel-store-u32 167772160 512 112 m)))"
                               :aarch64-aiueos-kernel-v1))
          code (:code artifact)]
      (is (pos? (aarch64-op-count code 0xffc00000 0xb9400000)) "ldr w?,[x?] (u32 load)")
      (is (pos? (aarch64-op-count code 0xffc00000 0xb9000000)) "str w?,[x?] (u32 store)")))
  (testing "u16 MMIO intrinsics compile to real halfword transfers"
    (let [artifact (:artifact (compiler/compile-source
                               "(defn main [] (let [m (kernel-load-u16 167772160 512 2)] (kernel-store-u16 167772160 512 144 m)))"
                               :aarch64-aiueos-kernel-v1))
          code (:code artifact)]
      (is (pos? (aarch64-op-count code 0xffc00000 0x79400000)) "ldrh w?,[x?]")
      (is (pos? (aarch64-op-count code 0xffc00000 0x79000000)) "strh w?,[x?]"))))

(deftest do-sequences-side-effects-exactly-once
  (testing "each `do` subexpression emits its store exactly once, in order"
    (let [artifact (:artifact (compiler/compile-source
                               "(defn main [] (do (kernel-store-u8 100 8 0 65) (kernel-store-u8 100 8 0 66) (kernel-store-u8 100 8 0 67)))"
                               :aarch64-aiueos-kernel-v1))
          code (:code artifact)
          strb (aarch64-op-count code 0xffc00000 0x39000000)]
      (is (= 3 strb) "three distinct strb w?,[x?] -- one per do subexpression, none dropped or duplicated")))
  (testing "a single-expression do collapses to the expression"
    (is (= (get-in (compiler/compile-source "(defn main [] (kernel-store-u8 100 8 0 65))" :aarch64-aiueos-kernel-v1)
                   [:artifact :code])
           (get-in (compiler/compile-source "(defn main [] (do (kernel-store-u8 100 8 0 65)))" :aarch64-aiueos-kernel-v1)
                   [:artifact :code]))))
  (testing "an empty do is rejected"
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"do requires at least one expression"
          (compiler/compile-source "(defn main [] (do))" :aarch64-aiueos-kernel-v1))))
  (testing "do works on a pure target too (returns the last value)"
    (is (= 3 (get-in (compiler/compile-source "(defn main [] (do 1 2 3))" :aarch64-kotoba-v1)
                     [:artifact :value])))))

(deftest x86-loop-recur-reuses-its-native-stack-frame
  (let [source "(defn main [] (loop [i 0 acc 0] (if (= i 20) acc (recur (+ i 1) (+ acc i)))))"
        artifact (:artifact (compiler/compile-source source :x86_64-aiueos-kernel-v1))
        {:keys [offset length]} (get-in artifact [:exports '__kotoba_loop_1])
        helper (subvec (:code artifact) offset (+ offset length))]
    (is (= 190 (:value artifact)))
    (is (some #(= [0x48 0x81 0xc4] %) (partition 3 1 helper))
        "tail recur releases the current MIR-owned frame")
    (is (some #(= [0x49 0xff 0x49 0x08] %) (partition 4 1 helper))
        "every back edge still consumes fuel")
    (is (some #{0xe9} helper) "tail recur branches to the function entry")
    (is (not-any? #{0xe8} helper) "tail recur emits no native self-call")))

(deftest x86-non-tail-recursion-remains-a-call
  (let [source "(defn fact [n] (if (<= n 1) 1 (* n (fact (- n 1))))) (defn main [] (fact 10))"
        artifact (:artifact (compiler/compile-source source :x86_64-aiueos-kernel-v1))
        {:keys [offset length]} (get-in artifact [:exports 'fact])
        fact-code (subvec (:code artifact) offset (+ offset length))]
    (is (= 3628800 (:value artifact)))
    (is (some #{0xe8} fact-code)
        "a recursive call nested under multiplication is not a tail position")))

(deftest kernel-target-emits-linkable-relocatable-probe-object
  (let [{:keys [object]} (compiler/compile-source "(defn main [] 42)"
                                                  :x86_64-aiueos-kernel-v1)
        bytes (:bytes object)
        section-offset (read-le bytes 40 8)
        section #(-> section-offset (+ (* % 64)))
        text (section 1)
        data (section 2)
        rela (section 3)
        symtab (section 4)
        strtab (section 5)
        strtab-offset (read-le bytes (+ strtab 24) 8)
        probe-symbol (+ (read-le bytes (+ symtab 24) 8) (* 4 24))]
    (is (= [0x7f 0x45 0x4c 0x46] (subvec bytes 0 4)))
    (is (= 1 (read-le bytes 16 2)) "ET_REL")
    (is (= 0x3e (read-le bytes 18 2)) "EM_X86_64")
    (is (zero? (read-le bytes 24 8)) "relocatable objects have no entry")
    (is (zero? (read-le bytes 32 8)) "no program headers/dynamic loader")
    (is (= 7 (read-le bytes 60 2)))
    (is (= (* 7 64) (- (count bytes) section-offset)))
    (is (= 1 (read-le bytes (+ text 4) 4)) "SHT_PROGBITS .text")
    (is (= 0x6 (read-le bytes (+ text 8) 8)) "ALLOC|EXEC")
    (is (= 0x3 (read-le bytes (+ data 8) 8)) "ALLOC|WRITE")
    (is (= 4 (read-le bytes (+ rela 4) 4)) "SHT_RELA")
    (is (= 4 (read-le bytes (+ rela 40) 4)) "relocation links .symtab")
    (is (= 1 (read-le bytes (+ rela 44) 4)) "relocation applies to .text")
    (is (= 2 (read-le bytes (+ (read-le bytes (+ rela 24) 8) 8) 4))
        "R_X86_64_PC32")
    (is (= 2 (unsigned-bit-shift-right
              (read-le bytes (+ (read-le bytes (+ rela 24) 8) 8) 8) 32))
        "relocation selects local .data section symbol")
    (is (= -4 (unchecked-long
               (read-le bytes (+ (read-le bytes (+ rela 24) 8) 16) 8))))
    (is (= 2 (read-le bytes (+ symtab 4) 4)) "SHT_SYMTAB")
    (is (= 4 (read-le bytes (+ symtab 44) 4)) "first global symbol index")
    (is (= "kotoba_aiueos_probe"
           (c-string bytes (+ strtab-offset (read-le bytes probe-symbol 4)))))
    (is (= 0x12 (nth bytes (+ probe-symbol 4))) "STB_GLOBAL|STT_FUNC")
    (is (= 1 (read-le bytes (+ probe-symbol 6) 2)) "defined in .text")
    (is (= [:text :data :rela.text :symtab :strtab :shstrtab]
           (:sections object)))
    (is (= "kotoba_aiueos_probe" (:export object)))
    (is (= :sysv (:abi object)))
    (is (= [{:section :text :offset 3 :type :r-x86-64-pc32
             :symbol :data :addend -4}]
           (:relocations object)))
    (is (empty? (:imports object)))
    (is (nil? (:interpreter object)))
    ;; Public wrapper begins with LEA r9,[RIP+disp32], whose immediate is
    ;; resolved by the single .rela.text record at link time.
    (is (= [0x4c 0x8d 0x0d 0 0 0 0] (subvec bytes 64 71)))))

(deftest elf64-packaging-is-not-applied-to-firmware-or-host-targets
  (is (nil? (:binary (compiler/compile-source "(defn main [] 0)"
                                              :x86_64-linux-kotoba-v1)))))

(deftest user-target-emits-loadable-cpl3-elf64-image
  (let [{:keys [binary]} (compiler/compile-source "(defn main [] (+ 40 2))"
                                                  :x86_64-aiueos-user-v1)
        bytes (:bytes binary)]
    (is (= 2 (read-le bytes 16 2)))
    (is (= 0x1e1000 (:entry-address binary)))
    (is (= 0x1e2000 (:result-address binary)))
    (is (= 2 (read-le bytes 56 2)))
    (is (= [0x4c 0x8d 0x0d] (subvec bytes 0x1000 0x1003)))
    (is (= [0x48 0x89 0x05] (subvec bytes 0x100c 0x100f)))
    (is (= :kotoba-sysv-context-r9-aiueos-runtime-v2 (:entry-contract binary)))
    (is (= 80 (:runtime-handle-offset binary)))
    (is (empty? (:imports binary)))))

(deftest user-target-lowers-admitted-capability-to-aiueos-runtime-syscall
  (let [{:keys [binary]}
        (compiler/compile-source "(defn main [] (cap-call 2 0))"
                                 :x86_64-aiueos-user-v1
                                 {:allow #{[:cap/call 2]}})
        bytes (:bytes binary)]
    (is (= 4 (read-le bytes (+ 0x2000 16) 1)) "only capability 2 is admitted")
    (is (= 0x1e1020 (read-le bytes (+ 0x2000 48) 8)))
    (is (= [0xb8 5 0 0 0 0x48 0x8b 0x7f 0x50 0x0f 5 0xc3]
           (subvec bytes 0x1020 0x102c)))
    (is (zero? (read-le bytes (+ 0x2000 80) 8))
        "the loader, never the compiler, installs the domain-owned handle")))

(deftest kernel-target-exports-four-argument-journal-planner
  (let [{:keys [object]}
        (compiler/compile-source
         "(defn aiueos-journal-plan [valid0 sequence0 valid1 sequence1] (if valid0 sequence0 sequence1)) (defn main [] 0)"
         :x86_64-aiueos-kernel-v1)]
    (is (= "kotoba_aiueos_journal_plan" (:export object)))
    (is (= :sysv (:abi object)))
    (is (empty? (:imports object)))))

(deftest kernel-target-lowers-bounded-byte-load-without-imports
  (let [{:keys [object]}
        (compiler/compile-source
         "(defn aiueos-journal-plan [base length index unused] (kernel-load-u8 base length index)) (defn main [] 0)"
         :x86_64-aiueos-kernel-v1)
        bytes (:bytes object)]
    (is (= "kotoba_aiueos_journal_plan" (:export object)))
    (is (empty? (:imports object)))
    (is (x86-memory-opcode? bytes [0x0f 0xb6]))
    (is (some #(= [0x0f 0x0b] %) (partition 2 1 bytes)))))

(deftest bounded-byte-load-requires-base-length-index
  (is (thrown-with-msg?
       clojure.lang.ExceptionInfo #"kernel memory operation arity mismatch"
       (compiler/check-source "(defn main [] (kernel-load-u8 1 2))"))))

(deftest kernel-target-exports-bounded-fnv-function
  (let [source "(defn aiueos-fnv1a [base length] (bit-xor (kernel-load-u8 base length 0) 7)) (defn main [] 0)"
        {:keys [object]} (compiler/compile-source source :x86_64-aiueos-kernel-v1)]
    (is (= "kotoba_aiueos_fnv1a" (:export object)))
    (is (empty? (:imports object)))
    (is (some #(= [0x49 0xc7 0x41 0x08 0x00 0x04 0x00 0x00] %)
              (partition 8 1 (:bytes object))))))

(deftest kernel-target-exports-wide-bounded-sha256-function
  (let [source "(defn aiueos-sha256 [input input-length output workspace workspace-length] (kernel-store-u8 output 32 0 (kernel-load-u8-16k input input-length 0))) (defn main [] 0)"
        {:keys [object]} (compiler/compile-source source :x86_64-aiueos-kernel-v1)
        bytes (:bytes object)]
    (is (= "kotoba_aiueos_sha256" (:export object)))
    (is (empty? (:imports object)))
    (is (some #(= [0x48 0x81 0xf9 0x00 0x40 0x00 0x00] %)
              (partition 7 1 bytes))
        "the SHA input primitive admits at most 16 KiB")
    (is (compares-against-bound? bytes 0x200)
        "the output store retains the 512-byte bound")
    (is (some #(= [0x49 0xc7 0x41 0x08 0x80 0x96 0x98 0x00] %)
              (partition 8 1 bytes))
        "the freestanding wrapper supplies ten million metered iterations")))

(deftest kernel-target-exports-bounded-rsa2048-verifier
  (let [source "(defn aiueos-rsa2048-sha256-verify [signature digest workspace workspace-length unused] (if (< workspace-length 1280) 0 (kernel-store-u8-4k workspace workspace-length 0 (kernel-load-u8-4k signature 256 0)))) (defn main [] 0)"
        {:keys [object]} (compiler/compile-source source :x86_64-aiueos-kernel-v1)
        bytes (:bytes object)]
    (is (= "kotoba_aiueos_rsa2048_sha256_verify" (:export object)))
    (is (empty? (:imports object)))
    (is (compares-against-bound? bytes 0x1000)
        "RSA inputs and workspace retain the compiler's 4 KiB bound")
    (is (some #(= [0x49 0xc7 0x41 0x08 0x80 0xb2 0xe6 0x0e] %)
              (partition 8 1 bytes))
        "the RSA wrapper supplies 250 million metered iterations")))

(deftest kernel-target-exports-bounded-digest-comparison
  (let [source "(defn aiueos-digest-equal [expected actual length] (bit-xor (kernel-load-u8 expected length 0) (kernel-load-u8 actual length 0))) (defn main [] 0)"
        {:keys [object]} (compiler/compile-source source :x86_64-aiueos-kernel-v1)
        bytes (:bytes object)]
    (is (= "kotoba_aiueos_digest_equal" (:export object)))
    (is (empty? (:imports object)))
    (is (compares-against-bound? bytes 0x200)
        "digest inputs retain the compiler's 512-byte bound")
    (is (some #(= [0x49 0xc7 0x41 0x08 0x00 0x04 0x00 0x00] %)
              (partition 8 1 bytes))
        "the comparison wrapper remains fuel-metered")))

(deftest kernel-target-exports-bounded-app-catalog-policy
  (let [source "(defn aiueos-app-catalog-valid [catalog length capacity catalog-sector signature-sector] (if (= (kernel-load-u8 catalog length 0) 65) capacity 0)) (defn main [] 0)"
        {:keys [object]} (compiler/compile-source source :x86_64-aiueos-kernel-v1)
        bytes (:bytes object)]
    (is (= "kotoba_aiueos_app_catalog_valid" (:export object)))
    (is (empty? (:imports object)))
    (is (compares-against-bound? bytes 0x200)
        "catalog reads retain the compiler's 512-byte bound")
    (is (some #(= [0x49 0xc7 0x41 0x08 0x00 0x04 0x00 0x00] %)
              (partition 8 1 bytes))
        "the catalog policy remains fuel-metered")))

(deftest kernel-target-exports-bounded-app-lookup-plan
  (let [source "(defn aiueos-app-lookup-plan [id metadata count stride length] (bit-xor (kernel-load-u8 id 16 0) (kernel-load-u8 metadata length 0))) (defn main [] 0)"
        {:keys [object]} (compiler/compile-source source :x86_64-aiueos-kernel-v1)
        bytes (:bytes object)]
    (is (= "kotoba_aiueos_app_lookup_plan" (:export object)))
    (is (empty? (:imports object)))
    (is (compares-against-bound? bytes 0x200))
    (is (some #(= [0x49 0xc7 0x41 0x08 0x00 0x04 0x00 0x00] %)
              (partition 8 1 bytes)))))

(deftest kernel-target-exports-bounded-user-elf-policy
  (let [source "(defn aiueos-user-elf-valid [image length] (kernel-load-u8-16k image length 0)) (defn main [] 0)"
        {:keys [object]} (compiler/compile-source source :x86_64-aiueos-kernel-v1)
        bytes (:bytes object)]
    (is (= "kotoba_aiueos_user_elf_valid" (:export object)))
    (is (empty? (:imports object)))
    (is (some #(= [0x48 0x81 0xf9 0x00 0x40 0x00 0x00] %)
              (partition 7 1 bytes)))
    (is (some #(= [0x49 0xc7 0x41 0x08 0x00 0x04 0x00 0x00] %)
              (partition 8 1 bytes)))))

(deftest kernel-target-exports-bounded-user-context-builder
  (let [source "(defn aiueos-user-context-build [stack entry argument user-stack] (kernel-store-u8-4k stack 4096 3936 entry)) (defn main [] 0)"
        {:keys [object]} (compiler/compile-source source :x86_64-aiueos-kernel-v1)
        bytes (:bytes object)]
    (is (= "kotoba_aiueos_user_context_build" (:export object)))
    (is (empty? (:imports object)))
    (is (compares-against-bound? bytes 0x1000))
    (is (some #(= [0x49 0xc7 0x41 0x08 0x00 0x00 0x01 0x00] %)
              (partition 8 1 bytes)))))

(deftest kernel-target-exports-page-mapping-plan
  (let [source "(defn aiueos-page-mapping-plan [process kind size active existing] (+ process (+ kind (+ size (+ active existing))))) (defn main [] 0)"
        {:keys [object]} (compiler/compile-source source :x86_64-aiueos-kernel-v1)]
    (is (= "kotoba_aiueos_page_mapping_plan" (:export object)))
    (is (empty? (:imports object)))))

(deftest kernel-target-exports-bounded-process-create-plan
  (let [source "(defn aiueos-process-create-plan [table length domain count stride] (kernel-load-u8 table length 0)) (defn main [] 0)"
        {:keys [object]} (compiler/compile-source source :x86_64-aiueos-kernel-v1)
        bytes (:bytes object)]
    (is (= "kotoba_aiueos_process_create_plan" (:export object)))
    (is (empty? (:imports object)))
    (is (compares-against-bound? bytes 0x200))))

(deftest kernel-target-exports-process-teardown-plan
  (let [source "(defn aiueos-process-teardown-plan [domain reaped revoked reclaimed stage] (+ domain (+ reaped (+ revoked (+ reclaimed stage))))) (defn main [] 0)"
        {:keys [object]} (compiler/compile-source source :x86_64-aiueos-kernel-v1)]
    (is (= "kotoba_aiueos_process_teardown_plan" (:export object)))
    (is (empty? (:imports object)))))

(deftest kernel-target-exports-bounded-task-slot-plan
  (let [source "(defn aiueos-task-slot-plan [table length count stride request] (kernel-load-u8 table length 0)) (defn main [] 0)"
        {:keys [object]} (compiler/compile-source source :x86_64-aiueos-kernel-v1)]
    (is (= "kotoba_aiueos_task_slot_plan" (:export object)))
    (is (empty? (:imports object)))))

(deftest kernel-target-exports-bounded-scheduler-dispatch-plan
  (let [source "(defn aiueos-scheduler-dispatch-plan [table length count stride state] (kernel-load-u8 table length 0)) (defn main [] 0)"
        {:keys [object]} (compiler/compile-source source :x86_64-aiueos-kernel-v1)]
    (is (= "kotoba_aiueos_scheduler_dispatch_plan" (:export object)))
    (is (empty? (:imports object)))))

(deftest kernel-target-exports-bounded-task-exit-route
  (let [source "(defn aiueos-task-exit-route [table length count stride domain] (kernel-load-u8 table length 0)) (defn main [] 0)"
        {:keys [object]} (compiler/compile-source source :x86_64-aiueos-kernel-v1)]
    (is (= "kotoba_aiueos_task_exit_route" (:export object)))
    (is (empty? (:imports object)))))

(deftest kernel-target-exports-service-task-transition
  (let [source "(defn aiueos-service-task-transition [action active slot current task-active] action) (defn main [] 0)"
        {:keys [object]} (compiler/compile-source source :x86_64-aiueos-kernel-v1)]
    (is (= "kotoba_aiueos_service_task_transition" (:export object)))
    (is (empty? (:imports object)))))

(deftest kernel-target-exports-capability-mutation-plan
  (let [source "(defn aiueos-capability-mutation-plan [action generation type state request] action) (defn main [] 0)"
        {:keys [object]} (compiler/compile-source source :x86_64-aiueos-kernel-v1)]
    (is (= "kotoba_aiueos_capability_mutation_plan" (:export object)))
    (is (empty? (:imports object)))))

(deftest bounded-kernel-memory-is-rejected-for-host-targets
  (let [source "(defn read-byte [base length index] (kernel-load-u8 base length index)) (defn main [] 0)"]
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"requires the aiueos kernel target"
         (compiler/compile-source source :x86_64-linux-kotoba-v1)))))

(deftest wide-bounded-kernel-memory-is-rejected-for-host-targets
  (let [source "(defn read-byte [base length index] (kernel-load-u8-16k base length index)) (defn main [] 0)"]
    (is (thrown-with-msg?
         clojure.lang.ExceptionInfo #"requires the aiueos kernel target"
         (compiler/compile-source source :x86_64-linux-kotoba-v1)))))

(deftest kernel-target-exports-record-validators
  (doseq [[entry expected]
          [['aiueos-journal-record-valid "kotoba_aiueos_journal_record_valid"]
           ['aiueos-object-transaction-valid "kotoba_aiueos_object_transaction_valid"]
           ['aiueos-object-transaction-route "kotoba_aiueos_object_transaction_route"]]]
    (let [source (str "(defn " entry " [base length] (bit-and (kernel-load-u8 base length 0) 255)) (defn main [] 0)")
          {:keys [object]} (compiler/compile-source source :x86_64-aiueos-kernel-v1)]
      (is (= expected (:export object)))
      (is (empty? (:imports object))))))

(deftest kernel-target-exports-storage-read-validators
  (doseq [[entry params expected]
          [['aiueos-mutable-object-valid '[object object-length sequence transaction transaction-length]
            "kotoba_aiueos_mutable_object_valid"]
           ['aiueos-superblock-valid '[base length] "kotoba_aiueos_superblock_valid"]]]
    (let [source (str "(defn " entry " " params " 1) (defn main [] 0)")
          {:keys [object]} (compiler/compile-source source :x86_64-aiueos-kernel-v1)]
      (is (= expected (:export object)))
      (is (empty? (:imports object))))))

(deftest kernel-target-lowers-bounded-byte-store
  (let [source "(defn aiueos-journal-record-build [base length value] (kernel-store-u8 base length 0 value)) (defn main [] 0)"
        {:keys [object]} (compiler/compile-source source :x86_64-aiueos-kernel-v1)]
    (is (= "kotoba_aiueos_journal_record_build" (:export object)))
    (is (empty? (:imports object)))
    (is (x86-memory-opcode? (:bytes object) [0x88]))
    (is (some #(= [0x0f 0x0b] %) (partition 2 1 (:bytes object))))))

(deftest bounded-byte-store-requires-four-operands
  (is (thrown-with-msg?
       clojure.lang.ExceptionInfo #"kernel memory operation arity mismatch"
       (compiler/check-source "(defn main [] (kernel-store-u8 1 2 3))"))))

(deftest kernel-target-exports-pci-planners
  (doseq [[entry params expected]
          [['aiueos-virtio-cap-valid '[pointer cap-length bar offset length]
            "kotoba_aiueos_virtio_cap_valid"]
           ['aiueos-pci-extent-valid '[value size] "kotoba_aiueos_pci_extent_valid"]
           ['aiueos-pci-region-valid '[offset bytes bar-length]
            "kotoba_aiueos_pci_region_valid"]
           ['aiueos-syscall-range-valid '[pointer length lower upper]
            "kotoba_aiueos_syscall_range_valid"]
           ['aiueos-copy-in '[source source-length destination destination-length count]
            "kotoba_aiueos_copy_in"]
           ['aiueos-capability-plan '[slot generation type state-rights request]
            "kotoba_aiueos_capability_plan"]
           ['aiueos-service-lifecycle '[generation restarts event budget]
            "kotoba_aiueos_service_lifecycle"]
           ['aiueos-service-registry-build '[base length sequence state0 state1]
            "kotoba_aiueos_service_registry_build"]
           ['aiueos-service-registry-state '[base length service]
            "kotoba_aiueos_service_registry_state"]
           ['aiueos-user-object-journal-build '[base length sequence domain value]
            "kotoba_aiueos_user_object_journal_build"]
           ['aiueos-user-object-journal-valid '[base length domain]
            "kotoba_aiueos_user_object_journal_valid"]
           ['aiueos-user-object-journal-value '[base length]
            "kotoba_aiueos_user_object_journal_value"]]]
    (let [source (str "(defn " entry " " params " 1) (defn main [] 0)")
          {:keys [object]} (compiler/compile-source source :x86_64-aiueos-kernel-v1)]
      (is (= expected (:export object)))
      (is (empty? (:imports object))))))

(deftest kernel-target-copy-in-retains-bounded-load-store-and-fuel
  (let [source "(defn aiueos-copy-in [source source-length destination destination-length count] (kernel-store-u8 destination destination-length 0 (kernel-load-u8 source source-length 0))) (defn main [] 0)"
        {:keys [object]} (compiler/compile-source source :x86_64-aiueos-kernel-v1)
        bytes (:bytes object)]
    (is (= "kotoba_aiueos_copy_in" (:export object)))
    (is (x86-memory-opcode? bytes [0x0f 0xb6]))
    (is (x86-memory-opcode? bytes [0x88]))
    (is (some #(= [0x49 0xc7 0x41 0x08 0x00 0x04 0x00 0x00] %)
              (partition 8 1 bytes)))))


(deftest firmware-target-emits-a-real-import-free-pe32+-efi-image
  (let [{:keys [binary]} (compiler/compile-source "(defn main [image system-table] 0)"
                                                  :x86_64-aiueos-uefi-v1)
        bytes (:bytes binary)
        pe-offset (read-le bytes 0x3c 4)
        coff (+ pe-offset 4)
        optional (+ coff 20)
        directories (+ optional 112)
        section-table (+ optional (read-le bytes (+ coff 16) 2))]
    (is (= [0x4d 0x5a] (subvec bytes 0 2)) "DOS MZ identity")
    (is (= [0x50 0x45 0 0] (subvec bytes pe-offset (+ pe-offset 4))))
    (is (= 0x8664 (read-le bytes coff 2)) "IMAGE_FILE_MACHINE_AMD64")
    (is (= 3 (read-le bytes (+ coff 2) 2)))
    (is (= 0x20b (read-le bytes optional 2)) "PE32+")
    (is (= 10 (read-le bytes (+ optional 68) 2)) "EFI application subsystem")
    (is (= 0x1000 (read-le bytes (+ optional 16) 4)) "entry RVA")
    (is (= 0 (read-le bytes (+ directories 8) 4)) "import directory RVA")
    (is (= 0 (read-le bytes (+ directories 12) 4)) "import directory size")
    (is (= 0x3000 (read-le bytes (+ directories (* 5 8)) 4)) "relocation RVA")
    (is (= 12 (read-le bytes (+ directories (* 5 8) 4) 4)))
    (is (= [:text :data :reloc] (:sections binary)))
    (is (empty? (:imports binary)))
    (is (= {:format :pe-base-relocation/v1 :fixups 0 :position-independent true}
           (:relocations binary)))
    (is (= :microsoft-x64-two-arity-efi-status-v2 (:entry-contract binary)))
    ;; sub rsp,40 reserves Microsoft shadow space and aligns before the call.
    (is (= [0x48 0x83 0xec 0x28] (subvec bytes 0x200 0x204)))
    (is (= [0x48 0x89 0xcf 0x48 0x89 0xd6] (subvec bytes 0x204 0x20a))
        "RCX/RDX firmware handles move into Kotoba's RDI/RSI homes")
    ;; Three complete 40-byte section headers fit before SizeOfHeaders.
    (is (<= (+ section-table (* 3 40)) 0x200))))

(deftest efi-packaging-rejects-an-entry-that-cannot-satisfy-its-boundary-contract
  (is (thrown-with-msg? clojure.lang.ExceptionInfo #"(two-arity|take 2 arguments)"
                        (compiler/compile-source "(defn main [image] image)"
                                                 :x86_64-aiueos-uefi-v1))))

;; amu#626 / aiueos ADR-0054. `kotoba.native.elf64`'s `kernel-object-entries`
;; is the whole rule for a kernel object's public symbol, and it used to hand
;; the probe's contract to anything it did not list. That is not a fallback but
;; a collision: three of aiueos's `value-*` objects each compiled to a
;; valid-looking ET_REL exporting `kotoba_aiueos_probe`, colliding with
;; `kernel-probe` and with each other, and the compile said nothing. The rule
;; was undiscoverable for exactly that reason -- every minimal source anyone
;; wrote to find it got the generic symbol, and the real file did not.
;;
;; Both directions live in one deftest deliberately. The refusal alone would
;; pass just as well if packaging had stopped admitting anything at all.
(deftest kernel-object-with-an-unlisted-aiueos-export-is-refused-not-given-the-probe-symbol
  (testing "an unlisted aiueos-* export is refused, and names itself"
    (let [thrown (try (compiler/compile-source
                       (str "(ns aiueos.not-a-real-object"
                            "  (:export [aiueos-not-in-the-table main]))"
                            "(defn aiueos-not-in-the-table [n :i64] :i64 n)"
                            "(defn main [] :i64 0)")
                       :x86_64-aiueos-kernel-v1)
                      (catch clojure.lang.ExceptionInfo e e))]
      (is (instance? clojure.lang.ExceptionInfo thrown)
          "packaging must refuse rather than emit a colliding symbol")
      (is (re-find #"no admitted symbol" (ex-message thrown)))
      (is (= '[aiueos-not-in-the-table] (:unlisted-exports (ex-data thrown)))
          "the refusal names the export that has no entry")))
  (testing "a source claiming no aiueos name still packages as the probe"
    (is (= "kotoba_aiueos_probe"
           (:export (:object (compiler/compile-source "(defn main [] 42)"
                                                      :x86_64-aiueos-kernel-v1)))))
    (is (= "kotoba_aiueos_probe"
           (:export (:object (compiler/compile-source
                              "(defn fact [n] (if (= n 0) 1 (* n (fact (- n 1))))) (defn main [] (fact 5))"
                              :x86_64-aiueos-kernel-v1))))
        "helper exports are not an aiueos identity claim"))
  (testing "a listed entry still gets its own symbol"
    (is (= "kotoba_aiueos_fnv1a"
           (:export (:object (compiler/compile-source
                              (str "(ns aiueos.fnv1a (:export [aiueos-fnv1a main]))"
                                   "(defn aiueos-fnv1a [seed :i64 byte :i64] :i64"
                                   "  (bit-xor seed byte))"
                                   "(defn main [] :i64 0)")
                              :x86_64-aiueos-kernel-v1)))))))

;; aiueos ADR-0054's export class, from the side that can check it. Two of the
;; three objects carry `:native {:export "..."}` in their own contract, so
;; `kernel-object-entries` transcribes those symbols rather than choosing them
;; -- and this asserts the transcription, so dropping an entry is a red test
;; rather than a silent return to `kotoba_aiueos_probe`.
;;
;; The sources here mirror the real ones' ns/export/arity. The end-to-end check
;; against `os/aiueos/kotoba/value-runtime-syscall-plan.kotoba` itself lives in
;; aiueos, which is where that file is.
(deftest contract-declared-value-runtime-entries-carry-their-own-symbol
  (is (= "kotoba_aiueos_value_runtime_syscall_plan"
         (:export (:object (compiler/compile-source
                            (str "(ns aiueos.value-runtime-syscall-plan"
                                 "  (:export [aiueos-value-runtime-syscall-plan main]))"
                                 "(defn aiueos-value-runtime-syscall-plan"
                                 "  [number :i64 domain :i64 pointer :i64"
                                 "   user-rip :i64 user-rsp :i64] :i64"
                                 "  (if (= number 5) domain 0))"
                                 "(defn main [] :i64 0)")
                            :x86_64-aiueos-kernel-v1)))))
  (is (= "kotoba_aiueos_value_runtime_cas_verify"
         (:export (:object (compiler/compile-source
                            (str "(ns aiueos.value-runtime-cas-verify"
                                 "  (:export [aiueos-value-runtime-cas-verify main]))"
                                 "(defn aiueos-value-runtime-cas-verify"
                                 "  [block :i64 block-length :i64 expected :i64"
                                 "   output :i64 workspace :i64] :i64"
                                 "  (if (> block-length 0) 1 0))"
                                 "(defn main [] :i64 0)")
                            :x86_64-aiueos-kernel-v1))))))
