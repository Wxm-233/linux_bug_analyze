"""Verify the bounded unsupported input and seal stage, without Git/rules."""
from pathlib import Path
import hashlib,json,subprocess,sys
HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for name in ['synthesis.md','checkpoint.md','support_card.json','audit_support/review.json']:assert (HERE/name).is_file(),name
closed=HERE/'completion_manifest.json';assert not closed.exists()
argv=[sys.executable,'-B','-X','utf8',str(HERE/'verify_saved.py')]
p=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
for name,raw in [('verify.stdout.bin',p.stdout),('verify.stderr.bin',p.stderr)]:
    target=HERE/name;assert not target.exists();target.write_bytes(raw)
counts=json.loads(p.stdout) if p.returncode==0 else None
(HERE/'verify_receipt.json').write_text(json.dumps(dict(argv=argv,returncode=p.returncode,stdout_sha256=sha(HERE/'verify.stdout.bin'),stderr_sha256=sha(HERE/'verify.stderr.bin'),counts=counts,rule_or_git_reexecuted=False),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
if p.returncode:sys.stderr.buffer.write(p.stderr);raise SystemExit(p.returncode)
files=[p for p in sorted(HERE.rglob('*')) if p.is_file() and '__pycache__' not in p.parts]
closed.write_text(json.dumps(dict(files=[dict(path=str(p),sha256=sha(p)) for p in files],counts=counts),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
q=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
if q.returncode:sys.stdout.buffer.write(q.stdout);sys.stderr.buffer.write(q.stderr);raise SystemExit(q.returncode)
print(json.dumps(dict(counts=counts,completion_sha256=sha(closed)),ensure_ascii=False))
