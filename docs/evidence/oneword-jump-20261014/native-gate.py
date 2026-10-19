from pathlib import Path
import struct,json,hashlib,importlib.util
s=importlib.util.spec_from_file_location('utils',Path(__file__).with_name('native-utils.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def audit(old,new):
 A,ae=m.payload(old);B,be=m.payload(new);assert ae==be and len(A)==len(B)
 assert Path(old['source']['path']).read_bytes()==Path(new['source']['path']).read_bytes()
 if A==B:return dict(status='WHOLE_IDENTITY',changed=False)
 pool,entries=m.source_pool(Path(new['source']['path']).read_bytes());end=len(A)-len(pool);assert end%4==0
 if pool:assert A[end:]==B[end:]==pool
 loader=Path(__file__).with_name('trusted-loader-abi.c'); ls=loader.read_text();assert hashlib.sha256(loader.read_bytes()).hexdigest()=='f44b50995a0e45db4be35244da34dd61538a484c7d5ea2f15f7f5a73d9daa8c3'
 a=struct.unpack('<'+'I'*(end//4),A[:end]);b=struct.unpack('<'+'I'*(end//4),B[:end]);roots={x[0]for x in ae.values()};refs=[];hostCalls=[]
 for i,z in enumerate(a):
  r=m.ref(z,i*4)
  if r:
   roots.add(r[1]);refs.append(dict(pc=i*4,kind=r[0],target=r[1]));assert m.ref(b[i],i*4)==r or(z==0x14000002 and b[i]==0xd503201f and b[i+1]==0xd503201f)
  if z&0xfffffc1f in [0xd61f0000,0xd63f0000]:
   assert z==0xd63f0200 and i>=2,('UNKNOWN_INDIRECT_CONTROL',i*4)
   ld=a[i-1]; assert ld&~0x3ffc00==0xf9400010
   slot=(ld>>10&4095)*8;field={56:'pair_new',144:'string_code_point_at',200:'vector_alloc'}.get(slot);assert field,('UNKNOWN_HOST_VTABLE_SLOT',i*4,slot)
   assert f'offsetof(struct kexe_context_v11, {field}) == {slot}'in ls
   assert f'shared->context.{field} = checked_{field};'in ls
   context=a[i-2];saved=None
   if context!=0xaa0703e0:
    assert context&~0x3ffc00==0xf94003e0
    cslot=(context>>10&4095)*8;store=0xf90003e7|((cslot//8)<<10)
    starts=[j for j in range(i-2)if a[j]==0xa9bf7bfd];assert starts;root=max(starts)
    assert a[root+1]==0x910003fd and a[root+2]&0xffc003ff==0xd10003ff
    F=a[root+2]>>10&4095;assert cslot==F-8
    saves=[j for j in range(root+3,min(root+20,i-2))if a[j]==store];assert len(saves)==1
    # Context reserved slot belongs to original canonical frame, and every
    # SP-using memory or arithmetic instruction through this call keeps SP.
    for j in range(root+3,i-2):
     w=a[j];assert not(w&0xff00001f in [0x9100001f,0xd100001f])
     assert w&0xffc003e0 not in [0xa98003e0,0xa88003e0,0xa8c003e0]
    saved=dict(frameRoot=root*4,frameBytes=F,contextSlotBytes=cslot,savePC=saves[0]*4)
   hostCalls.append(dict(pc=i*4,slotBytes=slot,loaderField=field,contextReloadOwner=saved,unchangedThreeWordCall=True,targetIsPinnedCheckedHostFunction=True))
 sites=[];changed={i for i,(z,v)in enumerate(zip(a,b))if z!=v};covered=set()
 for i in sorted(changed):
  if i in covered:continue
  assert a[i]==0x14000002 and i+2<len(a) and b[i]==b[i+1]==0xd503201f,(i*4,hex(a[i]),hex(b[i]))
  assert (i+1)*4 not in roots,('ENTRY_TO_SKIPPED_WORD',i*4,a[i+1])
  assert i+1 not in covered and i not in covered
  covered.update([i,i+1]);sites.append(dict(branchPC=i*4,skippedPC=(i+1)*4,branchTarget=(i+2)*4,skippedWord=hex(a[i+1]),originalUnconditional=True,noAlternateEntry=True,allRegistersNZCVMemoryFuelTrapAndLayoutUnchanged=True))
 assert sites and changed<=covered and all(a[i]!=b[i]or a[i]==0xd503201f for i in covered)
 return dict(status='PASS_SAME_LAYOUT_B_PLUS2_DEAD_SKIP_TWO_NOP_COMPLETE_ROOTS',changed=True,sites=sites,refs=refs,hostCalls=hostCalls,sourcePoolBytes=len(pool),exports=ae,completeOtherBytesIdentity=True,proof='An unconditional direct B+2 has no side effect and skips the next word. All unchanged direct/address/literal/export roots exclude entering the skipped word. Replacing both by NOP reaches the same target with exactly the same registers/NZCV/memory/fuel. All other bytes including charges/publications/traps and checked host calls stay identical. Frozen code root inventory.',adopted=False,performanceMeasured=False)
