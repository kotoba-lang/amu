"""Pure numeric sample-row contract; no group queries or file writes."""
def row(sample,monotonic_ns,ownedPID,birth):
 assert type(ownedPID)is int and 0<ownedPID<2**31
 assert set(sample)=={'sample','ownedPGID','metric','aggregateBytes','thresholdBytes','members','hardMemoryCapEstablished'}
 assert type(sample['sample'])is int and 1<=sample['sample']<=2048 and type(sample['ownedPGID'])is int and sample['ownedPGID']==ownedPID
 assert type(monotonic_ns)is int and 0<=monotonic_ns<2**64
 assert type(sample['members'])is list and 1<=len(sample['members'])<=2
 numbers=[]
 for member in sample['members']:
  assert set(member)=={'pid','start','exit','physicalFootprintBytes','uuid'} and type(member['uuid'])is str and len(member['uuid'])==32 and all(c in '0123456789abcdef'for c in member['uuid'])
  pid,start,foot=member['pid'],member['start'],member['physicalFootprintBytes']
  assert type(pid)is int and 0<pid<2**31 and type(start)is int and 0<start<2**64 and type(foot)is int and 0<=foot<2**64
  assert member.get('exit')==0
  numbers.append([pid,start,foot])
 assert len({v[0]for v in numbers})==len(numbers) and sample['metric']=='sum-ri_phys_footprint' and sample['hardMemoryCapEstablished'] is False
 assert type(sample['aggregateBytes'])is int and type(sample['thresholdBytes'])is int and 0<=sample['aggregateBytes']<=sample['thresholdBytes']==4294967296 and sample['aggregateBytes']==sum(v[2]for v in numbers)
 owners=[v for v in numbers if v[0]==ownedPID];assert len(owners)==1
 if birth:assert birth=={'pid':ownedPID,'birth':owners[0][1]}
 return [sample['sample'],monotonic_ns,ownedPID,numbers],{'pid':ownedPID,'birth':owners[0][1]}
