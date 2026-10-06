"""Independent SIR cases for closed vector descriptor chains (bootstrap tests)."""

def add_fixtures(fx, run, MIN, MAX, s64):
    writer=[('LABEL','lv_w_entry'),('LGET',0,1),('LGET',1,2),('LGET',2,3),('RT','RT-VECTOR-ASSOC-IN-PLACE',0,3),('RET',0)]
    fx('lv_writer',3,3,writer)
    fx('lv_charged_writer',3,3,[('FUEL',)]+[tuple('lv_cw_entry' if a=='lv_w_entry' else a for a in op) for op in writer])
    fx('lv_sink',1,1,[('LGET',0,1),('CONST',1,0),('RT','RT-VECTOR-AT',0,2),('LGET',0,1),('RET',0)])
    fx('lv_finish',1,2,[('FUEL',),('LGET',0,1),('CONST',1,0),('RT','RT-VECTOR-AT',0,2),('CONST',1,1),('BIN','BOP-ADD',0),('LSET',2,0),('LGET',0,1),('CONST',1,0),('LGET',2,2),('RT','RT-VECTOR-ASSOC-IN-PLACE',0,3),('LGET',0,1),('CALL','lv_sink',0,1),('RET',0)])
    prefix=[('FUEL',),('LGET',0,1),('CONST',1,0),('RT','RT-VECTOR-AT',0,2),('LSET',2,0),('LGET',0,1),('CONST',1,1),('RT','RT-VECTOR-AT',0,2),('LSET',3,0),('LGET',0,1),('LGET',1,2),('RT','RT-VECTOR-AT',0,2)]
    loadwrite=[('LSET',2,0),('LGET',0,1),('LGET',1,3),('LGET',2,2)]
    variants=[('normal','lv_writer',[]),('zero','lv_writer',[]),('direct',None,[]),('branch','lv_writer',[('BR','lv_branch_join'),('LABEL','lv_branch_join')]),('charged','lv_charged_writer',[]),('changed','lv_writer',[('LGET',0,1),('CONST',1,6),('RT','RT-VECTOR-AT',0,2),('LSET',1,0)]),('ns4','lv_writer',[('CONST',0,91),('LSET',4,0)]),('dp4','lv_writer',[]),('quot0','lv_writer',[]),('quotneg','lv_writer',[]),('quot3','lv_writer',[]),('twice','lv_writer',[]),('transfer_new','lv_writer',[]),('transfer_invalid','lv_writer',[]),('write_first','lv_writer',[])]
    for kind,target,extra in variants:
     arith=[('CONST',1,0 if kind=='quot0' else -1 if kind=='quotneg' else 3 if kind=='quot3' else 7),('BIN','BOP-QUOT' if kind.startswith('quot') else 'BOP-ADD',0)]
     head=prefix+[('CONST',3,17)] if kind=='dp4' else prefix
     if kind=='ns4':extra=[('CONST',2,91),('LSET',4,2)]
     ops=head+arith+loadwrite
     if kind=='zero':ops[-1]=('CONST',2,0)
     if kind=='changed':ops +=extra+[('LGET',0,1),('LGET',1,3),('LGET',2,2)]
     else:ops +=extra+([('LGET',2,2)] if kind=='ns4' else [])
     ops += [('RT','RT-VECTOR-ASSOC-IN-PLACE',0,3)] if target is None else [('CALL',target,0,3)]
     if kind=='twice':ops += [('LGET',0,1),('CONST',1,0),('CONST',2,-99),('CALL','lv_writer',0,3)]
     if kind in ['transfer_new','transfer_invalid']:ops += [('LGET',0,1),('CONST',1,6 if kind=='transfer_new' else 4),('RT','RT-VECTOR-AT',0,2)]
     if kind=='write_first':ops=[('FUEL',),('LGET',0,1),('CONST',1,2),('CONST',2,7),('CALL','lv_writer',0,3)]
     ops += [('CALL','lv_finish',0,1),('RET',0)];fx('lv_'+kind,1,4 if kind=='ns4' else 3,ops)
     driver=[('FUEL',),('CONST',0,13),('CONST',1,17),('CONST',2,19),('CONST',3,23),('VEC',0,4),('LSET',4,0),('LGET',0,1),('LGET',1,2),('CONST',2,MIN),('CONST',3,MAX),('CONST',4,-1),('CONST',5,42),('LGET',6,4),('VEC',0,7),('CALL','lv_'+kind,0,1),('LGET',1,3),('RT','RT-VECTOR-AT',0,2),('RET',0)]
     fx('lv_'+kind+'_driver',3,4,driver)
    
    variants_chain=variants
    
    specs=[('BIN',x) for x in ['BOP-ADD','BOP-SUB','BOP-MUL','BOP-QUOT','BOP-AND','BOP-OR','BOP-XOR','BOP-SHL','BOP-USHR','BOP-SSHR']]+[('CMP',x) for x in ['CC-EQ','CC-LT','CC-GT','CC-LE','CC-GE']]+[('UN',x) for x in ['UOP-NOT','UOP-BITNOT']]
    for kind,op in specs:
     name='scratch_'+op.lower().replace('-','_');ops=[('FUEL',),('LGET',0,1),('CONST',1,2),('RT','RT-VECTOR-AT',0,2),('LSET',2,0),('LGET',0,1),('CONST',1,3),('RT','RT-VECTOR-AT',0,2),('LSET',3,0),('LGET',0,2)]
     if kind!='UN':ops += [('LGET',1,3)]
     ops += [(kind,op,0),('LSET',2,0),('LGET',0,1),('CONST',1,5),('LGET',2,2),('RT','RT-VECTOR-ASSOC-IN-PLACE',0,3),('LGET',0,1),('CALL','lv_finish',0,1),('RET',0)];fx(name,1,3,ops)
     driver=[('FUEL',),('CONST',0,13),('CONST',1,17),('CONST',2,19),('CONST',3,23),('VEC',0,4),('CONST',0,0),('CONST',1,0),('LGET',2,1),('LGET',3,2),('CONST',4,0),('CONST',5,0),('CONST',6,1),('VEC',0,7),('CALL',name,0,1),('CONST',1,5),('RT','RT-VECTOR-AT',0,2),('RET',0)];fx(name+'_driver',2,2,driver)
    
    read=[('LGET',0,1),('CONST',1,0),('RT','RT-VECTOR-AT',0,2)]
    other=[('LGET',0,1),('CONST',1,6),('RT','RT-VECTOR-AT',0,2),('LSET',2,0)]
    fx('sv_cold',1,2,[('FUEL',),('LGET',0,1),('CALL','lv_finish',0,1),('RET',0)])
    variants=['no_read','warm_cold','diamond_tail','diamond_read','alias_set','other_read_root','other_read_back','invalid_root']
    for kind in variants:
     target='sv_cold' if kind in ['no_read','warm_cold'] else 'lv_finish';body=[('FUEL',)]
     if kind=='warm_cold':body+=read
     if kind.startswith('diamond'):
      body+=read+[('BRZ',0,'sv_'+kind+'_zero')]+other+[('LGET',0,2),('LSET',1,0),('BR','sv_'+kind+'_join'),('LABEL','sv_'+kind+'_zero'),('LABEL','sv_'+kind+'_join')]
      if kind=='diamond_read':body+=read
     if kind=='alias_set':body+=read+[('LGET',0,1),('LSET',1,0)]
     if kind.startswith('other_read'):body+=other+[('LGET',0,2),('CONST',1,0),('RT','RT-VECTOR-AT',0,2)]+(read if kind=='other_read_back' else [])
     if kind=='invalid_root':body+=[('LGET',0,1),('CONST',1,4),('RT','RT-VECTOR-AT',0,2),('LSET',1,0)]
     body +=[('LGET',0,1),('CALL',target,0,1),('RET',0)];fx('sv_'+kind,1,2,body)
     driver=[('FUEL',),('CONST',0,13),('CONST',1,17),('CONST',2,19),('CONST',3,23),('VEC',0,4),('LSET',2,0),('LGET',0,1),('CONST',1,0),('CONST',2,MIN),('CONST',3,MAX),('CONST',4,-1),('CONST',5,42),('LGET',6,2),('VEC',0,7),('CALL','sv_'+kind,0,1),('CONST',1,0),('RT','RT-VECTOR-AT',0,2),('RET',0)];fx('sv_'+kind+'_driver',1,2,driver)
    
    wrap=s64
    def oracle(kind,a,b,probe,fuel):
     other=[13,17,19,23];inp=[a,b,MIN,MAX,-1,42,1];result='trap';remaining=max(fuel-2,0)
     arith_ok=True;read_ok=kind=='write_first' or 0<=a<7
     if fuel>=2 and read_ok:
      if kind=='write_first':v=7;wi=2
      else:
       v=inp[a];wi=b
       if kind=='quot0':arith_ok=False
       elif kind=='quotneg':arith_ok=v!=MIN;v=wrap(-v)
       elif kind=='quot3':v=(abs(v)//3)*(-1 if v<0 else 1)
       else:v=0 if kind=='zero' else wrap(v+7)
      if arith_ok:
       charges=3 if kind=='charged' else 2;remaining=max(fuel-charges,0);dest=other if kind=='changed' else inp
       if fuel>=charges and 0<=wi<len(dest):
        dest[wi]=v
        if kind=='twice':dest[0]=-99
        # Final parameter fetch occurs before the finish charge. transfer_new
        # index6 is valid, transfer_invalid index4 is valid; loaded -1 traps
        # at finish's original checked read after its charge.
        handle=inp[6] if kind=='transfer_new' else inp[4] if kind=='transfer_invalid' else (1 if dest is other else 2)
        target=other if handle==1 else inp if handle==2 else None
        remaining=max(fuel-charges-1,0)
        if fuel>=charges+1 and target is not None:
         target[0]=wrap(target[0]+1)
         if 0<=probe<len(target):result=target[probe]
     return result,remaining,other+inp
    pairs=[(0,0),(0,1),(1,1),(2,2),(2,3),(3,2),(4,0),(5,6),(6,5),(2,6),(6,6),(-1,0),(7,0),(MIN,0),(MAX,0),(2,-1),(2,7),(2,MIN),(2,MAX),(2,4),(2,5)]
    
    for kind,_,_ in variants_chain:
     for a,b in pairs:
      for probe in [0,2,6,-1,7]:
       for fuel in [1,2,3,4,5,(1<<53)-1]:
        want,remaining,items=oracle(kind,a,b,probe,fuel)
        run('lv_'+kind+'_driver',[a,b,probe],want,fuel=fuel,fuel_remaining=remaining)
    wrap=s64
    def value(op,a,b):
     if op=='BOP-QUOT':return None if b==0 or (a==MIN and b==-1) else (abs(a)//abs(b))*(-1 if (a<0)!=(b<0) else 1)
     f={'BOP-ADD':lambda:a+b,'BOP-SUB':lambda:a-b,'BOP-MUL':lambda:a*b,'BOP-AND':lambda:a&b,'BOP-OR':lambda:a|b,'BOP-XOR':lambda:a^b,'BOP-SHL':lambda:a<<(b&63),'BOP-USHR':lambda:(a&((1<<64)-1))>>(b&63),'BOP-SSHR':lambda:a>>(b&63),'CC-EQ':lambda:int(a==b),'CC-LT':lambda:int(a<b),'CC-GT':lambda:int(a>b),'CC-LE':lambda:int(a<=b),'CC-GE':lambda:int(a>=b),'UOP-NOT':lambda:a^1,'UOP-BITNOT':lambda:~a};return wrap(f[op]())
    pairs=[(0,0),(0,1),(1,1),(-1,1),(MIN,-1),(MIN,MAX),(MAX,MIN),(MAX,2),(MIN,2),(7,3),(-7,3),(7,-3),(-7,-3),(1,63),(MIN,64),(-1,65),(MAX,-64)];
    for kind,op in specs:
     name='scratch_'+op.lower().replace('-','_')+'_driver'
     for a,b in pairs:
      v=value(op,a,b)
      for fuel in [1,2,3,4,(1<<53)-1]:
       result='trap';remaining=max(fuel-2,0)
       if fuel>=2 and v is not None:
        remaining=max(fuel-3,0)
        if fuel>=3:result=v
       run(name,[a,b],result,fuel=fuel,fuel_remaining=remaining)
    for kind in variants:
     for flag in [-1,0,1,MIN,MAX]:
      for fuel in [1,2,3,4,5,(1<<53)-1]:
       charge=4 if kind in ['no_read','warm_cold'] else 3
       result='trap'
       if fuel>=charge and kind!='invalid_root':result=14 if kind.startswith('diamond') and flag!=0 else s64(flag+1)
       run('sv_'+kind+'_driver',[flag],result,fuel=fuel,fuel_remaining=max(0,fuel-charge))
