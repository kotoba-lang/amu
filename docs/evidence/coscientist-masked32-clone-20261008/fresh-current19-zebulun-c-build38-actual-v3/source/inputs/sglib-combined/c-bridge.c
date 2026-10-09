/* BOOTSTRAP-TOOL: exact pinned C body with snapshots, no timed instrumentation.
 * Copyright 2014-2019 Embecosm / University of Bristol.
 * SPDX-License-Identifier: GPL-3.0-or-later */
#include <stdint.h>
#include <limits.h>
#define GLOBAL_SCALE_FACTOR 1
#include "../upstream/src/sglib-combined/combined.c"
static int64_t states[6][1860];static int64_t visit[100];static int visit_count;
static int list_id(dllist *p){return p?(int)(((char*)p-heap)/sizeof(dllist))+1:0;}
static int hash_id(ilist *p){return p?(int)(((char*)p-heap-2400)/sizeof(ilist))+1:0;}
static int tree_id(rbtree *p){return p?(int)(((char*)p-heap-4000)/sizeof(rbtree))+1:0;}
static void snap(int stage,int cnt,int bytes,int *a,int ai,int aj,rbtree *root){int64_t *v=states[stage];
 v[0]=cnt;v[1]=stage>=1?list_id(the_list):0;v[2]=stage==5?tree_id(root):0;v[3]=bytes;
 for(int i=0;i<100;i++)v[100+i]=array2[i];
 if(stage>=1)for(int i=0;i<100;i++){dllist *p=(dllist*)(heap+i*sizeof(dllist));v[200+i*3]=p->i;v[201+i*3]=list_id(p->ptr_to_next);v[202+i*3]=list_id(p->ptr_to_previous);}
 if(stage>=2){for(int i=0;i<100;i++){ilist *p=(ilist*)(heap+2400+i*sizeof(ilist));v[500+i*2]=p->i;v[501+i*2]=hash_id(p->next);}for(int i=0;i<20;i++)v[700+i]=hash_id(htab[i]);}
 if(stage>=3){for(int i=0;i<100;i++)v[720+i]=a[i];v[5]=ai;v[6]=aj;v[7]=stage>=4?ai:0;}
 if(stage==5){for(int i=0;i<100;i++){rbtree *p=(rbtree*)(heap+4000+i*sizeof(rbtree));v[900+i*4]=p->n;v[901+i*4]=p->color_field;v[902+i*4]=tree_id(p->left);v[903+i*4]=tree_id(p->right);}v[8]=0;v[9]=0;v[10]=visit_count;for(int i=0;i<visit_count;i++)v[1760+i]=visit[i];}}
static void observed(unsigned n){memset(states,0,sizeof(states));memset(heap,0,sizeof(heap));visit_count=0;
 volatile int cnt;for(unsigned run=0;run<n;run++){visit_count=0;
	int i;
	dllist *l;
	struct ilist ii, *nn, *ll;
	struct sglib_hashed_ilist_iterator it;
	int ai, aj, n;
	int a[MAX_PARAMS];
	struct rbtree e, *t, *the_tree, *te;
	struct sglib_rbtree_iterator it2;

	/* Array quicksort */

	memcpy (array2, array, 100 * sizeof (array[0]));
	SGLIB_ARRAY_SINGLE_QUICK_SORT (int, array2, 100,
				       SGLIB_NUMERIC_COMPARATOR);

snap(0,0,0,a,0,0,NULL);
	/* Doubly linked list */

	init_heap_beebs ((void *) heap, HEAP_SIZE);
	the_list = NULL;

	for (i = 0; i < 100; ++i)
	  {
	    l = malloc_beebs (sizeof (dllist));
	    l->i = array[i];
	    sglib_dllist_add (&the_list, l);
	  }

	sglib_dllist_sort (&the_list);

	cnt = 0;

	for (l = sglib_dllist_get_first (the_list); l != NULL;
	     l = l->ptr_to_next)
	  cnt++;

snap(1,cnt,2400,a,0,0,NULL);
	/* Hash table */

	sglib_hashed_ilist_init (htab);

	for (i = 0; i < 100; i++)
	  {
	    ii.i = array[i];
	    if (sglib_hashed_ilist_find_member (htab, &ii) == NULL)
	      {
		nn = malloc_beebs (sizeof (struct ilist));
		nn->i = array[i];
		sglib_hashed_ilist_add (htab, nn);
	      }
	  }

	for (ll = sglib_hashed_ilist_it_init (&it, htab);
	     ll != NULL; ll = sglib_hashed_ilist_it_next (&it))
	  {
	    cnt++;
	  }

snap(2,cnt,4000,a,0,0,NULL);
	/* Queue */

	// echo parameters using a queue
	SGLIB_QUEUE_INIT (int, a, ai, aj);
	for (i = 0; i < 100; i++)
	  {
	    n = array[i];
	    SGLIB_QUEUE_ADD (int, a, n, ai, aj, MAX_PARAMS);
	  }
	while (!SGLIB_QUEUE_IS_EMPTY (int, a, ai, aj))
	  {
	    cnt += SGLIB_QUEUE_FIRST_ELEMENT (int, a, ai, aj);
	    SGLIB_QUEUE_DELETE (int, a, ai, aj, MAX_PARAMS);
	  }

snap(3,cnt,4000,a,ai,aj,NULL);
	// print parameters in descending order
	SGLIB_HEAP_INIT (int, a, ai);
	for (i = 0; i < 100; i++)
	  {
	    n = array[i];
	    SGLIB_HEAP_ADD (int, a, n, ai, MAX_PARAMS,
			    SGLIB_NUMERIC_COMPARATOR);
	  }
	while (!SGLIB_HEAP_IS_EMPTY (int, a, ai))
	  {
	    cnt += SGLIB_HEAP_FIRST_ELEMENT (int, a, ai);
	    SGLIB_HEAP_DELETE (int, a, ai, MAX_PARAMS,
			       SGLIB_NUMERIC_COMPARATOR);
	  }

snap(4,cnt,4000,a,ai,aj,NULL);
	/* RB Tree */

	the_tree = NULL;
	for (i = 0; i < 100; i++)
	  {
	    e.n = array[i];
	    if (sglib_rbtree_find_member (the_tree, &e) == NULL)
	      {
		t = malloc_beebs (sizeof (struct rbtree));
		t->n = array[i];
		sglib_rbtree_add (&the_tree, t);
	      }
	  }

	for (te = sglib_rbtree_it_init_inorder (&it2, the_tree);
	     te != NULL; te = sglib_rbtree_it_next (&it2))
	  {
	    visit[visit_count++]=tree_id(te);
	    cnt += te->n;
	  }
snap(5,cnt,6400,a,ai,aj,the_tree);
}}
#define EXTRA int64_t x1,int64_t x2,int64_t x3,int64_t x4,int64_t x5,int64_t x6,int64_t ctx
int64_t observe_stage(int64_t encoded,EXTRA){int stage=encoded/4096,cell=encoded%4096;if(encoded<0||stage>5||cell>=1860)return INT64_MIN;observed(1);return states[stage][cell];}
int64_t oracle_selfcheck(int64_t n,EXTRA){if(n<1||n>32)return 0;observed((unsigned)n);int64_t expected[1860];memcpy(expected,states[5],sizeof(expected));int result=benchmark_body(1,(unsigned)n);
 int a[101]={0};snap(5,result,6400,a,0,100,NULL);
 // The original body has no public tree root; compare its public array/list/hash and result.
 for(int i=100;i<720;i++)if(states[5][i]!=expected[i])return 0;
 for(int i=900;i<1300;i++)if(states[5][i]!=expected[i])return 0;
 return result==15050 && verify_benchmark(result);}
int64_t observe_repeat(int64_t encoded,EXTRA){int n=encoded/4096,cell=encoded%4096;if(encoded<0||n<1||n>32||cell>=1760)return INT64_MIN;observed(n);return states[5][cell];}
int64_t batch(int64_t n,EXTRA){if(n<1||n>UINT_MAX)return 0;return verify_benchmark(benchmark_body(1,(unsigned)n));}
