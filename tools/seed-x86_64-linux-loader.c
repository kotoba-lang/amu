/* Optional native compiler launcher. The pinned loader, syscall filter,
 * grants and resource limits are included unchanged. Pre-map 512 KiB of the
 * existing process stack before the loader lowers RLIMIT_AS below the size
 * of its fixed arenas. Stay below its 1 MiB stack budget; no runtime mmap. */
#define main kexe_pinned_loader_main
#include "../seed/bootstrap/adopted-loader-20261012.c"
#undef main

#if !defined(__linux__) || !defined(__x86_64__)
#error "this bootstrap launcher is only for x86_64 Linux"
#endif

__attribute__((noinline)) static void compiler_stack_reserve(void) {
  volatile unsigned char pages[512u * 1024u];
  __asm__ __volatile__("" : : "r"(pages) : "memory");
  for (size_t i = 0; i < sizeof(pages); i += 4096u) pages[i] = 0;
  pages[sizeof(pages) - 1u] = 0;
}

int main(int argc, char **argv) {
  struct rlimit launch;
  if (getrlimit(RLIMIT_STACK, &launch) != 0 ||
      (launch.rlim_cur != RLIM_INFINITY && launch.rlim_cur < 1024u * 1024u)) {
    fprintf(stderr, "native compiler requires at least 1 MiB launch stack\n");
    return 2;
  }
  compiler_stack_reserve();
  return kexe_pinned_loader_main(argc, argv);
}
