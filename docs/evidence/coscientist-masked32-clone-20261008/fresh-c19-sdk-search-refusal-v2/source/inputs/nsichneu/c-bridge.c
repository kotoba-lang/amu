/* BOOTSTRAP-TOOL: pinned NSichneu diagnostic C copy.
 * Copyright 1998/1999 C-LAB Paderborn, 2014-2019 Embecosm/University of Bristol.
 * SPDX-License-Identifier: GPL-3.0-or-later */
#include <stdint.h>
#include <limits.h>
#define GLOBAL_SCALE_FACTOR 1
#include "../upstream/src/nsichneu/libnsichneu.c"
static int64_t observation[127*17];
static unsigned stage;
static void snapshot(unsigned n){
 observation[n*17]=P1_is_marked;observation[n*17+1]=P2_is_marked;observation[n*17+2]=P3_is_marked;
 for(int i=0;i<3;i++)observation[n*17+3+i]=P1_marking_member_0[i];
 for(int i=0;i<5;i++)observation[n*17+6+i]=P2_marking_member_0[i];
 for(int i=0;i<6;i++)observation[n*17+11+i]=P3_marking_member_0[i];
}
static int64_t seed_value(int test,int i){
 if(test==0)return 0;
 if(test==1)return i==3?-2:i<6?1:i==6?-3:2;
 if(test==2)return i==4?-2:i<6?1:i==7?-3:2;
 if(test==3)return i<6?i-4:(i%3)-1;
 if(test==4)return -7;
 if(test==5)return 5+(i*7)%3;
 if(i<6)return 0;if(i>=11)return 9;
 if(test==6)return i==6?-3:i==9?3:2;
 return i==6?7:i==7?-3:2;
}
static void prepare(int test){
 for(int i=0;i<3;i++)P1_marking_member_0[i]=seed_value(test,i+3);
 for(int i=0;i<5;i++)P2_marking_member_0[i]=seed_value(test,i+6);
 for(int i=0;i<6;i++)P3_marking_member_0[i]=seed_value(test,i+11);
}
static int __attribute__ ((noinline))
benchmark_observe(unsigned int lsf, unsigned int gsf)
{
  int j;

  for (unsigned int lsf_cnt = 0; lsf_cnt < lsf; lsf_cnt++)
    for (unsigned int gsf_cnt = 0; gsf_cnt < gsf; gsf_cnt++)
      {
	P1_is_marked = 3;
	P2_is_marked = 5;
	P3_is_marked = 0;

	snapshot(stage++);
	/* Permutation for Place P1 : 0, 1, 2 */
	/* Transition T1 */
	if ((P1_is_marked >= 3) &&
	    (P3_is_marked + 3 <= 6) &&
	    (P1_marking_member_0[1] == P1_marking_member_0[2]))
	  {

	    long x;
	    long y;
	    long z;

	    x = P1_marking_member_0[0];
	    y = P1_marking_member_0[1];

	    /* Transition condition */
	    if (x < y)
	      {

		/* demarking of input places */
		P1_is_marked -= 3;

		/* preaction */
		z = x - y;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = x;
		P3_marking_member_0[P3_is_marked + 1] = y;
		P3_marking_member_0[P3_is_marked + 2] = z;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }

	snapshot(stage++);
	/* Permutation for Place P1 : 0, 2, 1 */
	/* Transition T1 */
	if ((P1_is_marked >= 3) &&
	    (P3_is_marked + 3 <= 6) &&
	    (P1_marking_member_0[2] == P1_marking_member_0[1]))
	  {

	    long x;
	    long y;
	    long z;

	    x = P1_marking_member_0[0];
	    y = P1_marking_member_0[2];

	    /* Transition condition */
	    if ((x < y))
	      {


		/* demarking of input places */
		P1_is_marked -= 3;

		/* preaction */
		z = x - y;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = x;
		P3_marking_member_0[P3_is_marked + 1] = y;
		P3_marking_member_0[P3_is_marked + 2] = z;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }

	snapshot(stage++);
	/* Permutation for Place P1 : 1, 0, 2 */
	/* Transition T1 */
	if ((P1_is_marked >= 3) &&
	    (P3_is_marked + 3 <= 6) &&
	    (P1_marking_member_0[0] == P1_marking_member_0[2]))
	  {

	    long x;
	    long y;
	    long z;

	    x = P1_marking_member_0[1];
	    y = P1_marking_member_0[0];

	    /* Transition condition */
	    if (x < y)
	      {


		/* demarking of input places */
		P1_is_marked -= 3;

		/* preaction */
		z = x - y;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = x;
		P3_marking_member_0[P3_is_marked + 1] = y;
		P3_marking_member_0[P3_is_marked + 2] = z;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }

	snapshot(stage++);
	/* Permutation for Place P1 : 1, 2, 0 */
	/* Transition T1 */
	if ((P1_is_marked >= 3) &&
	    (P3_is_marked + 3 <= 6) &&
	    (P1_marking_member_0[2] == P1_marking_member_0[0]))
	  {

	    long x;
	    long y;
	    long z;

	    x = P1_marking_member_0[1];
	    y = P1_marking_member_0[2];

	    /* Transition condition */
	    if ((x < y))
	      {


		/* demarking of input places */
		P1_is_marked -= 3;

		/* preaction */
		z = x - y;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = x;
		P3_marking_member_0[P3_is_marked + 1] = y;
		P3_marking_member_0[P3_is_marked + 2] = z;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }

	snapshot(stage++);
	/* Permutation for Place P1 : 2, 0, 1 */
	/* Transition T1 */
	if ((P1_is_marked >= 3) &&
	    (P3_is_marked + 3 <= 6) &&
	    (P1_marking_member_0[0] == P1_marking_member_0[1]))
	  {
	    long x;
	    long y;
	    long z;

	    x = P1_marking_member_0[2];
	    y = P1_marking_member_0[0];

	    /* Transition condition */
	    if ((x < y))
	      {

		/* demarking of input places */
		P1_is_marked -= 3;

		/* preaction */
		z = x - y;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = x;
		P3_marking_member_0[P3_is_marked + 1] = y;
		P3_marking_member_0[P3_is_marked + 2] = z;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }

	snapshot(stage++);
	/* Permutation for Place P1 : 2, 1, 0 */
	/* Transition T1 */
	if ((P1_is_marked >= 3) &&
	    (P3_is_marked + 3 <= 6) &&
	    (P1_marking_member_0[1] == P1_marking_member_0[0]))
	  {
	    long x;
	    long y;
	    long z;

	    x = P1_marking_member_0[2];
	    y = P1_marking_member_0[1];

	    /* Transition condition */
	    if ((x < y))
	      {

		/* demarking of input places */
		P1_is_marked -= 3;

		/* preaction */
		z = x - y;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = x;
		P3_marking_member_0[P3_is_marked + 1] = y;
		P3_marking_member_0[P3_is_marked + 2] = z;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }

	snapshot(stage++);
	/* Permutation for Place P2 : 0, 1, 2, 3 */
	/* Transition T2 */
	if ((P2_is_marked >= 4) &&
	    (((P3_is_marked + 3) <= 6)) &&
	    (((P2_marking_member_0[1] == P2_marking_member_0[2])) &&
	     ((P2_marking_member_0[1] == P2_marking_member_0[3]))))
	  {
	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[0];
	    b = P2_marking_member_0[1];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }

	snapshot(stage++);
	/* Permutation for Place P2 : 0, 1, 3, 2 */
	/* Transition T2 */
	if ((P2_is_marked >= 4) &&
	    (((P3_is_marked + 3) <= 6)) &&
	    ((P2_marking_member_0[1] == P2_marking_member_0[3]) &&
	     (P2_marking_member_0[1] == P2_marking_member_0[2])))
	  {
	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[0];
	    b = P2_marking_member_0[1];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }

	snapshot(stage++);
	/* Permutation for Place P2 : 0, 2, 1, 3 */
	/* Transition T2 */
	if ((P2_is_marked >= 4) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[2] == P2_marking_member_0[1]) &&
	     (P2_marking_member_0[2] == P2_marking_member_0[3])))
	  {
	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[0];
	    b = P2_marking_member_0[2];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }

	snapshot(stage++);
	/* Permutation for Place P2 : 0, 2, 3, 1 */
	/* Transition T2 */
	if ((P2_is_marked >= 4) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[2] == P2_marking_member_0[3]) &&
	     (P2_marking_member_0[2] == P2_marking_member_0[1])))
	  {
	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[0];
	    b = P2_marking_member_0[2];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }

	snapshot(stage++);
	/* Permutation for Place P2 : 0, 3, 1, 2 */
	/* Transition T2 */
	if ((P2_is_marked >= 4) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[3] == P2_marking_member_0[1]) &&
	     (P2_marking_member_0[3] == P2_marking_member_0[2])))
	  {
	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[0];
	    b = P2_marking_member_0[3];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }

	snapshot(stage++);
	/* Permutation for Place P2 : 0, 3, 2, 1 */
	/* Transition T2 */
	if ((P2_is_marked >= 4) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[3] == P2_marking_member_0[2]) &&
	     (P2_marking_member_0[3] == P2_marking_member_0[1])))
	  {
	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[0];
	    b = P2_marking_member_0[3];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }

	snapshot(stage++);
	/* Permutation for Place P2 : 1, 0, 2, 3 */
	/* Transition T2 */
	if ((P2_is_marked >= 4) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[0] == P2_marking_member_0[2]) &&
	     (P2_marking_member_0[0] == P2_marking_member_0[3])))
	  {
	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[1];
	    b = P2_marking_member_0[0];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }

	snapshot(stage++);
	/* Permutation for Place P2 : 1, 0, 3, 2 */
	/* Transition T2 */
	if ((P2_is_marked >= 4) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[0] == P2_marking_member_0[3]) &&
	     (P2_marking_member_0[0] == P2_marking_member_0[2])))
	  {
	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[1];
	    b = P2_marking_member_0[0];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }

	snapshot(stage++);
	/* Permutation for Place P2 : 1, 2, 0, 3 */
	/* Transition T2 */
	if ((P2_is_marked >= 4) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[2] == P2_marking_member_0[0]) &&
	     (P2_marking_member_0[2] == P2_marking_member_0[3])))
	  {
	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[1];
	    b = P2_marking_member_0[2];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }

	snapshot(stage++);
	/* Permutation for Place P2 : 1, 2, 3, 0 */
	/* Transition T2 */
	if ((P2_is_marked >= 4) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[2] == P2_marking_member_0[3]) &&
	     (P2_marking_member_0[2] == P2_marking_member_0[0])))
	  {
	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[1];
	    b = P2_marking_member_0[2];

	    /* Transition condition */
	    if ((b > a))
	      {
		/* demarking of input places */
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }

	snapshot(stage++);
	/* Permutation for Place P2 : 1, 3, 0, 2 */
	/* Transition T2 */
	if ((P2_is_marked >= 4) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[3] == P2_marking_member_0[0]) &&
	     (P2_marking_member_0[3] == P2_marking_member_0[2])))
	  {
	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[1];
	    b = P2_marking_member_0[3];

	    /* Transition condition */
	    if ((b > a))
	      {
		/* demarking of input places */
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 1, 3, 2, 0 */
	/* Transition T2 */
	if ((P2_is_marked >= 4) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[3] == P2_marking_member_0[2]) &&
	     (P2_marking_member_0[3] == P2_marking_member_0[0])))
	  {
	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[1];
	    b = P2_marking_member_0[3];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 2, 0, 1, 3 */
	/* Transition T2 */
	if ((P2_is_marked >= 4) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[0] == P2_marking_member_0[1]) &&
	     (P2_marking_member_0[0] == P2_marking_member_0[3])))
	  {
	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[2];
	    b = P2_marking_member_0[0];

	    /* Transition condition */
	    if ((b > a))
	      {
		/* demarking of input places */
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }

	snapshot(stage++);
	/* Permutation for Place P2 : 2, 0, 3, 1 */
	/* Transition T2 */
	if ((P2_is_marked >= 4) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[0] == P2_marking_member_0[3]) &&
	     (P2_marking_member_0[0] == P2_marking_member_0[1])))
	  {
	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[2];
	    b = P2_marking_member_0[0];

	    /* Transition condition */
	    if ((b > a))
	      {
		/* demarking of input places */
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }

	snapshot(stage++);
	/* Permutation for Place P2 : 2, 1, 0, 3 */
	/* Transition T2 */
	if ((P2_is_marked >= 4) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[1] == P2_marking_member_0[0]) &&
	     (P2_marking_member_0[1] == P2_marking_member_0[3])))
	  {
	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[2];
	    b = P2_marking_member_0[1];

	    /* Transition condition */
	    if ((b > a))
	      {
		/* demarking of input places */
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }

	snapshot(stage++);
	/* Permutation for Place P2 : 2, 1, 3, 0 */
	/* Transition T2 */
	if ((P2_is_marked >= 4) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[1] == P2_marking_member_0[3]) &&
	     (P2_marking_member_0[1] == P2_marking_member_0[0])))
	  {
	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[2];
	    b = P2_marking_member_0[1];

	    /* Transition condition */
	    if ((b > a))
	      {
		/* demarking of input places */
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }

	snapshot(stage++);
	/* Permutation for Place P2 : 2, 3, 0, 1 */
	/* Transition T2 */
	if ((P2_is_marked >= 4) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[3] == P2_marking_member_0[0]) &&
	     (P2_marking_member_0[3] == P2_marking_member_0[1])))
	  {
	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[2];
	    b = P2_marking_member_0[3];

	    /* Transition condition */
	    if ((b > a))
	      {
		/* demarking of input places */
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }

	snapshot(stage++);
	/* Permutation for Place P2 : 2, 3, 1, 0 */
	/* Transition T2 */
	if ((P2_is_marked >= 4) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[3] == P2_marking_member_0[1]) &&
	     (P2_marking_member_0[3] == P2_marking_member_0[0])))
	  {
	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[2];
	    b = P2_marking_member_0[3];

	    /* Transition condition */
	    if ((b > a))
	      {
		/* demarking of input places */
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }

	snapshot(stage++);
	/* Permutation for Place P2 : 3, 0, 1, 2 */
	/* Transition T2 */
	if ((P2_is_marked >= 4) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[0] == P2_marking_member_0[1]) &&
	     (P2_marking_member_0[0] == P2_marking_member_0[2])))
	  {
	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[3];
	    b = P2_marking_member_0[0];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 3, 0, 2, 1 */
	/* Transition T2 */
	if ((P2_is_marked >= 4) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[0] == P2_marking_member_0[2]) &&
	     (P2_marking_member_0[0] == P2_marking_member_0[1])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[3];
	    b = P2_marking_member_0[0];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 3, 1, 0, 2 */
	/* Transition T2 */
	if ((P2_is_marked >= 4) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[1] == P2_marking_member_0[0]) &&
	     (P2_marking_member_0[1] == P2_marking_member_0[2])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[3];
	    b = P2_marking_member_0[1];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 3, 1, 2, 0 */
	/* Transition T2 */
	if ((P2_is_marked >= 4) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[1] == P2_marking_member_0[2]) &&
	     (P2_marking_member_0[1] == P2_marking_member_0[0])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[3];
	    b = P2_marking_member_0[1];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 3, 2, 0, 1 */
	/* Transition T2 */
	if ((P2_is_marked >= 4) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[2] == P2_marking_member_0[0]) &&
	     (P2_marking_member_0[2] == P2_marking_member_0[1])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[3];
	    b = P2_marking_member_0[2];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 3, 2, 1, 0 */
	/* Transition T2 */
	if ((P2_is_marked >= 4) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[2] == P2_marking_member_0[1]) &&
	     (P2_marking_member_0[2] == P2_marking_member_0[0])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[3];
	    b = P2_marking_member_0[2];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 0, 1, 2, 4 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[1] == P2_marking_member_0[2]) &&
	     (P2_marking_member_0[1] == P2_marking_member_0[4])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[0];
	    b = P2_marking_member_0[1];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[3];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 0, 1, 3, 4 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[1] == P2_marking_member_0[3]) &&
	     (P2_marking_member_0[1] == P2_marking_member_0[4])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[0];
	    b = P2_marking_member_0[1];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[2];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 0, 1, 4, 2 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[1] == P2_marking_member_0[4]) &&
	     (P2_marking_member_0[1] == P2_marking_member_0[2])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[0];
	    b = P2_marking_member_0[1];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[3];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 0, 1, 4, 3 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[1] == P2_marking_member_0[4]) &&
	     (P2_marking_member_0[1] == P2_marking_member_0[3])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[0];
	    b = P2_marking_member_0[1];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[2];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 0, 2, 1, 4 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[2] == P2_marking_member_0[1]) &&
	     (P2_marking_member_0[2] == P2_marking_member_0[4])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[0];
	    b = P2_marking_member_0[2];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[3];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 0, 2, 3, 4 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[2] == P2_marking_member_0[3]) &&
	     (P2_marking_member_0[2] == P2_marking_member_0[4])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[0];
	    b = P2_marking_member_0[2];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[1];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 0, 2, 4, 1 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[2] == P2_marking_member_0[4]) &&
	     (P2_marking_member_0[2] == P2_marking_member_0[1])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[0];
	    b = P2_marking_member_0[2];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[3];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 0, 2, 4, 3 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[2] == P2_marking_member_0[4]) &&
	     (P2_marking_member_0[2] == P2_marking_member_0[3])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[0];
	    b = P2_marking_member_0[2];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[1];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 0, 3, 1, 4 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[3] == P2_marking_member_0[1]) &&
	     (P2_marking_member_0[3] == P2_marking_member_0[4])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[0];
	    b = P2_marking_member_0[3];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[2];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 0, 3, 2, 4 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[3] == P2_marking_member_0[2]) &&
	     (P2_marking_member_0[3] == P2_marking_member_0[4])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[0];
	    b = P2_marking_member_0[3];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[1];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 0, 3, 4, 1 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[3] == P2_marking_member_0[4]) &&
	     (P2_marking_member_0[3] == P2_marking_member_0[1])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[0];
	    b = P2_marking_member_0[3];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[2];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 0, 3, 4, 2 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[3] == P2_marking_member_0[4]) &&
	     (P2_marking_member_0[3] == P2_marking_member_0[2])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[0];
	    b = P2_marking_member_0[3];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[1];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 0, 4, 1, 2 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[4] == P2_marking_member_0[1]) &&
	     (P2_marking_member_0[4] == P2_marking_member_0[2])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[0];
	    b = P2_marking_member_0[4];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[3];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 0, 4, 1, 3 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[4] == P2_marking_member_0[1]) &&
	     (P2_marking_member_0[4] == P2_marking_member_0[3])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[0];
	    b = P2_marking_member_0[4];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[2];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 0, 4, 2, 1 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[4] == P2_marking_member_0[2]) &&
	     (P2_marking_member_0[4] == P2_marking_member_0[1])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[0];
	    b = P2_marking_member_0[4];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[3];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 0, 4, 2, 3 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[4] == P2_marking_member_0[2]) &&
	     (P2_marking_member_0[4] == P2_marking_member_0[3])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[0];
	    b = P2_marking_member_0[4];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[1];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 0, 4, 3, 1 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[4] == P2_marking_member_0[3]) &&
	     (P2_marking_member_0[4] == P2_marking_member_0[1])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[0];
	    b = P2_marking_member_0[4];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[2];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 0, 4, 3, 2 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[4] == P2_marking_member_0[3]) &&
	     (P2_marking_member_0[4] == P2_marking_member_0[2])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[0];
	    b = P2_marking_member_0[4];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[1];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 1, 0, 2, 4 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[0] == P2_marking_member_0[2]) &&
	     (P2_marking_member_0[0] == P2_marking_member_0[4])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[1];
	    b = P2_marking_member_0[0];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[3];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 1, 0, 3, 4 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[0] == P2_marking_member_0[3]) &&
	     (P2_marking_member_0[0] == P2_marking_member_0[4])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[1];
	    b = P2_marking_member_0[0];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[2];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 1, 0, 4, 2 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[0] == P2_marking_member_0[4]) &&
	     (P2_marking_member_0[0] == P2_marking_member_0[2])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[1];
	    b = P2_marking_member_0[0];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[3];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 1, 0, 4, 3 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[0] == P2_marking_member_0[4]) &&
	     (P2_marking_member_0[0] == P2_marking_member_0[3])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[1];
	    b = P2_marking_member_0[0];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[2];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 1, 2, 0, 4 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[2] == P2_marking_member_0[0]) &&
	     (P2_marking_member_0[2] == P2_marking_member_0[4])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[1];
	    b = P2_marking_member_0[2];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[3];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 1, 2, 3, 4 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[2] == P2_marking_member_0[3]) &&
	     (P2_marking_member_0[2] == P2_marking_member_0[4])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[1];
	    b = P2_marking_member_0[2];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 1, 2, 4, 0 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[2] == P2_marking_member_0[4]) &&
	     (P2_marking_member_0[2] == P2_marking_member_0[0])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[1];
	    b = P2_marking_member_0[2];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[3];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 1, 2, 4, 3 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[2] == P2_marking_member_0[4]) &&
	     (P2_marking_member_0[2] == P2_marking_member_0[3])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[1];
	    b = P2_marking_member_0[2];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 1, 3, 0, 4 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[3] == P2_marking_member_0[0]) &&
	     (P2_marking_member_0[3] == P2_marking_member_0[4])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[1];
	    b = P2_marking_member_0[3];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[2];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 1, 3, 2, 4 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[3] == P2_marking_member_0[2]) &&
	     (P2_marking_member_0[3] == P2_marking_member_0[4])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[1];
	    b = P2_marking_member_0[3];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 1, 3, 4, 0 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[3] == P2_marking_member_0[4]) &&
	     (P2_marking_member_0[3] == P2_marking_member_0[0])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[1];
	    b = P2_marking_member_0[3];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[2];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 1, 3, 4, 2 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[3] == P2_marking_member_0[4]) &&
	     (P2_marking_member_0[3] == P2_marking_member_0[2])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[1];
	    b = P2_marking_member_0[3];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 1, 4, 0, 2 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[4] == P2_marking_member_0[0]) &&
	     (P2_marking_member_0[4] == P2_marking_member_0[2])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[1];
	    b = P2_marking_member_0[4];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[3];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 1, 4, 0, 3 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[4] == P2_marking_member_0[0]) &&
	     (P2_marking_member_0[4] == P2_marking_member_0[3])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[1];
	    b = P2_marking_member_0[4];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[2];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 1, 4, 2, 0 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[4] == P2_marking_member_0[2]) &&
	     (P2_marking_member_0[4] == P2_marking_member_0[0])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[1];
	    b = P2_marking_member_0[4];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[3];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 1, 4, 2, 3 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[4] == P2_marking_member_0[2]) &&
	     (P2_marking_member_0[4] == P2_marking_member_0[3])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[1];
	    b = P2_marking_member_0[4];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 1, 4, 3, 0 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[4] == P2_marking_member_0[3]) &&
	     (P2_marking_member_0[4] == P2_marking_member_0[0])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[1];
	    b = P2_marking_member_0[4];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[2];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 1, 4, 3, 2 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[4] == P2_marking_member_0[3]) &&
	     (P2_marking_member_0[4] == P2_marking_member_0[2])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[1];
	    b = P2_marking_member_0[4];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 2, 0, 1, 4 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[0] == P2_marking_member_0[1]) &&
	     (P2_marking_member_0[0] == P2_marking_member_0[4])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[2];
	    b = P2_marking_member_0[0];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[3];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 2, 0, 3, 4 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[0] == P2_marking_member_0[3]) &&
	     (P2_marking_member_0[0] == P2_marking_member_0[4])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[2];
	    b = P2_marking_member_0[0];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[1];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 2, 0, 4, 1 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[0] == P2_marking_member_0[4]) &&
	     (P2_marking_member_0[0] == P2_marking_member_0[1])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[2];
	    b = P2_marking_member_0[0];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[3];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 2, 0, 4, 3 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[0] == P2_marking_member_0[4]) &&
	     (P2_marking_member_0[0] == P2_marking_member_0[3])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[2];
	    b = P2_marking_member_0[0];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[1];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 2, 1, 0, 4 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[1] == P2_marking_member_0[0]) &&
	     (P2_marking_member_0[1] == P2_marking_member_0[4])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[2];
	    b = P2_marking_member_0[1];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[3];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 2, 1, 3, 4 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[1] == P2_marking_member_0[3]) &&
	     (P2_marking_member_0[1] == P2_marking_member_0[4])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[2];
	    b = P2_marking_member_0[1];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 2, 1, 4, 0 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[1] == P2_marking_member_0[4]) &&
	     (P2_marking_member_0[1] == P2_marking_member_0[0])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[2];
	    b = P2_marking_member_0[1];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[3];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 2, 1, 4, 3 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[1] == P2_marking_member_0[4]) &&
	     (P2_marking_member_0[1] == P2_marking_member_0[3])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[2];
	    b = P2_marking_member_0[1];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 2, 3, 0, 4 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[3] == P2_marking_member_0[0]) &&
	     (P2_marking_member_0[3] == P2_marking_member_0[4])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[2];
	    b = P2_marking_member_0[3];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[1];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 2, 3, 1, 4 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[3] == P2_marking_member_0[1]) &&
	     (P2_marking_member_0[3] == P2_marking_member_0[4])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[2];
	    b = P2_marking_member_0[3];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 2, 3, 4, 0 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[3] == P2_marking_member_0[4]) &&
	     (P2_marking_member_0[3] == P2_marking_member_0[0])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[2];
	    b = P2_marking_member_0[3];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[1];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 2, 3, 4, 1 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[3] == P2_marking_member_0[4]) &&
	     (P2_marking_member_0[3] == P2_marking_member_0[1])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[2];
	    b = P2_marking_member_0[3];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 2, 4, 0, 1 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[4] == P2_marking_member_0[0]) &&
	     (P2_marking_member_0[4] == P2_marking_member_0[1])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[2];
	    b = P2_marking_member_0[4];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[3];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 2, 4, 0, 3 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[4] == P2_marking_member_0[0]) &&
	     (P2_marking_member_0[4] == P2_marking_member_0[3])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[2];
	    b = P2_marking_member_0[4];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[1];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 2, 4, 1, 0 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[4] == P2_marking_member_0[1]) &&
	     (P2_marking_member_0[4] == P2_marking_member_0[0])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[2];
	    b = P2_marking_member_0[4];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[3];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 2, 4, 1, 3 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[4] == P2_marking_member_0[1]) &&
	     (P2_marking_member_0[4] == P2_marking_member_0[3])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[2];
	    b = P2_marking_member_0[4];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 2, 4, 3, 0 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[4] == P2_marking_member_0[3]) &&
	     (P2_marking_member_0[4] == P2_marking_member_0[0])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[2];
	    b = P2_marking_member_0[4];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[1];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 2, 4, 3, 1 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[4] == P2_marking_member_0[3]) &&
	     (P2_marking_member_0[4] == P2_marking_member_0[1])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[2];
	    b = P2_marking_member_0[4];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 3, 0, 1, 4 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[0] == P2_marking_member_0[1]) &&
	     (P2_marking_member_0[0] == P2_marking_member_0[4])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[3];
	    b = P2_marking_member_0[0];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[2];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 3, 0, 2, 4 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[0] == P2_marking_member_0[2]) &&
	     (P2_marking_member_0[0] == P2_marking_member_0[4])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[3];
	    b = P2_marking_member_0[0];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[1];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 3, 0, 4, 1 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[0] == P2_marking_member_0[4]) &&
	     (P2_marking_member_0[0] == P2_marking_member_0[1])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[3];
	    b = P2_marking_member_0[0];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[2];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 3, 0, 4, 2 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[0] == P2_marking_member_0[4]) &&
	     (P2_marking_member_0[0] == P2_marking_member_0[2])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[3];
	    b = P2_marking_member_0[0];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[1];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 3, 1, 0, 4 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[1] == P2_marking_member_0[0]) &&
	     (P2_marking_member_0[1] == P2_marking_member_0[4])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[3];
	    b = P2_marking_member_0[1];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[2];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 3, 1, 2, 4 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[1] == P2_marking_member_0[2]) &&
	     (P2_marking_member_0[1] == P2_marking_member_0[4])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[3];
	    b = P2_marking_member_0[1];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 3, 1, 4, 0 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[1] == P2_marking_member_0[4]) &&
	     (P2_marking_member_0[1] == P2_marking_member_0[0])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[3];
	    b = P2_marking_member_0[1];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[2];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 3, 1, 4, 2 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[1] == P2_marking_member_0[4]) &&
	     (P2_marking_member_0[1] == P2_marking_member_0[2])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[3];
	    b = P2_marking_member_0[1];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 3, 2, 0, 4 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[2] == P2_marking_member_0[0]) &&
	     (P2_marking_member_0[2] == P2_marking_member_0[4])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[3];
	    b = P2_marking_member_0[2];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[1];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 3, 2, 1, 4 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[2] == P2_marking_member_0[1]) &&
	     (P2_marking_member_0[2] == P2_marking_member_0[4])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[3];
	    b = P2_marking_member_0[2];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 3, 2, 4, 0 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[2] == P2_marking_member_0[4]) &&
	     (P2_marking_member_0[2] == P2_marking_member_0[0])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[3];
	    b = P2_marking_member_0[2];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[1];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 3, 2, 4, 1 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[2] == P2_marking_member_0[4]) &&
	     (P2_marking_member_0[2] == P2_marking_member_0[1])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[3];
	    b = P2_marking_member_0[2];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 3, 4, 0, 1 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[4] == P2_marking_member_0[0]) &&
	     (P2_marking_member_0[4] == P2_marking_member_0[1])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[3];
	    b = P2_marking_member_0[4];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[2];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 3, 4, 0, 2 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[4] == P2_marking_member_0[0]) &&
	     (P2_marking_member_0[4] == P2_marking_member_0[2])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[3];
	    b = P2_marking_member_0[4];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[1];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 3, 4, 1, 0 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[4] == P2_marking_member_0[1]) &&
	     (P2_marking_member_0[4] == P2_marking_member_0[0])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[3];
	    b = P2_marking_member_0[4];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[2];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 3, 4, 1, 2 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[4] == P2_marking_member_0[1]) &&
	     (P2_marking_member_0[4] == P2_marking_member_0[2])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[3];
	    b = P2_marking_member_0[4];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 3, 4, 2, 0 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[4] == P2_marking_member_0[2]) &&
	     (P2_marking_member_0[4] == P2_marking_member_0[0])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[3];
	    b = P2_marking_member_0[4];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[1];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 3, 4, 2, 1 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[4] == P2_marking_member_0[2]) &&
	     (P2_marking_member_0[4] == P2_marking_member_0[1])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[3];
	    b = P2_marking_member_0[4];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 4, 0, 1, 2 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[0] == P2_marking_member_0[1]) &&
	     (P2_marking_member_0[0] == P2_marking_member_0[2])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[4];
	    b = P2_marking_member_0[0];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[3];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 4, 0, 1, 3 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[0] == P2_marking_member_0[1]) &&
	     (P2_marking_member_0[0] == P2_marking_member_0[3])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[4];
	    b = P2_marking_member_0[0];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[2];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 4, 0, 2, 1 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[0] == P2_marking_member_0[2]) &&
	     (P2_marking_member_0[0] == P2_marking_member_0[1])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[4];
	    b = P2_marking_member_0[0];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[3];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 4, 0, 2, 3 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[0] == P2_marking_member_0[2]) &&
	     (P2_marking_member_0[0] == P2_marking_member_0[3])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[4];
	    b = P2_marking_member_0[0];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[1];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 4, 0, 3, 1 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[0] == P2_marking_member_0[3]) &&
	     (P2_marking_member_0[0] == P2_marking_member_0[1])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[4];
	    b = P2_marking_member_0[0];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[2];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 4, 0, 3, 2 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[0] == P2_marking_member_0[3]) &&
	     (P2_marking_member_0[0] == P2_marking_member_0[2])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[4];
	    b = P2_marking_member_0[0];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[1];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 4, 1, 0, 2 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[1] == P2_marking_member_0[0]) &&
	     (P2_marking_member_0[1] == P2_marking_member_0[2])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[4];
	    b = P2_marking_member_0[1];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[3];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 4, 1, 0, 3 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[1] == P2_marking_member_0[0]) &&
	     (P2_marking_member_0[1] == P2_marking_member_0[3])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[4];
	    b = P2_marking_member_0[1];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[2];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 4, 1, 2, 0 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[1] == P2_marking_member_0[2]) &&
	     (P2_marking_member_0[1] == P2_marking_member_0[0])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[4];
	    b = P2_marking_member_0[1];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[3];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 4, 1, 2, 3 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[1] == P2_marking_member_0[2]) &&
	     (P2_marking_member_0[1] == P2_marking_member_0[3])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[4];
	    b = P2_marking_member_0[1];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 4, 1, 3, 0 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[1] == P2_marking_member_0[3]) &&
	     (P2_marking_member_0[1] == P2_marking_member_0[0])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[4];
	    b = P2_marking_member_0[1];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[2];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 4, 1, 3, 2 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[1] == P2_marking_member_0[3]) &&
	     (P2_marking_member_0[1] == P2_marking_member_0[2])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[4];
	    b = P2_marking_member_0[1];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 4, 2, 0, 1 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[2] == P2_marking_member_0[0]) &&
	     (P2_marking_member_0[2] == P2_marking_member_0[1])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[4];
	    b = P2_marking_member_0[2];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[3];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 4, 2, 0, 3 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[2] == P2_marking_member_0[0]) &&
	     (P2_marking_member_0[2] == P2_marking_member_0[3])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[4];
	    b = P2_marking_member_0[2];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[1];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 4, 2, 1, 0 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[2] == P2_marking_member_0[1]) &&
	     (P2_marking_member_0[2] == P2_marking_member_0[0])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[4];
	    b = P2_marking_member_0[2];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[3];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 4, 2, 1, 3 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[2] == P2_marking_member_0[1]) &&
	     (P2_marking_member_0[2] == P2_marking_member_0[3])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[4];
	    b = P2_marking_member_0[2];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 4, 2, 3, 0 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[2] == P2_marking_member_0[3]) &&
	     (P2_marking_member_0[2] == P2_marking_member_0[0])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[4];
	    b = P2_marking_member_0[2];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[1];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 4, 2, 3, 1 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[2] == P2_marking_member_0[3]) &&
	     (P2_marking_member_0[2] == P2_marking_member_0[1])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[4];
	    b = P2_marking_member_0[2];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 4, 3, 0, 1 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[3] == P2_marking_member_0[0]) &&
	     (P2_marking_member_0[3] == P2_marking_member_0[1])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[4];
	    b = P2_marking_member_0[3];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[2];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 4, 3, 0, 2 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[3] == P2_marking_member_0[0]) &&
	     (P2_marking_member_0[3] == P2_marking_member_0[2])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[4];
	    b = P2_marking_member_0[3];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[1];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 4, 3, 1, 0 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[3] == P2_marking_member_0[1]) &&
	     (P2_marking_member_0[3] == P2_marking_member_0[0])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[4];
	    b = P2_marking_member_0[3];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[2];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 4, 3, 1, 2 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[3] == P2_marking_member_0[1]) &&
	     (P2_marking_member_0[3] == P2_marking_member_0[2])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[4];
	    b = P2_marking_member_0[3];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 4, 3, 2, 0 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[3] == P2_marking_member_0[2]) &&
	     (P2_marking_member_0[3] == P2_marking_member_0[0])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[4];
	    b = P2_marking_member_0[3];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_marking_member_0[0] = P2_marking_member_0[1];
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }


	snapshot(stage++);
	/* Permutation for Place P2 : 4, 3, 2, 1 */
	/* Transition T2 */
	if ((P2_is_marked >= 5) &&
	    ((P3_is_marked + 3) <= 6) &&
	    ((P2_marking_member_0[3] == P2_marking_member_0[2]) &&
	     (P2_marking_member_0[3] == P2_marking_member_0[1])))
	  {

	    long a;
	    long b;
	    long c;

	    a = P2_marking_member_0[4];
	    b = P2_marking_member_0[3];

	    /* Transition condition */
	    if ((b > a))
	      {

		/* demarking of input places */
		P2_is_marked -= 4;

		/* preaction */
		c = a + b;

		/* marking of output places */
		P3_marking_member_0[P3_is_marked + 0] = a;
		P3_marking_member_0[P3_is_marked + 1] = b;
		P3_marking_member_0[P3_is_marked + 2] = c;
		P3_is_marked += 3;

	      }			/* end of if (Transition condition) */
	  }
        snapshot(stage++);
      }

  return 0;
}
#define EXTRA int64_t x1,int64_t x2,int64_t x3,int64_t x4,int64_t x5,int64_t x6,int64_t ctx
int64_t stage_cell(int64_t encoded,EXTRA){
 int test=encoded/4096,code=encoded%4096,n=code/17,cell=code%17;
 if(encoded<0||test>7||n>126)return INT64_MIN;
 prepare(test);stage=0;benchmark_observe(1,1);return observation[n*17+cell];
}
int64_t oracle_selfcheck(int64_t test,EXTRA){
 if(test<0||test>7)return 0;
 prepare(test);stage=0;benchmark_observe(1,1);
 if(stage!=127)return 0;
 prepare(test);benchmark_body(1,1);snapshot(0);
 for(int i=0;i<17;i++)if(observation[i]!=observation[126*17+i])return 0;
 return 1;
}
int64_t batch(int64_t n,EXTRA){
 if(n<1||n>UINT_MAX)return 0;prepare(0);
 return verify_benchmark(benchmark_body(1,(unsigned)n));
}
