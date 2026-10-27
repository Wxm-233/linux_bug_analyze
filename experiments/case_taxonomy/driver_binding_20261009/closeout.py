"""Seal finite binding evidence with read-only verification and no Git rerun."""
from pathlib import Path
import hashlib,json,subprocess,sys

HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for name in ['binding_card.json','audit_protocol/review_code_pre.json','audit_semantics/review.json','audit_kbuild/review.json','synthesis.md','checkpoint.md']:
    assert (HERE/name).is_file(),name
argv=[sys.executable,'-B','-X','utf8',str(HERE/'verify_stage.py')]
p=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
for name,raw in [('verify.stdout.bin',p.stdout),('verify.stderr.bin',p.stderr)]:
    target=HERE/name;assert not target.exists();target.write_bytes(raw)
receipt=HERE/'verify_receipt.json';assert not receipt.exists()
receipt.write_text(json.dumps(dict(argv=argv,returncode=p.returncode,stdout_sha256=sha(HERE/'verify.stdout.bin'),
    stderr_sha256=sha(HERE/'verify.stderr.bin'),git_reexecuted=False,old_rules_reexecuted=False,
    counts=json.loads(p.stdout) if p.returncode==0 else None),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
if p.returncode:sys.stderr.buffer.write(p.stderr);raise SystemExit(p.returncode)
for args in [argv+['--freeze'],argv]:
    q=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if q.returncode:
        sys.stdout.buffer.write(q.stdout);sys.stderr.buffer.write(q.stderr);raise SystemExit(q.returncode)
print(json.dumps(dict(counts=json.loads(q.stdout),completion_sha256=sha(HERE/'completion_manifest.json')),ensure_ascii=False))
