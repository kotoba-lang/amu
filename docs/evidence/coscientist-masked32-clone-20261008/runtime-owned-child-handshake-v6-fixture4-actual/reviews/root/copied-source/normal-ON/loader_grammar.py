"""Pure model of nonembedded pinned loader main argv grammar, not guest execution.
Source kexe_loader.c12455..12480 and12528..12535: split first -- BEFORE argc6+arity.
"""
import re
def interpretation(argv):
 assert type(argv)is list and all(type(x)is str for x in argv)
 guest=None;own=argv
 if '--'in argv[1:]:
  i=argv.index('--',1);guest=argv[i+1:];own=argv[:i]
 assert 6<=len(own)<=11 and re.fullmatch(r'[0-9]+',own[2])and re.fullmatch(r'[0-9]+',own[3])
 arity=int(own[3]);assert arity<=5 and len(own)==6+arity and own[4]in ['x86_64','aarch64']
 assert all(re.fullmatch(r'-?[0-9]+',x)and -(1<<63)<=int(x)<(1<<63)for x in own[6:])
 return {'typedI64':[int(x)for x in own[6:]],'guestArgv':guest,'effectiveArgc':len(own)}
