/* BOOTSTRAP-TOOL: unchanged original C model/body and diagnostic votes. */
#define GLOBAL_SCALE_FACTOR 1
#include <stdint.h>
#include <limits.h>
#include <string.h>
#include "../upstream/src/xgboost/xgboost.c"
#include "../upstream/src/xgboost/testbench.c"
#define EXTRA int64_t x1,int64_t x2,int64_t x3,int64_t x4,int64_t x5,int64_t x6,int64_t ctx
static uint16_t snapshot_votes[10];static uint16_t snapshots[128][11];
static uint8_t observed_predict(const uint8_t *x) {
    uint16_t votes[NUM_CLASSES] = { 0 };

    size_t tree_idx = 0;
    size_t node_base = 0;
    size_t leaf_base = 0;
    for (size_t i = 0; i < NUM_CLASSES; i++) {
        for (size_t j = 0; j < NUM_TREES; j++) {
            const uint8_t tree_size = tree_sizes[tree_idx];
            const uint8_t *tree_idxs = &comparison_idxs[node_base];
            const uint8_t *tree_values = &comparison_values[node_base];
            const uint8_t *tree_left_children = &left_children[node_base];
            const uint8_t *tree_right_children = &right_children[node_base];
            const uint8_t *tree_leaf_values = &leaf_values[leaf_base];

            // Find leaf node for this tree
            uint8_t node_id = 0;
            while(!(node_id & 0x80)) { // Leaf nodes have ID >= 128
                const uint16_t node_idx = tree_idxs[node_id];
                const uint8_t node_value = tree_values[node_id];
                if (x[node_idx] < node_value) { // Check condition for node
                    node_id = tree_left_children[node_id];
                } else {
                    node_id = tree_right_children[node_id];
                }
            }
            uint8_t leaf_idx = node_id & 0x7F; // Clear MSB to get leaf index
            uint8_t leaf_value = tree_leaf_values[leaf_idx];
            votes[i] += leaf_value;

            tree_idx++;
            node_base += tree_size;
            leaf_base += tree_size+1; // n internal nodes => n+1 leaves
        }
    }

    // return argmax of votes
    uint8_t class_idx = 0;
    uint16_t max_votes = votes[0];
    for (uint8_t i = 1; i < 10; i++) {
        if (votes[i] > max_votes) {
            class_idx = i;
            max_votes = votes[i];
        }
    }

    for(int observer_i=0;observer_i<10;observer_i++)snapshot_votes[observer_i]=votes[observer_i];
    return class_idx;
}
int64_t bench(int64_t n,EXTRA){if(!n)return 0;initialise_benchmark();return verify_benchmark(benchmark_body(1,n));}
int64_t result(int64_t n,EXTRA){if(!n)return 0;initialise_benchmark();return benchmark_body(1,n);}
int64_t observe(int64_t encoded,EXTRA){int n=encoded/2048,f=encoded%2048;memset(snapshots,0,sizeof(snapshots));int correct=0;for(int b=0;b<n;b++)for(int i=0;i<128;i++){uint8_t predicted=observed_predict(X_test[i]);snapshots[i][0]=predicted;for(int j=0;j<10;j++)snapshots[i][j+1]=snapshot_votes[j];if(predicted==Y_test[i])correct++;}if(f==0)return correct;if(f<=1408)return snapshots[(f-1)/11][(f-1)%11];return INT64_MIN;}
static unsigned char model_byte(int i){
 if(i<400)return ((const uint8_t *)tree_sizes)[i-0];
 if(i<6487)return ((const uint8_t *)comparison_idxs)[i-400];
 if(i<12574)return ((const uint8_t *)comparison_values)[i-6487];
 if(i<18661)return ((const uint8_t *)left_children)[i-12574];
 if(i<24748)return ((const uint8_t *)right_children)[i-18661];
 if(i<31235)return ((const uint8_t *)leaf_values)[i-24748];
 if(i<39427)return ((const uint8_t *)X_test)[i-31235];
 if(i<39555)return ((const uint8_t *)Y_test)[i-39427];
 return 0;}
int64_t model_observe(int64_t group,EXTRA){int64_t acc=0;for(int i=0;i<4;i++)acc=acc*256+model_byte(group*4+i);return acc;}
int64_t oracle_selfcheck(int64_t n,EXTRA){for(int i=0;i<128;i++)if(observed_predict(X_test[i])!=predict(X_test[i]))return 0;return result(n,0,0,0,0,0,0,0)==126*n&&bench(n,0,0,0,0,0,0,0)==1;}
