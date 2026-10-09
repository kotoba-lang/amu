/* BOOTSTRAP-TOOL: unchanged original body/verifier; untimed snapshots. */
#define GLOBAL_SCALE_FACTOR 1
#include <stdint.h>
#include "../upstream/src/aha-mont64/mont64.c"
#define EXTRA int64_t x1,int64_t x2,int64_t x3,int64_t x4,int64_t x5,int64_t x6,int64_t ctx
static uint64 snapshot[4];
static int
observed_body(unsigned int lsf, unsigned int gsf)
{
  int i;
  int errors;

  for (unsigned int lsf_cnt = 0; lsf_cnt < lsf; lsf_cnt++)
    for (unsigned int gsf_cnt = 0; gsf_cnt < gsf; gsf_cnt++)
      {
	uint64 a, b, m, hr, p1hi, p1lo, p1, p, abar, bbar;
	uint64 phi, plo;
	volatile uint64 rinv, mprime;
	errors = 0;

	m = in_m;			// Must be odd.
	b = in_b;			// Must be smaller than m.
	a = in_a;			// Must be smaller than m.

	/* The simple calculation: This computes (a*b)**4 (mod m) correctly for all a,
	   b, m < 2**64. */

	mulul64 (a, b, &p1hi, &p1lo);	// Compute a*b (mod m).
	p1 = modul64 (p1hi, p1lo, m);
	mulul64 (p1, p1, &p1hi, &p1lo);	// Compute (a*b)**2 (mod m).
	p1 = modul64 (p1hi, p1lo, m);
	mulul64 (p1, p1, &p1hi, &p1lo);	// Compute (a*b)**4 (mod m).
	p1 = modul64 (p1hi, p1lo, m);

	/* The MM method uses a quantity r that is the smallest power of 2
	   that is larger than m, and hence also larger than a and b. Here we
	   deal with a variable hr that is just half of r. This is because r can
	   be as large as 2**64, which doesn't fit in one 64-bit word. So we
	   deal with hr, where 2**63 <= hr <= 1, and make the appropriate
	   adjustments wherever it is used.
	   We fix r at 2**64, and its log base 2 at 64. It doesn't hurt if
	   they are too big, it's just that some quantities (e.g., mprime) come
	   out larger than they would otherwise be. */

	hr = 0x8000000000000000LL;

	/* Now, for the MM method, first compute the quantities that are
	   functions of only r and m, and hence are relatively constant. These
	   quantities can be used repeatedly, without change, when raising a
	   number to a large power modulo m.
	   First use the extended GCD algorithm to compute two numbers rinv
	   and mprime, such that

	   r*rinv - m*mprime = 1

	   Reading this nodulo m, clearly r*rinv = 1 (mod m), i.e., rinv is the
	   multiplicative inverse of r modulo m. It is needed to convert the
	   result of MM back to a normal number. The other calculated number,
	   mprime, is used in the MM algorithm. */

	xbinGCD (hr, m, &rinv, &mprime);	// xbinGCD, in effect, doubles hr.

	/* Do a partial check of the results. It is partial because the
	   multiplications here give only the low-order half (64 bits) of the
	   products. */

	if (2 * hr * rinv - m * mprime != 1)
	  {
	    errors = 1;
	  }

	/* Compute abar = a*r(mod m) and bbar = b*r(mod m). That is, abar =
	   (a << 64)%m, and bbar = (b << 64)%m. */

	abar = modul64 (a, 0, m);
	bbar = modul64 (b, 0, m);

	p = montmul (abar, bbar, m, mprime);	/* Compute a*b (mod m). */
	p = montmul (p, p, m, mprime);	/* Compute (a*b)**2 (mod m). */
	p = montmul (p, p, m, mprime);	/* Compute (a*b)**4 (mod m). */

	/* Convert p back to a normal number by p = (p*rinv)%m. */

	mulul64 (p, rinv, &phi, &plo);
	p = modul64 (phi, plo, m);
	if (p != p1)
	  errors = 1;
        snapshot[0]=p1;snapshot[1]=p;snapshot[2]=(2*hr*rinv-m*mprime==1);snapshot[3]=errors;
      }

  return errors;
}

int64_t bench(int64_t n,EXTRA){if(!n)return 0;initialise_benchmark();return verify_benchmark(benchmark_body(1,n));}
int64_t observe(int64_t encoded,EXTRA){initialise_benchmark();observed_body(1,encoded/4);return (int64_t)snapshot[encoded%4];}
int64_t oracle_selfcheck(int64_t n,EXTRA){initialise_benchmark();int a=observed_body(1,n),b=benchmark_body(1,n);return a==b&&verify_benchmark(a)&&verify_benchmark(b)&&snapshot[0]==snapshot[1]&&snapshot[2]==1&&snapshot[3]==0;}
