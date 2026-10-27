from pathlib import Path
import hashlib,json,shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
old=ROOT/'模型调用测试/2026-10-25/btrfs_actual_path_closure'
new=ROOT/'模型调用测试/2026-10-25/btrfs_actual_path_closure_authorized_retry'
assert not new.exists(),'preserve prior attempt'
new.mkdir()
shutil.copyfile(old/'prompt.md',new/'prompt.md')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(old/'prompt.md')==sha(new/'prompt.md')
record=dict(authorization='用户明确：解除本次停点，允许原样重新调用',
 original_attempt=str(old.relative_to(ROOT)),new_attempt=str(new.relative_to(ROOT)),
 prompt_sha256=sha(new/'prompt.md'),prompt_unchanged=True,old_receipt_sha256=sha(old/'receipt.json'),
 per_call_allowance=1000000,historical_usage_deducted=False,
 no_automatic_followup_retry=True)
(HERE/'retry_authorization.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Authorized retry prepared with identical prompt bytes in new directory')
