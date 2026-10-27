"""Finite arithmetic counterexamples to overstrong model prose, not kernel runs."""
from pathlib import Path
import json
H=Path(__file__).resolve().parent
def trace(size,shift,fixed):
 pages=size>>shift;cursor=0;rows=[]
 if fixed and pages&31==1:pages+=1
 while cursor<size:
  if pages==0:return dict(status='would_call_ffs_zero',steps=rows)
  scale=(pages&-pages).bit_length()-1;chunks=(pages>>scale)&31
  step=chunks<<(scale+shift);rows.append(dict(scale=scale,num=chunks-1,bytes=step));cursor+=step;pages-=chunks<<scale
 return dict(status='terminated',covered=cursor,steps=rows)
a=trace(31*4096,12,True);assert a['steps'][0]['scale']==0
b=trace(6144,12,True);assert b['status']=='terminated' and b['covered']==8192
c=trace(6144,12,False);assert c['status']=='would_call_ffs_zero'
assert 16384%4096==0 and 14!=12
with (H/'model_counterexamples.json').open('x') as f:json.dump(dict(kind='manual semantic model, finite checks; not legal notifier inputs or Linux defects',fixed_31_pages=a,fixed_partial_page=b,old_partial_page=c,granule_equality_not_necessary_for_divisibility=dict(cpu_page_shift=14,minimum_shift=12,size=16384,divisible=True,actual_configuration_legal='unproved')),f,indent=2)
print('Three overstrong statements distinguished with arithmetic counterexamples; no undefined C executed.')
