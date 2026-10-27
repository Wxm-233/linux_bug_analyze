"""Save a bounded, title-only historical pool before opening source or patches."""
from pathlib import Path
import subprocess,json
from datetime import datetime,timezone

repo='/root/repos/linux'
out=Path(__file__).parent/'repr_v4_metadata_pool_20260930.json'
args=['git','-C',repo,'log','--all','--no-merges','--since=2010-01-01',
      '--until=2017-12-31','--regexp-ignore-case','--grep=endian',
      '--grep=sparse','--max-count=100','--format=%H%x09%cs%x09%s','--','drivers']
r=subprocess.run(args,capture_output=True,text=True,check=True)
records=[]
for line in r.stdout.splitlines():
    sha,date,subject=line.split('\t',2)
    paths=subprocess.run(['git','-C',repo,'diff-tree','--no-commit-id','--name-only','-r',sha],
                         capture_output=True,text=True,check=True).stdout.splitlines()
    records.append({'commit':sha,'date':date,'subject':subject,'paths':paths})
out.write_text(json.dumps({'saved_at_utc':datetime.now(timezone.utc).isoformat(),
    'query':args,'cap':100,'count':len(records),'records':records,
    'read_boundary':'Only subjects, dates and changed paths exposed. Git grep may match commit body internally; no bodies, diffs or source opened.'},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(out.name,len(records))
