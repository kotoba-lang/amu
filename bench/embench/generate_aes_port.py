#!/usr/bin/env python3
# BOOTSTRAP-TOOL: pinned profile/table extraction; the algorithm is Kotoba.
import argparse,hashlib,pathlib,re
p=argparse.ArgumentParser();p.add_argument('upstream',type=pathlib.Path);p.add_argument('output',type=pathlib.Path);a=p.parse_args()
b=a.upstream.read_bytes()
if hashlib.sha256(b).hexdigest()!='140117d48a832ecdc13ae817ea88a7436c01ec654d25d5dd0ba48cdf5f3ab3bc':raise SystemExit('unreviewed AES profile')
s=b.decode()
def values(marker):
 start=s.index('{',s.index(marker));depth=1;end=start+1
 while depth:
  depth+=(s[end]=='{')-(s[end]=='}');end+=1
 text=re.sub(r'/\*.*?\*/|//[^\n]*','',s[start:end],flags=re.S)
 return [int(v,16) for v in re.findall(r'0x[0-9a-fA-F]+',text)]
enc=values('_aes_encrypt_table =');dec=values('_aes_decrypt_table =');assert len(enc)==len(dec)==1280
parts=['''(ns embench.nettle-aes-full (:export [batch stage-cell test-nettle-aes]))
;; Full pinned Nettle AES-256 workload: both schedules, inversion, 16 blocks.
;; Copyright 2000-2013 Rafael R. Sevilla/Niels Moeller, 2019 Embecosm.
;; SPDX-License-Identifier: GPL-3.0-or-later.
''']
def table(name,items):
 for k in range((len(items)+127)//128):parts.append('(def '+name+'-'+str(k)+' ['+' '.join(map(str,items[k*128:(k+1)*128]))+'])\n')
 getter='(vector-at '+name+'-'+str((len(items)-1)//128)+' '+('i' if len(items)<=128 else '(- i '+str(((len(items)-1)//128)*128)+')')+')'
 for k in reversed(range((len(items)-1)//128)):
  index='i' if k==0 else '(- i '+str(k*128)+')'
  getter='(if (< i '+str((k+1)*128)+') (vector-at '+name+'-'+str(k)+' '+index+') '+getter+')'
 parts.append('(defn- '+name+' [i :i64] :i64 '+getter+')\n')
for mode,v in [('enc',enc),('dec',dec)]:
 table(mode+'-sbox',v[:256])
 for k in range(4):table(mode+'-t'+str(k),v[256+k*256:512+k*256])
for name,marker,count in [('mt','mtable[0x100]',256),('key-data','unsigned char key[32]',32),('plain-data','unsigned char plaintext[LEN]',256),('expected-data','unsigned char expected[LEN]',256),('rcon','rcon[10]',10)]:
 v=values(marker);assert len(v)==count,(name,len(v));table(name,v)
parts.append(pathlib.Path(__file__).with_name('aes-full-body.kotoba').read_text());a.output.write_text(''.join(parts))
