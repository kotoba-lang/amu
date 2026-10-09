"""Offline individual COMPLETE30 diagnostics; never promotes subset aggregates."""
from pathlib import Path
import hashlib, importlib.util, json, math
O=Path(__file__).resolve().parent
C=O.parent/'vector-leaf-straight-read-cache-current19-timing-go-v2-root/collected'
A=O.parent/'vector-leaf-straight-read-cache-current19-timing-actual-review-v2-independent'
EXPECTED_AUDIT='e77bb1e2cad6598ea677c754e31db7ecdbac0f6177410be866a5101aaea74a25'
EXPECTED_PURE_HELPER='89eab8f3dba7bcb061f6f99ea300d3fef7bece6de849e4c79c5c451dd8b74f44'
def load(p):return json.loads(Path(p).read_bytes())
def h(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def need(v,s):
    if not v:raise ValueError(s)
def reasons(q,en):
    return [key for key,v in [('intervalBelow50ms',q['elapsedNanoseconds']<50000000),('beforeLoadAbove4',en['loadBefore']>4),('afterLoadAbove4',en['loadAfter']>4),('backgroundIdleBelow90pct',en['activity']['estimatedBackgroundIdlePercent']<90)]if v]
def count_reasons(counter,keys):
    for k in keys:counter[k]=counter.get(k,0)+1
def main():
    need(h(A/'report.json')==EXPECTED_AUDIT,'exact independently accepted partial audit')
    audit=load(A/'report.json');need(audit['status']=='PASS_SAVED_PARTIAL_LC_CURRENT19_TIMING_V2_NO_FIXED19_TIMING_ACCEPTANCE' and audit['completedWorkloads']==11 and audit['allClosed']is True,'prerequisite saved partial PASS')
    need(h(A/'validate_saved.py')==EXPECTED_PURE_HELPER,'frozen independent pure formulas')
    for p,r in load(O/'input-pins.json').items():need(Path(p).is_file() and not Path(p).is_symlink() and Path(p).stat().st_size==r['bytes'] and h(p)==r['sha256'],'diagnostic input pin')
    spec=importlib.util.spec_from_file_location('independent_saved_formulas',A/'validate_saved.py');pure=importlib.util.module_from_spec(spec);spec.loader.exec_module(pure)
    pr=load(C/'source/preregistration.json');envs={}
    for p in sorted((C/'timing/children').glob('*/envelope.json')):envs[h(p)]=(p,load(p))
    outputs=[];partials=[]
    for entry in pr['entries']:
        name=entry['workload'];state=load(C/'timing'/(name+'-state.json'));calreasons={};rejections={};cal=[]
        def telemetry(rawid):
            p,en=envs[rawid];q=load(p.parent/'stdout');return q,en
        for event in state['calibration']:
            q,en=telemetry(event['rawId']);rs=reasons(q,en);need(event['quiet']==(not rs),'independently audited quiet unchanged');count_reasons(calreasons,rs)
            if q['elapsedNanoseconds']<225000000:count_reasons(calreasons,['targetBelow225ms'])
            if q['elapsedNanoseconds']>450000000:count_reasons(calreasons,['targetAbove450ms'])
            cal.append(dict(arm=event['arm'],attempt=event['attempt'],calls=event['calls'],elapsedNs=event['elapsedNs'],quiet=event['quiet'],quietRejectReasons=rs))
        rejected=0
        for triple in state['triples']:
            for arm,event in triple['events'].items():
                q,en=telemetry(event['rawId']);rs=reasons(q,en);need(event['quiet']==(not rs),'quiet event consistency');count_reasons(rejections,rs)
            if not triple['accepted']:rejected+=1
        common=dict(workload=name,status=state['status'],acceptedTriples=len(state['accepted']),attemptedTriples=len(state['triples']),rejectedTriples=rejected,calibration=cal,calibrationReasonCounts=calreasons,measurementArmRejectReasonCounts=rejections)
        if state['status']!='COMPLETE30':
            need(len(state['accepted'])<30,'partial less30');common.update(performanceQualified=False,individualMetrics=None);partials.append(common);continue
        xs=state['accepted'];need(len(xs)==30 and all(set(x)==set(pure.ARMS)for x in xs),'exact independently audited paired30');arms={}
        for arm in pure.ARMS:
            values=[x[arm]for x in xs];m=math.fsum(values)/30;s=math.sqrt(math.fsum((x-m)**2 for x in values)/29);arms[arm]=dict(meanNsPerOriginalBody=m,sampleSDNsPerOriginalBody=s,CV=s/m)
        cis={num+'/candidate':pure.ci([[math.log(x[num]/x['candidate'])for x in xs]],audit['sourcePinsSHA256'],name,num)for num in ('baseline','C')}
        stable=all(x['CV']<=.1 for x in arms.values());b,lc,c=(arms[x]for x in pure.ARMS)
        common.update(arms=arms,allThreeArmsStable=stable,CMeanOverCandidateMean=c['meanNsPerOriginalBody']/lc['meanNsPerOriginalBody'],baselineMeanOverCandidateMean=b['meanNsPerOriginalBody']/lc['meanNsPerOriginalBody'],pairedCI95=cis,individualStableCOrBetter=stable and c['meanNsPerOriginalBody']>=lc['meanNsPerOriginalBody'] and cis['C/candidate']['lower95']>=1,changed=entry['codeChanged'],baselineAdoptionBenefitPredicate=bool(entry['codeChanged'] and stable and b['meanNsPerOriginalBody']/lc['meanNsPerOriginalBody']>=1.05 and b['meanNsPerOriginalBody']-lc['meanNsPerOriginalBody']>b['sampleSDNsPerOriginalBody']+lc['sampleSDNsPerOriginalBody'] and cis['baseline/candidate']['lower95']>=1.05),confidenceScope='individual marginal95; no joint95 confidence',diagnosticOnly=True)
        outputs.append(common)
    need(len(outputs)==11 and len(partials)==8,'all19 coverage')
    report=dict(status='PARTIAL_CAMPAIGN_INDIVIDUAL_COMPLETE30_DIAGNOSTIC_ONLY_NO_GM',independent=True,actualAuditSHA256=EXPECTED_AUDIT,pureFormulaHelperSHA256=EXPECTED_PURE_HELPER,sourcePinsSHA256=audit['sourcePinsSHA256'],fullOriginalWorkloads=19,complete30Workloads=11,partialWorkloads=8,complete30=outputs,partials=partials,fixed19GM=None,subsetGM=None,overall19CGoalClaim=False,timingCampaignQualified=False,partialWorkloadPerformanceQualified=False,officialScore=False,CIDRuntimeEffect=False,productAdopted=False,bootstrapReplicates=20000,reviewerOperationalCalls=0,limitations=['Individual COMPLETE30 metrics from independently audited saved paired rows; no complete19 or subset aggregate promotion.','Eight partial workloads receive counts and rejection causes only, no performance metrics or qualification.','Reject reason counts are per arm and can overlap; they are observed gating failures, not causal explanations.','Root read-only progress probe during active campaign introduced host work; no causal sample attribution or untouched-host claim.','CPU envelope includes process setup, warmup and drain; individual confidence intervals are marginal95, not joint95.'])
    (O/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status=report['status'],complete30=[dict(workload=x['workload'],CMeanOverCandidateMean=x['CMeanOverCandidateMean'],pairedLower95=x['pairedCI95']['C/candidate']['lower95'],pairedUpper95=x['pairedCI95']['C/candidate']['upper95'],CVs={a:y['CV']for a,y in x['arms'].items()},stable=x['allThreeArmsStable'],individualCOrBetter=x['individualStableCOrBetter'])for x in outputs],partials=[{k:x[k]for k in ['workload','status','acceptedTriples','attemptedTriples','calibrationReasonCounts','measurementArmRejectReasonCounts']}for x in partials]),indent=2))
if __name__=='__main__':main()
