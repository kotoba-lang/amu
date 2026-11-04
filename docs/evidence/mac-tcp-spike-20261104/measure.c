// Measures the Darwin TCP behaviours ADR 0404 still lists as unmeasured. libc wrappers (same kernel
// calls and constants as the direct-svc spike); loopback only; nothing leaves the machine.
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <signal.h>
#include <unistd.h>
#include <sys/socket.h>
#include <sys/wait.h>
#include <netinet/in.h>
#include <arpa/inet.h>

static int lis(int port, int *out_port) {
  int s = socket(AF_INET, SOCK_STREAM, 0), one = 1;
  setsockopt(s, SOL_SOCKET, SO_REUSEADDR, &one, 4);
  struct sockaddr_in a; memset(&a, 0, sizeof a);
  a.sin_len = 16; a.sin_family = AF_INET; a.sin_port = htons(port); a.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
  if (bind(s, (void *)&a, 16)) { perror("bind"); return -1; }
  listen(s, 4);
  socklen_t l = sizeof a;
  getsockname(s, (void *)&a, &l);
  if (out_port) *out_port = ntohs(a.sin_port);
  printf("getsockname: len=%u sin_len=%u family=%u port=%u (asked %d)\n", l, a.sin_len, a.sin_family, ntohs(a.sin_port), port);
  return s;
}
static int cli(int port, int nb) {
  int s = socket(AF_INET, SOCK_STREAM, 0);
  if (nb) fcntl(s, F_SETFL, O_NONBLOCK);
  struct sockaddr_in a; memset(&a, 0, sizeof a);
  a.sin_len = 16; a.sin_family = AF_INET; a.sin_port = htons(port); a.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
  int r = connect(s, (void *)&a, 16);
  printf("connect(nonblock=%d) -> %d errno=%d (%s)\n", nb, r, r ? errno : 0, r ? strerror(errno) : "ok");
  return s;
}
int main(void) {
  printf("CONST POLLIN=%d POLLOUT=%d POLLERR=%d POLLHUP=%d POLLNVAL=%d\n", POLLIN, POLLOUT, POLLERR, POLLHUP, POLLNVAL);
  printf("CONST F_GETFD=%d F_SETFD=%d FD_CLOEXEC=%d F_GETFL=%d F_SETFL=%d O_NONBLOCK=%d SO_ERROR=%d SO_LINGER=%d SO_NOSIGPIPE=0x%x\n",
         F_GETFD, F_SETFD, FD_CLOEXEC, F_GETFL, F_SETFL, O_NONBLOCK, SO_ERROR, SO_LINGER, SO_NOSIGPIPE);
  printf("ERRNO EAGAIN=%d EINPROGRESS=%d ECONNREFUSED=%d ECONNRESET=%d ENETUNREACH=%d EHOSTUNREACH=%d ETIMEDOUT=%d EPIPE=%d EADDRINUSE=%d\n",
         EAGAIN, EINPROGRESS, ECONNREFUSED, ECONNRESET, ENETUNREACH, EHOSTUNREACH, ETIMEDOUT, EPIPE, EADDRINUSE);

  puts("\n-- FD_CLOEXEC");
  int s = socket(AF_INET, SOCK_STREAM, 0);
  int before = fcntl(s, F_GETFD); int set = fcntl(s, F_SETFD, FD_CLOEXEC); int after = fcntl(s, F_GETFD);
  printf("F_GETFD before=%d F_SETFD->%d F_GETFD after=%d\n", before, set, after); close(s);

  puts("\n-- getsockname with port 0");
  int p; int L = lis(0, &p);

  puts("\n-- dial: refused / success (loopback)");
  int closedport; { int t = lis(0, &closedport); close(t); }
  int c0 = cli(closedport, 1);
  struct pollfd pf = { c0, POLLOUT | POLLIN, 0 };
  int pr = poll(&pf, 1, 2000);
  int err = 0; socklen_t el = 4; getsockopt(c0, SOL_SOCKET, SO_ERROR, &err, &el);
  printf("poll->%d revents=0x%x SO_ERROR=%d (%s)\n", pr, pf.revents, err, err ? strerror(err) : "none"); close(c0);
  int c1 = cli(p, 1);
  pf = (struct pollfd){ c1, POLLOUT, 0 }; pr = poll(&pf, 1, 2000);
  err = 0; getsockopt(c1, SOL_SOCKET, SO_ERROR, &err, &el);
  printf("to listener: poll->%d revents=0x%x SO_ERROR=%d\n", pr, pf.revents, err);
  int a1 = accept(L, 0, 0);
  printf("accepted fd flags O_NONBLOCK=%s FD_CLOEXEC=%s\n", (fcntl(a1, F_GETFL) & O_NONBLOCK) ? "inherited" : "not inherited", (fcntl(a1, F_GETFD) & FD_CLOEXEC) ? "inherited" : "not inherited");

  puts("\n-- POLLOUT and partial writes (peer not reading)");
  fcntl(a1, F_SETFL, O_NONBLOCK);
  char buf[16384]; memset(buf, 'x', sizeof buf);
  long total = 0; int writes = 0, partial = 0, first_eagain = 0;
  for (;;) {
    ssize_t w = write(c1, buf, sizeof buf);
    if (w < 0) { first_eagain = errno; break; }
    total += w; writes++; if (w < (ssize_t)sizeof buf) partial++;
    if (writes > 100000) break;
  }
  printf("wrote %ld bytes in %d writes, %d partial, stopped with errno=%d (EAGAIN=%d)\n", total, writes, partial, first_eagain, EAGAIN);
  pf = (struct pollfd){ c1, POLLOUT, 0 }; pr = poll(&pf, 1, 200);
  printf("poll POLLOUT while full -> %d revents=0x%x\n", pr, pf.revents);
  long drained = 0; char rb[65536];
  for (;;) { ssize_t r = read(a1, rb, sizeof rb); if (r <= 0) break; drained += r; }
  pf = (struct pollfd){ c1, POLLOUT, 0 }; pr = poll(&pf, 1, 2000);
  printf("drained %ld; poll POLLOUT after -> %d revents=0x%x\n", drained, pr, pf.revents);

  puts("\n-- orderly close: read returns 0");
  close(c1);
  pf = (struct pollfd){ a1, POLLIN, 0 }; pr = poll(&pf, 1, 2000);
  ssize_t r = read(a1, rb, sizeof rb);
  printf("poll->%d revents=0x%x read->%zd errno=%d\n", pr, pf.revents, r, r < 0 ? errno : 0); close(a1);

  puts("\n-- reset: SO_LINGER {1,0} then close sends RST");
  int c2 = cli(p, 0); int a2 = accept(L, 0, 0); fcntl(a2, F_SETFL, O_NONBLOCK);
  struct linger lg = { 1, 0 }; setsockopt(c2, SOL_SOCKET, SO_LINGER, &lg, sizeof lg); close(c2);
  pf = (struct pollfd){ a2, POLLIN, 0 }; pr = poll(&pf, 1, 2000);
  r = read(a2, rb, sizeof rb);
  printf("poll->%d revents=0x%x read->%zd errno=%d (ECONNRESET=%d)\n", pr, pf.revents, r, r < 0 ? errno : 0, ECONNRESET);

  puts("\n-- write to a reset peer: SIGPIPE?");
  for (int nosig = 0; nosig < 2; nosig++) {
    int c3 = cli(p, 0); int a3 = accept(L, 0, 0);
    if (nosig) { int one = 1; setsockopt(a3, SOL_SOCKET, SO_NOSIGPIPE, &one, 4); }
    close(c3);                                   // orderly close of the client
    usleep(100000);
    pid_t pid = fork();
    if (pid == 0) {
      ssize_t w1 = write(a3, "a", 1); usleep(100000);       // first write may succeed (RST comes back)
      ssize_t w2 = write(a3, "b", 1);
      printf("  child (SO_NOSIGPIPE=%d): w1=%zd w2=%zd errno=%d (EPIPE=%d)\n", nosig, w1, w2, w2 < 0 ? errno : 0, EPIPE);
      fflush(stdout); _exit(0);
    }
    int st; waitpid(pid, &st, 0);
    if (WIFSIGNALED(st)) printf("  child (SO_NOSIGPIPE=%d) killed by signal %d (SIGPIPE=%d)\n", nosig, WTERMSIG(st), SIGPIPE);
    close(a3);
  }
  return 0;
}
