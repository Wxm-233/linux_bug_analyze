from pathlib import Path
import json,subprocess,hashlib
s=Path(__file__).resolve().parent;p=s/'symbol_search_pre.json';d=json.loads(p.read_bytes());rows=[]
for c in d['cases']:
 assert len(c['symbols'])<=6
 argv=['git','-C','/root/repos/linux','grep','-n','-w','-F']
 for sym in c['symbols']:argv+=['-e',sym]
 argv+=[c['parent'],'--',*c['paths']]
 r=subprocess.run(argv,capture_output=True,timeout=45)
 rows.append({'case':c['case'],'argv':argv,'exit_code':r.returncode,'text':r.stdout.decode('utf-8'),'stderr':r.stderr.decode('utf-8','replace')})
with (s/'symbol_search.json').open('x',encoding='utf-8') as f:json.dump({'pre_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'rows':rows,'child_reads':0,'network':0},f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({'searches':len(rows),'returncodes':[r['exit_code'] for r in rows]}))
