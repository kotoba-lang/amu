/* BOOTSTRAP-TOOL: original C body, with only initialized y captured. */
#define GLOBAL_SCALE_FACTOR 1
#include <stdint.h>
#include <limits.h>
#include "../upstream/src/ud/libud.c"
#define EXTRA int64_t x1,int64_t x2,int64_t x3,int64_t x4,int64_t x5,int64_t x6,int64_t ctx
static long snapshot_y[6];
static int observed_ludcmp(int nmax, int n)
{
  int i, j, k;
  long w, y[100];

  /* if(n > 99 || eps <= 0.0) return(999); */
  for(i = 0; i < n; i++)
    {
      /* if(fabs(a[i][i]) <= eps) return(1); */
      for(j = i+1; j <= n; j++) /* triangular loop vs. i */
        {
          w = a[j][i];
          if(i != 0)            /* sub-loop is conditional, done
                                   all iterations except first of the
                                   OUTER loop */
            for(k = 0; k < i; k++)
              w -= a[j][k] * a[k][i];
          a[j][i] = w / a[i][i];
        }
      for(j = i+1; j <= n; j++) /* triangular loop vs. i */
        {
          w = a[i+1][j];
          for(k = 0; k <= i; k++) /* triangular loop vs. i */
            w -= a[i+1][k] * a[k][j];
          a[i+1][j] = w;
        }
    }
  y[0] = b[0];
  for(i = 1; i <= n; i++)       /* iterates n times */
    {
      w = b[i];
      for(j = 0; j < i; j++)    /* triangular sub loop */
        w -= a[i][j] * y[j];
      y[i] = w;
    }
  x[n] = y[n] / a[n][n];
  for(i = n-1; i >= 0; i--)     /* iterates n times */
    {
      w = y[i];
      for(j = i+1; j <= n; j++) /* triangular sub loop */
        w -= a[i][j] * x[j];
      x[i] = w / a[i][i] ;
    }
  for(int observer_i=0;observer_i<6;observer_i++)snapshot_y[observer_i]=y[observer_i];
  return(0);
}
static int
observed_body(unsigned int lsf, unsigned int gsf)
{
  for (unsigned int lsf_cnt = 0; lsf_cnt < lsf; lsf_cnt++)
    for (unsigned int gsf_cnt = 0; gsf_cnt < gsf; gsf_cnt++)
      {
	int      i, j, nmax = 20, n = 5;
	long int /* eps, */ w;

	/* eps = 1.0e-6; */

	/* Init loop */
	for(i = 0; i <= n; i++)
	  {
	    w = 0;              /* data to fill in cells */
	    for(j = 0; j <= n; j++)
	      {
		a[i][j] = (i + 1) + (j + 1);
		if(i == j)            /* only once per loop pass */
		  a[i][j] *= 2;
		w += a[i][j];
	      }
	    b[i] = w;
	  }

	/*  chkerr = ludcmp(nmax, n, eps); */
	chkerr = observed_ludcmp(nmax,n);
      }

  return chkerr;
}

static int64_t field(int cell){if(cell<400)return a[cell/20][cell%20];if(cell<420)return b[cell-400];if(cell<440)return x[cell-420];if(cell<446)return snapshot_y[cell-440];if(cell==540)return chkerr;return INT64_MIN;}
int64_t bench(int64_t n,EXTRA){if(!n)return 0;initialise_benchmark();return verify_benchmark(benchmark_body(1,n));}
int64_t observe(int64_t encoded,EXTRA){memset(a,0,sizeof(a));memset(b,0,sizeof(b));memset(x,0,sizeof(x));memset(snapshot_y,0,sizeof(snapshot_y));chkerr=0;if(encoded/1024)observed_body(1,encoded/1024);return field(encoded%1024);}
int64_t oracle_selfcheck(int64_t n,EXTRA){int r=observed_body(1,n);long saved_a[20][20],saved_b[20],saved_x[20];memcpy(saved_a,a,sizeof(a));memcpy(saved_b,b,sizeof(b));memcpy(saved_x,x,sizeof(x));int s=benchmark_body(1,n);return r==s&&verify_benchmark(r)&&verify_benchmark(s)&&memcmp(saved_a,a,sizeof(a))==0&&memcmp(saved_b,b,sizeof(b))==0&&memcmp(saved_x,x,sizeof(x))==0;}
