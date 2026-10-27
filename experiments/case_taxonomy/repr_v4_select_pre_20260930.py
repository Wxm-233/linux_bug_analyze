"""Freeze two metadata-only leads, without exposing old or repaired source."""
import json,subprocess,hashlib
from pathlib import Path
from datetime import datetime,timezone
here=Path(__file__).parent
poolpath=here/'repr_v4_metadata_pool_20260930.json'
pool=json.loads(poolpath.read_text(encoding='utf-8'))
specs=[('494f401b','drivers/scsi/mpt3sas/mpt3sas_base.c','possible typed write; sparse title does not establish exact syntax'),
       ('c30b93ea','drivers/bluetooth/hci_ll.c','conversion scope contrast; title does not establish macro or compound write')]
targets=[]
for prefix,path,role in specs:
    item=next(r for r in pool['records'] if r['commit'].startswith(prefix))
    parent=subprocess.run(['git','-C','/root/repos/linux','rev-parse',item['commit']+'^'],
                          capture_output=True,text=True,check=True).stdout.strip()
    assert path in item['paths']
    targets.append(dict(item,old_revision=parent,source_path=path,role=role))
report={'selected_at_utc':datetime.now(timezone.utc).isoformat(),'targets':targets,
    'pool_sha256':hashlib.sha256(poolpath.read_bytes()).hexdigest(),
    'selection':'manual fixed metadata-only choice, before old source, fix patch or body review',
    'novelty':'filename-only search in experiments/tests/analysis_out found only the current pool for these SHA prefixes',
    'limit':'purposeful historical revision leads; same mechanism and defect truth not established by metadata'}
(here/'repr_v4_selection_20260930_pre.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('metadata selection saved; source and patch unopened')
