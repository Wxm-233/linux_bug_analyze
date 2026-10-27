"""Prepare a known-case integration packet without replaying any kernel."""
from pathlib import Path
import copy
import hashlib
import importlib.util
import json
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUTER = ROOT.parent
CASES = HERE.parent
RUNTIME = CASES/'s390_arch_contract_20261013/runtime'
sys.path.insert(0, str(ROOT))
from linux_bug_analyze.contract_protocol import CLAIM_ROLES, SCHEMA


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def save(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def main():
    assert not (HERE/'trial_inputs.json').exists(), 'preserve prepared packet'
    review = HERE/'reviewed_chain.md'
    assert review.is_file(), 'external source/role review must precede packet'
    names = ['当前代办.md', '当前研究方向与进展.md', '项目研究与文档写作交接说明.md']
    save(HERE/'notes_before.json', {'before_sha256': {name: sha((OUTER/name).read_bytes()) for name in names}})
    legacy_path = CASES/'state_predicate_extract_20261015/evaluate_predicates.py'
    spec = importlib.util.spec_from_file_location('n223_archive_foundation', legacy_path)
    legacy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(legacy)
    foundation = legacy.load_archives()
    assert foundation['inputs_unchanged'] and len(foundation['rows']) == 4
    assert not any(row['failed_foundation'] for row in foundation['rows'])
    protocol = json.loads((HERE/'protocol_pre.json').read_text(encoding='utf-8'))
    rows = []
    artifact_paths_all = {}
    for archived in foundation['rows']:
        profile = archived['profile']
        assert profile in protocol['profiles']
        directory = RUNTIME/'profiles'/profile
        build = json.loads((directory/'build.json').read_text(encoding='utf-8'))
        manifest_path = RUNTIME/(build['variant']+'_observer_sources.json')
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        files = {key: directory/name for key, name in (
            ('build','build.json'), ('boot','boot.json'), ('config','kernel.config'),
            ('autoconf','autoconf.h'), ('log','qemu_boot.stdout.log'))}
        files['source_manifest'] = manifest_path
        files['semantic_review'] = review
        for item in manifest['files']:
            files['source:'+item['path']] = RUNTIME/'observer_sources'/build['variant']/item['path']
        hashes = {key: sha(path.read_bytes()) for key, path in files.items()}
        context = 'n223.'+profile+'.'+hashes['config'][:12]+'.'+hashes['log'][:12]
        # The old loader's field name is historical; this is deliberately a sample.
        sample = archived['first_consumption']
        target = sample['cpu']
        obj = 'logged_smt_group.cpu'+str(target)
        sample_id = context+'.pre_irq_disable_sample'
        deadline = context+'.mask_content_iteration'
        contract = {
            'schema': SCHEMA, 'id': 'n223.target_lock_coverage', 'revision': build['revision'],
            'authority_kind': 'consumer_inferred', 'sufficient_for_correctness': False,
            'field_origins': {key: 'researcher_authored' for key in
                             ('scope','relation','symbols','required_claims','authority_kind')},
            'required_claims': {role: 'review.'+role for role in CLAIM_ROLES},
            'symbols': {'selected_path': {'type':'bool','role':'configuration'},
                        'members': {'type':'int_set','role':'observation'},
                        'target_cpu': {'type':'int','role':'observation'}},
            'scope': {'symbol':'selected_path'},
            'relation': {'op':'contains','args':[{'symbol':'members'},{'symbol':'target_cpu'}]}}
        documents = {}
        for key, path in files.items():
            doc_id = 'D_'+key.replace(':','_').replace('/','_').replace('.','_')
            documents[doc_id] = {'path': str(path.relative_to(ROOT)).replace('\\','/'),
                                 'context_revision': build['revision'], 'artifact_key': key,
                                 'sha256': hashes[key], 'start_line': 1,
                                 'end_line': len(path.read_text(encoding='utf-8-sig').splitlines())}
        def ref(key):
            doc_id = 'D_'+key.replace(':','_').replace('/','_').replace('.','_')
            doc = documents[doc_id]
            return {'document': doc_id,'start_line':doc['start_line'],'end_line':doc['end_line']}
        statements = {
            'authority': 'Externally reviewed conditional target-lock coverage purpose, not an independent universal specification.',
            'interface': 'The archived probe samples the group obtained through cpu_smt_mask(cpu) in sched_core_lock.',
            'consumer_requirement': 'If this loop must cover the selected target rq and no other protection is established, membership is a necessary narrow condition. This is a researcher premise.',
            'provider_binding': 'Bind only the local probe/getter producing this logged sample. Complete native preparation and all write effects are not certified.',
            'object_binding': 'Bind logged CPU and the local probe parameter as one logical sample role; do not prove physical lock-target alias identity.',
            'deadline_binding': 'The later for_each_cpu content traversal is the reviewed deadline; the pre-IRQ sample is a different event.',
            'applicability': 'Selected archived ordinary two-CPU SCHED_CORE startup under its own checked configuration.'}
        ledger = {'contract_id':contract['id'],'revision':build['revision'],'basis':'archived_runtime',
                  'context_id':context,'field_origins':copy.deepcopy(contract['field_origins']),
                  'documents':documents,'claims':{}}
        for role, statement in statements.items():
            refs = [ref('semantic_review')]
            if role == 'applicability': refs += [ref('config'),ref('autoconf')]
            else: refs += [ref('source:kernel/sched/core.c')]
            claim = {'role':role,'status':'supported','origin':'researcher_review',
                     'statement':statement,'context_id':context,'references':refs}
            if role in {'consumer_requirement','provider_binding','object_binding','deadline_binding'}:
                claim['object_id'] = obj
            ledger['claims']['review.'+role] = claim
        ledger['claims']['review.authority'].update(authority_kind='consumer_inferred',supports_requirement='review.consumer_requirement')
        for role, expression in [('applicability','scope'),('consumer_requirement','relation')]:
            ledger['claims']['review.'+role].update(expression=copy.deepcopy(contract[expression]),symbols=copy.deepcopy(contract['symbols']))
        ledger['claims']['review.deadline_binding'].update(event_id=deadline,event_kind='content_consumption')
        observation = {'context_id':context,'object_id':obj,'event_id':sample_id,
                       'deadline_id':deadline,'event_kind':'sample'}
        ledger['claims']['review.observation'] = {'role':'observation_binding','status':'supported',
            'origin':'researcher_review','statement':'Only the pre-local_irq_save mask sample; print is after unlock. No continuous-stability or precise-traversal claim.',
            'context_id':context,'references':[ref('semantic_review'),ref('source:kernel/sched/core.c'),ref('log')],
            'binding':observation}
        record = {'id':profile+'.sample','revision':build['revision'],'basis':'archived_runtime',
                  'context_id':context,'object_id':obj,'sample_event':sample_id,'sample_kind':'sample',
                  'deadline_event':deadline,'observation_binding':{**observation,'claim':'review.observation'},'facts':{}}
        values = {'selected_path':True,'members':[cpu for cpu in range(4) if sample['mask'] & (1<<cpu)],'target_cpu':target}
        for name, value in values.items():
            role = contract['symbols'][name]['role']
            projected = {'symbol':name,'value':value,'role':role,'context_id':context}
            fact = {'value':value,'claim':'fact.'+name}
            if role == 'observation':
                projected.update(object_id=obj,event_id=sample_id)
                fact.update(object_id=obj,event_id=sample_id)
            ledger['claims']['fact.'+name] = {'role':'fact','status':'supported','origin':'program_projection',
                'statement':'Archived event/config projection, not an inferred requirement or runtime causal-effect proof.',
                'context_id':context,'references':[ref('log') if role=='observation' else ref('config')],
                'fact':projected}
            record['facts'][name] = fact
        binding = {'profile':profile,'revision':build['revision'],'arch':build['arch'],'context_id':context,
                   'image_sha256':build['image_sha256'],'initrd_sha256':build['initrd_sha256'],
                   'artifact_sha256':hashes,'sample':{key:sample[key] for key in ('cpu','phase','line','seq')}}
        artifact_paths = {key:str(path.relative_to(ROOT)).replace('\\','/') for key,path in files.items()}
        artifact_paths_all.update({path:hashes[key] for key,path in artifact_paths.items()})
        rows.append({'profile':profile,'contract':contract,'ledger':ledger,'record':record,'binding':binding,
                     'artifact_paths':artifact_paths,'foundation':archived['foundation'],
                     'complete_preparation_effect':'insufficient','physical_lock_target_alias':'insufficient',
                     'exact_consumption_value':'insufficient','continuous_stability':'insufficient'})
    save(HERE/'trial_inputs.json', {'task':'N2.23','rows':rows,'archive_input_sha256':foundation['input_fingerprints'],
                                   'artifact_sha256':artifact_paths_all,'legacy_evaluator_sha256':sha(legacy_path.read_bytes()),
                                   'old_judgments_used':False,'sample_kind_corrected_explicitly':True})
    print(json.dumps({'prepared_profiles':len(rows),'archived_input_files':len(foundation['input_fingerprints']),
                      'new_kernel_boots':0,'new_model_calls':0}))


if __name__ == '__main__':
    main()
