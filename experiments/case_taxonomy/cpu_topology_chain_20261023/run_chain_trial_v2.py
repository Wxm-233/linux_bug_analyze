"""Run one bounded integration and evidence-removal controls on old archives."""
from pathlib import Path
import copy
import hashlib
import json
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
from sample_adapter import evaluate_bound_sample


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def save(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def main():
    output = HERE/'results_v2.json'
    assert not output.exists(), 'preserve first run'
    review = (HERE/'pre_execution_review.md').read_text(encoding='utf-8')
    assert 'V2_EXECUTION_GATE: PASS' in review
    method = json.loads((HERE/'method_manifest_v2.json').read_text(encoding='utf-8'))
    for relative, digest in method['files_sha256'].items():
        assert sha((ROOT/relative).read_bytes()) == digest, relative
    packet = json.loads((HERE/'trial_inputs.json').read_text(encoding='utf-8'))
    for relative, digest in packet['archive_input_sha256'].items():
        assert sha((HERE.parent/relative).read_bytes()) == digest, relative
    rows, controls = [], []
    for item in packet['rows']:
        artifacts = {}
        for key, relative in item['artifact_paths'].items():
            path = (ROOT/relative).resolve()
            assert path.is_relative_to(ROOT.resolve())
            artifacts[key] = path.read_bytes()
            assert sha(artifacts[key]) == item['binding']['artifact_sha256'][key]
        args = [item['contract'], item['ledger'], item['record'], item['binding'], artifacts]
        checked = evaluate_bound_sample(*args)
        raw = artifacts['log'].decode('utf-8-sig')
        members = re.findall(r'^.*R4_USER field=cpu1_threads value=([^\r\n]*)\r?$', raw, re.M)
        assert len(members) == 1
        # This existing archive uses a single decimal CPU list value, not hex.
        assert re.fullmatch(r'\d+(?:,\d+)*', members[0].strip())
        final_members = [int(v) for v in members[0].strip().split(',')]
        line = raw.splitlines()[item['binding']['sample']['line']-1]
        online = re.search(r'\bonline=(0|1)\b', line)
        assert online is not None
        rows.append({'profile':item['profile'], 'checked':checked,
                     'comparative_diagnostics': {
                         'final_state_only_contains_target': item['binding']['sample']['cpu'] in final_members,
                         'online_at_sample_only': bool(int(online[1])),
                         'final_members':final_members,
                         'meaning':'Contrastive simplifications only, not independently justified correctness rules.'},
                     'chain_limits':{key:item[key] for key in ('complete_preparation_effect','physical_lock_target_alias',
                                                             'exact_consumption_value','continuous_stability')}})
        for kind in ('missing_effect_value','missing_object_review','wrong_profile','sample_promoted_to_consumption'):
            altered = copy.deepcopy(args[:4])
            if kind == 'missing_effect_value':
                altered[2]['facts'].pop('members')
            elif kind == 'missing_object_review':
                altered[1]['claims'].pop(item['contract']['required_claims']['object_binding'])
            elif kind == 'wrong_profile':
                altered[3]['profile'] = next(row['profile'] for row in packet['rows'] if row['profile'] != item['profile'])
            else:
                altered[2]['sample_kind'] = 'content_consumption'
                altered[2]['sample_event'] = altered[2]['deadline_event']
            answer = evaluate_bound_sample(*altered, artifacts)
            controls.append({'profile':item['profile'],'control':kind,'checked':answer,
                             'kind':'development evidence removal/mutation; not a Linux case'})
    result = {'task':'N2.23','status':'recorded','profiles':rows,'controls':controls,
              'method_manifest_sha256':sha((HERE/'method_manifest_v2.json').read_bytes()),
              'trial_inputs_sha256':sha((HERE/'trial_inputs.json').read_bytes()),
              'summary':{'archived_run_records':len(rows),'evidence_controls':len(controls)},
              'new_kernel_boots':0,'new_compiles':0,'new_model_calls':0,'new_cases':0,
              'independent_positive':0,'independent_normal':0,
              'scope':'known case-specific archive/contract integration; manual purpose/role inputs, no automatic contract extraction'}
    save(output, result)
    print(json.dumps(result['summary']))


if __name__ == '__main__':
    main()
