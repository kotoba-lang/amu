#include <signal.h>
#include <sys/time.h>
#include <sys/ucontext.h>
static volatile uintptr_t prof_base, prof_len;
static uint32_t prof_hist[1<<20]; static volatile uint64_t prof_out;
static void prof_handler(int sig, siginfo_t *si, void *uc_) {
  ucontext_t *uc=(ucontext_t*)uc_; uintptr_t pc=(uintptr_t)uc->uc_mcontext->__ss.__pc;
  if (pc>=prof_base && pc<prof_base+prof_len) { uintptr_t o=(pc-prof_base)>>2; if(o<(1<<20)) prof_hist[o]++; } else prof_out++;
}
static void prof_start(void *base, size_t len){ prof_base=(uintptr_t)base; prof_len=len;
  struct sigaction sa; memset(&sa,0,sizeof sa); sa.sa_sigaction=prof_handler; sa.sa_flags=SA_SIGINFO|SA_RESTART; sigaction(SIGPROF,&sa,0);
  struct itimerval it={{0,100},{0,100}}; setitimer(ITIMER_PROF,&it,0);}
static void prof_stop(void){ struct itimerval it={{0,0},{0,0}}; setitimer(ITIMER_PROF,&it,0);
  for (uint32_t i=0;i<(1<<20);i++) if(prof_hist[i]) fprintf(stderr,"PROF %x %u\n",i*4,prof_hist[i]); fprintf(stderr,"PROF out %llu\n",(unsigned long long)prof_out);}
