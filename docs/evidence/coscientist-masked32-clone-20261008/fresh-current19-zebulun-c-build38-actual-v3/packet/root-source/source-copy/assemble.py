"""Pure registration assembler. Inputs are exact frozen source, not remote artifacts."""
from pathlib import Path
import json,hashlib
from packet import validate
D=Path(__file__).resolve().parent;W=D.parent
CORE=W/'tc-hft-current19-transfer-packet-manifest-source-v1-20261009-dense'
CONSUMER=W/'tc-hft-current17-timing-consumer-source-v2-20261009-crc'
def assemble(cbuild):
 cbuild=Path(cbuild);core=json.loads((CORE/'manifest.json').read_text());out=[]
 def add(p,dest,owner):
  b=p.read_bytes();out.append({'source':str(p),'relativePath':dest,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'owner':owner})
 for x in core['files']:out.append(dict({k:x[k]for k in ('source','relativePath','bytes','sha256')},owner='core156'))
 sp=json.loads((CONSUMER/'source-pins.json').read_text())
 for n,r in sp.items():
  add(CONSUMER/n,'source/consumer/'+n,'consumerV2');assert out[-1]['bytes']==r['bytes'] and out[-1]['sha256']==r['sha256']
 add(CONSUMER/'source-pins.json','control/consumer-source-pins.json','consumerV2')
 for n in ('manifest.json','C-recipes.json','source-pins.json'):add(CORE/n,'control/core-'+n,'core156')
 # C-build helper registry explicitly controls active source; never duplicates its inputs/ or any SDK tree.
 bsp=json.loads((cbuild/'source-pins.json').read_text())
 for n,r in bsp.items():
  assert '/'not in n and n not in ('.','..')
  add(cbuild/n,'source/C-build/'+n,'freshC38');assert out[-1]['bytes']==r['bytes'] and out[-1]['sha256']==r['sha256']
 for n in ('source-pins.json','input-pins.json','freeze.json'):add(cbuild/n,'source/C-build/'+n,'freshC38')
 # Exact 53 source inputs are already core members; verify destination and bytes, never duplicate.
 bank={r['relativePath']:r for r in out}
 for n,r in json.loads((cbuild/'input-pins.json').read_text()).items():assert n in bank and bank[n]['bytes']==r['bytes'] and bank[n]['sha256']==r['sha256']
 for n in ('install.py','packet.py'):add(D/n,'source/install/'+n,'installerV3')
 m={'schema':'CURRENT19_CORE_CONSUMER_CBUILD_PACKET_V1','remoteRoot':'/Users/zebulun/github/workspaces/codex/tc-hft-current19-quiet-c-packet-v3-20261009-root','files':out,'exactFiles':len(out),'exactLogicalBytes':sum(x['bytes']for x in out),'owners':['core156','consumerV2','freshC38','installerV3'],'executionCredit':False}
 validate(m);return m
if __name__=='__main__':
 import sys
 assert len(sys.argv)==2
 print(json.dumps(assemble(sys.argv[1]),indent=2))
