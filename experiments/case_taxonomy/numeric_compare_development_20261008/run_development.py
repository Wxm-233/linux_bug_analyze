from pathlib import Path
import hashlib
import json
import sys
from numeric_compare import Source,inspect_function,domain_witnesses

HERE=Path(__file__).resolve().parent
lock=json.loads((HERE/'input_lock_pre.json').read_text(encoding='utf-8'))
for r in lock['files']:
    assert hashlib.sha256(Path(r['path']).read_bytes()).hexdigest()==r['sha256'],r['path']
records=[]
for label,source in lock['source_inputs'].items():
    raw=Path(source['saved_path']).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==source['sha256']
    assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==source['blob_sha1']
    src=Source(source['source_path'],source['revision'],source['saved_path'],source['blob_sha1'],raw)
    records.append(dict(label=label,source=source,
        functions=[inspect_function(src,name) for name in lock['selected_functions']],
        format_context=[domain_witnesses(src,name,'RESTART_AREA','seq_num_bits') for name in ('log_create_ra','log_replay')]))
result=dict(development_only=True,source_interface_count=1,revision_observations=2,
            new_confirmed_cases=0,independent_detections=0,model_calls=0,records=records)
target=Path(sys.argv[1]);assert not target.exists()
target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
for row in records:
    counts={key:sum(v['status']==key for f in row['functions'] for v in f['field_atoms'])
            for key in ('candidate','normal','insufficient','not_value_read')}
    print(json.dumps(dict(label=row['label'],counts=counts,atoms=sum(f['enumerated_logical_atoms'] for f in row['functions']))))
