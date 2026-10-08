"""Pure finite event-policy model, not a runtime driver or OS fixture."""
def trace(events,cap=8,drain_ticks=2):
 state={'authority':True,'waitEntered':False,'memoryAdmission':True,'raw':b'','truncated':False,'EOF':False,'remainingDrain':None,'qualification':False,'operations':[],'closure':'unavailable'}
 for event,value in events:
  if event=='sample-failure':
   state['memoryAdmission']=False;state['authority']=False;state['remainingDrain']=drain_ticks
  elif event=='data':
   if state['remainingDrain']!=0 and not state['EOF']:
    room=cap-len(state['raw']);state['raw']+=value[:room];state['truncated']|=len(value)>room
  elif event=='tick':
   if state['remainingDrain']is not None:state['remainingDrain']=max(0,state['remainingDrain']-1)
  elif event=='EOF':state['EOF']=True
  elif event=='signal':
   assert state['authority'] and not state['waitEntered'];state['operations'].append('signal')
  elif event=='wait':
   assert not state['waitEntered'];state['authority']=False;state['waitEntered']=True;state['closure']=value;state['operations'].append('wait')
  elif event=='group-query':
   assert state['authority'] and not state['waitEntered'];state['operations'].append('group-query')
  elif event=='complete':
   state['qualification']=state['memoryAdmission'] and state['EOF'] and not state['truncated'] and state['closure']=='closed0'
  else:raise AssertionError(event)
 return state
def controls():
 q=trace([('sample-failure',None),('data',b'answer'),('EOF',None),('wait','closed0'),('complete',None)])
 assert q['raw']==b'answer' and not q['qualification']
 assert trace([('sample-failure',None),('tick',None),('tick',None),('data',b'late')])['raw']==b''
 assert trace([('data',b'abcdefghijk')])['raw']==b'abcdefgh'
 assert trace([('data',b'abcdefghijk')])['truncated']
 assert not trace([('EOF',None),('wait','uncertain'),('complete',None)])['qualification']
 bad=[[('sample-failure',None),('signal',None)],[('sample-failure',None),('group-query',None)],[('wait','closed0'),('signal',None)],[('wait','uncertain'),('group-query',None)],[('wait','uncertain'),('wait','closed0')]]
 for events in bad:
  try:trace(events)
  except AssertionError:pass
  else:raise AssertionError('ownership mutation accepted')
 return {'status':'PASS_PURE_POLICY_MODEL_ONLY','negativeOwnershipTraces':len(bad),'positiveCaptureBoundaries':5,'nativeCalls':0,'processAPICalls':0,'threadedFDOwnershipQualified':False}
