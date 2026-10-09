/* BOOTSTRAP-TOOL: Embench diagnostic C copy with observation only.
 * Copyright 2014-2019 Embecosm Limited and University of Bristol.
 * Derived from Scott Robert Ladd, contributors James Pallister/Jeremy Bennett.
 * SPDX-License-Identifier: GPL-3.0-or-later */
#include <stdint.h>
#include <limits.h>
#define GLOBAL_SCALE_FACTOR 1
#include "../upstream/src/huffbench/libhuffbench.c"
#include "../upstream/support/beebsc.c"
static int64_t observation[3309];
void
compdecomp_observe (byte * data, size_t data_len)
{
  size_t i, j, n, mask;
  bits32 k, t;
  byte c;
  byte *cptr;
  byte *dptr = data;

  /*
     COMPRESSION
   */

  // allocate data space
  byte *comp = (byte *) malloc_beebs (data_len + 1);

  size_t freq[512];		// allocate frequency table
  size_t heap[256];		// allocate heap
  int link[512];		// allocate link array
  bits32 code[256];		// huffman codes
  byte clen[256];		// bit lengths of codes

  memset (comp, 0, sizeof (byte) * (data_len + 1));
  memset (freq, 0, sizeof (size_t) * 512);
  memset (heap, 0, sizeof (size_t) * 256);
  memset (link, 0, sizeof (int) * 512);
  memset (code, 0, sizeof (bits32) * 256);
  memset (clen, 0, sizeof (byte) * 256);

  // count frequencies
  for (i = 0; i < data_len; ++i)
    {
      ++freq[(size_t) (*dptr)];
      ++dptr;
    }

  // create indirect heap based on frequencies
  n = 0;

  for (i = 0; i < 256; ++i)
    {
      if (freq[i])
	{
	  heap[n] = i;
	  ++n;
	}
    }

  for (i = n; i > 0; --i)
    heap_adjust (freq, heap, n, i);

  // generate a trie from heap
  size_t temp;
  size_t observed_distinct = n;

  // at this point, n contains the number of characters
  // that occur in the data array
  while (n > 1)
    {
      // take first item from top of heap
      --n;
      temp = heap[0];
      heap[0] = heap[n];

      // adjust the heap to maintain properties
      heap_adjust (freq, heap, n, 1);

      // in upper half of freq array, store sums of
      // the two smallest frequencies from the heap
      freq[256 + n] = freq[heap[0]] + freq[temp];
      link[temp] = 256 + n;	// parent
      link[heap[0]] = -256 - n;	// left child
      heap[0] = 256 + n;	// right child

      // adjust the heap again
      heap_adjust (freq, heap, n, 1);
    }

  link[256 + n] = 0;

  // generate codes
  size_t m, x, maxx = 0, maxi = 0;
  int l;

  for (m = 0; m < 256; ++m)
    {
      if (!freq[m])		// character does not occur
	{
	  code[m] = 0;
	  clen[m] = 0;
	}
      else
	{
	  i = 0;		// length of current code
	  j = 1;		// bit being set in code
	  x = 0;		// code being built
	  l = link[m];		// link in trie

	  while (l)		// while not at end of trie
	    {
	      if (l < 0)	// left link (negative)
		{
		  x += j;	// insert 1 into code
		  l = -l;	// reverse sign
		}

	      l = link[l];	// move to next link
	      j <<= 1;		// next bit to be set
	      ++i;		// increment code length
	    }

	  code[m] = (unsigned long) x;	// save code
	  clen[m] = (unsigned char) i;	// save code len

	  // keep track of biggest key
	  if (x > maxx)
	    maxx = x;

	  // keep track of longest key
	  if (i > maxi)
	    maxi = i;
	}
    }

  // make sure longest codes fit in unsigned long-bits
  if (maxi > (sizeof (unsigned long) * 8))
    {
      return;
    }

  // encode data
  size_t comp_len = 0;		// number of data_len output
  char bout = 0;		// byte of encoded data
  int bit = -1;			// count of bits stored in bout
  dptr = data;

  // watch for one-value file!
  if (maxx == 0)
    {
      return;
    }

  for (j = 0; j < data_len; ++j)
    {
      // start copying at first bit of code
      mask = 1 << (clen[(*dptr)] - 1);

      // copy code bits
      for (i = 0; i < clen[(*dptr)]; ++i)
	{
	  if (bit == 7)
	    {
	      // store full output byte
	      comp[comp_len] = bout;
	      ++comp_len;

	      // check for output longer than input!
	      if (comp_len == data_len)
		{
		  return;
		}

	      bit = 0;
	      bout = 0;
	    }
	  else
	    {
	      // move to next bit
	      ++bit;
	      bout <<= 1;
	    }

	  if (code[(*dptr)] & mask)
	    bout |= 1;

	  mask >>= 1;
	}

      ++dptr;
    }

  // output any incomplete data_len and bits
  bout <<= (7 - bit);
  comp[comp_len] = bout;
  ++comp_len;

  // printf("data len = %u\n",data_len);
  // printf("comp len = %u\n",comp_len);

  /*
     DECOMPRESSION
   */

  // allocate heap2
  bits32 heap2[256];

  // allocate output character buffer
  char outc[256];

  // initialize work areas
  memset (heap2, 0, 256 * sizeof (bits32));

  // create decode table as trie heap2
  char *optr = outc;

  for (j = 0; j < 256; ++j)
    {
      (*optr) = (char) j;
      ++optr;

      // if code exists for this byte
      if (code[j] | clen[j])
	{
	  // begin at first code bit
	  k = 0;
	  mask = 1 << (clen[j] - 1);

	  // find proper node, using bits in
	  // code as path.
	  for (i = 0; i < clen[j]; ++i)
	    {
	      k = k * 2 + 1;	// right link

	      if (code[j] & mask)
		++k;		// go left

	      mask >>= 1;	// next bit
	    }

	  heap2[j] = k;		// store link in heap2
	}
    }

  // sort outc based on heap2
  for (i = 1; i < 256; ++i)
    {
      t = heap2[i];
      c = outc[i];
      j = i;

      while ((j) && (heap2[j - 1] > t))
	{
	  heap2[j] = heap2[j - 1];
	  outc[j] = outc[j - 1];
	  --j;
	}

      heap2[j] = t;
      outc[j] = c;
    }

  // find first character in table
  for (j = 0; heap2[j] == 0; ++j);

  // decode data
  k = 0;			// link in trie
  i = j;
  mask = 0x80;
  n = 0;
  cptr = comp;
  dptr = data;

  while (n < data_len)
    {
      k = k * 2 + 1;		// right link

      if ((*cptr) & mask)
	++k;			// left link if bit on

      // search heap2 until link >= k
      while (heap2[i] < k)
	++i;

      // code matches, character found
      if (k == heap2[i])
	{
	  (*dptr) = outc[i];
	  ++dptr;
	  ++n;
	  k = 0;
	  i = j;
	}

      // move to next bit
      if (mask > 1)
	mask >>= 1;
      else			// code extends into next byte
	{
	  mask = 0x80;
	  ++cptr;
	}
    }

  // remove work areas
  for(size_t z=0;z<500;z++) observation[z]=data[z];
  for(size_t z=0;z<501;z++) observation[500+z]=comp[z];
  for(size_t z=0;z<512;z++){observation[1001+z]=(int64_t)freq[z];observation[1769+z]=link[z];}
  for(size_t z=0;z<256;z++){observation[1513+z]=(int64_t)heap[z];observation[2281+z]=(int64_t)code[z];observation[2537+z]=clen[z];observation[2793+z]=(int64_t)heap2[z];observation[3049+z]=(unsigned char)outc[z];}
  observation[3305]=comp_len;observation[3306]=observed_distinct;observation[3307]=maxx;observation[3308]=maxi;
  free_beebs (comp);
}
static void observe(void){init_heap_beebs((void*)heap,HEAP_SIZE);memcpy(test_data,orig_data,TEST_SIZE);memset(observation,0,sizeof observation);compdecomp_observe(test_data,TEST_SIZE);}
#define EXTRA int64_t x1,int64_t x2,int64_t x3,int64_t x4,int64_t x5,int64_t x6,int64_t ctx
int64_t state_cell(int64_t i,EXTRA){observe();return observation[i];}
int64_t oracle_selfcheck(int64_t n,EXTRA){observe();benchmark_body(1,1);if(!verify_benchmark(0))return 0;for(int i=0;i<500;i++)if(test_data[i]!=observation[i])return 0;for(int i=0;i<501;i++)if((unsigned char)heap[i]!=observation[500+i])return 0;return 1;}
int64_t batch(int64_t n,EXTRA){if(n<1||n>UINT_MAX)return 0;return verify_benchmark(benchmark_body(1,(unsigned)n));}
