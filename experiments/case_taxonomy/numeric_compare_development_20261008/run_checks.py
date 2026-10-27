"""Capture one frozen test/development pass without overwriting previous output."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime,timezone

HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
p=argparse.ArgumentParser();p.add_argument('--tag',required=True);p.add_argument('--lock',default='freeze_code_pre.json');a=p.parse_args()
assert a.tag.replace('_','').isalnum()
locked=json.loads((HERE/a.lock).read_text(encoding='utf-8'))
def check():
    for r in locked['files']:assert sha(Path(r['path']))==r['sha256'],r['path']
check()
folder=HERE/a.tag;folder.mkdir(exist_ok=False)
receipt=dict(start_utc=datetime.now(timezone.utc).isoformat(),freeze_path=str(HERE/a.lock),freeze_sha256=sha(HERE/a.lock),commands=[])
for name,argv in [('tests',[sys.executable,'-B','-X','utf8','-m','unittest','-v','test_numeric_compare']),
                  ('development',[sys.executable,'-B','-X','utf8',str(HERE/'run_development.py'),str(folder/'results.json')])]:
    result=subprocess.run(argv,cwd=HERE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    out=folder/(name+'_stdout.txt');err=folder/(name+'_stderr.txt')
    out.write_bytes(result.stdout);err.write_bytes(result.stderr)
    receipt['commands'].append(dict(name=name,argv=argv,returncode=result.returncode,stdout=str(out),stderr=str(err),stdout_sha256=sha(out),stderr_sha256=sha(err)))
check();receipt['end_utc']=datetime.now(timezone.utc).isoformat();receipt['code_unchanged_after_execution']=True
(folder/'execution_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(tag=a.tag,returncodes=[r['returncode'] for r in receipt['commands']],results_sha256=sha(folder/'results.json') if (folder/'results.json').exists() else None)))
raise SystemExit(any(r['returncode'] for r in receipt['commands']))
