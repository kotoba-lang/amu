#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <sys/mman.h>
int g;
int main(int argc, char **argv, char **envp, char **apple) {
  long *a = (long *)argv;
  printf("argc=%d  argv[-1]==argc:%s  envp==argv+argc+1:%s  apple==envp+n+1:%s\n", argc, (a[-1] == argc) ? "yes" : "NO",
         (envp == argv + argc + 1) ? "yes" : "NO", "n/a");
  int n = 0; while (envp[n]) n++;
  printf("apple==envp+n+1:%s  nenv=%d\n", (apple == envp + n + 1) ? "yes" : "NO", n);
  printf("main=%p global=%p\n", (void *)main, (void *)&g);
  void *p = mmap((void *)0x40000000, 1 << 20, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANON | MAP_FIXED, -1, 0);
  printf("mmap fixed 0x40000000 -> %p\n", p);
  void *q = mmap((void *)0x400000, 1 << 20, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANON | MAP_FIXED, -1, 0);
  printf("mmap fixed 0x400000   -> %p\n", q);
  void *r = mmap((void *)0x200000000ULL, 1 << 20, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANON | MAP_FIXED, -1, 0);
  printf("mmap fixed 0x200000000 -> %p\n", r);
  return 0;
}
