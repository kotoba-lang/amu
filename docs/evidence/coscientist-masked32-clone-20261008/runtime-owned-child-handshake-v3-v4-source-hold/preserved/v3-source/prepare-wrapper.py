from pathlib import Path
D=Path(__file__).resolve().parent;B=D.parent/'published-mode2-x8-g4-original19-runtime190-source-v1-20261009-root'
s=(B/'launch-wrapper.py').read_text().replace('import os,sys,json,resource,hashlib,stat','import os,sys,json,resource,hashlib,stat,fcntl')
s=s.replace("go['maximumLoaderCalls']==190","go['maximumLoaderCalls']==2")
s=s.replace('def main(fd,sealSHA,argv):','def main(fd,sealSHA,ownershipFD,argv):')
s=s.replace(" checked(pr['loaderArtifact']['path'],pr['loaderArtifact']);checked(pr['interpreter']['path'],pr['interpreter'])"," checked(pr['interpreter']['path'],pr['interpreter'])")
s=s.replace(' seal=json.loads(sealBytes);admit(argv,pr,seal,sp,sealSHA)'," seal=json.loads(sealBytes);admit(argv,pr,seal,sp,sealSHA)\n from run import diagnostic_loader\n diagnostic_loader(json.loads(Path(seal['rootGO']['path']).read_bytes()),pr)\n assert type(ownershipFD)is int and ownershipFD>4 and fd!=4 and ownershipFD!=fd\n try:fcntl.fcntl(4,fcntl.F_GETFD)\n except OSError as ex:assert ex.errno==9,'fixed FD4 must be absent'\n else:raise AssertionError('FD4 collision')\n assert fcntl.fcntl(ownershipFD,fcntl.F_GETFL)&os.O_NONBLOCK\n os.dup2(ownershipFD,4,inheritable=True);os.close(ownershipFD)")
s=s.replace("sys.argv[5]=='--'","sys.argv[5]=='--ownership-fd'and sys.argv[7]=='--'").replace('len(sys.argv)>=7','len(sys.argv)>=9').replace('main(int(sys.argv[2]),sys.argv[4],sys.argv[6:])','main(int(sys.argv[2]),sys.argv[4],int(sys.argv[6]),sys.argv[8:])')
(D/'launch-wrapper.py').write_text(s)
