"""Locate exactly two parent-version consumer names; no source expansion."""
from pathlib import Path
import json
import subprocess

stage=Path(__file__).resolve().parent
plan=json.loads((stage/'protocol_pre.json').read_text(encoding='utf-8'))
out=stage/'definition_locations.json'
if out.exists():
    raise SystemExit('Locations already saved; do not overwrite.')
command=['git','-C','/root/repos/linux','grep','-n','-E',r'(^|[[:space:]])(cpu_init_topology|cpu_parse_topology)[[:space:]]*\(',plan['parent'],'--','arch/x86']
result=subprocess.run(command,capture_output=True)
record={'parent':plan['parent'],'names':plan['definition_names'],'status':'located' if result.returncode==0 else 'not_found' if result.returncode==1 else 'failure','lines':result.stdout.decode('utf-8').splitlines(),'stderr':result.stderr.decode('utf-8'),'scope':'symbol locations only; no helper body or child revision read'}
out.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(record,ensure_ascii=False))
