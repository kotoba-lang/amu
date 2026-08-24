(ns kotoba.compiler.packaging.elf-fixture
  "One crafted ELF, shared by the JVM test and the nbb case, so that the thing
  both runtimes are asked about is literally the same bytes.

  It is a well-formed x86-64 ET_EXEC with two PT_LOAD segments, valid in every
  way the `package-embedded-kernel` contract checks EXCEPT that the first
  segment's `p_paddr` is 0x0001000000100000 -- about 256 terabytes. The
  contract requires `paddr <= 0x40000000 - memsz`, so this must be rejected.

  Why that exact value. `read-le` used to accumulate with
  `(bit-shift-left byte (* 8 index))`, and cljs shift counts are taken mod 32,
  so the byte at index 6 is shifted by 16 instead of 48: it lands in the LOW
  bits. The value was chosen so the misread is not merely wrong but still
  passes every check the contract makes -- 0x110000 is page-aligned, is at
  least 0x100000, and is well under 0x40000000. `e_entry` is 0x110000 for the
  same reason, so the misread segment still contains the entry point.

  Measured 2026-08-25, before the fix: the JVM read 281474977759232 and
  rejected the kernel; nbb read 1114112 and ACCEPTED it, emitting a boot image
  for a kernel the contract refuses. An admission check that fails open on the
  second runtime.

  A first attempt at this fixture put the high byte at index 4, where the
  misread is 1048577. nbb rejected that one too -- but because 1048577 is not
  page-aligned, not because of the bound. A negative test that passes for a
  reason other than the one it names is the thing this fixture exists to avoid,
  so the byte was moved.

  Every legal kernel this packager sees has all four high bytes zero (the
  contract caps paddr and memsz at 0x40000000 and 0x100000), which is why the
  defect was inert for real input and invisible to the JVM suite alike.")

(def ^:private byte-scale
  ;; 2^(8*i). Written as literals for the same reason the packager itself
  ;; writes its bounds as literals: `(bit-shift-left 1 32)` is 1 on cljs.
  ;; Each is a power of two, exact as a JVM long and as a JS double alike.
  [1 256 65536 16777216 4294967296 1099511627776 281474976710656 72057594037927936])

(defn le
  "VALUE as WIDTH little-endian bytes. Uses quot/rem, never a shift."
  [value width]
  (mapv (fn [i] (mod (quot value (nth byte-scale i)) 256)) (range width)))

;; 0x0001000000100000, written out rather than computed, so that constructing
;; the fixture cannot itself depend on the arithmetic under test.
(def paddr-above-the-bound-bytes [0x00 0x00 0x10 0x00 0x00 0x00 0x01 0x00])
(def paddr-above-the-bound 281474977759232)

;; What the shift-wrapped reader answered instead. Named so a test can say
;; which of the two it got rather than only that the numbers differ.
(def paddr-as-misread-by-a-wrapped-shift 1114112)

(def ^:private page 4096)
(def ^:private phoff 64)
(def ^:private phentsize 56)
(def ^:private body-offset (+ phoff (* 2 phentsize)))

(defn- program-header [{:keys [flags offset paddr-bytes size]}]
  (vec (concat (le 1 4)               ; p_type = PT_LOAD
               (le flags 4)
               (le offset 8)          ; p_offset
               paddr-bytes            ; p_vaddr (= p_paddr, as usual)
               paddr-bytes            ; p_paddr
               (le size 8)            ; p_filesz
               (le size 8)            ; p_memsz
               (le page 8))))         ; p_align

(defn kernel-with-out-of-range-paddr
  "The bytes. Rejected on both runtimes once `read-le` reads all eight bytes."
  []
  (let [header (vec (concat [0x7f 0x45 0x4c 0x46 2 1 1 0]
                            (repeat 8 0)
                            (le 2 2)            ; e_type   = ET_EXEC
                            (le 0x3e 2)         ; e_machine= EM_X86_64
                            (le 1 4)            ; e_version
                            (le 0x110000 8)     ; e_entry -- inside the MISREAD segment 0
                            (le phoff 8)        ; e_phoff
                            (le 0 8)            ; e_shoff
                            (le 0 4)            ; e_flags
                            (le 64 2)           ; e_ehsize
                            (le phentsize 2)
                            (le 2 2)            ; e_phnum
                            (le 0 2) (le 0 2) (le 0 2)))
        ph0 (program-header {:flags 5 :offset body-offset
                             :paddr-bytes paddr-above-the-bound-bytes :size page})
        ph1 (program-header {:flags 6 :offset (+ body-offset page)
                             :paddr-bytes (le 0x200000 8) :size page})]
    (vec (concat header ph0 ph1 (repeat (* 2 page) 0)))))
