"""One additional lexical definition from an already generated .i; no compiler."""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path('/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze')
STAGE = ROOT / 'experiments/case_taxonomy/runtime_evidence_alignment_20261017'
sys.path.insert(0, str(ROOT))
from linux_bug_analyze.preprocessed_evidence import extract_definitions

output = STAGE / 'old_x86_smp_callin.supplementary.json'
if output.exists():
    raise RuntimeError('refuse overwrite')
execution = json.loads((STAGE / 'execution_result.json').read_text())
row, = [r for r in execution['results'] if r['profile'] == 'old_x86'
        and r['unit'] == 'arch/x86/kernel/smpboot.c']
path = Path(row['output'])
payload = path.read_bytes()
if hashlib.sha256(payload).hexdigest() != row['sha256']:
    raise RuntimeError('preprocessing changed')
base = json.loads((STAGE / row['regions_file']).read_text())
result = {k: v for k, v in base.items() if k != 'functions'}
result['functions'] = extract_definitions(payload.decode(), {'smp_callin': base['source_path']})
result['selection_status'] = 'supplementary_after_initial_result'
result['selector_protocol_sha256'] = hashlib.sha256((STAGE / 'supplementary_selector_pre.json').read_bytes()).hexdigest()
result['new_preprocessor_invocations'] = 0
output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'selected': list(result['functions']), 'new_preprocessor_invocations': 0}))
