"""One read-only saved-fact verification, receipt, then an immutable file list."""
from pathlib import Path
import hashlib,json,subprocess,sys

HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(name,value):
    p=HERE/name;assert not p.exists(),p
    p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
assert not (HERE/'completion_manifest.json').exists()
assert not (HERE/'verify.stdout.bin').exists()
argv=[sys.executable,'-B','-X','utf8',str(HERE/'verify_saved.py')]
p=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
out=HERE/'verify.stdout.bin';err=HERE/'verify.stderr.bin';out.write_bytes(p.stdout);err.write_bytes(p.stderr)
put('verify.receipt.json',dict(argv=argv,returncode=p.returncode,stdout_sha256=sha(out),stderr_sha256=sha(err),purpose='read_only_saved_fact_verification_not_rule_execution'))
assert p.returncode==0,p.stderr.decode('utf-8',errors='replace')
result=json.loads(p.stdout);assert result['verification_passed'] is True
files=[dict(path=str(q),sha256=sha(q)) for q in sorted(HERE.rglob('*')) if q.is_file()]
put('completion_manifest.json',dict(date='2026-10-09',files=files,result_summary=result,stage_complete=True,implementation_input_formed=False,detector_generalization_proven=False))
for row in files:assert sha(Path(row['path']))==row['sha256']
print(json.dumps(dict(**result,sealed_files=len(files),completion_manifest_sha256=sha(HERE/'completion_manifest.json')),ensure_ascii=False))
