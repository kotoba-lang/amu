(ns kotoba.compiler.packaging.pe32plus
  (:require [kotoba.artifact.core :as artifact]
            [kotoba.object.pe32plus :as pe]))

(def ^:private firmware-target :x86_64-aiueos-uefi-v1)
(def ^:private file-alignment 0x200)
(def ^:private section-alignment 0x1000)
(def ^:private image-base 0x400000)
(def ^:private text-rva 0x1000)
(def ^:private data-rva 0x2000)
(def ^:private reloc-rva 0x3000)
(def ^:private text-offset 0x200)
(def ^:private context-size 80)

(def le pe/little-endian)
(def align pe/align-up)

(defn- utf16z [value]
  (vec (mapcat #(le (int %) 2) (concat value [\u0000]))))

;; 2^(8*width) for the widths this packager emits. Written as literals rather
;; than `(bit-shift-left 1 (* 8 width))`, which is NOT portable: JavaScript
;; shift counts are taken mod 32, so on ClojureScript `(bit-shift-left 1 32)`
;; is 1, not 2^32. Measured 2026-08-20 under nbb -- `limit` came out 1, so
;; `maximum` was 0 and every nonzero field was rejected as "out of range",
;; including a relocation displacement of 4085. Both bounds below are powers of
;; two, exact as a JVM long and as a JS double alike.
(def ^:private signed-limit {1 256 2 65536 4 4294967296 8 18446744073709551616})

(defn- signed-le [n width]
  (let [limit (or (signed-limit width)
                  (throw (ex-info "unsupported signed little-endian width"
                                  {:width width})))
        minimum (- (quot limit 2))
        maximum (dec (quot limit 2))]
    (when-not (<= minimum n maximum)
      (throw (ex-info "signed little-endian field is out of range"
                      {:value n :width width})))
    (le (if (neg? n) (+ limit n) n) width)))

(defn- entry-shim [source-rva context-rva]
  ;; UEFI invokes this boundary with the Microsoft x64 ABI. Reserve its 32-byte
  ;; shadow space plus alignment, move ImageHandle/SystemTable from RCX/RDX to
  ;; Kotoba's first two integer homes RDI/RSI, initialize the hidden r9 context,
  ;; call the internal entry, and return its rax as EFI_STATUS. This is an ABI
  ;; adapter, not a claim that internal Kotoba lowering is Microsoft x64.
  (let [after-lea (+ text-rva 17)
        after-call (+ text-rva 22)]
    (vec (concat [0x48 0x83 0xec 0x28
                  0x48 0x89 0xcf
                  0x48 0x89 0xd6
                  0x4c 0x8d 0x0d]
                 (signed-le (- context-rva after-lea) 4)
                 [0xe8] (signed-le (- source-rva after-call) 4)
                 [0x48 0x83 0xc4 0x28 0xc3]))))

(defn package-efi
  "Package a sealed aiueos firmware artifact as an import-free PE32+ EFI image.
  The Microsoft x64 boundary passes ImageHandle and SystemTable to a two-arity
  Kotoba entry returning an EFI_STATUS-sized integer; internal functions retain
  the compiler context ABI."
  [artifact]
  (when-not (artifact/valid-seal? artifact)
    (throw (ex-info "PE32+ EFI packaging requires a sealed artifact" {})))
  (when-not (= firmware-target (:target artifact))
    (throw (ex-info "PE32+ EFI packaging requires the aiueos UEFI target"
                    {:target (:target artifact)})))
  (when-not (and (= :none (get-in artifact [:target-profile :runtime]))
                 (false? (get-in artifact [:target-profile :ambient-syscalls])))
    (throw (ex-info "PE32+ EFI packaging requires a freestanding profile"
                    {:target-profile (:target-profile artifact)})))
  (let [source-entry (get-in artifact [:program :entry])
        export (get-in artifact [:exports source-entry])]
    (when-not export
      (throw (ex-info "Kotoba firmware entry is not exported" {:entry source-entry})))
    (when-not (= 2 (:arity export))
      (throw (ex-info "UEFI boundary requires a two-arity Kotoba entry"
                      {:entry source-entry :arity (:arity export)})))
    (let [shim-size 27
          source-rva (+ text-rva shim-size (:offset export))
          shim (entry-shim source-rva data-rva)
          text (into shim (:code artifact))
          context (into (vec (repeat 8 0))
                        (concat (le 512 8) (repeat (- context-size 16) 0)))
          text-raw-size (align (count text) file-alignment)
          data-offset (+ text-offset text-raw-size)
          data-raw-size (align context-size file-alignment)
          reloc-offset (+ data-offset data-raw-size)
          ;; A legal relocation directory containing two IMAGE_REL_BASED_ABSOLUTE
          ;; padding entries. All image references are relative, so no fixups exist.
          reloc (vec (concat (le 0 4) (le 12 4) (le 0 2) (le 0 2)))
          reloc-raw-size (align (count reloc) file-alignment)
          bytes (pe/encode-image
                 {:machine :x86-64 :entry-rva text-rva :text-rva text-rva
                  :image-base image-base :section-alignment section-alignment
                  :file-alignment file-alignment :headers-size text-offset
                  :image-size 0x4000 :subsystem :efi-application
                  :data-directories {5 {:rva reloc-rva :size (count reloc)}}
                  :sections [{:name ".text" :virtual-size (count text)
                              :rva text-rva :raw-size text-raw-size
                              :raw-offset text-offset :characteristics 0x60000020
                              :bytes text}
                             {:name ".data" :virtual-size context-size
                              :rva data-rva :raw-size data-raw-size
                              :raw-offset data-offset :characteristics 0xc0000040
                              :bytes context}
                             {:name ".reloc" :virtual-size (count reloc)
                              :rva reloc-rva :raw-size reloc-raw-size
                              :raw-offset reloc-offset :characteristics 0x42000040
                              :bytes reloc}]})]
      {:format :pe32+/v1
       :target firmware-target
       :entry :efi_main
       :source-entry source-entry
       :entry-rva text-rva
       :entry-contract :microsoft-x64-two-arity-efi-status-v2
       :sections [:text :data :reloc]
       :imports []
       :relocations {:format :pe-base-relocation/v1 :fixups 0 :position-independent true}
       :bytes bytes})))

;; 2^(8*i) for i in 0..7, for the same reason the bounds above are literals:
;; `(bit-shift-left 1 32)` is 1 on ClojureScript. Each is a power of two, exact
;; as a JVM long and as a JS double alike.
(def ^:private byte-scale
  [1 256 65536 16777216 4294967296 1099511627776 281474976710656 72057594037927936])

(defn- read-le
  "WIDTH little-endian bytes at OFFSET, as one number.

  This used to accumulate with `(bit-shift-left byte (* 8 index))`, which is
  the very hazard the comment above this file's bounds was written about, at a
  width the comment's author was not looking at: the six ELF fields read here
  with width 8 need shifts of 32, 40, 48 and 56, and cljs takes shift counts
  mod 32. Bytes 4 through 7 of every 64-bit field were folded into the LOW
  bits.

  It was inert for legal input -- the PT_LOAD contract caps paddr at
  0x40000000 and memsz at 0x100000, so those four bytes are zero in every
  kernel this packager is supposed to see. It was NOT inert for input the
  contract exists to refuse. Measured 2026-08-25 with
  `kotoba.compiler.packaging.elf-fixture`, whose first segment sits at
  0x0001000000100000: the JVM read 281474977759232 and rejected the kernel;
  nbb read 1114112, passed every bound check, and emitted a boot image.
  The admission check failed open on the second runtime."
  [bytes offset width]
  (reduce (fn [value index]
            (+ value (* (nth bytes (+ offset index)) (nth byte-scale index))))
          0 (range width)))

(defn- code-size [tokens]
  (reduce (fn [size token]
            (+ size (cond
                      (and (map? token) (:label token)) 0
                      (and (map? token) (:rel32 token)) 4
                      :else 1)))
          0 tokens))

(defn- finalize-loader [tokens external-labels]
  (let [labels (loop [remaining tokens position text-rva out external-labels]
                 (if-let [token (first remaining)]
                   (cond
                     (and (map? token) (:label token))
                     (recur (next remaining) position
                            (assoc out (:label token) position))

                     (and (map? token) (:rel32 token))
                     (recur (next remaining) (+ position 4) out)

                     :else
                     (recur (next remaining) (inc position) out))
                   out))]
    (loop [remaining tokens position text-rva out []]
      (if-let [token (first remaining)]
        (cond
          (and (map? token) (:label token))
          (recur (next remaining) position out)

          (and (map? token) (:rel32 token))
          (let [target (get labels (:rel32 token))]
            (when-not target (throw (ex-info "unknown UEFI loader label" {:label (:rel32 token)})))
            (recur (next remaining) (+ position 4)
                   (into out (signed-le (- target (+ position 4)) 4))))

          :else (recur (next remaining) (inc position) (conj out token)))
        (vec out)))))

(defn- rip [label] {:rel32 label})
(defn- label [name] {:label name})

(defn- allocate-segment [address-label pages source-label size]
  (concat
   [0xb9 2 0 0 0 0xba 2 0 0 0 0x41 0xb8] (le pages 4)
   [0x4c 0x8d 0x0d] [(rip address-label)]
   [0x41 0xff 0x56 0x28 0x48 0x85 0xc0 0x0f 0x85] [(rip :fail)]
   [0x48 0x8b 0x0d] [(rip address-label)]
   [0x48 0x8d 0x15] [(rip source-label)]
   [0x41 0xb8] (le size 4)
   [0x41 0xff 0x96 0x60 0x01 0x00 0x00]))

;; The pure AIUEOS kernel needs page-table, exception, allocator, and RTL8125
;; DMA storage after ExitBootServices. Reserve it while UEFI still owns the
;; memory map instead of asking the kernel to infer ownership from whatever
;; EfiConventionalMemory happens to remain on a particular machine.
(def ^:private kernel-scratch-pages 14)

(defn- store-status-nibble [source shift digit-label store-label target-label]
  (concat
   [0x44 0x89 0xf8]
   (when (pos? shift) [0xc1 0xe8 shift])
   [0x83 0xe0 0x0f 0x83 0xf8 0x0a 0x0f 0x8c] [(rip digit-label)]
   [0x83 0xc0 0x37 0xe9] [(rip store-label)]
   [(label digit-label)] [0x83 0xc0 0x30]
   [(label store-label)] [0x66 0x89 0x05] [(rip target-label)]
   ;; Retain the explicit source register in this helper's contract. Both
   ;; callers currently convert r15d, which holds the kernel return status.
   (when (not (= source :r15d)) [0xcc])))

(defn- uefi-output-string-tokens [message-label return-label]
  (concat
   ;; EFI_SYSTEM_TABLE.ConOut is at +0x40 and SIMPLE_TEXT_OUTPUT.OutputString
   ;; is at +0x08. Keep each checkpoint optional when firmware exposes no
   ;; console, so the headless boot path remains valid.
   [0x49 0x8b 0x4d 0x40 0x48 0x85 0xc9 0x0f 0x84] [(rip return-label)]
   [0x48 0x8d 0x15] [(rip message-label)]
   [0x48 0x8b 0x41 0x08 0xff 0xd0]
   [(label return-label)]))

(defn- k16-preflight-tokens [entry]
  (concat
   ;; Read 02:00.0 through PCI mechanism #1. Only the explicit K16 diagnostic
   ;; profile calls the kernel while Boot Services and ConOut are still live.
   [0x66 0xba 0xf8 0x0c 0xb8 0x00 0x00 0x02 0x80 0xef
    0x66 0xba 0xfc 0x0c 0xed 0x3d 0xec 0x10 0x25 0x81
    0x0f 0x85] [(rip :exit-boot)]
   (uefi-output-string-tokens :rtl-message :rtl-message-return)
   [0x48 0x8d 0x3d] [(rip :boot-info)]
   [0x48 0xb8] (le entry 8) [0xff 0xd0 0x49 0x89 0xc7]
   (store-status-nibble :r15d 4 :status-high-digit :status-high-store
                        :status-high)
   (store-status-nibble :r15d 0 :status-low-digit :status-low-store
                        :status-low)
   [0x49 0x8b 0x4d 0x40 0x48 0x85 0xc9 0x0f 0x84]
   [(rip :preflight-return)]
   [0x48 0x8d 0x15] [(rip :status-message)]
   [0x48 0x8b 0x41 0x08 0xff 0xd0]
   [(label :preflight-return)]
   ;; Return before ExitBootServices so firmware can recover/retry PXE after
   ;; the one-shot diagnostic. Restore the Microsoft x64 entry frame exactly.
   [0xb8 0x01 0x00 0x00 0x00 0x48 0x83 0xc4 0x28
    0x41 0x5f 0x41 0x5e 0x41 0x5d 0x41 0x5c 0xc3]))

(defn package-embedded-kernel
  "Generate a position-independent PE32+ UEFI transition loader around a
  compiler-produced aiueos kernel ELF. No C object, CRT, import, or linker is
  involved. The current hard-flip contract admits exactly two bounded PT_LOAD
  segments and transfers control after ExitBootServices.

  ⚠ NOT PORTABLE, measured 2026-08-31. This function emits different bytes
  under ClojureScript than under the JVM. Given one identical kernel it
  produced 129,024 bytes on both, differing in exactly two, inside an
  eight-byte run the JVM writes as `AIUEBOOT` and cljs as a NUL followed by
  `HUEBOOT`; read as one little-endian word the two differ by 321. Both routes reported
  the same kernel sha256, so both had read the same input.

  `package-efi` in this same namespace IS byte-identical across the two, so
  this is one function, not the file. That is also why `bin/amu`'s JDK-free
  route serves `--target x86_64-aiueos-uefi-v1` and refuses
  `package-aiueos-boot`: the boot command was implemented on that route,
  measured, and reverted rather than shipped.

  No test guards this, and one cannot be written here. Clojure and nbb each
  load their own runtime; a comparison has to build the same input under BOTH
  and diff the bytes, which is what aiueos's
  `os/aiueos/scripts/verify-jvm-free-object-parity.cljs` does for kernel
  objects. Whoever narrows this down should do the same for the boot image.

  This file has ZERO reader conditionals. That was taken as evidence it was
  portable; it is evidence that nobody wrote one. Suspect the arithmetic --
  cljs bitwise operators truncate to int32, and the values here (entry points,
  paddrs, segment sizes) are 64-bit. See aiueos ADR-0130."
  ([kernel] (package-embedded-kernel kernel [] {}))
  ([kernel payload] (package-embedded-kernel kernel payload {}))
  ([kernel payload options]
  (let [kernel (vec kernel)
        payload (vec payload)
        k16-preflight? (true? (:k16-preflight? options))]
    (when (> (count payload) 16384)
      (throw (ex-info "embedded RT payload exceeds 16 KiB" {:bytes (count payload)})))
    (when-not (and (= [0x7f 0x45 0x4c 0x46] (subvec kernel 0 4))
                   (= 2 (read-le kernel 16 2)) (= 0x3e (read-le kernel 18 2)))
      (throw (ex-info "embedded kernel must be x86-64 ET_EXEC" {})))
    (let [entry (read-le kernel 24 8)
          phoff (read-le kernel 32 8)
          phentsize (read-le kernel 54 2)
          phnum (read-le kernel 56 2)
          segments (mapv (fn [index]
                           (let [offset (+ phoff (* index phentsize))]
                             {:type (read-le kernel offset 4)
                              :flags (read-le kernel (+ offset 4) 4)
                              :offset (read-le kernel (+ offset 8) 8)
                              :paddr (read-le kernel (+ offset 24) 8)
                              :filesz (read-le kernel (+ offset 32) 8)
                              :memsz (read-le kernel (+ offset 40) 8)}))
                         (range phnum))]
      (let [first-segment (first segments) second-segment (second segments)
            entry-segment (some #(and (= 5 (:flags %))
                                      (<= (:paddr %) entry)
                                      (< entry (+ (:paddr %) (:memsz %)))) segments)
            non-overlap (or (<= (+ (:paddr first-segment) (:memsz first-segment))
                                (:paddr second-segment))
                            (<= (+ (:paddr second-segment) (:memsz second-segment))
                                (:paddr first-segment)))]
      (when-not (and (= 2 phnum) (= 56 phentsize)
                     (every? #(and (= 1 (:type %)) (pos? (:filesz %))
                                   (= (:filesz %) (:memsz %))
                                   (<= 0x100000 (:paddr %))
                                   (<= (:memsz %) 0x100000)
                                   (<= (:paddr %) (- 0x40000000 (:memsz %)))
                                   (zero? (mod (:paddr %) 4096))
                                   (<= (+ (:offset %) (:filesz %)) (count kernel))) segments)
                     (= [5 6] (mapv :flags segments)) entry-segment non-overlap)
        (throw (ex-info "embedded kernel PT_LOAD contract rejected" {:segments segments})))
      (let [data-addresses [0 8]
            rx-limit (align (+ (:paddr first-segment) (:memsz first-segment)) 4096)
            rw-start (:paddr second-segment)
            rw-end (+ rw-start (:memsz second-segment))
            payload? (seq payload)
            ;; Two loader-private segment destinations precede boot-info.
            ;; Boot-info v4 is 96 bytes without a payload: the original
            ;; firmware-map and W^X fields followed by a loader-owned scratch
            ;; address/page count. An optional payload pointer/length follows.
            variables-size (if payload? 128 112)
            memory-map-offset (align variables-size 16)
            memory-map-capacity 16384
            embedded-offset (align (+ memory-map-offset memory-map-capacity) 16)
            payload-offset embedded-offset
            kernel-offset (align (+ payload-offset (count payload)) 16)
            status-prefix "AIUEOS K16 PREFLIGHT STATUS "
            enter-message (if k16-preflight?
                            (utf16z "AIUEOS K16 PREFLIGHT ENTER\r\n") [])
            rtl-message (if k16-preflight?
                          (utf16z "AIUEOS K16 PREFLIGHT RTL8125\r\n") [])
            status-message (if k16-preflight?
                             (utf16z (str status-prefix "00\r\n")) [])
            enter-message-offset (align (+ kernel-offset (count kernel)) 16)
            rtl-message-offset (align (+ enter-message-offset
                                         (count enter-message)) 16)
            status-message-offset (align (+ rtl-message-offset
                                            (count rtl-message)) 16)
            ;; Build once with provisional external RVAs; instruction length is
            ;; independent of displacement values.
            segment-tokens (mapcat (fn [index segment]
                                     (allocate-segment (keyword (str "address" index))
                                      (quot (+ (:memsz segment) 4095) 4096)
                                      (keyword (str "segment" index)) (:filesz segment)))
                                   (range) segments)
            tokens (vec (concat
                    [0x41 0x54 0x41 0x55 0x41 0x56 0x41 0x57
                     0x48 0x83 0xec 0x28 0x49 0x89 0xcc 0x49 0x89 0xd5
                     0x4c 0x8b 0x72 0x60]
                    (when k16-preflight?
                      (uefi-output-string-tokens :enter-message
                                                 :enter-message-return))
                    segment-tokens
                    ;; AllocateAnyPages/EfiLoaderData. The returned physical
                    ;; address is explicit boot authority, so no fixed low-RAM
                    ;; hole or conventional-memory scan is required on K16.
                    [0xb9 0 0 0 0 0xba 2 0 0 0 0x41 0xb8]
                    (le kernel-scratch-pages 4)
                    [0x4c 0x8d 0x0d] [(rip :scratch-address)]
                    [0x41 0xff 0x56 0x28 0x48 0x85 0xc0 0x0f 0x85]
                    [(rip :fail)]
                    (when payload?
                      (concat [0x48 0x8d 0x05] [(rip :payload)]
                              [0x48 0x89 0x05] [(rip :payload-pointer)]
                              [0xb8] (le (count payload) 4)
                              [0x48 0x89 0x05] [(rip :payload-length)]))
                    ;; The bounded memory map is part of the loader image's RW
                    ;; section, immediately after boot-info. This makes the
                    ;; handoff one compiler-owned region: the kernel derives
                    ;; boot+64 instead of trusting a pointer read from firmware
                    ;; data as a new memory authority. GetMemoryMap fails closed
                    ;; when 16 KiB is insufficient.
                    [0x48 0x8d 0x05] [(rip :memory-map)]
                    [0x48 0x89 0x05] [(rip :map-pointer)]
                    [(label :get-map)]
                    [0xb8 0x00 0x40 0x00 0x00]
                    [0x48 0x89 0x05] [(rip :map-size)]
                    [0x48 0x8d 0x0d] [(rip :map-size)]
                    [0x48 0x8b 0x15] [(rip :map-pointer)]
                    [0x4c 0x8d 0x05] [(rip :map-key)]
                    [0x4c 0x8d 0x0d] [(rip :descriptor-size)]
                    [0x48 0x8d 0x05] [(rip :descriptor-version)]
                    [0x48 0x89 0x44 0x24 0x20 0x41 0xff 0x56 0x38
                     0x48 0x85 0xc0 0x0f 0x85] [(rip :fail)]
                    (when k16-preflight? (k16-preflight-tokens entry))
                    [(label :exit-boot)]
                    [0x4c 0x89 0xe1 0x48 0x8b 0x15] [(rip :map-key)]
                    [0x41 0xff 0x96 0xe8 0x00 0x00 0x00 0x48 0x85 0xc0
                     0x0f 0x85] [(rip :get-map)]
                    [0x48 0x8d 0x3d] [(rip :boot-info)]
                    [0x48 0xb8] (le entry 8) [0xff 0xd0]
                    [(label :fail)]
                    [0x66 0xba 0xe9 0x00 0xb0 0x46 0xee
                     0x66 0xba 0xf4 0x00 0xb8 0x7f 0x00 0x00 0x00 0xef
                     0xfa 0xf4 0xeb 0xfc]))
            text-size (code-size tokens)
            data-address (align (+ text-rva text-size) section-alignment)
            data (vec (concat (mapcat #(le (:paddr %) 8) segments)
                              (le 0x544f4f4245554941 8)
                              (le 4 8)
                              ;; map pointer/size/key/descriptor fields are
                              ;; populated by the loader before handoff.
                              (repeat 40 0)
                              (le rx-limit 8)
                              (le rw-start 8)
                              (le rw-end 8)
                              (repeat 8 0)
                              (le kernel-scratch-pages 8)
                              (when payload? (repeat 16 0))
                              (repeat (- memory-map-offset variables-size) 0)
                              (repeat memory-map-capacity 0)
                              (repeat (- embedded-offset
                                         (+ memory-map-offset memory-map-capacity)) 0)
                              payload
                              (repeat (- kernel-offset
                                         (+ payload-offset (count payload))) 0)
                              kernel
                              (when k16-preflight?
                                (concat
                                 (repeat (- enter-message-offset
                                            (+ kernel-offset (count kernel))) 0)
                                 enter-message
                                 (repeat (- rtl-message-offset
                                            (+ enter-message-offset
                                               (count enter-message))) 0)
                                 rtl-message
                                 (repeat (- status-message-offset
                                            (+ rtl-message-offset
                                               (count rtl-message))) 0)
                                 status-message))))
            data-raw-size (align (count data) file-alignment)
            reloc-address (align (+ data-address (count data)) section-alignment)
            labels (merge {:address0 (+ data-address (nth data-addresses 0))
                           :address1 (+ data-address (nth data-addresses 1))
                           :boot-info (+ data-address 16)
                           :map-pointer (+ data-address 32)
                           :map-size (+ data-address 40)
                           :descriptor-size (+ data-address 48)
                           :descriptor-version (+ data-address 56)
                           :map-key (+ data-address 64)
                           :rx-limit (+ data-address 72)
                           :rw-start (+ data-address 80)
                           :rw-end (+ data-address 88)
                           :scratch-address (+ data-address 96)
                           :memory-map (+ data-address memory-map-offset)
                           :payload-pointer (+ data-address 112)
                           :payload-length (+ data-address 120)
                           :payload (+ data-address payload-offset)}
                          (when k16-preflight?
                            {:enter-message (+ data-address enter-message-offset)
                             :rtl-message (+ data-address rtl-message-offset)
                             :status-message (+ data-address status-message-offset)
                             :status-high (+ data-address status-message-offset
                                             (* 2 (count status-prefix)))
                             :status-low (+ data-address status-message-offset
                                            (* 2 (inc (count status-prefix))))})
                          (into {} (map-indexed
                                    (fn [index segment]
                                      [(keyword (str "segment" index))
                                       (+ data-address kernel-offset (:offset segment))])
                                    segments)))
            text (finalize-loader tokens labels)
            text-raw-size (align (count text) file-alignment)
            data-offset (+ text-offset text-raw-size)
            reloc-offset (+ data-offset data-raw-size)
            reloc (vec (concat (le 0 4) (le 12 4) (le 0 2) (le 0 2)))
            reloc-raw-size (align (count reloc) file-alignment)
            image-size (align (+ reloc-address (count reloc)) section-alignment)
            bytes (pe/encode-image
                   {:machine :x86-64 :entry-rva text-rva :text-rva text-rva
                    :image-base image-base :section-alignment section-alignment
                    :file-alignment file-alignment :headers-size text-offset
                    :image-size image-size :subsystem :efi-application
                    :data-directories {5 {:rva reloc-address :size (count reloc)}}
                    :sections [{:name ".text" :virtual-size (count text)
                                :rva text-rva :raw-size text-raw-size
                                :raw-offset text-offset :characteristics 0x60000020
                                :bytes text}
                               {:name ".data" :virtual-size (count data)
                                :rva data-address :raw-size data-raw-size
                                :raw-offset data-offset :characteristics 0xc0000040
                                :bytes data}
                               {:name ".reloc" :virtual-size (count reloc)
                                :rva reloc-address :raw-size reloc-raw-size
                                :raw-offset reloc-offset :characteristics 0x42000040
                                :bytes reloc}]})]
        {:format :pe32+-embedded-kernel/v3 :target firmware-target
         :entry :efi_main :entry-rva text-rva :sections [:text :data :reloc]
         :boot-info-layout (cond->
                            {:bytes (+ (- memory-map-offset 16)
                                       memory-map-capacity (count payload))
                             :memory-map-offset (- memory-map-offset 16)
                             :memory-map-capacity memory-map-capacity
                             :rx-limit-offset 56
                             :rw-start-offset 64
                             :rw-end-offset 72
                             :kernel-scratch-address-offset 80
                             :kernel-scratch-pages-offset 88
                             :kernel-scratch-pages kernel-scratch-pages}
                             payload?
                             (assoc :payload-offset (- payload-offset 16)
                                    :payload-bytes (count payload)))
         :imports [] :embedded-kernel-sha256 (artifact/sha256 kernel)
         :embedded-payload-sha256 (when payload? (artifact/sha256 payload))
         :k16-preflight? k16-preflight?
         :bytes bytes}))))))
