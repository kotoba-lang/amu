#include <stdint.h>
int64_t run(int64_t n, int64_t a, int64_t b, int64_t c, int64_t d,
            int64_t e, int64_t f, int64_t context) {
  (void)n; (void)a; (void)b; (void)c; (void)d; (void)e; (void)f; (void)context;
  uint64_t value=17;
  for (int i=0;i<10000;i++) value=value*UINT64_C(6364136223846793005)+1;
  return (int64_t)value;
}
