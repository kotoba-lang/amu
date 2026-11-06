# Diagnostic only; requires an independently built and signed ADI2 helper.
import argparse, os, pathlib, struct, subprocess, tempfile
ap=argparse.ArgumentParser();ap.add_argument('--helper',required=True);args=ap.parse_args();helper=str(pathlib.Path(args.helper).resolve(strict=True))
def inspect(fd,extra=()):
 st=os.fstat(fd)
 def mapfd():
  if fd!=3:os.dup2(fd,3)
 r=subprocess.run([helper,*extra],pass_fds=((fd,) if fd==3 else (3,fd)),preexec_fn=mapfd,capture_output=True,timeout=6)
 if r.returncode:return r,None
 raw=bytes.fromhex(r.stdout.strip().decode());magic,n,dev,ino=struct.unpack_from('<4sIQQ',raw)
 assert magic==b'ADI2' and n==len(raw)-24 and dev==(st.st_dev&0xffffffff) and ino==st.st_ino
 entries=[];i=24
 while i<len(raw):
  _,_,reclen,namelen,typ=struct.unpack_from('<QQHHB',raw,i);assert reclen>=22 and i+reclen<=len(raw) and namelen+22<=reclen
  name=raw[i+21:i+21+namelen];assert raw[i+21+namelen]==0;entries.append((name.decode(),typ));i+=reclen
 return r,(dev,ino,entries)
with tempfile.TemporaryDirectory(prefix='awai156-identity-') as d:
 root=pathlib.Path(d);cur=root/'target';cur.mkdir();(cur/'one').write_bytes(b'1');(cur/'link').symlink_to('one');(cur/'sub').mkdir();fd=os.open(cur,os.O_RDONLY|os.O_DIRECTORY);assert fd==3
 try:
  os.listdir(fd);r,first=inspect(fd);assert r.returncode==0 and {n for n,t in first[2]}=={'.','..','one','link','sub'}
  r,_=inspect(fd,('unexpected',));assert r.returncode!=0 and not r.stdout
  cur.rename(root/'held-old');cur.mkdir();(cur/'other').write_text('other');fd2=os.open(cur,os.O_RDONLY|os.O_DIRECTORY)
  try:
   r,second=inspect(fd2);assert r.returncode==0 and first[:2]!=second[:2]
   r,old=inspect(fd);assert r.returncode==0 and old[:2]==first[:2]
  finally:os.close(fd2)
 finally:os.close(fd)
 fd=os.open(root/'held-old'/'one',os.O_RDONLY);assert fd==3
 try:r,_=inspect(fd);assert r.returncode!=0 and not r.stdout
 finally:os.close(fd)
 many=root/'many';many.mkdir()
 for i in range(200):(many/('entry%03d'%i)).touch()
 fd=os.open(many,os.O_RDONLY|os.O_DIRECTORY);assert fd==3
 try:r,_=inspect(fd);assert r.returncode!=0 and not r.stdout
 finally:os.close(fd)
print('identity, replacement, old FD, file, argument and overflow cases passed')
