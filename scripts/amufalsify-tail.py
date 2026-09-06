path = '/Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu/docs/codegen-coscientist.md'
lines = open(path, encoding='utf-8').read().split('\n')
out = open('/Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu/docs/probe_out2.txt', 'w', encoding='utf-8')
out.write("VERIFY LINE 40 TAIL: ...%s\n" % lines[39][-320:])
out.close()
