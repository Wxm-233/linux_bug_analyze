"""Trial frozen components on parent-only selected functions and unchanged model claims."""
from pathlib import Path
import hashlib
import importlib.util
import json
import re
import sys

stage = Path(__file__).resolve().parent
root = stage.parents[2]
sys.path.insert(0, str(root))
from linux_bug_analyze.source_conditions import analyze_function, check_source_claim
from linux_bug_analyze.forward_guards import extract_forward_paths

spec = importlib.util.spec_from_file_location('existing_parent_locator', stage.parent / 'preparation_eligibility_20261016/collect_sources.py')
locator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(locator)
protocol = json.loads((stage / 'protocol_pre.json').read_text(encoding='utf-8'))
index = json.loads((stage / 'parent_files.json').read_text(encoding='utf-8'))
selections = json.loads((stage / 'manual_function_locations.json').read_text(encoding='utf-8'))['functions']
output = stage / 'parent_component_results.json'
if output.exists():
    raise SystemExit('Parent trial already recorded; do not overwrite.')
files = {(d['candidate'],d['path']):d for d in index['documents']}
model_records = {}
model_claims = []
for case in protocol['candidates']:
    folder = root.parent / '模型调用测试/2026-10-17' / ('parent_qualification_' + case['id'])
    receipt = json.loads((folder / 'receipt.json').read_text(encoding='utf-8')) if (folder / 'receipt.json').exists() else {}
    if receipt.get('status') == 'started':
        raise RuntimeError('Wait for parent model completion/failure before recording final component trial')
    record = {'delivery_status':receipt.get('status','missing_receipt'),'raw_claims_adopted':False}
    if receipt.get('status') == 'complete_final_received':
        raw = (folder / 'final.md').read_text(encoding='utf-8')
        match = re.fullmatch(r'\s*```(?:json)?\s*\n([\s\S]*)\n```\s*',raw)
        try:
            value = json.loads(match[1] if match else raw)
            if not isinstance(value,dict) or value.get('schema') != 'parent-qualification-v1' or not isinstance(value.get('source_claims'),list) or len(value['source_claims']) > 3:
                raise ValueError('wrong schema or source_claims')
            record.update(protocol_parse='pass',fence_removed=bool(match),model_qualification_proposal=value.get('qualification'),requirements_count=len(value.get('requirements',[])))
            for claim in value['source_claims']:
                model_claims.append((case['id'],claim))
                if isinstance(claim,dict) and isinstance(claim.get('path'),str) and isinstance(claim.get('function'),str):
                    selections.append({'candidate':case['id'],'path':claim['path'],'function':claim['function'],'reason':'unchanged model source_claim function location'})
        except (ValueError,TypeError) as exc:
            record.update(protocol_parse='failed_preserved_no_retry',parse_reason=str(exc))
    model_records[case['id']] = record

analyses, forward, documents, failures, manual = {}, {}, [], [], []
for chosen in selections:
    key = (chosen['candidate'],chosen['path'],chosen['function'])
    if key in analyses or any(tuple(x.get('key',[])) == key for x in failures):
        continue
    data = files.get(key[:2])
    if data is None or not re.fullmatch(r'[A-Za-z_]\w*',key[2]):
        failures.append({'key':key,'stage':'material_binding','reason':'unregistered file or invalid function name'})
        continue
    raw = (stage / data['saved_path']).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == data['sha256']
    try:
        lo,hi,source = locator.complete_function(raw,key[2])
    except ValueError as exc:
        failures.append({'key':key,'stage':'existing_material_locator','reason':str(exc),'selection_origin':chosen['reason']})
        continue
    document = {'id':data['id'],'revision':data['revision'],'path':data['path'],'start_line':lo,'end_line':hi,'text':source}
    documents.append({**document,'function':key[2],'function_sha256':hashlib.sha256(source.encode()).hexdigest(),'selection_origin':chosen['reason']})
    analyses[key] = analyze_function(document,annotations=('__init',))
    forward[key] = extract_forward_paths(document)
    manual.append({'key':key,'selection_origin':chosen['reason'],'source_status':analyses[key]['status'],'forward_status':forward[key]['status']})

checked=[]
for candidate, claim in model_claims:
    if not isinstance(claim,dict):
        checked.append({'candidate':candidate,'status':'insufficient','reason':'claim is not an object','original_claim':claim})
        continue
    if not isinstance(claim.get('path'),str) or not isinstance(claim.get('function'),str):
        checked.append({'candidate':candidate,'status':'insufficient','reason':'invalid source selector type','original_claim':claim})
        continue
    key=(candidate,claim.get('path'),claim.get('function'))
    if key not in analyses:
        checked.append({'candidate':candidate,'status':'insufficient','reason':'complete supported material unavailable','original_claim':claim})
    else:
        checked.append({'candidate':candidate,**check_source_claim(analyses[key],claim)})

record={'protocol_sha256':hashlib.sha256((stage/'protocol_pre.json').read_bytes()).hexdigest(),'model':model_records,'material_trials':manual,'collection_failures':failures,'unchanged_model_claim_checks':checked,'whole_contract':'insufficient','actual_configuration_proved':False,'primitive_summaries_supplied':False,'new_builds':0,'new_kernel_runs':0,'independent_positive':0,'independent_normal':0,'repair_material_read':False}
(stage/'selected_parent_functions.json').write_text(json.dumps({'documents':documents},ensure_ascii=False,indent=2),encoding='utf-8')
(stage/'source_component_facts.json').write_text(json.dumps({'source':list(analyses.values()),'forward':list(forward.values())},ensure_ascii=False,indent=2),encoding='utf-8')
output.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'functions_collected':len(documents),'collection_failures':len(failures),'source_statuses':{s:sum(a['status']==s for a in analyses.values()) for s in {a['status'] for a in analyses.values()}},'model_claims_checked':len(checked),'claim_statuses':{s:sum(a['status']==s for a in checked) for s in {a['status'] for a in checked}},'whole_contract':'insufficient'},ensure_ascii=False))
