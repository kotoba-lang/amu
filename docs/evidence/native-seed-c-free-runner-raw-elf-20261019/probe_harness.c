/* JUN-29 vehicle (b) probe — measurement instrument only (NOT a run path).
 *
 * Executes the machine code extracted from the emitted raw-ELF runner probe
 * in-process on this host, against a synthetic kexe_context_v11-shaped table,
 * to verify the hand-emitted instruction semantics:
 *   - vtable dispatch at the exact displacements (cap_call/pair_* /string_*)
 *   - lea rsi,[rip+disp32] string literal reaches the called stub
 *   - fuel@8 inline read/decrement/write contract
 *   - js -> ud2 refusal trap (SIGILL)
 *   - tail jmp rax dispatch (tail_entry)
 * The Linux process-exit sequence in the image is byte-scanned only (this
 * harness returns via ret).
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <setjmp.h>
#include <signal.h>
#include <sys/mman.h>

static sigjmp_buf env;
static int ill_hits = 0;
static void on_ill(int sig) { (void)sig; ill_hits++; siglongjmp(env, 1); }

typedef uint64_t (*entry_fn)(void *ctx);

static int n_cap = 0, n_pnew = 0, n_pfirst = 0, n_psecond = 0, n_seq = 0, n_scat = 0;

static uint64_t cap_stub(void *ctx, const char *str) {
    (void)ctx; n_cap++;
    return (str && strcmp(str, "runner-probe") == 0) ? 30 : 999;
}
static uint64_t pair_new_stub(void *ctx, const char *str)     { (void)ctx; (void)str; n_pnew++;    return 56; }
static uint64_t pair_first_stub(void *ctx, const char *str)   { (void)ctx; (void)str; n_pfirst++;  return 64; }
static uint64_t pair_second_stub(void *ctx, const char *str)  { (void)ctx; (void)str; n_psecond++; return 72; }
static uint64_t string_equal_stub(void *ctx, const char *str) { (void)ctx; (void)str; n_seq++;     return 112; }
static uint64_t string_concat_stub(void *ctx, const char *str){ (void)ctx; (void)str; n_scat++;    return 120; }

#define SLOT_CAP_CALL      (0x30 / 8)
#define SLOT_PAIR_NEW      (0x38 / 8)
#define SLOT_PAIR_FIRST    (0x40 / 8)
#define SLOT_PAIR_SECOND   (0x48 / 8)
#define SLOT_STRING_EQUAL  (0x70 / 8)
#define SLOT_STRING_CONCAT (0x78 / 8)
#define FUEL_IDX           (0x08 / 8)

static int failures = 0;
static void expect(const char *name, int ok, const char *detail) {
    printf("%-38s %s  %s\n", name, ok ? "PASS" : "FAIL", detail);
    if (!ok) failures++;
}

int main(int argc, char **argv) {
    setvbuf(stdout, NULL, _IONBF, 0);
    if (argc < 2) { fprintf(stderr, "usage: probe_harness <emitted-elf>\n"); return 2; }
    FILE *f = fopen(argv[1], "rb");
    if (!f) { perror("open"); return 2; }
    fseek(f, 0, SEEK_END); long n = ftell(f); fseek(f, 0, SEEK_SET);
    uint8_t *raw = malloc((size_t)n);
    if (fread(raw, 1, (size_t)n, f) != (size_t)n) { fprintf(stderr, "short read\n"); return 2; }
    fclose(f);

    if (memcmp(raw, "\x7f""ELF", 4) != 0 || raw[4] != 2) { fprintf(stderr, "not ELF64\n"); return 2; }
    uint64_t e_entry, e_phoff; uint16_t e_phentsize, e_phnum;
    memcpy(&e_entry, raw + 24, 8); memcpy(&e_phoff, raw + 32, 8);
    memcpy(&e_phentsize, raw + 54, 2); memcpy(&e_phnum, raw + 56, 2);
    (void)e_phentsize;

    uint8_t *ph = raw + e_phoff;
    uint32_t p_type; uint64_t p_offset, p_vaddr, p_filesz;
    memcpy(&p_type, ph, 4);
    memcpy(&p_offset, ph + 8, 8); memcpy(&p_vaddr, ph + 16, 8);
    memcpy(&p_filesz, ph + 32, 8);
    if (p_type != 1 || e_phnum < 1) { fprintf(stderr, "not PT_LOAD\n"); return 2; }

    size_t seg = (size_t)p_filesz;
    void *base = mmap(NULL, seg, PROT_READ | PROT_WRITE | PROT_EXEC,
                      MAP_PRIVATE | MAP_ANON, -1, 0);
    if (base == MAP_FAILED) { perror("mmap RWX"); return 2; }
    memcpy(base, raw + p_offset, seg);
    uint64_t entry_off = e_entry - p_vaddr;

    static const uint8_t tailpat[] = {0x48, 0x8B, 0x47, 0x38, 0xFF, 0xE0};
    long tail_off = -1;
    for (size_t i = 0; i + sizeof(tailpat) < seg; i++) {
        if (memcmp((uint8_t *)base + i, tailpat, sizeof(tailpat)) == 0) { tail_off = (long)i; break; }
    }
    char detail[256];
    snprintf(detail, sizeof detail, "entry_off=0x%llx tail_off=0x%lx",
             (unsigned long long)entry_off, tail_off);
    expect("locate tail_entry pattern", tail_off >= 0, detail);
    if (tail_off < 0) return 2;

    struct sigaction sa; memset(&sa, 0, sizeof sa);
    sa.sa_handler = on_ill; sigemptyset(&sa.sa_mask);
    sigaction(SIGILL, &sa, NULL);

    uint64_t ctx[32];
    entry_fn entry = (entry_fn)((uint8_t *)base + entry_off);
    entry_fn tail  = (entry_fn)((uint8_t *)base + (size_t)tail_off);

    /* run 1: full dispatch + fuel contract */
    memset(ctx, 0, sizeof ctx);
    ctx[SLOT_CAP_CALL]      = (uint64_t)(uintptr_t)cap_stub;
    ctx[SLOT_PAIR_NEW]      = (uint64_t)(uintptr_t)pair_new_stub;
    ctx[SLOT_PAIR_FIRST]    = (uint64_t)(uintptr_t)pair_first_stub;
    ctx[SLOT_PAIR_SECOND]   = (uint64_t)(uintptr_t)pair_second_stub;
    ctx[SLOT_STRING_EQUAL]  = (uint64_t)(uintptr_t)string_equal_stub;
    ctx[SLOT_STRING_CONCAT] = (uint64_t)(uintptr_t)string_concat_stub;
    ctx[FUEL_IDX] = 100;
    uint64_t r = entry(ctx);
    snprintf(detail, sizeof detail, "ret=%llu (expect 454)", (unsigned long long)r);
    expect("entry: vtable sum", r == 454, detail);
    snprintf(detail, sizeof detail, "fuel=%llu (expect 99)", (unsigned long long)ctx[FUEL_IDX]);
    expect("entry: fuel@8 decrement", ctx[FUEL_IDX] == 99, detail);
    snprintf(detail, sizeof detail,
             "cap=%d pnew=%d pfirst=%d psecond=%d seq=%d scat=%d",
             n_cap, n_pnew, n_pfirst, n_psecond, n_seq, n_scat);
    expect("entry: all slots called once",
           n_cap == 1 && n_pnew == 1 && n_pfirst == 1 && n_psecond == 1 &&
           n_seq == 1 && n_scat == 1, detail);

    /* run 2: tail dispatch */
    r = tail(ctx);
    snprintf(detail, sizeof detail, "ret=%llu (expect 56)", (unsigned long long)r);
    expect("tail_entry: jmp rax to pair_new", r == 56, detail);

    /* run 3: fuel exhausted -> js trap -> ud2 -> SIGILL */
    memset(ctx, 0, sizeof ctx);
    ctx[SLOT_CAP_CALL] = (uint64_t)(uintptr_t)cap_stub;
    ctx[FUEL_IDX] = 0;
    ill_hits = 0;
    if (sigsetjmp(env, 1) == 0) {
        volatile uint64_t ignored = entry(ctx);
        (void)ignored;
        expect("trap: SIGILL on fuel exhaustion", 0, "returned without trap");
    } else {
        /* fuel@8 write-back happens before the js, so the stored value is -1 */
        snprintf(detail, sizeof detail, "SIGILL caught x%d, fuel=%llu (expect 2^64-1)",
                 ill_hits, (unsigned long long)ctx[FUEL_IDX]);
        expect("trap: SIGILL on fuel exhaustion",
               ill_hits == 1 && ctx[FUEL_IDX] == UINT64_MAX, detail);
    }

    printf(failures == 0 ? "HARNESS_PASS\n" : "HARNESS_FAIL %d\n", failures);
    return failures == 0 ? 0 : 1;
}
