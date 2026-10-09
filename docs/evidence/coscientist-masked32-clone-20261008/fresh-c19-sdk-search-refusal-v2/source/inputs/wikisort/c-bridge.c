/* BOOTSTRAP-TOOL: full original WikiSort body + branch counters.
 * Copyright 2014-2019 Embecosm/Bristol and WikiSort contributors; GPL-3.0-or-later. */
#define GLOBAL_SCALE_FACTOR 1
#include "../upstream/support/beebsc.c"
#include "../upstream/src/wikisort/libwikisort.c"
static long counts[4],fallback;
static void observed_sort(Test array[],long size,Comparison compare){

  /* use a small cache to speed up some of the operations */
  /* since the cache size is fixed, it's still O(1) memory! */
  /* just keep in mind that making it too small ruins the point (nothing will fit into it), */
  /* and making it too large also ruins the point (so much for "low memory"!) */
  /* removing the cache entirely still gives 70% of the performance of a standard merge */

  /* also, if you change this to dynamically allocate a full-size buffer, */
  /* the algorithm seamlessly degenerates into a standard merge sort! */
#define CACHE_SIZE 512
  const long cache_size = CACHE_SIZE;
  Test cache[CACHE_SIZE];

  long index, merge_size, start, mid, end, fractional, decimal;
  long power_of_two, fractional_base, fractional_step, decimal_step;

  /* if there are 32 or fewer items, just insertion sort the entire array */
  if (size <= 32)
    {
      counts[0]++; InsertionSort (array, MakeRange (0, size), compare);
      return;
    }

  /* calculate how to scale the index value to the range within the array */
  /* (this is essentially fixed-point math, where we manually check for and handle overflow) */
  power_of_two = FloorPowerOfTwo (size);
  fractional_base = power_of_two / 16;
  fractional_step = size % fractional_base;
  decimal_step = size / fractional_base;

  /* first insertion sort everything the lowest level, which is 16-31 items at a time */
  decimal = 0;
  fractional = 0;
  while (decimal < size)
    {
      start = decimal;

      decimal += decimal_step;
      fractional += fractional_step;
      if (fractional >= fractional_base)
	{
	  fractional -= fractional_base;
	  decimal += 1;
	}

      end = decimal;

      counts[0]++; InsertionSort (array, MakeRange (start, end), compare);
    }

  /* then merge sort the higher levels, which can be 32-63, 64-127, 128-255, etc. */
  for (merge_size = 16; merge_size < power_of_two; merge_size += merge_size)
    {
      counts[1]++; long block_size = sqrt (decimal_step);
      long buffer_size = decimal_step / block_size + 1;

      /* as an optimization, we really only need to pull out an internal buffer once for each level of merges */
      /* after that we can reuse the same buffer over and over, then redistribute it when we're finished with this level */
      Range level1 = MakeRange (0, 0);
      Range level2 = MakeRange (0, 0);
      Range levelA = MakeRange (0, 0);
      Range levelB = MakeRange (0, 0);

      decimal = fractional = 0;
      while (decimal < size)
	{
	  start = decimal;

	  decimal += decimal_step;
	  fractional += fractional_step;
	  if (fractional >= fractional_base)
	    {
	      fractional -= fractional_base;
	      decimal += 1;
	    }

	  mid = decimal;

	  decimal += decimal_step;
	  fractional += fractional_step;
	  if (fractional >= fractional_base)
	    {
	      fractional -= fractional_base;
	      decimal += 1;
	    }

	  end = decimal;

	  if (compare (array[end - 1], array[start]))
	    {
	      /* the two ranges are in reverse order, so a simple rotation should fix it */
	      counts[2]++; Rotate (array, mid - start, MakeRange (start, end), cache,
		      cache_size);
	    }
	  else if (compare (array[mid], array[mid - 1]))
	    {
	      Range bufferA, bufferB, buffer1, buffer2, blockA, blockB,
		firstA, lastA, lastB;
	      long indexA, minA, findA;
	      Test min_value;

	      /* these two ranges weren't already in order, so we'll need to merge them! */
	      Range A = MakeRange (start, mid), B = MakeRange (mid, end);

	      /* try to fill up two buffers with unique values in ascending order */
	      if (Range_length (A) <= cache_size)
		{
		  counts[3]++; memcpy (&cache[0], &array[A.start],
			  Range_length (A) * sizeof (array[0]));
		  WikiMerge (array, MakeRange (0, 0), A, B, compare, cache,
			     cache_size);
		  continue;
		}

	      fallback++; if (Range_length (level1) > 0)
		{
		  /* reuse the buffers we found in a previous iteration */
		  bufferA = MakeRange (A.start, A.start);
		  bufferB = MakeRange (B.end, B.end);
		  buffer1 = level1;
		  buffer2 = level2;

		}
	      else
		{
		  long count, length;

		  /* the first item is always going to be the first unique value, so let's start searching at the next index */
		  count = 1;
		  for (buffer1.start = A.start + 1; buffer1.start < A.end;
		       buffer1.start++)
		    if (compare
			(array[buffer1.start - 1], array[buffer1.start])
			|| compare (array[buffer1.start],
				    array[buffer1.start - 1]))
		      if (++count == buffer_size)
			break;
		  buffer1.end = buffer1.start + count;

		  /* if the size of each block fits into the cache, we only need one buffer for tagging the A blocks */
		  /* this is because the other buffer is used as a swap space for merging the A blocks into the B values that follow it, */
		  /* but we can just use the cache as the buffer instead. this skips some memmoves and an insertion sort */
		  if (buffer_size <= cache_size)
		    {
		      buffer2 = MakeRange (A.start, A.start);

		      if (Range_length (buffer1) == buffer_size)
			{
			  /* we found enough values for the buffer in A */
			  bufferA =
			    MakeRange (buffer1.start,
				       buffer1.start + buffer_size);
			  bufferB = MakeRange (B.end, B.end);
			  buffer1 =
			    MakeRange (A.start, A.start + buffer_size);

			}
		      else
			{
			  /* we were unable to find enough unique values in A, so try B */
			  bufferA = MakeRange (buffer1.start, buffer1.start);
			  buffer1 = MakeRange (A.start, A.start);

			  /* the last value is guaranteed to be the first unique value we encounter, so we can start searching at the next index */
			  count = 1;
			  for (buffer1.start = B.end - 2;
			       buffer1.start >= B.start; buffer1.start--)
			    if (compare
				(array[buffer1.start],
				 array[buffer1.start + 1])
				|| compare (array[buffer1.start + 1],
					    array[buffer1.start]))
			      if (++count == buffer_size)
				break;
			  buffer1.end = buffer1.start + count;

			  if (Range_length (buffer1) == buffer_size)
			    {
			      bufferB =
				MakeRange (buffer1.start,
					   buffer1.start + buffer_size);
			      buffer1 =
				MakeRange (B.end - buffer_size, B.end);
			    }
			}
		    }
		  else
		    {
		      /* the first item of the second buffer isn't guaranteed to be the first unique value, so we need to find the first unique item too */
		      count = 0;
		      for (buffer2.start = buffer1.start + 1;
			   buffer2.start < A.end; buffer2.start++)
			if (compare
			    (array[buffer2.start - 1], array[buffer2.start])
			    || compare (array[buffer2.start],
					array[buffer2.start - 1]))
			  if (++count == buffer_size)
			    break;
		      buffer2.end = buffer2.start + count;

		      if (Range_length (buffer2) == buffer_size)
			{
			  /* we found enough values for both buffers in A */
			  bufferA =
			    MakeRange (buffer2.start,
				       buffer2.start + buffer_size * 2);
			  bufferB = MakeRange (B.end, B.end);
			  buffer1 =
			    MakeRange (A.start, A.start + buffer_size);
			  buffer2 =
			    MakeRange (A.start + buffer_size,
				       A.start + buffer_size * 2);

			}
		      else if (Range_length (buffer1) == buffer_size)
			{
			  /* we found enough values for one buffer in A, so we'll need to find one buffer in B */
			  bufferA =
			    MakeRange (buffer1.start,
				       buffer1.start + buffer_size);
			  buffer1 =
			    MakeRange (A.start, A.start + buffer_size);

			  /* like before, the last value is guaranteed to be the first unique value we encounter, so we can start searching at the next index */
			  count = 1;
			  for (buffer2.start = B.end - 2;
			       buffer2.start >= B.start; buffer2.start--)
			    if (compare
				(array[buffer2.start],
				 array[buffer2.start + 1])
				|| compare (array[buffer2.start + 1],
					    array[buffer2.start]))
			      if (++count == buffer_size)
				break;
			  buffer2.end = buffer2.start + count;

			  if (Range_length (buffer2) == buffer_size)
			    {
			      bufferB =
				MakeRange (buffer2.start,
					   buffer2.start + buffer_size);
			      buffer2 =
				MakeRange (B.end - buffer_size, B.end);

			    }
			  else
			    buffer1.end = buffer1.start;	/* failure */
			}
		      else
			{
			  /* we were unable to find a single buffer in A, so we'll need to find two buffers in B */
			  count = 1;
			  for (buffer1.start = B.end - 2;
			       buffer1.start >= B.start; buffer1.start--)
			    if (compare
				(array[buffer1.start],
				 array[buffer1.start + 1])
				|| compare (array[buffer1.start + 1],
					    array[buffer1.start]))
			      if (++count == buffer_size)
				break;
			  buffer1.end = buffer1.start + count;

			  count = 0;
			  for (buffer2.start = buffer1.start - 1;
			       buffer2.start >= B.start; buffer2.start--)
			    if (compare
				(array[buffer2.start],
				 array[buffer2.start + 1])
				|| compare (array[buffer2.start + 1],
					    array[buffer2.start]))
			      if (++count == buffer_size)
				break;
			  buffer2.end = buffer2.start + count;

			  if (Range_length (buffer2) == buffer_size)
			    {
			      bufferA = MakeRange (A.start, A.start);
			      bufferB =
				MakeRange (buffer2.start,
					   buffer2.start + buffer_size * 2);
			      buffer1 =
				MakeRange (B.end - buffer_size, B.end);
			      buffer2 =
				MakeRange (buffer1.start - buffer_size,
					   buffer1.start);

			    }
			  else
			    buffer1.end = buffer1.start;	/* failure */
			}
		    }

		  if (Range_length (buffer1) < buffer_size)
		    {
		      /* we failed to fill both buffers with unique values, which implies we're merging two subarrays with a lot of the same values repeated */
		      /* we can use this knowledge to write a merge operation that is optimized for arrays of repeating values */
		      while (Range_length (A) > 0 && Range_length (B) > 0)
			{
			  /* find the first place in B where the first item in A needs to be inserted */
			  long mid = BinaryFirst (array, A.start, B, compare);

			  /* rotate A into place */
			  long amount = mid - A.end;
			  Rotate (array, -amount, MakeRange (A.start, mid),
				  cache, cache_size);

			  /* calculate the new A and B ranges */
			  B.start = mid;
			  A =
			    MakeRange (BinaryLast
				       (array, A.start + amount, A, compare),
				       B.start);
			}

		      continue;
		    }

		  /* move the unique values to the start of A if needed */
		  length = Range_length (bufferA);
		  count = 0;
		  for (index = bufferA.start; count < length; index--)
		    {
		      if (index == A.start
			  || compare (array[index - 1], array[index])
			  || compare (array[index], array[index - 1]))
			{
			  Rotate (array, -count,
				  MakeRange (index + 1, bufferA.start + 1),
				  cache, cache_size);
			  bufferA.start = index + count;
			  count++;
			}
		    }
		  bufferA = MakeRange (A.start, A.start + length);

		  /* move the unique values to the end of B if needed */
		  length = Range_length (bufferB);
		  count = 0;
		  for (index = bufferB.start; count < length; index++)
		    {
		      if (index == B.end - 1
			  || compare (array[index], array[index + 1])
			  || compare (array[index + 1], array[index]))
			{
			  Rotate (array, count,
				  MakeRange (bufferB.start, index), cache,
				  cache_size);
			  bufferB.start = index - count;
			  count++;
			}
		    }
		  bufferB = MakeRange (B.end - length, B.end);

		  /* reuse these buffers next time! */
		  level1 = buffer1;
		  level2 = buffer2;
		  levelA = bufferA;
		  levelB = bufferB;
		}

	      /* break the remainder of A into blocks. firstA is the uneven-sized first A block */
	      blockA = MakeRange (bufferA.end, A.end);
	      firstA =
		MakeRange (bufferA.end,
			   bufferA.end + Range_length (blockA) % block_size);

	      /* swap the second value of each A block with the value in buffer1 */
	      index = 0;
	      for (indexA = firstA.end + 1; indexA < blockA.end;
		   index++, indexA += block_size)
		Swap (array[buffer1.start + index], array[indexA], Test);

	      /* start rolling the A blocks through the B blocks! */
	      /* whenever we leave an A block behind, we'll need to merge the previous A block with any B blocks that follow it, so track that information as well */
	      lastA = firstA;
	      lastB = MakeRange (0, 0);
	      blockB =
		MakeRange (B.start,
			   B.start + Min (block_size,
					  Range_length (B) -
					  Range_length (bufferB)));
	      blockA.start += Range_length (firstA);

	      minA = blockA.start;
	      min_value = array[minA];
	      indexA = 0;

	      if (Range_length (lastA) <= cache_size)
		memcpy (&cache[0], &array[lastA.start],
			Range_length (lastA) * sizeof (array[0]));
	      else
		BlockSwap (array, lastA.start, buffer2.start,
			   Range_length (lastA));

	      while (true)
		{
		  /* if there's a previous B block and the first value of the minimum A block is <= the last value of the previous B block */
		  if ((Range_length (lastB) > 0
		       && !compare (array[lastB.end - 1], min_value))
		      || Range_length (blockB) == 0)
		    {
		      /* figure out where to split the previous B block, and rotate it at the split */
		      long B_split =
			BinaryFirst (array, minA, lastB, compare);
		      long B_remaining = lastB.end - B_split;

		      /* swap the minimum A block to the beginning of the rolling A blocks */
		      BlockSwap (array, blockA.start, minA, block_size);

		      /* we need to swap the second item of the previous A block back with its original value, which is stored in buffer1 */
		      /* since the firstA block did not have its value swapped out, we need to make sure the previous A block is not unevenly sized */
		      Swap (array[blockA.start + 1],
			    array[buffer1.start + indexA++], Test);

		      /* locally merge the previous A block with the B values that follow it, using the buffer as swap space */
		      WikiMerge (array, buffer2, lastA,
				 MakeRange (lastA.end, B_split), compare,
				 cache, cache_size);

		      /* copy the previous A block into the cache or buffer2, since that's where we need it to be when we go to merge it anyway */
		      if (block_size <= cache_size)
			memcpy (&cache[0], &array[blockA.start],
				block_size * sizeof (array[0]));
		      else
			BlockSwap (array, blockA.start, buffer2.start,
				   block_size);

		      /* this is equivalent to rotating, but faster */
		      /* the area normally taken up by the A block is either the contents of buffer2, or data we don't need anymore since we memcopied it */
		      /* either way, we don't need to retain the order of those items, so instead of rotating we can just block swap B to where it belongs */
		      BlockSwap (array, B_split,
				 blockA.start + block_size - B_remaining,
				 B_remaining);

		      /* now we need to update the ranges and stuff */
		      lastA =
			MakeRange (blockA.start - B_remaining,
				   blockA.start - B_remaining + block_size);
		      lastB = MakeRange (lastA.end, lastA.end + B_remaining);
		      blockA.start += block_size;
		      if (Range_length (blockA) == 0)
			break;

		      /* search the second value of the remaining A blocks to find the new minimum A block (that's why we wrote unique values to them!) */
		      minA = blockA.start + 1;
		      for (findA = minA + block_size; findA < blockA.end;
			   findA += block_size)
			if (compare (array[findA], array[minA]))
			  minA = findA;
		      minA = minA - 1;	/* decrement once to get back to the start of that A block */
		      min_value = array[minA];

		    }
		  else if (Range_length (blockB) < block_size)
		    {
		      /* move the last B block, which is unevenly sized, to before the remaining A blocks, by using a rotation */
		      /* (using the cache is disabled since we have the contents of the previous A block in it!) */
		      Rotate (array, -Range_length (blockB),
			      MakeRange (blockA.start, blockB.end), cache, 0);
		      lastB =
			MakeRange (blockA.start,
				   blockA.start + Range_length (blockB));
		      blockA.start += Range_length (blockB);
		      blockA.end += Range_length (blockB);
		      minA += Range_length (blockB);
		      blockB.end = blockB.start;

		    }
		  else
		    {
		      /* roll the leftmost A block to the end by swapping it with the next B block */
		      BlockSwap (array, blockA.start, blockB.start,
				 block_size);
		      lastB =
			MakeRange (blockA.start, blockA.start + block_size);
		      if (minA == blockA.start)
			minA = blockA.end;

		      blockA.start += block_size;
		      blockA.end += block_size;
		      blockB.start += block_size;
		      blockB.end += block_size;
		      if (blockB.end > bufferB.start)
			blockB.end = bufferB.start;
		    }
		}

	      /* merge the last A block with the remaining B blocks */
	      WikiMerge (array, buffer2, lastA,
			 MakeRange (lastA.end,
				    B.end - Range_length (bufferB)), compare,
			 cache, cache_size);
	    }
	}

      if (Range_length (level1) > 0)
	{
	  long level_start;

	  /* when we're finished with this step we should have b1 b2 left over, where one of the buffers is all jumbled up */
	  /* insertion sort the jumbled up buffer, then redistribute them back into the array using the opposite process used for creating the buffer */
	  InsertionSort (array, level2, compare);

	  /* redistribute bufferA back into the array */
	  level_start = levelA.start;
	  for (index = levelA.end; Range_length (levelA) > 0; index++)
	    {
	      if (index == levelB.start
		  || !compare (array[index], array[levelA.start]))
		{
		  long amount = index - levelA.end;
		  Rotate (array, -amount, MakeRange (levelA.start, index),
			  cache, cache_size);
		  levelA.start += (amount + 1);
		  levelA.end += amount;
		  index--;
		}
	    }

	  /* redistribute bufferB back into the array */
	  for (index = levelB.start; Range_length (levelB) > 0; index--)
	    {
	      if (index == level_start
		  || !compare (array[levelB.end - 1], array[index - 1]))
		{
		  long amount = levelB.start - index;
		  Rotate (array, amount, MakeRange (index, levelB.end), cache,
			  cache_size);
		  levelB.start -= amount;
		  levelB.end -= (amount + 1);
		  index++;
		}
	    }
	}

      decimal_step += decimal_step;
      fractional_step += fractional_step;
      if (fractional_step >= fractional_base)
	{
	  fractional_step -= fractional_base;
	  decimal_step += 1;
	}
    }

#undef CACHE_SIZE
}
static TestCasePtr modes[9]={TestingPathological,TestingRandom,TestingMostlyDescending,TestingMostlyAscending,TestingAscending,TestingDescending,TestingEqual,TestingJittered,TestingMostlyEqual};
static void reset(void){srand_beebs(0);memset(counts,0,sizeof(counts));fallback=0;}
static void cases(int stop,int phase){reset();for(int c=0;c<=stop;c++){for(int i=0;i<400;i++){array1[i].value=modes[c](i,400);array1[i].index=i;}if(c!=stop||phase)observed_sort(array1,400,TestCompare);}}
static int64_t cellvalue(int cell){if(cell>=0&&cell<800)return (cell&1)?array1[cell/2].index:array1[cell/2].value;if(cell==1830)return seed;if(cell>=1831&&cell<1835)return counts[cell-1831];return INT64_MIN;}
#define EXTRA int64_t x1,int64_t x2,int64_t x3,int64_t x4,int64_t x5,int64_t x6,int64_t ctx
int64_t observe(int64_t encoded,EXTRA){int stage=encoded/2048,cell=encoded%2048;if(stage<0||stage>17||RAND_MAX!=2147483647||sizeof(long)!=8)return INT64_MIN;cases(stage/2,stage%2);return cellvalue(cell);}
int64_t repeat_observe(int64_t encoded,EXTRA){int n=encoded/2048,cell=encoded%2048;if(n<1||n>32)return INT64_MIN;for(int i=0;i<n;i++)cases(8,1);return cellvalue(cell);}
int64_t batch(int64_t n,EXTRA){if(n<1||n>32)return 0;benchmark_body(1,n);return verify_benchmark(0);}
int64_t oracle_selfcheck(int64_t n,EXTRA){if(n<1||n>32)return 0;benchmark_body(1,n);Test saved[400];memcpy(saved,array1,sizeof(saved));int ok=verify_benchmark(0);for(int i=0;i<n;i++)cases(8,1);return ok&&!fallback&&memcmp(saved,array1,sizeof(saved))==0&&verify_benchmark(0);}
int64_t unsupported_branches(int64_t stage,EXTRA){cases(stage/2,stage%2);return fallback;}
