"""Strict observation gate for future emitter candidates; diagnostic tooling.
This compares observations, not arbitrary program semantics or completeness of
the observer. Callers must independently qualify their observation adapter.
"""
import copy
import json
import re

FIELDS = {'result','exit','trap','trapSite','fuel','resources','arena','effects'}

def validate(before, after):
    fields={'format','sourceSha256','semanticProfile','cases'}
    for document in [before,after]:
        if set(document) != fields or document['format'] != 'amu.translation-observations/v1':
            raise ValueError('unsupported observation format')
        if not re.fullmatch('[0-9a-f]{64}',document['sourceSha256']) or not document['semanticProfile']:
            raise ValueError('source hash and semantic profile required')
        if not document['cases']:raise ValueError('empty observation set')
        for case,observation in document['cases'].items():
            if not case or set(observation) != FIELDS:
                raise ValueError('incomplete or unknown observation fields')
            if not isinstance(observation['effects'],list) or not isinstance(observation['arena'],list):
                raise ValueError('ordered effects and arena observations required')
    if before['sourceSha256'] != after['sourceSha256'] or before['semanticProfile'] != after['semanticProfile']:
        raise ValueError('source or semantic profile changed')
    if set(before['cases']) != set(after['cases']):raise ValueError('case coverage changed')
    for case in before['cases']:
        for field in FIELDS:
            old=json.dumps(before['cases'][case][field],sort_keys=True,allow_nan=False)
            new=json.dumps(after['cases'][case][field],sort_keys=True,allow_nan=False)
            if old != new:
                raise ValueError('translation difference: '+case+'/'+field)
    return len(before['cases'])

def controls():
    # Synthetic adapter controls, expressly not actual guest observations.
    original={'format':'amu.translation-observations/v1','sourceSha256':'0'*64,
              'semanticProfile':'fixture-wrapping-i64',
              'cases':{'fixture':{'result':7,'exit':0,'trap':None,'trapSite':None,
                                'fuel':2,'resources':{'vectors':1},'arena':[7],
                                'effects':['store','read']}}}
    assert validate(original,copy.deepcopy(original))==1
    refused=[]
    for field,value in [('result',8),('exit',120),('trap','bounds'),('trapSite',4),
                        ('fuel',3),('resources',{'vectors':2}),('arena',[8]),
                        ('effects',['read','store'])]:
        mutant=copy.deepcopy(original);mutant['cases']['fixture'][field]=value
        try:validate(original,mutant)
        except ValueError:refused.append(field)
        else:raise AssertionError('changed observation accepted')
    for label in ['missing-field','missing-case','source-change']:
        mutant=copy.deepcopy(original)
        if label=='missing-field':del mutant['cases']['fixture']['fuel']
        elif label=='missing-case':mutant['cases']={}
        else:mutant['sourceSha256']='1'*64
        try:validate(original,mutant)
        except ValueError:refused.append(label)
        else:raise AssertionError('incomplete observation accepted')
    return {'syntheticAdapterControls':True,'matchingCases':1,'mutationsRefused':refused,
            'productCandidateValidated':False}
