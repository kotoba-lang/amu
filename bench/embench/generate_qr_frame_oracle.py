#!/usr/bin/env python3
# BOOTSTRAP-TOOL: observe pinned initframe; full QR benchmark remains incomplete.
import argparse,hashlib,json,pathlib
p=argparse.ArgumentParser();p.add_argument('upstream',type=pathlib.Path);p.add_argument('directory',type=pathlib.Path);a=p.parse_args()
pins={'qrencode.c':'05d2147e1809578fcdce4ebd6105a555e59dc8c9b5c5b2f4d7a239ea8d9bf5b8','qrframe.c':'3d3400ff94ba165d0cf2945a364527f55291fa144511e0a94f317fdc58992f15','ecctable.h':'54e176fa47d4c20baab098962a0c0f1a8629362499dbc8fbab5d581312b1002c'}
for f,d in pins.items():
 if hashlib.sha256((a.upstream/f).read_bytes()).hexdigest()!=d:raise SystemExit('unreviewed QR frame profile: '+f)
s=(a.upstream/'qrframe.c').read_text();begin=s.index('initframe ()\n{');end=s.index('\nvoid\nfreeframe',begin);body=s[begin:end];body=body[body.index('{')+1:body.rfind('}')]
markers=[('// finders','snapshot(0);'),('// alignment blocks','snapshot(1);'),('// single black','snapshot(2);'),('// timing gap','snapshot(3);'),('// reserve mask-format area','snapshot(4);'),('// timing\n','snapshot(5);'),('// version block','snapshot(6);')]
for marker,call in markers:
 assert body.count(marker)==1,(marker,body.count(marker));body=body.replace(marker,call+'\n  '+marker,1)
assert body.count('  putvpat ();')==1;body=body.replace('  putvpat ();','  putvpat ();\n  snapshot(7);',1);body+='\nsnapshot(8);\n'
c='''/* BOOTSTRAP-TOOL: pinned C initframe with untimed snapshots only.
 * Copyright 2014-2019 Embecosm/Bristol, qrduino contributors; GPL-3.0-or-later. */
#include <stdint.h>
#include <limits.h>
#include "../upstream/src/qrduino/qrframe.c"
static unsigned char heap[8192] __attribute__((aligned));static int64_t states[9][256];
static void snapshot(int stage){for(int i=0;i<100;i++)states[stage][i]=framebase[i];for(int i=0;i<41;i++)states[stage][128+i]=framask[i];}
static int prepare(void){memset(states,0,sizeof(states));init_heap_beebs(heap,8192);initeccsize(1,22);return VERSION==2&&WD==25&&WDB==4&&adelta[VERSION]==15;}
static void observed(void){
'''+body+'''}
#define EXTRA int64_t x1,int64_t x2,int64_t x3,int64_t x4,int64_t x5,int64_t x6,int64_t ctx
int64_t observe(int64_t encoded,EXTRA){int stage=encoded/256,cell=encoded%256;if(encoded<0||stage>8||!prepare())return INT64_MIN;observed();return states[stage][cell];}
int64_t oracle_selfcheck(int64_t n,EXTRA){if(n<1||n>32||!prepare())return 0;observed();int64_t saved[256];memcpy(saved,states[8],sizeof(saved));
 for(int j=0;j<n;j++){if(!prepare())return 0;initframe();for(int i=0;i<100;i++)if(framebase[i]!=saved[i])return 0;for(int i=0;i<41;i++)if(framask[i]!=saved[128+i])return 0;freeframe();freeecc();if(!check_heap_beebs(heap))return 0;}return 1;}
'''
a.directory.mkdir(parents=True,exist_ok=True);(a.directory/'c-bridge.c').write_text(c);(a.directory/'profile.json').write_text(json.dumps({'status':'frame-fragment-only','version':2,'size':22,'eccLevel':1,'WD':25,'WDB':4,'alignmentDelta':15,'baseBytes':100,'maskBytes':41,'sourcePins':pins},indent=2)+'\n')
