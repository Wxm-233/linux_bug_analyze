"""Check saved artifacts without rerunning rules or asserting semantic truth."""
from pathlib import Path
import hashlib
import json
import sys

HERE = Path(__file__).resolve().parent
BASE = HERE.parent


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def read(name):
    return json.loads((HERE/name).read_text(encoding='utf-8'))


def check_files(records):
    for r in records:
        assert sha(Path(r['path'])) == r['sha256'], r['path']


def all_quotes(value):
    if isinstance(value, dict):
        if {'saved_path','start_line','end_line','text','sha256','blob_sha1'} <= value.keys():
            yield value
        for child in value.values():
            yield from all_quotes(child)
    elif isinstance(value, list):
        for child in value:
            yield from all_quotes(child)


def main():
    check_files(read('freeze_metadata_pre.json')['files'])
    check_files(read('freeze_queries_pre.json')['files'])
    err=read('export_erratum_pre.json')
    assert sha(HERE/'prepare_export_resume.py') == err['resume_runner_sha256']
    for name, digest in err['original_failure_artifacts'].items():
        assert sha(HERE/name) == digest
    assert read('parent_sources.json')['parent_prescreens'] == 0
    assert len(read('parent_commands.json')) == 2
    assert not list((HERE/'prescreen').rglob('source*'))
    assert sha(BASE/'interface_facts_20261008/interface_fact_extractor.py') == '45f2daf253aa03e229df30a2f7c93d266711886a0c1e887b7fb57162cf24b715'
    assert sha(BASE/'endian_consumer_single_revision.py') == '71e50604221ff0b68ac44039ca64606253e32e6b0a136206aea768e329bd467c'
    lock=read('parent_output_lock.json')
    assert sha(HERE/'parent_results.json') == lock['parent_results_sha256']
    assert sha(HERE/'freeze_queries_pre.json') == lock['query_freeze_sha256']
    assert sha(HERE/'parent_output_lock.json') == read('unseal_manifest.json')['output_lock_sha256']
    assert read('freeze_queries_pre.json')['time_utc'] < lock['time_utc'] < read('unseal_manifest.json')['time_utc']
    sources=[s for r in read('parent_resume_sources.json')['observations'] for s in r['sources']]
    sources += [s for r in read('unseal_manifest.json')['observations'] for s in r['sources']]
    for s in sources:
        raw=Path(s['saved_path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == s['sha256']
        assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest() == s['blob_sha1']
    assert len(sources) == 15
    command_count=0
    for name in ['parent_commands.json','parent_resume_commands.json','unseal_commands.json','causal_metadata_commands.json']:
        records=read(name)
        if isinstance(records,dict): records=records['commands']
        for r in records:
            assert r['returncode'] == 0
            assert sha(Path(r['stdout'])) == r['stdout_sha256']
            assert sha(Path(r['stderr'])) == r['stderr_sha256']
            command_count += 1
    quotes=0
    for name in ['parent_results.json','fixed_results.json','review.json']:
        for q in all_quotes(read(name)):
            raw=Path(q['saved_path']).read_bytes()
            assert hashlib.sha256(raw).hexdigest() == q['sha256']
            assert '\n'.join(raw.decode('utf-8').splitlines()[q['start_line']-1:q['end_line']]) == q['text']
            assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest() == q['blob_sha1']
            quotes += 1
    selected=read('selection_pre.json')
    assert selected['parent_prescreen_count'] == 4 and len(selected['queries']) == 1
    q=selected['queries'][0]
    assert q['field'] == 'minor_ver' and q['specified_main_site']['line'] == 445
    for name in ['parent_results.json','fixed_results.json']:
        obs=read(name)['outputs']
        assert len(obs) == 1 and obs[0]['query'] == q['id'] and obs[0]['execution_status'] == 'ok'
        out=obs[0]['outputs']
        assert len(out)==1 and out[0]['status']=='normal' and out[0]['expression']=='!rhdr->minor_ver'
        assert out[0]['normal_scope']=='local_occurrence_shape'
        assert not out[0]['whole_condition_certified']
    assert read('review.json')['new_confirmed_cases']==0
    assert not read('review.json')['frozen_site_result']['repair_target_correspondence']
    completion=HERE/'completion_manifest.json'
    if '--freeze' in sys.argv:
        assert not completion.exists(), 'Refusing overwrite of closeout'
        files=[p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p!=completion]
        deps=[BASE/'interface_facts_20261008/interface_fact_extractor.py',BASE/'endian_consumer_single_revision.py',
              BASE/'interface_facts_20261008/closeout_manifest.json',BASE/'bounded_interface_holdout_20261003/pool_metadata.json']
        completion.write_text(json.dumps(dict(files=[dict(path=str(p),sha256=sha(p)) for p in sorted(files+deps)]),indent=2)+'\n',encoding='utf-8')
    if completion.exists(): check_files(read('completion_manifest.json')['files'])
    print(json.dumps(dict(metadata_pool=32,parent_prescreens=4,unsupported=3,selected_parent_queries=1,
                         extra_normal_control=0,post_unseal_queries=1,verified_source_files=len(sources),
                         verified_quotes=quotes,verified_git_command_records=command_count,
                         independent_positive_detections=0,new_confirmed_cases=0,model_calls=0,
                         no_rule_reexecution=True,hash_check_is_not_semantic_truth=True)))


if __name__=='__main__':
    main()
