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
  ;; shadow space plus alignment, initialize Kotoba's hidden r9 context, call a
  ;; zero-arity internal entry, and return its rax as EFI_STATUS. This is an ABI
  ;; adapter, not a claim that the internal Kotoba lowering is Microsoft x64.
  (let [after-lea (+ text-rva 11)
        after-call (+ text-rva 16)]
    (vec (concat [0x48 0x83 0xec 0x28
                  0x4c 0x8d 0x0d]
                 (signed-le (- context-rva after-lea) 4)
                 [0xe8] (signed-le (- source-rva after-call) 4)
                 [0x48 0x83 0xc4 0x28 0xc3]))))

(defn package-efi
  "Package a sealed aiueos firmware artifact as an import-free PE32+ EFI image.
  The Microsoft x64 boundary supports a zero-arity Kotoba entry returning an
  EFI_STATUS-sized integer; internal functions retain the compiler context ABI."
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
    (when-not (zero? (:arity export))
      (throw (ex-info "UEFI boundary requires a zero-arity Kotoba entry"
                      {:entry source-entry :arity (:arity export)})))
    (let [shim-size 21
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
       :entry-contract :microsoft-x64-zero-arity-efi-status-v1
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
                   (if-let [label (and (map? token) (:label token))]
                     (recur (next remaining) position (assoc out label position))
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

(defn package-embedded-kernel
  "Generate a position-independent PE32+ UEFI transition loader around a
  compiler-produced aiueos kernel ELF. No C object, CRT, import, or linker is
  involved. The current hard-flip contract admits exactly two bounded PT_LOAD
  segments and transfers control after ExitBootServices."
  [kernel]
  (let [kernel (vec kernel)]
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
            variables-size 72
            memory-map-offset (align variables-size 16)
            memory-map-capacity 16384
            embedded-offset (align (+ memory-map-offset memory-map-capacity) 16)
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
                    segment-tokens
                    ;; The bounded memory map is part of the loader image's RW
                    ;; section, immediately after boot-info. This makes the
                    ;; handoff one compiler-owned region: the kernel derives
                    ;; boot+64 instead of trusting a pointer read from firmware
                    ;; data as a new memory authority. GetMemoryMap fails closed
                    ;; when 16 KiB is insufficient.
                    [0x48 0x8d 0x05] [(rip :memory-map)]
                    [0x48 0x89 0x05] [(rip :map-pointer)]
                    [(label :get-map)]
                    [0x48 0xc7 0x05] [(rip :map-size)] [0 0x40 0 0]
                    [0x48 0x8d 0x0d] [(rip :map-size)]
                    [0x48 0x8b 0x15] [(rip :map-pointer)]
                    [0x4c 0x8d 0x05] [(rip :map-key)]
                    [0x4c 0x8d 0x0d] [(rip :descriptor-size)]
                    [0x48 0x8d 0x05] [(rip :descriptor-version)]
                    [0x48 0x89 0x44 0x24 0x20 0x41 0xff 0x56 0x38
                     0x48 0x85 0xc0 0x0f 0x85] [(rip :fail)]
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
                              (le 1 8)
                              (repeat (- variables-size 32) 0)
                              (repeat (- memory-map-offset variables-size) 0)
                              (repeat memory-map-capacity 0)
                              (repeat (- embedded-offset
                                         (+ memory-map-offset memory-map-capacity)) 0)
                              kernel))
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
                           :memory-map (+ data-address memory-map-offset)}
                          (into {} (map-indexed
                                    (fn [index segment]
                                      [(keyword (str "segment" index))
                                       (+ data-address embedded-offset (:offset segment))])
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
        {:format :pe32+-embedded-kernel/v2 :target firmware-target
         :entry :efi_main :entry-rva text-rva :sections [:text :data :reloc]
         :boot-info-layout {:bytes (+ 64 memory-map-capacity)
                            :memory-map-offset 64
                            :memory-map-capacity memory-map-capacity}
         :imports [] :embedded-kernel-sha256 (artifact/sha256 kernel)
         :bytes bytes})))))
