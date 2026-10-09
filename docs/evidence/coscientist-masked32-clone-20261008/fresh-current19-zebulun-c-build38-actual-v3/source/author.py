from pathlib import Path
import json,hashlib
D=Path(__file__).resolve().parent;P=Path('/Users/junkawasaki/github/workspaces/codex/tc-hft-current19-transfer-packet-manifest-source-v1-20261009-dense')
def rec(b):return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
m=json.loads((P/'manifest.json').read_text());ip={}
for r in m['files']:
 if r['role']=='original-C-owned-source-or-header':
  b=Path(r['source']).read_bytes();assert rec(b)=={k:r[k]for k in ('bytes','sha256')}
  p=D/r['relativePath'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b);ip[r['relativePath']]=rec(b)
recipes=json.loads((P/'C-recipes.json').read_text());(D/'recipes.json').write_text(json.dumps(recipes,indent=2)+'\n')
pr={'status':'SOURCE_ONLY_CURRENT19_ZEBULUN_C_BUILD38_V3','sourceReviewStatus':'PASS_SOURCE_ONLY_CURRENT19_ZEBULUN_C_BUILD38_V3','rootGOStatus':'GO_CURRENT19_ZEBULUN_C_BUILD38_ONCE_V3','outputRelative':'C-build-outputs','maximumChildCalls':38,'dependencyCalls':19,'buildCalls':19,'guestCalls':0,'consumerCalls':0,'timingCalls':0,'noRetry':True,'C2':False,'exactInputFiles':len(ip),'exactInputLogicalBytes':sum(r['bytes']for r in ip.values()),'maximumInputFiles':128,'maximumInputBytes':2097152,'maximumDynamicHeaders':4096,'maximumDynamicHeaderBytes':67108864,'maximumSingleHeaderBytes':8388608,'maximumCampaignSeconds':7200,'dependencyTimeoutSeconds':60,'buildTimeoutSeconds':180,'cleanupSeconds':30,'CPUSoftSeconds':180,'CPUHardSeconds':181,'maximumRegularFileBytes':16777216,'maximumRawBytesPerStream':1048576,'maximumArtifactBytes':16777216,'maximumMetadataBytes':8388608,'controlledOutputReservationBytes':1073741824,'environment':{'PATH':'/usr/bin:/bin:/usr/sbin:/sbin','LANG':'C','LC_ALL':'C','TZ':'UTC','DEVELOPER_DIR':'/Library/Developer/CommandLineTools'},'host':'zebulun@100.66.28.79','targetMachine':'arm64','hostIdentityAtGORequired':True,'hostBindingIsFreshSelectionNotPerformanceProof':True,'dependencyDomain':'owned packet inputs, canonical exact GO SDK or Clang resource roots only','completionStatus':'COMPLETE_CURRENT19_FRESH_C_BUILD38_SOURCE_IDENTITY_ONLY','expectedIndependentPerWorkloadStatus':'PASS_INDEPENDENT_FRESH_CURRENT19_C_BUILD_SOURCE_IDENTITY_ONLY'}
(D/'preregistration.json').write_text(json.dumps(pr,indent=2)+'\n');(D/'input-pins.json').write_text(json.dumps(ip,indent=2)+'\n')
