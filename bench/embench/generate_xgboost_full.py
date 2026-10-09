#!/usr/bin/env python3
# BOOTSTRAP-TOOL: unchanged encoded data/decoder plus full owned-model repetition.
import argparse,ast,hashlib,json,pathlib,re
p=argparse.ArgumentParser();p.add_argument('upstream',type=pathlib.Path);p.add_argument('port',type=pathlib.Path);p.add_argument('directory',type=pathlib.Path);a=p.parse_args()
pins={'xgboost.c':'f8bfdbe790a59387d7970cda4d01851708d75895b2042fcbfea4eeb4fcb907ac','xgboost.h':'ccc41929ab9aea88311390c1181da4fda36cf68806477fedd32de5f2aa71bd52','testbench.c':'f357fe4b10ef55a4414dc9973092369c0ca7f8fab2ba7c17af4e9aaa952c3c57'}
for f,h in pins.items():
 if hashlib.sha256((a.upstream/f).read_bytes()).hexdigest()!=h:raise SystemExit('unreviewed xgboost profile: '+f)
helperpin='1a2b12e0e00f2700da87b7c83b5075b70437c505ad92503793c4f4ea8671ab9c'
if hashlib.sha256(a.port.read_bytes()).hexdigest()!=helperpin:raise SystemExit('unreviewed xgboost data/decoder')
module=ast.parse(pathlib.Path(__file__).with_name('generate_picojpeg_coefficients.py').read_text());helpers=[x for x in module.body if isinstance(x,(ast.ClassDef,ast.FunctionDef)) and x.name in ('Vec','read','emit')];exec(compile(ast.Module(body=helpers,type_ignores=[]),'checked AST reader','exec'))
forms=[f for f in read(a.port.read_text()) if f[0]=='def' or (f[0]=='defn-' and f[1] in ('sextet','byte-at'))]
s=(a.upstream/'xgboost.c').read_text();names=['tree_sizes','comparison_idxs','comparison_values','left_children','right_children','leaf_values','X_test','Y_test'];sizes={};bases={};total=0
for name in names:
 m=re.search(r'const\s+uint8_t\s+'+name+r'(?:\[[^;=]*\])*\s*=\s*\{(.*?)\}\s*;',s,re.S)
 if m is None:raise SystemExit('unreviewed array '+name)
 values=[int(x) for x in re.findall(r'\d+',m.group(1))];sizes[name]=len(values);bases[name]=total;total+=len(values)
if total!=39555 or sizes['tree_sizes']!=400 or sizes['X_test']!=8192 or sizes['Y_test']!=128:raise SystemExit('unreviewed model dimensions')
new='''
(defn- put [v :vector-i64 i :i64 x :i64] :vector-i64 (vector-assoc! v i x))
(defn- decode [v :vector-i64 data :string base :i64 n :i64 i :i64] :vector-i64
 (if (= i n) v (decode (put v (+ base i) (byte-at data i)) data base n (+ i 1))))
'''
expr='(vector-alloc (if record 40974 39566))'
for name in names:expr='(decode '+expr+' '+name.replace('_','-').lower()+' '+str(bases[name])+' '+str(sizes[name])+' 0)'
new+='(defn- input-state [record :bool] :vector-i64 '+expr+')\n'
new+='''
(defn- clear-votes [v :vector-i64 i :i64] :vector-i64
 (if (= i 10) v (clear-votes (put v (+ 39555 i) 0) (+ i 1))))
(defn- walk [v :vector-i64 sample :i64 nb :i64 lb :i64 node :i64] :i64
 (if (= (bit-and node 128) 128) (vector-at v (+ LEAF (+ lb (bit-and node 127))))
  (let [feature (vector-at v (+ IDX (+ nb node))) threshold (vector-at v (+ VALUE (+ nb node))) x (vector-at v (+ X (+ (* sample 64) feature))) next (vector-at v (+ (if (< x threshold) LEFT RIGHT) (+ nb node)))]
   (walk v sample nb lb next))))
(defn- trees [v :vector-i64 sample :i64 cls :i64 j :i64 tree :i64 nb :i64 lb :i64] :vector-i64
 (if (= cls 10) v
  (if (= j 40) (trees v sample (+ cls 1) 0 tree nb lb)
   (let [size (vector-at v tree) vote (walk v sample nb lb 0) w (put v (+ 39555 cls) (+ (vector-at v (+ 39555 cls)) vote))]
    (trees w sample cls (+ j 1) (+ tree 1) (+ nb size) (+ lb size 1))))))
(defn- argmax [v :vector-i64 cls :i64 best :i64 max-vote :i64] :i64
 (if (= cls 10) best
  (let [candidate (vector-at v (+ 39555 cls))]
   (if (> candidate max-vote) (argmax v (+ cls 1) cls candidate) (argmax v (+ cls 1) best max-vote)))))
(defn- record-votes [v :vector-i64 sample :i64 i :i64] :vector-i64
 (if (= i 10) v (record-votes (put v (+ 39566 (+ (* sample 11) (+ i 1))) (vector-at v (+ 39555 i))) sample (+ i 1))))
(defn- samples [v :vector-i64 sample :i64 record :bool] :vector-i64
 (if (= sample 128) v
  (let [w (trees (clear-votes v 0) sample 0 0 0 0 0) prediction (argmax w 1 0 (vector-at w 39555))
        count (+ (vector-at w 39565) (if (= prediction (vector-at w (+ Y sample))) 1 0)) out (put w 39565 count)
        recorded (if record (put (record-votes out sample 0) (+ 39566 (* sample 11)) prediction) out)]
   (samples recorded (+ sample 1) record))))
(defn- bodies [v :vector-i64 n :i64 i :i64 record :bool] :vector-i64
 (if (= i n) v (bodies (samples v 0 record) n (+ i 1) record)))
(defn- state [n :i64 record :bool] :vector-i64 (bodies (input-state record) n 0 record))
(defn bench [n :i64] :i64 (if (= n 0) 0 (if (>= (vector-at (state n false) 39565) 0) 1 0)))
(defn result [n :i64] :i64 (if (= n 0) 0 (vector-at (state n false) 39565)))
(defn observe [encoded :i64] :i64
 (let [v (state (quot encoded 2048) true) field (rem encoded 2048)]
  (if (= field 0) (vector-at v 39565) (vector-at v (+ 39566 (- field 1))))))
(defn- pack4 [v :vector-i64 base :i64 i :i64 acc :i64] :i64
 (if (= i 4) acc (pack4 v base (+ i 1) (+ (* acc 256) (if (< (+ base i) 39555) (vector-at v (+ base i)) 0)))))
(defn model-observe [group :i64] :i64 (pack4 (input-state false) (* group 4) 0 0))
(defn bounds-probe [i :i64] :i64 (vector-at (vector-alloc 40974) i))
'''
for token,name in [('LEAF','leaf_values'),('IDX','comparison_idxs'),('VALUE','comparison_values'),('X','X_test'),('LEFT','left_children'),('RIGHT','right_children'),('Y','Y_test')]:new=re.sub(r'\b'+token+r'\b',str(bases[name]),new)
a.directory.mkdir(parents=True,exist_ok=True);(a.directory/'xgboost-full.kotoba').write_text('(ns embench.xgboost-full (:export [bench result observe model-observe bounds-probe]))\n;; All original 400 trees / 128 inputs. GPL-3.0-or-later, Embench contributors.\n'+'\n'.join(map(emit,forms+read(new)))+'\n')
start=s.index('uint8_t predict(');end=s.index('\n\n\nconst uint8_t X_test',start);predict=s[start:end].replace('uint8_t predict(','static uint8_t observed_predict(',1);needle='    return class_idx;';assert predict.count(needle)==1;predict=predict.replace(needle,'    for(int observer_i=0;observer_i<10;observer_i++)snapshot_votes[observer_i]=votes[observer_i];\n'+needle)
c='''/* BOOTSTRAP-TOOL: unchanged original C model/body and diagnostic votes. */
#define GLOBAL_SCALE_FACTOR 1
#include <stdint.h>
#include <limits.h>
#include <string.h>
#include "../upstream/src/xgboost/xgboost.c"
#include "../upstream/src/xgboost/testbench.c"
#define EXTRA int64_t x1,int64_t x2,int64_t x3,int64_t x4,int64_t x5,int64_t x6,int64_t ctx
static uint16_t snapshot_votes[10];static uint16_t snapshots[128][11];
'''+predict+'''
int64_t bench(int64_t n,EXTRA){if(!n)return 0;initialise_benchmark();return verify_benchmark(benchmark_body(1,n));}
int64_t result(int64_t n,EXTRA){if(!n)return 0;initialise_benchmark();return benchmark_body(1,n);}
int64_t observe(int64_t encoded,EXTRA){int n=encoded/2048,f=encoded%2048;memset(snapshots,0,sizeof(snapshots));int correct=0;for(int b=0;b<n;b++)for(int i=0;i<128;i++){uint8_t predicted=observed_predict(X_test[i]);snapshots[i][0]=predicted;for(int j=0;j<10;j++)snapshots[i][j+1]=snapshot_votes[j];if(predicted==Y_test[i])correct++;}if(f==0)return correct;if(f<=1408)return snapshots[(f-1)/11][(f-1)%11];return INT64_MIN;}
static unsigned char model_byte(int i){
'''
for name in names:c+=' if(i<'+str(bases[name]+sizes[name])+')return ((const uint8_t *)'+name+')[i-'+str(bases[name])+'];\n'
c+=''' return 0;}
int64_t model_observe(int64_t group,EXTRA){int64_t acc=0;for(int i=0;i<4;i++)acc=acc*256+model_byte(group*4+i);return acc;}
int64_t oracle_selfcheck(int64_t n,EXTRA){for(int i=0;i<128;i++)if(observed_predict(X_test[i])!=predict(X_test[i]))return 0;return result(n,0,0,0,0,0,0,0)==126*n&&bench(n,0,0,0,0,0,0,0)==1;}
'''
(a.directory/'c-bridge.c').write_text(c);(a.directory/'profile.json').write_text(json.dumps({'sourcePins':pins,'helperComponentSha256':helperpin,'sizes':sizes,'bases':bases,'modelBytes':39555,'modelPackedGroups':9889,'benchmarkWorkspaceCells':39566,'workspaceCells':40974,'fields':list(range(1409)),'iterations':[0,1,2,17,32],'observationIterations':[0,1,32],'verification':'original verifier once after batch, strong raw-count/prediction/vote diagnostics'},indent=2)+'\n')
