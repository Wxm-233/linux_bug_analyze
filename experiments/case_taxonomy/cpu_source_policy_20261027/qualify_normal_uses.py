"""Known same-context defaults: normal source-policy controls, not new cases."""
from pathlib import Path
import ast
import copy
import json
import re

import source_adapter as adapter

HERE = Path(__file__).resolve().parent
GROUPS = {
    'package': {'id': 'topology_physical_package_id', 'mask': 'topology_core_cpumask',
                'show': 'physical_package_id', 'read': 'package_cpus', 'id_default': '-1',
                'id_body': '#define topology_physical_package_id(cpu) ((void)(cpu), -1)',
                'mask_body': '#define topology_core_cpumask(cpu) cpumask_of(cpu)'},
    'core': {'id': 'topology_core_id', 'mask': 'topology_sibling_cpumask',
             'show': 'core_id', 'read': 'core_cpus', 'id_default': '0',
             'id_body': '#define topology_core_id(cpu) ((void)(cpu), 0)',
             'mask_body': '#define topology_sibling_cpumask(cpu) cpumask_of(cpu)'},
}

def save(name, value):
    with (HERE / name).open('x', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write('\n')

def project(profile):
    receipt = adapter.verify(profile)
    root = receipt['source_tree']
    text = (HERE / 'preprocessing' / profile / 'topology.i').read_text()
    macros = {value[k] for value in GROUPS.values() for k in ['id', 'mask']}
    marker = re.compile(r'^#\s+(\d+)\s+("(?:[^"\\]|\\.)*")(?:\s+\d+)*\s*$')
    directive = re.compile(r'^#(define|undef)\s+(' + '|'.join(sorted(macros)) + r')(?=\(|\s|$)')
    definitions, state, uses, tables = [], {}, {}, {}
    filename, source_line = '<unknown>', 0
    for index, line in enumerate(text.splitlines(), 1):
        match = marker.match(line)
        if match:
            filename, source_line = ast.literal_eval(match[2]), int(match[1])
            continue
        row = {'file': filename, 'source_line': source_line, 'preprocessed_line': index}
        match = directive.match(line)
        if match:
            row.update(action=match[1], name=match[2], definition=line)
            definitions.append(copy.deepcopy(row))
            if match[1] == 'define':
                state[match[2]] = copy.deepcopy(row)
            else:
                state.pop(match[2], None)
        for group, binding in GROUPS.items():
            for kind, function in [('id', binding['show'] + '_show'), ('mask', binding['read'] + '_read')]:
                if line.startswith('static ssize_t ' + function + '('):
                    key = group + '.' + kind
                    adapter.need(key not in uses, 'ambiguous_normal_use:' + key)
                    uses[key] = {**copy.deepcopy(row), 'expanded_line': line, 'effective_definition': copy.deepcopy(state.get(binding[kind]))}
        for key, pattern in [('id', 'static struct attribute *default_attrs[]'), ('mask', 'static struct bin_attribute *bin_attrs[]')]:
            if line.startswith(pattern):
                adapter.need(key not in tables, 'ambiguous_normal_table:' + key)
                tables[key] = {**copy.deepcopy(row), 'state': copy.deepcopy(state)}
        source_line += 1
    result = []
    for group, binding in GROUPS.items():
        row = {'profile': profile, 'use': group, 'revision': receipt['revision'], 'config_sha256': receipt['before_sha256']['config'],
               'preprocessed_sha256': receipt['preprocessed_sha256'], 'id_native': False, 'mask_native': False,
               'listed_any': True, 'documented_default_permitted': {'id': True, 'mask': True}, 'uses': {}}
        for kind in ['id', 'mask']:
            use = uses[group + '.' + kind]
            definition = use['effective_definition']
            adapter.need(definition is not None and definition['file'] == root + '/' + adapter.PUBLIC, 'unreviewed_normal_origin')
            adapter.need(adapter.normalize(definition['definition']) == adapter.normalize(binding[kind + '_body']), 'unreviewed_normal_body')
            adapter.need(use['file'] == tables[kind]['file'] == root + '/' + adapter.DRIVER, 'normal_use_outside_driver')
            adapter.need(tables[kind]['state'][binding[kind]] == definition, 'normal_definition_changed_before_table')
            if kind == 'id':
                adapter.need('((void)(dev->id), ' + binding['id_default'] + ')' in use['expanded_line'], 'normal_ID_expansion_mismatch')
            else:
                adapter.need('get_cpu_mask(dev->id)' in use['expanded_line'], 'normal_mask_expansion_mismatch')
            row['uses'][kind] = use
        # Reuse the complete table parser rather than trusting a substring in
        # a declaration. Attribute membership is separate from origin facts.
        die = adapter.parse(text, root)
        id_members = adapter.legacy.project_static(die['pp'], root, 's390')['evidence']['arrays']['default_attrs']['members']
        mask_members = adapter.legacy.project_static(die['pp'], root, 's390')['evidence']['arrays']['bin_attrs']['members']
        expected = ['dev_attr_' + binding['show'], 'bin_attr_' + binding['read'], 'bin_attr_' + binding['read'] + '_list']
        adapter.need(all(name in id_members + mask_members for name in expected), 'normal_group_not_compiled')
        row['compiled_members'] = expected
        row['blanket_native_filter_would_flag'] = not (row['id_native'] and row['mask_native'])
        row['scope'] = 'documented defaults and reviewed static export; no runtime or physical truth'
        result.append(row)
    return result

def make_envelope(row, evidence):
    ident = 'cpu.normal.' + row['profile'] + '.' + row['use']
    origins = {key: 'researcher_authored' for key in ['scope', 'relation', 'symbols', 'required_claims', 'authority_kind']}
    names = ['sysfs_enabled', 'native_id', 'native_mask', 'id_default_allowed', 'mask_default_allowed', 'listed_any']
    symbols = {name: {'type': 'bool', 'role': 'observation' if name=='listed_any' else 'configuration'} for name in names}
    sym = lambda x: {'symbol': x}
    either = lambda a,b: {'op': 'or', 'args': [sym(a), sym(b)]}
    relation = {'op': 'or', 'args': [{'op': 'not', 'args': [sym('listed_any')]},
                                   {'op': 'and', 'args': [either('native_id','id_default_allowed'), either('native_mask','mask_default_allowed')]}]}
    contract = {'schema': 'architecture_contract_v1', 'id': ident, 'revision': row['revision'], 'authority_kind': 'documented',
                'sufficient_for_correctness': False, 'field_origins': origins, 'symbols': symbols,
                'required_claims': {role:'review.'+role for role in adapter.legacy.CLAIM_ROLES},
                'scope': sym('sysfs_enabled'), 'relation': relation}
    obj, sample, deadline = ident+'.attribute_group', ident+'.compiled_table', ident+'.potential_read'
    record = {'id': ident+'.record', 'revision': row['revision'], 'basis': 'source_projection', 'context_id': ident,
              'object_id': obj, 'sample_event': sample, 'deadline_event': deadline, 'sample_kind':'sample', 'facts':{},
              'observation_binding': {'object_id':obj, 'event_id':sample, 'deadline_id':deadline, 'claim':'review.observation'}}
    policy = HERE / 'normal_policy_review.md'
    documents = {name: {'context_revision':row['revision'], 'source_revision':row['revision'],
                        'path':str(path.relative_to(adapter.INNER)), 'sha256':adapter.sha(path),
                        'start_line':1, 'end_line':len(path.read_text(encoding='utf-8').splitlines())}
                 for name,path in [('evidence',evidence),('policy',policy)]}
    refs = lambda name: [{'document':name, 'start_line':1,'end_line':documents[name]['end_line']}]
    ledger = {'contract_id':ident,'revision':row['revision'],'basis':'source_projection','context_id':ident,
              'field_origins':copy.deepcopy(origins),'documents':documents,'claims':{},
              'policy_use':row['use'], 'policy_profile':row['profile'], 'policy_source_revision':row['revision']}
    for role in adapter.legacy.CLAIM_ROLES:
        ledger['claims']['review.'+role] = {'role':role,'status':'supported','origin':'researcher_review','context_id':ident,
            'statement':'Reviewed package/core default permission in the exact reconstructed context; no physical or runtime claim.',
            'references':refs('policy' if role in ['authority','consumer_requirement'] else 'evidence')}
    ledger['claims']['review.authority'].update(authority_kind='documented',supports_requirement='review.consumer_requirement')
    for role, expression in [('applicability','scope'),('consumer_requirement','relation')]:
        ledger['claims']['review.'+role].update(expression=copy.deepcopy(contract[expression]),symbols=copy.deepcopy(symbols))
    for role in ['consumer_requirement','provider_binding','object_binding','deadline_binding']:
        ledger['claims']['review.'+role]['object_id'] = obj
    ledger['claims']['review.deadline_binding'].update(event_id=deadline,event_kind='content_consumption',actual_occurrence_proved=False)
    binding = {'object_id':obj,'event_id':sample,'deadline_id':deadline,'context_id':ident,'event_kind':'sample'}
    ledger['claims']['review.observation'] = {'role':'observation_binding','status':'supported','origin':'researcher_review',
        'context_id':ident,'statement':'Compiled table only.','references':refs('evidence'),'binding':binding}
    values = dict(sysfs_enabled=True,native_id=False,native_mask=False,id_default_allowed=True,mask_default_allowed=True,listed_any=True)
    for name,value in values.items():
        fact = {'symbol':name,'value':value,'role':symbols[name]['role'],'context_id':ident}
        record['facts'][name] = {'value':value,'claim':'fact.'+name}
        if name=='listed_any':
            record['facts'][name].update(object_id=obj,event_id=sample)
            fact.update(object_id=obj,event_id=sample)
        from_policy = name.endswith('_allowed')
        ledger['claims']['fact.'+name] = {'role':'fact','status':'supported', 'origin':'researcher_review' if from_policy else 'program_projection',
            'context_id':ident,'statement':'Purpose-specific documented permission.' if from_policy else 'Reviewed same-context source fact.',
            'references':refs('policy' if from_policy else 'evidence'),'fact':fact}
    return {'profile':row['profile'],'use':row['use'],'contract':contract,'ledger':ledger,'record':record}

def evaluate(item):
    try:
        adapter.need(adapter.sha(adapter.CORE) == adapter.CORE_SHA, 'core_changed')
        adapter.need(item['profile'] in ['old_s390','fixed_s390'] and item['use'] in GROUPS, 'outside_reviewed_default_policy_use')
        adapter.need(item['ledger']['policy_use'] == item['use'] and item['ledger']['policy_profile']==item['profile'], 'normal_policy_context_mismatch')
        adapter.need(item['ledger']['policy_source_revision'] == adapter.PROFILES[item['profile']][0] == item['contract']['revision'], 'normal_policy_revision_mismatch')
        return adapter.legacy.evaluate_contract(item['contract'],item['ledger'],item['record'])
    except (ValueError, KeyError, TypeError) as exc:
        return {'relation_at_observation':'insufficient','whole_path':'insufficient','reasons':[str(exc)]}

def main():
    rows = [row for profile in ['old_s390','fixed_s390'] for row in project(profile)]
    save('normal_source_evidence.json', rows)
    evidence = HERE / 'normal_source_evidence.json'
    inputs = [make_envelope(row,evidence) for row in rows]
    outputs = [evaluate(item) for item in inputs]
    adapter.need(all(row['relation_at_observation']=='satisfied' for row in outputs), 'normal_source_policy_not_satisfied')
    controls = []
    def reject(name,mutate):
        item = copy.deepcopy(inputs[0]); mutate(item); result=evaluate(item)
        adapter.need(result['relation_at_observation']=='insufficient',(name,result))
        controls.append({'name':name,'result':result,'constructed_input':True})
    reject('defaults_cannot_be_borrowed_by_die',lambda i:i.update(use='die'))
    reject('defaults_cannot_be_borrowed_from_different_version',lambda i:i['ledger'].update(policy_source_revision=adapter.legacy.FIXED))
    reject('missing_origin_is_not_documented_default',lambda i:i['ledger']['claims']['review.provider_binding'].update(status='unknown'))
    save('normal_policy.json', {'inputs':inputs,'results':outputs,'controls':controls,
                              'source_use_contexts':4,'new_core_evaluations':7,'independent_normal':0,
                              'blanket_native_filter_flags':4,'not_detection_accuracy':True,
                              'qualification':'Same known case/configurations, purpose-scoped static documented defaults; not full correct behavior.'})
    print(json.dumps({'normal_source_use_contexts':len(rows),'satisfied':len(outputs),'controls_rejected':len(controls),'new_independent_normals':0}))

if __name__ == '__main__':
    main()
