/* Diagnostic timing consumer; included after the exact current loader helpers. */
#include <dlfcn.h>
#include "timing-packet-generated.h"
struct timing_shared { uint64_t elapsed_ns, calls, warmup, arm, verified, benchmark_fuel, verify_fuel, state; };
static struct timing_shared *timing_receipt;
static uint64_t timing_calls, timing_warmup;
static unsigned timing_arm;
static kexe_fn8 timing_c_fn;
static void *timing_c_handle;
static uint64_t timing_now(void) {
  struct timespec t;
  if (clock_gettime(CLOCK_MONOTONIC_RAW,&t)!=0) fail("timing clock");
  return (uint64_t)t.tv_sec*UINT64_C(1000000000)+(uint64_t)t.tv_nsec;
}
static uint64_t timing_decimal(const char *s,uint64_t hi) {
  if (!s || !*s) { fprintf(stderr,"timing decimal empty\n");exit(2); }
  uint64_t n=0;
  for (;*s;s++) { if (*s<'0'||*s>'9'||((unsigned)(*s-'0')>hi || n>(hi-(unsigned)(*s-'0'))/10)) {fprintf(stderr,"timing decimal bounds\n");exit(2);} n=n*10+(unsigned)(*s-'0'); }
  return n;
}
static void timing_reset(struct kexe_shared_v11 *s) {
  if (!kexe_use || !kexe_vector_region || !kexe_growth_regions || !kexe_string_regions || !kexe_string_region_cache || kexe_hashcons || kexe_empty_vector || kexe_census_sites || kexe_census_pair_sites || kexe_stdout_used || kexe_append_used) {
    fprintf(stderr,"timing unsupported reset state\n");raise(SIGILL);
  }
  uint64_t p=s->pair_used>kexe_use->peak_pairs?s->pair_used:kexe_use->peak_pairs;
  uint64_t v=s->vector_used>kexe_use->peak_vectors?s->vector_used:kexe_use->peak_vectors;
  if(p>KEXE_PAIR_MAX||v>KEXE_VECTOR_MAX) raise(SIGILL);
  memset(s->pair_validated,0,(size_t)p);
  memset(kexe_vector_region,0,(size_t)v*sizeof(*kexe_vector_region));
  if(kexe_use->string_regions) memset(kexe_string_region_cache,0,KEXE_STRING_REGION_CACHE*sizeof(*kexe_string_region_cache));
  kexe_growth_region_count=0;kexe_string_region_count=0;
  memset(kexe_growth_region_marks,0,sizeof(kexe_growth_region_marks));
  memset(kexe_string_region_marks,0,sizeof(kexe_string_region_marks));
  memset(s->arena_scope_marks,0,sizeof(s->arena_scope_marks));
  s->pair_used=0;s->kgraph_used=0;s->string_pool_used=0;s->vector_used=0;s->vector_item_used=0;
  s->arena_scope_depth=0;s->region_used=0;s->region_count=0;
  s->budget_exhausted=0;s->value_trap=0;s->result=0;s->completed=0;
  memset(kexe_use,0,sizeof(*kexe_use));s->context.fuel=kexe_initial_fuel;
}
static void timing_snapshot(struct kexe_shared_v11*s,uint64_t a[17]) {
#define TP(field,peak) (s->field>kexe_use->peak?s->field:kexe_use->peak)
  a[0]=TP(pair_used,peak_pairs);a[1]=TP(string_pool_used,peak_string_pool);
  a[2]=TP(vector_used,peak_vectors);a[3]=TP(vector_item_used,peak_vector_items);
  a[4]=a[0]*sizeof(struct kexe_pair_v1)+a[1]+a[2]*sizeof(struct kexe_vector_v1)+a[3]*8;
  a[5]=kexe_use->conj_calls;a[6]=kexe_use->conj_tail;a[7]=kexe_use->conj_region;a[8]=kexe_use->conj_copy;
  a[9]=kexe_use->copied_words;a[10]=kexe_use->reserved_words;a[11]=kexe_use->regions;a[12]=kexe_use->scope_releases;
  a[13]=kexe_use->string_regions;a[14]=kexe_use->string_region_appends;a[15]=kexe_use->string_copied_bytes;a[16]=kexe_use->string_reserved_bytes;
#undef TP
}
/* One benchmark() clock bracket; verify-state follows in the SAME context.
 * Reset/warmup/arena receipt work are outside the measured interval. */
static int64_t timing_loop(kexe_fn8 fn,struct kexe_shared_v11*s,int64_t args[5]) {
  if(!kexe_fuel_metered || !kexe_initial_fuel || kexe_initial_fuel>KEXE_FUEL_MAX || args[0]<=0) raise(SIGILL);
  unsigned char *base=(unsigned char *)(uintptr_t)fn-TIMING_BENCH_OFFSET;
  kexe_fn8 verify=(kexe_fn8)(base+TIMING_VERIFY_OFFSET);
  timing_reset(s);
  int64_t warm=fn(1,0,0,0,0,0,0,(int64_t)(uintptr_t)&s->context);
  if(s->budget_exhausted||s->value_trap||s->arena_scope_depth)raise(SIGILL);
  int64_t warm_seed=0;
  if(TIMING_WARM_SEED_OFFSET>=0){
    kexe_fn8 seed=(kexe_fn8)(base+TIMING_WARM_SEED_OFFSET);
    warm_seed=seed(warm,0,0,0,0,0,0,(int64_t)(uintptr_t)&s->context);
    if(s->budget_exhausted||s->value_trap)raise(SIGILL);
  }
  timing_reset(s);
  uint64_t initial=s->context.fuel,begin=timing_now();
  int64_t state=fn(args[0],warm_seed,0,0,0,0,0,(int64_t)(uintptr_t)&s->context);
  uint64_t end=timing_now(),benchmark_fuel=initial-s->context.fuel;
  if(end<begin||s->budget_exhausted||s->value_trap||s->arena_scope_depth)raise(SIGILL);
  uint64_t before=s->context.fuel;
  int64_t verified=verify(state,args[0],0,0,0,0,0,(int64_t)(uintptr_t)&s->context);
  if(verified!=1||s->budget_exhausted||s->value_trap||s->arena_scope_depth)raise(SIGILL);
  timing_receipt->elapsed_ns=end-begin;timing_receipt->calls=1;timing_receipt->warmup=1;
  timing_receipt->benchmark_fuel=benchmark_fuel;timing_receipt->verify_fuel=before-s->context.fuel;
  timing_receipt->state=(uint64_t)state;timing_receipt->verified=1;return verified;
}
static void timing_parent_report(int status) {
 if(status||!timing_receipt->verified)return;
 printf("{\"schema\":\"SEPARATED_TRANSLATED_BENCHMARK_VERIFY_V1\",\"elapsedNs\":%llu,\"benchmarkFuel\":%llu,\"verifyFuel\":%llu,\"warmupBodies\":1,\"calls\":1,\"result\":1,\"verifyOutsideTiming\":true,\"resetIncluded\":false,\"sameContextVerify\":true}\n",
  (unsigned long long)timing_receipt->elapsed_ns,(unsigned long long)timing_receipt->benchmark_fuel,(unsigned long long)timing_receipt->verify_fuel);
}
