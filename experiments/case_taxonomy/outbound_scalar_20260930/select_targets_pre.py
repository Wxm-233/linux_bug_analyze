"""Fix metadata leads before developer freeze and root source/patch review."""
from pathlib import Path
from datetime import datetime, timezone
import json, subprocess, hashlib

HERE=Path(__file__).resolve().parent
PICKS=[('727ea61a5028','net/bluetooth/hci_core.c',
        'Explicit missing conversion title near an already known byte-copy interface; actual scalar shape not yet read.'),
       ('0ab905c3be8c','net/bluetooth/coredump.c',
        'Explicit u32 byte-order storage title; sink and scalar shape not yet read.')]

def main():
    poolpath=HERE/'metadata_pool.json'
    rows=json.loads(poolpath.read_text(encoding='utf-8'))['records']
    dest=HERE/'selection_pre.json'
    if dest.exists():raise RuntimeError('refusing to overwrite preselection')
    targets=[]
    for prefix,path,role in PICKS:
        matches=[r for r in rows if r['commit'].startswith(prefix)]
        if len(matches)!=1 or path not in matches[0]['paths']:
            raise RuntimeError('metadata target not unique or path mismatch')
        r=matches[0]
        parent=subprocess.run(['git','-C','/root/repos/linux','rev-parse',r['commit']+'^'],capture_output=True,text=True,check=True).stdout.strip()
        targets.append({**r,'old_revision':parent,'source_path':path,'role':role})
    report={'selected_at_utc':datetime.now(timezone.utc).isoformat(),'targets':targets,
            'pool_sha256':hashlib.sha256(poolpath.read_bytes()).hexdigest(),
            'selection':'Two fixed metadata-only leads; no target body, patch or source read before selection or rule freeze.',
            'reading_audit':'Filename-only SHA-prefix search in experiments/tests/analysis_out found only the current metadata pool. This is bounded evidence, not proof of no exposure anywhere.',
            'limit':'Same mechanism, format authority and supported source shape not established from metadata. No replacement based on checker output.'}
    dest.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('metadata targets fixed:',len(targets))

if __name__=='__main__':main()
