#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>
static int lis(int *port, int nb) {
  int s = socket(AF_INET, SOCK_STREAM, 0), one = 1;
  setsockopt(s, SOL_SOCKET, SO_REUSEADDR, &one, 4);
  struct sockaddr_in a; memset(&a, 0, sizeof a);
  a.sin_len = 16; a.sin_family = AF_INET; a.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
  bind(s, (void *)&a, 16); listen(s, 4);
  socklen_t l = 16; getsockname(s, (void *)&a, &l); *port = ntohs(a.sin_port);
  if (nb) fcntl(s, F_SETFL, O_NONBLOCK);
  return s;
}
static int dial(int port) {
  int s = socket(AF_INET, SOCK_STREAM, 0);
  struct sockaddr_in a; memset(&a, 0, sizeof a);
  a.sin_len = 16; a.sin_family = AF_INET; a.sin_port = htons(port); a.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
  connect(s, (void *)&a, 16); return s;
}
int main(void) {
  setvbuf(stdout, 0, _IONBF, 0);
  for (int nb = 0; nb < 2; nb++) {
    int p; int L = lis(&p, nb); int c = dial(p);
    struct pollfd pf = { L, POLLIN, 0 }; poll(&pf, 1, 2000);
    int a = accept(L, 0, 0);
    printf("listener O_NONBLOCK=%d -> accepted socket O_NONBLOCK=%s\n", nb, (fcntl(a, F_GETFL) & O_NONBLOCK) ? "inherited" : "NOT inherited");
    close(a); close(c); close(L);
  }
  puts("-- orderly close, nothing in flight");
  int p; int L = lis(&p, 0); int c = dial(p); int a = accept(L, 0, 0);
  close(c);
  struct pollfd pf = { a, POLLIN, 0 }; int pr = poll(&pf, 1, 2000);
  char b[64]; ssize_t r = read(a, b, sizeof b);
  printf("poll->%d revents=0x%x read->%zd errno=%d\n", pr, pf.revents, r, r < 0 ? errno : 0);
  r = read(a, b, sizeof b);
  printf("second read->%zd\n", r);
  puts("-- write timeout shape: peer idle, how long until POLLOUT is absent for a full buffer");
  close(a);
  return 0;
}
