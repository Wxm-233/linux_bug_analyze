from pathlib import Path
import json,copy
H=Path(__file__).resolve().parent
def assess(row):
 phase='idle';completed=0;granule=1<<row['shift'];synced=False
 for line in row['stdout'].splitlines():
  op,*args=line.split()
  if op=='SYNC_CLEAR':synced=True
  elif op=='PARENT_CLEAR_OBSERVED':
   if phase!='idle':return 'violation'
   phase='clear'
  elif op=='WALK':
   if phase!='clear':return 'insufficient_clear_evidence'
   if not row['coherent'] and not synced:return 'insufficient_sync_evidence'
   a,n,g=map(int,args)
   if g!=granule or n!=(1<<(2*row['shift']-3)) or a%n:return 'violation'
   phase='walk'
  elif op=='WALK_RETURN':
   if phase!='walk':return 'violation'
   phase='returned'
  elif op=='FREE':
   if phase!='returned':return 'violation'
   if int(args[0])!=granule:return 'violation'
   completed+=1;phase='idle';synced=False
  elif op=='RESULT':
   if completed!=int(args[1]) or completed!=int(args[3]):return 'insufficient_trace'
 return 'pass_local_sequence' if phase=='idle' and completed else 'insufficient_trace'
rows=json.loads((H/'observed_results.json').read_text())['cases'];results=[]
for row in rows:
 verdict=assess(row);assert verdict=='pass_local_sequence'
 results.append(dict(shift=row['shift'],mode=row['mode'],coherent=row['coherent'],sequence=verdict,hardware_visibility='insufficient',whole_path='insufficient'))
base=rows[0];controls=[]
for name,old,new,expected in [
 ('free_before_return','WALK_RETURN\nFREE','FREE','violation'),
 ('missing_clear','PARENT_CLEAR_OBSERVED\n','','insufficient_clear_evidence'),
 ('missing_sync','SYNC_CLEAR\n','','insufficient_sync_evidence'),
 ('wrong_granule','2097152 2097152 4096','2097152 2097152 8192','violation')]:
 row=copy.deepcopy(base);assert old in row['stdout'];row['stdout']=row['stdout'].replace(old,new,1);v=assess(row);assert v==expected,(name,v);controls.append(dict(name=name,synthetic=True,verdict=v))
(H/'sequence_audit.json').write_text(json.dumps(dict(cases=results,controls=controls,scope='researcher-registered level2 table deletion sequence; callback returns are not hardware completion'),indent=2));print('12 original traces + 4 sequence/evidence controls passed')
