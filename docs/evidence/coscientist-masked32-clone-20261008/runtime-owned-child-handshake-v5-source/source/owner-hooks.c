#ifdef KEXE_OWNERSHIP_DIAGNOSTIC_V3
#if !defined(__APPLE__) || __BYTE_ORDER__ != __ORDER_LITTLE_ENDIAN__
#error diagnostic ownership requires pinned little endian Darwin
#endif
#include <libproc.h>
#include <sys/time.h>
#define OH_MAGIC UINT64_C(0x32564e574f45584b)
struct oh_frame {uint64_t w[8]; unsigned char go[32], nonce[32];};
_Static_assert(sizeof(struct oh_frame)==128,"fixed ownership ABI");
static struct oh_frame oh_ticket;
static uint64_t oh_deadline,oh_child_birth,oh_cleanup_stop;
static pid_t oh_child,oh_owned_child;
enum oh_anchor_state {OH_NONE,OH_ANCHORED,OH_EXIT_HELD,OH_WAIT_ENTERED,OH_REAPED,OH_UNCERTAIN};
static enum oh_anchor_state oh_child_state=OH_NONE;
static int oh_gate[2]={-1,-1},oh_records;
static uint64_t oh_now(void) {struct timespec t;if(clock_gettime(CLOCK_MONOTONIC,&t))return UINT64_MAX;return (uint64_t)t.tv_sec*1000000000u+(uint64_t)t.tv_nsec;}
static int oh_io(int fd,void *buf,size_t n,int writing) {
 unsigned char *p=buf;size_t used=0;unsigned operations=0;
 while(used<n) {
  uint64_t now=oh_now();if(now>=oh_deadline||++operations>512)return -1;
  uint64_t ms=(oh_deadline-now+999999u)/1000000u;if(ms>30000)ms=30000;
  struct pollfd q={.fd=fd,.events=writing?POLLOUT:POLLIN};int ready=poll(&q,1,(int)ms);
  if(ready<0&&errno==EINTR)continue;
  if(ready<=0||(q.revents&(POLLERR|POLLNVAL))||!(q.revents&q.events))return -1;
  ssize_t got=writing?write(fd,p+used,n-used):read(fd,p+used,n-used);
  if(got<0&&errno==EINTR)continue;
  if(got<=0)return -1;used+=(size_t)got;
 }
 return oh_now()<oh_deadline?0:-1;
}
static int oh_send(struct oh_frame *q) {if(++oh_records>8)return -1;return oh_io(4,q,sizeof(*q),1);}
static int oh_recv(struct oh_frame *q) {if(++oh_records>8)return -1;return oh_io(4,q,sizeof(*q),0);}
static int oh_birth(pid_t pid,pid_t group,uint64_t *birth) {
 struct rusage_info_v0 r={0};if(getpgid(pid)!=group)return -1;
 if(proc_pid_rusage(pid,RUSAGE_INFO_V0,(rusage_info_t*)&r)||!r.ri_proc_start_abstime||r.ri_proc_exit_abstime)return -1;
 *birth=r.ri_proc_start_abstime;return 0;
}
static int oh_hold(unsigned stage,pid_t child,uint64_t birth) {
 struct oh_frame q=oh_ticket,ack;
 q.w[1]=stage;q.w[2]=stage==2?1:2;q.w[3]=(uint64_t)getpid();q.w[4]=(uint64_t)child;q.w[5]=birth;q.w[6]=(uint64_t)getpgrp();q.w[7]=0;
 if(oh_send(&q)||oh_recv(&ack))return -1;
 q.w[1]=stage+1;
 return memcmp(&ack,&q,sizeof(q))==0?0:-1;
}
static int oh_close_gate(void) {int rc=0;for(int i=0;i<2;i++)if(oh_gate[i]>=0){int fd=oh_gate[i];oh_gate[i]=-1;if(close(fd))rc=-1;}return rc;}
static int oh_begin(void) {
 uint64_t now=oh_now();if(now==UINT64_MAX||kexe_wall_seconds!=30)return -1;oh_deadline=now+30000000000u;
 int flags=fcntl(4,F_GETFL);if(flags<0||!(flags&O_NONBLOCK))return -1;
 if(oh_recv(&oh_ticket)||oh_ticket.w[0]!=OH_MAGIC||oh_ticket.w[1]!=1||oh_ticket.w[2]!=0||oh_ticket.w[3]!=(uint64_t)getpid()||oh_ticket.w[4]||oh_ticket.w[5]||oh_ticket.w[6]!=(uint64_t)getpid()||oh_ticket.w[7]<=oh_now()||oh_ticket.w[7]>oh_deadline)return -1;
 oh_deadline=oh_ticket.w[7];
 uint64_t birth=0;if(oh_birth(getpid(),getpid(),&birth)||oh_hold(2,0,birth))return -1;
 if(pipe(oh_gate))return -1;
 for(int i=0;i<2;i++)if(fcntl(oh_gate[i],F_SETFD,FD_CLOEXEC)<0||fcntl(oh_gate[i],F_SETFL,O_NONBLOCK)<0){oh_close_gate();return -1;}
 return 0;
}
static int oh_parent_release(pid_t child) {
 oh_child=child;int read_end=oh_gate[0];oh_gate[0]=-1;if(close(read_end))return -1;
 if(oh_birth(child,getpid(),&oh_child_birth)||oh_hold(4,child,oh_child_birth))return -1;
 unsigned char token=0x5a;int rc=oh_io(oh_gate[1],&token,1,1);if(oh_close_gate())return -1;return rc;
}
static int oh_guest_gate(void) {
 int write_end=oh_gate[1];oh_gate[1]=-1;if(close(write_end)||close(4))return -1;
 unsigned char token=0;int rc=oh_io(oh_gate[0],&token,1,0);if(oh_close_gate())return -1;
 return rc==0&&token==0x5a?0:-1;
}
static void oh_cleanup_record(const char *tag) {
 /* Diagnostic refusal evidence only; partial/error write is not a receipt proof. */
 char line[128];int n=snprintf(line,sizeof(line),"KEXE_OWNERSHIP_CHILD_CLEANUP:%s\n",tag);
 if(n<=0||n>=(int)sizeof(line))return;
 int flags=fcntl(STDERR_FILENO,F_GETFL);
 if(flags<0||fcntl(STDERR_FILENO,F_SETFL,flags|O_NONBLOCK)<0)return;
 uint64_t stop=oh_cleanup_stop;
 size_t sent=0;for(unsigned k=0;k<512&&sent<(size_t)n&&oh_now()<stop;k++) {
  ssize_t q=write(STDERR_FILENO,line+sent,(size_t)n-sent);
  if(q>0)sent+=(size_t)q;
  else if(q<0&&errno==EINTR)continue;
  else if(q<0&&(errno==EAGAIN||errno==EWOULDBLOCK)) {
   struct pollfd p={.fd=STDERR_FILENO,.events=POLLOUT};(void)poll(&p,1,10);
  }else break;
 }
 /* Failure path only; never restore/reuse a descriptor after uncertain close. */
}
static void oh_abort_unwaited(pid_t child) {
 /* Never infer numeric-PID authority from a failed wait. The signal target
  * is permanently retired BEFORE every potentially reaping cleanup wait. */
 uint64_t begin=oh_now();oh_cleanup_stop=begin>UINT64_MAX-UINT64_C(5000000000)?UINT64_MAX:begin+UINT64_C(5000000000);
 supervised_pid=-1;alarm(0);(void)oh_close_gate();
 if(child!=oh_owned_child || (oh_child_state!=OH_ANCHORED&&oh_child_state!=OH_EXIT_HELD)) {
  oh_cleanup_record(oh_child_state==OH_REAPED?"reaped":"uncertain-no-further-signal");return;
 }
 int killed=kill(child,SIGKILL);int kill_error=errno;
 uint64_t stop=oh_cleanup_stop;
 oh_child_state=OH_WAIT_ENTERED;
 for(unsigned n=0;n<512;n++) {
  int s=0;pid_t w=waitpid(child,&s,WNOHANG);
  if(w==child) {oh_child_state=OH_REAPED;oh_cleanup_record("exact-reaped");return;}
  if(w<0&&errno!=EINTR) {oh_child_state=OH_UNCERTAIN;oh_cleanup_record("wait-error-uncertain");return;}
  if(oh_now()>=stop)break;
  (void)poll(NULL,0,10);
 }
 oh_child_state=OH_UNCERTAIN;
 oh_cleanup_record(killed==0||kill_error==ESRCH?"cleanup-deadline-uncertain":"kill-failed-unclosed");
}
static int oh_supervisor_refuse(pid_t child,int code) {oh_abort_unwaited(child);return code;}
static int oh_exit_held(pid_t child) {
 siginfo_t info;memset(&info,0,sizeof(info));
 unsigned tries=0;
 for(;;) {
  if(++tries>512||oh_now()>=oh_deadline)return -1;
  if(waitid(P_PID,(id_t)child,&info,WEXITED|WNOWAIT)==0)break;
  if(errno!=EINTR)return -1;
 }
 if(info.si_pid!=child)return -1;
 oh_child_state=OH_EXIT_HELD;
 if(info.si_code!=CLD_EXITED||info.si_status!=0)return -1;
 struct oh_frame q=oh_ticket,ack;q.w[1]=6;q.w[2]=3;q.w[3]=(uint64_t)getpid();q.w[4]=(uint64_t)child;q.w[5]=oh_child_birth;q.w[6]=(uint64_t)getpid();q.w[7]=0;
 if(child!=oh_child||!oh_child_birth||oh_send(&q)||oh_recv(&ack))return -1;
 q.w[1]=7;return memcmp(&q,&ack,sizeof(q))==0?0:-1;
}
static int oh_arm_deadline(int guest) {
 uint64_t now=oh_now();uint64_t end=oh_deadline;
 if(guest) {if(end<1000000000u)return -1;end-=1000000000u;}
 if(now>=end)return -1;
 uint64_t us=(end-now)/1000u;if(!us)return -1;
 struct itimerval timer;memset(&timer,0,sizeof(timer));timer.it_value.tv_sec=(time_t)(us/1000000u);timer.it_value.tv_usec=(suseconds_t)(us%1000000u);
 return setitimer(ITIMER_REAL,&timer,NULL);
}
static int oh_wait_receipt(pid_t child,int status) {
 struct oh_frame q=oh_ticket;q.w[1]=8;q.w[2]=4;q.w[3]=(uint64_t)getpid();q.w[4]=(uint64_t)child;q.w[5]=oh_child_birth;q.w[6]=(uint64_t)getpid();q.w[7]=(uint64_t)(unsigned int)status;
 if(child!=oh_child||!oh_child_birth||oh_send(&q))return -1;
 return close(4);
}
#endif
