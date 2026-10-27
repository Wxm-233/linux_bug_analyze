"""Local explicit relation envelopes, using the existing generic evaluator."""
from pathlib import Path
import copy
import hashlib
import sys

HERE=Path(__file__).resolve().parent
INNER=HERE.parents[2]
sys.path.insert(0,str(INNER))
from linux_bug_analyze.contract_protocol import CLAIM_ROLES,evaluate_contract

CORE=INNER/'linux_bug_analyze/contract_protocol.py'
CORE_SHA='42d37cc48d1c87a4c4b938d67a5acaedcc685ceb207deae3f72d7dcc88da830e'

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def sym(name): return {'symbol':name}
def literal(value): return {'literal':value}
def eq(a,b): return {'op':'eq','args':[a,b]}
def le(a,b): return {'op':'le','args':[a,b]}
def conjunction(*items): return {'op':'and','args':list(items)}

RELATIONS={
    'mapping':conjunction(eq(sym('unprovided_hardware'),literal([])),eq(sym('missing_selected_map'),literal([])),
                          eq(sym('selected_count'),sym('unique_target_count'))),
    'hardware':eq(sym('mismatched_online_hardware'),literal([])),
    'bound':eq(sym('runtime_bound'),sym('required_logical_upper')),
    'activation':conjunction(eq(sym('online_outside_present'),literal([])),eq(sym('present_outside_possible'),literal([])),
                            le(sym('online_count'),sym('activation_limit'))),
    'selection':le(sym('selected_count'),sym('selection_limit'))}

SAMPLES={'mapping':'arch_after_prepare','hardware':'completed_secondary_hardware_sample_window',
         'bound':'common_after_rebound','activation':'common_after_bringup','selection':'common_after_bringup'}

def envelope(context,revision,basis,kind,facts,evidence,sample_stage=None):
    ident='cpu.identity.'+context+'.'+kind
    obj=context+'.'+('CPU_identity_mapping' if kind in ['mapping','hardware'] else 'CPU_boot_domain')
    sample=context+'.'+(sample_stage or SAMPLES[kind]); deadline=context+'.unobserved_consumer_deadline'
    origins={key:'researcher_authored' for key in ['scope','relation','symbols','required_claims','authority_kind']}
    symbols={'supported_context':{'type':'bool','role':'configuration'}}
    for name,value in facts.items():
        symbols[name]={'type':'int_set' if isinstance(value,list) else 'int','role':'observation'}
    contract={'schema':'architecture_contract_v1','id':ident,'revision':revision,'authority_kind':'consumer_inferred',
        'sufficient_for_correctness':False,'field_origins':origins,'symbols':symbols,
        'required_claims':{role:'review.'+role for role in CLAIM_ROLES},'scope':sym('supported_context'),
        'relation':copy.deepcopy(RELATIONS[kind])}
    record={'id':ident+'.record','revision':revision,'basis':basis,'context_id':context,'object_id':obj,
        'sample_event':sample,'deadline_event':deadline,'sample_kind':'sample','facts':{},
        'observation_binding':{'object_id':obj,'event_id':sample,'deadline_id':deadline,'claim':'review.observation'}}
    documents={}
    for name,path in [('evidence',evidence),('policy',HERE/'checking_policy.md')]:
        documents[name]={'context_revision':revision,'source_revision':revision,'path':str(path.relative_to(INNER)),
            'sha256':sha(path),'start_line':1,'end_line':len(path.read_text(encoding='utf-8').splitlines())}
    refs=lambda name:[{'document':name,'start_line':1,'end_line':documents[name]['end_line']}]
    ledger={'contract_id':ident,'revision':revision,'basis':basis,'context_id':context,'field_origins':copy.deepcopy(origins),
            'documents':documents,'claims':{},'policy_origin':'researcher_review_of_development_materials',
            'actual_first_content_consumption_proved':False}
    for role in CLAIM_ROLES:
        ledger['claims']['review.'+role]={'role':role,'status':'supported','origin':'researcher_review','context_id':context,
            'statement':'Finite reviewed namespace/configuration/stage requirement; evidence tier is explicit, not physical truth or full lifecycle.',
            'references':refs('policy' if role in ['authority','consumer_requirement'] else 'evidence')}
    ledger['claims']['review.authority'].update(authority_kind='consumer_inferred',supports_requirement='review.consumer_requirement')
    for role,expr in [('applicability','scope'),('consumer_requirement','relation')]:
        ledger['claims']['review.'+role].update(expression=copy.deepcopy(contract[expr]),symbols=copy.deepcopy(symbols))
    for role in ['consumer_requirement','provider_binding','object_binding','deadline_binding']:
        ledger['claims']['review.'+role]['object_id']=obj
    ledger['claims']['review.deadline_binding'].update(event_id=deadline,event_kind='content_consumption',actual_occurrence_proved=False)
    ledger['claims']['review.observation']={'role':'observation_binding','status':'supported','origin':'researcher_review',
        'context_id':context,'statement':'Sample at the declared stage/window, without promotion to an unobserved deadline.',
        'references':refs('evidence'),'binding':{'object_id':obj,'event_id':sample,'deadline_id':deadline,'context_id':context,'event_kind':'sample'}}
    for name,value in {'supported_context':True,**facts}.items():
        declared={'symbol':name,'value':value,'role':symbols[name]['role'],'context_id':context}
        record['facts'][name]={'value':value,'claim':'fact.'+name}
        if name!='supported_context':
            declared.update(object_id=obj,event_id=sample); record['facts'][name].update(object_id=obj,event_id=sample)
        ledger['claims']['fact.'+name]={'role':'fact','status':'supported','origin':'program_projection','context_id':context,
            'statement':'Fact from this exact declared sample and evidence tier, not a model-authored fact.',
            'references':refs('evidence'),'fact':declared}
    return {'kind':kind,'contract':contract,'ledger':ledger,'record':record}

def evaluate(item):
    if sha(CORE)!=CORE_SHA:
        raise ValueError('common_contract_core_changed')
    return evaluate_contract(item['contract'],item['ledger'],item['record'])
