"""Freeze checked rule files and the independently selected metadata leads."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
FILES=['outbound_scalar_single_revision.py','outbound_scalar_single_revision_test.py',
       'representation_producer_v5.py','representation_producer_v5_test.py',
       'representation_producer_v4.py','representation_producer_v3.py',
       'endian_consumer_single_revision.py',
       'outbound_scalar_20260930/run_frozen.py',
       'outbound_scalar_20260930/select_metadata.py',
       'outbound_scalar_20260930/select_targets_pre.py']
OLD={'representation_producer_v4.py':'2c57d2c54e96d0926cc3c5a25529f1de0d83f3fc0144368e3189ccf8886ec7b4',
     'representation_producer_v3.py':'ef9e292fe414ab597931d161bb10fdf35a8fd22b1cde6df3a91b05417ce91a9c',
     'endian_consumer_single_revision.py':'71e50604221ff0b68ac44039ca64606253e32e6b0a136206aea768e329bd467c'}

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    dest=HERE/'freeze_manifest.json'
    if dest.exists():raise RuntimeError('freeze already exists')
    for name,expected in OLD.items():
        if sha(BASE/name)!=expected:raise RuntimeError('old frozen implementation changed: '+name)
    tests=HERE/'root_test_run.json'
    audit=HERE/'method_audit.json'
    if not tests.exists() or not audit.exists():
        raise RuntimeError('root tests and independent final audit records required')
    t=json.loads(tests.read_text(encoding='utf-8'))
    a=json.loads(audit.read_text(encoding='utf-8'))
    if t.get('exit_code')!=0 or a.get('status')!='pass':
        raise RuntimeError('verification has not passed')
    for record in t['tested_implementations']:
        if sha(BASE/record['path'])!=record['sha256']:
            raise RuntimeError('tested implementation changed')
    for record in a['implementations']:
        name=Path(record['path']).name
        if name not in {'outbound_scalar_single_revision.py','representation_producer_v5.py'}:
            raise RuntimeError('unexpected audited implementation')
        if sha(BASE/name)!=record['sha256']:
            raise RuntimeError('audited implementation changed')
    report={'frozen_at_utc':datetime.now(timezone.utc).isoformat(),
            'files':[{'path':name,'sha256':sha(BASE/name)} for name in FILES],
            'selection_sha256':sha(HERE/'selection_pre.json'),
            'pool_sha256':sha(HERE/'metadata_pool.json'),
            'protocol_sha256':sha(HERE/'protocol_pre.md'),
            'root_test_record_sha256':sha(tests),'method_audit_record_sha256':sha(audit),
            'context':'Linux kernel source, __KERNEL__ true; unspecified configuration macros unknown',
            'rule_limit':'Local declaration/byte-copy facts, not opcode-format or value-path correctness. Zero sites not normal. No paid requests.'}
    dest.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('freeze saved:',len(FILES),'files')

if __name__=='__main__':main()
