"""Project archived operands into frozen, externally reviewed diagnostic checks."""
from pathlib import Path
import copy
import hashlib
import importlib.util
import json
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / 'linux_bug_analyze'))
from linux_bug_analyze.contract_protocol import SCHEMA, CLAIM_ROLES, evaluate_contract

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name, value):
    (HERE/name).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
def sym(n): return {'symbol': n}
def op(n, *args): return {'op': n, 'args': list(args)}

def build(entry, event, kind, folder):
    context = event['event_id']
    values = {'selected_profile': True, 'cache': event['consumed_cache']}
    if kind == 'A':
        values.update(request=event['request'], result=event['result'])
        relation = op('or', op('and', op('le',sym('request'),sym('cache')),op('eq',sym('result'),sym('request'))),
                      op('and',op('lt',sym('cache'),sym('request')),op('eq',sym('result'),sym('cache'))))
    else:
        reference = 'adjacent_disk' if kind == 'B' else 'disk_at_deadline'
        if kind == 'B': values[reference] = event['adjacent_disk_sample']
        relation = op('eq',sym('cache'),sym(reference))
    names = list(values) + (['disk_at_deadline'] if kind == 'C' else [])
    symbols = {n: {'type': 'bool' if n == 'selected_profile' else 'int',
                   'role': 'configuration' if n == 'selected_profile' else 'observation'} for n in names}
    contract = dict(schema=SCHEMA,id='btrfs.layered.'+kind,revision=entry['revision'],authority_kind='consumer_inferred',
                    sufficient_for_correctness=False, symbols=symbols,scope=sym('selected_profile'),relation=relation,
                    required_claims={n:n for n in sorted(CLAIM_ROLES)},
                    field_origins={n:'researcher_authored' for n in ('scope','relation','symbols','required_claims','authority_kind')})
    documents = {}
    for n,p in [('review',HERE/'review.md'),('boot',folder/'boot.log'),('source',folder/'super.observed.c')]:
        documents[n] = dict(path=str(p),context_revision=entry['revision'],start_line=1,
                            end_line=len(p.read_text(encoding='utf-8').splitlines()),sha256=sha(p))
    refs = [dict(document='review',start_line=1,end_line=documents['review']['end_line']),
            dict(document='source',start_line=787,end_line=799)]
    record = dict(id=context+'.'+kind,revision=entry['revision'],basis='archived_runtime',context_id=context,
                  object_id=event['object_id'],sample_event=context+':record',deadline_event=context+':min',
                  sample_kind='sample',facts={},metadata=dict(operand_capture=event,
                  scope='manually selected verified ARM64 64K/64K positive-request observer archive'))
    ledger = dict(contract_id=contract['id'],revision=entry['revision'],basis='archived_runtime',context_id=context,
                  field_origins=contract['field_origins'],documents=documents,claims={})
    statements = {
        'authority':'Researcher-selected diagnostic relation A/B only; C readiness candidate remains unadmitted; see review.',
        'interface':'Positive max_inline branch in the saved observation transformation.',
        'consumer_requirement':'A: arithmetic-record consistency; B: cross-time numeric comparison; C: unproven deadline readiness.',
        'provider_binding':'Saved request/cache/result locals and later same-info super_copy getter; not simultaneous reference.',
        'object_binding':'Boot and mount scoped info identity; local same-info accesses only, no full lifecycle.',
        'deadline_binding':'The earlier min consumes saved operands; the later printed record is a distinct event.',
        'applicability':'Researcher selected verified instrumented 64K/64K positive 2048/8192 archive only.'}
    for role in sorted(CLAIM_ROLES):
        ledger['claims'][role] = dict(role=role,status='supported',origin='researcher_review',context_id=context,
                                    statement=statements[role],references=refs,object_id=record['object_id'])
    ledger['claims']['authority'].update(authority_kind='consumer_inferred',supports_requirement='consumer_requirement')
    ledger['claims']['applicability'].update(expression=contract['scope'],symbols=symbols)
    ledger['claims']['consumer_requirement'].update(expression=relation,symbols=symbols)
    ledger['claims']['deadline_binding'].update(event_id=record['deadline_event'],event_kind='content_consumption')
    if kind == 'C':
        ledger['claims']['provider_binding'].update(status='insufficient',statement='No disk_at_deadline or interval stability proof; later sample cannot substitute.')
        ledger['claims']['consumer_requirement']['status'] = 'insufficient'
    binding = dict(object_id=record['object_id'],event_id=record['sample_event'],deadline_id=record['deadline_event'])
    record['observation_binding'] = dict(binding,claim='binding')
    ledger['claims']['binding'] = dict(role='observation_binding',status='supported',origin='researcher_review',
        context_id=context,statement='Saved log record distinct from earlier min; no deadline promotion.',references=refs,
        binding=dict(binding,context_id=context,event_kind='sample'))
    for n,v in values.items():
        fact = dict(value=v,claim='fact.'+n)
        expected = dict(symbol=n,value=v,role=symbols[n]['role'],context_id=context)
        if symbols[n]['role'] == 'observation':
            fact.update(object_id=record['object_id'],event_id=record['sample_event'])
            expected.update(object_id=record['object_id'],event_id=record['sample_event'])
        record['facts'][n] = fact
        ledger['claims']['fact.'+n] = dict(role='fact',status='supported',origin='program_projection' if n!='selected_profile' else 'researcher_review',
            context_id=context,statement='Archive tuple projection; selected_profile is researcher registration.' if n=='selected_profile' else 'Saved operand or explicitly later disk sample, not same-time values.',
            references=refs if n=='selected_profile' else [dict(document='boot',start_line=event['boot_line'],end_line=event['boot_line'])],fact=expected)
    return dict(contract=contract,ledger=ledger,record=record)

def evaluate(bundle, **kwargs): return evaluate_contract(bundle['contract'],bundle['ledger'],bundle['record'],**kwargs)

def main():
    frozen=json.loads((HERE/'frozen_inputs.json').read_text(encoding='utf-8-sig'))
    for p,h in frozen.items(): assert sha(ROOT/p)==h,p
    raw=ROOT/'linux_bug_analyze/analysis_out/btrfs-consumer-observation-20261024'
    parser_path=ROOT/'linux_bug_analyze/experiments/case_taxonomy/btrfs_consumer_observation_20261024/observations.py'
    spec=importlib.util.spec_from_file_location('frozen_observations',parser_path)
    parser=importlib.util.module_from_spec(spec);spec.loader.exec_module(parser)
    bundles=[]
    for entry in json.loads((raw/'manifest.json').read_text()):
        folder=raw/entry['mode']
        for p,h in entry['artifacts'].items(): assert sha(folder/p)==h,p
        assert sha(folder/'super.observed.c')==entry['source_after_sha256']
        assert sha(folder/'observation.patch')==entry['patch_sha256']
        disk=(folder/'super.txt').read_text()
        fsid=re.search(r'^fsid\s+([0-9a-f-]+)',disk,re.M).group(1)
        events=parser.project_operands((folder/'boot.log').read_text(),fsid,'observer.'+entry['mode'])
        for event in events:
            for kind in ('A','B','C'): bundles.append(build(entry,event,kind,folder))
    # Persist reviewed inputs before executing the frozen evaluator.
    save('registered_inputs.json',bundles)
    results=[evaluate(b) for b in bundles]
    assert [r['relation_at_observation'] for r in results]==['satisfied','violated','insufficient']*2+['satisfied','satisfied','insufficient']*2
    assert all(r['relation_at_deadline']==r['whole_path']=='insufficient' for r in results)
    controls=[]
    for name in ('wrong_object','wrong_event','wrong_revision','tampered_fact','missing_review','promoted_sample','wrong_context','wrong_reference'):
        b=copy.deepcopy(bundles[0]);r=b['record'];l=b['ledger']
        if name=='wrong_object': r['object_id']='other'
        elif name=='wrong_event': r['facts']['cache']['event_id']='other'
        elif name=='wrong_revision': r['revision']='other'
        elif name=='tampered_fact': r['facts']['cache']['value']+=1
        elif name=='missing_review': del l['claims']['authority']
        elif name=='promoted_sample': r['sample_kind']='content_consumption';r['sample_event']=r['deadline_event']
        elif name=='wrong_context': r['context_id']='other'
        else: l['documents']['source']['context_revision']='other'
        out=evaluate(b);assert out['relation_at_observation']=='insufficient',name
        controls.append(dict(name=name,result=out))
    b=copy.deepcopy(bundles[0]);b['ledger']['basis']=b['record']['basis']='synthetic'
    b['record']['metadata']={'control':'Synthetic wrong arithmetic tuple; not a kernel event.'}
    for claim in b['ledger']['claims'].values():
        claim['origin']='synthetic_assumption';claim['statement']='Synthetic control premise; no assertion of real runtime truth.'
        claim['references']=[dict(document='control',start_line=1,end_line=1)]
    control=HERE/'synthetic_control.md'
    control.write_text('Synthetic unit control: copy schema only; change result to 999; all claims assumed, no real event or defect.\n',encoding='utf-8')
    b['ledger']['documents']={'control':dict(path=str(control),context_revision=b['contract']['revision'],start_line=1,end_line=1)}
    b['record']['facts']['result']['value']=999;b['ledger']['claims']['fact.result']['fact']['value']=999
    synthetic=evaluate(b,allow_synthetic=True)
    assert synthetic['relation_at_observation']=='violated'
    assert evaluate(b)['relation_at_observation']=='insufficient'
    save('synthetic_input.json',b)
    output=dict(real_events=4,evaluations=results,negative_controls=controls,synthetic_control=synthetic,
                new_boots=0,model_calls=0,independent_positives=0,independent_normals=0,
                limitations=['A prevalidated by parser; no incremental detection claim','B cross-time only','C lacks deadline reference/stability','All semantic registration researcher supplied'])
    save('results.json',output)
    print('4 archive events; 12 evaluations; 8 invalid bindings rejected; synthetic arithmetic violation confirmed; all deadlines insufficient')

if __name__=='__main__': main()
