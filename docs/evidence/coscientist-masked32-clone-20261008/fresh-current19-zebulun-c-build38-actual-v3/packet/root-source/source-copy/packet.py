"""Pure bounded regular-file packet constructor; no network/process/archive API."""
from pathlib import Path,PurePosixPath
import base64,hashlib,json,stat
H=lambda b:hashlib.sha256(b).hexdigest()
MAX_FILES=256;MAX_LOGICAL=8*1024*1024;MAX_PAYLOAD=8*1024*1024
REMOTE='/Users/zebulun/github/workspaces/codex/tc-hft-current19-quiet-c-packet-v3-20261009-root'
def relative(s):
 assert type(s) is str and s and '\\' not in s and '\x00' not in s
 p=PurePosixPath(s);assert not p.is_absolute() and '..' not in p.parts and '.' not in s.split('/') and str(p)==s and len(p.parts)<=12 and len(s)<=256
 return s
def read_pin(r):
 p=Path(r['source']);before=p.lstat();assert stat.S_ISREG(before.st_mode) and not p.is_symlink() and before.st_size==r['bytes'] and 0<=before.st_size<=MAX_LOGICAL
 b=p.read_bytes();after=p.lstat();assert (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)==(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns)
 assert len(b)==r['bytes'] and H(b)==r['sha256'];return b
def validate(manifest):
 assert set(manifest)=={'schema','remoteRoot','files','exactFiles','exactLogicalBytes','owners','executionCredit'}
 assert manifest['schema']=='CURRENT19_CORE_CONSUMER_CBUILD_PACKET_V1' and manifest['remoteRoot']==REMOTE and manifest['executionCredit'] is False
 files=manifest['files'];assert len(files)==manifest['exactFiles'] and 1<=len(files)<=MAX_FILES
 assert sum(x['bytes'] for x in files)==manifest['exactLogicalBytes']<=MAX_LOGICAL
 seen=set()
 for r in files:
  assert set(r)=={'source','relativePath','bytes','sha256','owner'} and r['owner'] in manifest['owners']
  s=relative(r['relativePath']);assert s not in seen and s!='install-receipt.json';seen.add(s)
  assert type(r['bytes']) is int and r['bytes']>=0 and type(r['sha256']) is str and len(r['sha256'])==64
  assert not any(s.startswith(x+'/') for x in seen if x!=s) and not any(x.startswith(s+'/') for x in seen if x!=s)
  read_pin(r)
 return True
def payload(manifest):
 validate(manifest)
 records=[{'relativePath':r['relativePath'],'bytes':r['bytes'],'sha256':r['sha256'],'base64':base64.b64encode(read_pin(r)).decode('ascii')} for r in manifest['files']]
 b=json.dumps({'schema':'CURRENT19_INSTALL_ENVELOPE_V1','manifest':manifest,'files':records},separators=(',',':')).encode()
 assert len(b)<=MAX_PAYLOAD;return b
