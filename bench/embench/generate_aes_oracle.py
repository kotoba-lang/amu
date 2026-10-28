#!/usr/bin/env python3
# BOOTSTRAP-TOOL: observation uses unchanged AES functions; timed body unchanged.
import argparse,hashlib,pathlib
p=argparse.ArgumentParser();p.add_argument('upstream',type=pathlib.Path);p.add_argument('output',type=pathlib.Path);a=p.parse_args()
if hashlib.sha256(a.upstream.read_bytes()).hexdigest()!='140117d48a832ecdc13ae817ea88a7436c01ec654d25d5dd0ba48cdf5f3ab3bc':raise SystemExit('unreviewed AES profile')
a.output.write_text('''/* BOOTSTRAP-TOOL: Nettle AES-256 state oracle, unchanged upstream calls.
 * Copyright 2000-2013 Rafael R. Sevilla/Niels Moeller, 2019 Embecosm.
 * SPDX-License-Identifier: GPL-3.0-or-later */
#include <stdint.h>
#include <limits.h>
#include <string.h>
#define GLOBAL_SCALE_FACTOR 1
#include "../upstream/src/nettle-aes/nettle-aes.c"
static uint8_t original_key[32],original_plaintext[256];
static int initialized;
static int64_t observation[5*634];
static void prepare(unsigned test){
 if(!initialized){memcpy(original_key,key,32);memcpy(original_plaintext,plaintext,256);initialized=1;}
 for(unsigned i=0;i<32;i++)key[i]=test==3?0:test==1?original_key[i]^255:original_key[i];
 for(unsigned i=0;i<256;i++)plaintext[i]=test==3?0:test==2?original_plaintext[i]^i:original_plaintext[i];
 memset(&encctx,0,sizeof encctx);memset(&decctx,0,sizeof decctx);
 memset(encrypted,0,256);memset(decrypted,0,256);
}
static void snapshot(unsigned stage){
 int64_t *v=observation+stage*634;
 for(unsigned i=0;i<60;i++){v[i]=encctx.keys[i];v[60+i]=decctx.keys[i];}
 for(unsigned i=0;i<256;i++){v[120+i]=encrypted[i];v[376+i]=decrypted[i];}
 v[632]=encctx.rounds;v[633]=decctx.rounds;
}
static void observe(unsigned test){
 prepare(test);snapshot(0);aes_set_encrypt_key(&encctx,32,key);snapshot(1);
 aes_encrypt(&encctx,256,encrypted,plaintext);snapshot(2);
 aes_set_decrypt_key(&decctx,32,key);snapshot(3);
 aes_decrypt(&decctx,256,decrypted,encrypted);snapshot(4);
}
#define EXTRA int64_t x1,int64_t x2,int64_t x3,int64_t x4,int64_t x5,int64_t x6,int64_t ctx
int64_t stage_cell(int64_t encoded,EXTRA){
 unsigned test=encoded/4096,code=encoded%4096,stage=code/634,cell=code%634;
 if(encoded<0||test>3||stage>4)return INT64_MIN;
 observe(test);return observation[stage*634+cell];
}
int64_t oracle_selfcheck(int64_t test,EXTRA){
 if(test<0||test>3)return 0;observe(test);
 if(test==0&&!verify_benchmark(0))return 0;
 prepare(test);benchmark_body(1,1);snapshot(0);
 for(unsigned i=0;i<634;i++)if(observation[i]!=observation[4*634+i])return 0;
 return test==0?verify_benchmark(0):1;
}
int64_t batch(int64_t n,EXTRA){
 if(n<1||n>UINT_MAX)return 0;prepare(0);
 return verify_benchmark(benchmark_body(1,(unsigned)n));
}
''')
