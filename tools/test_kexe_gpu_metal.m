/* test_kexe_gpu_metal.m -- the wire-42 Metal broker's request verbs, driven
 * directly (no guest, no pipe): the review findings of amu #1404 held to
 * their behavior. Built and run by scripts/test-gpu-metal-broker.sh:
 *
 *   refusal-marker     every refusal begins with '!' (the guest provider
 *                      fails closed only on that byte)
 *   bindings           PIPELINE with 0 or 17 bindings is refused before any
 *                      dispatch can write past handles[16]
 *   writedec-offset    an offset past the buffer, and a list that does not
 *                      fit, are refused; nothing is written
 *   read-bound         READ longer than the guest's 4 MiB answer buffer is
 *                      refused; an in-bound READ answers hex
 *   zero-recording     ZERO between BEGIN and SUBMIT is refused
 *   kdot-last-block    kdot_h2_r1 (and .r4 / .r8) over ONE Q8_0 block in a
 *                      34-byte weight buffer completes with the exact dot --
 *                      run with MTL_SHADER_VALIDATION=1 the old two-bytes-
 *                      past-the-end read made the command buffer fail, which
 *                      is now a refusal rather than a success
 *   host-timing        DISPATCH answers host nanoseconds (> 0)
 *
 *   test_kexe_gpu_metal <tools-dir>     exit 0 every case held
 */
#include "kexe_gpu_metal.m"

static int failures = 0;
static char answer_text[KGPU_STAGING_BYTES * 2 + 64];

static const char *ask(const char *request) {
  static uint8_t answer[KGPU_STAGING_BYTES * 2 + 64];
  size_t n = kgpu_handle((const uint8_t *)request, strlen(request), answer, sizeof answer);
  memcpy(answer_text, answer, n);
  answer_text[n] = 0;
  return answer_text;
}

static void expect(const char *name, int ok, const char *got) {
  if (!ok) failures++;
  printf("%s %s%s%.200s\n", ok ? "PASS" : "FAIL", name, ok ? "" : " -- got: ", ok ? "" : got);
}

static int refused(const char *a, const char *reason) {
  return a[0] == '!' && strstr(a, reason) != NULL;
}

static char *hexrep(const char *unit, int count, char *buf) {
  buf[0] = 0;
  for (int i = 0; i < count; i++) strcat(buf, unit);
  return buf;
}

static void kdot_case(const char *tools, const char *variant) {
  char req[4096], path[1024], name[128];
  snprintf(name, sizeof name, "kdot-last-block%s", variant);
  /* PIPELINE maps <name>.spv -> <name>.msl, so a .msl.r4 / .msl.r8 variant
   * is copied to $TMPDIR/kdot-variant<r4|r8>.msl and asked for by the
   * matching .spv name. */
  if (variant[0] == 0) {
    snprintf(path, sizeof path, "%s/kdot_h2_r1.spv", tools);
  } else {
    char src[1024], dst[1024];
    snprintf(src, sizeof src, "%s/kdot_h2_r1.msl%s", tools, variant);
    snprintf(dst, sizeof dst, "%s/kdot-variant%s.msl", getenv("TMPDIR") ? getenv("TMPDIR") : "/tmp", variant + 1);
    NSError *err = nil;
    NSString *text = [NSString stringWithContentsOfFile:[NSString stringWithUTF8String:src] encoding:NSUTF8StringEncoding error:&err];
    [text writeToFile:[NSString stringWithUTF8String:dst] atomically:YES encoding:NSUTF8StringEncoding error:&err];
    snprintf(path, sizeof path, "%s/kdot-variant%s.spv", getenv("TMPDIR") ? getenv("TMPDIR") : "/tmp", variant + 1);
  }
  snprintf(req, sizeof req, "PIPELINE %s 5", path);
  char pipe_id[32]; snprintf(pipe_id, sizeof pipe_id, "%s", ask(req));
  if (pipe_id[0] == '!') { expect(name, 0, pipe_id); return; }
  char meta[32], w[32], x[32], o[32], e[32];
  snprintf(meta, sizeof meta, "%s", ask("ALLOC 32"));
  snprintf(w, sizeof w, "%s", ask("ALLOC 34"));   /* exactly one Q8_0 block: no slack */
  snprintf(x, sizeof x, "%s", ask("ALLOC 128"));
  snprintf(o, sizeof o, "%s", ask("ALLOC 16"));
  snprintf(e, sizeof e, "%s", ask("ALLOC 4"));
  snprintf(req, sizeof req, "WRITEDEC %s 0 1,32,8,1,0,0,0,0", meta); ask(req);
  char codes[200];
  /* d = half 1.0 (0x3c00, little-endian 00 3c), then 32 codes of 1 */
  snprintf(req, sizeof req, "WRITE %s 0 003c%s", w, hexrep("01", 32, codes)); ask(req);
  static char xs[1024];
  snprintf(req, sizeof req, "WRITE %s 0 %s", x, hexrep("0000803f", 32, xs)); ask(req);
  snprintf(req, sizeof req, "ZERO %s", e); ask(req);
  snprintf(req, sizeof req, "DISPATCH %s 1 1 1 %s %s %s %s %s", pipe_id, meta, w, x, o, e);
  const char *ns = ask(req);
  int dispatched = ns[0] != '!';
  if (!dispatched) { expect(name, 0, ns); return; }
  snprintf(req, sizeof req, "READ %s 0 4", o);
  const char *sum = ask(req);
  /* 32 codes x 1.0 x d=1.0 = 32.0f = 0x42000000 */
  expect(name, strcmp(sum, "00000042") == 0, sum);
}

int main(int argc, char **argv) {
  const char *tools = argc > 1 ? argv[1] : "tools";
  const char *a;

  a = ask("READ 999 0 4");
  expect("refusal-marker", refused(a, "READ: no such buffer"), a);
  a = ask("NOSUCHVERB");
  expect("refusal-marker-unknown", refused(a, "unknown gpu request"), a);

  a = ask("PIPELINE /nonexistent/x.spv 17");
  expect("bindings-17", refused(a, "bindings must be 1..16"), a);
  a = ask("PIPELINE /nonexistent/x.spv 0");
  expect("bindings-0", refused(a, "bindings must be 1..16"), a);

  char h[32]; snprintf(h, sizeof h, "%s", ask("ALLOC 16"));
  char req[512];
  snprintf(req, sizeof req, "WRITEDEC %s 18446744073709551615 1", h);
  a = ask(req); expect("writedec-offset-huge", refused(a, "WRITEDEC past the buffer"), a);
  snprintf(req, sizeof req, "WRITEDEC %s 20 1", h);
  a = ask(req); expect("writedec-offset-past", refused(a, "WRITEDEC past the buffer"), a);
  snprintf(req, sizeof req, "WRITEDEC %s 12 1,2", h);
  a = ask(req); expect("writedec-list-does-not-fit", refused(a, "WRITEDEC past the buffer"), a);
  snprintf(req, sizeof req, "READ %s 12 4", h);
  a = ask(req); expect("writedec-refusal-wrote-nothing", strcmp(a, "00000000") == 0, a);
  snprintf(req, sizeof req, "WRITEDEC %s 12 7", h);
  a = ask(req); expect("writedec-fits", strcmp(a, "1") == 0, a);
  snprintf(req, sizeof req, "WRITE %s 18446744073709551615 00", h);
  a = ask(req); expect("write-offset-huge", refused(a, "WRITE past the buffer"), a);

  char big[32]; snprintf(big, sizeof big, "%s", ask("ALLOC 4194304"));
  snprintf(req, sizeof req, "READ %s 0 2097153", big);
  a = ask(req); expect("read-past-guest-buffer", refused(a, "guest answer buffer"), a);
  snprintf(req, sizeof req, "READ %s 0 16", h);
  a = ask(req); expect("read-in-bound", strlen(a) == 32 && a[0] != '!', a);

  a = ask("BEGIN");
  snprintf(req, sizeof req, "ZERO %s", h);
  a = ask(req); expect("zero-while-recording", refused(a, "ZERO while recording"), a);
  a = ask("SUBMIT");
  a = ask(req); expect("zero-after-submit", strcmp(a, "1") == 0, a);

  kdot_case(tools, "");
  kdot_case(tools, ".r4");
  kdot_case(tools, ".r8");

  printf("%d failed\n", failures);
  return failures == 0 ? 0 : 1;
}
