"""Save a single no-input stop and native verification receipt, then seal artifacts."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
from datetime import datetime,timezone

HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,value):
    p=HERE/name;assert not p.exists()
    p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

parent=json.loads((HERE/'parent_manifest.json').read_text(encoding='utf-8'))
support=json.loads((HERE/'audit_parent_support/review.json').read_text(encoding='utf-8'))
assert support['supported_main_input'] is None
source=parent['observations'][0]['sources'][0];lines=Path(source['saved_path']).read_text(encoding='utf-8').splitlines()
save('stop_receipt.json',dict(time_utc=datetime.now(timezone.utc).isoformat(),
    status='stopped_after_parent_support_no_input',parent_support_attempts=1,supported_inputs=0,
    rule_executions=0,patch_exports=0,project_model_calls=0,new_confirmed_cases=0,
    independent_positive_cases=0,pool_expanded=False,queue_substituted=False,
    second_input_freeze='not_performed_no_supported_input',
    output_lock='not_performed_no_rule_output',
    support_review_sha256=sha(HERE/'audit_parent_support/review.json'),
    method_review_sha256=sha(HERE/'audit_method/review.json'),
    semantic_status='support_prescreen; not a true negative or false negative',
    root_hypothesis_quotes=[dict(saved_path=source['saved_path'],line=n,text=lines[n-1]) for n in [73,74,471]],
    root_hypothesis_status='length-domain question only; field declaration/path/value/patch not verified'))
argv=[sys.executable,'-B','-X','utf8',str(HERE/'verify_stage.py')]
p=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
(HERE/'verify.stdout.bin').write_bytes(p.stdout);(HERE/'verify.stderr.bin').write_bytes(p.stderr)
save('verify_receipt.json',dict(argv=argv,returncode=p.returncode,
    stdout_sha256=sha(HERE/'verify.stdout.bin'),stderr_sha256=sha(HERE/'verify.stderr.bin'),
    detector_executed=False,counts=json.loads(p.stdout) if p.returncode==0 else None))
if p.returncode:raise SystemExit(p.returncode)
p2=subprocess.run(argv+['--freeze'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
if p2.returncode:
    sys.stdout.buffer.write(p2.stdout);sys.stderr.buffer.write(p2.stderr);raise SystemExit(p2.returncode)
p3=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
if p3.returncode:
    sys.stdout.buffer.write(p3.stdout);sys.stderr.buffer.write(p3.stderr);raise SystemExit(p3.returncode)
print(json.dumps(dict(counts=json.loads(p3.stdout),completion_sha256=sha(HERE/'completion_manifest.json')),ensure_ascii=False))
