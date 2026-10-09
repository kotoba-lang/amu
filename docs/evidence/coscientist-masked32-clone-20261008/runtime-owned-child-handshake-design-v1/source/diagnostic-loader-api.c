/* SOURCE interface/insertion sketch ONLY, not a compiled or complete patch.
 * Future fresh copied f44 loader, enabled by KEXE_OWNERSHIP_DIAGNOSTIC_V1.
 * Native argv and supplied environment17 unchanged. FD4 is a NEW explicit
 * host-private duplex endpoint, installed by a separately qualified wrapper.
 * Record 128 bytes: 8 LE u64 words, GO SHA25632, invocation nonce32.
 * No guest receives FD4 or either internal gate endpoint at guest entry.
 */
#include <stdint.h>
#include <sys/types.h>
#include <sys/resource.h>
#include <unistd.h>
#include <libproc.h>
#define OWNER_HOST_FD 4
#define OWNER_MAX_RECORDS 8
#define OWNER_RECORD_BYTES 128
struct owner_birth { pid_t pid; pid_t pgid; uint64_t start; };
/* Concrete primary SDK API use. Caller invokes only while target is held.
 * Every failure refuses; no read-error suppression or PID-only acceptance.
 */
static int owner_read_birth(pid_t pid, pid_t leader, struct owner_birth *out) {
  struct rusage_info_v0 r = {0};
  pid_t pgid = getpgid(pid);
  if (pgid != leader) return -1;
  if (proc_pid_rusage(pid, RUSAGE_INFO_V0, (rusage_info_t *)&r) != 0) return -1;
  if (!r.ri_proc_start_abstime || r.ri_proc_exit_abstime) return -1;
  out->pid = pid; out->pgid = pgid; out->start = r.ri_proc_start_abstime;
  return 0;
}
/* Required fixed protocol helpers NOT implemented/qualified in this design.
 * Implement with poll/read/write using ORIGINAL absolute deadline; bounded
 * fixed128B records, max8; no malloc, no stdio/guest stdout/stderr. The ACK
 * echoes exact stage/sequence/GO/nonce/birth and only follows supervisor fsync.
 * All partial/duplicate/out-of-order/missing ACK/errors are terminal failures.
 */
int owner_ticket_and_hold_leader(int fd, pid_t leader, uint64_t deadline);
int owner_child_hold(int gate_read, int host_fd, uint64_t deadline);
int owner_parent_bind_ack_release(int fd, int gate_write, pid_t leader,
                                 pid_t child, uint64_t deadline);
int owner_child_wait_receipt(int fd, pid_t child, uint64_t birth,
                             int exact_wait_status, uint64_t deadline);
/* f44 main insertion at12910 (before ordinary fork):
 *   validate descriptors4 and create ONE private gate pipe under cleanup;
 *   leader reads currentGO ticket; own held birth/group emitted; waitACK;
 *   child=fork(); on error fail closed; no repeated fork;
 *   child==0: close gate_write and hostFD; wait one release token;
 *             close gate_read BEFORE install_limits/sandbox/guest;
 *   child>0: close gate_read; owner_read_birth(child) while gate holds child;
 *             emit fork-result,parent/birth/pgid/GO/nonce; wait durable ACK;
 *             write one token; close gate_write; call unchanged supervise;
 * f44 supervise insertion at11771 after successful exact waitpid(child):
 *   emit correlated child wait status ONCE before reporting; no group lookup
 *   or signal after this reaping point. If journal fails, diagnostic fails.
 * unchanged ordinary sandbox/limits/trap/raw result17arena reporting.
 * Failure BEFORE release: child never starts; close gate to make child refuse;
 * parent kill/wait only its exact unreaped child using original bounded cleanup.
 * Supervisor leader signaling retires BEFORE ANY direct potentially reaping
 * wait, including exception gaps; no post-wait group API. Unknown closure is
 * retained honestly and cannot publish COMPLETE.
 */
