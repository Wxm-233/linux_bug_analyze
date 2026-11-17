from closure import bfs
from common import write
def n(f,k=1): return ('function',f,f,k,1)
a,b,c,d,e=[n('arch/riscv/'+v+'.c') for v in 'abcde']
p,q=n('kernel/p.c'),n('kernel/q.c')
same_name_other_file=n('arch/riscv/other.c')
edges={a:{b,p},b:{c},c:{a,d},d:{e},p:{q},q:{p},same_name_other_file:{e}}
EXPECTED={a:0,b:1,c:2,d:3,p:0,q:1}
distance,parent=bfs({a,p},edges)
assert distance==EXPECTED,(distance,EXPECTED)
assert e not in distance and same_name_other_file not in distance
assert parent[d]==c and parent[p] is None
assert bfs({e},edges)[0]=={e:0}
write('selftest_closure_result.json',{'passed':True,'nodes':len(distance),
      'checks':['two_sides','cycle','depth3','depth4_excluded','static_identity','cross_side_blocked','unknown_no_outgoing']})
print('closure selftest passed')
