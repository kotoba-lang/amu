from pathlib import Path
import subprocess,json,hashlib,tarfile
W=Path(__file__).parent;R=Path('/Users/junkawasaki/github/wt/codex/seed-copy-chain48-20261014')
def git(*args):return subprocess.check_output(['git',*args],cwd=R)
def sha(b):return hashlib.sha256(b).hexdigest()
pr=json.loads((W/'pr1313-merged.json').read_text());assert pr['state']=='MERGED'and pr['headRefOid']=='cdcca3523f1208abfb3bdfef0236e157f323e1b7'
head=git('rev-parse','origin/main').decode().strip();assert head==pr['mergeCommit']['oid']
for commit in ['cdcca3523f1208abfb3bdfef0236e157f323e1b7','ffa4cfc1923b50b545c782c5b8545ba290c1c8b2']:
 assert subprocess.run(['git','merge-base','--is-ancestor',commit,head],cwd=R).returncode==0
def data(p):return git('show',head+':'+p)
receipt=json.loads(data('seed/adoption-20261012.json'));assert receipt['sourceUnitySHA256']=='233cafbff4e01c23c3a3dab38c256483c08a3477df7f9c15cbf3f5f333d211a6'
for x in receipt['sourceFiles']:
 b=data(x['path']);assert len(b)==x['bytes']and sha(b)==x['sha256']
manifest=[x for x in data('seed/MANIFEST').decode().splitlines()if x and not x.startswith('#')];assert len(manifest)==16;assert sha(b''.join(data(x)+b'\n'for x in manifest))==receipt['sourceUnitySHA256']
b=data('seed/bootstrap/adopted-20261012.bin');k=data('seed/bootstrap/adopted-20261012.kseed');h,p=k.split(b'\n\n',1);assert p==b and h.decode().splitlines()[1:]==['main 0 0'];assert sha(b)==receipt['nativeImageSHA256']=='87efe842dc0389f0ba7d476fcf034f6820483632df61fad53b474a2297e3e345';assert sha(k)==receipt['bootstrapContainerSHA256']
assert sha(data('seed/bootstrap/adopted-loader-20261012.c'))==receipt['loaderSourceSHA256']=='f44b50995a0e45db4be35244da34dd61538a484c7d5ea2f15f7f5a73d9daa8c3'
for x in receipt['evidenceDigests']:
 if 'path'in x:z=data(x['path']);assert len(z)==x['bytes']and sha(z)==x['sha256']
gold=json.loads(data(receipt['policyNativeGoldenPath']));assert len(gold['images'])==19 and gold['producerNativeSHA256']==sha(b)
assert sha(data(receipt['policyNativeGoldenPath']))==receipt['policyNativeGoldenSHA256'];assert sha(data(receipt['policyNativeGoldenArchivePath']))==receipt['policyNativeGoldenArchiveSHA256']
checks=json.loads((W/'pr1313-final-checks.json').read_text());assert checks['headRefOid']==pr['headRefOid']and len(checks['statusCheckRollup'])==20 and all(x['status']=='COMPLETED'and x['conclusion']=='SUCCESS'for x in checks['statusCheckRollup'])
r=dict(status='PASS_REMOTE_MAIN_PR1313_SOURCE20_UNITY16_NATIVE_CONTAINER_LOADER_GOLDEN19_ALL20CI_ANCESTRY_AND_EVIDENCE_READBACK',main=head,pullRequest=pr['url'],PRHead=pr['headRefOid'],sourceCommit='ffa4cfc1923b50b545c782c5b8545ba290c1c8b2',sourceUnitySHA256=receipt['sourceUnitySHA256'],nativeSHA256=sha(b),containerSHA256=sha(k),loaderSourceSHA256=receipt['loaderSourceSHA256'],adopted=True,performanceGoalAchieved=False,officialEmbenchScore=False,pairedRound116ObservedShorterPercent=3.4648327176549087,individualPairs=[0.9769918606651077,0.9533423206591826],stableStatisticalGainClaim=False,source20=True,unity16=True,all20CI=True,golden19=True,mergeAncestry=True)
(W/'main-integration-receipt.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'],head,flush=True)
