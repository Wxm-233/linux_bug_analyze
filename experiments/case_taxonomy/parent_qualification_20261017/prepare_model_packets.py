"""Create unchanged parent-only inputs, without repair labels or supplied predicates."""
from pathlib import Path
import hashlib
import json
import re

stage = Path(__file__).resolve().parent
root = stage.parents[2]
outer = root.parent
protocol = json.loads((stage / 'protocol_pre.json').read_text(encoding='utf-8'))
index = json.loads((stage / 'parent_files.json').read_text(encoding='utf-8'))
records = []
instruction = '''You are reviewing historical Linux parent-version source for a research study of architecture-conditioned interface requirements. Analyze only the provided material. Do not infer a fix from a title or prior patch knowledge. No repair, screening conclusion, expected predicate or runtime answer is provided.

Explain whether these sources support a preparation-to-consumption requirement: what information or capability a provider must establish, for which object and scope, and before which actual use. Distinguish common Linux consumer code, code shared only by one CPU architecture, CPU-vendor differences, device modes and runtime CPU choices. A local ordering concern is not automatically a cross-architecture defect. Consumer code can contain an incorrect assumption; do not treat it as the only specification. Separate source facts, a proposed obligation and a proved violation. No warning, an empty fallback, cleanup-style code or missing evidence is not a normality oracle. Do not shrink consumer applicability using a provider guard that may be precisely the unmet prerequisite.

Return one JSON object, with schema "parent-qualification-v1", and these fields:
- source_claims: at most three unchanged, precisely located local structural claims you consider useful. Each has id, document (exact file id below), revision, path, function, kind and target. kind can be before, requires_branch or unconditional_call. target has callee and original integer line; for before also first:{callee,line}; for requires_branch also branch:{line,taken:boolean}. These claims are limited to call structure and do not assert call effects, feasible execution or interface truth. Prefer a supported fact over inventing a missing anchor. An empty list is acceptable.
- requirements: at most two candidates, each with obligation, applicability, provider, object, actual_consumer, deadline, authority_and_evidence, legal_differences, missing_evidence. Give file and original lines for concrete claims. State whether this is a proposed use requirement or an explicit versioned rule. Do not supply a generic assertion merely to fill the list.
- analysis: a concise explanation of the preparation/guard/object/use chain and what architecture-related differences are or are not established. Identify evidence limits in the provided files; do not invent absent functions or an architecture pair.
- qualification: one of potentially_same_mechanism, different_mechanism, insufficient. This is only your source-based proposal, not a confirmed label.
- needed_materials: a short list of exact missing definitions/configuration/path evidence, or empty.

Keep the total response focused, normally within 6000 words. Do not call tools or invent experiment results. If the material cannot establish a condition, retain that uncertainty.
'''
for case in protocol['candidates']:
    output = outer / '模型调用测试/2026-10-17' / ('parent_qualification_' + case['id'])
    output.mkdir(parents=True, exist_ok=True)
    if (output / 'prompt.md').exists() or (output / 'receipt.json').exists():
        raise RuntimeError('Do not overwrite or resend a prepared parent task')
    pieces = [instruction, '\nThe following files are exact unconfigured source, not a preprocessed translation unit. Source #if branches and header declarations do not prove actual execution.\n']
    for doc in index['documents']:
        if doc['candidate'] != case['id']:
            continue
        raw = (stage / doc['saved_path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == doc['sha256']
        pieces.append('\nFILE ' + json.dumps({k:doc[k] for k in ['id','revision','path','sha256']}) + '\n')
        pieces.append('\n'.join(f'{i}: {line}' for i,line in enumerate(raw.decode('utf-8').splitlines(),1)) + '\nEND FILE\n')
    prompt = '\n'.join(pieces)
    assert not re.search(r'\bsk-[A-Za-z0-9_-]{12,}', prompt)
    encoded = prompt.encode('utf-8')
    if len(encoded) > protocol['model']['max_input_utf8_bytes_per_candidate']:
        raise RuntimeError('Registered input limit exceeded; no truncation or model request')
    (output / 'prompt.md').write_bytes(encoded)
    records.append({'candidate':case['id'],'parent':case['parent'],'output_directory':str(output),'prompt_sha256':hashlib.sha256(encoded).hexdigest(),'prompt_utf8_bytes':len(encoded),'researcher_predicate_or_role_supplied':False,'path_selection_origin':'researcher_registered_metadata_based','repair_supplied':False,'reservation':protocol['model']['conservative_reservation_per_request']})
(stage / 'model_packet_index.json').write_text(json.dumps({'packets':records,'total_reservation':sum(r['reservation'] for r in records),'independent_detector_result':False},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'packets':[{k:r[k] for k in ['candidate','prompt_utf8_bytes','reservation']} for r in records],'total_reservation':sum(r['reservation'] for r in records)},ensure_ascii=False))
